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
        return save_fallback_elasticity(db, product_id, -0.5, "Inelastic (Insufficient Data)", sample_size=len(df))
        
    # Group by price to get volume at different price points
    df_grouped = df.groupby("price").agg({"quantity": "mean"}).reset_index()
    
    # If standard deviation of price is 0, we can't calculate elasticity
    if df_grouped["price"].std() == 0 or len(df_grouped) < 2:
        return save_fallback_elasticity(db, product_id, -0.2, "Inelastic (No Price Variation)", sample_size=len(df))
        
    # Fit log-log model: ln(Q) = beta_0 + beta_1 * ln(P)
    # Add a small constant to quantity to handle 0 quantity
    x = np.log(df_grouped["price"].values).reshape(-1, 1)
    y = np.log(df_grouped["quantity"].values + 0.1)
    
    model = LinearRegression()
    model.fit(x, y)
    
    elasticity_score = float(model.coef_[0])
    
    # Calculate R-squared and sample size
    r_squared = float(model.score(x, y))
    if np.isnan(r_squared) or np.isinf(r_squared):
        r_squared = 0.0
    r_squared = max(0.0, min(1.0, r_squared))
    
    sample_size = len(df)
    
    # Calculate confidence score
    confidence_score = min(sample_size / 100.0, 1.0) * 0.4 + r_squared * 0.6
    confidence_score = max(0.0, min(1.0, confidence_score))
    
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
        sample_size=sample_size,
        r_squared=r_squared,
        confidence_score=confidence_score,
        analysis_date=datetime.now(timezone.utc)
    )
    db.add(analysis)
    db.commit()
    
    return {
        "status": "success",
        "elasticity_score": elasticity_score,
        "elasticity_type": el_type,
        "sample_size": sample_size,
        "r_squared": r_squared,
        "confidence_score": confidence_score
    }

def save_fallback_elasticity(
    db: Session,
    product_id: str,
    score: float,
    reason: str,
    sample_size: int = 0
) -> dict:
    """Save default elasticity analysis for products with static pricing or low data."""
    db.query(ElasticityAnalysis).filter(ElasticityAnalysis.product_id == product_id).delete()
    
    r_squared = 0.0
    confidence_score = min(sample_size / 100.0, 1.0) * 0.4 + r_squared * 0.6
    confidence_score = max(0.0, min(1.0, confidence_score))
    
    analysis = ElasticityAnalysis(
        product_id=product_id,
        elasticity_score=score,
        elasticity_type=ElasticityType.INELASTIC,
        sample_size=sample_size,
        r_squared=r_squared,
        confidence_score=confidence_score,
        analysis_date=datetime.now(timezone.utc)
    )
    db.add(analysis)
    db.commit()
    
    return {
        "status": "fallback",
        "elasticity_score": score,
        "elasticity_type": ElasticityType.INELASTIC,
        "reason": reason,
        "sample_size": sample_size,
        "r_squared": r_squared,
        "confidence_score": confidence_score
    }

def calculate_all_elasticities(db: Session) -> dict:
    """Calculate elasticity for all products in the database."""
    products = db.query(Product).all()
    results = {}
    for p in products:
        results[p.product_name] = calculate_product_elasticity(db, p.id)
    return results
