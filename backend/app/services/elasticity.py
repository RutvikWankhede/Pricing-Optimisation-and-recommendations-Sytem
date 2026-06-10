import numpy as np
import pandas as pd
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sklearn.linear_model import LinearRegression
from app.database.models import SalesData, ElasticityAnalysis, Product
from app.core.constants import ElasticityType

def calculate_product_elasticity(db: Session, product_id: str) -> dict:
    """Calculate price elasticity of demand for a product and save results."""
    # 1. Fetch sales data
    sales = db.query(SalesData).filter(SalesData.product_id == product_id).all()
    if not sales:
        return {"status": "skipped", "reason": "No sales data found for product."}
        
    data = []
    for s in sales:
        data.append({
            "price": float(s.price),
            "quantity": int(s.quantity_sold)
        })
        
    df = pd.DataFrame(data)
    
    # Check minimum observations
    if len(df) < 5:
        # Save fallback inelastic elasticity
        return save_fallback_elasticity(db, product_id, -0.5, "Inelastic (Insufficient Data)")
        
    # Group by price to get volume at different price points
    df_grouped = df.groupby("price").agg({"quantity": "mean"}).reset_index()
    
    # If standard deviation of price is 0, we can't calculate elasticity
    if df_grouped["price"].std() == 0 or len(df_grouped) < 2:
        return save_fallback_elasticity(db, product_id, -0.2, "Inelastic (No Price Variation)")
        
    # Fit log-log model: ln(Q) = beta_0 + beta_1 * ln(P)
    # Add a small constant to quantity to handle 0 quantity
    x = np.log(df_grouped["price"].values).reshape(-1, 1)
    y = np.log(df_grouped["quantity"].values + 0.1)
    
    model = LinearRegression()
    model.fit(x, y)
    
    elasticity_score = float(model.coef_[0])
    
    # Classify elasticity type
    abs_elasticity = abs(elasticity_score)
    if abs_elasticity > 1.1:
        el_type = ElasticityType.ELASTIC
    elif abs_elasticity < 0.9:
        el_type = ElasticityType.INELASTIC
    else:
        el_type = ElasticityType.UNITARY
        
    # Clean up old analysis for this product
    db.query(ElasticityAnalysis).filter(ElasticityAnalysis.product_id == product_id).delete()
    
    # Save new analysis
    analysis = ElasticityAnalysis(
        product_id=product_id,
        elasticity_score=elasticity_score,
        elasticity_type=el_type,
        analysis_date=datetime.now(timezone.utc)
    )
    db.add(analysis)
    db.commit()
    
    return {
        "status": "success",
        "elasticity_score": elasticity_score,
        "elasticity_type": el_type
    }

def save_fallback_elasticity(db: Session, product_id: str, score: float, reason: str) -> dict:
    """Save default elasticity analysis for products with static pricing or low data."""
    db.query(ElasticityAnalysis).filter(ElasticityAnalysis.product_id == product_id).delete()
    
    analysis = ElasticityAnalysis(
        product_id=product_id,
        elasticity_score=score,
        elasticity_type=ElasticityType.INELASTIC,
        analysis_date=datetime.now(timezone.utc)
    )
    db.add(analysis)
    db.commit()
    
    return {
        "status": "fallback",
        "elasticity_score": score,
        "elasticity_type": ElasticityType.INELASTIC,
        "reason": reason
    }

def calculate_all_elasticities(db: Session) -> dict:
    """Calculate elasticity for all products in the database."""
    products = db.query(Product).all()
    results = {}
    for p in products:
        results[p.product_name] = calculate_product_elasticity(db, p.id)
    return results
