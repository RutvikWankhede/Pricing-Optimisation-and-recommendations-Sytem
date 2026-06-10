import numpy as np
import pandas as pd
from datetime import datetime, timedelta, date
from sqlalchemy.orm import Session
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, root_mean_squared_error
from app.database.models import SalesData, ForecastingResult, Product

def train_and_forecast_product(db: Session, product_id: str) -> dict:
    """Train forecasting models for a product and save 30-day forecasts."""
    # 1. Fetch sales data
    sales = db.query(SalesData).filter(SalesData.product_id == product_id).all()
    if not sales:
        return {"status": "skipped", "reason": "No sales data found for product."}
        
    # 2. Prepare DataFrame
    data = []
    for s in sales:
        data.append({
            "date": s.sales_date,
            "price": float(s.price),
            "quantity": int(s.quantity_sold)
        })
        
    df = pd.DataFrame(data)
    # Group by date to aggregate daily demand
    df = df.groupby("date").agg({
        "quantity": "sum",
        "price": "mean"
    }).reset_index()
    
    df = df.sort_values(by="date")
    
    # Check if we have enough observations (need at least 7 days of sales)
    if len(df) < 7:
        # Fallback to simple average forecast
        return generate_fallback_forecast(db, product_id, df)
        
    # Convert date to datetime for extracting components
    df["datetime"] = pd.to_datetime(df["date"])
    df["weekday"] = df["datetime"].dt.weekday
    df["month"] = df["datetime"].dt.month
    df["day"] = df["datetime"].dt.day
    # Trend feature: days elapsed since start
    min_date = df["datetime"].min()
    df["trend_t"] = (df["datetime"] - min_date).dt.days
    
    # Define features and target
    X = df[["price", "weekday", "month", "day", "trend_t"]]
    y = df["quantity"]
    
    # 3. Train-test split (chronological, last 20%)
    split_idx = int(len(df) * 0.8)
    if split_idx < 5:
        # Not enough data for validation, fit on all data
        X_train, y_train = X, y
        X_test, y_test = X, y
    else:
        X_train, y_train = X.iloc[:split_idx], y.iloc[:split_idx]
        X_test, y_test = X.iloc[split_idx:], y.iloc[split_idx:]
        
    # 4. Train Linear Regression
    lr = LinearRegression()
    lr.fit(X_train, y_train)
    lr_pred = lr.predict(X_test)
    lr_pred = np.clip(lr_pred, 0, None)  # Clip negative predictions to 0
    lr_mae = mean_absolute_error(y_test, lr_pred)
    
    # 5. Train Random Forest
    rf = RandomForestRegressor(n_estimators=50, random_state=42)
    rf.fit(X_train, y_train)
    rf_pred = rf.predict(X_test)
    rf_pred = np.clip(rf_pred, 0, None)
    rf_mae = mean_absolute_error(y_test, rf_pred)
    
    # 6. Model selection (choose model with lowest MAE)
    if lr_mae <= rf_mae:
        best_model = lr
        model_name = "LinearRegression"
        best_mae = lr_mae
    else:
        best_model = rf
        model_name = "RandomForest"
        best_mae = rf_mae
        
    # Fit the best model on all data before forecasting
    best_model.fit(X, y)
    
    # Calculate simple confidence score (coefficient of determination R2 on full set)
    r2_score = float(best_model.score(X, y))
    # Bound R2 between 0 and 1
    confidence = max(0.0, min(1.0, r2_score))
    
    # 7. Generate 30-day forecast
    last_date = df["date"].max()
    last_price = float(df["price"].iloc[-1])
    # Calculate bias at the end of historical data for smooth transition
    last_actual = float(df["quantity"].iloc[-1])
    last_pred = float(best_model.predict(X.iloc[-1:])[0])
    bias = last_actual - last_pred

    forecasts_to_save = []
    
    # Clear old forecasts for this product
    db.query(ForecastingResult).filter(ForecastingResult.product_id == product_id).delete()
    
    for i in range(1, 31):
        f_date = last_date + timedelta(days=i)
        f_datetime = datetime.combine(f_date, datetime.min.time())
        
        f_weekday = f_datetime.weekday()
        f_month = f_datetime.month
        f_day = f_datetime.day
        f_trend = (f_datetime - min_date).days if isinstance(min_date, datetime) else (f_datetime - datetime.combine(min_date, datetime.min.time())).days
        
        # Predict
        features = pd.DataFrame([{
            "price": last_price,
            "weekday": f_weekday,
            "month": f_month,
            "day": f_day,
            "trend_t": f_trend
        }])
        
        pred_qty = best_model.predict(features)[0]
        # Apply decaying bias correction for smooth continuance curves
        adjusted_qty = float(pred_qty) + bias * np.exp(-i / 7.0)
        pred_qty = max(0.0, adjusted_qty)
        
        forecasts_to_save.append(
            ForecastingResult(
                product_id=product_id,
                predicted_demand=pred_qty,
                forecast_date=f_date,
                model_name=model_name,
                confidence_score=confidence
            )
        )
        
    db.bulk_save_objects(forecasts_to_save)
    db.commit()
    
    return {
        "status": "success",
        "model_name": model_name,
        "mae": float(best_mae),
        "confidence_score": confidence,
        "records_forecasted": 30
    }

def generate_fallback_forecast(db: Session, product_id: str, df: pd.DataFrame) -> dict:
    """Generate average daily demand fallback forecast when data is insufficient."""
    avg_demand = float(df["quantity"].mean()) if not df.empty else 1.0
    last_date = df["date"].max() if not df.empty else date.today()
    
    # Clear old forecasts for this product
    db.query(ForecastingResult).filter(ForecastingResult.product_id == product_id).delete()
    
    forecasts_to_save = []
    for i in range(1, 31):
        f_date = last_date + timedelta(days=i)
        forecasts_to_save.append(
            ForecastingResult(
                product_id=product_id,
                predicted_demand=avg_demand,
                forecast_date=f_date,
                model_name="AverageFallback",
                confidence_score=0.5
            )
        )
        
    db.bulk_save_objects(forecasts_to_save)
    db.commit()
    
    return {
        "status": "fallback",
        "model_name": "AverageFallback",
        "mae": 0.0,
        "confidence_score": 0.5,
        "records_forecasted": 30
    }

def train_and_forecast_all(db: Session) -> dict:
    """Retrain forecasting models for all products in the database."""
    products = db.query(Product).all()
    results = {}
    for p in products:
        results[p.product_name] = train_and_forecast_product(db, p.id)
    return results
