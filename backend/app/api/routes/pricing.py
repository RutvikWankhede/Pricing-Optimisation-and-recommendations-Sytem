from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database.db import get_db
from app.database.models import Product, ElasticityAnalysis, PricingRecommendation, User, SalesData
from app.database.schemas import ElasticityResponse, RecommendationResponse, SimulationRequest, SimulationResponse, ProductResponse
from app.services.optimization import simulate_price_impact
from app.services.elasticity import calculate_product_elasticity
from app.services.recommendation import generate_product_recommendation
from app.api.routes.auth import get_current_user

router = APIRouter(prefix="/pricing", tags=["Pricing & Revenue Engine"])

@router.get("/products", response_model=list[ProductResponse])
def get_products(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retrieve list of all active products for analysis."""
    return db.query(Product).order_by(Product.product_name).all()

@router.get("/elasticity/{product_id}", response_model=ElasticityResponse)
def get_elasticity(
    product_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Fetch elasticity details for a specific product."""
    el = db.query(ElasticityAnalysis).filter(ElasticityAnalysis.product_id == product_id).first()
    if not el:
        # Try calculating on the fly
        calculate_product_elasticity(db, product_id)
        el = db.query(ElasticityAnalysis).filter(ElasticityAnalysis.product_id == product_id).first()
        
    if not el:
        raise HTTPException(status_code=404, detail="Elasticity analysis not available for this product.")
        
    return {
        "product_id": el.product_id,
        "product_name": el.product.product_name,
        "elasticity_score": float(el.elasticity_score),
        "elasticity_type": el.elasticity_type,
        "sample_size": el.sample_size,
        "r_squared": float(el.r_squared) if el.r_squared is not None else None,
        "confidence_score": float(el.confidence_score) if el.confidence_score is not None else None,
        "analysis_date": el.analysis_date
    }

@router.get("/elasticity", response_model=list[ElasticityResponse])
def get_all_elasticity(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Fetch price elasticity details for all products."""
    all_el = db.query(ElasticityAnalysis).all()
    return [
        {
            "product_id": el.product_id,
            "product_name": el.product.product_name,
            "elasticity_score": float(el.elasticity_score),
            "elasticity_type": el.elasticity_type,
            "sample_size": el.sample_size,
            "r_squared": float(el.r_squared) if el.r_squared is not None else None,
            "confidence_score": float(el.confidence_score) if el.confidence_score is not None else None,
            "analysis_date": el.analysis_date
        }
        for el in all_el
    ]

@router.get("/recommendations/{product_id}", response_model=RecommendationResponse)
def get_recommendation(
    product_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Fetch AI pricing recommendation for a specific product."""
    rec = db.query(PricingRecommendation).filter(PricingRecommendation.product_id == product_id).first()
    if not rec:
        # Try generating on the fly
        generate_product_recommendation(db, product_id)
        rec = db.query(PricingRecommendation).filter(PricingRecommendation.product_id == product_id).first()
        
    if not rec:
        raise HTTPException(status_code=404, detail="Pricing recommendation not available.")
        
    return {
        "product_id": rec.product_id,
        "product_name": rec.product.product_name,
        "current_price": float(rec.current_price),
        "recommended_price": float(rec.recommended_price),
        "expected_revenue_change": float(rec.expected_revenue_change) if rec.expected_revenue_change else 0.0,
        "expected_profit_change": float(rec.expected_profit_change) if rec.expected_profit_change else 0.0,
        "recommendation_reason": rec.recommendation_reason,
        "created_at": rec.created_at
    }

@router.get("/recommendations", response_model=list[RecommendationResponse])
def get_all_recommendations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Fetch all price optimization recommendations."""
    all_recs = db.query(PricingRecommendation).all()
    return [
        {
            "product_id": rec.product_id,
            "product_name": rec.product.product_name,
            "current_price": float(rec.current_price),
            "recommended_price": float(rec.recommended_price),
            "expected_revenue_change": float(rec.expected_revenue_change) if rec.expected_revenue_change else 0.0,
            "expected_profit_change": float(rec.expected_profit_change) if rec.expected_profit_change else 0.0,
            "recommendation_reason": rec.recommendation_reason,
            "created_at": rec.created_at
        }
        for rec in all_recs
    ]

@router.post("/simulate", response_model=SimulationResponse)
def simulate_price(
    req: SimulationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Run a scenario simulation for a hypothetical pricing offset."""
    result = simulate_price_impact(db, req.product_id, req.simulated_price)
    if not result:
        raise HTTPException(status_code=400, detail="Cannot run simulation for this product.")
    return result

@router.get("/sales/{product_id}", response_model=list[dict])
def get_product_sales_history(
    product_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Fetch raw sales history for a specific product."""
    sales = db.query(SalesData).filter(SalesData.product_id == product_id).order_by(SalesData.sales_date).all()
    return [
        {
            "sales_date": str(s.sales_date),
            "price": float(s.price),
            "quantity_sold": int(s.quantity_sold),
            "revenue": float(s.revenue),
            "profit": float(s.profit),
            "cost": float(s.cost)
        }
        for s in sales
    ]
