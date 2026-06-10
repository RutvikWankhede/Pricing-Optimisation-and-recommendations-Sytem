from datetime import date, datetime
from typing import List, Optional, Union
from pydantic import BaseModel, EmailStr, Field, ConfigDict

# User Schemas
class UserBase(BaseModel):
    full_name: str
    email: EmailStr
    role: Optional[str] = "analyst"

class UserCreate(UserBase):
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(UserBase):
    id: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

# Token Schemas
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None
    role: Optional[str] = None

# Dataset Schemas
class DatasetResponse(BaseModel):
    id: str
    file_name: str
    upload_time: datetime
    total_records: int
    status: str
    summary_metadata: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

# Product Schemas
class ProductResponse(BaseModel):
    id: str
    product_name: str
    category: str
    region: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

# Sales Data Schemas
class SalesDataResponse(BaseModel):
    id: str
    sales_date: date
    price: float
    quantity_sold: int
    revenue: float
    cost: float
    profit: float

    model_config = ConfigDict(from_attributes=True)

# Forecasting Schemas
class ForecastDetail(BaseModel):
    forecast_date: date
    predicted_demand: float
    model_name: str
    confidence_score: Optional[float] = None

class ForecastResponse(BaseModel):
    product_id: str
    product_name: str
    forecast: List[ForecastDetail]

# Elasticity Schemas
class ElasticityResponse(BaseModel):
    product_id: str
    product_name: str
    elasticity_score: float
    elasticity_type: str
    analysis_date: datetime

    model_config = ConfigDict(from_attributes=True)

# Recommendation Schemas
class RecommendationResponse(BaseModel):
    product_id: str
    product_name: str
    current_price: float
    recommended_price: float
    expected_revenue_change: Optional[float] = None
    expected_profit_change: Optional[float] = None
    recommendation_reason: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

# Scenario Simulation Schemas
class SimulationRequest(BaseModel):
    product_id: str
    simulated_price: float

class SimulationResponse(BaseModel):
    product_id: str
    product_name: str
    simulated_price: float
    predicted_demand: float
    predicted_revenue: float
    predicted_profit: float
    revenue_change_percent: float
    profit_change_percent: float
    base_price: float
    base_daily_quantity: float
    unit_cost: float
    elasticity_score: float
    elasticity_type: str

# Report Schemas
class ReportResponse(BaseModel):
    id: str
    report_type: str
    file_path: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

# Dashboard KPI Schemas
class KPICard(BaseModel):
    title: str
    value: str
    change: str
    trend: str  # "up", "down", "neutral"

class DashboardKPIs(BaseModel):
    total_revenue: KPICard
    total_profit: KPICard
    avg_margin: KPICard
    active_products: KPICard

class ChartPoint(BaseModel):
    label: str
    revenue: float
    profit: float

class CategoryShare(BaseModel):
    category: str
    revenue: float

class RegionShare(BaseModel):
    region: str
    revenue: float

class TopProductItem(BaseModel):
    id: str
    product_name: str
    category: str
    region: str
    revenue: float
    profit: float
    quantity_sold: int
    elasticity_score: Optional[float] = None
    elasticity_type: Optional[str] = None

class DashboardResponse(BaseModel):
    kpis: DashboardKPIs
    sales_trends: List[ChartPoint]
    category_share: List[CategoryShare]
    region_share: List[RegionShare]
    top_products: List[TopProductItem]
