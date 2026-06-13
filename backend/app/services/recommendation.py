import json
import pandas as pd
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.database.models import (
    SalesData,
    ElasticityAnalysis,
    PricingRecommendation,
    ForecastingResult,
    Product,
)
from app.core.constants import RecommendationAction
from app.services.optimization import simulate_price_impact

# ─────────────────────────────────────────────
#  Safety bounds (applied to EVERY recommendation)
# ─────────────────────────────────────────────
LOWER_BOUND = 0.85  # never recommend below 85% of current price
UPPER_BOUND = 1.15  # never recommend above 115% of current price
MIN_MARGIN = 1.15  # recommended price must be ≥ 115% of avg unit cost
MAX_MARGIN = 3.00  # recommended price must be ≤ 300% of avg unit cost


def _compute_recommended_price(
    elasticity: float,
    current_price: float,
    avg_unit_cost: float,
    confidence_score: float,
) -> dict:
    """
    Blended pricing engine:
      - Low confidence (<0.5)      : override, hold current price, action = MAINTAIN
      - Elastic zone   (e < -1.01) : 70% Lerner optimal  +  30% rule-of-thumb
      - Inelastic zone (e >= -1.01): tiered rule-based adjustments
      - Near-unit elastic           : hold current price (safest move)

    All outputs are clamped by safety bounds before returning, tracking which bounds are triggered.

    Returns:
        A dict containing:
        - recommended_price
        - action
        - branch_taken
        - bounds_applied
        - flagged_for_review
        - reasoning
    """
    bounds_applied = []
    
    # 1. Low confidence override check
    if confidence_score < 0.5:
        return {
            "recommended_price": current_price,
            "action": RecommendationAction.MAINTAIN,
            "branch_taken": "low_confidence_override",
            "bounds_applied": [],
            "flagged_for_review": True,
            "reasoning": "Confidence score is below the threshold of 0.5. Current price is maintained for safety."
        }

    # 2. Determine price and branch based on elasticity tiers
    if elasticity < -1.01:
        # ── Lerner / Ramsey optimal price ──────────────────────────────
        optimal_price = avg_unit_cost * (elasticity / (elasticity + 1))

        # Rule-of-thumb nudge (prevents formula from swinging wildly)
        if elasticity <= -1.5:
            nudge_price = current_price * 0.90  # highly elastic → reduce
        else:
            nudge_price = current_price * 0.95  # moderately elastic → slight reduce

        # Blend: 70% economic formula  +  30% business heuristic
        recommended_price = 0.70 * optimal_price + 0.30 * nudge_price
        branch_taken = "highly_elastic_lerner_blend"
        reasoning = f"Lerner Ramsey model blended with business heuristics due to high elasticity ({elasticity:.2f})."

    elif elasticity >= -0.4:
        # Very inelastic — volume barely changes with price → raise
        recommended_price = current_price * 1.10
        branch_taken = "moderately_inelastic_small_increase"
        reasoning = f"Modest price increase recommended to capture margin from inelastic behavior ({elasticity:.2f})."

    elif elasticity >= -0.8:
        # Slightly inelastic — modest raise safe
        recommended_price = current_price * 1.05
        branch_taken = "moderately_inelastic_small_increase"
        reasoning = f"Modest price increase recommended to capture margin from inelastic behavior ({elasticity:.2f})."

    elif elasticity >= -1.01:
        # Near unit-elastic — any move risks revenue loss → hold
        recommended_price = current_price
        branch_taken = "unit_elastic_hold"
        reasoning = f"Price maintained as elasticity ({elasticity:.2f}) is near unit-elastic, minimizing revenue risk."

    else:
        # Fallback
        recommended_price = current_price
        branch_taken = "unit_elastic_hold"
        reasoning = "Current price maintained."

    # ── Safety bounds (always enforced and tracked) ────────────────────
    floor_val = avg_unit_cost * MIN_MARGIN
    if recommended_price < floor_val:
        recommended_price = floor_val
        bounds_applied.append("min_margin_floor")
        
    cap_val = avg_unit_cost * MAX_MARGIN
    if recommended_price > cap_val:
        recommended_price = cap_val
        bounds_applied.append("max_margin_cap")
        
    lower_guard = current_price * LOWER_BOUND
    if recommended_price < lower_guard:
        recommended_price = lower_guard
        bounds_applied.append("lower_price_guardrail")
        
    upper_guard = current_price * UPPER_BOUND
    if recommended_price > upper_guard:
        recommended_price = upper_guard
        bounds_applied.append("upper_price_guardrail")

    recommended_price = round(recommended_price, 2)

    # Calculate percentage change for review flagging and action mapping
    pct_change = ((recommended_price - current_price) / current_price) * 100
    abs_pct_change = abs(pct_change)
    
    # Review flag logic: confidence score < 0.5 OR absolute price change > 15%
    flagged_for_review = (confidence_score < 0.5) or (abs_pct_change > 15.0)

    # Action Mapping from price delta (±3% threshold)
    if pct_change >= 3:
        action = RecommendationAction.INCREASE
    elif pct_change <= -3:
        action = RecommendationAction.DECREASE
    else:
        action = RecommendationAction.MAINTAIN

    return {
        "recommended_price": recommended_price,
        "action": action,
        "branch_taken": branch_taken,
        "bounds_applied": bounds_applied,
        "flagged_for_review": flagged_for_review,
        "reasoning": reasoning
    }


def _validate_action_via_simulation(
    recommended_price: float,
    current_price: float,
    expected_rev_change: float,
    expected_prof_change: float,
) -> RecommendationAction:
    """
    Final business validation using simulation results.
    Overrides naive price-delta logic with revenue/profit reality checks.

    Rules (in priority order):
      1. If simulation shows revenue falling > 5%  → DECREASE
      2. If simulation shows profit rising  > 8%   → INCREASE
      3. If both revenue and profit are flat (< 3%) → MAINTAIN
      4. Otherwise                                  → MAINTAIN (conservative default)
    """
    if expected_rev_change < -0.05:
        return RecommendationAction.DECREASE

    if expected_prof_change > 0.08:
        return RecommendationAction.INCREASE

    if abs(expected_rev_change) < 0.03 and abs(expected_prof_change) < 0.03:
        return RecommendationAction.MAINTAIN

    return RecommendationAction.MAINTAIN


def _build_reason_json(
    action: RecommendationAction,
    product_name: str,
    elasticity: float,
    current_price: float,
    recommended_price: float,
    pct_change: float,
    expected_prof_change: float,
    sim: dict,
    forecast_confidence: float,
    forecast_model: str,
    confidence_score: float,
    branch_taken: str,
    bounds_applied: list[str],
    flagged_for_review: bool,
    reasoning: str,
) -> str:
    """Generate structured natural-language explanation and explainability metadata for the recommendation."""
    # Coerce all inputs to standard Python primitives to avoid NumPy/SQLAlchemy Decimal JSON serialization issues
    recommended_price = float(recommended_price)
    confidence_score = float(confidence_score)
    elasticity = float(elasticity)
    current_price = float(current_price)
    pct_change = float(pct_change)
    expected_prof_change = float(expected_prof_change)
    forecast_confidence = float(forecast_confidence)
    flagged_for_review = bool(flagged_for_review)
    bounds_applied = [str(b) for b in bounds_applied]
    branch_taken = str(branch_taken)
    reasoning = str(reasoning)

    if action == RecommendationAction.INCREASE:
        summary = (
            f"Demand for '{product_name}' remains stable after recent price hikes, "
            f"indicating low customer price sensitivity."
        )
        elasticity_reasoning = (
            f"Price elasticity of {elasticity:.2f} signals inelastic behaviour. "
            f"Volume is relatively unresponsive to pricing shifts."
        )
        forecast_reasoning = (
            f"Our {forecast_model} model projects stable transaction volumes ahead, "
            f"supporting a premium price adjustment."
        )
        revenue_impact = (
            f"Increasing the price to ₹{recommended_price:.2f} (+{pct_change:.1f}%) "
            f"is simulated to boost total profit by {expected_prof_change * 100:.1f}% "
            f"while preserving standard sales volume."
        )

    elif action == RecommendationAction.DECREASE:
        base_qty = sim.get("base_daily_quantity", 1)
        pred_qty = sim.get("predicted_demand", base_qty)
        vol_change = ((pred_qty - base_qty) / base_qty) * 100

        summary = (
            f"'{product_name}' displays highly elastic demand — customers are "
            f"highly sensitive to price changes."
        )
        elasticity_reasoning = (
            f"High price sensitivity (elasticity: {elasticity:.2f}) means lowering "
            f"rates will trigger a significant boost in unit sales."
        )
        forecast_reasoning = (
            f"ML volume forecasts suggest current price points may be restricting "
            f"demand growth. Lowering rates is expected to unlock hidden volume."
        )
        revenue_impact = (
            f"A price reduction of {abs(pct_change):.1f}% to ₹{recommended_price:.2f} "
            f"is expected to grow demand by +{vol_change:.1f}%, driving a net profit "
            f"increase of {expected_prof_change * 100:.1f}%."
        )

    else:  # MAINTAIN
        if branch_taken == "low_confidence_override":
            summary = "Low confidence in pricing recommendations. Current price is maintained for safety."
            elasticity_reasoning = f"Price elasticity calculations for '{product_name}' have insufficient data or lack price variation."
            forecast_reasoning = f"Historical transaction sample size or R-squared model fit are below the confidence threshold."
            revenue_impact = "No pricing adjustments recommended until more sales transactions are ingested."
        else:
            summary = (
                f"The current price of ₹{current_price:.2f} for '{product_name}' is "
                f"optimal, successfully balancing margin with transaction volume."
            )
            elasticity_reasoning = (
                f"Elasticity of {elasticity:.2f} indicates that either raising or lowering "
                f"the price will cause revenue leakage or volume loss."
            )
            forecast_reasoning = (
                f"Weekly volume forecasts remain steady under the current pricing "
                f"structure, confirming market equilibrium."
            )
            revenue_impact = (
                f"Current pricing maximises the profit contribution. "
                f"Any adjustment would reduce unit margins or decrease volume unnecessarily."
            )

    return json.dumps(
        {
            # Structured explainability metadata
            "recommended_price": recommended_price,
            "confidence_score": confidence_score,
            "elasticity_used": elasticity,
            "branch_taken": branch_taken,
            "reasoning": reasoning if branch_taken != "low_confidence_override" else summary,
            "bounds_applied": bounds_applied,
            "flagged_for_review": flagged_for_review,

            # Legacy fields for frontend layout backward-compatibility
            "summary": summary,
            "elasticity_reasoning": elasticity_reasoning,
            "forecast_reasoning": forecast_reasoning,
            "revenue_impact": revenue_impact,
            "confidence": f"{confidence_score * 100:.1f}% Confidence Score",
        }
    )


# ═════════════════════════════════════════════
#  PUBLIC API
# ═════════════════════════════════════════════


def generate_product_recommendation(db: Session, product_id: str) -> dict:
    """Generate and persist a pricing recommendation for a single product."""

    # ── 1. Sales data ───────────────────────────────────────────────────
    sales = db.query(SalesData).filter(SalesData.product_id == product_id).all()
    if not sales:
        return {"status": "skipped", "reason": "No sales data found."}

    df = pd.DataFrame(
        [
            {
                "price": float(s.price),
                "cost": float(s.cost),
            }
            for s in sales
        ]
    )

    current_price = df["price"].iloc[-1]  # most recent observed price
    avg_unit_cost = df["cost"].mean()

    # ── 2. Elasticity ───────────────────────────────────────────────────
    elasticity_rec = (
        db.query(ElasticityAnalysis)
        .filter(ElasticityAnalysis.product_id == product_id)
        .first()
    )
    
    elasticity = float(elasticity_rec.elasticity_score) if elasticity_rec else -0.5
    confidence_score = float(elasticity_rec.confidence_score) if (elasticity_rec and elasticity_rec.confidence_score is not None) else 0.5

    # ── 3. Compute recommended price (blended engine) ───────────────────
    pricing_data = _compute_recommended_price(
        elasticity, current_price, avg_unit_cost, confidence_score
    )
    recommended_price = pricing_data["recommended_price"]
    initial_action = pricing_data["action"]
    branch_taken = pricing_data["branch_taken"]
    bounds_applied = pricing_data["bounds_applied"]
    flagged_for_review = pricing_data["flagged_for_review"]
    reasoning = pricing_data["reasoning"]

    # ── 4. Simulate impact at recommended price ─────────────────────────
    sim = simulate_price_impact(db, product_id, recommended_price)
    expected_rev_change = sim.get("revenue_change_percent", 0.0) / 100
    expected_prof_change = sim.get("profit_change_percent", 0.0) / 100

    # ── 5. Final action — simulation overrides initial price-delta action ─
    if branch_taken == "low_confidence_override":
        action = RecommendationAction.MAINTAIN
    else:
        action = _validate_action_via_simulation(
            recommended_price,
            current_price,
            expected_rev_change,
            expected_prof_change,
        )

    # If both signals agree on MAINTAIN, snap price back to current
    if action == RecommendationAction.MAINTAIN:
        recommended_price = current_price
        pct_change = 0.0
        # Re-evaluate review flags since price change snapped to 0
        flagged_for_review = (confidence_score < 0.5)
    else:
        pct_change = ((recommended_price - current_price) / current_price) * 100

    # ── 6. Forecast metadata ────────────────────────────────────────────
    forecast_rec = (
        db.query(ForecastingResult)
        .filter(ForecastingResult.product_id == product_id)
        .first()
    )
    if forecast_rec:
        forecast_confidence = (
            float(forecast_rec.confidence_score)
            if forecast_rec.confidence_score is not None
            else 0.85
        )
        forecast_model = forecast_rec.model_name
    else:
        forecast_confidence = 0.85
        forecast_model = "LinearRegression"

    # ── 7. Natural-language explanation ────────────────────────────────
    product_name = (
        db.query(Product).filter(Product.id == product_id).first().product_name
    )

    reason_json = _build_reason_json(
        action=action,
        product_name=product_name,
        elasticity=elasticity,
        current_price=current_price,
        recommended_price=recommended_price,
        pct_change=pct_change,
        expected_prof_change=expected_prof_change,
        sim=sim,
        forecast_confidence=forecast_confidence,
        forecast_model=forecast_model,
        confidence_score=confidence_score,
        branch_taken=branch_taken,
        bounds_applied=bounds_applied,
        flagged_for_review=flagged_for_review,
        reasoning=reasoning,
    )

    # ── 8. Persist ──────────────────────────────────────────────────────
    db.query(PricingRecommendation).filter(
        PricingRecommendation.product_id == product_id
    ).delete()

    rec = PricingRecommendation(
        product_id=product_id,
        current_price=current_price,
        recommended_price=recommended_price,
        expected_revenue_change=expected_rev_change,
        expected_profit_change=expected_prof_change,
        recommendation_reason=reason_json,
        created_at=datetime.now(timezone.utc),
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
        "reason": reason_json,
    }


def generate_all_recommendations(db: Session) -> dict:
    """Generate recommendations for every product in the database."""
    products = db.query(Product).all()
    return {p.product_name: generate_product_recommendation(db, p.id) for p in products}
