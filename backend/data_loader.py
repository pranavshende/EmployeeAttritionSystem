"""
Data Loader Module
Loads and preprocesses datasets (default IBM HR dataset or dynamically uploaded custom CSVs).
Supports automatic column detection, normalization, and on-the-spot band computations.
"""

import os
import logging
import hashlib
import pandas as pd
import numpy as np
from datetime import datetime

logger = logging.getLogger(__name__)

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
DATASET_VERSION = None
DATASET_PROFILE = None
DATASET_INFO = {"has_dataset": False, "version": None}


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

    max_inc = float(clean_df["MonthlyIncome"].max()) if len(clean_df) > 0 else 0
    if max_inc <= 25000:
        clean_df["IncomeBand"] = pd.cut(
            clean_df["MonthlyIncome"],
            bins=[-1, 5000, 10000, 15000, 100000000],
            labels=["1k-5k", "5k-10k", "10k-15k", "15k+"],
        )
    else:
        try:
            clean_df["IncomeBand"] = pd.qcut(
                clean_df["MonthlyIncome"],
                q=4,
                labels=["Tier 1 (Lowest)", "Tier 2 (Mid-Low)", "Tier 3 (Mid-High)", "Tier 4 (Highest)"],
                duplicates="drop",
            )
        except Exception:
            clean_df["IncomeBand"] = pd.cut(
                clean_df["MonthlyIncome"],
                bins=4,
                labels=["Tier 1", "Tier 2", "Tier 3", "Tier 4"],
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
    if id_col:
        clean_df["EmployeeNumber"] = clean_df[id_col].astype(str)
    elif "EmployeeNumber" not in clean_df.columns:
        clean_df["EmployeeNumber"] = np.arange(1001, 1001 + len(clean_df)).astype(str)
    else:
        clean_df["EmployeeNumber"] = clean_df["EmployeeNumber"].astype(str)

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


def compute_dataset_profile(dataframe, dataset_name):
    """
    Dynamically profile the complete active dataset:
    - Schema types, missing counts, uniqueness
    - Numerical distributions (min, max, mean, median, std, quartiles, outliers)
    - Categorical frequency & unique values
    - Duplicate detection & identifier validation
    - Data quality summary
    """
    if dataframe is None or len(dataframe) == 0:
        return {
            "has_dataset": False,
            "version": None,
            "total_rows": 0,
            "total_columns": 0,
            "columns": {},
            "numerical_columns": [],
            "categorical_columns": [],
            "identifier_columns": [],
            "target_column": None,
            "duplicates_count": 0,
            "missing_cells_count": 0,
            "overall_missing_pct": 0.0,
        }

    total_rows = len(dataframe)
    total_cols = len(dataframe.columns)
    col_profiles = {}
    num_cols = []
    cat_cols = []
    id_cols = []
    total_missing_cells = 0

    for col in dataframe.columns:
        s = dataframe[col]
        missing_count = int(s.isna().sum())
        total_missing_cells += missing_count
        missing_pct = round(missing_count / total_rows * 100, 2)
        unique_count = int(s.nunique(dropna=True))

        is_num = pd.api.types.is_numeric_dtype(s)
        is_bool = pd.api.types.is_bool_dtype(s)

        profile = {
            "name": col,
            "dtype": str(s.dtype),
            "missing_count": missing_count,
            "missing_pct": missing_pct,
            "unique_count": unique_count,
            "is_numeric": bool(is_num and not is_bool),
            "is_boolean": bool(is_bool),
        }

        # Check for potential identifier column (100% unique or ID pattern)
        if unique_count == total_rows and total_rows > 1:
            id_cols.append(col)
            profile["is_identifier"] = True
        elif col.lower() in ("employeenumber", "employeeid", "id", "emp_id", "empnumber"):
            id_cols.append(col)
            profile["is_identifier"] = True
        else:
            profile["is_identifier"] = False

        if is_num and not is_bool:
            num_cols.append(col)
            valid_s = s.dropna()
            if len(valid_s) > 0:
                q1 = float(valid_s.quantile(0.25))
                q3 = float(valid_s.quantile(0.75))
                iqr = q3 - q1
                outliers = int(((valid_s < (q1 - 1.5 * iqr)) | (valid_s > (q3 + 1.5 * iqr))).sum())
                profile.update({
                    "min": round(float(valid_s.min()), 2),
                    "max": round(float(valid_s.max()), 2),
                    "mean": round(float(valid_s.mean()), 2),
                    "median": round(float(valid_s.median()), 2),
                    "std": round(float(valid_s.std()), 2) if len(valid_s) > 1 else 0.0,
                    "q25": round(q1, 2),
                    "q75": round(q3, 2),
                    "outliers_count": outliers,
                })
        else:
            cat_cols.append(col)
            val_counts = s.value_counts(dropna=True).head(5)
            profile["top_values"] = [
                {"value": str(k), "count": int(v), "pct": round(int(v) / total_rows * 100, 1)}
                for k, v in val_counts.items()
            ]

        col_profiles[col] = profile

    duplicate_rows = int(dataframe.duplicated().sum())
    total_cells = total_rows * total_cols
    overall_missing_pct = round(total_missing_cells / total_cells * 100, 2) if total_cells > 0 else 0.0

    # Fingerprint hash
    sample_str = str(dataframe.head(3).to_dict()) + str(dataframe.tail(3).to_dict())
    hash_input = f"{dataset_name}_{total_rows}_{sorted(dataframe.columns)}_{sample_str}"
    version_hash = hashlib.sha256(hash_input.encode("utf-8")).hexdigest()[:10]

    health_score = round(max(0.0, min(100.0, 100 - (overall_missing_pct * 2 + (duplicate_rows > 0) * 10))), 1)

    return {
        "has_dataset": True,
        "version": version_hash,
        "dataset_name": dataset_name,
        "total_rows": total_rows,
        "total_columns": total_cols,
        "row_count": total_rows,
        "columns_count": total_cols,
        "columns": col_profiles,
        "numerical_columns": num_cols,
        "categorical_columns": cat_cols,
        "identifier_columns": list(set(id_cols)),
        "target_column": "AttritionFlag" if "AttritionFlag" in dataframe.columns else None,
        "duplicates_count": duplicate_rows,
        "missing_cells_count": total_missing_cells,
        "overall_missing_pct": overall_missing_pct,
        "data_quality": {
            "overall_health_score": health_score,
            "duplicate_rows": duplicate_rows,
            "overall_missing_pct": overall_missing_pct,
        },
    }


def _update_state(new_df, dataset_name, is_custom=True, detected_target="Attrition"):
    """Update global module variables."""
    global df, TOTAL_EMPLOYEES, ATTRITION_COUNT, RETENTION_COUNT, ATTRITION_RATE, DATASET_NAME, DATASET_VERSION, DATASET_PROFILE, DATASET_INFO
    df = new_df
    TOTAL_EMPLOYEES = len(df) if df is not None else 0
    ATTRITION_COUNT = int(df["AttritionFlag"].sum()) if (df is not None and "AttritionFlag" in df.columns) else 0
    RETENTION_COUNT = TOTAL_EMPLOYEES - ATTRITION_COUNT
    ATTRITION_RATE = round(ATTRITION_COUNT / TOTAL_EMPLOYEES * 100, 2) if TOTAL_EMPLOYEES > 0 else 0.0
    DATASET_NAME = dataset_name

    DATASET_PROFILE = compute_dataset_profile(df, dataset_name)
    DATASET_VERSION = DATASET_PROFILE.get("version")

    DATASET_INFO = {
        "has_dataset": True if df is not None and len(df) > 0 else False,
        "dataset_name": dataset_name,
        "version": DATASET_VERSION,
        "is_custom": is_custom,
        "total_employees": TOTAL_EMPLOYEES,
        "attrition_count": ATTRITION_COUNT,
        "retention_count": RETENTION_COUNT,
        "attrition_rate": ATTRITION_RATE,
        "columns_count": len(df.columns) if df is not None else 0,
        "detected_target": detected_target,
        "uploaded_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "duplicates_count": DATASET_PROFILE.get("duplicates_count", 0),
        "overall_missing_pct": DATASET_PROFILE.get("overall_missing_pct", 0.0),
    }


ACTIVE_DATASET_POINTER = os.path.join(DATA_DIR, ".active_dataset")


def _set_active_dataset_pointer(filename):
    """Persist active dataset name to disk so restarts and workers retain the active dataset."""
    try:
        with open(ACTIVE_DATASET_POINTER, "w", encoding="utf-8") as f:
            f.write(filename.strip())
    except Exception as e:
        logger.warning(f"Could not write active dataset pointer: {e}")


def _clear_active_dataset_pointer():
    """Remove active dataset pointer on explicit user clear/reset."""
    try:
        if os.path.exists(ACTIVE_DATASET_POINTER):
            os.remove(ACTIVE_DATASET_POINTER)
    except Exception as e:
        logger.warning(f"Could not clear active dataset pointer: {e}")


def ensure_dataset_loaded():
    """
    Ensure an active dataset is in memory.
    If df is None, restores the last active dataset from disk or latest upload.
    """
    global df
    if df is not None and len(df) > 0:
        return df

    # 1. Check active dataset pointer
    if os.path.exists(ACTIVE_DATASET_POINTER):
        try:
            with open(ACTIVE_DATASET_POINTER, "r", encoding="utf-8") as f:
                filename = f.read().strip()
            if filename:
                candidate = os.path.join(UPLOADS_DIR, filename)
                if os.path.exists(candidate):
                    return load_custom_csv(candidate, filename)
                candidate_data = os.path.join(DATA_DIR, filename)
                if os.path.exists(candidate_data):
                    return load_custom_csv(candidate_data, filename)
        except Exception as e:
            logger.warning(f"Error reading active dataset pointer: {e}")

    # 2. Check for latest uploaded file in UPLOADS_DIR
    if os.path.exists(UPLOADS_DIR):
        files = [f for f in os.listdir(UPLOADS_DIR) if f.lower().endswith(".csv")]
        if files:
            target = "employee_attrition_sample_10000.csv" if "employee_attrition_sample_10000.csv" in files else files[0]
            target_path = os.path.join(UPLOADS_DIR, target)
            return load_custom_csv(target_path, target)

    # 3. Fallback to default CSV
    if os.path.exists(DEFAULT_CSV_PATH):
        return load_default_dataset()

    return None


def clear_dataset():
    """Clear active dataset and reset to uninitialized state."""
    global df, TOTAL_EMPLOYEES, ATTRITION_COUNT, RETENTION_COUNT, ATTRITION_RATE, DATASET_NAME, DATASET_VERSION, DATASET_PROFILE, DATASET_INFO
    df = None
    TOTAL_EMPLOYEES = 0
    ATTRITION_COUNT = 0
    RETENTION_COUNT = 0
    ATTRITION_RATE = 0.0
    DATASET_NAME = None
    DATASET_VERSION = None
    DATASET_PROFILE = None
    DATASET_INFO = {
        "has_dataset": False,
        "dataset_name": None,
        "version": None,
        "is_custom": False,
        "total_employees": 0,
        "attrition_count": 0,
        "retention_count": 0,
        "attrition_rate": 0.0,
        "columns_count": 0,
    }
    _clear_active_dataset_pointer()


def get_dataset_version():
    """Return active dataset version fingerprint."""
    global DATASET_VERSION
    return DATASET_VERSION


def get_data():
    """Return active DataFrame singleton, ensuring it is loaded."""
    global df
    if df is None:
        return ensure_dataset_loaded()
    return df


def get_dataframe():
    """Alias for get_data()."""
    return get_data()


def get_dataset_profile():
    """Return comprehensive active dataset schema and distribution profile."""
    global DATASET_PROFILE, df, DATASET_NAME
    if DATASET_PROFILE is None and df is not None and len(df) > 0:
        DATASET_PROFILE = compute_dataset_profile(df, DATASET_NAME or "Active Dataset")
    return DATASET_PROFILE


def load_default_dataset():
    """Load default IBM HR Attrition dataset."""
    raw_df = pd.read_csv(DEFAULT_CSV_PATH, encoding="utf-8-sig")
    clean_df = _normalize_and_preprocess(raw_df, dataset_name="WA_Fn-UseC_-HR-Employee-Attrition.csv", is_custom=False)
    _update_state(clean_df, "WA_Fn-UseC_-HR-Employee-Attrition.csv", is_custom=False)
    _set_active_dataset_pointer("WA_Fn-UseC_-HR-Employee-Attrition.csv")
    return clean_df


def load_custom_csv(file_stream_or_path, filename):
    """
    Load an arbitrary uploaded CSV file and dynamically transform it for the dashboard.
    Saves the file to uploads directory, writes pointer, and updates module state.
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
    _set_active_dataset_pointer(filename)

    # Persist dataset and employee records to Supabase PostgreSQL database via Prisma
    try:
        from . import db
        db.save_dataset_in_background(
            clean_df,
            filename,
            TOTAL_EMPLOYEES,
            ATTRITION_COUNT,
            RETENTION_COUNT,
            ATTRITION_RATE,
        )
    except Exception as e:
        logger.warning(f"Could not queue Prisma database save: {e}")

    return clean_df


# Automatically restore active dataset on server startup
ensure_dataset_loaded()

