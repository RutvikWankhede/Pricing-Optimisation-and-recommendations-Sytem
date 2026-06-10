# Technical Stack & System Architecture Documentation

---

## Executive Summary

The **Pricing Optimization System** is a full‑stack web application built with a lightweight vanilla frontend and a **FastAPI**‑based Python backend. It provides data ingestion, automated analytics (elasticity calculation, demand forecasting), AI‑driven recommendations, and rich visual reporting through interactive charts. Security hardening (rate limiting, security headers, JWT authentication, secret management) and production‑ready configuration have been implemented. This document details each layer of the stack, design decisions, versions, and recommendations for further maturity improvements.

---

## 1. Frontend Stack

| Aspect | Technology / Library | Version / Source | Details |
|---|---|---|---|
| **Framework / Library** | Vanilla HTML, CSS, JavaScript (no framework) | N/A | Hand‑crafted UI in `frontend/` directory, pages under `frontend/pages/` |
| **UI / Icon Library** | Google **Material Symbols** (outlined) via CDN | `https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined` | Used for navigation icons and action buttons |
| **Styling System** | Custom CSS with **CSS Variables** (dark palette, glassmorphism) | N/A | `frontend/css/styles.css` defines a premium dark theme, glass‑like cards, and micro‑animations |
| **State Management** | Simple global JavaScript object (`appState`) in `frontend/js/app.js` | N/A | Stores auth token, user info, and UI flags |
| **Routing / Navigation** | Multi‑page navigation via `<a href="/page.html">` links (no SPA router) | N/A | Each page loads its own script; authentication guard performed in `app.js` |
| **Responsive System** | CSS Flexbox/Grid + media queries | N/A | Layout adapts to desktop, tablet, and mobile viewports |
| **Animations** | CSS transitions, `@keyframes` (pulse, hover effects) | N/A | Subtle micro‑animations for cards, buttons, and hover states |
| **Charting** | **Chart.js** + **chartjs‑plugin‑zoom** via CDN | `https://cdn.jsdelivr.net/npm/chart.js` | Interactive line, doughnut, and bar charts on Dashboard, Forecasting, Elasticity pages |
| **Form Handling** | Native HTML forms + `fetch` API for JSON payloads | N/A | Upload, mapping, and authentication forms use `FormData` and async fetch calls |
| **Data Fetching** | Browser `fetch` (Promise‑based) | N/A | All API calls go through `apiRequest` wrapper in `app.js` (adds JWT header) |

**Why this stack?**
- Minimal dependencies keep the bundle lightweight and reduce attack surface.
- Custom CSS enables a premium, glass‑morphic look without large UI frameworks.
- Chart.js provides a rich, interactive charting experience with zoom/pan support.

**Future considerations**
- Migrating to a modern SPA framework (React/Vite) could improve state handling and component reuse.
- Introduce a CSS‑in‑JS solution or Tailwind (if desired) for tighter design tokens.

---

## 2. Backend Stack

| Layer | Technology | Version | Purpose |
|---|---|---|---|
| **Web Framework** | **FastAPI** | `fastapi==0.111.0` | High‑performance async API server, automatic OpenAPI docs |
| **ASGI Server** | **uvicorn** | `uvicorn==0.30.1` | Production‑grade server for FastAPI |
| **ORM / DB Layer** | **SQLAlchemy** | `sqlalchemy>=2.0.31` | Object‑relational mapping, migrations, transaction handling |
| **Database** | **SQLite** (default) / **PostgreSQL** (optional) | N/A | `pricing_ai.db` for local dev; can switch via `DATABASE_URL` env var |
| **Authentication** | **PyJWT** & **passlib[bcrypt]** | `pyjwt==2.8.0`, `passlib[bcrypt]==1.7.4` | JWT token issuance & password hashing |
| **Environment Management** | **python‑dotenv** | `python-dotenv==1.0.1` | Loads `.env` configuration |
| **Rate Limiting** | **slowapi** (based on `limits`) | Included via custom middleware | Global 100 req/min, per‑endpoint 20 req/min for uploads |
| **Security Headers** | Custom `SecurityHeadersMiddleware` | N/A | Adds CSP, HSTS, X‑Frame‑Options, etc. |
| **Background Tasks** | FastAPI `BackgroundTasks` | N/A | Off‑loads heavy analytics pipelines |
| **Reporting** | **reportlab**, **openpyxl** | `reportlab==4.2.0`, `openpyxl==3.1.2` | PDF & Excel report generation |
| **Analytics / ML** | **pandas**, **numpy**, **scikit‑learn**, **matplotlib** | `pandas>=2.2.3`, `numpy>=2.1.0`, `scikit-learn>=1.5.2`, `matplotlib>=3.9.0` | Data cleaning, elasticity calculation, forecasting models, charts for PDFs |
| **Logging** | Python `logging` (INFO level) | N/A | Centralized logger with security‑aware messages |

**Key Design Decisions**
- **Stateless JWT** authentication enables scalable horizontal deployment.
- **Rate limiting** via `slowapi` protects critical endpoints from abuse.
- **Security headers** are enforced centrally through middleware.
- **Background tasks** avoid blocking the request thread for long‑running ML pipelines.

**Maturity Recommendations**
1. Add **Alembic** migrations for schema versioning.
2. Containerise the backend with **Docker** (multi‑stage build) for consistent deployments.
3. Configure **Uvicorn workers** (e.g., `--workers 4`) in production.
4. Enable **structured logging** (JSON) and push to a log aggregation service.

---

## 3. Analytics & ML Stack

| Component | Library | Role |
|---|---|---|
| **Data Manipulation** | **pandas** | Reads CSV/Excel, cleans, normalises, maps columns |
| **Numerical Computing** | **numpy** | Underpins pandas and scikit‑learn calculations |
| **Machine Learning** | **scikit‑learn** | Linear regression, Ridge, Lasso models for demand forecasting and price‑elasticity estimation |
| **Visualization for Reports** | **matplotlib** | Generates static charts embedded in PDF/Excel reports |
| **Background Orchestration** | FastAPI `BackgroundTasks` | Runs the entire pipeline (`process_uploaded_file → calculate_all_elasticities → train_and_forecast_all → generate_all_recommendations`) asynchronously |
| **Custom Services** | `app/services/*` (data_cleaning, elasticity, forecasting, recommendation) | Encapsulate domain‑specific logic, keep API routes thin |

**Pipeline Overview**
1. **Upload** – Raw file stored in `datasets/raw/`.
2. **Data Cleaning** – `process_uploaded_file` validates, parses, and inserts rows.
3. **Elasticity Calculation** – `calculate_all_elasticities` computes price‑elasticity per SKU.
4. **Forecasting** – `train_and_forecast_all` fits regression models and predicts future demand.
5. **Recommendations** – `generate_all_recommendations` creates pricing scenarios.
6. **Reporting** – PDF/Excel generated via ReportLab & OpenPyXL.

**Future Enhancements**
- Replace classical models with **XGBoost** or **LightGBM** for higher accuracy.
- Add **model versioning** (MLflow) and experiment tracking.
- Parallelise heavy calculations using **joblib** or **Dask**.

---

## 4. Security Stack

| Aspect | Implementation |
|---|---|
| **Secret Management** | All secrets reside in `.env` (git‑ignored). `SECRET_KEY` is mandatory; app fails on start if missing. |
| **Environment Variable Loading** | `python-dotenv` loads from `backend/.env` via `load_dotenv`. |
| **Public vs Private Env Vars** | Frontend can only read variables prefixed with `VITE_` or `NEXT_PUBLIC_` (currently none). |
| **Authentication** | JWT (`HS256`) signed with `SECRET_KEY`; token expiry configurable via `ACCESS_TOKEN_EXPIRE_MINUTES`. Passwords hashed with Bcrypt. |
| **Rate Limiting** | Global 100 req/min (IP‑based). Critical upload routes limited to 20 req/min via decorator (`@limiter.limit`). |
| **Security Headers** | CSP (self only), HSTS (1 yr), X‑Frame‑Options (DENY), X‑Content‑Type‑Options (nosniff), Referrer‑Policy (no‑referrer). |
| **Logging of Failed Logins** | `auth.py` logs warning on failed authentication attempts. |
| **File‑size Validation** | `MAX_IMAGE_SIZE` (5 MB) & `MAX_DOCUMENT_SIZE` (25 MB) enforced in upload routes; oversized uploads return `413`. |
| **Dependency Hygiene** | `requirements.txt` pins critical libraries; no known vulnerable versions (checked via `pip-audit`). |
| **CORS** | Configurable via `CORS_ORIGINS` env var; defaults to empty list (strict). |

**Verification**
- Manual tests have confirmed `429 Too Many Requests` with `Retry-After` headers on rate‑limited endpoints.
- `curl -I` against `/api/v1/upload/analyze` shows all security headers.

**Next Steps**
1. Enable **Content‑Security‑Policy** with script‑src nonce for inline scripts.
2. Add **OWASP Dependency‑Check** CI step.
3. Implement **HTTP‑Only, Secure cookies** for JWT (if moving to cookie‑based auth).

---

## 5. Reporting Stack

| Output Format | Library | Usage |
|---|---|---|
| **PDF** | **ReportLab** (`reportlab==4.2.0`) | Generates styled PDF reports with charts and tables. |
| **Excel** | **OpenPyXL** (`openpyxl==3.1.2`) | Writes forecast tables and recommendation sheets. |
| **Charts in Reports** | **matplotlib** | Renders static images saved as PNG and embedded in PDFs/Excel. |

Reports are stored under `reports/` with subfolders `pdf/` and `excel/` created automatically by `Settings`. The API endpoints (`/reports/...`) serve the generated files.

---

## 6. Deployment & Infrastructure Stack

| Component | Current State | Recommended Production Setup |
|---|---|---|
| **Operating System** | Development on **Windows 10/11** (PowerShell) | Deploy on **Linux** (Ubuntu 22.04) for better container support |
| **Process Manager** | `uvicorn` run via `python -m uvicorn main:app --reload` | Use **Gunicorn** with **uvicorn workers** (`gunicorn -k uvicorn.workers.UvicornWorker -w 4 main:app`) |
| **Containerisation** | Not containerised yet | Create a multi‑stage **Dockerfile** (builder → runtime) and push to a container registry |
| **CI/CD** | Manual `git push` and run locally | Configure **GitHub Actions** to lint, test, build Docker image, and deploy to a cloud platform (e.g., Azure App Service, AWS ECS) |
| **Static Frontend Hosting** | Served via FastAPI `StaticFiles` mount (`/frontend`) | Consider serving via a CDN (Azure Blob, CloudFront) for performance |
| **Database** | SQLite file (`pricing_ai.db`) in project root | Use **PostgreSQL** in production (set `DATABASE_URL` env var) and enable connection pooling |
| **Secrets Management** | `.env` file locally | Store secrets in **Azure Key Vault**, **AWS Secrets Manager**, or **HashiCorp Vault** |
| **Monitoring** | Basic `logging.INFO` | Integrate **Prometheus** metrics exporter and **Grafana** dashboards |

---

## 7. Data Pipeline & Storage

1. **Upload** – Files saved under `datasets/raw/` with UUID‑prefixed names.
2. **Processing** – Background task reads file, validates, cleans, and writes rows to the `sales_data` table.
3. **Intermediate Results** – Elasticity, forecasting, and recommendation results stored in dedicated tables (`elasticity_analysis`, `forecasting_result`, `pricing_recommendation`).
4. **Processed Artifacts** – Generated PDFs/Excel reports saved under `reports/pdf/` and `reports/excel/`.
5. **Cleanup** – Old raw files can be purged by a scheduled maintenance script (not yet implemented).

**Scalability Considerations**
- Switch to **object storage** (e.g., Azure Blob) for raw uploads to avoid disk bottlenecks.
- Use a **task queue** (Celery + Redis) for heavy pipelines when scaling horizontally.

---

## 8. External Integrations

| Integration | Current Status | Notes |
|---|---|---|
| **LLM / AI services** | Placeholder comment in code (`# LLM integrations`) – not yet wired | Future work could call OpenAI, Azure Cognitive Services for explanations or scenario generation. |
| **Third‑party APIs** | None active | If needed, add thin service wrappers and secure API keys via env vars. |

---

## 9. Infrastructure Assumptions

- **Runtime**: Python 3.12+ (tested on 3.12.0).
- **Hardware**: Minimum 2 CPU cores, 4 GB RAM for development; production should allocate ≥4 cores + 8 GB RAM for ML workloads.
- **Network**: API accessible via HTTPS (TLS termination at reverse proxy or cloud load balancer).
- **Scaling**: Stateless API enables horizontal scaling behind a load balancer.
- **Storage**: Local filesystem for dev; recommended switch to network‑attached storage or cloud bucket for production.

---

## 10. Maturity & Readiness Scores

| Category | Score (0‑10) | Comments |
|---|---|---|
| **Architecture** | 7 | Clean separation of concerns, but lacks containerisation & migration tooling. |
| **Security** | 8 | Strong headers, rate limiting, secret handling; missing CSP nonce & automated dependency scanning. |
| **Performance** | 6 | Synchronous DB ops; background tasks off‑load heavy work but no worker queue. |
| **Scalability** | 5 | Stateless API ready, but file storage and background processing need queuing and object storage. |
| **Maintainability** | 7 | Modular services, but missing Alembic migrations and typed pydantic schemas for all models. |
| **Observability** | 4 | Basic logging only; no metrics, tracing, or health checks. |

**Overall readiness** – **6 / 10**. The core functionality is production‑capable with additional ops tooling (Docker, CI/CD, monitoring, and migration management) the score can reach **9+**.

---

## 11. Recommendations & Next Steps
1. **Add Alembic migrations** for deterministic DB schema evolution.
2. **Dockerise** the entire stack and create a `docker-compose.yml` for dev/prod consistency.
3. Implement **CI/CD pipeline** (GitHub Actions) with linting, unit tests, security scans, and Docker build.
4. Introduce **structured JSON logging** and ship logs to a central service.
5. Deploy **Prometheus exporter** (`fastapi-prometheus`) and Grafana dashboards.
6. Migrate raw file storage to **cloud object storage** (Azure Blob / S3) and use signed URLs for upload/download.
7. Replace background tasks with **Celery + Redis** for reliable retry and scaling.
8. Harden **CSP** with nonces and enable **Subresource Integrity** for CDN assets.
9. Add **OpenAPI security schemes** (`bearerAuth`) to generated docs for easier client integration.
10. Explore **LLM integration** for natural‑language explanations of recommendations.

---

*Prepared by Antigravity – Advanced Agentic Coding*
