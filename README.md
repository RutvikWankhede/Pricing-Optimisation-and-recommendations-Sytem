
# PriceSense Analytics (ML-Based Pricing Optimization & Recommendation System)

PriceSense Analytics is a self-contained pricing optimization and demand forecasting system. It uses historical transactional sales data to estimate the price elasticity of demand, project volume shifts, train forecasting regression models, simulate dynamic pricing scenarios, and generate optimal price suggestions to maximize revenue or profits.

The application is structured as a **three-tier single-host system** where the static glassmorphic frontend (HTML/CSS/JS) is served directly from the FastAPI backend, allowing the entire platform to run on a single port.

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



