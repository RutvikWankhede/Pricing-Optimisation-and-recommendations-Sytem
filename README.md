
# PriceSense Analytics (ML-Based Pricing Optimization & Recommendation System)

PriceSense Analytics is an AI-powered pricing optimization dashboard that helps businesses analyze sales trends, forecast demand, and generate pricing recommendations using machine learning.

The project uses FastAPI for the backend, SQLite for storage, and a simple frontend dashboard for visualizing analytics and reports.

---

## 🚀 Getting Started

### 1. Prerequisites
Ensure you have **Python 3.10+** installed on your system.

### 2. Environment Setup
Create a virtual environment and install the required dependencies:

```bash
# Navigate to project folder
cd pricing_optimization_system

# Create virtual environment
python -m venv .venv

# Activate virtual environment
# On Windows:
.venv\Scripts\activate
# On macOS/Linux:
source .venv/bin/activate

# Install backend and server dependencies
pip install -r backend/requirements.txt
```

### 3. Initialize & Seed the Database
Run the seeder script to initialize the SQLite tables, create a default analyst account (`analyst@pricing.ai` / `password123`), process the sample dataset, calculate elasticities, and pre-train the ML models:

```bash
python init_db.py
```

### 4. Run the Application
Start the FastAPI backend server using Uvicorn:

```bash
python backend/app/main.py
```

Open your browser and navigate to:
👉 **[http://localhost:8000](http://localhost:8000)** (Main UI dashboard client)

The interactive Swagger API documentation is accessible at:
👉 [http://localhost:8000/docs](http://localhost:8000/docs)

---
## 🛠️ Testing

To run the automated backend endpoint test suite, execute:

```bash
python -m pytest backend/tests/
```
=======

## Features
* Demand forecasting
* Price elasticity analysis
* Revenue optimization
* Dynamic pricing simulations
* Interactive analytics dashboard
* CSV dataset upload and reporting
---

## ## Tech Stack

### Frontend

* HTML5
* CSS3
* JavaScript (Vanilla JS)
* Chart.js
* Material Symbols Icons

### Backend

* FastAPI
* Uvicorn
* SQLAlchemy
* JWT Authentication
* SlowAPI (Rate Limiting)

### Database

* SQLite
* PostgreSQL (optional production support)

### Machine Learning & Analytics

* Pandas
* NumPy
* Scikit-learn
* Matplotlib

### Reporting

* ReportLab (PDF Reports)
* OpenPyXL (Excel Reports)

### Security & Configuration

* Python-dotenv
* Passlib (bcrypt)
* PyJWT

### Deployment / Dev Tools

* Git & GitHub
* Python Virtual Environment
* REST API
* Swagger/OpenAPI Docs



