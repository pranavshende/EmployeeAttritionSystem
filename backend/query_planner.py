"""
Safe Analytical Query Planner for AttritionAI.
Translates natural-language questions into safe, typed, allowlisted analytical operations.
Strictly disallows arbitrary code or SQL execution. Validates all operations against the active dataset schema.
"""

import re
import json
import logging
from typing import Dict, Any, List, Optional, Tuple

from . import data_loader as dl
from . import analytics_engine as ae

logger = logging.getLogger(__name__)

# Allowlisted analytical operations
ALLOWED_OPERATIONS = {
    "aggregation",
    "groupby",
    "filter",
    "correlation",
    "crosstab",
    "distribution",
    "data_quality",
    "cohort_comparison",
    "top_n",
    "dataset_profile",
    "multi_step",
}

ALLOWED_METRICS = {
    "mean", "average", "avg", "median", "sum", "total",
    "min", "max", "std", "count", "nunique", "attrition_rate"
}

ALLOWED_FILTER_OPS = {"==", "!=", ">", "<", ">=", "<=", "in", "contains"}


# ─────────────────────────────────────────────────────────────
#  Deterministic Plan Compiler (Heuristic Pattern Matcher)
# ─────────────────────────────────────────────────────────────

def compile_rule_based_plan(user_query: str) -> Optional[Dict[str, Any]]:
    """
    Deterministically parse common analytical queries into structured query plans.
    Fast, 100% offline, zero latency, and safe.
    """
    q = user_query.lower().strip()

    # 1. Data Quality & Missing Values
    if any(k in q for k in ["missing value", "missing values", "null values", "nulls", "data quality", "duplicates", "duplicate rows", "cleanliness", "data health"]):
        return {
            "operation": "data_quality",
            "description": "Evaluate dataset data quality, missing values, duplicates, and column anomalies.",
        }

    # 2. Complete Dataset Profile / Overview
    if any(k in q for k in ["dataset overview", "dataset profile", "describe dataset", "schema", "columns list", "all columns", "column types", "summary of dataset"]):
        return {
            "operation": "dataset_profile",
            "description": "Inspect dynamic dataset schema, column types, and distributions.",
        }

    # 3. Correlation & Associations
    if "correlation" in q or "associated with" in q or "correlate" in q or "factors associated" in q:
        # Check if between two specific columns: "correlation between X and Y"
        m = re.search(r"between\s+([a-zA-Z_\s]+)\s+and\s+([a-zA-Z_\s]+)", q)
        if m:
            c1 = ae.resolve_column_name(m.group(1).strip())
            c2 = ae.resolve_column_name(m.group(2).strip())
            if c1 and c2:
                return {
                    "operation": "correlation",
                    "col1": c1,
                    "col2": c2,
                    "description": f"Compute pairwise linear correlation between {c1} and {c2}.",
                }
        return {
            "operation": "correlation",
            "target": "AttritionFlag",
            "top_n": 10,
            "description": "Identify numerical features with strongest statistical correlation to attrition.",
        }

    # 4. Distribution / Histogram
    if any(k in q for k in ["distribution", "histogram", "spread", "quantile", "percentile", "quartile"]):
        # Identify target column
        for word in q.split():
            clean_word = word.strip(",.?")
            resolved = ae.resolve_column_name(clean_word)
            if resolved:
                return {
                    "operation": "distribution",
                    "column": resolved,
                    "bins": 5,
                    "description": f"Calculate summary distribution, quartiles, and histogram for {resolved}.",
                }

    # 5. Cohort Comparison: "compare X and Y" or "compare X vs Y"
    if "compare" in q or " vs " in q or " versus " in q:
        # Check overtime comparison
        if "overtime" in q:
            return {
                "operation": "cohort_comparison",
                "cohort_column": "OverTime",
                "group1": "Yes",
                "group2": "No",
                "description": "Compare employees working Overtime vs Non-Overtime across all metrics.",
            }
        # Check gender comparison
        if "gender" in q or "male" in q or "female" in q:
            return {
                "operation": "cohort_comparison",
                "cohort_column": "Gender",
                "group1": "Female",
                "group2": "Male",
                "description": "Compare Male vs Female workforce metrics.",
            }

    # 6. GroupBy / Breakdown / By Department / By Role
    if any(k in q for k in ["by department", "by role", "by job role", "by age", "by gender", "by tenure", "by overtime", "by marital"]):
        # Find grouping column
        group_candidate = None
        for key in ["department", "jobrole", "role", "age", "gender", "overtime", "tenure", "marital", "education"]:
            if f"by {key}" in q or f"per {key}" in q:
                group_candidate = ae.resolve_column_name(key)
                break

        if group_candidate:
            # Check for specific metric
            metric_col = None
            agg = "attrition_rate"
            if "salary" in q or "income" in q or "pay" in q:
                metric_col = "MonthlyIncome"
                agg = "mean"
            elif "tenure" in q or "years" in q:
                metric_col = "YearsAtCompany"
                agg = "mean"
            elif "age" in q and group_candidate != "Age":
                metric_col = "Age"
                agg = "mean"

            return {
                "operation": "groupby",
                "group_column": group_candidate,
                "metric_column": metric_col,
                "agg": agg,
                "sort_desc": True,
                "limit": 15,
                "description": f"Calculate breakdown by {group_candidate}.",
            }

    # 7. Top / Bottom N or Rankings
    if any(k in q for k in ["rank", "ranking", "rankings", "leaderboard", "top", "bottom", "highest", "lowest"]):
        col = "JobRole" if any(k in q for k in ["role", "job", "position", "title"]) else "Department"
        direction_asc = any(k in q for k in ["bottom", "lowest", "least"])
        n_match = re.search(r"\b(\d{1,2})\b", q)
        n = int(n_match.group(1)) if n_match else (25 if "all" in q else 10)
        return {
            "operation": "top_n",
            "group_column": col,
            "metric": "attrition_rate",
            "ascending": direction_asc,
            "n": n,
            "description": f"Rank {col} by attrition rate.",
        }

    # 8. Single Aggregation (e.g. "average salary", "median age", "highest tenure", "total records")
    for metric_kw, m_name in [
        ("average", "mean"), ("avg", "mean"), ("mean", "mean"),
        ("median", "median"), ("highest", "max"), ("maximum", "max"), ("max", "max"),
        ("lowest", "min"), ("minimum", "min"), ("min", "min"),
        ("total", "sum"), ("sum", "sum"),
    ]:
        if metric_kw in q:
            for w in q.split():
                col = ae.resolve_column_name(w.strip(",.?"))
                if col and col != "AttritionFlag":
                    return {
                        "operation": "aggregation",
                        "column": col,
                        "metric": m_name,
                        "description": f"Calculate {m_name} of {col}.",
                    }

    return None


# ─────────────────────────────────────────────────────────────
#  LLM-Assisted Query Plan Compiler (For Complex / Arbitrary Queries)
# ─────────────────────────────────────────────────────────────

def compile_llm_plan(user_query: str, system_caller) -> Optional[Dict[str, Any]]:
    """
    Use Gemini with strict JSON schema to generate typed analytical execution plan
    when rule-based compilation is ambiguous or multi-step.
    """
    profile = dl.get_dataset_profile()
    if not profile or not profile.get("has_dataset"):
        return None

    columns_str = ", ".join([f"{col} ({p.get('dtype')})" for col, p in list(profile.get("columns", {}).items())[:30]])

    prompt = (
        f"You are the Analytical Query Planner for an Employee Attrition Intelligence system.\n"
        f"Convert the user's natural language question into a single typed analytical query plan.\n\n"
        f"ACTIVE DATASET COLUMNS:\n{columns_str}\n\n"
        f"ALLOWED OPERATIONS:\n"
        f"1. aggregation: {{\"operation\": \"aggregation\", \"column\": \"<col>\", \"metric\": \"mean|median|min|max|sum|std|count|nunique|attrition_rate\"}}\n"
        f"2. groupby: {{\"operation\": \"groupby\", \"group_column\": \"<col>\", \"metric_column\": \"<optional_num_col>\", \"agg\": \"mean|sum|count|attrition_rate\", \"sort_desc\": true, \"limit\": 15}}\n"
        f"3. filter: {{\"operation\": \"filter\", \"conditions\": [{{\"column\": \"<col>\", \"operator\": \"==|!=|>|<|>=|<=\", \"value\": <val>}}], \"limit\": 10}}\n"
        f"4. correlation: {{\"operation\": \"correlation\", \"col1\": \"<optional>\", \"col2\": \"<optional>\", \"target\": \"AttritionFlag\", \"top_n\": 10}}\n"
        f"5. crosstab: {{\"operation\": \"crosstab\", \"row_column\": \"<col1>\", \"col_column\": \"<col2>\"}}\n"
        f"6. distribution: {{\"operation\": \"distribution\", \"column\": \"<col>\", \"bins\": 5}}\n"
        f"7. cohort_comparison: {{\"operation\": \"cohort_comparison\", \"cohort_column\": \"<col>\", \"group1\": \"<val1>\", \"group2\": \"<val2>\"}}\n"
        f"8. top_n: {{\"operation\": \"top_n\", \"group_column\": \"<col>\", \"metric\": \"attrition_rate|headcount\", \"ascending\": false, \"n\": 5}}\n"
        f"9. data_quality: {{\"operation\": \"data_quality\"}}\n"
        f"10. dataset_profile: {{\"operation\": \"dataset_profile\"}}\n\n"
        f"Return ONLY valid JSON matching one of the above plans. No markdown fences, no conversational prose.\n"
        f"USER QUESTION: \"{user_query}\""
    )

    try:
        reply = system_caller(prompt)
        if not reply:
            return None
        # Clean JSON
        clean_json = re.sub(r"^```json\s*", "", reply.strip())
        clean_json = re.sub(r"\s*```$", "", clean_json).strip()
        plan = json.loads(clean_json)
        if isinstance(plan, dict) and plan.get("operation") in ALLOWED_OPERATIONS:
            return plan
    except Exception as e:
        logger.warning(f"LLM Query Planner parsing failed: {e}")

    return None


def compile_query_plan(user_query: str, allow_llm: bool = True, system_caller=None) -> Optional[Dict[str, Any]]:
    """Compile user natural language query into typed analytical plan."""
    plan = compile_rule_based_plan(user_query)
    if plan:
        return plan
    if allow_llm and system_caller:
        return compile_llm_plan(user_query, system_caller)
    return None


# ─────────────────────────────────────────────────────────────
#  Plan Validation & Safe Execution
# ─────────────────────────────────────────────────────────────

def validate_plan(plan: Dict[str, Any]) -> Tuple[bool, str, Dict[str, Any]]:
    """
    Validate plan against active dataset schema.
    Returns (is_valid, error_message, sanitized_plan).
    """
    if dl.df is None or len(dl.df) == 0:
        return False, "No active dataset loaded in memory.", {}

    op = str(plan.get("operation", "")).lower().strip()
    if op not in ALLOWED_OPERATIONS:
        return False, f"Unauthorized or unsupported analytical operation: '{op}'.", {}

    sanitized = dict(plan)
    sanitized["operation"] = op

    # 1. Aggregation validation
    if op == "aggregation":
        col = ae.resolve_column_name(plan.get("column"))
        if not col:
            return False, f"Cannot resolve column '{plan.get('column')}' in active dataset schema.", {}
        sanitized["column"] = col
        metric = str(plan.get("metric", "mean")).lower().strip()
        if metric not in ALLOWED_METRICS:
            sanitized["metric"] = "mean"

    # 2. Groupby validation
    elif op == "groupby":
        raw_grp = plan.get("group_column") or plan.get("group_by")
        grp_col = ae.resolve_column_name(raw_grp)
        if not grp_col:
            return False, f"Cannot resolve grouping column '{raw_grp}' in active dataset schema.", {}
        sanitized["group_column"] = grp_col
        raw_m = plan.get("metric_column") or plan.get("metric_col")
        if raw_m:
            m_col = ae.resolve_column_name(raw_m)
            sanitized["metric_column"] = m_col

    # 3. Filter validation
    elif op == "filter":
        conditions = plan.get("conditions", [])
        clean_conds = []
        for c in conditions:
            col = ae.resolve_column_name(c.get("column"))
            operator = str(c.get("operator", "==")).strip()
            if col and operator in ALLOWED_FILTER_OPS:
                clean_conds.append({
                    "column": col,
                    "operator": operator,
                    "value": c.get("value"),
                })
        if not clean_conds:
            return False, "No valid filter conditions could be verified against dataset columns.", {}
        sanitized["conditions"] = clean_conds

    # 4. Correlation validation
    elif op == "correlation":
        if plan.get("col1") and plan.get("col2"):
            c1 = ae.resolve_column_name(plan.get("col1"))
            c2 = ae.resolve_column_name(plan.get("col2"))
            if not c1 or not c2:
                return False, f"Pairwise correlation columns '{plan.get('col1')}', '{plan.get('col2')}' could not be resolved.", {}
            sanitized["col1"] = c1
            sanitized["col2"] = c2

    # 5. Crosstab validation
    elif op == "crosstab":
        r_col = ae.resolve_column_name(plan.get("row_column"))
        c_col = ae.resolve_column_name(plan.get("col_column"))
        if not r_col or not c_col:
            return False, f"Crosstab columns '{plan.get('row_column')}' or '{plan.get('col_column')}' could not be resolved.", {}
        sanitized["row_column"] = r_col
        sanitized["col_column"] = c_col

    # 6. Distribution validation
    elif op == "distribution":
        col = ae.resolve_column_name(plan.get("column"))
        if not col:
            return False, f"Distribution column '{plan.get('column')}' not found.", {}
        sanitized["column"] = col

    # 7. Cohort comparison validation
    elif op == "cohort_comparison":
        col = ae.resolve_column_name(plan.get("cohort_column"))
        if not col:
            return False, f"Cohort column '{plan.get('cohort_column')}' not found.", {}
        sanitized["cohort_column"] = col

    # 8. Top N validation
    elif op == "top_n":
        col = ae.resolve_column_name(plan.get("group_column"))
        if not col:
            return False, f"Ranking column '{plan.get('group_column')}' not found.", {}
        sanitized["group_column"] = col

    return True, "", sanitized


def validate_query_plan(plan: Dict[str, Any]) -> Tuple[bool, str]:
    """Validate query plan returning (is_valid, error_msg)."""
    valid, err, _ = validate_plan(plan)
    return valid, err


def execute_plan(plan: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute a validated query plan deterministically on the full active dataset.
    """
    if not plan or not isinstance(plan, dict):
        return {"error": "Invalid or empty query plan.", "success": False}

    op = str(plan.get("operation", "")).lower().strip()

    if op == "aggregation":
        col = plan.get("column")
        metric = plan.get("metric") or plan.get("aggregation") or "mean"
        res = ae.run_aggregation(col, metric=metric)

    elif op == "groupby":
        grp_col = plan.get("group_column") or plan.get("group_by")
        m_col = plan.get("metric_column") or plan.get("metric_col")
        agg = plan.get("agg") or plan.get("aggregation") or "count"
        res = ae.run_groupby(
            grp_col,
            metric_col=m_col,
            agg=agg,
            sort_desc=plan.get("sort_desc", True),
            limit=plan.get("limit", 15),
        )

    elif op == "filter":
        res = ae.run_filter(plan.get("conditions", []), limit=plan.get("limit", 10))

    elif op == "correlation":
        res = ae.run_correlation(
            target_col=plan.get("target", "AttritionFlag"),
            top_n=plan.get("top_n", 10),
            col1=plan.get("col1"),
            col2=plan.get("col2"),
        )

    elif op == "crosstab":
        res = ae.run_crosstab(plan["row_column"], plan["col_column"])

    elif op == "distribution":
        res = ae.run_distribution(plan["column"], bins=plan.get("bins", 5))

    elif op == "data_quality":
        res = ae.run_data_quality_audit()

    elif op == "cohort_comparison":
        res = ae.run_cohort_comparison(
            plan["cohort_column"],
            group1=plan.get("group1"),
            group2=plan.get("group2"),
        )

    elif op == "top_n":
        res = ae.run_top_n(
            plan["group_column"],
            metric=plan.get("metric", "attrition_rate"),
            ascending=plan.get("ascending", False),
            n=plan.get("n", 5),
        )

    elif op == "dataset_profile":
        profile = dl.get_dataset_profile()
        res = {"operation": "dataset_profile", "profile": profile}

    else:
        res = {"error": f"Unknown operation: {op}"}

    if isinstance(res, dict):
        res["success"] = "error" not in res
        if "results" not in res:
            res["results"] = res
        elif isinstance(res.get("results"), list):
            res["groups"] = res["results"]

    return res


# ─────────────────────────────────────────────────────────────
#  Deterministic Markdown Formatter for Evidence Results
# ─────────────────────────────────────────────────────────────

def format_plan_results_as_markdown(result: Dict[str, Any], query_plan: Optional[Dict[str, Any]] = None) -> str:
    """
    Render structured analytical results into beautiful GitHub Markdown tables & cards.
    Supports either (result, query_plan) or (query_plan, result) argument order.
    """
    if not isinstance(result, dict):
        return "📊 Analytical execution completed."

    # If caller passed (query_plan, result) in reverse
    if isinstance(query_plan, dict) and ("results" in query_plan or "success" in query_plan):
        result, query_plan = query_plan, result
    elif isinstance(result, dict) and "results" not in result and isinstance(query_plan, dict) and "results" in query_plan:
        result, query_plan = query_plan, result

    if "error" in result:
        return f"⚠️ **Analysis Execution Note:** {result['error']}"

    op = str(result.get("operation") or (query_plan and query_plan.get("operation")) or "").lower().strip()
    version = dl.get_dataset_version()
    v_badge = f"`[Dataset: {dl.DATASET_NAME or 'Active'} • v:{version}]`" if version else ""

    # 1. Aggregation
    if op == "aggregation":
        col = result.get("column") or (query_plan and query_plan.get("column"))
        metric = result.get("metric") or (query_plan and (query_plan.get("metric") or query_plan.get("aggregation"))) or "value"
        val = result.get("value")
        fmt = result.get("formatted", str(val))
        total = result.get("total_records", 0)
        return (
            f"📊 **Dataset Aggregation: {col}** {v_badge}\n\n"
            f"• **Metric:** `{str(metric).upper()}`\n"
            f"• **Computed Value:** **{fmt}**\n"
            f"• **Denominator:** Complete cohort of **{total:,}** employees analyzed without sampling."
        )

    # 2. GroupBy Table
    elif op == "groupby":
        grp_col = result.get("group_column") or (query_plan and (query_plan.get("group_column") or query_plan.get("group_by"))) or "Department"
        raw_res = result.get("results", [])
        if isinstance(raw_res, dict):
            raw_res = raw_res.get("results", [])
        results = raw_res if isinstance(raw_res, list) else []
        total_groups = result.get("total_groups", len(results))
        total_rec = result.get("total_records", 0)

        lines = [
            f"📊 **Cohort Breakdown by `{grp_col}`** {v_badge}\n",
            f"*Full dataset analysis across all {total_rec:,} records ({total_groups} unique categories).*\n",
            f"| {grp_col} | Headcount | % Cohort | Departed | Attrition Rate |",
            "| :--- | :---: | :---: | :---: | :---: |",
        ]
        for r in results:
            lines.append(f"| **{r.get('group', '')}** | {r.get('headcount', 0):,} | {r.get('headcount_pct', 0)}% | {r.get('attrition_count', 0)} | **{r.get('attrition_rate', 0)}%** |")

        return "\n".join(lines)

    # 3. Filtered Results
    elif op == "filter":
        matched = result.get("matched_count", 0)
        total = result.get("total_records", 0)
        pct = result.get("matched_pct", 0)
        att_c = result.get("attrition_count", 0)
        att_r = result.get("attrition_rate", 0)
        rules = ", ".join([f"`{r}`" for r in result.get("applied_rules", [])])

        lines = [
            f"🔍 **Multi-Condition Filter Analysis** {v_badge}\n",
            f"• **Filter Rules:** {rules}",
            f"• **Matched Cohort:** **{matched:,}** of {total:,} employees (**{pct}%** of active workforce)",
            f"• **Cohort Attrition:** **{att_r}%** ({att_c} departed vs overall {dl.ATTRITION_RATE}% baseline)\n",
        ]
        if "avg_income" in result:
            lines.append(f"• **Average Salary:** ₹{result['avg_income']:,.0f}/mo")
        if "avg_tenure" in result:
            lines.append(f"• **Average Tenure:** {result['avg_tenure']} years")

        samples = result.get("samples", [])
        if samples:
            lines.append("\n**Sample Matching Records:**\n")
            cols = list(samples[0].keys())
            lines.append("| " + " | ".join(cols) + " |")
            lines.append("| " + " | ".join([":---:" if "rate" in c.lower() or "id" in c.lower() else ":---" for c in cols]) + " |")
            for s in samples[:5]:
                lines.append("| " + " | ".join([str(s.get(c, "")) for c in cols]) + " |")

        return "\n".join(lines)

    # 4. Correlation
    elif op == "pairwise_correlation":
        c1 = result.get("column_1")
        c2 = result.get("column_2")
        r = result.get("correlation_coefficient")
        interp = result.get("interpretation")
        n = result.get("sample_size")
        return (
            f"📈 **Correlation Analysis: `{c1}` vs `{c2}`** {v_badge}\n\n"
            f"• **Pearson Correlation (r):** **{r}**\n"
            f"• **Statistical Relationship:** {interp}\n"
            f"• **Sample Analyzed:** {n:,} complete records.\n\n"
            f"> [!NOTE]\n"
            f"> Statistical correlation indicates observed co-variance; it does not prove direct causation."
        )

    elif op == "target_correlation":
        target = result.get("target_column")
        top_c = result.get("top_correlated", [])
        lines = [
            f"📈 **Features Most Strongly Associated with `{target}`** {v_badge}\n",
            f"*Linear Pearson correlation calculated across all complete numerical variables.*\n",
            "| Feature | Correlation (r) | Direction | Turnover Impact |",
            "| :--- | :---: | :---: | :--- |",
        ]
        for c in top_c[:8]:
            arrow = "🔴 Increases" if c["correlation"] > 0 else "🟢 Protects / Decreases"
            lines.append(f"| **{c['column']}** | `{c['correlation']:+0.3f}` | {c['direction']} | {arrow} |")
        lines.append("\n> [!NOTE]\n> Linear correlation measures association across the cohort, not causation.")
        return "\n".join(lines)

    # 5. Data Quality Audit
    elif op == "data_quality_audit":
        score = result.get("health_score", 100)
        rows = result.get("total_rows", 0)
        cols = result.get("total_columns", 0)
        dups = result.get("duplicate_rows_count", 0)
        dup_ids = result.get("duplicate_employee_ids", 0)
        missing = result.get("columns_with_missing_values", [])
        consts = result.get("constant_zero_variance_columns", [])
        outliers = result.get("numerical_columns_with_outliers", [])

        badge = "🟢 High Integrity" if score >= 90 else "🟡 Moderate Anomalies" if score >= 75 else "🔴 Needs Remediation"

        lines = [
            f"🛡️ **Dynamic Dataset Quality & Integrity Audit** {v_badge}\n",
            f"• **Overall Health Score:** **{score}/100** ({badge})",
            f"• **Dataset Dimensions:** **{rows:,}** rows × **{cols}** columns",
            f"• **Duplicate Records:** **{dups}** full duplicate rows | **{dup_ids}** duplicate employee IDs\n",
        ]

        if missing:
            lines.append("**Missing Values by Column:**\n")
            lines.append("| Column | Missing Count | Missing % |")
            lines.append("| :--- | :---: | :---: |")
            for m in missing[:8]:
                lines.append(f"| **{m['column']}** | {m['missing_count']:,} | {m['missing_pct']}% |")
        else:
            lines.append("• **Missing Values:** ✅ **0 null cells** detected across complete dataset.\n")

        if consts:
            lines.append(f"• **Constant Columns (Zero Variance):** {', '.join([f'`{c}`' for c in consts])}\n")

        if outliers:
            lines.append(f"• **Columns with Numerical Outliers (IQR Method):** {len(outliers)} columns flagged (e.g. `{outliers[0]['column']}`: {outliers[0]['outlier_count']} outliers).")

        return "\n".join(lines)

    # 6. Distribution
    elif op == "numerical_distribution":
        col = result.get("column")
        total = result.get("total_records", 0)
        lines = [
            f"📊 **Distribution Analysis: `{col}`** {v_badge}\n",
            f"• **Total Evaluated:** {total:,} records",
            f"• **Min / Max:** **{result.get('min')}** / **{result.get('max')}**",
            f"• **Mean (Average):** **{result.get('mean')}** (Std Dev: {result.get('std')})",
            f"• **Median (50th %):** **{result.get('median')}** (Q1: {result.get('q25')}, Q3: {result.get('q75')})",
            f"• **Outlier Count (IQR):** {result.get('outliers_count')} records\n",
            "**Histogram Frequency Bins:**\n",
            f"| Range | Headcount | % of Cohort | Attrition Rate |",
            "| :--- | :---: | :---: | :---: |",
        ]
        for b in result.get("histogram_buckets", []):
            att_str = f"**{b.get('attrition_rate')}%**" if "attrition_rate" in b else "N/A"
            lines.append(f"| **{b['range']}** | {b['count']:,} | {b['pct']}% | {att_str} |")

        return "\n".join(lines)

    # 7. Cohort Comparison
    elif op == "cohort_comparison":
        col = result.get("cohort_column")
        g1 = result.get("group_1", {})
        g2 = result.get("group_2", {})
        diff = result.get("rate_difference_percentage_points", 0)

        lines = [
            f"⚖️ **Comparative Cohort Analysis: `{col}`** {v_badge}\n",
            f"*Comparing `{g1.get('group')}` vs `{g2.get('group')}` across standardized workforce metrics.*\n",
            "| Metric | " + f"{g1.get('group')} | {g2.get('group')} | Variance (Δ) |",
            "| :--- | :---: | :---: | :---: |",
            f"| **Headcount** | {g1.get('headcount'):,} | {g2.get('headcount'):,} | {g1.get('headcount',0) - g2.get('headcount',0):+,} |",
            f"| **Attrition Rate** | **{g1.get('attrition_rate')}%** | **{g2.get('attrition_rate')}%** | **{diff:+} pp** |",
        ]
        if "avg_salary" in g1 and "avg_salary" in g2:
            lines.append(f"| **Average Salary** | ₹{g1.get('avg_salary'):,.0f} | ₹{g2.get('avg_salary'):,.0f} | ₹{g1.get('avg_salary',0)-g2.get('avg_salary',0):+,.0f} |")
        if "avg_tenure" in g1 and "avg_tenure" in g2:
            lines.append(f"| **Company Tenure** | {g1.get('avg_tenure')} yrs | {g2.get('avg_tenure')} yrs | {g1.get('avg_tenure',0)-g2.get('avg_tenure',0):+.1f} yrs |")
        if "overtime_rate" in g1 and "overtime_rate" in g2:
            lines.append(f"| **Overtime Work Rate** | {g1.get('overtime_rate')}% | {g2.get('overtime_rate')}% | {g1.get('overtime_rate',0)-g2.get('overtime_rate',0):+.1f} pp |")
        if "avg_risk_score" in g1 and "avg_risk_score" in g2:
            lines.append(f"| **Average Risk Score** | {g1.get('avg_risk_score')}/8 | {g2.get('avg_risk_score')}/8 | {g1.get('avg_risk_score',0)-g2.get('avg_risk_score',0):+.2f} |")

        lines.append(f"\n💡 **Key Takeaway:** {result.get('summary')}")
        return "\n".join(lines)

    # 8. Top N
    elif op == "top_n":
        col = result.get("group_column")
        metric = result.get("ranking_metric")
        order = result.get("order")
        res = result.get("results", [])

        lines = [
            f"🏆 **Leaderboard: Ranked `{col}` by `{metric}`** {v_badge}\n",
            f"*Sorted {order}. Entire dataset evaluated.*\n",
            f"| Rank | {col} | Headcount | Attrition Rate |",
            "| :---: | :--- | :---: | :---: |",
        ]
        for idx, r in enumerate(res, 1):
            badge = "🔥 " if idx <= 2 and "highest" in order else ""
            lines.append(f"| #{idx} | **{r['group']}** | {r['headcount']:,} | {badge}**{r['attrition_rate']}%** |")

        return "\n".join(lines)

    # 9. Dataset Profile
    elif op == "dataset_profile":
        prof = result.get("profile", {})
        num_c = len(prof.get("numerical_columns", []))
        cat_c = len(prof.get("categorical_columns", []))
        id_c = prof.get("identifier_columns", [])
        return (
            f"📋 **Dynamic Dataset Schema Profile** {v_badge}\n\n"
            f"• **Dataset Name:** `{prof.get('dataset_name')}`\n"
            f"• **Version Fingerprint:** `{prof.get('version')}`\n"
            f"• **Total Records:** **{prof.get('total_rows'):,}**\n"
            f"• **Total Columns:** **{prof.get('total_columns')}** ({num_c} numeric, {cat_c} categorical)\n"
            f"• **Target Metric:** `{prof.get('target_column') or 'None detected'}`\n"
            f"• **Identifier Column(s):** {', '.join([f'`{c}`' for c in id_c]) if id_c else 'Auto-indexed'}\n"
            f"• **Duplicate Rows:** {prof.get('duplicates_count')}\n"
            f"• **Missing Cells:** {prof.get('missing_cells_count')} ({prof.get('overall_missing_pct')}%)"
        )

    return "📊 Analytical execution completed successfully."
