import math
import numpy as np
import pandas as pd
from sqlalchemy.orm import Session
from app.database.models import SalesData, ElasticityAnalysis, Product

def simulate_price_impact(db: Session, product_id: str, simulated_price: float) -> dict:
    """Simulate revenue and profit changes for a product given a hypothetical price."""
    # 1. Fetch product metadata
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise ValueError(f"Product {product_id} not found.")
        
    # 2. Fetch sales data to compute baselines and average unit cost
    sales = db.query(SalesData).filter(SalesData.product_id == product_id).all()
    if not sales:
        return {}
        
    df = pd.DataFrame([{
        "price": float(s.price),
        "quantity": int(s.quantity_sold),
        "cost": float(s.cost),
        "revenue": float(s.revenue),
        "profit": float(s.profit)
    } for s in sales])
    
    def safe_float(v, fallback=0.0):
        try:
            val = float(v)
            if math.isnan(val) or math.isinf(val):
                return fallback
            return val
        except Exception:
            return fallback

    # Baseline calculations
    base_price = safe_float(df["price"].mean())
    base_daily_qty = safe_float(df["quantity"].mean())
    avg_unit_cost = safe_float(df["cost"].mean())
    
    base_revenue = base_daily_qty * base_price
    base_profit = base_daily_qty * (base_price - avg_unit_cost)
    
    # 3. Fetch elasticity score
    elasticity_rec = db.query(ElasticityAnalysis).filter(ElasticityAnalysis.product_id == product_id).first()
    elasticity = safe_float(elasticity_rec.elasticity_score) if elasticity_rec else -0.5
    
    # 4. Simulation using log-log constant elasticity demand curve
    # Q_sim = Q_base * (P_sim / P_base) ^ elasticity
    if base_price > 0 and simulated_price > 0:
        ratio = simulated_price / base_price
        # Avoid mathematical domain errors on negative ratio
        try:
            simulated_qty = base_daily_qty * (ratio ** elasticity)
        except Exception:
            simulated_qty = 0.0
    else:
        simulated_qty = 0.0
        
    simulated_qty = max(0.0, safe_float(simulated_qty))
    
    # Simulated revenue and profit
    simulated_revenue = simulated_qty * simulated_price
    simulated_profit = simulated_qty * (simulated_price - avg_unit_cost)
    
    # Changes
    rev_change_pct = ((simulated_revenue - base_revenue) / base_revenue * 100) if base_revenue > 0 else 0.0
    prof_change_pct = ((simulated_profit - base_profit) / abs(base_profit) * 100) if base_profit != 0 else 0.0
    
    return {
        "product_id": product_id,
        "product_name": product.product_name,
        "base_price": safe_float(base_price),
        "base_daily_quantity": safe_float(base_daily_qty),
        "unit_cost": safe_float(avg_unit_cost),
        "simulated_price": safe_float(simulated_price),
        "predicted_demand": safe_float(simulated_qty),
        "predicted_revenue": safe_float(simulated_revenue),
        "predicted_profit": safe_float(simulated_profit),
        "revenue_change_percent": safe_float(rev_change_pct),
        "profit_change_percent": safe_float(prof_change_pct),
        "elasticity_score": safe_float(elasticity),
        "elasticity_type": elasticity_rec.elasticity_type if elasticity_rec else "Inelastic"
    }
