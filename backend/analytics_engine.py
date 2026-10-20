"""
Analytics Engine
Pre-computes all dashboard KPIs, chart data, factor analysis, and high-risk profiles
from the loaded DataFrame. All computations happen at import time for fast API responses.
"""

import logging
import numpy as np
import pandas as pd
from . import data_loader as dl

logger = logging.getLogger(__name__)


def _safe_int(val, default=0):
    if pd.isna(val) or val is None or val == "":
        return default
    try:
        return int(float(val))
    except (ValueError, TypeError):
        return default


def _safe_float(val, default=0.0):
    if pd.isna(val) or val is None or val == "":
        return default
    try:
        return float(val)
    except (ValueError, TypeError):
        return default


def _safe_str(val, default=""):
    if pd.isna(val) or val is None:
        return default
    return str(val).strip()


def _attrition_breakdown(group_col, label_col=None):
    """Generic helper: compute attrition count, total, and rate grouped by a column."""
    if dl.df is None or len(dl.df) == 0 or group_col not in dl.df.columns or "AttritionFlag" not in dl.df.columns:
        return []
    col = label_col if label_col and label_col in dl.df.columns else group_col
    grouped = dl.df.groupby(col).agg(
        total=("AttritionFlag", "size"),
        attrition=("AttritionFlag", "sum"),
    ).reset_index()
    grouped["retention"] = grouped["total"] - grouped["attrition"]
    denom = grouped["total"].replace(0, 1)
    grouped["rate"] = (grouped["attrition"] / denom * 100).round(2)
    grouped = grouped.rename(columns={col: "label"})
    grouped["label"] = grouped["label"].astype(str)
    return grouped.sort_values("rate", ascending=False).to_dict(orient="records")


def _band_breakdown(band_col):
    """Compute attrition breakdown for pre-computed band columns."""
    if dl.df is None or len(dl.df) == 0 or band_col not in dl.df.columns or "AttritionFlag" not in dl.df.columns:
        return []
    grouped = dl.df.groupby(band_col, observed=True).agg(
        total=("AttritionFlag", "size"),
        attrition=("AttritionFlag", "sum"),
    ).reset_index()
    grouped["retention"] = grouped["total"] - grouped["attrition"]
    denom = grouped["total"].replace(0, 1)
    grouped["rate"] = (grouped["attrition"] / denom * 100).round(2)
    grouped = grouped.rename(columns={band_col: "label"})
    grouped["label"] = grouped["label"].astype(str)
    return grouped.to_dict(orient="records")


# ──────────────────────────────────────────────
#  KPI Metrics
# ──────────────────────────────────────────────

def get_kpis():
    """Top-level KPI metrics for the dashboard header cards."""
    if dl.df is None or len(dl.df) == 0:
        return {
            "has_data": False,
            "total_employees": 0,
            "attrition_count": 0,
            "retention_count": 0,
            "attrition_rate": 0.0,
            "avg_age": 0,
            "avg_monthly_income": 0,
            "avg_years_at_company": 0,
            "overtime_attrition_rate": 0.0,
            "no_overtime_attrition_rate": 0.0,
            "highest_risk_role": {"role": "N/A", "rate": 0.0, "count": 0, "total": 0},
        }

    avg_age = round(float(dl.df["Age"].mean()), 1) if "Age" in dl.df.columns else 0
    avg_income = round(float(dl.df["MonthlyIncome"].mean()), 0) if "MonthlyIncome" in dl.df.columns else 0
    avg_tenure = round(float(dl.df["YearsAtCompany"].mean()), 1) if "YearsAtCompany" in dl.df.columns else 0

    ot_rate = 0.0
    no_ot_rate = 0.0
    if "OvertimeFlag" in dl.df.columns and "AttritionFlag" in dl.df.columns:
        ot_mask = dl.df["OvertimeFlag"]
        if ot_mask.sum() > 0:
            ot_rate = round(float(dl.df[ot_mask]["AttritionFlag"].mean() * 100), 1)
        if (~ot_mask).sum() > 0:
            no_ot_rate = round(float(dl.df[~ot_mask]["AttritionFlag"].mean() * 100), 1)

    return {
        "has_data": True,
        "total_employees": dl.TOTAL_EMPLOYEES,
        "attrition_count": dl.ATTRITION_COUNT,
        "retention_count": dl.RETENTION_COUNT,
        "attrition_rate": dl.ATTRITION_RATE,
        "avg_age": avg_age,
        "avg_monthly_income": avg_income,
        "avg_years_at_company": avg_tenure,
        "overtime_attrition_rate": ot_rate,
        "no_overtime_attrition_rate": no_ot_rate,
        "highest_risk_role": _get_highest_risk_role(),
    }



def _get_highest_risk_role():
    """Find the job role with the highest attrition rate."""
    if dl.df is None or len(dl.df) == 0 or "JobRole" not in dl.df.columns or "AttritionFlag" not in dl.df.columns:
        return {"role": "N/A", "rate": 0.0, "count": 0, "total": 0}
    role_data = dl.df.groupby("JobRole").agg(
        total=("AttritionFlag", "size"),
        attrition=("AttritionFlag", "sum"),
    ).reset_index()
    if len(role_data) == 0 or role_data["total"].sum() == 0:
        return {"role": "N/A", "rate": 0.0, "count": 0, "total": 0}
    role_data["rate"] = (role_data["attrition"] / role_data["total"] * 100).round(1)
    highest = role_data.loc[role_data["rate"].idxmax()]
    return {
        "role": str(highest["JobRole"]),
        "rate": float(highest["rate"]),
        "count": int(highest["attrition"]),
        "total": int(highest["total"]),
    }


# ──────────────────────────────────────────────
#  Chart Breakdowns
# ──────────────────────────────────────────────

def get_department_data():
    return _attrition_breakdown("Department")

def get_job_role_data():
    return _attrition_breakdown("JobRole")

def get_age_data():
    return _band_breakdown("AgeBand")

def get_income_data():
    return _band_breakdown("IncomeBand")

def get_tenure_data():
    return _band_breakdown("TenureBand")

def get_distance_data():
    return _band_breakdown("DistanceBand")

def get_overtime_data():
    return _attrition_breakdown("OverTime")

def get_gender_data():
    return _attrition_breakdown("Gender")

def get_marital_data():
    return _attrition_breakdown("MaritalStatus")

def get_travel_data():
    return _attrition_breakdown("BusinessTravel")

def get_education_data():
    return _attrition_breakdown("Education", "EducationLabel")

def get_education_field_data():
    return _attrition_breakdown("EducationField")

def get_stock_options_data():
    return _attrition_breakdown("StockOptionLevel")

def get_satisfaction_data():
    """Combined job satisfaction and environment satisfaction."""
    job_sat = _attrition_breakdown("JobSatisfaction", "JobSatisfactionLabel")
    env_sat = _attrition_breakdown("EnvironmentSatisfaction", "EnvSatisfactionLabel")
    return {
        "job_satisfaction": job_sat,
        "env_satisfaction": env_sat,
        "environment_satisfaction": env_sat,
    }

def get_work_life_balance_data():
    return _attrition_breakdown("WorkLifeBalance", "WorkLifeBalanceLabel")


# ──────────────────────────────────────────────
#  Contributing Factors Analysis
# ──────────────────────────────────────────────

def get_contributing_factors():
    """Rank factors by their differential impact on attrition rate."""
    if dl.df is None or len(dl.df) == 0:
        return []

    factors = []

    # OverTime
    if "OvertimeFlag" in dl.df.columns and "AttritionFlag" in dl.df.columns:
        ot_mask = dl.df["OvertimeFlag"]
        if ot_mask.sum() > 0 and (~ot_mask).sum() > 0:
            ot_yes = float(dl.df[ot_mask]["AttritionFlag"].mean() * 100)
            ot_no = float(dl.df[~ot_mask]["AttritionFlag"].mean() * 100)
            diff = round(ot_yes - ot_no, 1)
            factors.append({
                "factor": "OverTime",
                "high_risk_group": "Yes",
                "high_risk_cohort": "Yes",
                "high_risk_rate": round(ot_yes, 1),
                "low_risk_group": "No",
                "low_risk_cohort": "No",
                "low_risk_rate": round(ot_no, 1),
                "impact": diff,
                "impact_pp": diff,
                "description": f"Employees working overtime leave at {round(ot_yes, 1)}% vs {round(ot_no, 1)}%",
            })

    # Income (adaptive percentiles or <=5k / >15k)
    if "MonthlyIncome" in dl.df.columns and "AttritionFlag" in dl.df.columns:
        inc_max = float(dl.df["MonthlyIncome"].max()) if len(dl.df) > 0 else 0
        if inc_max <= 25000:
            low_inc_mask = dl.df["MonthlyIncome"] <= 5000
            high_inc_mask = dl.df["MonthlyIncome"] > 15000
            low_label = "≤ ₹5,000"
            high_label = "> ₹15,000"
        else:
            q25 = float(dl.df["MonthlyIncome"].quantile(0.25))
            q75 = float(dl.df["MonthlyIncome"].quantile(0.75))
            low_inc_mask = dl.df["MonthlyIncome"] <= q25
            high_inc_mask = dl.df["MonthlyIncome"] >= q75
            low_label = f"≤ ₹{int(q25):,}"
            high_label = f"≥ ₹{int(q75):,}"

        if low_inc_mask.sum() > 0 and high_inc_mask.sum() > 0:
            low_inc = float(dl.df[low_inc_mask]["AttritionFlag"].mean() * 100)
            high_inc = float(dl.df[high_inc_mask]["AttritionFlag"].mean() * 100)
            diff = round(low_inc - high_inc, 1)
            factors.append({
                "factor": "Monthly Income",
                "high_risk_group": low_label,
                "high_risk_cohort": low_label,
                "high_risk_rate": round(low_inc, 1),
                "low_risk_group": high_label,
                "low_risk_cohort": high_label,
                "low_risk_rate": round(high_inc, 1),
                "impact": diff,
                "impact_pp": diff,
                "description": f"Low-income cohort leaves at {round(low_inc, 1)}% vs high-income at {round(high_inc, 1)}%",
            })

    # Tenure
    if "YearsAtCompany" in dl.df.columns and "AttritionFlag" in dl.df.columns:
        nh_mask = dl.df["YearsAtCompany"] <= 2
        vet_mask = dl.df["YearsAtCompany"] >= 11
        if nh_mask.sum() > 0 and vet_mask.sum() > 0:
            new_hire = float(dl.df[nh_mask]["AttritionFlag"].mean() * 100)
            veteran = float(dl.df[vet_mask]["AttritionFlag"].mean() * 100)
            diff = round(new_hire - veteran, 1)
            factors.append({
                "factor": "Company Tenure",
                "high_risk_group": "0-2 years",
                "high_risk_cohort": "0-2 years",
                "high_risk_rate": round(new_hire, 1),
                "low_risk_group": "11+ years",
                "low_risk_cohort": "11+ years",
                "low_risk_rate": round(veteran, 1),
                "impact": diff,
                "impact_pp": diff,
                "description": f"New hires (0-2 yrs) leave at {round(new_hire, 1)}% vs veterans at {round(veteran, 1)}%",
            })

    # Stock options
    if "StockOptionLevel" in dl.df.columns and "AttritionFlag" in dl.df.columns:
        no_s_mask = dl.df["StockOptionLevel"] == 0
        has_s_mask = dl.df["StockOptionLevel"] >= 1
        if no_s_mask.sum() > 0 and has_s_mask.sum() > 0:
            no_stock = float(dl.df[no_s_mask]["AttritionFlag"].mean() * 100)
            has_stock = float(dl.df[has_s_mask]["AttritionFlag"].mean() * 100)
            diff = round(no_stock - has_stock, 1)
            factors.append({
                "factor": "Stock Options",
                "high_risk_group": "Level 0 (None)",
                "high_risk_cohort": "Level 0 (None)",
                "high_risk_rate": round(no_stock, 1),
                "low_risk_group": "Level 1+",
                "low_risk_cohort": "Level 1+",
                "low_risk_rate": round(has_stock, 1),
                "impact": diff,
                "impact_pp": diff,
                "description": f"No stock options: {round(no_stock, 1)}% vs with options: {round(has_stock, 1)}%",
            })

    # Job Satisfaction
    if "JobSatisfaction" in dl.df.columns and "AttritionFlag" in dl.df.columns:
        l_sat_mask = dl.df["JobSatisfaction"] == 1
        h_sat_mask = dl.df["JobSatisfaction"] == 4
        if l_sat_mask.sum() > 0 and h_sat_mask.sum() > 0:
            low_sat = float(dl.df[l_sat_mask]["AttritionFlag"].mean() * 100)
            high_sat = float(dl.df[h_sat_mask]["AttritionFlag"].mean() * 100)
            diff = round(low_sat - high_sat, 1)
            factors.append({
                "factor": "Job Satisfaction",
                "high_risk_group": "Level 1 (Low)",
                "high_risk_cohort": "Level 1 (Low)",
                "high_risk_rate": round(low_sat, 1),
                "low_risk_group": "Level 4 (Very High)",
                "low_risk_cohort": "Level 4 (Very High)",
                "low_risk_rate": round(high_sat, 1),
                "impact": diff,
                "impact_pp": diff,
                "description": f"Low satisfaction: {round(low_sat, 1)}% vs very high: {round(high_sat, 1)}%",
            })

    # Environment Satisfaction
    if "EnvironmentSatisfaction" in dl.df.columns and "AttritionFlag" in dl.df.columns:
        l_env_mask = dl.df["EnvironmentSatisfaction"] == 1
        h_env_mask = dl.df["EnvironmentSatisfaction"] == 4
        if l_env_mask.sum() > 0 and h_env_mask.sum() > 0:
            low_env = float(dl.df[l_env_mask]["AttritionFlag"].mean() * 100)
            high_env = float(dl.df[h_env_mask]["AttritionFlag"].mean() * 100)
            diff = round(low_env - high_env, 1)
            factors.append({
                "factor": "Environment Satisfaction",
                "high_risk_group": "Level 1 (Low)",
                "high_risk_cohort": "Level 1 (Low)",
                "high_risk_rate": round(low_env, 1),
                "low_risk_group": "Level 4 (Very High)",
                "low_risk_cohort": "Level 4 (Very High)",
                "low_risk_rate": round(high_env, 1),
                "impact": diff,
                "impact_pp": diff,
                "description": f"Low env satisfaction: {round(low_env, 1)}% vs very high: {round(high_env, 1)}%",
            })

    # Age
    if "Age" in dl.df.columns and "AttritionFlag" in dl.df.columns:
        y_mask = dl.df["Age"] <= 25
        o_mask = (dl.df["Age"] >= 36) & (dl.df["Age"] <= 45)
        if y_mask.sum() > 0 and o_mask.sum() > 0:
            young = float(dl.df[y_mask]["AttritionFlag"].mean() * 100)
            older = float(dl.df[o_mask]["AttritionFlag"].mean() * 100)
            diff = round(young - older, 1)
            factors.append({
                "factor": "Age Group",
                "high_risk_group": "18-25",
                "high_risk_cohort": "18-25",
                "high_risk_rate": round(young, 1),
                "low_risk_group": "36-45",
                "low_risk_cohort": "36-45",
                "low_risk_rate": round(older, 1),
                "impact": diff,
                "impact_pp": diff,
                "description": f"Young employees (18-25): {round(young, 1)}% vs mid-career (36-45): {round(older, 1)}%",
            })

    # Distance from home
    if "DistanceFromHome" in dl.df.columns and "AttritionFlag" in dl.df.columns:
        f_mask = dl.df["DistanceFromHome"] >= 16
        n_mask = dl.df["DistanceFromHome"] <= 5
        if f_mask.sum() > 0 and n_mask.sum() > 0:
            far = float(dl.df[f_mask]["AttritionFlag"].mean() * 100)
            near = float(dl.df[n_mask]["AttritionFlag"].mean() * 100)
            diff = round(far - near, 1)
            factors.append({
                "factor": "Distance from Home",
                "high_risk_group": "16+ miles",
                "high_risk_cohort": "16+ miles",
                "high_risk_rate": round(far, 1),
                "low_risk_group": "0-5 miles",
                "low_risk_cohort": "0-5 miles",
                "low_risk_rate": round(near, 1),
                "impact": diff,
                "impact_pp": diff,
                "description": f"Long commute (16+ mi): {round(far, 1)}% vs nearby (0-5 mi): {round(near, 1)}%",
            })

    # Work-life balance
    if "WorkLifeBalance" in dl.df.columns and "AttritionFlag" in dl.df.columns:
        l_wlb_mask = dl.df["WorkLifeBalance"] == 1
        h_wlb_mask = dl.df["WorkLifeBalance"] == 4
        if l_wlb_mask.sum() > 0 and h_wlb_mask.sum() > 0:
            low_wlb = float(dl.df[l_wlb_mask]["AttritionFlag"].mean() * 100)
            high_wlb = float(dl.df[h_wlb_mask]["AttritionFlag"].mean() * 100)
            diff = round(low_wlb - high_wlb, 1)
            factors.append({
                "factor": "Work-Life Balance",
                "high_risk_group": "Level 1 (Bad)",
                "high_risk_cohort": "Level 1 (Bad)",
                "high_risk_rate": round(low_wlb, 1),
                "low_risk_group": "Level 4 (Best)",
                "low_risk_cohort": "Level 4 (Best)",
                "low_risk_rate": round(high_wlb, 1),
                "impact": diff,
                "impact_pp": diff,
                "description": f"Bad balance: {round(low_wlb, 1)}% vs best balance: {round(high_wlb, 1)}%",
            })

    # Sort by impact descending
    factors.sort(key=lambda x: x["impact"], reverse=True)
    return factors


# ──────────────────────────────────────────────
#  High-Risk Employees
# ──────────────────────────────────────────────

def get_high_risk_employees(min_risk_score=3, page=1, per_page=20):
    """Return employees matching >= min_risk_score criteria with resilient string ID support."""
    if dl.df is None or len(dl.df) == 0:
        return {
            "employees": [],
            "total": 0,
            "total_count": 0,
            "page": page,
            "per_page": per_page,
            "total_pages": 1,
        }

    score_col = "RiskScore" if "RiskScore" in dl.df.columns else None
    if score_col:
        high_risk = dl.df[dl.df[score_col] >= min_risk_score].copy()
        if len(high_risk) == 0:
            # Fallback to top-risk employees if none reach the threshold
            high_risk = dl.df.sort_values(score_col, ascending=False).head(100).copy()
        else:
            high_risk = high_risk.sort_values(score_col, ascending=False)
    else:
        high_risk = dl.df.copy()

    total = len(high_risk)
    start = (page - 1) * per_page
    end = start + per_page
    page_data = high_risk.iloc[start:end]

    employees = []
    for _, row in page_data.iterrows():
        factors_matched = []
        if str(row.get("OverTime", "")).lower() in ["yes", "true", "1"]:
            factors_matched.append("OverTime")
        if _safe_float(row.get("MonthlyIncome", 0)) < 5000:
            factors_matched.append("Low Income")
        if _safe_int(row.get("YearsAtCompany", 0)) <= 2:
            factors_matched.append("Tenure ≤2 yrs")
        if _safe_int(row.get("JobSatisfaction", 3)) <= 2:
            factors_matched.append("Low Job Sat")
        if _safe_int(row.get("EnvironmentSatisfaction", 3)) <= 2:
            factors_matched.append("Low Env Sat")
        if _safe_int(row.get("StockOptionLevel", 0)) == 0:
            factors_matched.append("Zero Stock")
        if _safe_int(row.get("Age", 0)) <= 25 and _safe_int(row.get("Age", 0)) > 0:
            factors_matched.append("Age ≤25")
        if _safe_int(row.get("WorkLifeBalance", 3)) <= 1:
            factors_matched.append("Poor WLB")

        emp_id_val = row.get("EmployeeNumber", row.get("EmployeeID", row.get("id", "N/A")))
        emp_id_str = _safe_str(emp_id_val, "N/A")

        score = _safe_int(row.get("RiskScore", len(factors_matched)), len(factors_matched))
        risk_lvl = _safe_str(row.get("RiskLevel", "High" if score >= 4 else "Medium" if score >= 2 else "Low"), "Low")

        employees.append({
            "employee_number": emp_id_str,
            "age": _safe_int(row.get("Age", 0)),
            "department": _safe_str(row.get("Department", "General")),
            "job_role": _safe_str(row.get("JobRole", "Employee")),
            "monthly_income": _safe_int(row.get("MonthlyIncome", 0)),
            "overtime": _safe_str(row.get("OverTime", "No")),
            "years_at_company": _safe_int(row.get("YearsAtCompany", 0)),
            "job_satisfaction": _safe_int(row.get("JobSatisfaction", 3)),
            "env_satisfaction": _safe_int(row.get("EnvironmentSatisfaction", 3)),
            "stock_option_level": _safe_int(row.get("StockOptionLevel", 0)),
            "risk_score": score,
            "risk_level": risk_lvl,
            "attrition": _safe_str(row.get("Attrition", "No")),
            "matched_factors": factors_matched,
            "risk_reasons": factors_matched,
        })

    return {
        "employees": employees,
        "total": total,
        "total_count": total,
        "page": page,
        "per_page": per_page,
        "total_pages": max(1, (total + per_page - 1) // per_page),
    }


# ──────────────────────────────────────────────
#  Filters
# ──────────────────────────────────────────────

def get_filter_options():
    """Return available filter options for the UI."""
    if dl.df is None or len(dl.df) == 0:
        return {
            "departments": [],
            "job_roles": [],
            "genders": [],
            "marital_statuses": [],
            "education_fields": [],
            "business_travel": [],
            "overtime_options": ["Yes", "No"],
            "age_range": {"min": 18, "max": 65},
            "income_range": {"min": 0, "max": 50000},
        }

    return {
        "departments": sorted(dl.df["Department"].dropna().unique().tolist()) if "Department" in dl.df.columns else [],
        "job_roles": sorted(dl.df["JobRole"].dropna().unique().tolist()) if "JobRole" in dl.df.columns else [],
        "genders": sorted(dl.df["Gender"].dropna().unique().tolist()) if "Gender" in dl.df.columns else [],
        "marital_statuses": sorted(dl.df["MaritalStatus"].dropna().unique().tolist()) if "MaritalStatus" in dl.df.columns else [],
        "education_fields": sorted(dl.df["EducationField"].dropna().unique().tolist()) if "EducationField" in dl.df.columns else [],
        "business_travel": sorted(dl.df["BusinessTravel"].dropna().unique().tolist()) if "BusinessTravel" in dl.df.columns else [],
        "overtime_options": ["Yes", "No"],
        "age_range": {
            "min": int(dl.df["Age"].min()) if "Age" in dl.df.columns and len(dl.df["Age"].dropna()) > 0 else 18,
            "max": int(dl.df["Age"].max()) if "Age" in dl.df.columns and len(dl.df["Age"].dropna()) > 0 else 65,
        },
        "income_range": {
            "min": int(dl.df["MonthlyIncome"].min()) if "MonthlyIncome" in dl.df.columns and len(dl.df["MonthlyIncome"].dropna()) > 0 else 0,
            "max": int(dl.df["MonthlyIncome"].max()) if "MonthlyIncome" in dl.df.columns and len(dl.df["MonthlyIncome"].dropna()) > 0 else 50000,
        },
    }


def get_filtered_analytics(filters):
    """Apply filters and return recalculated analytics."""
    if dl.df is None or len(dl.df) == 0:
        return {"total_employees": 0, "attrition_count": 0, "attrition_rate": 0, "charts": {}}

    filtered = dl.df.copy()

    if filters.get("department") and "Department" in filtered.columns:
        filtered = filtered[filtered["Department"] == filters["department"]]
    if filters.get("job_role") and "JobRole" in filtered.columns:
        filtered = filtered[filtered["JobRole"] == filters["job_role"]]
    if filters.get("gender") and "Gender" in filtered.columns:
        filtered = filtered[filtered["Gender"] == filters["gender"]]
    if filters.get("overtime") and "OverTime" in filtered.columns:
        filtered = filtered[filtered["OverTime"] == filters["overtime"]]
    if filters.get("marital_status") and "MaritalStatus" in filtered.columns:
        filtered = filtered[filtered["MaritalStatus"] == filters["marital_status"]]
    if filters.get("age_min") and "Age" in filtered.columns:
        filtered = filtered[filtered["Age"] >= _safe_int(filters["age_min"], 18)]
    if filters.get("age_max") and "Age" in filtered.columns:
        filtered = filtered[filtered["Age"] <= _safe_int(filters["age_max"], 100)]
    if filters.get("income_min") and "MonthlyIncome" in filtered.columns:
        filtered = filtered[filtered["MonthlyIncome"] >= _safe_int(filters["income_min"], 0)]
    if filters.get("income_max") and "MonthlyIncome" in filtered.columns:
        filtered = filtered[filtered["MonthlyIncome"] <= _safe_int(filters["income_max"], 10000000)]

    total = len(filtered)
    if total == 0:
        return {"total_employees": 0, "attrition_count": 0, "attrition_rate": 0, "charts": {}}

    attrition_count = int(filtered["AttritionFlag"].sum()) if "AttritionFlag" in filtered.columns else 0
    attrition_rate = round(attrition_count / total * 100, 2) if total > 0 else 0

    def _breakdown(col):
        if col not in filtered.columns or "AttritionFlag" not in filtered.columns:
            return []
        g = filtered.groupby(col, observed=True).agg(
            total=("AttritionFlag", "size"),
            attrition=("AttritionFlag", "sum"),
        ).reset_index()
        g["retention"] = g["total"] - g["attrition"]
        denom = g["total"].replace(0, 1)
        g["rate"] = (g["attrition"] / denom * 100).round(2)
        g = g.rename(columns={col: "label"})
        g["label"] = g["label"].astype(str)
        return g.to_dict(orient="records")

    avg_age = round(float(filtered["Age"].mean()), 1) if "Age" in filtered.columns else 0
    avg_income = round(float(filtered["MonthlyIncome"].mean()), 0) if "MonthlyIncome" in filtered.columns else 0

    return {
        "total_employees": total,
        "attrition_count": attrition_count,
        "retention_count": total - attrition_count,
        "attrition_rate": attrition_rate,
        "avg_age": avg_age,
        "avg_monthly_income": avg_income,
        "charts": {
            "department": _breakdown("Department"),
            "job_role": _breakdown("JobRole"),
            "age": _breakdown("AgeBand"),
            "income": _breakdown("IncomeBand"),
            "tenure": _breakdown("TenureBand"),
            "overtime": _breakdown("OverTime"),
            "gender": _breakdown("Gender"),
        },
    }


# ──────────────────────────────────────────────
#  Individual Employee Lookup
# ──────────────────────────────────────────────

def _format_employee_record(row):
    """Format a pandas Series row into a comprehensive employee profile dict."""
    risk_reasons = []
    if str(row.get("OverTime", "")).lower() in ("yes", "y", "true", "1"):
        risk_reasons.append("Frequently working overtime hours")
    try:
        if float(row.get("MonthlyIncome", 99999)) <= 5000:
            risk_reasons.append("Low compensation bracket (≤ ₹5,000/mo)")
    except Exception:
        pass
    try:
        if float(row.get("YearsAtCompany", 999)) <= 2:
            risk_reasons.append("Critical early tenure window (0-2 years)")
    except Exception:
        pass
    try:
        if int(row.get("JobSatisfaction", 3)) <= 2:
            risk_reasons.append(f"Low job satisfaction ({row.get('JobSatisfactionLabel', 'Level 1-2')})")
    except Exception:
        pass
    try:
        if int(row.get("EnvironmentSatisfaction", 3)) <= 2:
            risk_reasons.append(f"Low workplace environment satisfaction ({row.get('EnvSatisfactionLabel', 'Level 1-2')})")
    except Exception:
        pass
    try:
        if int(row.get("WorkLifeBalance", 3)) == 1:
            risk_reasons.append("Poor work-life balance (Rating: 1/4)")
    except Exception:
        pass
    try:
        if int(row.get("StockOptionLevel", 1)) == 0:
            risk_reasons.append("No stock equity participation (Level 0)")
    except Exception:
        pass
    try:
        if int(row.get("Age", 99)) <= 25:
            risk_reasons.append("Young employee demographic (≤ 25 yrs) with higher mobility")
    except Exception:
        pass
    try:
        if float(row.get("DistanceFromHome", 0)) >= 16:
            risk_reasons.append("Long commute distance (16+ miles)")
    except Exception:
        pass

    return {
        "employee_number": str(row.get("EmployeeNumber", "N/A")),
        "age": int(row.get("Age", 0)) if pd.notna(row.get("Age")) else "N/A",
        "gender": str(row.get("Gender", "Not Specified")),
        "marital_status": str(row.get("MaritalStatus", "Single")),
        "department": str(row.get("Department", "General")),
        "job_role": str(row.get("JobRole", "Employee")),
        "monthly_income": float(row.get("MonthlyIncome", 0)) if pd.notna(row.get("MonthlyIncome")) else 0,
        "overtime": str(row.get("OverTime", "No")),
        "years_at_company": int(row.get("YearsAtCompany", 0)) if pd.notna(row.get("YearsAtCompany")) else 0,
        "distance_from_home": int(row.get("DistanceFromHome", 0)) if pd.notna(row.get("DistanceFromHome")) else 0,
        "business_travel": str(row.get("BusinessTravel", "Travel_Rarely")),
        "job_satisfaction": int(row.get("JobSatisfaction", 3)) if pd.notna(row.get("JobSatisfaction")) else 3,
        "job_satisfaction_label": str(row.get("JobSatisfactionLabel", "Medium")),
        "env_satisfaction": int(row.get("EnvironmentSatisfaction", 3)) if pd.notna(row.get("EnvironmentSatisfaction")) else 3,
        "env_satisfaction_label": str(row.get("EnvSatisfactionLabel", "Medium")),
        "work_life_balance": int(row.get("WorkLifeBalance", 3)) if pd.notna(row.get("WorkLifeBalance")) else 3,
        "work_life_balance_label": str(row.get("WorkLifeBalanceLabel", "Medium")),
        "stock_option_level": int(row.get("StockOptionLevel", 0)) if pd.notna(row.get("StockOptionLevel")) else 0,
        "risk_score": int(row.get("RiskScore", len(risk_reasons))) if pd.notna(row.get("RiskScore")) else len(risk_reasons),
        "risk_level": str(row.get("RiskLevel", "High" if len(risk_reasons) >= 4 else "Medium" if len(risk_reasons) >= 2 else "Low")),
        "attrition": str(row.get("Attrition", "No")),
        "attrition_flag": bool(row.get("AttritionFlag", False)),
        "risk_reasons": risk_reasons,
    }


def get_employee_by_id(emp_id):
    """
    Look up a specific employee in the active dataset by ID or number.
    Checks EmployeeNumber, EmployeeID, and common identifier columns.
    Falls back to querying the Supabase PostgreSQL database via Prisma if not in memory.
    """
    target = str(emp_id).strip().lower().lstrip("#")
    if not target:
        return None

    # 1. In-memory cohort lookup
    if dl.df is not None and len(dl.df) > 0:
        id_candidates = ["EmployeeNumber", "EmployeeID", "id", "emp_id", "emp_number"]
        cols_to_check = [c for c in id_candidates if c in dl.df.columns]
        
        for col in cols_to_check:
            matches = dl.df[dl.df[col].astype(str).str.strip().str.lower() == target]
            if len(matches) > 0:
                return _format_employee_record(matches.iloc[0])

        if target.isdigit():
            target_int = int(target)
            for col in cols_to_check:
                try:
                    numeric_series = pd.to_numeric(dl.df[col], errors="coerce")
                    matches = dl.df[numeric_series == target_int]
                    if len(matches) > 0:
                        return _format_employee_record(matches.iloc[0])
                except Exception:
                    pass

    # 2. Database Scan: Query Supabase PostgreSQL via Prisma
    try:
        from . import db
        emp_from_db = db.find_employee_in_db(emp_id)
        if emp_from_db:
            return emp_from_db
    except Exception:
        pass

    return None


def get_sample_employee_ids(limit=5):
    """Return a small list of sample employee IDs and roles from the active dataset."""
    if dl.df is None or len(dl.df) == 0:
        return []

    id_col = "EmployeeNumber" if "EmployeeNumber" in dl.df.columns else "EmployeeID" if "EmployeeID" in dl.df.columns else None
    if not id_col:
        return []

    sample_rows = dl.df.head(limit)
    samples = []
    for _, r in sample_rows.iterrows():
        samples.append({
            "id": str(r.get(id_col, "")),
            "role": str(r.get("JobRole", "Employee")),
            "department": str(r.get("Department", "General")),
            "attrition": str(r.get("Attrition", "No")),
        })
    return samples


# ─────────────────────────────────────────────────────────────
#  Full-Dataset Generic Analytical Intelligence Engine
# ─────────────────────────────────────────────────────────────

def resolve_column_name(col_name):
    """Resolve user or query column name to actual DataFrame column using case-insensitive and alias matching."""
    if dl.df is None or not col_name:
        return None
    raw = str(col_name).strip()
    # Direct match
    if raw in dl.df.columns:
        return raw

    cleaned = raw.lower().replace(" ", "").replace("_", "").replace("-", "")
    for col in dl.df.columns:
        if str(col).strip().lower().replace(" ", "").replace("_", "").replace("-", "") == cleaned:
            return col

    # Common semantic aliases
    alias_map = {
        "attrition": "AttritionFlag",
        "attritionrate": "AttritionFlag",
        "turnover": "AttritionFlag",
        "churn": "AttritionFlag",
        "left": "AttritionFlag",
        "salary": "MonthlyIncome",
        "income": "MonthlyIncome",
        "pay": "MonthlyIncome",
        "compensation": "MonthlyIncome",
        "monthlyincome": "MonthlyIncome",
        "role": "JobRole",
        "job": "JobRole",
        "jobrole": "JobRole",
        "position": "JobRole",
        "title": "JobRole",
        "dept": "Department",
        "department": "Department",
        "division": "Department",
        "team": "Department",
        "ot": "OverTime",
        "overtime": "OverTime",
        "extra_hours": "OverTime",
        "tenure": "YearsAtCompany",
        "yearsatcompany": "YearsAtCompany",
        "experience": "YearsAtCompany",
        "commute": "DistanceFromHome",
        "distance": "DistanceFromHome",
        "distancefromhome": "DistanceFromHome",
        "jobsatisfaction": "JobSatisfaction",
        "satisfaction": "JobSatisfaction",
        "environmentsatisfaction": "EnvironmentSatisfaction",
        "envsatisfaction": "EnvironmentSatisfaction",
        "worklifebalance": "WorkLifeBalance",
        "wlb": "WorkLifeBalance",
        "stock": "StockOptionLevel",
        "stockoptions": "StockOptionLevel",
        "stockoptionlevel": "StockOptionLevel",
        "risk": "RiskScore",
        "riskscore": "RiskScore",
        "risklevel": "RiskLevel",
        "age": "Age",
        "gender": "Gender",
        "sex": "Gender",
        "marital": "MaritalStatus",
        "maritalstatus": "MaritalStatus",
        "travel": "BusinessTravel",
        "businesstravel": "BusinessTravel",
    }
    if cleaned in alias_map:
        mapped = alias_map[cleaned]
        if mapped in dl.df.columns:
            return mapped
    return None


def run_aggregation(column, metric="mean"):
    """
    Execute full-dataset aggregation on a column.
    Supported metrics: mean, median, sum, std, min, max, count, nunique, attrition_rate.
    """
    if dl.df is None or len(dl.df) == 0:
        return {"error": "No active dataset loaded."}

    actual_col = resolve_column_name(column)
    if not actual_col:
        return {"error": f"Column '{column}' not found in active dataset."}

    s = dl.df[actual_col]
    total_records = len(dl.df)

    metric_lower = str(metric).lower().strip()

    if metric_lower == "attrition_rate":
        if "AttritionFlag" not in dl.df.columns:
            return {"error": "Target attrition column not found."}
        rate = round(float(dl.df["AttritionFlag"].mean() * 100), 2)
        count = int(dl.df["AttritionFlag"].sum())
        return {
            "operation": "aggregation",
            "column": actual_col,
            "metric": "attrition_rate",
            "value": rate,
            "attrition_count": count,
            "total_records": total_records,
            "formatted": f"{rate}% ({count:,} / {total_records:,} departed)",
        }

    if metric_lower in ("count", "records"):
        val = int(s.count())
        return {"operation": "aggregation", "column": actual_col, "metric": "count", "value": val, "total_records": total_records}

    if metric_lower in ("nunique", "unique_count", "distinct"):
        val = int(s.nunique())
        return {"operation": "aggregation", "column": actual_col, "metric": "nunique", "value": val, "total_records": total_records}

    # Numerical metrics
    if not pd.api.types.is_numeric_dtype(s) and not pd.api.types.is_bool_dtype(s):
        # Fallback to mode or count for non-numeric
        top_val = str(s.mode().iloc[0]) if len(s.dropna()) > 0 else "N/A"
        return {
            "operation": "aggregation",
            "column": actual_col,
            "metric": "mode",
            "value": top_val,
            "note": f"Column '{actual_col}' is categorical. Most frequent value returned.",
            "total_records": total_records,
        }

    s_clean = s.dropna()
    if len(s_clean) == 0:
        return {"error": f"No valid values in column '{actual_col}'."}

    val = 0.0
    if metric_lower in ("mean", "average", "avg"):
        val = round(float(s_clean.mean()), 2)
    elif metric_lower in ("median", "med"):
        val = round(float(s_clean.median()), 2)
    elif metric_lower in ("sum", "total"):
        val = round(float(s_clean.sum()), 2)
    elif metric_lower in ("min", "minimum"):
        val = round(float(s_clean.min()), 2)
    elif metric_lower in ("max", "maximum"):
        val = round(float(s_clean.max()), 2)
    elif metric_lower in ("std", "stdev", "standard_deviation"):
        val = round(float(s_clean.std()), 2)
    else:
        val = round(float(s_clean.mean()), 2)
        metric_lower = "mean"

    return {
        "operation": "aggregation",
        "column": actual_col,
        "metric": metric_lower,
        "value": val,
        "total_records": total_records,
        "total_rows_evaluated": total_records,
        "formatted": f"{val:,.2f}" if abs(val) >= 100 else f"{val}",
    }


def run_groupby(group_col, metric_col=None, agg="count", sort_desc=True, limit=20, **kwargs):
    """
    Execute full-dataset Group-By aggregation with verified attrition rates and metrics.
    """
    if dl.df is None or len(dl.df) == 0:
        return {"error": "No active dataset loaded."}

    if metric_col is None and "metric_column" in kwargs:
        metric_col = kwargs["metric_column"]
    if "agg_func" in kwargs:
        agg = kwargs["agg_func"]

    actual_group_col = resolve_column_name(group_col)
    if not actual_group_col:
        return {"error": f"Grouping column '{group_col}' not found in active dataset."}

    actual_metric_col = resolve_column_name(metric_col) if metric_col else None
    has_attr = "AttritionFlag" in dl.df.columns

    groups = []
    total_records = len(dl.df)

    grouped = dl.df.groupby(actual_group_col, observed=True)

    for group_val, grp_df in grouped:
        headcount = len(grp_df)
        pct_of_total = round(headcount / total_records * 100, 1)

        attr_count = int(grp_df["AttritionFlag"].sum()) if has_attr else 0
        attr_rate = round(attr_count / headcount * 100, 1) if (has_attr and headcount > 0) else 0.0

        item = {
            "group": str(group_val),
            "headcount": headcount,
            "row_count": headcount,
            "headcount_pct": pct_of_total,
            "attrition_count": attr_count,
            "attrition_rate": attr_rate,
        }

        # Optional extra metric aggregation
        if actual_metric_col and actual_metric_col in grp_df.columns:
            m_series = grp_df[actual_metric_col].dropna()
            if len(m_series) > 0 and pd.api.types.is_numeric_dtype(m_series):
                agg_type = str(agg).lower()
                if agg_type in ("mean", "average", "avg"):
                    item[f"{actual_metric_col}_mean"] = round(float(m_series.mean()), 2)
                elif agg_type == "median":
                    item[f"{actual_metric_col}_median"] = round(float(m_series.median()), 2)
                elif agg_type == "sum":
                    item[f"{actual_metric_col}_sum"] = round(float(m_series.sum()), 2)
                elif agg_type in ("min", "max"):
                    item[f"{actual_metric_col}_{agg_type}"] = round(float(getattr(m_series, agg_type)()), 2)

        groups.append(item)

    # Sort
    sort_key = "attrition_rate" if (has_attr and (agg == "attrition_rate" or not actual_metric_col)) else "headcount"
    if actual_metric_col:
        for k in groups[0].keys():
            if k.startswith(actual_metric_col):
                sort_key = k
                break

    groups.sort(key=lambda x: x.get(sort_key, 0), reverse=sort_desc)

    return {
        "operation": "groupby",
        "group_column": actual_group_col,
        "metric_column": actual_metric_col,
        "total_groups": len(groups),
        "total_records": total_records,
        "results": groups[:limit],
        "groups": groups[:limit],
    }


def run_filter(conditions, limit=20):
    """
    Execute full-dataset multi-condition boolean filtering.
    conditions: list of {"column": str, "operator": str, "value": Any}
    Operators: ==, !=, >, <, >=, <=, in, contains.
    """
    if dl.df is None or len(dl.df) == 0:
        return {"error": "No active dataset loaded."}

    filtered_df = dl.df.copy()
    total_records = len(dl.df)
    applied_rules = []

    for cond in conditions:
        col = resolve_column_name(cond.get("column"))
        op = cond.get("operator", "==").strip()
        val = cond.get("value")

        if not col or col not in filtered_df.columns:
            continue

        try:
            s = filtered_df[col]
            if op == "==":
                if isinstance(val, (int, float)) and pd.api.types.is_numeric_dtype(s):
                    filtered_df = filtered_df[s == float(val)]
                else:
                    filtered_df = filtered_df[s.astype(str).str.lower() == str(val).lower().strip()]
            elif op == "!=":
                if isinstance(val, (int, float)) and pd.api.types.is_numeric_dtype(s):
                    filtered_df = filtered_df[s != float(val)]
                else:
                    filtered_df = filtered_df[s.astype(str).str.lower() != str(val).lower().strip()]
            elif op == ">":
                filtered_df = filtered_df[pd.to_numeric(s, errors="coerce") > float(val)]
            elif op == "<":
                filtered_df = filtered_df[pd.to_numeric(s, errors="coerce") < float(val)]
            elif op == ">=":
                filtered_df = filtered_df[pd.to_numeric(s, errors="coerce") >= float(val)]
            elif op == "<=":
                filtered_df = filtered_df[pd.to_numeric(s, errors="coerce") <= float(val)]
            elif op == "in" and isinstance(val, (list, tuple)):
                clean_vals = [str(v).lower().strip() for v in val]
                filtered_df = filtered_df[s.astype(str).str.lower().isin(clean_vals)]
            elif op == "contains":
                filtered_df = filtered_df[s.astype(str).str.lower().str.contains(str(val).lower().strip(), na=False)]

            applied_rules.append(f"{col} {op} {val}")
        except Exception as e:
            logger.warning(f"Error applying filter rule {cond}: {e}")

    matched_count = len(filtered_df)
    matched_pct = round(matched_count / total_records * 100, 1) if total_records > 0 else 0.0

    has_attr = "AttritionFlag" in filtered_df.columns
    attr_count = int(filtered_df["AttritionFlag"].sum()) if has_attr else 0
    attr_rate = round(attr_count / matched_count * 100, 1) if (has_attr and matched_count > 0) else 0.0

    # Summary metrics for matched cohort
    summary = {
        "matched_count": matched_count,
        "matching_count": matched_count,
        "total_records": total_records,
        "matched_pct": matched_pct,
        "percentage_of_dataset": matched_pct,
        "attrition_count": attr_count,
        "attrition_rate": attr_rate,
        "applied_rules": applied_rules,
    }

    if "MonthlyIncome" in filtered_df.columns and matched_count > 0:
        summary["avg_income"] = round(float(filtered_df["MonthlyIncome"].mean()), 0)
    if "YearsAtCompany" in filtered_df.columns and matched_count > 0:
        summary["avg_tenure"] = round(float(filtered_df["YearsAtCompany"].mean()), 1)
    if "Age" in filtered_df.columns and matched_count > 0:
        summary["avg_age"] = round(float(filtered_df["Age"].mean()), 1)

    # Sample rows (up to limit)
    id_col = "EmployeeNumber" if "EmployeeNumber" in filtered_df.columns else "EmployeeID" if "EmployeeID" in filtered_df.columns else None
    samples = []
    display_cols = [c for c in [id_col, "Department", "JobRole", "MonthlyIncome", "OverTime", "YearsAtCompany", "RiskLevel", "Attrition"] if c and c in filtered_df.columns]
    for _, r in filtered_df.head(limit).iterrows():
        samples.append({c: r.get(c) for c in display_cols})

    summary["samples"] = samples
    summary["operation"] = "filter"
    return summary


def run_correlation(target_col="AttritionFlag", top_n=10, col1=None, col2=None):
    """
    Compute Pearson correlation across numerical columns.
    If col1 and col2 given (or first two args are column strings): correlation between those two columns.
    Else: correlation of all numerical features with target_col.
    """
    if dl.df is None or len(dl.df) == 0:
        return {"error": "No active dataset loaded."}

    # Handle run_correlation("Age", "MonthlyIncome") positional call
    if isinstance(top_n, str) and not col1 and not col2:
        col1 = target_col
        col2 = top_n
        top_n = 10

    # Case 1: Pairwise correlation between two specific columns
    if col1 and col2:
        c1 = resolve_column_name(col1)
        c2 = resolve_column_name(col2)
        if not c1 or not c2:
            return {"error": f"Columns '{col1}' or '{col2}' could not be resolved."}

        s1 = pd.to_numeric(dl.df[c1], errors="coerce")
        s2 = pd.to_numeric(dl.df[c2], errors="coerce")
        valid = dl.df[[c1, c2]].dropna()
        if len(valid) < 2:
            return {"error": "Not enough valid numerical pairs to calculate correlation."}

        corr = round(float(valid[c1].astype(float).corr(valid[c2].astype(float))), 3)
        interpretation = "strong positive" if corr >= 0.5 else "moderate positive" if corr >= 0.2 else "negligible" if corr > -0.2 else "moderate negative" if corr > -0.5 else "strong negative"

        return {
            "operation": "pairwise_correlation",
            "column_1": c1,
            "column_2": c2,
            "correlation": corr,
            "correlation_coefficient": corr,
            "interpretation": f"A {interpretation} association (r = {corr}). Note: Correlation does not imply causation.",
            "sample_size": len(valid),
        }

    # Case 2: Correlation of all numeric columns with target attrition
    actual_target = resolve_column_name(target_col) or "AttritionFlag"
    if actual_target not in dl.df.columns:
        return {"error": f"Target column '{target_col}' not found."}

    target_series = dl.df[actual_target].astype(float)
    numeric_df = dl.df.select_dtypes(include=[np.number, "bool"]).copy()

    corrs = []
    for c in numeric_df.columns:
        if c == actual_target or c.lower() in ("employeenumber", "employeeid", "id"):
            continue
        valid_mask = numeric_df[c].notna() & target_series.notna()
        if valid_mask.sum() > 10 and numeric_df.loc[valid_mask, c].nunique() > 1 and target_series.loc[valid_mask].nunique() > 1:
            try:
                val = float(numeric_df.loc[valid_mask, c].astype(float).corr(target_series.loc[valid_mask]))
                if not np.isnan(val):
                    corrs.append({
                        "column": c,
                        "correlation": round(val, 3),
                        "abs_correlation": round(abs(val), 3),
                        "direction": "Increases Turnover" if val > 0 else "Decreases Turnover",
                    })
            except Exception:
                pass

    corrs.sort(key=lambda x: x["abs_correlation"], reverse=True)

    return {
        "operation": "target_correlation",
        "target_column": actual_target,
        "total_numerical_features": len(corrs),
        "top_correlated": corrs[:top_n],
        "note": "Pearson linear correlation coefficients. Statistical association does not prove causality.",
    }


def run_crosstab(row_col, col_col):
    """
    Generate contingency table / cross-tabulation with headcount and attrition rates.
    """
    if dl.df is None or len(dl.df) == 0:
        return {"error": "No active dataset loaded."}

    r_col = resolve_column_name(row_col)
    c_col = resolve_column_name(col_col)

    if not r_col or not c_col:
        return {"error": f"Could not resolve columns '{row_col}' or '{col_col}'."}

    has_attr = "AttritionFlag" in dl.df.columns
    total_records = len(dl.df)

    ct_count = pd.crosstab(dl.df[r_col], dl.df[c_col])

    table = []
    for r_idx in ct_count.index:
        row_dict = {"row_category": str(r_idx), "columns": {}}
        for c_idx in ct_count.columns:
            cell_count = int(ct_count.loc[r_idx, c_idx])
            cell_data = {"count": cell_count}
            if has_attr and cell_count > 0:
                mask = (dl.df[r_col] == r_idx) & (dl.df[c_col] == c_idx)
                att_c = int(dl.df.loc[mask, "AttritionFlag"].sum())
                att_r = round(att_c / cell_count * 100, 1)
                cell_data["attrition_count"] = att_c
                cell_data["attrition_rate"] = att_r
            row_dict["columns"][str(c_idx)] = cell_data
        table.append(row_dict)

    return {
        "operation": "crosstab",
        "row_column": r_col,
        "col_column": c_col,
        "row_values": [str(x) for x in ct_count.index],
        "col_values": [str(x) for x in ct_count.columns],
        "matrix": table,
        "total_records": total_records,
    }


def run_distribution(column, bins=5):
    """
    Compute complete numerical distribution: min, max, mean, median, std, quartiles, outliers, and histogram bins.
    """
    if dl.df is None or len(dl.df) == 0:
        return {"error": "No active dataset loaded."}

    col = resolve_column_name(column)
    if not col:
        return {"error": f"Column '{column}' could not be resolved."}

    s = dl.df[col].dropna()
    if not pd.api.types.is_numeric_dtype(s):
        # Categorical distribution
        counts = s.value_counts()
        total = len(s)
        items = [{"value": str(k), "count": int(v), "pct": round(int(v) / total * 100, 1)} for k, v in counts.items()]
        return {
            "operation": "categorical_distribution",
            "column": col,
            "total_records": total,
            "unique_categories": len(counts),
            "distribution": items[:15],
        }

    q1 = float(s.quantile(0.25))
    q3 = float(s.quantile(0.75))
    iqr = q3 - q1
    outliers = int(((s < (q1 - 1.5 * iqr)) | (s > (q3 + 1.5 * iqr))).sum())

    # Histogram binning
    cuts, bin_edges = pd.cut(s, bins=bins, retbins=True)
    bin_counts = cuts.value_counts(sort=False)
    has_attr = "AttritionFlag" in dl.df.columns

    bucket_results = []
    for interval, count in bin_counts.items():
        low = round(float(interval.left), 1)
        high = round(float(interval.right), 1)
        b_dict = {
            "range": f"{low} - {high}",
            "count": int(count),
            "pct": round(int(count) / len(s) * 100, 1) if len(s) > 0 else 0.0,
        }
        if has_attr and int(count) > 0:
            mask = (dl.df[col] >= interval.left) & (dl.df[col] <= interval.right)
            att_c = int(dl.df.loc[mask, "AttritionFlag"].sum())
            b_dict["attrition_rate"] = round(att_c / int(count) * 100, 1)
        bucket_results.append(b_dict)

    return {
        "operation": "numerical_distribution",
        "column": col,
        "total_records": len(s),
        "count": len(s),
        "min": round(float(s.min()), 2),
        "max": round(float(s.max()), 2),
        "mean": round(float(s.mean()), 2),
        "median": round(float(s.median()), 2),
        "std": round(float(s.std()), 2) if len(s) > 1 else 0.0,
        "q25": round(q1, 2),
        "q75": round(q3, 2),
        "quartiles": {"q1": round(q1, 2), "q3": round(q3, 2)},
        "outliers_count": outliers,
        "histogram_buckets": bucket_results,
    }


def run_data_quality_audit():
    """
    Generate dataset-wide data quality audit:
    - Missing value percentages
    - Duplicate records and IDs
    - Constant zero-variance columns
    - Outlier detection summary
    """
    if dl.df is None or len(dl.df) == 0:
        return {"error": "No active dataset loaded."}

    total_rows = len(dl.df)
    total_cols = len(dl.df.columns)
    duplicate_rows = int(dl.df.duplicated().sum())

    missing_cols = []
    constant_cols = []
    outlier_summary = []

    for c in dl.df.columns:
        s = dl.df[c]
        null_count = int(s.isna().sum())
        if null_count > 0:
            missing_cols.append({
                "column": c,
                "missing_count": null_count,
                "missing_pct": round(null_count / total_rows * 100, 2),
            })

        if s.nunique(dropna=True) <= 1:
            constant_cols.append(c)

        if pd.api.types.is_numeric_dtype(s) and not pd.api.types.is_bool_dtype(s):
            clean = s.dropna()
            if len(clean) > 0:
                q1 = float(clean.quantile(0.25))
                q3 = float(clean.quantile(0.75))
                iqr = q3 - q1
                outliers = int(((clean < (q1 - 1.5 * iqr)) | (clean > (q3 + 1.5 * iqr))).sum())
                if outliers > 0:
                    outlier_summary.append({
                        "column": c,
                        "outlier_count": outliers,
                        "outlier_pct": round(outliers / total_rows * 100, 2),
                    })

    # Identifier validation
    id_col = "EmployeeNumber" if "EmployeeNumber" in dl.df.columns else "EmployeeID" if "EmployeeID" in dl.df.columns else None
    duplicate_ids = 0
    if id_col:
        duplicate_ids = int(dl.df[id_col].duplicated().sum())

    health = round(max(0.0, min(100.0, 100 - (len(missing_cols) * 2 + (duplicate_rows > 0) * 10 + len(constant_cols) * 2))), 1)

    return {
        "operation": "data_quality_audit",
        "dataset_name": dl.DATASET_NAME or "Active Dataset",
        "dataset_version": dl.get_dataset_version(),
        "total_rows": total_rows,
        "total_columns": total_cols,
        "duplicate_rows_count": duplicate_rows,
        "duplicate_rows": duplicate_rows,
        "duplicate_employee_ids": duplicate_ids,
        "columns_with_missing_values": missing_cols,
        "missing_summary": missing_cols,
        "constant_zero_variance_columns": constant_cols,
        "numerical_columns_with_outliers": outlier_summary,
        "health_score": health,
        "overall_health_score": health,
    }


def run_cohort_comparison(cohort_col, group1=None, group2=None):
    """
    Execute full-dataset side-by-side comparison between two groups in cohort_col.
    """
    if dl.df is None or len(dl.df) == 0:
        return {"error": "No active dataset loaded."}

    actual_col = resolve_column_name(cohort_col)
    if not actual_col:
        return {"error": f"Cohort column '{cohort_col}' could not be resolved."}

    unique_vals = [str(x) for x in dl.df[actual_col].dropna().unique()]
    if len(unique_vals) < 2:
        return {"error": f"Column '{actual_col}' only has {len(unique_vals)} unique group(s). At least 2 required for comparison."}

    # Resolve group names
    def match_val(g_name):
        if not g_name:
            return None
        cleaned = str(g_name).strip().lower()
        for u in unique_vals:
            if u.lower() == cleaned:
                return u
        for u in unique_vals:
            if cleaned in u.lower():
                return u
        return None

    g1_val = match_val(group1) or unique_vals[0]
    g2_val = match_val(group2) or (unique_vals[1] if unique_vals[1] != g1_val else unique_vals[0])

    df1 = dl.df[dl.df[actual_col].astype(str) == g1_val]
    df2 = dl.df[dl.df[actual_col].astype(str) == g2_val]

    def cohort_stats(c_df, label):
        n = len(c_df)
        has_attr = "AttritionFlag" in c_df.columns
        att_c = int(c_df["AttritionFlag"].sum()) if has_attr else 0
        att_r = round(att_c / n * 100, 1) if (has_attr and n > 0) else 0.0

        res = {
            "group": label,
            "headcount": n,
            "attrition_count": att_c,
            "attrition_rate": att_r,
        }
        if "MonthlyIncome" in c_df.columns and n > 0:
            res["avg_salary"] = round(float(c_df["MonthlyIncome"].mean()), 0)
        if "YearsAtCompany" in c_df.columns and n > 0:
            res["avg_tenure"] = round(float(c_df["YearsAtCompany"].mean()), 1)
        if "Age" in c_df.columns and n > 0:
            res["avg_age"] = round(float(c_df["Age"].mean()), 1)
        if "OvertimeFlag" in c_df.columns and n > 0:
            res["overtime_rate"] = round(float(c_df["OvertimeFlag"].mean() * 100), 1)
        if "JobSatisfaction" in c_df.columns and n > 0:
            res["avg_satisfaction"] = round(float(c_df["JobSatisfaction"].mean()), 2)
        if "RiskScore" in c_df.columns and n > 0:
            res["avg_risk_score"] = round(float(c_df["RiskScore"].mean()), 2)

        return res

    stats1 = cohort_stats(df1, g1_val)
    stats2 = cohort_stats(df2, g2_val)

    # Differential calculation
    rate_diff = round(stats1.get("attrition_rate", 0) - stats2.get("attrition_rate", 0), 1)
    salary_diff = round(stats1.get("avg_salary", 0) - stats2.get("avg_salary", 0), 0)

    return {
        "operation": "cohort_comparison",
        "cohort_column": actual_col,
        "group_1": stats1,
        "group_2": stats2,
        "rate_difference_percentage_points": rate_diff,
        "salary_difference": salary_diff,
        "summary": f"{g1_val} has an attrition rate of {stats1.get('attrition_rate')}% vs {g2_val} at {stats2.get('attrition_rate')}% (Δ {rate_diff:+} pp).",
    }


def run_top_n(group_col, metric="attrition_rate", ascending=False, n=10):
    """
    Return top or bottom N groups ranked by metric.
    """
    grp_res = run_groupby(group_col, sort_desc=not ascending, limit=100)
    if "error" in grp_res:
        return grp_res

    results = grp_res.get("results", [])
    if metric == "headcount":
        results.sort(key=lambda x: x["headcount"], reverse=not ascending)
    else:
        results.sort(key=lambda x: x["attrition_rate"], reverse=not ascending)

    return {
        "operation": "top_n",
        "group_column": grp_res["group_column"],
        "ranking_metric": metric,
        "order": "ascending (lowest)" if ascending else "descending (highest)",
        "results": results[:n],
    }

