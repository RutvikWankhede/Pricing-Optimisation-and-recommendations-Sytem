import os
import sys
from pathlib import Path

# Add backend to python path so we can import app
project_root = Path(__file__).resolve().parent
backend_path = project_root / "backend"
sys.path.append(str(backend_path))

# Load environment variables
from dotenv import load_dotenv
load_dotenv(dotenv_path=project_root / ".env")

from app.database.db import engine, Base, SessionLocal
from app.database.models import User, Dataset, SalesData
from app.core.security import hash_password
from app.services.data_cleaning import process_uploaded_file
from app.services.elasticity import calculate_all_elasticities
from app.services.forecasting import train_and_forecast_all
from app.services.recommendation import generate_all_recommendations

def initialize_and_seed():
    print("Resetting database (dropping and recreating tables)...")
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    
    # Purge old raw/processed uploaded dataset files
    from app.core.config import settings
    print("Purging old uploaded files from disk...")
    for folder in [settings.UPLOAD_FOLDER, settings.PROCESSED_FOLDER]:
        if folder.exists():
            for file_path in folder.iterdir():
                if file_path.is_file():
                    try:
                        file_path.unlink()
                    except Exception as e:
                        print(f"Warning: Failed to delete {file_path.name}: {str(e)}")
    
    db = SessionLocal()
    try:
        # 1. Check/Create Default Analyst User
        default_email = "analyst@pricing.ai"
        user = db.query(User).filter(User.email == default_email).first()
        if not user:
            print(f"Creating default analyst user: {default_email}...")
            user = User(
                full_name="Pricing Analyst",
                email=default_email,
                password_hash=hash_password("password123"),
                role="analyst"
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            print("Analyst user registered successfully.")
        else:
            print("Default analyst user already exists.")
            
        # 2. Check if dataset already loaded
        sales_count = db.query(SalesData).count()
        if sales_count == 0:
            print("Seeding database with sample sales transaction data...")
            sample_csv_path = project_root / "datasets" / "sample_data" / "sales_sample.csv"
            
            if not sample_csv_path.exists():
                print("Error: sales_sample.csv not found! Attempting to generate it first...")
                # Run sample generator
                import subprocess
                subprocess.run([sys.executable, str(project_root / "datasets" / "sample_data" / "generate_sample.py")], check=True)
                
            if sample_csv_path.exists():
                # Read csv bytes
                with open(sample_csv_path, "rb") as f:
                    csv_content = f.read()
                    
                # Create a dataset record
                dataset = Dataset(
                    file_name="sales_sample.csv",
                    user_id=user.id,
                    total_records=0,
                    status="uploaded"
                )
                db.add(dataset)
                db.commit()
                db.refresh(dataset)
                
                print("Running analytics data cleaning & model training pipeline. This may take 5-10 seconds...")
                # Run standard cleaning
                process_uploaded_file(db, csv_content, "sales_sample.csv", dataset.id)
                print(f"Loaded records. Total database transactions count: {db.query(SalesData).count()}")
                
                # Re-calculate elasticity
                print("Calculating price elasticities...")
                calculate_all_elasticities(db)
                
                # Re-train models
                print("Training forecasting models and compiling forecasts...")
                train_and_forecast_all(db)
                
                # Recommendations
                print("Generating pricing recommendation actions...")
                generate_all_recommendations(db)
                
                print("Database fully seeded and analyzed successfully!")
            else:
                print("Critical Error: Failed to locate or generate sales_sample.csv. Seeding aborted.")
        else:
            print(f"Database already contains {sales_count} sales transactions. Skipping seeding.")
            
    except Exception as e:
        print(f"Error during seeding: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    initialize_and_seed()
