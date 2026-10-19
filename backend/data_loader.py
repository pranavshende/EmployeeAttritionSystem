"""
Data Loader Module
Loads and preprocesses datasets (default IBM HR dataset or dynamically uploaded custom CSVs).
Supports automatic column detection, normalization, and on-the-spot band computations.
"""

import os
import pandas as pd
import numpy as np
from datetime import datetime

# Path to the default cleaned CSV copy
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
UPLOADS_DIR = os.path.join(DATA_DIR, "uploads")
DEFAULT_CSV_PATH = os.path.join(DATA_DIR, "WA_Fn-UseC_-HR-Employee-Attrition.csv")

os.makedirs(UPLOADS_DIR, exist_ok=True)

# Module state singletons
df = None
TOTAL_EMPLOYEES = 0
ATTRITION_COUNT = 0
RETENTION_COUNT = 0
ATTRITION_RATE = 0.0
DATASET_NAME = None
DATASET_INFO = {"has_dataset": False}


def _find_column_by_aliases(columns, aliases):
    """Find a column in a dataframe by checking a list of lowercase aliases."""
    col_map = {str(c).lower().replace(" ", "").replace("_", "").replace("-", ""): c for c in columns}
    for alias in aliases:
        clean_alias = alias.lower().replace(" ", "").replace("_", "").replace("-", "")
        if clean_alias in col_map:
            return col_map[clean_alias]
    return None


def _normalize_and_preprocess(raw_df, dataset_name="WA_Fn-UseC_-HR-Employee-Attrition.csv", is_custom=False):
    """Normalize any CSV into the dashboard schema with robust fallbacks."""
    clean_df = raw_df.copy()
    cols = clean_df.columns.tolist()

    # 1. Target Attrition column detection
    attr_col = _find_column_by_aliases(cols, ["attrition", "left", "churn", "turnover", "is_left", "resigned", "terminated", "status", "exit"])
    if attr_col:
        # Convert to boolean flag
        positive_values = {"yes", "y", "1", 1, True, "left", "resigned", "terminated", "true"}
        clean_df["AttritionFlag"] = clean_df[attr_col].apply(
            lambda v: True if str(v).strip().lower() in positive_values or v is True else False
        )
        clean_df["Attrition"] = clean_df["AttritionFlag"].apply(lambda v: "Yes" if v else "No")
    else:
        # If no target found, create a baseline
        clean_df["AttritionFlag"] = False
        clean_df["Attrition"] = "No"

    # 2. Department detection
    dept_col = _find_column_by_aliases(cols, ["department", "dept", "team", "division", "businessunit", "business_unit", "group"])
    if dept_col and dept_col != "Department":
        clean_df["Department"] = clean_df[dept_col].astype(str)
    elif "Department" not in clean_df.columns:
        # Find any categorical column with 2-10 unique values
        cat_candidates = [c for c in cols if 2 <= clean_df[c].nunique() <= 10 and not c.startswith("Attrition")]
        clean_df["Department"] = clean_df[cat_candidates[0]].astype(str) if cat_candidates else "General Department"

    # 3. Job Role detection
    role_col = _find_column_by_aliases(cols, ["jobrole", "role", "title", "position", "designation", "job_title"])
    if role_col and role_col != "JobRole":
        clean_df["JobRole"] = clean_df[role_col].astype(str)
    elif "JobRole" not in clean_df.columns:
        clean_df["JobRole"] = clean_df["Department"].astype(str) + " Specialist"

    # 4. OverTime detection
    ot_col = _find_column_by_aliases(cols, ["overtime", "ot", "over_time", "extra_hours"])
    if ot_col:
        pos_ot = {"yes", "y", "1", 1, True, "true"}
        clean_df["OvertimeFlag"] = clean_df[ot_col].apply(lambda v: True if str(v).strip().lower() in pos_ot or v is True else False)
        clean_df["OverTime"] = clean_df["OvertimeFlag"].apply(lambda v: "Yes" if v else "No")
    elif "OverTime" not in clean_df.columns:
        clean_df["OvertimeFlag"] = False
        clean_df["OverTime"] = "No"

    # 5. Age detection & Banding
    age_col = _find_column_by_aliases(cols, ["age", "years_of_age", "employee_age"])
    if age_col and age_col != "Age":
        clean_df["Age"] = pd.to_numeric(clean_df[age_col], errors="coerce").fillna(35).astype(int)
    elif "Age" not in clean_df.columns:
        clean_df["Age"] = 35

    clean_df["AgeBand"] = pd.cut(
        clean_df["Age"],
        bins=[-1, 25, 35, 45, 55, 120],
        labels=["18-25", "26-35", "36-45", "46-55", "56+"],
    )

    # 6. Monthly Income detection & Banding
    income_col = _find_column_by_aliases(cols, ["monthlyincome", "salary", "income", "compensation", "monthly_income", "pay", "wage"])
    if income_col and income_col != "MonthlyIncome":
        clean_df["MonthlyIncome"] = pd.to_numeric(clean_df[income_col], errors="coerce").fillna(5000).astype(float)
    elif "MonthlyIncome" not in clean_df.columns:
        clean_df["MonthlyIncome"] = 6500.0

    clean_df["IncomeBand"] = pd.cut(
        clean_df["MonthlyIncome"],
        bins=[-1, 5000, 10000, 15000, 1000000],
        labels=["1k-5k", "5k-10k", "10k-15k", "15k+"],
    )

    # 7. Tenure (YearsAtCompany) detection & Banding
    tenure_col = _find_column_by_aliases(cols, ["yearsatcompany", "tenure", "years_at_company", "experience", "company_tenure"])
    if tenure_col and tenure_col != "YearsAtCompany":
        clean_df["YearsAtCompany"] = pd.to_numeric(clean_df[tenure_col], errors="coerce").fillna(3).astype(int)
    elif "YearsAtCompany" not in clean_df.columns:
        clean_df["YearsAtCompany"] = 4

    clean_df["TenureBand"] = pd.cut(
        clean_df["YearsAtCompany"],
        bins=[-1, 2, 5, 10, 100],
        labels=["0-2 yrs", "3-5 yrs", "6-10 yrs", "11+ yrs"],
    )

    # 8. DistanceFromHome
    dist_col = _find_column_by_aliases(cols, ["distancefromhome", "distance", "commute", "commute_distance"])
    if dist_col and dist_col != "DistanceFromHome":
        clean_df["DistanceFromHome"] = pd.to_numeric(clean_df[dist_col], errors="coerce").fillna(5).astype(int)
    elif "DistanceFromHome" not in clean_df.columns:
        clean_df["DistanceFromHome"] = 8

    clean_df["DistanceBand"] = pd.cut(
        clean_df["DistanceFromHome"],
        bins=[-1, 5, 15, 200],
        labels=["0-5 mi", "6-15 mi", "16+ mi"],
    )

    # 9. Gender & MaritalStatus
    gender_col = _find_column_by_aliases(cols, ["gender", "sex"])
    if gender_col and gender_col != "Gender":
        clean_df["Gender"] = clean_df[gender_col].astype(str)
    elif "Gender" not in clean_df.columns:
        clean_df["Gender"] = "Not Specified"

    marital_col = _find_column_by_aliases(cols, ["maritalstatus", "marital", "marital_status"])
    if marital_col and marital_col != "MaritalStatus":
        clean_df["MaritalStatus"] = clean_df[marital_col].astype(str)
    elif "MaritalStatus" not in clean_df.columns:
        clean_df["MaritalStatus"] = "Single"

    # 10. BusinessTravel
    travel_col = _find_column_by_aliases(cols, ["businesstravel", "travel", "business_travel"])
    if travel_col and travel_col != "BusinessTravel":
        clean_df["BusinessTravel"] = clean_df[travel_col].astype(str)
    elif "BusinessTravel" not in clean_df.columns:
        clean_df["BusinessTravel"] = "Travel_Rarely"

    # 11. Satisfaction Ratings (JobSatisfaction, EnvironmentSatisfaction, WorkLifeBalance)
    for sat_name, aliases in [
        ("JobSatisfaction", ["jobsatisfaction", "job_satisfaction", "satisfaction"]),
        ("EnvironmentSatisfaction", ["environmentsatisfaction", "env_satisfaction", "workplace_satisfaction"]),
        ("WorkLifeBalance", ["worklifebalance", "work_life_balance", "wlb"]),
    ]:
        col_found = _find_column_by_aliases(cols, aliases)
        if col_found and col_found != sat_name:
            clean_df[sat_name] = pd.to_numeric(clean_df[col_found], errors="coerce").fillna(3).astype(int)
        elif sat_name not in clean_df.columns:
            clean_df[sat_name] = 3

    satisfaction_map = {1: "Low", 2: "Medium", 3: "High", 4: "Very High"}
    clean_df["JobSatisfactionLabel"] = clean_df["JobSatisfaction"].map(satisfaction_map).fillna("High")
    clean_df["EnvSatisfactionLabel"] = clean_df["EnvironmentSatisfaction"].map(satisfaction_map).fillna("High")
    clean_df["WorkLifeBalanceLabel"] = clean_df["WorkLifeBalance"].map(satisfaction_map).fillna("High")

    # 12. StockOptionLevel
    stock_col = _find_column_by_aliases(cols, ["stockoptionlevel", "stock_options", "equity_level"])
    if stock_col and stock_col != "StockOptionLevel":
        clean_df["StockOptionLevel"] = pd.to_numeric(clean_df[stock_col], errors="coerce").fillna(0).astype(int)
    elif "StockOptionLevel" not in clean_df.columns:
        clean_df["StockOptionLevel"] = 0

    # 13. Employee Identifier
    id_col = _find_column_by_aliases(cols, ["employeenumber", "employeeid", "id", "emp_id", "emp_number"])
    if id_col and id_col != "EmployeeNumber":
        clean_df["EmployeeNumber"] = clean_df[id_col].astype(str)
    elif "EmployeeNumber" not in clean_df.columns:
        clean_df["EmployeeNumber"] = np.arange(1001, 1001 + len(clean_df))

    # 14. Dynamic Risk Score calculation
    ot_score = (clean_df["OverTime"] == "Yes").astype(int) if "OverTime" in clean_df.columns else 0
    inc_score = (clean_df["MonthlyIncome"] < 5000).astype(int)
    tenure_score = (clean_df["YearsAtCompany"] <= 2).astype(int)
    sat_score = (clean_df["JobSatisfaction"] <= 2).astype(int)
    env_score = (clean_df["EnvironmentSatisfaction"] <= 2).astype(int)
    stock_score = (clean_df["StockOptionLevel"] == 0).astype(int)
    age_score = (clean_df["Age"] <= 25).astype(int)
    wlb_score = (clean_df["WorkLifeBalance"] == 1).astype(int)

    clean_df["RiskScore"] = (
        ot_score + inc_score + tenure_score + sat_score + env_score + stock_score + age_score + wlb_score
    )

    clean_df["RiskLevel"] = pd.cut(
        clean_df["RiskScore"],
        bins=[-1, 2, 4, 10],
        labels=["Low", "Medium", "High"],
    )

    return clean_df


def _update_state(new_df, dataset_name, is_custom=True, detected_target="Attrition"):
    """Update global module variables."""
    global df, TOTAL_EMPLOYEES, ATTRITION_COUNT, RETENTION_COUNT, ATTRITION_RATE, DATASET_NAME, DATASET_INFO
    df = new_df
    TOTAL_EMPLOYEES = len(df) if df is not None else 0
    ATTRITION_COUNT = int(df["AttritionFlag"].sum()) if (df is not None and "AttritionFlag" in df.columns) else 0
    RETENTION_COUNT = TOTAL_EMPLOYEES - ATTRITION_COUNT
    ATTRITION_RATE = round(ATTRITION_COUNT / TOTAL_EMPLOYEES * 100, 2) if TOTAL_EMPLOYEES > 0 else 0.0
    DATASET_NAME = dataset_name
    DATASET_INFO = {
        "has_dataset": True if df is not None and len(df) > 0 else False,
        "dataset_name": dataset_name,
        "is_custom": is_custom,
        "total_employees": TOTAL_EMPLOYEES,
        "attrition_count": ATTRITION_COUNT,
        "retention_count": RETENTION_COUNT,
        "attrition_rate": ATTRITION_RATE,
        "columns_count": len(df.columns) if df is not None else 0,
        "detected_target": detected_target,
        "uploaded_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }


def clear_dataset():
    """Clear active dataset and reset to uninitialized state (do not show pre-existing CSV)."""
    global df, TOTAL_EMPLOYEES, ATTRITION_COUNT, RETENTION_COUNT, ATTRITION_RATE, DATASET_NAME, DATASET_INFO
    df = None
    TOTAL_EMPLOYEES = 0
    ATTRITION_COUNT = 0
    RETENTION_COUNT = 0
    ATTRITION_RATE = 0.0
    DATASET_NAME = None
    DATASET_INFO = {
        "has_dataset": False,
        "dataset_name": None,
        "is_custom": False,
        "total_employees": 0,
        "attrition_count": 0,
        "retention_count": 0,
        "attrition_rate": 0.0,
        "columns_count": 0,
    }


def load_default_dataset():
    """Load default IBM HR Attrition dataset (called only on explicit user request)."""
    raw_df = pd.read_csv(DEFAULT_CSV_PATH, encoding="utf-8-sig")
    clean_df = _normalize_and_preprocess(raw_df, dataset_name="WA_Fn-UseC_-HR-Employee-Attrition.csv", is_custom=False)
    _update_state(clean_df, "WA_Fn-UseC_-HR-Employee-Attrition.csv", is_custom=False)
    return clean_df


def load_custom_csv(file_stream_or_path, filename):
    """
    Load an arbitrary uploaded CSV file and dynamically transform it for the dashboard.
    Saves the file to uploads directory and updates the module singleton state.
    """
    save_path = os.path.join(UPLOADS_DIR, filename)
    if isinstance(file_stream_or_path, str):
        raw_df = pd.read_csv(file_stream_or_path, encoding="utf-8-sig")
    else:
        # File-like object (from Flask request.files)
        raw_df = pd.read_csv(file_stream_or_path, encoding="utf-8-sig")
        raw_df.to_csv(save_path, index=False, encoding="utf-8-sig")

    clean_df = _normalize_and_preprocess(raw_df, dataset_name=filename, is_custom=True)
    _update_state(clean_df, filename, is_custom=True)
    return clean_df


# Initialize completely empty — do NOT show details of pre-existing CSV
clear_dataset()

