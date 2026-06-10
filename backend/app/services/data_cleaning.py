import io
import json
import logging
import numpy as np
import pandas as pd
from datetime import datetime, date
from sqlalchemy.orm import Session
from app.database.models import Dataset, Product, SalesData
from app.core.constants import DatasetStatus

logger = logging.getLogger("data_cleaning")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

def normalize_column_name(name: str) -> str:
    """Normalize string by lowercasing, stripping spaces, and stripping underscores."""
    if not isinstance(name, str):
        return ""
    return name.strip().lower().replace(" ", "").replace("_", "")

# ─────────────────────────────────────────────────────────────────────────────
# COLUMN_MAPS: comprehensive aliases covering generic sales, food delivery,
# e-commerce, restaurant, and retail datasets.
# Keys = internal standard field names.
# Values = list of normalized (lowercased, no spaces/underscores) alias strings.
# ─────────────────────────────────────────────────────────────────────────────
COLUMN_MAPS = {
    # Product / item identifier
    "product_name": [
        "productname", "product", "itemname", "item", "sku", "name",
        "restaurant", "restaurantname", "restaurantid",  # food delivery
        "store", "outlet", "brand", "shopname",           # retail
        "servicename", "serviceid", "menuitem",            # service
    ],

    # Selling price per unit
    "price": [
        "price", "unitprice", "sellingprice", "rate", "listedprice",
        "offerprice", "baseprice", "avgprice", "averageprice",
        "dishprice", "itemprice",
    ],

    # Quantity / demand / orders
    "units_sold": [
        "unitssold", "quantity", "quantitysold", "units", "qty", "sold",
        "orders", "ordercount", "numorders", "totalorders",  # food delivery
        "demand", "requests", "transactions",
    ],

    # Revenue / turnover
    "revenue": [
        "revenue", "sales", "salesamount", "turnover", "totalsales",
        "grossrevenue", "netrevenue", "totalrevenue", "grosssales",
        "billingamount", "invoiceamount",
    ],

    # Cost per unit
    "cost": [
        "cost", "unitcost", "itemcost", "productcost", "expenses",
        "cogs", "costofgoods", "variablecost", "directcost",
    ],

    # Date
    "date": [
        "date", "salesdate", "timestamp", "transactiondate", "day",
        "orderdate", "invoicedate", "billingdate", "period",
    ],

    # Region / city / geography
    "region": [
        "region", "salesregion", "area", "location",
        "city", "cityname",                         # food delivery
        "state", "zone", "district", "territory", "market",
        "country", "branch", "hub",
    ],

    # Category / segment
    "category": [
        "category", "productcategory", "segment", "type",
        "foodcategory", "cuisine", "cuisinetype",   # food delivery
        "itemcategory", "dishcategory", "mealtype",
        "producttype", "itemtype", "genre",
        "department", "classification", "vertical",
    ],

    # Absolute profit (if directly available)
    "profit": [
        "profit", "netprofit", "profitamount",
        # NOTE: profit_margin_percent is handled separately below
    ],

    # Profit margin as a percentage column (e.g. 30.5 means 30.5%)
    "profit_margin_pct": [
        "profitmarginpercent", "profitmargin", "marginpercent",
        "margin", "grossprofitmargin", "netmargin",
    ],

    # Discount
    "discount": [
        "discount", "discountpercent", "discountamount", "discount%",
        "offerpct", "offerpercent",
    ],
}

def map_columns(df_columns: list) -> dict:
    """Map dataframe column names to standard fields using expanded alias table."""
    normalized_cols = {normalize_column_name(c): c for c in df_columns}
    mapping = {}

    logger.info("Auto-mapping columns: %s", list(df_columns))
    logger.info("Normalized lookup keys: %s", list(normalized_cols.keys()))

    for standard_name, aliases in COLUMN_MAPS.items():
        found = False
        for alias in aliases:
            if alias in normalized_cols:
                mapping[standard_name] = normalized_cols[alias]
                found = True
                logger.info("  ✓ %s → '%s' (matched alias '%s')", standard_name, normalized_cols[alias], alias)
                break
        if not found:
            mapping[standard_name] = None
            logger.debug("  ✗ %s → not found (checked: %s)", standard_name, aliases)

    return mapping

# Known food-delivery-specific category keywords for smart inference fallback
_FOOD_CATEGORY_KEYWORDS = [
    "biryani", "pizza", "burger", "sushi", "pasta", "noodles", "chinese",
    "salad", "sandwich", "wrap", "taco", "curry", "thali", "dosa",
    "idli", "roll", "momos", "soup", "dessert", "ice cream", "coffee",
    "juice", "shake", "waffle", "fries", "steak", "kebab", "wings",
    "rice", "pav bhaji", "chole", "dal", "roti", "paratha",
]

def _infer_category_from_name(product_name: str) -> str:
    """If no category column was found, try to infer from product/restaurant name."""
    lower = product_name.lower()
    for kw in _FOOD_CATEGORY_KEYWORDS:
        if kw in lower:
            return kw.title()
    return "General"


def clean_sales_dataframe(df: pd.DataFrame, mappings: dict = None) -> pd.DataFrame:
    """Clean the raw sales dataframe with robust schema-aware normalization."""
    # 1. Map columns (use provided mappings or auto-detect)
    if mappings is None:
        mappings = map_columns(df.columns)

    logger.info("Final column mappings resolved: %s", mappings)

    # 2. Check for required columns
    if not mappings.get("product_name") or mappings["product_name"] not in df.columns:
        raise ValueError("Missing required field: product_name (tried aliases: restaurant, item, sku, name, etc.)")

    if not mappings.get("date") or mappings["date"] not in df.columns:
        raise ValueError("Missing required field: date")

    # Resolve actual mapped columns (only include those that exist in df)
    col_mapping = {}
    for std_col, orig_col in mappings.items():
        if orig_col and orig_col in df.columns:
            col_mapping[std_col] = orig_col
        else:
            col_mapping[std_col] = None

    has_price = col_mapping.get("price") is not None
    has_units = col_mapping.get("units_sold") is not None
    has_revenue = col_mapping.get("revenue") is not None

    if not (has_price or has_revenue):
        raise ValueError("Missing required field: price or revenue")
    if not (has_units or has_revenue):
        raise ValueError("Unable to detect quantity column (tried: orders, qty, units, etc.)")

    # Rename mapped columns to standard names
    rename_dict = {orig_col: std_col for std_col, orig_col in col_mapping.items() if orig_col is not None}
    df = df.rename(columns=rename_dict)

    # Select only standard columns that are present
    # Include profit_margin_pct if it landed in the df (before further drops)
    standard_cols = list(COLUMN_MAPS.keys())
    cols_to_keep = [c for c in standard_cols if c in df.columns]
    df = df[cols_to_keep].copy()

    logger.info("Columns kept after mapping: %s", cols_to_keep)

    # ── Drop rows where critical identifiers are null ──────────────────────────
    df = df.dropna(subset=["product_name", "date"])
    df["product_name"] = df["product_name"].astype(str).str.strip()
    df = df[df["product_name"] != ""]

    # ── Date normalization ────────────────────────────────────────────────────
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    if df["date"].isna().all():
        raise ValueError("Date column contains only invalid values")
    df = df.dropna(subset=["date"])
    df["sales_date"] = df["date"].dt.date
    df = df.drop(columns=["date"])

    # ── Region / city ─────────────────────────────────────────────────────────
    if "region" not in df.columns:
        df["region"] = "National"
        logger.info("Region not found — defaulting to 'National'")
    else:
        df["region"] = df["region"].fillna("National").astype(str).str.strip()
        df.loc[df["region"] == "", "region"] = "National"
        unique_regions = df["region"].nunique()
        logger.info("Region column mapped — %d unique regions detected", unique_regions)

    # ── Category ──────────────────────────────────────────────────────────────
    if "category" not in df.columns:
        # Smart fallback: try to infer category from product name
        logger.warning(
            "Category column NOT found in dataset! "
            "Attempting smart inference from product_name. "
            "Rows will fall back to 'General' if no keyword match."
        )
        df["category"] = df["product_name"].apply(_infer_category_from_name)
        inferred_cats = df["category"].value_counts().to_dict()
        logger.info("Inferred category distribution: %s", inferred_cats)
    else:
        df["category"] = df["category"].fillna("").astype(str).str.strip()
        # For any empty values, try smart inference before falling back to General
        empty_mask = df["category"] == ""
        if empty_mask.any():
            logger.warning("%d rows have empty category — applying smart inference", empty_mask.sum())
            df.loc[empty_mask, "category"] = df.loc[empty_mask, "product_name"].apply(_infer_category_from_name)
        # Still-empty values get General
        df.loc[df["category"] == "", "category"] = "General"
        unique_cats = df["category"].nunique()
        cat_dist = df["category"].value_counts().to_dict()
        logger.info("Category column mapped — %d unique categories: %s", unique_cats, cat_dist)

    # ── Deduplication ─────────────────────────────────────────────────────────
    df = df.drop_duplicates()

    # ── Numeric cleaning ──────────────────────────────────────────────────────
    numeric_cols = ["price", "units_sold", "revenue", "cost", "profit", "profit_margin_pct", "discount"]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Add sentinel NaN columns for missing variables
    if "units_sold" not in df.columns:
        df["units_sold"] = np.nan
    if "price" not in df.columns:
        df["price"] = np.nan
    if "revenue" not in df.columns:
        df["revenue"] = np.nan

    # Fallback: units_sold = revenue / price
    mask_calc_units = df["units_sold"].isna() & df["revenue"].notna() & df["price"].notna()
    price_not_zero = df["price"] > 0
    df.loc[mask_calc_units & price_not_zero, "units_sold"] = (
        df.loc[mask_calc_units & price_not_zero, "revenue"]
        / df.loc[mask_calc_units & price_not_zero, "price"]
    ).round()

    # Fallback: price = revenue / units_sold
    mask_calc_price = df["price"].isna() & df["revenue"].notna() & df["units_sold"].notna()
    units_not_zero = df["units_sold"] > 0
    df.loc[mask_calc_price & units_not_zero, "price"] = (
        df.loc[mask_calc_price & units_not_zero, "revenue"]
        / df.loc[mask_calc_price & units_not_zero, "units_sold"]
    )

    # Fallback: revenue = price × units_sold
    mask_calc_revenue = df["revenue"].isna() & df["price"].notna() & df["units_sold"].notna()
    df.loc[mask_calc_revenue, "revenue"] = (
        df.loc[mask_calc_revenue, "price"] * df.loc[mask_calc_revenue, "units_sold"]
    )

    df = df.dropna(subset=["price", "units_sold", "revenue"])
    df = df[(df["price"] > 0) & (df["units_sold"] >= 0) & (df["revenue"] >= 0)]

    # ── Cost derivation ───────────────────────────────────────────────────────
    DEFAULT_MARGIN = 0.30
    if "cost" not in df.columns:
        df["cost"] = df["price"] * (1.0 - DEFAULT_MARGIN)
    else:
        df["cost"] = df["cost"].fillna(df["price"] * (1.0 - DEFAULT_MARGIN))
        df.loc[df["cost"] <= 0, "cost"] = df["price"] * (1.0 - DEFAULT_MARGIN)

    # ── Profit derivation ─────────────────────────────────────────────────────
    # Priority: absolute profit column > profit_margin_pct column > default margin
    if "profit" in df.columns and df["profit"].notna().any():
        df["profit"] = df["profit"].fillna(df["revenue"] * DEFAULT_MARGIN)
        logger.info("Using absolute profit column")
    elif "profit_margin_pct" in df.columns and df["profit_margin_pct"].notna().any():
        # profit_margin_pct is stored as a percentage (e.g. 30.5 means 30.5%)
        # Absolute profit = revenue × (margin% / 100)
        logger.info("Deriving absolute profit from profit_margin_pct column")
        df["profit"] = df["revenue"] * (df["profit_margin_pct"].clip(0, 100) / 100.0)
        df["profit"] = df["profit"].fillna(df["revenue"] * DEFAULT_MARGIN)
        # Also back-calculate cost per unit from margin
        df["cost"] = (df["revenue"] * (1.0 - df["profit_margin_pct"].clip(0, 100) / 100.0)) / df["units_sold"].replace(0, np.nan)
        df["cost"] = df["cost"].fillna(df["price"] * (1.0 - DEFAULT_MARGIN))
    else:
        logger.info("No profit column found — defaulting to %.0f%% margin", DEFAULT_MARGIN * 100)
        df["profit"] = df["revenue"] - (df["cost"] * df["units_sold"])

    # ── Final casts ───────────────────────────────────────────────────────────
    df["price"] = df["price"].astype(float)
    df["units_sold"] = df["units_sold"].fillna(0).astype(int)
    df["revenue"] = df["revenue"].astype(float)
    df["cost"] = df["cost"].astype(float)
    df["profit"] = df["profit"].astype(float)

    logger.info(
        "Cleaning complete — %d rows | %d unique products | %d unique categories | %d unique regions",
        len(df), df["product_name"].nunique(), df["category"].nunique(), df["region"].nunique()
    )

    return df.sort_values(by="sales_date")

def process_uploaded_file(db: Session, file_content: bytes, file_name: str, dataset_id: str, mappings: dict = None) -> dict:
    """Parse, clean, and insert raw uploaded sales data in the database."""
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise ValueError(f"Dataset {dataset_id} not found.")
        
    dataset.status = DatasetStatus.PROCESSING
    db.commit()
    
    try:
        # Load CSV or Excel
        if file_name.endswith((".xlsx", ".xls")):
            df_raw = pd.read_excel(io.BytesIO(file_content))
        else:
            df_raw = pd.read_csv(io.BytesIO(file_content))
            
        raw_rows_count = len(df_raw)
        duplicates_removed = int(df_raw.duplicated().sum())
        
        # Clean dataframe
        df_cleaned = clean_sales_dataframe(df_raw, mappings)
        
        if df_cleaned.empty:
            raise ValueError("The uploaded file has no valid sales transactions after data cleaning.")
            
        cleaned_rows_count = len(df_cleaned)
        missing_values_fixed = max(0, raw_rows_count - cleaned_rows_count - duplicates_removed)
        
        # ── Detect if dataset has multi-category-per-product pattern ─────────────
        # If the number of unique (product_name, category) combos is significantly
        # higher than unique product_names, this is a multi-category dataset
        # (e.g. food delivery where one restaurant serves many categories).
        # In that case, use (product_name + " | " + category) as the Product entity
        # to preserve distinct category segmentation in all analytics.
        n_products = df_cleaned["product_name"].nunique()
        n_product_cat_combos = df_cleaned[["product_name", "category"]].drop_duplicates().shape[0]
        is_multi_category_dataset = n_product_cat_combos > n_products

        if is_multi_category_dataset:
            logger.info(
                "Multi-category dataset detected (%d products, %d product×category combos). "
                "Using category as primary product dimension for analytics segmentation.",
                n_products, n_product_cat_combos
            )
            # Use category as the analytics product name, keeping region from first match
            # This gives us proper category-level revenue mix and elasticity analysis
            df_cleaned["_analytics_product"] = df_cleaned["category"]
            # Region = most common city for this category
        else:
            df_cleaned["_analytics_product"] = df_cleaned["product_name"]

        unique_products = (
            df_cleaned[["_analytics_product", "category", "region"]]
            .drop_duplicates(subset=["_analytics_product"])
            .rename(columns={"_analytics_product": "product_name"})
        )

        product_map = {}
        for _, row in unique_products.iterrows():
            prod_name = row["product_name"]
            db_product = db.query(Product).filter(Product.product_name == prod_name).first()
            if not db_product:
                db_product = Product(
                    product_name=prod_name,
                    category=row["category"],
                    region=row["region"]
                )
                db.add(db_product)
                db.flush()
            else:
                db_product.category = row["category"]
                db_product.region = row["region"]

            product_map[prod_name] = db_product.id
            
        # Insert SalesData
        # Use _analytics_product (category name in multi-category datasets) for the product_map key
        sales_records = []
        for _, row in df_cleaned.iterrows():
            analytics_key = row.get("_analytics_product", row["product_name"])
            prod_id = product_map[analytics_key]
            sales_records.append(
                SalesData(
                    dataset_id=dataset.id,
                    product_id=prod_id,
                    sales_date=row["sales_date"],
                    price=float(row["price"]),
                    quantity_sold=int(row["units_sold"]),
                    revenue=float(row["revenue"]),
                    cost=float(row["cost"]),
                    profit=float(row["profit"])
                )
            )
            
        db.bulk_save_objects(sales_records)
        
        # Calculate summary metrics
        analytics_product_col = "_analytics_product" if "_analytics_product" in df_cleaned.columns else "product_name"
        summary = {
            "rows_processed": cleaned_rows_count,
            "duplicates_removed": duplicates_removed,
            "missing_values_fixed": missing_values_fixed,
            "mapped_columns": {k: v for k, v in (mappings or map_columns(df_raw.columns)).items() if v},
            "detected_products": int(df_cleaned[analytics_product_col].nunique()),
            "detected_categories": int(df_cleaned["category"].nunique()),
            "date_range": f"{df_cleaned['sales_date'].min()} to {df_cleaned['sales_date'].max()}",
            "total_revenue": float(df_cleaned["revenue"].sum()),
            "is_multi_category_dataset": is_multi_category_dataset if "_analytics_product" in df_cleaned.columns else False
        }
        
        dataset.status = DatasetStatus.PROCESSING
        dataset.total_records = cleaned_rows_count
        dataset.summary_metadata = json.dumps(summary)
        db.commit()
        
        return {
            "dataset_id": dataset.id,
            "status": DatasetStatus.PROCESSED,
            "total_records": cleaned_rows_count,
            "products_processed": len(product_map),
            "summary": summary
        }
        
    except Exception as e:
        db.rollback()
        dataset.status = DatasetStatus.FAILED
        db.commit()
        raise e

