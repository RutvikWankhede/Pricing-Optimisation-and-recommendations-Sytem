# Backend Schema Documentation
## Project: PriceSense Analytics (ML-Based Pricing Optimization & Recommendation System)

---

## 1. Backend Folder Structure
The backend codebase uses a modular directory structure to separate API routers, core configuration, database management, and business services.

```text
backend/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI application entry point
│   ├── api/
│   │   ├── __init__.py
│   │   └── routes/             # Endpoint definitions
│   │       ├── auth.py         # Login, registration, JWT tokens
│   │       ├── dashboard.py    # Aggregate stats, KPIs, chart data
│   │       ├── forecasting.py  # 30-day demand predictions
│   │       ├── pricing.py      # Elasticity, recommendations, simulation
│   │       ├── reports.py      # PDF/Excel report downloads
│   │       └── upload.py       # Dataset upload & ingestion status
│   ├── core/
│   │   ├── config.py           # Settings and environment loaders
│   │   ├── constants.py        # Global application constants
│   │   └── security.py         # Password hashing and JWT generation
│   ├── database/
│   │   ├── db.py               # SQLite connection and session maker
│   │   ├── models.py           # SQLAlchemy database model structures
│   │   └── schemas.py          # Pydantic data schemas and validators
│   └── services/
│       ├── data_cleaning.py    # CSV/Excel preprocessing logic
│       ├── elasticity.py       # PED log-log linear regressions
│       ├── forecasting.py      # ML demand forecasting models
│       ├── optimization.py     # Economic price optimizations
│       ├── recommendation.py   # Business logic triggers and logs
│       └── reporting.py        # ReportLab PDF & OpenPyXL Excel builders
├── datasets/                   # Storage folder for uploaded CSVs
├── tests/                      # Unit and integration test files
├── requirements.txt            # Python dependencies lists
└── .env                        # Local secret configurations
```

---

## 2. Database Schema (`schema.sql`)
The following SQL schema represents the tables generated in SQLite to store users, historical transaction data, and optimization outputs.

```sql
-- 1. Users Table
CREATE TABLE users (
    id TEXT PRIMARY KEY,
    full_name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role TEXT DEFAULT 'analyst',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_users_email ON users(email);

-- 2. Datasets Table
CREATE TABLE datasets (
    id TEXT PRIMARY KEY,
    user_id TEXT,
    file_name TEXT NOT NULL,
    upload_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    total_records INTEGER DEFAULT 0,
    status TEXT DEFAULT 'uploaded',
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE SET NULL
);

-- 3. Products Table
CREATE TABLE products (
    id TEXT PRIMARY KEY,
    product_name TEXT UNIQUE NOT NULL,
    category TEXT DEFAULT 'General',
    region TEXT DEFAULT 'National',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_products_name ON products(product_name);

-- 4. Sales Data Table
CREATE TABLE sales_data (
    id TEXT PRIMARY KEY,
    dataset_id TEXT NOT NULL,
    product_id TEXT NOT NULL,
    sales_date DATE NOT NULL,
    price REAL NOT NULL,
    quantity_sold INTEGER NOT NULL,
    revenue REAL NOT NULL,
    cost REAL NOT NULL,
    profit REAL NOT NULL,
    FOREIGN KEY(dataset_id) REFERENCES datasets(id) ON DELETE CASCADE,
    FOREIGN KEY(product_id) REFERENCES products(id) ON DELETE CASCADE
);

CREATE INDEX idx_sales_data_date ON sales_data(sales_date);
CREATE INDEX idx_sales_data_product ON sales_data(product_id);

-- 5. Forecasting Results Table
CREATE TABLE forecasting_results (
    id TEXT PRIMARY KEY,
    product_id TEXT NOT NULL,
    predicted_demand REAL NOT NULL,
    forecast_date DATE NOT NULL,
    model_name TEXT NOT NULL,
    confidence_score REAL,
    FOREIGN KEY(product_id) REFERENCES products(id) ON DELETE CASCADE
);

CREATE INDEX idx_forecast_product ON forecasting_results(product_id);

-- 6. Elasticity Analysis Table
CREATE TABLE elasticity_analysis (
    id TEXT PRIMARY KEY,
    product_id TEXT NOT NULL,
    elasticity_score REAL NOT NULL,
    elasticity_type TEXT NOT NULL,
    analysis_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(product_id) REFERENCES products(id) ON DELETE CASCADE
);

CREATE INDEX idx_elasticity_product ON elasticity_analysis(product_id);

-- 7. Pricing Recommendations Table
CREATE TABLE pricing_recommendations (
    id TEXT PRIMARY KEY,
    product_id TEXT NOT NULL,
    current_price REAL NOT NULL,
    recommended_price REAL NOT NULL,
    expected_revenue_change REAL,
    expected_profit_change REAL,
    recommendation_reason TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(product_id) REFERENCES products(id) ON DELETE CASCADE
);

CREATE INDEX idx_recommendation_product ON pricing_recommendations(product_id);

-- 8. Scenario Simulations Table
CREATE TABLE scenario_simulations (
    id TEXT PRIMARY KEY,
    product_id TEXT NOT NULL,
    simulated_price REAL NOT NULL,
    predicted_demand REAL NOT NULL,
    predicted_revenue REAL NOT NULL,
    predicted_profit REAL NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(product_id) REFERENCES products(id) ON DELETE CASCADE
);

-- 9. Generated Reports Metadata Table
CREATE TABLE reports (
    id TEXT PRIMARY KEY,
    user_id TEXT,
    report_type TEXT NOT NULL,
    file_path TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE SET NULL
);
```

---

## 3. SQLAlchemy Database Models (`models.py`)
Refer to the codebase at [models.py](file:///C:/Users/HP/.gemini/antigravity-ide/scratch/pricing_optimization_system/backend/app/database/models.py) for the complete implementation. Below is an outline of table associations and cascading deletion configurations:

* **Users $\rightarrow$ Datasets / Reports**: One-to-Many relationships. If a user is deleted, datasets are kept (set `user_id` to NULL) to preserve raw transaction records.
* **Datasets $\rightarrow$ SalesData**: One-to-Many relationship with `cascade="all, delete-orphan"`. Deleting a dataset runs a hard cascade deleting all related sales records.
* **Products $\rightarrow$ SalesData / Forecasts / Elasticity / Recommendations / Simulations**: One-to-Many relationships configured with `cascade="all, delete-orphan"`. Ensures updating or removing SKUs purges calculated analytical records.

---

## 4. API Request/Response Schemas (`schemas.py`)
Refer to the file at [schemas.py](file:///C:/Users/HP/.gemini/antigravity-ide/scratch/pricing_optimization_system/backend/app/database/schemas.py) for the exact structures.
Key validations are handled via Pydantic model configurations:
* **`UserCreate`**: Validates standard string passwords during signup.
* **`SimulationRequest`**: Restricts variables to prevent zero-division errors, validating positive float inputs for pricing fields.
* **`DashboardResponse`**: Structure designed to map nested KPIs and chart coordinates directly to JSON formats needed by visual dashboard libraries.
