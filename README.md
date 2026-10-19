# Employee Attrition Intelligence System 🚀

An end-to-end, AI-powered **Workforce Attrition Analysis Dashboard & Conversational Copilot** built with **React 19**, **Flask**, and **Google Gemini 2.5 Flash**.

Featuring a clean **White & Emerald Green** design system, this platform allows HR leaders to upload any employee CSV dataset and instantly generate predictive flight-risk metrics, 11 interactive visualizations, root-cause diagnostic rankings, and an AI assistant capable of answering questions about the workforce cohort or looking up specific employees by Employee ID.

---

## 🌟 Key Features

* **Instant Dynamic CSV Ingestion**:
  * Drop or upload any workforce CSV to synthesize real-time analytics on the spot.
  * Smart column auto-detection & alias normalizer (`Attrition`, `Department`, `Role`, `MonthlyIncome`, `OverTime`, `Tenure`, etc.).
  * **Clean Initial State**: Starts completely empty without showing pre-existing or default dataset statistics until a CSV is added.
* **Executive KPI Suite**:
  * Total Headcount, Attrition Count, Retention Count, and Overall Turnover Rate.
  * Average Age, Average Monthly Income, Average Tenure, and Highest Flight-Risk Role.
* **11 Interactive Visualizations (Chart.js)**:
  * Department-Wise Attrition Breakdown
  * Job Role Flight Risk
  * Age Cohorts (18-25, 26-35, 36-45, 46-55, 56+)
  * Salary / Income Bands
  * Company Tenure Curves
  * OverTime Impact (Differential turnover)
  * Commute Distance Impact
  * Job & Workplace Environment Satisfaction
  * Work-Life Balance Distributions
  * Stock Option Equity Level
  * Business Travel Frequency
* **Differential Root-Cause Driver Ranking**:
  * Quantifies the percentage-point impact of key flight factors (Overtime, Compensation, Tenure, Satisfaction).
* **High-Risk Employee Watchlist Table**:
  * Searchable, paginated table displaying employees with composite flight-risk scores (≥ 3/8).
* **AttritionAI Copilot (Gemini 2.5 Flash)**:
  * Grounded exclusively in the active dataset's verified metrics to prevent hallucination.
  * **Individual Employee Lookup by ID**: Ask *"Tell me about employee 101"* or *"Is employee #103 likely to leave?"* to receive a complete profile, risk score, triggered factors, and targeted retention recommendations.
  * Seamless offline rule-based fallback if Gemini API is unreachable or rate-limited.
* **One-Click Cohort Demonstrations**:
  * Built-in instant loaders for quick testing with sample cohorts (e.g., 15-employee tech startup cohort, 1,470-employee benchmark dataset).

---

## 🛠️ Tech Stack

* **Frontend**: React 19, Vite, Chart.js, Lucide-React, Modern CSS Variables.
* **Backend**: Python 3, Flask, Pandas, NumPy, Flask-CORS.
* **AI Model**: Google Gemini (`gemini-2.5-flash`, `gemini-flash-latest`) via Google Generative Language API.

---

## 🚀 Getting Started

### 1. Prerequisites
* Python 3.10+
* Node.js 18+ and npm
* (Optional) Google Gemini API Key from [Google AI Studio](https://aistudio.google.com/)

### 2. Backend Setup
```bash
# Navigate to project root
cd employee_attrition

# Install Python dependencies
pip install -r backend/requirements.txt

# Configure Gemini API key (optional for AI chat)
cp backend/.env.example backend/.env
# Edit backend/.env and insert your GEMINI_API_KEY

# Start Flask backend server (runs on port 5000)
python -m backend.app
```

### 3. Frontend Setup
```bash
# Navigate to frontend directory
cd frontend

# Install npm dependencies
npm install

# Start Vite development server (runs on port 3000)
npm run dev
```

Visit **`http://localhost:3000`** in your browser.

---

## 📂 Project Structure

```
employee_attrition/
├── backend/
│   ├── api/
│   │   ├── chatbot_routes.py     # Chatbot message endpoint
│   │   └── dashboard_routes.py   # REST APIs for KPIs, charts, filters, upload, employee lookup
│   ├── analytics_engine.py       # Pre-computation, risk scoring, factor analysis, employee queries
│   ├── chatbot_engine.py         # Grounded Gemini copilot & rule-based engine
│   ├── data_loader.py            # Dynamic CSV parser, schema normalizer, state singleton
│   ├── requirements.txt          # Python dependencies
│   └── app.py                    # Flask application entry point
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── Header.jsx        # Dynamic header, status pills, upload & reset actions
│   │   │   ├── UploadHero.jsx    # Clean empty-state landing & dropzone
│   │   │   ├── AiInsightsBanner.jsx # On-the-spot Gemini executive summary
│   │   │   ├── KpiCards.jsx      # 6 KPI metric cards
│   │   │   ├── FilterBar.jsx     # Multidimensional filter controls
│   │   │   ├── ChartsGrid.jsx    # 11 interactive Chart.js charts
│   │   │   ├── HighRiskTable.jsx # High-risk employee watchlist table
│   │   │   ├── ChatbotDrawer.jsx # Slide-out AttritionAI copilot
│   │   │   └── UploadModal.jsx   # CSV upload dialog
│   │   ├── api.js                # Frontend API client
│   │   ├── App.jsx               # Main React application
│   │   └── index.css             # White & Emerald Green design system
│   ├── package.json
│   └── vite.config.js
├── data/
│   └── WA_Fn-UseC_-HR-Employee-Attrition.csv # Benchmark IBM HR dataset
├── .gitignore                    # Git ignore file (excludes secrets, uploads, cache)
└── README.md
```

---

## 📄 License
MIT License.
