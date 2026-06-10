# PriceSense Analytics Implementation Plan

Implementation roadmap for building the **PriceSense Analytics (ML-Based Pricing Optimization & Recommendation System)** minor project. It is structured to run locally on SQLite, FastAPI, and a responsive HTML/CSS/JS frontend styled with Tailwind CSS.

---

## User Review Required

> [!IMPORTANT]
> The current frontend is built with **Streamlit** (which is Python-based). However, the technical requirement specifies a frontend using **HTML, CSS, JS, and Tailwind CSS**.
> To keep the premium look and feel of the original Streamlit application (sidebar navigation, dark glassmorphism cards, dashboard widgets), we propose migrating the UI layout to a clean HTML/JS single-page application using Tailwind CSS (via CDN) and Chart.js/Plotly.js for interactive rendering.

> [!WARNING]
> Authentication is requested to be avoided or simplified (avoiding full enterprise systems). The current backend codebase contains custom login/registration endpoints in `auth.py` and models in `models.py`. We plan to keep a simplified local authentication flow to maintain basic security rules without introducing third-party services.

---

## Open Questions

> [!IMPORTANT]
> 1. Do you want to completely replace the Streamlit frontend with the static HTML/Tailwind CSS/JS implementation in the `frontend` folder, or do you want to keep the Streamlit app as an alternative visualization tool?
> 2. For the HTML frontend, should we load Tailwind CSS via CDN (which is simpler for local student development) or integrate a build process (e.g., using PostCSS/Vite)? *Recommendation: Load Tailwind CSS and libraries (Chart.js, Plotly) via CDNs for standard student-level deployments.*

---

## Proposed Changes

We will build the system iteratively over 9 phases. The proposed files are located under the local workspace directory:
[pricing_optimization_system](file:///C:/Users/HP/.gemini/antigravity-ide/scratch/pricing_optimization_system)

### Phase 1: Project Setup & Static Integration
* **Tasks**: Verify current virtual environment configurations, ensure FastAPI backend routes load successfully on local ports, and initialize a basic static index file.
* **Dependencies**: Python 3.10+
* **Estimated Complexity**: Low (1-2 hours)
* **Expected Output**: Running FastAPI server with basic home response; structured workspace.

#### [NEW] [index.html](file:///C:/Users/HP/.gemini/antigravity-ide/scratch/pricing_optimization_system/frontend/index.html)
#### [NEW] [main.js](file:///C:/Users/HP/.gemini/antigravity-ide/scratch/pricing_optimization_system/frontend/main.js)
#### [NEW] [index.css](file:///C:/Users/HP/.gemini/antigravity-ide/scratch/pricing_optimization_system/frontend/index.css)

---

### Phase 2: Ingest, Upload & Cleaning
* **Tasks**: Hook up the HTML upload forms to the `/api/v1/upload/dataset` backend router. Enable automatic mapping of column headers and validation rules.
* **Dependencies**: Phase 1, Pandas.
* **Estimated Complexity**: Medium (4-6 hours)
* **Expected Output**: Files uploaded via UI; logs printed, and data saved to SQLite `sales_data` and `products` tables.

#### [MODIFY] [data_cleaning.py](file:///C:/Users/HP/.gemini/antigravity-ide/scratch/pricing_optimization_system/backend/app/services/data_cleaning.py)

---

### Phase 3: Dashboard & Revenue Analytics
* **Tasks**: Map JSON metrics from `/api/v1/dashboard/kpis` to visual components in the frontend. Plot the historical revenue/profit charts.
* **Dependencies**: Phase 2, Chart.js.
* **Estimated Complexity**: Medium (4 hours)
* **Expected Output**: Interactive line graphs and KPI summary numbers updating automatically post-upload.

#### [MODIFY] [dashboard.py](file:///C:/Users/HP/.gemini/antigravity-ide/scratch/pricing_optimization_system/backend/app/api/routes/dashboard.py)

---

### Phase 4: Demand Forecasting
* **Tasks**: Connect the selected product to the Scikit-Learn training services. Generate the 30-day forecast and plot the demand trend line.
* **Dependencies**: Phase 3, Scikit-Learn.
* **Estimated Complexity**: High (6-8 hours)
* **Expected Output**: Historical volumes plotted alongside a forecasted prediction line.

#### [MODIFY] [forecasting.py](file:///C:/Users/HP/.gemini/antigravity-ide/scratch/pricing_optimization_system/backend/app/services/forecasting.py)

---

### Phase 5: Price Elasticity Analysis
* **Tasks**: Implement the log-log ordinary least-squares regression calculations. Categorize products as Elastic/Inelastic, and draw the demand curve charts.
* **Dependencies**: Phase 2, Statsmodels / Scikit-Learn.
* **Estimated Complexity**: High (8 hours)
* **Expected Output**: A scatter plot representing historical transactions overlaid with the derived demand curve.

#### [MODIFY] [elasticity.py](file:///C:/Users/HP/.gemini/antigravity-ide/scratch/pricing_optimization_system/backend/app/services/elasticity.py)

---

### Phase 6: Recommendation Engine
* **Tasks**: Apply economic optimization calculations to recommend pricing adjustments. Explain the reasons behind suggestions in clear card blocks.
* **Dependencies**: Phase 5.
* **Estimated Complexity**: Medium (4-6 hours)
* **Expected Output**: An optimization table listing recommended price adjustments and expected profit/revenue percentage shifts.

#### [MODIFY] [recommendation.py](file:///C:/Users/HP/.gemini/antigravity-ide/scratch/pricing_optimization_system/backend/app/services/recommendation.py)

---

### Phase 7: Scenario Simulation
* **Tasks**: Connect price slider changes in the client to the simulation endpoint, computing impact values in real-time.
* **Dependencies**: Phase 6.
* **Estimated Complexity**: Medium (4 hours)
* **Expected Output**: Interactive sliders updating expected revenue/profit changes instantly on drag.

---

### Phase 8: Report Export
* **Tasks**: Generate professional PDF reports summarizing findings via ReportLab, and download Excel data logs via OpenPyXL.
* **Dependencies**: Phase 2, Phase 6.
* **Estimated Complexity**: High (8 hours)
* **Expected Output**: Clickable download triggers streaming file formats to the local machine.

#### [MODIFY] [reporting.py](file:///C:/Users/HP/.gemini/antigravity-ide/scratch/pricing_optimization_system/backend/app/services/reporting.py)

---

### Phase 9: Testing & GitHub Ready
* **Tasks**: Run backend unit tests, audit API endpoints for security practices, document setup instructions in README, and package files for a student portfolio.
* **Dependencies**: All Phases.
* **Estimated Complexity**: Medium (4 hours)
* **Expected Output**: Clean passing test suite; comprehensive README markdown documentation.

#### [NEW] [README.md](file:///C:/Users/HP/.gemini/antigravity-ide/scratch/pricing_optimization_system/README.md)

---

## Verification Plan

### Automated Tests
* Run the backend tests to verify SQLAlchemy structures, API responses, and authentication flows:
  ```powershell
  python -m pytest backend/tests/
  ```

### Manual Verification
* Start the FastAPI service:
  ```powershell
  python backend/app/main.py
  ```
* Open the frontend in a standard web browser (e.g. `http://localhost:8000` or double-click `index.html`) to verify upload functionalities, dynamic simulation curves, and download actions.
