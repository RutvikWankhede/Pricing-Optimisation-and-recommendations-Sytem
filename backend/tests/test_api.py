import os
import sys
import io
import pytest
from pathlib import Path
from fastapi.testclient import TestClient

# Add backend directory to Python path
project_root = Path(__file__).resolve().parents[2]
backend_path = project_root / "backend"
sys.path.append(str(backend_path))

from app.main import app
from app.database.db import SessionLocal, Base, engine
from app.database.models import User, Product, SalesData, Dataset

client = TestClient(app)

@pytest.fixture(scope="module", autouse=True)
def setup_db():
    # Make sure tables exist and match latest schema
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        # Check if default analyst exists, if not create one for testing
        test_email = "test_analyst@pricing.ai"
        user = db.query(User).filter(User.email == test_email).first()
        if not user:
            from app.core.security import hash_password
            user = User(
                full_name="Test Analyst",
                email=test_email,
                password_hash=hash_password("password123"),
                role="analyst"
            )
            db.add(user)
            db.commit()
    finally:
        db.close()
    yield

def get_auth_headers():
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "test_analyst@pricing.ai", "password": "password123"}
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

def test_user_login_invalid():
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "nonexistent@pricing.ai", "password": "wrongpassword"}
    )
    assert response.status_code == 401

def test_user_profile():
    headers = get_auth_headers()
    response = client.get("/api/v1/auth/me", headers=headers)
    assert response.status_code == 200
    assert response.json()["email"] == "test_analyst@pricing.ai"

def test_dashboard_summary_empty():
    # Test dashboard when database has active products but maybe not fully populated, or verify it works
    headers = get_auth_headers()
    response = client.get("/api/v1/dashboard/summary", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert "kpis" in data
    assert "sales_trends" in data
    assert "category_share" in data
    assert "region_share" in data
    assert "top_products" in data

def test_dataset_upload():
    headers = get_auth_headers()
    
    # Create a small CSV string with correct headers mapped in COLUMN_MAPS
    # COLUMN_MAPS has aliases like "product name", "price", "units sold", "cost", "date", "revenue"
    csv_data = (
        "product name,price,quantity_sold,cost,date,revenue,category,region\n"
        "Chicken Biryani,250,5,100,2026-06-01,1250,Biryani,Chennai\n"
        "Chicken Biryani,250,4,100,2026-06-02,1000,Biryani,Chennai\n"
        "Chicken Biryani,240,7,100,2026-06-03,1680,Biryani,Chennai\n"
        "Chicken Biryani,260,3,100,2026-06-04,780,Biryani,Chennai\n"
        "Chicken Biryani,250,6,100,2026-06-05,1500,Biryani,Chennai\n"
        "Margherita Pizza,299,2,120,2026-06-01,598,Pizza,Bangalore\n"
        "Margherita Pizza,299,3,120,2026-06-02,897,Pizza,Bangalore\n"
        "Margherita Pizza,289,5,120,2026-06-03,1445,Pizza,Bangalore\n"
        "Margherita Pizza,299,2,120,2026-06-04,598,Pizza,Bangalore\n"
        "Margherita Pizza,319,4,120,2026-06-05,1276,Pizza,Bangalore\n"
    )
    
    file_payload = {"file": ("test_sales.csv", io.BytesIO(csv_data.encode("utf-8")), "text/csv")}
    
    response = client.post(
        "/api/v1/upload/upload_dataset",
        headers=headers,
        files=file_payload
    )
    
    # Endpoint returns 202 ACCEPTED
    assert response.status_code == 202
    data = response.json()
    assert "id" in data
    assert data["status"] == "uploaded"
    assert data["file_name"] == "test_sales.csv"

def test_get_upload_history():
    headers = get_auth_headers()
    response = client.get("/api/v1/upload/history", headers=headers)
    assert response.status_code == 200
    assert len(response.json()) > 0

def test_pricing_products():
    headers = get_auth_headers()
    response = client.get("/api/v1/pricing/products", headers=headers)
    assert response.status_code == 200
    products = response.json()
    assert len(products) > 0
    # Capture first product for next tests
    pytest.shared_product_id = products[0]["id"]
    pytest.shared_product_name = products[0]["product_name"]

def test_pricing_elasticity():
    headers = get_auth_headers()
    product_id = pytest.shared_product_id
    response = client.get(f"/api/v1/pricing/elasticity/{product_id}", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert "elasticity_score" in data
    assert "elasticity_type" in data
    assert data["product_id"] == product_id

def test_pricing_all_elasticity():
    headers = get_auth_headers()
    response = client.get("/api/v1/pricing/elasticity", headers=headers)
    assert response.status_code == 200
    assert len(response.json()) > 0

def test_pricing_recommendation():
    headers = get_auth_headers()
    product_id = pytest.shared_product_id
    response = client.get(f"/api/v1/pricing/recommendations/{product_id}", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert "recommended_price" in data
    assert "recommendation_reason" in data

def test_pricing_all_recommendations():
    headers = get_auth_headers()
    response = client.get("/api/v1/pricing/recommendations", headers=headers)
    assert response.status_code == 200
    assert len(response.json()) > 0

def test_pricing_simulate():
    headers = get_auth_headers()
    product_id = pytest.shared_product_id
    # Run simulation for a +10% price offset
    response = client.get(f"/api/v1/pricing/recommendations/{product_id}", headers=headers)
    current_price = response.json()["current_price"]
    
    sim_payload = {
        "product_id": product_id,
        "simulated_price": current_price * 1.10
    }
    response_sim = client.post(
        "/api/v1/pricing/simulate",
        headers=headers,
        json=sim_payload
    )
    assert response_sim.status_code == 200
    sim_data = response_sim.json()
    assert "predicted_demand" in sim_data
    assert "revenue_change_percent" in sim_data
    assert "profit_change_percent" in sim_data

def test_demand_forecast():
    headers = get_auth_headers()
    product_id = pytest.shared_product_id
    response = client.get(f"/api/v1/forecast/{product_id}", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert "forecast" in data
    assert len(data["forecast"]) == 30
    assert "predicted_demand" in data["forecast"][0]

def test_reports_generation():
    headers = get_auth_headers()
    response = client.post("/api/v1/reports/generate", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "excel_file" in data
    assert "pdf_file" in data

def test_download_report_excel():
    headers = get_auth_headers()
    response = client.get("/api/v1/reports/download/excel", headers=headers)
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    assert len(response.content) > 0

def test_download_report_pdf():
    headers = get_auth_headers()
    response = client.get("/api/v1/reports/download/pdf", headers=headers)
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert len(response.content) > 0

def test_recommendation_explainability_fields():
    import json
    headers = get_auth_headers()
    product_id = pytest.shared_product_id
    response = client.get(f"/api/v1/pricing/recommendations/{product_id}", headers=headers)
    assert response.status_code == 200
    data = response.json()
    reason_str = data["recommendation_reason"]
    reason = json.loads(reason_str)
    
    assert "recommended_price" in reason
    assert "confidence_score" in reason
    assert "elasticity_used" in reason
    assert "branch_taken" in reason
    assert "reasoning" in reason
    assert "bounds_applied" in reason
    assert "flagged_for_review" in reason
    assert isinstance(reason["bounds_applied"], list)
    assert isinstance(reason["flagged_for_review"], bool)
