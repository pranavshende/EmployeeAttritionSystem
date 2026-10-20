# How AttritionAI Finds & Predicts the Attrition Percentage

This document outlines the end-to-end architecture, mathematical formulas, and AI workflows used by the **Employee Attrition Intelligence System** to compute attrition percentages and predict employee flight risks.

---

## 1. Core Architectural Philosophy: Deterministic Grounding

To prevent Large Language Models (LLMs) from hallucinating mathematical calculations, the system separates **exact statistical computing** from **cognitive reasoning & explanation**:

```
 ┌──────────────────────┐      ┌─────────────────────────────┐      ┌──────────────────────────┐
 │  Uploaded Workforce  │ ───► │  Deterministic Analytics    │ ───► │   Grounded Gemini AI     │
 │       CSV Data       │      │  (Pandas / Vectorized Math) │      │  (Gemini 2.5 Flash + RAG)│
 └──────────────────────┘      └─────────────────────────────┘      └──────────────────────────┘
                                   │                                     │
                                   ▼                                     ▼
                            Exact 16.2% Rate,                     Root-Cause Insight,
                            8-Factor Risk Scores,                 Flight-Risk Explanations,
                            Cohort Disaggregations                Targeted Action Plans
```

1. **Deterministic Core:** Pandas & NumPy calculate all rates, sums, medians, and correlations with 100% mathematical precision.
2. **Cognitive Layer:** Google Gemini 2.5 Flash receives verified calculations and produces contextual explanations, root-cause analyses, and retention interventions.

---

## 2. Ingestion & Column Auto-Detection

When a dataset is uploaded, `backend/data_loader.py` uses alias mapping to normalize heterogeneous column names:

- **Target Column Aliases Checked:** `attrition`, `left`, `churn`, `turnover`, `is_left`, `resigned`, `terminated`, `status`, `exit`.
- **Target Value Normalization:**
  Departure signals (`"Yes"`, `"1"`, `True`, `"Left"`, `"Resigned"`, `"Terminated"`) are converted into a binary flag:
  $$\text{AttritionFlag} \in \{0, 1\}$$
  Where:
  - $1 = \text{Departed Employee}$
  - $0 = \text{Retained Employee}$

---

## 3. Attrition Rate Calculation Formula

### 3.1 Overall Company Attrition Rate

The overall turnover percentage is calculated as the ratio of historical departures to total headcount:

$$\text{Attrition Rate (\%)} = \left( \frac{\sum_{i=1}^{N} \text{AttritionFlag}_i}{N} \right) \times 100 = \left( \frac{\text{Attrition Count}}{\text{Total Headcount}} \right) \times 100$$

#### Implementation in Code:
```python
# backend/data_loader.py
TOTAL_EMPLOYEES = len(df)
ATTRITION_COUNT = int(df["AttritionFlag"].sum())
RETENTION_COUNT = TOTAL_EMPLOYEES - ATTRITION_COUNT
ATTRITION_RATE = round((ATTRITION_COUNT / TOTAL_EMPLOYEES) * 100, 2) if TOTAL_EMPLOYEES > 0 else 0.0
```

---

### 3.2 Cohort & Segment Disaggregation

The exact same mathematical formula is disaggregated across dimensional slices (Departments, Roles, Age Bands, Income Tiers, Tenure Groups):

$$\text{Cohort Attrition Rate (\%)} = \left( \frac{\sum \text{AttritionFlag}_{\text{Cohort}}}{\text{Total Headcount}_{\text{Cohort}}} \right) \times 100$$

#### Implementation in Code:
```python
# backend/analytics_engine.py
grouped = df.groupby(column).agg(
    total=("AttritionFlag", "size"),
    attrition=("AttritionFlag", "sum")
).reset_index()
grouped["retention"] = grouped["total"] - grouped["attrition"]
grouped["rate"] = (grouped["attrition"] / grouped["total"].replace(0, 1) * 100).round(2)
```

---

## 4. 8-Factor Predictive Flight-Risk Scoring

For currently active employees, the system computes an empirical **Flight-Risk Score (0 to 8)** based on validated organizational turnover drivers:

| # | Risk Factor | Trigger Condition | Points | Rationale |
| :-: | :--- | :--- | :-: | :--- |
| **1** | **Overtime Pressure** | `OverTime == "Yes"` | **+1** | Employees on regular overtime exhibit ~3x higher attrition. |
| **2** | **Compensation Risk** | Bottom quartile or $< ₹5,000/\text{mo}$ | **+1** | Below-market pay creates acute flight sensitivity. |
| **3** | **Early Tenure Cliff** | $\le 2$ years at company | **+1** | First 24 months are historically highest turnover window. |
| **4** | **Low Job Satisfaction** | Rating $\le 2 / 4$ | **+1** | Direct indicator of disengagement. |
| **5** | **Environment Friction** | Rating $\le 2 / 4$ | **+1** | Dissatisfaction with workplace culture or management. |
| **6** | **Zero Equity Alignment** | `StockOptionLevel == 0` | **+1** | Lack of long-term financial lock-in or incentive. |
| **7** | **Early Career Cohort** | $\text{Age} \le 25$ | **+1** | Junior demographic has highest external mobility. |
| **8** | **Work-Life Imbalance** | Rating $1 / 4$ | **+1** | Immediate driver of burnout and abrupt resignations. |

### Mathematical Formulation
$$\text{RiskScore}_i = \sum_{k=1}^{8} \mathbb{I}(\text{Condition}_{i, k})$$

### Classification Tiers:
- **🟢 Low Risk:** $0 - 2$ points (Healthy retention profile)
- **🟡 Medium Risk:** $3 - 4$ points (Monitor workload and engagement)
- **🔴 High Risk:** $\ge 5$ points (Immediate intervention required; routed to Watchlist)

---

## 5. Differential Factor Impact (Root-Cause Analysis)

To identify *which specific issues* drive turnover in a cohort, the engine calculates the **differential percentage-point impact ($\Delta\text{pp}$)**:

$$\Delta\text{pp} = \text{Attrition Rate}_{\text{High-Risk Group}} - \text{Attrition Rate}_{\text{Low-Risk Group}}$$

### Benchmark Example:
- **Overtime Cohort Turnover:** $30.5\%$
- **Standard Hours Turnover:** $10.4\%$
- **Differential Impact:** $+20.1\text{pp}$ (Ranked as the #1 primary turnover driver)

---

## 6. How Gemini 2.5 Flash Uses This Data

When an HR leader asks a question in the **AttritionAI Copilot**:

1. **Semantic Routing & Intent Parsing:**
   `backend/chatbot_engine.py` determines whether the question is asking for global KPIs, department deep-dives, specific employee lookups, or root-cause factors.
2. **Deterministic Context Injection:**
   The exact numerical results from Pandas (e.g., `16.2% overall rate`, `Sales at 20.6%`, `Overtime impact +20.1pp`) are formatted into the LLM system prompt.
3. **Grounded Synthesis:**
   Gemini 2.5 Flash explains the results in executive language, diagnoses the root causes, and generates actionable retention playbooks (e.g., 5-day manager check-ins, workload caps, and compensation adjustments) with **zero mathematical hallucination**.
