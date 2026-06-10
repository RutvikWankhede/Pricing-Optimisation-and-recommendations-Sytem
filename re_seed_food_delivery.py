"""
Re-seeds pricing_ai.db using the food delivery dataset through the fixed ingestion pipeline.
Run from the project root: .venv\Scripts\python re_seed_food_delivery.py
"""
import sys, os
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
import uuid

db = SessionLocal()

# 1. Wipe all existing analytics
print("[1/7] Purging old data...")
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
print("[2/7] Ensuring default analyst user...")
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

# 3. Load food delivery CSV
csv_path = "datasets/raw/5446406a-3948-4cef-b6f6-7ccc3c1895a9_food_delivery_pricing_dataset.csv"
if not os.path.exists(csv_path):
    # fallback to any food delivery file
    import glob
    found = glob.glob("datasets/raw/*food_delivery*.csv")
    if found:
        csv_path = found[0]
    else:
        print("ERROR: No food delivery dataset found in datasets/raw/")
        sys.exit(1)

print(f"[3/7] Ingesting: {csv_path}")
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

# 4. Process file
print("[4/7] Cleaning and inserting sales data...")
result = process_uploaded_file(db, content, os.path.basename(csv_path), dataset_id, mappings=None)
print(f"  -> {result['total_records']} rows processed")
print(f"  -> {result.get('summary', {}).get('detected_categories', '?')} categories detected")
print(f"  -> {result.get('summary', {}).get('detected_products', '?')} products detected")

# 5. Calculate elasticities
print("[5/7] Calculating elasticities...")
calculate_all_elasticities(db)

# 6. Forecast
print("[6/7] Training forecast models...")
train_and_forecast_all(db)

# 7. Recommendations
print("[7/7] Generating pricing recommendations...")
generate_all_recommendations(db)

# Mark complete
dataset_record = db.query(Dataset).filter(Dataset.id == dataset_id).first()
if dataset_record:
    dataset_record.status = "processed"
    db.commit()

# Verification
print("\n=== VERIFICATION ===")
products = db.query(Product).all()
print(f"Products: {len(products)}")
cat_counts = {}
for p in products:
    cat_counts[p.category] = cat_counts.get(p.category, 0) + 1
print(f"Categories: {cat_counts}")
reg_counts = {}
for p in products:
    reg_counts[p.region] = reg_counts.get(p.region, 0) + 1
print(f"Regions: {reg_counts}")
print(f"SalesData rows: {db.query(SalesData).count()}")
print(f"Elasticity analyses: {db.query(ElasticityAnalysis).count()}")
print(f"Forecast results: {db.query(ForecastingResult).count()}")
print(f"Recommendations: {db.query(PricingRecommendation).count()}")

db.close()
print("\nDone! Database re-seeded with food delivery dataset.")
