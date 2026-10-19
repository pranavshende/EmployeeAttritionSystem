"""
Analytics Engine
Pre-computes all dashboard KPIs, chart data, factor analysis, and high-risk profiles
from the loaded DataFrame. All computations happen at import time for fast API responses.
"""

import numpy as np
import pandas as pd
from . import data_loader as dl


def _attrition_breakdown(group_col, label_col=None):
    """Generic helper: compute attrition count, total, and rate grouped by a column."""
    if dl.df is None or len(dl.df) == 0 or group_col not in dl.df.columns:
        return []
    col = label_col if label_col and label_col in dl.df.columns else group_col
    grouped = dl.df.groupby(col).agg(
        total=("AttritionFlag", "size"),
        attrition=("AttritionFlag", "sum"),
    ).reset_index()
    grouped["retention"] = grouped["total"] - grouped["attrition"]
    grouped["rate"] = (grouped["attrition"] / grouped["total"] * 100).round(2)
    grouped = grouped.rename(columns={col: "label"})
    grouped["label"] = grouped["label"].astype(str)
    return grouped.sort_values("rate", ascending=False).to_dict(orient="records")


def _band_breakdown(band_col):
    """Compute attrition breakdown for pre-computed band columns."""
    if dl.df is None or len(dl.df) == 0 or band_col not in dl.df.columns:
        return []
    grouped = dl.df.groupby(band_col, observed=True).agg(
        total=("AttritionFlag", "size"),
        attrition=("AttritionFlag", "sum"),
    ).reset_index()
    grouped["retention"] = grouped["total"] - grouped["attrition"]
    grouped["rate"] = (grouped["attrition"] / grouped["total"] * 100).round(2)
    grouped = grouped.rename(columns={band_col: "label"})
    grouped["label"] = grouped["label"].astype(str)
    return grouped.to_dict(orient="records")


# ──────────────────────────────────────────────
#  KPI Metrics
# ──────────────────────────────────────────────

def get_kpis():
    """Top-level KPI metrics for the dashboard header cards."""
    if dl.df is None or len(dl.df) == 0:
        return None

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
    return {
        "job_satisfaction": _attrition_breakdown("JobSatisfaction", "JobSatisfactionLabel"),
        "env_satisfaction": _attrition_breakdown("EnvironmentSatisfaction", "EnvSatisfactionLabel"),
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
            factors.append({
                "factor": "OverTime",
                "high_risk_group": "Yes",
                "high_risk_rate": round(ot_yes, 1),
                "low_risk_group": "No",
                "low_risk_rate": round(ot_no, 1),
                "impact": round(ot_yes - ot_no, 1),
                "description": f"Employees working overtime leave at {round(ot_yes, 1)}% vs {round(ot_no, 1)}%",
            })

    # Income
    if "MonthlyIncome" in dl.df.columns and "AttritionFlag" in dl.df.columns:
        low_inc_mask = dl.df["MonthlyIncome"] <= 5000
        high_inc_mask = dl.df["MonthlyIncome"] > 15000
        if low_inc_mask.sum() > 0 and high_inc_mask.sum() > 0:
            low_inc = float(dl.df[low_inc_mask]["AttritionFlag"].mean() * 100)
            high_inc = float(dl.df[high_inc_mask]["AttritionFlag"].mean() * 100)
            factors.append({
                "factor": "Monthly Income",
                "high_risk_group": "≤ ₹5,000",
                "high_risk_rate": round(low_inc, 1),
                "low_risk_group": "> ₹15,000",
                "low_risk_rate": round(high_inc, 1),
                "impact": round(low_inc - high_inc, 1),
                "description": f"Low-income employees leave at {round(low_inc, 1)}% vs {round(high_inc, 1)}%",
            })

    # Tenure
    if "YearsAtCompany" in dl.df.columns and "AttritionFlag" in dl.df.columns:
        nh_mask = dl.df["YearsAtCompany"] <= 2
        vet_mask = dl.df["YearsAtCompany"] >= 11
        if nh_mask.sum() > 0 and vet_mask.sum() > 0:
            new_hire = float(dl.df[nh_mask]["AttritionFlag"].mean() * 100)
            veteran = float(dl.df[vet_mask]["AttritionFlag"].mean() * 100)
            factors.append({
                "factor": "Company Tenure",
                "high_risk_group": "0-2 years",
                "high_risk_rate": round(new_hire, 1),
                "low_risk_group": "11+ years",
                "low_risk_rate": round(veteran, 1),
                "impact": round(new_hire - veteran, 1),
                "description": f"New hires (0-2 yrs) leave at {round(new_hire, 1)}% vs veterans at {round(veteran, 1)}%",
            })

    # Stock options
    if "StockOptionLevel" in dl.df.columns and "AttritionFlag" in dl.df.columns:
        no_s_mask = dl.df["StockOptionLevel"] == 0
        has_s_mask = dl.df["StockOptionLevel"] >= 1
        if no_s_mask.sum() > 0 and has_s_mask.sum() > 0:
            no_stock = float(dl.df[no_s_mask]["AttritionFlag"].mean() * 100)
            has_stock = float(dl.df[has_s_mask]["AttritionFlag"].mean() * 100)
            factors.append({
                "factor": "Stock Options",
                "high_risk_group": "Level 0 (None)",
                "high_risk_rate": round(no_stock, 1),
                "low_risk_group": "Level 1+",
                "low_risk_rate": round(has_stock, 1),
                "impact": round(no_stock - has_stock, 1),
                "description": f"No stock options: {round(no_stock, 1)}% vs with options: {round(has_stock, 1)}%",
            })

    # Job Satisfaction
    if "JobSatisfaction" in dl.df.columns and "AttritionFlag" in dl.df.columns:
        l_sat_mask = dl.df["JobSatisfaction"] == 1
        h_sat_mask = dl.df["JobSatisfaction"] == 4
        if l_sat_mask.sum() > 0 and h_sat_mask.sum() > 0:
            low_sat = float(dl.df[l_sat_mask]["AttritionFlag"].mean() * 100)
            high_sat = float(dl.df[h_sat_mask]["AttritionFlag"].mean() * 100)
            factors.append({
                "factor": "Job Satisfaction",
                "high_risk_group": "Level 1 (Low)",
                "high_risk_rate": round(low_sat, 1),
                "low_risk_group": "Level 4 (Very High)",
                "low_risk_rate": round(high_sat, 1),
                "impact": round(low_sat - high_sat, 1),
                "description": f"Low satisfaction: {round(low_sat, 1)}% vs very high: {round(high_sat, 1)}%",
            })

    # Environment Satisfaction
    if "EnvironmentSatisfaction" in dl.df.columns and "AttritionFlag" in dl.df.columns:
        l_env_mask = dl.df["EnvironmentSatisfaction"] == 1
        h_env_mask = dl.df["EnvironmentSatisfaction"] == 4
        if l_env_mask.sum() > 0 and h_env_mask.sum() > 0:
            low_env = float(dl.df[l_env_mask]["AttritionFlag"].mean() * 100)
            high_env = float(dl.df[h_env_mask]["AttritionFlag"].mean() * 100)
            factors.append({
                "factor": "Environment Satisfaction",
                "high_risk_group": "Level 1 (Low)",
                "high_risk_rate": round(low_env, 1),
                "low_risk_group": "Level 4 (Very High)",
                "low_risk_rate": round(high_env, 1),
                "impact": round(low_env - high_env, 1),
                "description": f"Low env satisfaction: {round(low_env, 1)}% vs very high: {round(high_env, 1)}%",
            })

    # Age
    if "Age" in dl.df.columns and "AttritionFlag" in dl.df.columns:
        y_mask = dl.df["Age"] <= 25
        o_mask = (dl.df["Age"] >= 36) & (dl.df["Age"] <= 45)
        if y_mask.sum() > 0 and o_mask.sum() > 0:
            young = float(dl.df[y_mask]["AttritionFlag"].mean() * 100)
            older = float(dl.df[o_mask]["AttritionFlag"].mean() * 100)
            factors.append({
                "factor": "Age Group",
                "high_risk_group": "18-25",
                "high_risk_rate": round(young, 1),
                "low_risk_group": "36-45",
                "low_risk_rate": round(older, 1),
                "impact": round(young - older, 1),
                "description": f"Young employees (18-25): {round(young, 1)}% vs mid-career (36-45): {round(older, 1)}%",
            })

    # Distance from home
    if "DistanceFromHome" in dl.df.columns and "AttritionFlag" in dl.df.columns:
        f_mask = dl.df["DistanceFromHome"] >= 16
        n_mask = dl.df["DistanceFromHome"] <= 5
        if f_mask.sum() > 0 and n_mask.sum() > 0:
            far = float(dl.df[f_mask]["AttritionFlag"].mean() * 100)
            near = float(dl.df[n_mask]["AttritionFlag"].mean() * 100)
            factors.append({
                "factor": "Distance from Home",
                "high_risk_group": "16+ miles",
                "high_risk_rate": round(far, 1),
                "low_risk_group": "0-5 miles",
                "low_risk_rate": round(near, 1),
                "impact": round(far - near, 1),
                "description": f"Long commute (16+ mi): {round(far, 1)}% vs nearby (0-5 mi): {round(near, 1)}%",
            })

    # Work-life balance
    if "WorkLifeBalance" in dl.df.columns and "AttritionFlag" in dl.df.columns:
        l_wlb_mask = dl.df["WorkLifeBalance"] == 1
        h_wlb_mask = dl.df["WorkLifeBalance"] == 4
        if l_wlb_mask.sum() > 0 and h_wlb_mask.sum() > 0:
            low_wlb = float(dl.df[l_wlb_mask]["AttritionFlag"].mean() * 100)
            high_wlb = float(dl.df[h_wlb_mask]["AttritionFlag"].mean() * 100)
            factors.append({
                "factor": "Work-Life Balance",
                "high_risk_group": "Level 1 (Bad)",
                "high_risk_rate": round(low_wlb, 1),
                "low_risk_group": "Level 4 (Best)",
                "low_risk_rate": round(high_wlb, 1),
                "impact": round(low_wlb - high_wlb, 1),
                "description": f"Bad balance: {round(low_wlb, 1)}% vs best balance: {round(high_wlb, 1)}%",
            })

    # Sort by impact descending
    factors.sort(key=lambda x: x["impact"], reverse=True)
    return factors


# ──────────────────────────────────────────────
#  High-Risk Employees
# ──────────────────────────────────────────────

def get_high_risk_employees(min_risk_score=3, page=1, per_page=20):
    """Return employees matching >= min_risk_score criteria."""
    if dl.df is None or len(dl.df) == 0:
        return {
            "employees": [],
            "total": 0,
            "page": page,
            "per_page": per_page,
            "total_pages": 1,
        }

    score_col = "RiskScore" if "RiskScore" in dl.df.columns else None
    if score_col:
        high_risk = dl.df[dl.df[score_col] >= min_risk_score].copy()
        high_risk = high_risk.sort_values(score_col, ascending=False)
    else:
        high_risk = dl.df.copy()

    total = len(high_risk)
    start = (page - 1) * per_page
    end = start + per_page
    page_data = high_risk.iloc[start:end]

    employees = []
    for _, row in page_data.iterrows():
        employees.append({
            "employee_number": int(row.get("EmployeeNumber", 0)),
            "age": int(row.get("Age", 0)),
            "department": str(row.get("Department", "General")),
            "job_role": str(row.get("JobRole", "Employee")),
            "monthly_income": int(row.get("MonthlyIncome", 0)),
            "overtime": str(row.get("OverTime", "No")),
            "years_at_company": int(row.get("YearsAtCompany", 0)),
            "job_satisfaction": int(row.get("JobSatisfaction", 3)),
            "env_satisfaction": int(row.get("EnvironmentSatisfaction", 3)),
            "stock_option_level": int(row.get("StockOptionLevel", 0)),
            "risk_score": int(row.get("RiskScore", 0)),
            "risk_level": str(row.get("RiskLevel", "Low")),
            "attrition": str(row.get("Attrition", "No")),
        })

    return {
        "employees": employees,
        "total": total,
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
        filtered = filtered[filtered["Age"] >= int(filters["age_min"])]
    if filters.get("age_max") and "Age" in filtered.columns:
        filtered = filtered[filtered["Age"] <= int(filters["age_max"])]
    if filters.get("income_min") and "MonthlyIncome" in filtered.columns:
        filtered = filtered[filtered["MonthlyIncome"] >= int(filters["income_min"])]
    if filters.get("income_max") and "MonthlyIncome" in filtered.columns:
        filtered = filtered[filtered["MonthlyIncome"] <= int(filters["income_max"])]

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
        g["rate"] = (g["attrition"] / g["total"] * 100).round(2)
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
    """
    if dl.df is None or len(dl.df) == 0:
        return None

    target = str(emp_id).strip().lower().lstrip("#")
    if not target:
        return None

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

