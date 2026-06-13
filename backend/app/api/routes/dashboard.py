from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database.db import get_db
from app.database.models import SalesData, Product, User, ElasticityAnalysis
from app.database.schemas import DashboardResponse
from app.api.routes.auth import get_current_user
from typing import Optional, List
import pandas as pd
from app.services.analytics import apply_rolling_average

router = APIRouter(prefix="/dashboard", tags=["Dashboard Analytics"])

@router.get("/summary", response_model=DashboardResponse)
def get_dashboard_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Fetch high-level business intelligence metrics and chart data."""
    # 1. Fetch Sales and Product stats
    sales_count = db.query(SalesData).count()
    
    if sales_count == 0:
        # Return empty structure
        return {
            "kpis": {
                "total_revenue": {"title": "Total Revenue", "value": "₹0.00", "change": "0.0%", "trend": "neutral"},
                "total_profit": {"title": "Total Profit", "value": "₹0.00", "change": "0.0%", "trend": "neutral"},
                "avg_margin": {"title": "Average Margin", "value": "0.0%", "change": "0.0%", "trend": "neutral"},
                "active_products": {"title": "Active Products", "value": "0", "change": "0.0%", "trend": "neutral"}
            },
            "sales_trends": [],
            "category_share": [],
            "region_share": [],
            "top_products": []
        }
        
    # Calculate Total Revenue, Cost, Profit
    total_rev = db.query(func.sum(SalesData.revenue)).scalar() or 0.0
    total_profit = db.query(func.sum(SalesData.profit)).scalar() or 0.0
    margin = (total_profit / total_rev * 100) if total_rev > 0 else 0.0
    active_products = db.query(Product).count()
    
    # Calculate period-over-period KPI changes dynamically
    dates = db.query(func.min(SalesData.sales_date), func.max(SalesData.sales_date)).first()
    min_date, max_date = dates[0], dates[1]
    
    if min_date and max_date and min_date != max_date:
        mid_date = min_date + (max_date - min_date) / 2
        
        # Revenue Change
        rev_first = db.query(func.sum(SalesData.revenue)).filter(SalesData.sales_date < mid_date).scalar() or 0.0
        rev_second = db.query(func.sum(SalesData.revenue)).filter(SalesData.sales_date >= mid_date).scalar() or 0.0
        rev_change = ((float(rev_second) - float(rev_first)) / float(rev_first) * 100.0) if float(rev_first) > 0 else 0.0
        rev_trend = "up" if rev_change >= 0 else "down"
        rev_change_str = f"{rev_change:+.1f}%"
        
        # Profit Change
        profit_first = db.query(func.sum(SalesData.profit)).filter(SalesData.sales_date < mid_date).scalar() or 0.0
        profit_second = db.query(func.sum(SalesData.profit)).filter(SalesData.sales_date >= mid_date).scalar() or 0.0
        profit_change = ((float(profit_second) - float(profit_first)) / float(profit_first) * 100.0) if float(profit_first) > 0 else 0.0
        profit_trend = "up" if profit_change >= 0 else "down"
        profit_change_str = f"{profit_change:+.1f}%"
        
        # Margin Change
        margin_first = (float(profit_first) / float(rev_first) * 100.0) if float(rev_first) > 0 else 0.0
        margin_second = (float(profit_second) / float(rev_second) * 100.0) if float(rev_second) > 0 else 0.0
        margin_change = margin_second - margin_first
        margin_trend = "up" if margin_change >= 0 else "down"
        margin_change_str = f"{margin_change:+.1f}%"
        
        # Active Products Change
        prod_first = db.query(func.count(func.distinct(SalesData.product_id))).filter(SalesData.sales_date < mid_date).scalar() or 0
        prod_second = db.query(func.count(func.distinct(SalesData.product_id))).filter(SalesData.sales_date >= mid_date).scalar() or 0
        prod_change = ((prod_second - prod_first) / prod_first * 100.0) if prod_first > 0 else 0.0
        prod_trend = "up" if prod_change >= 0 else "down"
        prod_change_str = f"{prod_change:+.1f}%"
    else:
        rev_trend, rev_change_str = "neutral", "0.0%"
        profit_trend, profit_change_str = "neutral", "0.0%"
        margin_trend, margin_change_str = "neutral", "0.0%"
        prod_trend, prod_change_str = "neutral", "0.0%"

    # 2. Extract Sales Trends (aggregated by date)
    trend_query = db.query(
        SalesData.sales_date,
        func.sum(SalesData.revenue).label("rev"),
        func.sum(SalesData.profit).label("prof")
    ).group_by(SalesData.sales_date).order_by(SalesData.sales_date).all()
    
    sales_trends = [
        {"label": str(t[0]), "revenue": float(t[1]), "profit": float(t[2])}
        for t in trend_query
    ]
    
    # 3. Share by Product Category
    cat_query = db.query(
        Product.category,
        func.sum(SalesData.revenue)
    ).join(SalesData, SalesData.product_id == Product.id)\
     .group_by(Product.category).all()
     
    category_share = [{"category": c[0], "revenue": float(c[1])} for c in cat_query]
    
    # 4. Share by Region
    reg_query = db.query(
        Product.region,
        func.sum(SalesData.revenue)
    ).join(SalesData, SalesData.product_id == Product.id)\
     .group_by(Product.region).all()
     
    region_share = [{"region": r[0], "revenue": float(r[1])} for r in reg_query]
    
    # 5. Top 10 Performing Products
    top_query = db.query(
        Product.id,
        Product.product_name,
        Product.category,
        Product.region,
        func.sum(SalesData.revenue).label("rev"),
        func.sum(SalesData.profit).label("prof"),
        func.sum(SalesData.quantity_sold).label("qty"),
        ElasticityAnalysis.elasticity_score,
        ElasticityAnalysis.elasticity_type
    ).join(SalesData, SalesData.product_id == Product.id)\
     .outerjoin(ElasticityAnalysis, ElasticityAnalysis.product_id == Product.id)\
     .group_by(Product.id)\
     .order_by(func.sum(SalesData.revenue).desc())\
     .limit(10).all()
     
    top_products = [
        {
            "id": t[0],
            "product_name": t[1],
            "category": t[2],
            "region": t[3],
            "revenue": float(t[4]),
            "profit": float(t[5]),
            "quantity_sold": int(t[6]),
            "elasticity_score": float(t[7]) if t[7] is not None else None,
            "elasticity_type": t[8]
        }
        for t in top_query
    ]
    
    return {
        "kpis": {
            "total_revenue": {"title": "Total Revenue", "value": f"₹{total_rev:,.2f}", "change": rev_change_str, "trend": rev_trend},
            "total_profit": {"title": "Total Profit", "value": f"₹{total_profit:,.2f}", "change": profit_change_str, "trend": profit_trend},
            "avg_margin": {"title": "Average Margin", "value": f"{margin:.1f}%", "change": margin_change_str, "trend": margin_trend},
            "active_products": {"title": "Active Products", "value": str(active_products), "change": prod_change_str, "trend": prod_trend}
        },
        "sales_trends": sales_trends,
        "category_share": category_share,
        "region_share": region_share,
        "top_products": top_products
    }

@router.get("/trends")
def get_trends(
    interval: str = "daily",
    category: Optional[str] = None,
    metric: str = "revenue",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retrieve raw daily sales trend data with category filters and rolling averages."""
    # 1. Fetch sales trends grouped by sales_date
    query = db.query(
        SalesData.sales_date,
        func.sum(SalesData.revenue).label("revenue"),
        func.sum(SalesData.profit).label("profit"),
        func.sum(SalesData.quantity_sold).label("quantity_sold")
    )
    
    if category:
        query = query.join(Product, SalesData.product_id == Product.id).filter(Product.category == category)
        
    query = query.group_by(SalesData.sales_date).order_by(SalesData.sales_date)
    results = query.all()
    
    if not results:
        return []
        
    # 2. Query top category per date to include in tooltip context
    top_cat_query = db.query(
        SalesData.sales_date,
        Product.category,
        func.sum(SalesData.revenue).label("rev")
    ).join(Product, SalesData.product_id == Product.id)\
     .group_by(SalesData.sales_date, Product.category).all()
     
    top_cats = {}
    for d, cat, rev in top_cat_query:
        d_str = str(d)
        val = float(rev or 0.0)
        if d_str not in top_cats or val > top_cats[d_str]["rev"]:
            top_cats[d_str] = {"category": cat, "rev": val}
            
    # 3. Compile daily record list
    data = []
    for r in results:
        d_str = str(r.sales_date)
        rev_val = float(r.revenue or 0.0)
        qty_val = int(r.quantity_sold or 0)
        profit_val = float(r.profit or 0.0)
        avg_val = (rev_val / qty_val) if qty_val > 0 else 0.0
        top_cat = top_cats.get(d_str, {}).get("category", "General")
        
        data.append({
            "date": d_str,
            "revenue": rev_val,
            "profit": profit_val,
            "quantity_sold": qty_val,
            "avg_order_value": avg_val,
            "top_category": top_cat
        })
        
    df = pd.DataFrame(data)
    
    # 4. Map the requested metric to actual column
    target_metric = metric
    if target_metric not in ["revenue", "profit", "quantity_sold", "avg_order_value"]:
        target_metric = "revenue"
        
    # Compute 3-day and 7-day rolling averages on the target metric
    df["rolling_avg_3"] = apply_rolling_average(df, target_metric, 3)
    df["rolling_avg_7"] = apply_rolling_average(df, target_metric, 7)
    
    # Fill NaN values with 0
    df = df.fillna(0)
    
    return df.to_dict(orient="records")

