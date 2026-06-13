# PriceSense Analytics

### ML-Based Pricing Optimization & Recommendation System

PriceSense Analytics is a pricing optimization and business analytics platform built to help businesses analyze sales performance, forecast demand, and generate smart pricing recommendations using machine learning concepts.

The project combines data analytics, forecasting, elasticity analysis, and interactive dashboards into a simple SaaS-style web application.

---

## Live Demo
Frontend: https://pricing-optimisation-and-recommenda.vercel.app/

# Features

* Revenue and profit analytics dashboard
* Demand forecasting
* Price elasticity analysis
* AI-based pricing recommendations
* Dynamic pricing simulation
* CSV dataset upload support
* PDF and Excel report generation
* Interactive charts and visualizations
* JWT-based authentication system

---

# Tech Stack

## Frontend

* HTML5
* CSS3
* Vanilla JavaScript
* Chart.js

## Backend

* FastAPI
* SQLAlchemy
* Uvicorn
* JWT Authentication

## Database

* SQLite (Development)
* PostgreSQL ready (optional)

## Machine Learning & Analytics

* Pandas
* NumPy
* Scikit-learn

## Reporting

* ReportLab
* OpenPyXL

---

# Getting Started

## 1. Clone the Repository

```bash
git clone https://github.com/RutvikWankhede/Pricing-Optimisation-and-recommendations-Sytem.git
cd Pricing-Optimisation-and-recommendations-Sytem
```

---

## 2. Create Virtual Environment

```bash
python -m venv .venv
```

### Activate Environment

#### Windows

```bash
.venv\Scripts\activate
```

#### macOS/Linux

```bash
source .venv/bin/activate
```

---

## 3. Install Dependencies

```bash
pip install -r backend/requirements.txt
```

---

## 4. Initialize Database

```bash
python init_db.py
```

OR use the advanced realistic dataset:

```bash
python pricesense_clean_dataset.py
```

This generates:

* realistic food delivery transactions
* elasticity calculations
* forecasting data
* pricing recommendations

---

## 5. Run the Application

```bash
python -m uvicorn backend.app.main:app --reload
```

---

# Access the Application

Main Dashboard:

```txt
http://localhost:8000
```

Swagger API Docs:

```txt
http://localhost:8000/docs
```

---

# Demo Login

```txt
Email: analyst@pricing.ai
Password: password123
```

---

# Running Tests

```bash
python -m pytest backend/tests/
```

---

# Project Highlights

* Confidence-aware pricing recommendation engine
* Explainable AI recommendation logic
* Interactive SaaS-style analytics dashboard
* Realistic synthetic dataset generation
* Revenue optimization simulation
* Modern dark UI with responsive charts

---

# Future Improvements


* PostgreSQL production migration
* Redis caching
* Advanced forecasting models
* Role-based access control

---



Built as a college-level ML and analytics project focused on pricing optimization, forecasting, and business intelligence systems.
