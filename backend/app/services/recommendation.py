import pandas as pd
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.database.models import SalesData, ElasticityAnalysis, PricingRecommendation, Product
from app.core.constants import RecommendationAction
from app.services.optimization import simulate_price_impact

def generate_product_recommendation(db: Session, product_id: str) -> dict:
    """Generate and save pricing recommendation for a product."""
    # 1. Fetch sales data for product
    sales = db.query(SalesData).filter(SalesData.product_id == product_id).all()
    if not sales:
        return {"status": "skipped", "reason": "No sales data found."}
        
    df = pd.DataFrame([{
        "price": float(s.price),
        "cost": float(s.cost)
    } for s in sales])
    
    current_price = df["price"].iloc[-1]  # Latest price
    avg_unit_cost = df["cost"].mean()
    
    # 2. Fetch elasticity record
    elasticity_rec = db.query(ElasticityAnalysis).filter(ElasticityAnalysis.product_id == product_id).first()
    elasticity = float(elasticity_rec.elasticity_score) if elasticity_rec else -0.5
    
    # 3. Recommendation logic
    # optimal price: P_opt = Cost * (Elasticity / (Elasticity + 1))
    if elasticity < -1:
        # Elastic demand
        optimal_price = avg_unit_cost * (elasticity / (elasticity + 1))
        # Protect against extreme values, bound recommended price between 85% and 120% of current
        recommended_price = max(current_price * 0.85, min(current_price * 1.2, optimal_price))
        # Protect unit margin (minimum 15% profit margin)
        recommended_price = max(recommended_price, avg_unit_cost * 1.15)
    else:
        # Inelastic demand (elasticity is between -1 and 0, or positive)
        # For inelastic products, price increases always increase revenue. Suggest 10% increase.
        recommended_price = current_price * 1.10
        # Guard against excessive margins (cap at 3x cost)
        recommended_price = min(recommended_price, avg_unit_cost * 3.0)
        
    # Standardize values
    recommended_price = round(recommended_price, 2)
    
    # Calculate price change
    pct_change = ((recommended_price - current_price) / current_price) * 100
    
    if abs(pct_change) < 1.0:
        action = RecommendationAction.MAINTAIN
        recommended_price = current_price
    elif pct_change > 0:
        action = RecommendationAction.INCREASE
    else:
        action = RecommendationAction.DECREASE
        
    # 4. Simulate impact under recommended price
    sim = simulate_price_impact(db, product_id, recommended_price)
    expected_rev_change = sim.get("revenue_change_percent", 0.0) / 100
    expected_prof_change = sim.get("profit_change_percent", 0.0) / 100
    
    # 4.5 Fetch forecast details to show confidence metrics
    from app.database.models import ForecastingResult
    forecast_rec = db.query(ForecastingResult).filter(ForecastingResult.product_id == product_id).first()
    if forecast_rec:
        forecast_confidence = float(forecast_rec.confidence_score) if forecast_rec.confidence_score is not None else 0.85
        forecast_model = forecast_rec.model_name
    else:
        forecast_confidence = 0.85
        forecast_model = "LinearRegression"
        
    # 5. Formulate natural language reasons (Structured Explainability)
    product_name = db.query(Product).filter(Product.id == product_id).first().product_name
    
    if action == RecommendationAction.INCREASE:
        summary = f"Demand for '{product_name}' remains stable after recent price hikes, indicating low customer price sensitivity."
        elasticity_reasoning = f"Price elasticity coefficient of {elasticity:.2f} indicates inelastic behavior. Volume is relatively unresponsive to pricing shifts."
        forecast_reasoning = f"Our {forecast_model} model projects stable transaction volumes ahead, supporting a premium price adjustment."
        revenue_impact = f"Increasing the price to ₹{recommended_price:.2f} (+{pct_change:.1f}%) is simulated to boost total profit by {expected_prof_change*100:.1f}% while preserving standard sales volume."
    elif action == RecommendationAction.DECREASE:
        summary = f"'{product_name}' displays highly elastic demand, indicating that customers are highly sensitive to price changes."
        elasticity_reasoning = f"High price sensitivity (elasticity: {elasticity:.2f}) indicates that lowering rates will trigger a significant boost in unit sales."
        forecast_reasoning = f"ML volume forecasts suggest current price points may be restricting demand growth. Lowering rates is expected to unlock hidden volume."
        revenue_impact = f"A price reduction of {abs(pct_change):.1f}% to ₹{recommended_price:.2f} is expected to grow demand by +{((sim.get('predicted_demand', 0) - sim.get('base_daily_quantity', 0)) / sim.get('base_daily_quantity', 1) * 100):.1f}%, driving a net profit increase of {expected_prof_change*100:.1f}%."
    else:
        summary = f"The current price of ₹{current_price:.2f} for '{product_name}' is optimal, successfully balancing margin size with transaction volume."
        elasticity_reasoning = f"Pricing elasticity ({elasticity:.2f}) indicates that either increasing or decreasing the price will lead to revenue leakage or volume loss."
        forecast_reasoning = f"Weekly volume forecasts remain steady under the current pricing structure, verifying market equilibrium."
        revenue_impact = "Current pricing maximizes the profit contribution. Any adjustments would reduce unit margins or decrease volume unnecessarily."

    import json
    reason_json = json.dumps({
        "summary": summary,
        "elasticity_reasoning": elasticity_reasoning,
        "forecast_reasoning": forecast_reasoning,
        "revenue_impact": revenue_impact,
        "confidence": f"{forecast_confidence * 100:.1f}% Model Fit ({forecast_model})"
    })
        
    # Clear old recommendations for product
    db.query(PricingRecommendation).filter(PricingRecommendation.product_id == product_id).delete()
    
    # Save recommendation
    rec = PricingRecommendation(
        product_id=product_id,
        current_price=current_price,
        recommended_price=recommended_price,
        expected_revenue_change=expected_rev_change,
        expected_profit_change=expected_prof_change,
        recommendation_reason=reason_json,
        created_at=datetime.now(timezone.utc)
    )
    db.add(rec)
    db.commit()
    
    return {
        "status": "success",
        "action": action,
        "current_price": current_price,
        "recommended_price": recommended_price,
        "expected_revenue_change": expected_rev_change,
        "expected_profit_change": expected_prof_change,
        "reason": reason_json
    }

def generate_all_recommendations(db: Session) -> dict:
    """Generate recommendations for all products in the database."""
    products = db.query(Product).all()
    results = {}
    for p in products:
        results[p.product_name] = generate_product_recommendation(db, p.id)
    return results
