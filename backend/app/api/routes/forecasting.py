from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database.db import get_db
from app.database.models import ForecastingResult, Product, User
from app.database.schemas import ForecastResponse
from app.services.forecasting import train_and_forecast_product
from app.api.routes.auth import get_current_user

router = APIRouter(prefix="/forecast", tags=["Demand Forecasting"])

@router.get("/{product_id}", response_model=ForecastResponse)
def get_product_forecast(
    product_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retrieve 30-day demand forecasting results for a product."""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(
            status_code=404,
            detail="Product not found"
        )
        
    forecasts = db.query(ForecastingResult)\
                  .filter(ForecastingResult.product_id == product_id)\
                  .order_by(ForecastingResult.forecast_date)\
                  .all()
                  
    # If no forecasts exist, try training on-the-fly
    if not forecasts:
        train_and_forecast_product(db, product_id)
        forecasts = db.query(ForecastingResult)\
                      .filter(ForecastingResult.product_id == product_id)\
                      .order_by(ForecastingResult.forecast_date)\
                      .all()
                      
    forecast_list = [
        {
            "forecast_date": f.forecast_date,
            "predicted_demand": float(f.predicted_demand),
            "model_name": f.model_name,
            "confidence_score": float(f.confidence_score) if f.confidence_score else None
        }
        for f in forecasts
    ]
    
    return {
        "product_id": product_id,
        "product_name": product.product_name,
        "forecast": forecast_list
    }

@router.post("/train/{product_id}")
def retrain_forecast(
    product_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Manually trigger ML model retraining and forecast generation for a product."""
    result = train_and_forecast_product(db, product_id)
    if result.get("status") == "skipped":
        raise HTTPException(
            status_code=400,
            detail=result.get("reason", "Could not train model.")
        )
    return result
