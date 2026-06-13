"""
Generates a highly realistic synthetic food delivery sales dataset and re-seeds pricing_ai.db.
Incorporates weekend spikes, seasonal variations, promo discounts, category-specific elasticity, and demand noise.
"""
import sys
import os
import random
import uuid
import glob
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

sys.path.insert(0, 'backend')

# Ensure tables exist
from app.database.db import Base, engine, SessionLocal
Base.metadata.create_all(bind=engine)
try:
    from sqlalchemy import text
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE datasets ADD COLUMN summary_metadata TEXT"))
except Exception:
    pass

from app.database.models import (
    User, SalesData, Product, Dataset, ForecastingResult,
    ElasticityAnalysis, PricingRecommendation, ScenarioSimulation, Report
)
from app.core.security import hash_password
from app.services.data_cleaning import process_uploaded_file
from app.services.elasticity import calculate_all_elasticities
from app.services.forecasting import train_and_forecast_all
from app.services.recommendation import generate_all_recommendations

def generate_realistic_dataset():
    print("Generating highly realistic synthetic food delivery dataset...")
    np.random.seed(42)
    random.seed(42)

    # Config for food categories
    category_configs = {
        "Pizza": {
            "base_price": 399.0,
            "cost": 140.0,
            "elasticity": -1.9,
            "base_qty": 60,
            "weekend_factor": 1.65,  # strong weekend spike
            "restaurants": ["Pizza Point", "Taco Fiesta", "Burger Hub"]
        },
        "Sushi": {
            "base_price": 799.0,
            "cost": 360.0,
            "elasticity": -0.5,      # inelastic, premium
            "base_qty": 20,
            "weekend_factor": 1.10,  # stable premium demand
            "restaurants": ["Sushi Zen", "Royal Thali", "Pasta Palace"]
        },
        "Burger": {
            "base_price": 179.0,
            "cost": 55.0,
            "elasticity": -2.4,      # highly elastic
            "base_qty": 85,
            "weekend_factor": 1.45,
            "restaurants": ["Burger Hub", "Spice Villa", "Healthy Bowl"]
        },
        "Drinks": {
            "base_price": 99.0,
            "cost": 25.0,
            "elasticity": -1.2,
            "base_qty": 90,
            "weekend_factor": 1.30,
            "seasonal_summer_boost": 1.55, # highly seasonal
            "seasonal_winter_dip": 0.55,
            "restaurants": ["Pizza Point", "Burger Hub", "Street Chow", "Pasta Palace"]
        },
        "Biryani": {
            "base_price": 329.0,
            "cost": 110.0,
            "elasticity": -1.4,
            "base_qty": 70,
            "weekend_factor": 1.35,
            "rainy_boost": 1.25,      # spikes during rainy days
            "restaurants": ["Urban Biryani", "Spice Villa", "Royal Thali"]
        },
        "Pasta": {
            "base_price": 289.0,
            "cost": 95.0,
            "elasticity": -1.3,
            "base_qty": 45,
            "weekend_factor": 1.30,
            "restaurants": ["Pasta Palace", "Healthy Bowl", "Street Chow"]
        },
        "Salad": {
            "base_price": 249.0,
            "cost": 70.0,
            "elasticity": -1.1,
            "base_qty": 40,
            "weekend_factor": 0.95,  # lower on weekends
            "restaurants": ["Healthy Bowl", "Spice Villa", "Sushi Zen"]
        },
        "Mexican": {
            "base_price": 229.0,
            "cost": 70.0,
            "elasticity": -1.5,
            "base_qty": 50,
            "weekend_factor": 1.25,
            "restaurants": ["Taco Fiesta", "Burger Hub", "Pasta Palace"]
        },
        "Chinese": {
            "base_price": 219.0,
            "cost": 65.0,
            "elasticity": -1.6,
            "base_qty": 65,
            "weekend_factor": 1.30,
            "restaurants": ["Street Chow", "Royal Thali", "Healthy Bowl"]
        },
        "North Indian": {
            "base_price": 279.0,
            "cost": 90.0,
            "elasticity": -1.2,
            "base_qty": 80,
            "weekend_factor": 1.20,
            "restaurants": ["Royal Thali", "Spice Villa", "Urban Biryani"]
        }
    }

    cities = ["Chennai", "Bangalore", "Mumbai", "Delhi", "Hyderabad", "Pune"]
    weathers = ["Sunny", "Cloudy", "Rainy", "Stormy"]
    weather_probs = [0.60, 0.20, 0.15, 0.05]

    # Generate daily data for 180 days leading to today
    end_date = datetime.now()
    start_date = end_date - timedelta(days=180)

    records = []
    current_date = start_date

    order_counter = 1

    while current_date <= end_date:
        weekday = current_date.weekday()
        is_weekend = 1 if weekday in [5, 6] else 0
        month = current_date.month

        # Define monthly general factor (peaks in summer May/June & winter Nov/Dec)
        month_factor = 1.20 if month in [5, 6, 11, 12] else 0.90
        
        # Festival flags on a few dates
        is_festival = 0
        if (month == 10 and current_date.day in [20, 24]) or \
           (month == 11 and current_date.day in [10, 11, 12]) or \
           (month == 12 and current_date.day in [24, 25, 31]) or \
           (month == 10 and current_date.day == 31):
            is_festival = 1

        # We will loop through categories to generate some rows per day
        for category, config in category_configs.items():
            # Pick a subset of restaurants and cities to generate transactions
            active_restaurants = config["restaurants"]
            for restaurant in active_restaurants:
                for city in random.sample(cities, k=random.randint(1, 3)):
                    # Determine Weather
                    weather = np.random.choice(weathers, p=weather_probs)
                    
                    # Base factors
                    weekend_mult = config["weekend_factor"] if is_weekend else 0.85
                    
                    # Category specific seasonal adjustments
                    seasonal_mult = 1.0
                    if category == "Drinks":
                        if month in [5, 6, 7]:
                            seasonal_mult = config["seasonal_summer_boost"]
                        elif month in [11, 12, 1]:
                            seasonal_mult = config["seasonal_winter_dip"]
                    
                    # Weather impact
                    weather_mult = 1.0
                    if weather in ["Rainy", "Stormy"]:
                        if category == "Biryani":
                            weather_mult = config.get("rainy_boost", 1.25)
                        elif category == "Salad":
                            weather_mult = 0.70  # Cold foods drop during rain
                        else:
                            weather_mult = 0.85  # general reduction

                    # Promo / Discount (5% chance of promo day)
                    is_promo = random.random() < 0.05
                    discount_pct = random.choice([15, 20, 25, 30]) if is_promo else 0
                    if not is_promo and random.random() < 0.15:
                        discount_pct = 5 # small default discounts

                    # Price adjustments
                    base_price = config["base_price"]
                    # Add small variance to list price per city/restaurant
                    price_var = (random.randint(-2, 2) * 10.0)
                    price = max(config["cost"] + 10.0, base_price + price_var)
                    
                    # Effective price after discount
                    effective_price = price * (1.0 - (discount_pct / 100.0))

                    # Demand calculation via Elasticity
                    price_ratio = effective_price / base_price
                    expected_qty = config["base_qty"] * (price_ratio ** config["elasticity"])
                    
                    # Apply multipliers
                    expected_qty *= weekend_mult * month_factor * seasonal_mult * weather_mult
                    if is_festival:
                        expected_qty *= 1.35
                    
                    # Long term growth trend (+0.08% per day)
                    days_elapsed = (current_date - start_date).days
                    expected_qty *= (1.0 + 0.0008 * days_elapsed)

                    # Add noise
                    noise = np.random.normal(1.0, 0.12)
                    orders = max(5, int(round(expected_qty * noise)))

                    # Revenue, Cost, Profit
                    revenue = orders * effective_price
                    total_cost = orders * config["cost"]
                    profit = revenue - total_cost
                    profit_margin_pct = (profit / revenue * 100) if revenue > 0 else 0.0

                    # Delivery time
                    delivery_time = random.randint(15, 35)
                    if weather == "Stormy":
                        delivery_time += random.randint(15, 30)
                    elif weather == "Rainy":
                        delivery_time += random.randint(5, 15)

                    # Competitor Price
                    competitor_price = price * np.random.normal(1.0, 0.04)

                    records.append({
                        "order_id": f"ORD{order_counter:05d}",
                        "date": current_date.strftime("%Y-%m-%d"),
                        "restaurant": restaurant,
                        "food_category": category,
                        "city": city,
                        "weather": weather,
                        "festival_flag": is_festival,
                        "weekend": is_weekend,
                        "price": round(price, 2),
                        "discount_percent": discount_pct,
                        "competitor_price": round(competitor_price, 2),
                        "orders": orders,
                        "delivery_time_minutes": delivery_time,
                        "revenue": round(revenue, 2),
                        "profit_margin_percent": round(profit_margin_pct, 2),
                        "customer_rating": round(random.uniform(3.2, 5.0), 1)
                    })
                    order_counter += 1

        current_date += timedelta(days=1)

    df = pd.DataFrame(records)
    
    # Save CSV
    output_dir = "datasets/raw"
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "pricesense_clean_dataset.csv")
    df.to_csv(output_path, index=False)
    print(f"Generated realistic dataset with {len(df)} rows at: {output_path}")
    return output_path

def seed_database(csv_path):
    print("Re-seeding SQLite database...")
    db = SessionLocal()
    try:
        # 1. Wipe all existing analytics tables
        print("[1/7] Purging old database records...")
        db.query(Report).delete()
        db.query(ScenarioSimulation).delete()
        db.query(PricingRecommendation).delete()
        db.query(ElasticityAnalysis).delete()
        db.query(ForecastingResult).delete()
        db.query(SalesData).delete()
        db.query(Product).delete()
        db.query(Dataset).delete()
        db.commit()

        # 2. Ensure default user
        print("[2/7] Ensuring default analyst user exists...")
        user = db.query(User).filter(User.email == "analyst@pricing.ai").first()
        if not user:
            user = User(
                full_name="Pricing Analyst",
                email="analyst@pricing.ai",
                password_hash=hash_password("password123"),
                role="analyst"
            )
            db.add(user)
            db.commit()
            db.refresh(user)

        # 3. Load generated CSV file contents
        print(f"[3/7] Ingesting sales data from: {csv_path}")
        with open(csv_path, "rb") as f:
            content = f.read()

        dataset_id = str(uuid.uuid4())
        dataset = Dataset(
            id=dataset_id,
            file_name=os.path.basename(csv_path),
            user_id=user.id,
            total_records=0,
            status="processing"
        )
        db.add(dataset)
        db.commit()

        # 4. Clean and insert sales data
        print("[4/7] Ingesting and mapping records...")
        result = process_uploaded_file(db, content, os.path.basename(csv_path), dataset_id, mappings=None)
        print(f"  -> {result['total_records']} rows inserted successfully")
        print(f"  -> {result.get('summary', {}).get('detected_categories', '?')} categories detected")

        # 5. Calculate elasticities
        print("[5/7] Analyzing price elasticities of demand (PED)...")
        calculate_all_elasticities(db)

        # 6. Forecasting
        print("[6/7] Training forecast engine (Linear & Random Forest models)...")
        train_and_forecast_all(db)

        # 7. Recommendations
        print("[7/7] Pre-compiling price recommendations list...")
        generate_all_recommendations(db)

        # Mark complete
        dataset_record = db.query(Dataset).filter(Dataset.id == dataset_id).first()
        if dataset_record:
            dataset_record.status = "processed"
            db.commit()

        print("\n=== DATA BASE SEED VERIFICATION ===")
        products = db.query(Product).all()
        print(f"Active Products: {len(products)}")
        cat_counts = {}
        for p in products:
            cat_counts[p.category] = cat_counts.get(p.category, 0) + 1
        print(f"Categories Distribution: {cat_counts}")
        print(f"Sales Data rows: {db.query(SalesData).count()}")
        print(f"Elasticity Profiles: {db.query(ElasticityAnalysis).count()}")
        print(f"Forecasting results: {db.query(ForecastingResult).count()}")
        print(f"Price recommendations: {db.query(PricingRecommendation).count()}")

        print("\nDone! Database re-seeded with premium realistic dataset.")
    except Exception as e:
        print(f"Critical error during seeding: {str(e)}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    csv_path = generate_realistic_dataset()
    seed_database(csv_path)
