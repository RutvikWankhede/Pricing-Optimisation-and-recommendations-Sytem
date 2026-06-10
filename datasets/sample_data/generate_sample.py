import os
import random
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

def generate_sample_dataset():
    # Set random seed for reproducibility
    np.random.seed(42)
    random.seed(42)
    
    # Define food delivery products with cost, base price, base daily quantity, elasticity coefficient, and category
    products_config = {
        "Chicken Biryani": {
            "cost": 100.0,
            "base_price": 250.0,
            "base_qty": 65,
            "elasticity": -1.5,  # Moderately Elastic
            "category": "Biryani",
            "price_points": [199.0, 229.0, 250.0, 279.0, 299.0]
        },
        "Margherita Pizza": {
            "cost": 120.0,
            "base_price": 299.0,
            "base_qty": 55,
            "elasticity": -1.7,  # Highly Elastic
            "category": "Pizza",
            "price_points": [249.0, 279.0, 299.0, 329.0, 349.0]
        },
        "Veggie Burger": {
            "cost": 45.0,
            "base_price": 119.0,
            "base_qty": 80,
            "elasticity": -1.3,  # Moderately Elastic
            "category": "Burger",
            "price_points": [89.0, 99.0, 119.0, 139.0, 149.0]
        },
        "Hakka Noodles": {
            "cost": 60.0,
            "base_price": 159.0,
            "base_qty": 50,
            "elasticity": -1.1,  # Unitary Elastic
            "category": "Chinese",
            "price_points": [129.0, 149.0, 159.0, 179.0, 199.0]
        },
        "Salmon Sushi": {
            "cost": 220.0,
            "base_price": 499.0,
            "base_qty": 20,
            "elasticity": -0.7,  # Inelastic
            "category": "Sushi",
            "price_points": [429.0, 459.0, 499.0, 529.0, 549.0]
        },
        "Penne Alfredo": {
            "cost": 80.0,
            "base_price": 199.0,
            "base_qty": 40,
            "elasticity": -1.2,  # Moderately Elastic
            "category": "Pasta",
            "price_points": [169.0, 189.0, 199.0, 219.0, 239.0]
        }
    }
    
    regions = ["Chennai", "Bangalore", "Mumbai", "Delhi", "Hyderabad", "Pune"]
    
    # We will generate daily data for the last 180 days
    end_date = datetime.now()
    start_date = end_date - timedelta(days=180)
    
    records = []
    
    current_date = start_date
    while current_date <= end_date:
        weekday = current_date.weekday()  # 0 to 6
        month = current_date.month
        
        # Seasonality factors
        # Higher sales on weekends (Sat: 1.2x, Sun: 1.3x)
        weekday_factor = 1.3 if weekday == 6 else (1.2 if weekday == 5 else 0.9)
        # Seasonal monthly demand variations (higher in summer/winter holidays)
        month_factor = 1.2 if month in [11, 12, 5, 6] else 0.95
        
        for prod_name, config in products_config.items():
            # For each product, let's select a price point that changes occasionally (every 30 days)
            # This simulates real business price testing experiments
            price_phase = (current_date - start_date).days // 30
            # Ensure price phase wraps within list bounds
            price_idx = price_phase % len(config["price_points"])
            price = config["price_points"][price_idx]
            
            # Add small random price shifts per region to enrich the data
            for region in regions:
                region_price_shift = (random.randint(-2, 2) * 50.0) if config["base_price"] > 2000 else (random.randint(-2, 2) * 10.0)
                final_price = max(config["cost"] + 5.0, price + region_price_shift)
                
                # Elasticity simulation formula:
                # Q = Q_base * (Price_final / Price_base) ^ Elasticity * Seasonality * Noise
                price_ratio = final_price / config["base_price"]
                expected_qty = config["base_qty"] * (price_ratio ** config["elasticity"])
                
                # Apply seasonality
                expected_qty *= weekday_factor * month_factor
                
                # Apply a slight long-term growth trend (+0.1% growth per day)
                days_elapsed = (current_date - start_date).days
                trend_factor = 1.0 + (0.001 * days_elapsed)
                expected_qty *= trend_factor
                
                # Apply noise
                noise = np.random.normal(1.0, 0.15)
                qty = max(0, int(round(expected_qty * noise)))
                
                # Calculate revenue, cost, profit
                revenue = qty * final_price
                total_cost = qty * config["cost"]
                profit = revenue - total_cost
                
                records.append({
                    "Product Name": prod_name,
                    "Category": config["category"],
                    "Price": final_price,
                    "Units Sold": qty,
                    "Revenue": revenue,
                    "Cost": config["cost"],
                    "Date": current_date.strftime("%Y-%m-%d"),
                    "Region": region
                })
                
        current_date += timedelta(days=1)
        
    df = pd.DataFrame(records)
    
    # Save CSV
    output_dir = os.path.dirname(os.path.abspath(__file__))
    output_path = os.path.join(output_dir, "sales_sample.csv")
    df.to_csv(output_path, index=False)
    print(f"Generated sample dataset with {len(df)} rows at: {output_path}")

if __name__ == "__main__":
    generate_sample_dataset()
