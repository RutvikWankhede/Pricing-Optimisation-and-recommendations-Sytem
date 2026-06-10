import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, Numeric, DateTime, Date, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.database.db import Base

class User(Base):
    __tablename__ = "users"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    full_name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(String, default="analyst")  # admin, analyst
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    # Relationships
    datasets = relationship("Dataset", back_populates="user")
    reports = relationship("Report", back_populates="user")

class Dataset(Base):
    __tablename__ = "datasets"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=True)
    file_name = Column(String, nullable=False)
    upload_time = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    total_records = Column(Integer, default=0)
    status = Column(String, default="uploaded")  # uploaded, processing, processed, failed
    file_url = Column(String, nullable=True)  # Cloudinary URL for the uploaded file
    summary_metadata = Column(Text, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="datasets")
    sales_records = relationship("SalesData", back_populates="dataset", cascade="all, delete-orphan")

class Product(Base):
    __tablename__ = "products"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    product_name = Column(String, unique=True, index=True, nullable=False)
    category = Column(String, default="General")
    region = Column(String, default="National")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    # Relationships
    sales_records = relationship("SalesData", back_populates="product", cascade="all, delete-orphan")
    forecasts = relationship("ForecastingResult", back_populates="product", cascade="all, delete-orphan")
    elasticity_analyses = relationship("ElasticityAnalysis", back_populates="product", cascade="all, delete-orphan")
    recommendations = relationship("PricingRecommendation", back_populates="product", cascade="all, delete-orphan")
    simulations = relationship("ScenarioSimulation", back_populates="product", cascade="all, delete-orphan")

class SalesData(Base):
    __tablename__ = "sales_data"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    dataset_id = Column(String, ForeignKey("datasets.id"), nullable=False)
    product_id = Column(String, ForeignKey("products.id"), nullable=False)
    sales_date = Column(Date, nullable=False)
    price = Column(Numeric(10, 2), nullable=False)
    quantity_sold = Column(Integer, nullable=False)
    revenue = Column(Numeric(12, 2), nullable=False)
    cost = Column(Numeric(10, 2), nullable=False)
    profit = Column(Numeric(12, 2), nullable=False)
    
    # Relationships
    dataset = relationship("Dataset", back_populates="sales_records")
    product = relationship("Product", back_populates="sales_records")

class ForecastingResult(Base):
    __tablename__ = "forecasting_results"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    product_id = Column(String, ForeignKey("products.id"), nullable=False)
    predicted_demand = Column(Numeric(10, 2), nullable=False)
    forecast_date = Column(Date, nullable=False)
    model_name = Column(String, nullable=False)  # LinearRegression, RandomForest
    confidence_score = Column(Numeric(5, 4), nullable=True)  # R-squared or evaluation metric
    
    # Relationships
    product = relationship("Product", back_populates="forecasts")

class ElasticityAnalysis(Base):
    __tablename__ = "elasticity_analysis"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    product_id = Column(String, ForeignKey("products.id"), nullable=False)
    elasticity_score = Column(Numeric(8, 4), nullable=False)
    elasticity_type = Column(String, nullable=False)  # elastic, inelastic, unitary
    analysis_date = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    # Relationships
    product = relationship("Product", back_populates="elasticity_analyses")

class PricingRecommendation(Base):
    __tablename__ = "pricing_recommendations"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    product_id = Column(String, ForeignKey("products.id"), nullable=False)
    current_price = Column(Numeric(10, 2), nullable=False)
    recommended_price = Column(Numeric(10, 2), nullable=False)
    expected_revenue_change = Column(Numeric(8, 4), nullable=True)  # percentage
    expected_profit_change = Column(Numeric(8, 4), nullable=True)   # percentage
    recommendation_reason = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    # Relationships
    product = relationship("Product", back_populates="recommendations")

class ScenarioSimulation(Base):
    __tablename__ = "scenario_simulations"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    product_id = Column(String, ForeignKey("products.id"), nullable=False)
    simulated_price = Column(Numeric(10, 2), nullable=False)
    predicted_demand = Column(Numeric(10, 2), nullable=False)
    predicted_revenue = Column(Numeric(12, 2), nullable=False)
    predicted_profit = Column(Numeric(12, 2), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    # Relationships
    product = relationship("Product", back_populates="simulations")

class Report(Base):
    __tablename__ = "reports"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=True)
    report_type = Column(String, nullable=False)  # pdf, excel
    file_path = Column(Text, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    # Relationships
    user = relationship("User", back_populates="reports")
