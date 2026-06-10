# UI/UX Design Brief
## Project: PriceSense Analytics (ML-Based Pricing Optimization & Recommendation System)

---

## 1. Design Philosophy & Tone
The design of **PriceSense Analytics** moves away from heavy enterprise fintech wording, automated AI engine branding, and executive multi-billion-dollar corporate aesthetics. Instead, it embraces a **“modern, student-built ML analytics dashboard”** look: it is clean, highly visual, accessible, and scientifically sound.

The visual approach utilizes a sleek dark-themed workspace with glassmorphic cards and subtle highlight gradients. This layout organizes density so that complex economic relationships (like demand curves and regression scatterplots) are readable, while micro-interactions (hovering over charts, dragging simulation sliders) make the system feel active.

---

## 2. Design System & Theme Tokens

### 2.1 Color Palette
* **Primary Canvas Background**: `#0F172A` (Deep Slate Gray / Dark Mode Background)
* **Sidebar Background**: `#020617` (Rich Dark Indigo/Black for solid navigation contrast)
* **Glass Panels Background**: `rgba(30, 41, 59, 0.7)` with `backdrop-filter: blur(12px)` and border `rgba(255, 255, 255, 0.05)`
* **Primary Accent Color**: `#2563EB` (Cobalt Blue for interactive buttons, tabs, links)
* **Secondary Accent Color**: `#1E3A8A` (Navy Blue for headers, badges, highlights)
* **Success Indicator**: `#10B981` (Emerald Green for price decreases recommendations, revenue gains, upward trend flags)
* **Warning / Danger Indicator**: `#EF4444` (Vibrant Red for price increases, downward trends, processing errors)
* **Muted Text / Sub-headers**: `#94A3B8` (Cool Gray for secondary labels, text metadata)
* **Primary Text**: `#F8FAFC` (Off-white for high-contrast reading)

### 2.2 Typography
* **Primary Font Family**: `Inter`, sans-serif (imported via Google Fonts).
* **Weights**:
  - `300 (Light)`: Data labels and sub-labels.
  - `400 (Regular)`: General descriptions and body paragraphs.
  - `500 (Medium)`: KPI card descriptions and interactive controls.
  - `600 (Semibold)`: Dashboard section titles, table headers, and buttons.
  - `700 (Bold)`: Core KPI numeric values and main branding header.

### 2.3 Layout Grid & Spacing
* **Page Wrapper**: Grid system featuring a left-pinned vertical navigation sidebar (fixed `260px` width) and a flexible, fluid main content area.
* **Content Container**: Padded at `2rem (32px)` with a maximum width of `1600px` to prevent layout stretching on ultra-wide monitors.
* **Card Component Grid**:
  - Single-column for large trend lines and charts.
  - 2-column or 3-column layouts for comparative data metrics (elasticity stats vs demand curve).
  - 4-column rows for the primary KPI dashboard metrics.

---

## 3. Screen-by-Screen Layout & Wireframe Concepts

### 3.1 Persistent Left Sidebar
* **Branding Header**: "PriceSense Analytics" text logo with a mini trendline icon.
* **Profile Card**: Simple analyst profile widget containing name, role (`Analyst`), and active database indicator (SQLite / Local).
* **Navigation Links**:
  - Ingest & Upload
  - Dashboard Overview
  - Demand Forecasting
  - Price Elasticity
  - Pricing Recommendations
  - Scenario Simulation
  - Export Center
* **Action Footer**: Logout button or database reset trigger.

### 3.2 Ingest & Upload View
* **Hero Header**: "Historical Dataset Ingestion" with short, technical instructions.
* **Upload Card**: Large drag-and-drop file interface accepting `.csv` or `.xlsx` formats. Highlights with a dashed border that glows bright blue when files are hovered over.
* **File Upload Table**: Lists recently uploaded files showing Filename, Upload Time, Row Count, and Processing Status (e.g., yellow `"Processing"`, green `"Processed"`, red `"Failed"`).

### 3.3 Dashboard Overview
* **KPI Matrix (4-column row)**:
  1. *Total Revenue*: Calculated absolute revenue with a percentage change indicator.
  2. *Total Profit*: Net profit with a trend flag.
  3. *Gross Profit Margin*: Percentage efficiency card.
  4. *Active SKU Listings*: Total count of distinct products in database.
* **Data Trends (Main Section)**: Interactive dual-line chart showing Revenue vs. Profit progression over time (using Chart.js / Plotly.js).
* **Top Performance Split**: Split layout:
  - *Left Card*: Category share bar chart.
  - *Right Card*: Top 5 products table listing SKU, category, revenue, volume, and unit margins.

### 3.4 Demand Forecasting View
* **Product Select Row**: Searchable dropdown select menu to isolate a specific product ID.
* **Performance Dashboard**: Shows the model's prediction accuracy ($R^2$ score) in a small glass badge.
* **Historical vs. Forecast Chart**: A Plotly.js chart displaying historical units sold in solid blue and the 30-day forecasted demand in a dashed orange line.

### 3.5 Price Elasticity View
* **Elasticity Scoreboard Card**: Shows the calculated coefficient (e.g., `-1.84`), classification classification ("Elastic"), and a brief microeconomic translation text box.
* **Demand Curve Curve Plot**: A scatter plot of historical price-quantity points overlaid with the calculated regression curve $Q = A \cdot P^{PED}$.

### 3.6 Pricing Recommendations & Scenario Simulation
* **Grid recommendations**: Tables summarizing SKU name, current price, recommended price, expected profit change, and recommendation justification.
* **Scenario Slider Panel**:
  - Dropdown to choose product.
  - An interactive slider range (-50% to +50% price change).
  - KPI Comparison Matrix: Displays side-by-side KPI values comparing current values with simulated metrics.

### 3.7 Export Center
* **Export PDF Card**: Large glass card offering "Download Summary Report PDF". Detailed bullet points list what is included in the export (revenue trends, optimization recommendations, Top SKUs).
* **Export Excel Card**: Large glass card offering "Download Historical Sales Ledger". Detailed bullet points list the structured tabs included in the spreadsheet.

---

## 4. Responsive Design Rules
* **Breakpoints**: Standard tailwind utility values:
  - Mobile (`sm: 640px`): Navigation sidebar shifts to a top collapsible slide-out drawer. KPI grid wraps to a single vertical column.
  - Tablet (`md: 768px`): Content padding reduces to `1rem`. Double-column charts stack vertically.
  - Desktop (`lg: 1024px`): Full sidebar is pinned. Grid layouts transition to their multi-column structures.
* **Touch Optimization**: Slide controls, drop-down menus, and button actions maintain a minimum touch target size of `44px` with clear visual feedback states.
