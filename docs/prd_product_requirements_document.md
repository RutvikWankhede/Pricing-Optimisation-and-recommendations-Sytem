# Product Requirements Document (PRD)
## Project: PriceSense Analytics (ML-Based Pricing Optimization & Recommendation System)

---

## 1. Project Overview
**PriceSense Analytics** is a data-driven pricing optimization and recommendation system designed as an advanced undergraduate/graduate minor project. The system allows retail managers, e-commerce sellers, and business analysts to upload historical transaction datasets, clean and process the data, analyze sales revenue KPIs, forecast future consumer demand using machine learning, compute price elasticity of demand, simulate pricing scenarios, and generate actionable optimization recommendations. The goal is to maximize either total revenue or gross profit through optimal pricing recommendations.

---

## 2. Problem Statement
Many small-to-medium e-commerce businesses and retailers set product prices based on intuition, static cost-plus margins, or basic competitor tracking. They fail to understand how changes in price affect consumer demand (price elasticity) and how pricing adjustments impact overall revenues and margins. While enterprise-grade pricing optimization systems exist, they are overly complex, expensive, and require extensive infrastructure. There is a need for a lightweight, accessible, yet analytically rigorous tool that lets users upload historical sales data and instantly obtain ML-driven demand forecasts, elasticity values, and pricing recommendations.

---

## 3. Objectives & Goals
* **Democratize Data-Driven Pricing**: Build a clean, self-contained dashboard that translates raw sales data into actionable price recommendations without needing complex setups.
* **Integrate Machine Learning and Economics**: Combine regression-based demand forecasting (using Scikit-Learn) with microeconomic concepts of price elasticity of demand (PED).
* **Maximize Efficacy & Margin**: Provide a pricing simulator where users can run "what-if" scenarios to visualize predicted demand and profitability shifts before applying prices.
* **Resume & GitHub-Ready**: Package the codebase clearly, adhering to industry standards (FastAPI backend structure, SQLite database, dynamic Tailwind CSS frontend) so it serves as an excellent academic showcase.

---

## 4. Target Users
* **Retail & E-commerce Merchants**: Small-to-medium merchants looking to optimize their pricing strategies to boost profits or sales volume.
* **Business Analysts & Researchers**: Academic users and business students analyzing demand trends, price elasticity curves, and sales forecasting algorithms.

---

## 5. Core Features

### 5.1 Dataset Upload & Ingestion
* **Format Support**: Users can upload `.csv`, `.xls`, or `.xlsx` files.
* **Flexible Schemas**: Automatic mapping of common column aliases (e.g., mapping `Qty`, `units`, or `quantity_sold` to a standard field `units_sold`).
* **Background Ingestion**: Backend accepts uploads, validates rows, and initiates cleaning and database insertion asynchronously.

### 5.2 Data Validation & Cleaning
* **Validation Rules**: Check for missing columns, verify positive prices and non-negative quantities, validate correct date formats, and filter out highly anomalous outliers.
* **Auto-Correction**: Missing categories default to `"General"`, missing regions default to `"National"`, and revenue is automatically calculated or corrected as `price * units_sold`.
* **Database Persistency**: Sanitized rows are bulk-saved to SQLite tables for further queries.

### 5.3 Revenue Analytics Dashboard
* **Key KPI Cards**: Display Total Revenue, Total Profit, Average Profit Margin (%), and Active Products.
* **Trend Visualizations**: Time-series charts displaying monthly/weekly revenue and profit trends.
* **Segment Breakdown**: Bar and pie charts representing revenue split across product categories and geographic regions.
* **Top-Performing Products Table**: Sortable overview of items generating the highest revenue, profit, and volume.

### 5.4 Demand Forecasting
* **ML Model Training**: Automatic training of regression models (e.g., Linear Regression, Random Forest) on historical sales volume, prices, and time-based features (month, day of week).
* **Demand Prediction**: Generate a 30-day forecast of units sold for selected products under current prices.
* **Confidence & Metrics**: Expose the model's prediction confidence metrics (such as $R^2$ score).

### 5.5 Elasticity Analysis
* **Elasticity Coefficient Calculation**: Calculate the price elasticity of demand (PED) for each product using log-log regression coefficients or price/quantity variations:
  $$\text{PED} = \frac{\% \Delta Q}{\% \Delta P}$$
* **Classification**: Categorize products as **Elastic** (PED < -1), **Inelastic** (0 > PED > -1), or **Unitary** (PED = -1).
* **Interactive Demand Curves**: Scatter plots of historical price-quantity points overlaid with the calculated demand curve.

### 5.6 Pricing Recommendations
* **Optimization Goal**: Maximize Revenue or Maximize Profit based on product-specific price elasticity.
* **Optimal Price Suggestions**: Recommend optimal price points for each product.
* **Impact Estimations**: Project percentage shifts in revenue and profit if recommended prices are adopted.
* **Written Justifications**: Textual explanation detailing why the price change is recommended (e.g., "Product is highly elastic; lowering price by 5% is expected to boost sales volume by 12%, growing revenue by 6.4%").

### 5.7 Scenario Simulation (What-If Analysis)
* **Interactive Slider**: Allow users to drag a slider to adjust a product's price from -50% to +50% of the current value.
* **Live Calculation**: Instantly compute the expected demand, revenue, and profit at that simulated price point.
* **Visual Comparison**: Side-by-side KPI card comparison of "Current" vs "Simulated" metrics.

### 5.8 PDF/Excel Export
* **Summary Business Brief (PDF)**: Generate a clean, structured PDF report containing top-performing product charts, high-level KPIs, and optimization recommendations.
* **Detailed Data Sheet (Excel)**: Export pricing recommendations and historical analytics using formatted spreadsheets for spreadsheet offline use.

---

## 6. Optional Features (Future Scope)
* **Competitor Price Benchmarking**: Ingest competitor prices to recommend pricing relative to market indexes.
* **Promotional Pricing Calendar**: Suggest optimal markdown dates and discounts during seasonal dips.
* **Multi-user Workspace Sharing**: Support shared team dashboards and review approvals.

---

## 7. Non-Goals (Out of Scope for Student Project)
* **Enterprise SaaS Multi-tenancy**: No subscription tiers, tenant database isolation, billing integrations, or advanced workspace provisioning.
* **Complex Authentication Systems**: Avoid complex token revocation, OAuth integration, or password reset emails. Keep authentication to a basic local SQLite login/registration setup.
* **AI Agents & LLM Integration**: Avoid OpenAI/Anthropic API integrations, conversational agents, or LLM-based analysis. All recommendations must be strictly derived from mathematical and statistical formulas (Pandas, Scikit-Learn).
* **Microservices & Cloud Native**: Avoid Kubernetes, Docker containers, Redis caching, Celery task queues, and cloud-native services (AWS, GCP, Azure). The system should run locally on a single machine via FastAPI and SQLite.

---

## 8. MVP Scope Boundaries
The system is deemed complete and successful when:
1. A single CSV file can be uploaded and processed without crashing.
2. The UI dashboard updates automatically once database tables are populated.
3. The forecasting model outputs reasonable values, and elasticity is computed for products with at least three distinct price-quantity points.
4. The user can export a generated PDF summary and Excel datasheet to their local machine.
