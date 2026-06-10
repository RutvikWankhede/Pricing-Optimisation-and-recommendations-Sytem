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

## 📁 Technical Documentation Index

Detailed requirements, architecture schemas, and implementation logs are stored in the `docs/` folder:

1. **[Product Requirements Document (PRD)](./docs/prd_product_requirements_document.md)**: Product overview, user stories, MVP scope, core features, and project goals.
2. **[Technical Requirements Document (TRD)](./docs/trd_technical_requirements_document.md)**: Three-tier architecture, Scikit-Learn regression models, PED equations, and tech stack justifications.
3. **[App Flow & Workflows](./docs/app_flow_documentation.md)**: User journeys, endpoint interaction diagrams, ML modeling pipelines, and export execution flows.
4. **[UI/UX Design Brief](./docs/ui_ux_design_brief.md)**: Slate-dark palette theme, glassmorphic card grids, responsive viewports, and page-specific wireframe models.
5. **[Backend Schema Ledger](./docs/backend_schema_documentation.md)**: Entity-relation structures, `schema.sql` syntax, SQLAlchemy database models, and API route mappings.
6. **[Project Implementation Plan](./docs/implementation_plan.md)**: Phase-by-phase timeline milestones, tasks checklists, and system verification plans.

---

## 🛠️ Testing

To run the automated backend endpoint test suite, execute:

```bash
python -m pytest backend/tests/
```
