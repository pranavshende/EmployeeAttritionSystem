import os
import json
import urllib.request
import logging
import re
import pandas as pd
from typing import Optional, Dict, Any, List

from . import data_loader as dl
from . import analytics_engine as ae
from . import query_planner as qp
from . import rag_engine as rag

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────
#  API Key & LLM Configuration
# ─────────────────────────────────────────────────────────────

def _load_gemini_api_key():
    """Load Gemini API Key from environment or .env file."""
    for var in ["GEMINI_API_KEY", "API_KEY", "API Key"]:
        val = os.environ.get(var)
        if val:
            return val.strip()

    base_dir = os.path.dirname(os.path.abspath(__file__))
    env_path = os.path.join(base_dir, ".env")
    if os.path.exists(env_path):
        try:
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    if "=" in line:
                        k, v = line.split("=", 1)
                        k = k.strip()
                        v = v.strip()
                        if k in ("GEMINI_API_KEY", "API_KEY", "API Key"):
                            return v
        except Exception as e:
            logger.warning(f"Error reading .env file: {e}")

    return None


_GEMINI_API_KEY = _load_gemini_api_key()


def _get_gemini_api_key():
    global _GEMINI_API_KEY
    if not _GEMINI_API_KEY:
        _GEMINI_API_KEY = _load_gemini_api_key()
    return _GEMINI_API_KEY


# ─────────────────────────────────────────────────────────────
#  Conversational Context Session Store with Dataset Version Tracking
# ─────────────────────────────────────────────────────────────

_sessions = {}


def get_session(session_id="default"):
    """Get or create a conversational context session dictionary with dataset version validation."""
    global _sessions
    current_ver = dl.get_dataset_version()
    if session_id not in _sessions:
        _sessions[session_id] = {
            "last_employee_id": None,
            "last_employee": None,
            "last_department": None,
            "last_role": None,
            "last_intent": None,
            "history": [],
            "dataset_version": current_ver,
        }

    session = _sessions[session_id]

    # Invalidate stale entity references if dataset changed during session
    if session.get("dataset_version") and session["dataset_version"] != current_ver:
        session["last_employee_id"] = None
        session["last_employee"] = None
        session["last_department"] = None
        session["last_role"] = None
        session["dataset_version"] = current_ver
    elif session.get("dataset_version") is None and current_ver:
        session["dataset_version"] = current_ver

    return session


def clear_sessions():
    """Reset all conversational sessions (e.g. when dataset is reset)."""
    global _sessions
    _sessions.clear()


# ─────────────────────────────────────────────────────────────
#  Dynamic Pregenerated Questions (Derived from Uploaded Data)
# ─────────────────────────────────────────────────────────────

def generate_dataset_questions():
    """
    Generate dynamic suggested questions derived STRICTLY from the active dataset.
    Never hardcodes fixed IDs or departments; dynamically inspects dl.df.
    Returns 6 tailored, high-value prompt suggestions.
    """
    if dl.df is None or len(dl.df) == 0:
        return [
            "How does employee attrition analysis work?",
            "What CSV columns should my dataset include?",
            "How do I upload an employee dataset?",
            "What are top indicators of employee turnover?",
        ]

    questions = []

    # 1. Real Sample Employee Lookup (Prefer high flight risk active employee)
    id_col = "EmployeeNumber" if "EmployeeNumber" in dl.df.columns else "EmployeeID" if "EmployeeID" in dl.df.columns else None
    sample_emp_id = None
    sample_role = None

    if id_col:
        # Prefer active employee with High risk
        high_risk_active = dl.df[(dl.df.get("AttritionFlag", 0) == 0) & (dl.df.get("RiskLevel", "") == "High")]
        if len(high_risk_active) > 0:
            row = high_risk_active.iloc[0]
            sample_emp_id = str(row[id_col])
            sample_role = str(row.get("JobRole", "Employee"))
        else:
            active = dl.df[dl.df.get("AttritionFlag", 0) == 0]
            if len(active) > 0:
                row = active.iloc[0]
                sample_emp_id = str(row[id_col])
                sample_role = str(row.get("JobRole", "Employee"))
            elif len(dl.df) > 0:
                row = dl.df.iloc[0]
                sample_emp_id = str(row[id_col])
                sample_role = str(row.get("JobRole", "Employee"))

    if sample_emp_id:
        if sample_role:
            questions.append(f"Tell me about employee #{sample_emp_id} ({sample_role})")
        else:
            questions.append(f"Tell me about employee #{sample_emp_id}")

    # 2. Department Deep Dive (Highest attrition department)
    depts = []
    if "Department" in dl.df.columns and "AttritionFlag" in dl.df.columns:
        dept_grp = dl.df.groupby("Department")["AttritionFlag"].agg(["count", "sum"])
        if len(dept_grp) > 0:
            dept_grp["rate"] = (dept_grp["sum"] / dept_grp["count"] * 100).round(1)
            dept_sorted = dept_grp.sort_values("rate", ascending=False)
            highest_dept = dept_sorted.index[0]
            highest_rate = dept_sorted.iloc[0]["rate"]
            depts = list(dept_sorted.index)
            questions.append(f"Why is {highest_dept} attrition at {highest_rate}%?")

    # 3. Department Comparison (Between top 2 departments if available)
    if len(depts) >= 2:
        questions.append(f"Compare {depts[0]} vs {depts[1]}")
    elif len(depts) == 1:
        questions.append(f"Analyze {depts[0]} department")

    # 4. Top Risk Factor Analysis
    try:
        factors = ae.get_contributing_factors()
        if factors and len(factors) > 0:
            top_factor = factors[0]["factor"]
            questions.append(f"How does {top_factor} impact turnover?")
        else:
            questions.append("What are the top contributing factors to attrition?")
    except Exception:
        questions.append("What are the top contributing factors to attrition?")

    # 5. Rankings
    questions.append("Rank all departments by attrition rate")

    # 6. Active High-Risk Watchlist / Retention Recommendations
    questions.append("Who are the top high-risk active employees?")

    return questions


# ─────────────────────────────────────────────────────────────
#  Dynamic Gemini Grounding & Prompt Builder
# ─────────────────────────────────────────────────────────────

def _build_dynamic_system_instruction():
    """Build dynamic Gemini system instructions incorporating whatever dataset is currently active."""
    if dl.df is None or dl.TOTAL_EMPLOYEES == 0:
        return (
            "You are AttritionAI, an expert HR Analytics and Workforce Intelligence Assistant for an Employee Attrition Dashboard.\n\n"
            "CURRENT STATUS: No employee dataset has been loaded or uploaded yet.\n"
            "The dashboard is currently in an empty state waiting for the user to upload a CSV file.\n\n"
            "Instructions:\n"
            "1. If the user asks questions about attrition rates, flight risks, departments, or employee data, warmly let them know that no dataset has been uploaded yet, and invite them to add/upload their workforce CSV using the upload zone or 'Upload CSV' button to instantly generate the full dashboard and analytics.\n"
            "2. For general greetings, chit-chat, or questions about HR concepts (e.g. 'What causes employee burnout?', 'How to improve retention?'), answer warmly, knowledgeably, and concisely.\n"
            "3. Format your responses in clean GitHub Markdown with clear bullet points and emojis."
        )

    dataset_name = dl.DATASET_NAME or "Active Dataset"
    total = dl.TOTAL_EMPLOYEES
    attr_count = dl.ATTRITION_COUNT
    attr_rate = dl.ATTRITION_RATE
    ret_count = dl.RETENTION_COUNT

    # Summarize departments in active dataset
    dept_stats = []
    if "Department" in dl.df.columns and "AttritionFlag" in dl.df.columns:
        try:
            dept_grouped = dl.df.groupby("Department")["AttritionFlag"].agg(["count", "sum"])
            for dept_name, row in dept_grouped.iterrows():
                d_tot = row["count"]
                d_att = row["sum"]
                d_rate = round(d_att / d_tot * 100, 1) if d_tot > 0 else 0
                dept_stats.append(f"{dept_name}: {d_att}/{d_tot} left ({d_rate}%)")
        except Exception:
            pass
    dept_str = "; ".join(dept_stats) if dept_stats else "N/A"

    # Summarize top risk factors
    try:
        factors = ae.get_contributing_factors()
        top_factors = [f"{f['factor']} (+{f.get('impact', 0)}pp)" for f in factors[:4]]
        factors_str = ", ".join(top_factors)
    except Exception:
        factors_str = "OverTime, Compensation, Tenure"

    # Summarize highest risk roles
    try:
        highest_role = ae._get_highest_risk_role()
        role_str = f"{highest_role['role']} ({highest_role['rate']}%, {highest_role['count']}/{highest_role['total']} departed)"
    except Exception:
        role_str = "High-risk roles"

    ai_notes = dl.DATASET_INFO.get("ai_summary", "")
    ai_section = f"\nAI Executive Summary of this dataset:\n{ai_notes}\n" if ai_notes else ""

    return (
        f"You are AttritionAI, an expert HR Analytics and Workforce Intelligence Assistant for an Employee Attrition Dashboard.\n\n"
        f"You are currently analyzing the active dataset: '{dataset_name}'.\n"
        f"Key facts about this verified dataset:\n"
        f"- Total employees in dataset: {total:,} ({attr_count:,} departed, {ret_count:,} retained, overall attrition rate: {attr_rate}%).\n"
        f"- Department breakdown: {dept_str}.\n"
        f"- Highest flight-risk job role: {role_str}.\n"
        f"- Top flight-risk drivers: {factors_str}.\n"
        f"{ai_section}\n"
        f"CRITICAL GROUND RULES:\n"
        f"1. When answering workforce or employee attrition questions, ALWAYS ground your answers in the numbers of this active dataset ('{dataset_name}'). Quote specific figures and percentages!\n"
        f"2. Clearly distinguish between HISTORICAL ATTRITION (employees who already left) and FUTURE FLIGHT RISK (currently active employees showing high predictive flight-risk indicators).\n"
        f"3. Never invent fictitious employees, predictions, or metrics.\n"
        f"4. Format your responses in clean GitHub Markdown with structured tables, clear bullet points, and emojis."
    )


def generate_ai_dataset_summary(dataset_name=None):
    """Generate an on-the-spot AI executive analysis of the currently loaded dataset using Gemini."""
    api_key = _get_gemini_api_key()
    dataset_name = dataset_name or dl.DATASET_NAME
    total = dl.TOTAL_EMPLOYEES
    attr_count = dl.ATTRITION_COUNT
    attr_rate = dl.ATTRITION_RATE

    if not api_key:
        fallback = (
            f"• **Stability**: Ingested {total:,} records with an overall attrition rate of {attr_rate}%.\n"
            f"• **Risk Drivers**: OverTime and low compensation cohorts show the steepest departure rates.\n"
            f"• **Action**: Review workload distribution and early-tenure employee onboarding."
        )
        dl.DATASET_INFO["ai_summary"] = fallback
        return fallback

    prompt = (
        f"You are an executive HR People Analytics Partner. We have just ingested a dataset '{dataset_name}' with {total:,} employees.\n"
        f"- Attrition rate: {attr_rate}% ({attr_count} employees left).\n"
        f"Generate a concise, high-impact 3-bullet executive summary for leadership: "
        f"1. Workforce Stability Assessment, 2. Primary Flight-Risk Drivers, 3. Immediate Retention Recommendation. "
        f"Keep it professional, data-driven, and brief (under 120 words)."
    )

    models = ["gemini-2.5-flash", "gemini-flash-latest"]
    for model in models:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.5, "maxOutputTokens": 300}
        }
        try:
            req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=12) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                candidates = data.get("candidates", [])
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    if parts and "text" in parts[0]:
                        summary = parts[0]["text"].strip()
                        dl.DATASET_INFO["ai_summary"] = summary
                        return summary
        except Exception as e:
            logger.warning(f"Error generating AI dataset summary: {e}")

    fallback = (
        f"• **Stability**: Ingested {total:,} records with an overall attrition rate of {attr_rate}%.\n"
        f"• **Risk Drivers**: OverTime and low compensation cohorts show the steepest departure rates.\n"
        f"• **Action**: Review workload distribution and early-tenure employee onboarding."
    )
    dl.DATASET_INFO["ai_summary"] = fallback
    return fallback


def _call_gemini_api(user_message, custom_context=None):
    """Call Google Gemini API for freeform or conversational chat with optional custom grounding context."""
    api_key = _get_gemini_api_key()
    if not api_key:
        return None

    system_instruction = _build_dynamic_system_instruction()
    if custom_context:
        system_instruction = f"{system_instruction}\n\n{custom_context}"

    models = ["gemini-2.5-flash", "gemini-flash-latest"]
    for model in models:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        payload = {
            "contents": [{"parts": [{"text": user_message}]}],
            "systemInstruction": {"parts": [{"text": system_instruction}]},
            "generationConfig": {
                "temperature": 0.7,
                "maxOutputTokens": 800,
            }
        }
        try:
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=12) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                candidates = data.get("candidates", [])
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    if parts and "text" in parts[0]:
                        return parts[0]["text"].strip()
        except urllib.error.HTTPError as e:
            logger.warning(f"Gemini call to {model} failed: {e}")
            if e.code == 429:
                break
            continue
        except Exception as e:
            logger.warning(f"Gemini call to {model} failed: {e}")
            continue

    return None


# ─────────────────────────────────────────────────────────────
#  Entity Extractors (Alphanumeric IDs, Departments, Roles)
# ─────────────────────────────────────────────────────────────

_EMP_ID_FALSE_POSITIVES = {
    "rate", "rates", "turnover", "attrition", "count", "score",
    "list", "table", "details", "info", "overview", "kpi", "kpis",
    "summary", "analysis", "data", "dataset", "status", "who", "why",
    "how", "what", "which", "where", "when", "is", "are", "tell", "show",
    "about", "me", "the", "an", "a", "this", "that", "give", "please", "can",
    "you", "do", "i", "we", "he", "she", "they", "them", "him", "her",
    "leave", "stay", "leaving", "risk", "high", "low", "medium", "profile",
    "card", "report", "stats", "view", "find", "check"
}


def _extract_employee_id(text):
    """
    Extract an employee ID/number from user query text.
    Handles:
      - '#E02744', '#104', '#EMP-01'
      - 'employee E02744', 'emp #101', 'id 105'
      - Alphanumeric codes: 'E02744', 'EMP102'
      - Contextual verbs: 'tell me about 104', 'details for E001'
      - Direct token verification against active dataset ID columns
    """
    if not text:
        return None

    cleaned_text = text.strip()

    # 1. Direct hashtag match: #E02744, #104, #EMP-01
    m = re.search(r"#([a-zA-Z0-9_\-]+)", cleaned_text)
    if m:
        val = m.group(1).strip()
        if val.lower() not in _EMP_ID_FALSE_POSITIVES and (any(c.isdigit() for c in val) or len(val) >= 3):
            return val

    # 2. Keywords followed by ID: employee [id] [:] #?E02744 / 104
    m = re.search(
        r"\b(?:employee|emp|worker|staff|user|record)\s+(?:id|number|no|#|\:)?\s*#?([a-zA-Z0-9_\-]+)\b",
        cleaned_text,
        re.IGNORECASE,
    )
    if m:
        val = m.group(1).strip()
        if val.lower() not in _EMP_ID_FALSE_POSITIVES and (any(c.isdigit() for c in val) or len(val) >= 3):
            return val

    # 3. Alphanumeric employee ID code pattern: E02744, EMP102, EMP-01
    m = re.search(r"\b([A-Za-z]{1,4}[-_]?[0-9]{2,8})\b", cleaned_text)
    if m:
        val = m.group(1).strip()
        if val.lower() not in _EMP_ID_FALSE_POSITIVES:
            return val

    # 4. Contextual lookup verbs: 'tell me about 104', 'details for E001'
    m = re.search(
        r"\b(?:about|details\s+for|details\s+on|who\s+is|look\s*up|status\s+of)\s+#?([a-zA-Z0-9_\-]+)\b",
        cleaned_text,
        re.IGNORECASE,
    )
    if m:
        val = m.group(1).strip()
        if val.lower() not in _EMP_ID_FALSE_POSITIVES and any(c.isdigit() for c in val):
            return val

    # 5. Direct token verification against active dataset ID columns
    if dl.df is not None and len(dl.df) > 0:
        id_candidates = ["EmployeeNumber", "EmployeeID", "id", "emp_id", "emp_number"]
        cols = [c for c in id_candidates if c in dl.df.columns]
        if cols:
            tokens = re.findall(r"\b#?([a-zA-Z0-9_\-]+)\b", cleaned_text)
            for token in tokens:
                clean_tok = token.lstrip("#").strip().lower()
                if len(clean_tok) < 2 or clean_tok in _EMP_ID_FALSE_POSITIVES:
                    continue
                for c in cols:
                    if (dl.df[c].astype(str).str.strip().str.lower() == clean_tok).any():
                        return token.lstrip("#").strip()

    return None


def _get_active_departments():
    """Return a list of unique department names present in the active dataset."""
    if dl.df is None or len(dl.df) == 0 or "Department" not in dl.df.columns:
        return []
    return [str(d).strip() for d in dl.df["Department"].dropna().unique() if str(d).strip()]


def _extract_department(text):
    """
    Dynamically detect department name mentioned in user text.
    Matches aliases (e.g. 'r&d' -> 'Research & Development', 'hr' -> 'Human Resources')
    and any custom department name present in the loaded dataset.
    """
    if not text or dl.df is None or "Department" not in dl.df.columns:
        return None

    cleaned = text.lower()
    depts = _get_active_departments()
    if not depts:
        return None

    # Common aliases
    alias_map = {
        "r&d": "Research & Development",
        "r & d": "Research & Development",
        "research & development": "Research & Development",
        "research and development": "Research & Development",
        "hr": "Human Resources",
        "human resources": "Human Resources",
        "human resource": "Human Resources",
        "sales": "Sales",
        "engineering": "Engineering",
        "operations": "Operations",
        "marketing": "Marketing",
        "finance": "Finance",
        "customer support": "Customer Support",
        "support": "Customer Support",
    }

    # 1. Alias check
    for alias, standard in alias_map.items():
        if re.search(r"\b" + re.escape(alias) + r"\b", cleaned):
            for d in depts:
                if d.lower() == standard.lower():
                    return d

    # 2. Direct match against active dataset departments (longest first)
    for d in sorted(depts, key=len, reverse=True):
        if re.search(r"\b" + re.escape(d.lower()) + r"\b", cleaned):
            return d

    return None


def _extract_departments_to_compare(text):
    """Extract two departments to compare from user text, or return top 2 departments."""
    depts = _get_active_departments()
    if len(depts) < 2:
        return depts

    found = []
    cleaned = text.lower()

    alias_map = {
        "r&d": "Research & Development",
        "research & development": "Research & Development",
        "research and development": "Research & Development",
        "hr": "Human Resources",
        "human resources": "Human Resources",
        "sales": "Sales",
        "engineering": "Engineering",
        "operations": "Operations",
        "marketing": "Marketing",
        "finance": "Finance",
        "customer support": "Customer Support",
    }

    for alias, standard in alias_map.items():
        if re.search(r"\b" + re.escape(alias) + r"\b", cleaned):
            for d in depts:
                if d.lower() == standard.lower() and d not in found:
                    found.append(d)

    for d in sorted(depts, key=len, reverse=True):
        if re.search(r"\b" + re.escape(d.lower()) + r"\b", cleaned) and d not in found:
            found.append(d)

    if len(found) >= 2:
        return found[:2]

    # If general comparison, sort departments by size and pick top 2
    if dl.df is not None and "Department" in dl.df.columns:
        counts = dl.df["Department"].value_counts()
        top_depts = list(counts.index[:2])
        return top_depts

    return depts[:2]


# ─────────────────────────────────────────────────────────────
#  Modular Intent Handlers & Formatted Responses
# ─────────────────────────────────────────────────────────────

def _format_employee_card(emp):
    """
    Format a detailed, visually clear markdown profile card for an individual employee.
    Explicitly distinguishes historical attrition (departed) from future flight risk (active).
    """
    emp_no = emp["employee_number"]
    role = emp["job_role"]
    dept = emp["department"]
    age = emp["age"]
    gender = emp["gender"]
    marital = emp["marital_status"]
    salary = emp["monthly_income"]
    ot = emp["overtime"]
    tenure = emp["years_at_company"]
    commute = emp["distance_from_home"]
    travel = emp["business_travel"]
    job_sat = emp["job_satisfaction"]
    job_sat_lbl = emp["job_satisfaction_label"]
    env_sat = emp["env_satisfaction"]
    env_sat_lbl = emp["env_satisfaction_label"]
    wlb = emp["work_life_balance"]
    wlb_lbl = emp["work_life_balance_label"]
    stock = emp["stock_option_level"]
    risk_score = emp["risk_score"]
    risk_lvl = emp["risk_level"]
    attrition = emp["attrition"]
    reasons = emp.get("risk_reasons", [])

    is_departed = (attrition == "Yes" or emp.get("attrition_flag") is True)

    if is_departed:
        status_badge = "🔴 **Left Company (Historical Attrition)**"
        risk_badge = f"📉 **Historical Exit Profile (Score: {risk_score}/8)**"
        status_note = "⚠️ *This employee has already departed the organization. Their profile reflects historical exit record data.*"
        rec_str = (
            "📋 **Historical Exit Review Summary**:\n"
            "This employee departed prior to retention intervention. "
            f"Primary exit signals on file: {', '.join(reasons) if reasons else 'Standard turnover indicators'}. "
            f"Use these insights to address similar flight risks currently active in the {dept} department."
        )
    else:
        status_badge = "🟢 **Active Employee (Retained)**"
        risk_badge = f"🔥 **{risk_lvl} Flight Risk ({risk_score}/8)**" if risk_lvl == "High" else f"⚡ **{risk_lvl} Flight Risk ({risk_score}/8)**"
        status_note = "✅ *This employee is currently active. Early retention intervention can mitigate flight risk.*"
        if risk_lvl == "High":
            rec_str = (
                f"💡 **Recommended Retention Intervention (High Flight Risk)**:\n"
                f"• Schedule an urgent 1-on-1 check-in within 5 business days.\n"
                f"• Priority Action: Review {reasons[0].lower() if reasons else 'workload and compensation'}.\n"
                f"• Explore equity participation (Stock Level currently {stock}) or flexible working arrangements."
            )
        elif risk_lvl == "Medium":
            rec_str = (
                f"💡 **Recommended Retention Intervention (Moderate Risk)**:\n"
                f"• Conduct quarterly engagement review.\n"
                f"• Monitor overtime hours (currently {ot}) and check job satisfaction."
            )
        else:
            rec_str = (
                "💡 **Recommended Retention Intervention (Low Risk)**:\n"
                "• Profile reflects healthy retention signals.\n"
                "• Maintain standard career development pathways and recognition."
            )

    salary_str = f"₹{salary:,.0f}/month" if salary else "Not specified"

    if reasons:
        reasons_str = "\n".join([f"  • ⚠️ {r}" for r in reasons])
    else:
        reasons_str = "  • ✅ No major flight risk triggers detected (Stable profile)"

    return (
        f"👤 **Employee Profile: #{emp_no}**\n\n"
        f"**Status:** {status_badge} &nbsp;|&nbsp; **Flight Risk:** {risk_badge}\n\n"
        f"{status_note}\n\n"
        f"📌 **Role & Demographics:**\n"
        f"  • **Role:** {role} ({dept})\n"
        f"  • **Demographics:** {age} yrs old • {gender} • {marital}\n\n"
        f"💼 **Tenure & Compensation:**\n"
        f"  • **Company Tenure:** {tenure} {'years' if tenure != 1 else 'year'}\n"
        f"  • **Monthly Salary:** {salary_str}\n"
        f"  • **Stock Option Level:** {stock} (Equity Tier)\n\n"
        f"⚙️ **Working Conditions & Engagement:**\n"
        f"  • **OverTime:** **{ot}** {'⚠️ (Major Turnover Driver)' if ot == 'Yes' else '✅ (Standard Hours)'}\n"
        f"  • **Job Satisfaction:** Level {job_sat}/4 ({job_sat_lbl})\n"
        f"  • **Environment Satisfaction:** Level {env_sat}/4 ({env_sat_lbl})\n"
        f"  • **Work-Life Balance:** Level {wlb}/4 ({wlb_lbl})\n"
        f"  • **Commute & Travel:** {commute} miles away • {travel}\n\n"
        f"🔍 **Flight Risk Diagnostics ({risk_score}/8 Criteria):**\n"
        f"{reasons_str}\n\n"
        f"{rec_str}"
    )


def _all_departments_response():
    """
    Generate comprehensive breakdown across all active departments in the dataset.
    """
    if dl.df is None or len(dl.df) == 0:
        dl.ensure_dataset_loaded()
        if dl.df is None or len(dl.df) == 0:
            return {
                "response": "⚠️ No employee dataset is currently loaded.",
                "suggestions": ["How do I upload a CSV?"],
            }

    dept_data = ae.get_department_data()
    if not dept_data:
        return {"response": "No department data found in this dataset.", "suggestions": []}

    rows = []
    for d in dept_data:
        tier = "🔴 High Risk" if d["rate"] >= 20 else "🟡 Moderate" if d["rate"] >= 15 else "🟢 Stable"
        active_count = d["total"] - d["attrition"]
        rows.append(
            f"| **{d['label']}** | {d['total']:,} | {d['attrition']:,} | {active_count:,} | **{d['rate']}%** | {tier} |"
        )

    table_md = (
        "| Department | Total Staff | Departed | Retained | Attrition Rate | Flight Risk Tier |\n"
        "| :--- | :---: | :---: | :---: | :---: | :--- |\n"
        + "\n".join(rows)
    )

    highest = dept_data[0]
    total_depts = len(dept_data)

    return {
        "response": (
            f"🏢 **Workforce Breakdown Across All {total_depts} Departments**\n\n"
            f"{table_md}\n\n"
            f"📌 **Key Observations:**\n"
            f"• **Highest Flight Risk:** **{highest['label']}** leads turnover at **{highest['rate']}%**.\n"
            f"• Ask *\"Analyze {highest['label']} department\"* for deep dive metrics or *\"Compare {dept_data[0]['label']} vs {dept_data[1]['label'] if len(dept_data) > 1 else dept_data[0]['label']}\"*."
        ),
        "data": {"departments": dept_data},
        "suggestions": [
            f"Analyze {highest['label']} department",
            f"Compare {dept_data[0]['label']} vs {dept_data[1]['label']}" if len(dept_data) > 1 else "Rank all departments by attrition rate",
            "Who are the top high-risk active employees?",
        ],
    }


def _department_deep_dive_response(dept_name):
    """
    Generate complete, robust department analysis from active dataset.
    Calculates headcount, departed, attrition rate, income, overtime, satisfaction,
    and role breakdown for the specified department.
    """
    if dl.df is None or len(dl.df) == 0 or "Department" not in dl.df.columns:
        return {
            "response": "⚠️ No dataset is currently loaded to perform department analysis.",
            "suggestions": ["How do I upload a CSV?"],
        }

    dept_df = dl.df[dl.df["Department"].astype(str).str.lower() == dept_name.lower()]
    if len(dept_df) == 0:
        depts = _get_active_departments()
        dept_list = ", ".join([f"`{d}`" for d in depts])
        return {
            "response": f"🔍 Department `{dept_name}` was not found in the active dataset.\n\nAvailable departments: {dept_list}.",
            "suggestions": [f"Analyze {d}" for d in depts[:3]],
        }

    total_dept = len(dept_df)
    departed = int(dept_df["AttritionFlag"].sum()) if "AttritionFlag" in dept_df.columns else 0
    active = total_dept - departed
    dept_rate = round(departed / total_dept * 100, 1) if total_dept > 0 else 0.0

    overall_rate = dl.ATTRITION_RATE
    diff_pp = round(dept_rate - overall_rate, 1)
    diff_badge = f"+{diff_pp}pp higher than company average" if diff_pp > 0 else f"{abs(diff_pp)}pp lower than company average"

    # Compensation & workload
    avg_salary = round(float(dept_df["MonthlyIncome"].mean()), 0) if "MonthlyIncome" in dept_df.columns else 0
    ot_rate = round(float(dept_df["OvertimeFlag"].mean() * 100), 1) if "OvertimeFlag" in dept_df.columns else 0
    avg_job_sat = round(float(dept_df["JobSatisfaction"].mean()), 2) if "JobSatisfaction" in dept_df.columns else 0
    avg_wlb = round(float(dept_df["WorkLifeBalance"].mean()), 2) if "WorkLifeBalance" in dept_df.columns else 0

    # Role breakdown within department
    role_rows = []
    if "JobRole" in dept_df.columns and "AttritionFlag" in dept_df.columns:
        role_grp = dept_df.groupby("JobRole")["AttritionFlag"].agg(["count", "sum"])
        role_grp["rate"] = (role_grp["sum"] / role_grp["count"] * 100).round(1)
        role_sorted = role_grp.sort_values("rate", ascending=False)
        for role_name, r in role_sorted.iterrows():
            role_rows.append(f"| {role_name} | {r['count']} | {r['sum']} | **{r['rate']}%** |")

    role_table = ""
    if role_rows:
        role_table = (
            "\n\n**Job Role Breakdown within " + dept_name + ":**\n\n"
            "| Job Role | Total | Departed | Attrition Rate |\n"
            "| :--- | :---: | :---: | :---: |\n"
            + "\n".join(role_rows)
        )

    # Tailored Department Action Plan
    if dept_rate > overall_rate:
        action_plan = (
            f"💡 **Targeted Retention Plan for {dept_name}**:\n"
            f"• **Priority Level:** 🔴 High Attention ({diff_badge}).\n"
            f"• **Workload:** {ot_rate}% of {dept_name} employees work overtime. Institute strict caps on consecutive overtime shifts.\n"
            f"• **Compensation:** Benchmark average monthly salary (₹{avg_salary:,.0f}) against company median to ensure competitive compensation.\n"
            f"• **Engagement:** Focus retention interviews on high-attrition roles in this department."
        )
    else:
        action_plan = (
            f"💡 **Targeted Retention Plan for {dept_name}**:\n"
            f"• **Priority Level:** 🟢 Healthy Retention ({diff_badge}).\n"
            f"• **Best Practices:** Document effective team norms and manager practices from {dept_name} to replicate across higher-risk departments."
        )

    response_text = (
        f"🏢 **Complete Department Deep Dive: {dept_name}**\n\n"
        f"• **Total Headcount:** **{total_dept:,}** employees ({active:,} active, {departed:,} departed)\n"
        f"• **Department Attrition Rate:** **{dept_rate}%** ({diff_badge})\n"
        f"• **Average Monthly Income:** **₹{avg_salary:,.0f}**\n"
        f"• **OverTime Rate:** **{ot_rate}%** working overtime hours\n"
        f"• **Average Job Satisfaction:** **{avg_job_sat} / 4.0**\n"
        f"• **Average Work-Life Balance:** **{avg_wlb} / 4.0**"
        f"{role_table}\n\n"
        f"{action_plan}"
    )

    other_depts = [d for d in _get_active_departments() if d.lower() != dept_name.lower()]
    suggestions = [
        f"Compare {dept_name} vs {other_depts[0]}" if other_depts else "Rank all departments",
        "Who is likely to leave?",
        "What recommendations do you have?",
    ]

    return {
        "response": response_text,
        "data": {
            "department": dept_name,
            "total": total_dept,
            "departed": departed,
            "active": active,
            "rate": dept_rate,
            "avg_salary": avg_salary,
            "overtime_rate": ot_rate,
        },
        "suggestions": suggestions,
    }


def _department_comparison_response(dept1, dept2):
    """
    Generate side-by-side Markdown comparison table and analytical takeaway between two departments.
    """
    if dl.df is None or len(dl.df) == 0 or "Department" not in dl.df.columns:
        return {
            "response": "⚠️ No dataset loaded to perform department comparison.",
            "suggestions": ["How do I upload a CSV?"],
        }

    df1 = dl.df[dl.df["Department"].astype(str).str.lower() == dept1.lower()]
    df2 = dl.df[dl.df["Department"].astype(str).str.lower() == dept2.lower()]

    if len(df1) == 0 or len(df2) == 0:
        depts = _get_active_departments()
        return {
            "response": f"🔍 Could not find both departments `{dept1}` and `{dept2}` in active dataset.\n\nAvailable departments: {', '.join(depts)}.",
            "suggestions": [f"Compare {depts[0]} vs {depts[1]}"] if len(depts) >= 2 else ["Overall stats"],
        }

    # Department 1 stats
    tot1 = len(df1)
    att1 = int(df1["AttritionFlag"].sum()) if "AttritionFlag" in df1.columns else 0
    rate1 = round(att1 / tot1 * 100, 1) if tot1 > 0 else 0
    sal1 = round(float(df1["MonthlyIncome"].mean()), 0) if "MonthlyIncome" in df1.columns else 0
    ot1 = round(float(df1["OvertimeFlag"].mean() * 100), 1) if "OvertimeFlag" in df1.columns else 0
    sat1 = round(float(df1["JobSatisfaction"].mean()), 2) if "JobSatisfaction" in df1.columns else 0
    wlb1 = round(float(df1["WorkLifeBalance"].mean()), 2) if "WorkLifeBalance" in df1.columns else 0

    # Department 2 stats
    tot2 = len(df2)
    att2 = int(df2["AttritionFlag"].sum()) if "AttritionFlag" in df2.columns else 0
    rate2 = round(att2 / tot2 * 100, 1) if tot2 > 0 else 0
    sal2 = round(float(df2["MonthlyIncome"].mean()), 0) if "MonthlyIncome" in df2.columns else 0
    ot2 = round(float(df2["OvertimeFlag"].mean() * 100), 1) if "OvertimeFlag" in df2.columns else 0
    sat2 = round(float(df2["JobSatisfaction"].mean()), 2) if "JobSatisfaction" in df2.columns else 0
    wlb2 = round(float(df2["WorkLifeBalance"].mean()), 2) if "WorkLifeBalance" in df2.columns else 0

    rate_diff = round(rate1 - rate2, 1)
    if rate_diff > 0:
        higher_dept = dept1
        lower_dept = dept2
        gap_str = f"**{dept1}** has a **{rate_diff}pp higher** attrition rate than **{dept2}**."
    elif rate_diff < 0:
        higher_dept = dept2
        lower_dept = dept1
        gap_str = f"**{dept2}** has a **{abs(rate_diff)}pp higher** attrition rate than **{dept1}**."
    else:
        gap_str = f"Both **{dept1}** and **{dept2}** share identical attrition rates of **{rate1}%**."

    table_md = (
        f"| Metric | {dept1} | {dept2} | Difference |\n"
        f"| :--- | :---: | :---: | :---: |\n"
        f"| **Headcount** | {tot1:,} | {tot2:,} | {tot1 - tot2:+d} |\n"
        f"| **Departed** | {att1:,} | {att2:,} | {att1 - att2:+d} |\n"
        f"| **Attrition Rate** | **{rate1}%** | **{rate2}%** | **{rate1 - rate2:+.1f}pp** |\n"
        f"| **Avg Monthly Income** | ₹{sal1:,.0f} | ₹{sal2:,.0f} | ₹{sal1 - sal2:+,.0f} |\n"
        f"| **OverTime Rate** | {ot1}% | {ot2}% | {ot1 - ot2:+.1f}pp |\n"
        f"| **Job Satisfaction** | {sat1} / 4.0 | {sat2} / 4.0 | {sat1 - sat2:+.2f} |\n"
        f"| **Work-Life Balance** | {wlb1} / 4.0 | {wlb2} / 4.0 | {wlb1 - wlb2:+.2f} |"
    )

    response_text = (
        f"⚖️ **Department Comparison: {dept1} vs {dept2}**\n\n"
        f"{table_md}\n\n"
        f"📌 **Key Takeaway & Analysis:**\n"
        f"{gap_str} "
        f"Notice that OverTime is {ot1}% in {dept1} vs {ot2}% in {dept2}, "
        f"while average compensation is ₹{sal1:,.0f} vs ₹{sal2:,.0f}. "
        f"Target retention initiatives in the higher-turnover group to narrow the gap."
    )

    return {
        "response": response_text,
        "data": {
            dept1: {"total": tot1, "attrition": att1, "rate": rate1, "salary": sal1},
            dept2: {"total": tot2, "attrition": att2, "rate": rate2, "salary": sal2},
        },
        "suggestions": [
            f"Analyze {dept1} department",
            f"Analyze {dept2} department",
            "Rank all departments by attrition rate",
        ],
    }


def _rankings_response(entity_type="department"):
    """
    Generate ranked leaderboard tables (by Attrition Rate) for departments or job roles.
    """
    if dl.df is None or len(dl.df) == 0:
        return {
            "response": "⚠️ No dataset loaded to compute rankings.",
            "suggestions": ["How do I upload a CSV?"],
        }

    if entity_type == "role":
        role_data = ae.get_job_role_data()
        if not role_data:
            return {"response": "No job role data available.", "suggestions": []}

        rows = []
        for i, r in enumerate(role_data, 1):
            tier = "🔴 High Risk" if r["rate"] >= 20 else "🟡 Moderate" if r["rate"] >= 12 else "🟢 Stable"
            rows.append(f"| {i} | {r['label']} | {r['total']} | {r['attrition']} | **{r['rate']}%** | {tier} |")

        table_md = (
            "| Rank | Job Role | Total | Departed | Attrition Rate | Flight Risk Tier |\n"
            "| :---: | :--- | :---: | :---: | :---: | :---: |\n"
            + "\n".join(rows)
        )

        highest = role_data[0]
        return {
            "response": (
                f"👔 **Job Role Attrition Rankings (Highest to Lowest)**\n\n"
                f"{table_md}\n\n"
                f"📌 **Key Insight:** **{highest['label']}** ranks #1 in turnover at **{highest['rate']}%**."
            ),
            "data": {"roles": role_data},
            "suggestions": [
                "Rank departments by attrition rate",
                "Why do employees leave?",
                "Who is likely to leave?",
            ],
        }

    # Department rankings
    dept_data = ae.get_department_data()
    if not dept_data:
        return {"response": "No department data available.", "suggestions": []}

    rows = []
    for i, d in enumerate(dept_data, 1):
        tier = "🔴 High" if d["rate"] >= 20 else "🟡 Moderate" if d["rate"] >= 15 else "🟢 Stable"
        rows.append(f"| {i} | {d['label']} | {d['total']:,} | {d['attrition']:,} | **{d['rate']}%** | {tier} |")

    table_md = (
        "| Rank | Department | Total Headcount | Departed | Attrition Rate | Flight Risk Tier |\n"
        "| :---: | :--- | :---: | :---: | :---: | :---: |\n"
        + "\n".join(rows)
    )

    highest = dept_data[0]
    lowest = dept_data[-1]

    return {
        "response": (
            f"🏆 **Department Attrition Rankings (Highest to Lowest)**\n\n"
            f"{table_md}\n\n"
            f"📌 **Key Insight:** **{highest['label']}** leads turnover at **{highest['rate']}%**, "
            f"while **{lowest['label']}** is the most stable department at **{lowest['rate']}%** "
            f"(a {round(highest['rate'] - lowest['rate'], 1)}pp spread)."
        ),
        "data": {"departments": dept_data},
        "suggestions": [
            f"Analyze {highest['label']} department",
            f"Compare {highest['label']} vs {lowest['label']}",
            "Who are the top high-risk active employees?",
        ],
    }


def _historical_attrition_response():
    """
    Factual summary of HISTORICAL turnover (employees who have already left).
    Contrasts directly with future predictive flight risk.
    """
    if dl.df is None or len(dl.df) == 0:
        return {
            "response": "⚠️ No dataset is currently loaded.",
            "suggestions": ["How do I upload a CSV?"],
        }

    kpis = ae.get_kpis()
    dept_data = ae.get_department_data()

    dept_lines = []
    for d in dept_data:
        dept_lines.append(f"  • **{d['label']}**: {d['attrition']:,} departed ({d['rate']}% exit rate)")

    return {
        "response": (
            f"📉 **Historical Attrition Review (Past Departures)**\n\n"
            f"• **Total Historical Departures:** **{kpis['attrition_count']:,}** employees left the organization\n"
            f"• **Historical Turnover Rate:** **{kpis['attrition_rate']}%** of all recorded staff\n"
            f"• **Active Retained Employees:** **{kpis['retention_count']:,}** employees remain\n\n"
            f"🏛️ **Departures by Department:**\n"
            + "\n".join(dept_lines) + "\n\n"
            f"⚠️ **Note on Data Types:** This represents confirmed *historical* turnover (employees who already exited). "
            f"To view *currently active* employees who are at future flight risk, ask *\"Who is likely to leave?\"*."
        ),
        "data": {"historical_attrition": kpis},
        "suggestions": [
            "Who is likely to leave?",
            "Why do employees leave?",
            "What recommendations do you have?",
        ],
    }


def _who_likely_leave_response():
    """
    Summary of FUTURE FLIGHT RISK among CURRENTLY ACTIVE employees.
    Uses RiskScore (0-8) and RiskLevel ('High') calculated dynamically from the active dataset.
    Never invents predictions.
    """
    if dl.df is None or len(dl.df) == 0:
        return {
            "response": "⚠️ No dataset is currently loaded.",
            "suggestions": ["How do I upload a CSV?"],
        }

    high_risk = ae.get_high_risk_employees(min_risk_score=4, page=1, per_page=5)
    employees = high_risk["employees"]
    total_high = high_risk["total"]

    emp_lines = []
    for emp in employees[:5]:
        emp_lines.append(
            f"  • **#{emp['employee_number']}** — {emp['job_role']}, {emp['department']}, "
            f"₹{emp['monthly_income']:,}/mo, OT: {emp['overtime']}, "
            f"Risk: **{emp['risk_level']}** ({emp['risk_score']}/8)"
        )

    return {
        "response": (
            f"🚨 **Active High-Risk Watchlist (Future Flight Risk)**\n\n"
            f"There are **{total_high:,}** currently active employees matching 4+ flight risk indicators.\n\n"
            f"**Top 5 highest-risk active employees:**\n"
            + "\n".join(emp_lines) + "\n\n"
            f"📌 **Predictive Risk Criteria Grounding:**\n"
            f"Scores are evaluated on: OverTime, low income, tenure ≤ 2 years, low satisfaction (job & env), "
            f"no equity/stock options, young age (≤25), and poor work-life balance.\n\n"
            f"Ask about any specific employee (e.g. *\"Tell me about #{employees[0]['employee_number']}\"*) to see their intervention plan."
        ),
        "data": {"total_high_risk": total_high, "top_employees": employees[:5]},
        "suggestions": [
            f"Tell me about employee #{employees[0]['employee_number']}" if employees else "Why do employees leave?",
            "Why do employees leave?",
            "What recommendations do you have?",
        ],
    }


def _why_leave_response():
    """Top contributing factors to attrition ranked by differential impact."""
    if dl.df is None or len(dl.df) == 0:
        return {"response": "⚠️ No dataset loaded.", "suggestions": []}

    factors = ae.get_contributing_factors()
    factor_lines = []
    for i, f in enumerate(factors[:5], 1):
        factor_lines.append(
            f"  {i}. **{f['factor']}** — **+{f['impact']}pp impact** "
            f"({f['high_risk_group']}: {f['high_risk_rate']}% vs "
            f"{f['low_risk_group']}: {f['low_risk_rate']}%)"
        )

    return {
        "response": (
            "📈 **Top Contributing Factors to Turnover**\n\n"
            "Ranked by differential impact on departure rates in this dataset:\n\n"
            + "\n".join(factor_lines) + "\n\n"
            "The strongest drivers reflect workload demands, compensation positioning, and onboarding experience."
        ),
        "data": {"factors": factors[:5]},
        "suggestions": [
            "How does overtime affect attrition?",
            "What about salary impact?",
            "Recommendations",
        ],
    }


def _overtime_response():
    """Overtime and workload impact analysis."""
    if dl.df is None or len(dl.df) == 0:
        return {"response": "⚠️ No dataset loaded.", "suggestions": []}

    ot_data = ae.get_overtime_data()
    ot_yes = next((d for d in ot_data if str(d["label"]).lower() == "yes"), {})
    ot_no = next((d for d in ot_data if str(d["label"]).lower() == "no"), {})

    yes_rate = ot_yes.get("rate", 0)
    no_rate = ot_no.get("rate", 0)
    multiplier = round(yes_rate / max(no_rate, 0.1), 1)

    return {
        "response": (
            "⏰ **OverTime & Workload Impact on Turnover**\n\n"
            f"• **OverTime = Yes**: {ot_yes.get('attrition', 0):,}/{ot_yes.get('total', 0):,} employees — **{yes_rate}%** attrition\n"
            f"• **OverTime = No**: {ot_no.get('attrition', 0):,}/{ot_no.get('total', 0):,} employees — **{no_rate}%** attrition\n\n"
            f"📌 **Key Finding:** Employees working overtime leave at **{multiplier}x the rate** of standard-hours peers. "
            f"Sustained overtime is one of the strongest leading indicators of impending attrition."
        ),
        "data": {"overtime": ot_data},
        "suggestions": [
            "What about salary impact?",
            "Who is at risk?",
            "Recommendations",
        ],
    }


def _salary_response():
    """Salary bands vs attrition."""
    if dl.df is None or len(dl.df) == 0:
        return {"response": "⚠️ No dataset loaded.", "suggestions": []}

    income_data = ae.get_income_data()
    lines = []
    for band in income_data:
        lines.append(f"  • **{band['label']}**: {band['attrition']:,}/{band['total']:,} — **{band['rate']}%**")

    return {
        "response": (
            "💰 **Monthly Compensation vs Turnover**\n\n"
            + "\n".join(lines) + "\n\n"
            "Lower compensation tiers show significantly elevated departure rates. "
            "Compensation compression is a major driver during the first 2-3 years."
        ),
        "data": {"income_bands": income_data},
        "suggestions": [
            "Stock options impact?",
            "Tenure effect?",
            "Recommendations",
        ],
    }


def _satisfaction_response():
    """Job and environment satisfaction impact."""
    if dl.df is None or len(dl.df) == 0:
        return {"response": "⚠️ No dataset loaded.", "suggestions": []}

    sat_data = ae.get_satisfaction_data()
    job_lines = [f"  • **{s['label']}**: {s['attrition']:,}/{s['total']:,} — **{s['rate']}%**" for s in sat_data.get("job_satisfaction", [])]
    env_lines = [f"  • **{s['label']}**: {s['attrition']:,}/{s['total']:,} — **{s['rate']}%**" for s in sat_data.get("env_satisfaction", [])]

    return {
        "response": (
            "😊 **Satisfaction & Morale vs Turnover**\n\n"
            "**Job Satisfaction:**\n" + "\n".join(job_lines) + "\n\n"
            "**Environment Satisfaction:**\n" + "\n".join(env_lines) + "\n\n"
            "Employees in Level 1 (Low) satisfaction leave at dramatically higher rates than peers in Levels 3 & 4."
        ),
        "data": sat_data,
        "suggestions": [
            "How does overtime affect attrition?",
            "Who is at risk?",
            "Recommendations",
        ],
    }


def _tenure_response():
    """Tenure at company breakdown."""
    if dl.df is None or len(dl.df) == 0:
        return {"response": "⚠️ No dataset loaded.", "suggestions": []}

    tenure_data = ae.get_tenure_data()
    lines = [f"  • **{band['label']}**: {band['attrition']:,}/{band['total']:,} — **{band['rate']}%**" for band in tenure_data]

    return {
        "response": (
            "📅 **Company Tenure vs Attrition**\n\n"
            + "\n".join(lines) + "\n\n"
            "Early-career staff (0-2 years) exhibit the sharpest turnover curve. "
            "Formal 30-60-90 day onboarding checkpoints significantly reduce this early attrition."
        ),
        "data": {"tenure_bands": tenure_data},
        "suggestions": [
            "Who is likely to leave?",
            "Recommendations",
            "Overall stats",
        ],
    }


def _recommendations_response():
    """Actionable retention recommendations tied to active dataset drivers."""
    factors = ae.get_contributing_factors()
    if not factors:
        return {
            "response": (
                "💡 **Actionable Retention Recommendations**\n\n"
                "• Conduct proactive retention check-ins with high-risk employees.\n"
                "• Benchmark department compensation against market rates.\n"
                "• Monitor and cap sustained overtime hours."
            ),
            "suggestions": ["Who is likely to leave?", "Overall stats"],
        }

    rec_items = []
    for i, f in enumerate(factors[:4], 1):
        rec_items.append(
            f"{i}. **Address {f['factor']}** — {f['description']}.\n"
            f"   *Target Intervention:* Prioritize the {f['high_risk_group']} cohort for immediate management check-ins."
        )

    return {
        "response": (
            "💡 **Data-Driven Retention Recommendations**\n\n"
            "Derived directly from the primary risk drivers in this dataset:\n\n"
            + "\n\n".join(rec_items) + "\n\n"
            "📊 **Suggested Retention Rhythm:** Track the High-Risk Watchlist weekly, cap consecutive overtime, and establish 90-day onboarding mentorships."
        ),
        "suggestions": [
            "Who are the top high-risk active employees?",
            "Rank all departments by attrition rate",
            "Overall stats",
        ],
    }


def _overall_stats_response():
    """Dataset summary and KPI metrics."""
    if dl.df is None or len(dl.df) == 0:
        return {"response": "⚠️ No dataset loaded.", "suggestions": []}

    kpis = ae.get_kpis()
    dataset_name = dl.DATASET_NAME or "Active Dataset"

    return {
        "response": (
            f"📊 **Workforce Attrition Summary for `{dataset_name}`**\n\n"
            f"• **Total Headcount:** **{kpis['total_employees']:,}** employees\n"
            f"• **Historical Departures:** **{kpis['attrition_count']:,}** employees left\n"
            f"• **Current Active Headcount:** **{kpis['retention_count']:,}** employees retained\n"
            f"• **Overall Attrition Rate:** **{kpis['attrition_rate']}%**\n"
            f"• **Average Employee Age:** **{kpis['avg_age']}** years\n"
            f"• **Average Monthly Income:** **₹{kpis['avg_monthly_income']:,.0f}**\n"
            f"• **Average Tenure:** **{kpis['avg_years_at_company']}** years"
        ),
        "data": kpis,
        "suggestions": [
            "Why do employees leave?",
            "Rank all departments by attrition rate",
            "Who is likely to leave?",
        ],
    }


# ─────────────────────────────────────────────────────────────
#  Intent Detection & Router
# ─────────────────────────────────────────────────────────────

def _match_intent(message, session):
    """
    Match user message to an intent using keyword priority, regex, and session context.
    """
    msg = message.lower().strip()

    # 1. Employee lookup by ID
    emp_id = _extract_employee_id(message)
    if emp_id:
        return "employee_lookup", {"emp_id": emp_id}

    # 2. Conversational follow-ups using session context
    pronouns = ["they", "them", "he", "she", "him", "her", "this employee", "that employee", "his"]
    if any(re.search(r"\b" + re.escape(p) + r"\b", msg) for p in pronouns):
        if session.get("last_employee_id"):
            return "employee_followup", {"emp_id": session["last_employee_id"]}

    dept_pronouns = ["there", "this department", "that department", "that team", "how to fix it"]
    if any(p in msg for p in dept_pronouns) and session.get("last_department"):
        return "department_deep_dive", {"dept": session["last_department"]}

    # 3. Department comparison
    compare_triggers = ["compare", " vs ", " versus ", "difference between"]
    if any(t in msg for t in compare_triggers):
        depts = _extract_departments_to_compare(message)
        if len(depts) >= 2:
            return "department_comparison", {"dept1": depts[0], "dept2": depts[1]}

    # 4. Department analysis & breakdown
    all_dept_triggers = [
        "all department", "all departments", "list department", "list departments",
        "tell me all department", "tell me all departments", "what department",
        "what departments", "which department", "which departments",
        "show department", "show departments", "every department", "department list",
        "departments list", "tell me department", "tell me departments",
        "departments overview", "view departments"
    ]
    if any(t in msg for t in all_dept_triggers):
        specific_dept = _extract_department(message)
        if specific_dept and not any(k in msg for k in ["all", "list", "every", "each"]):
            return "department_deep_dive", {"dept": specific_dept}
        return "all_departments", {}

    dept_triggers = ["analyze", "how is", "deep dive", "tell me about", "department", "dept"]
    if any(t in msg for t in dept_triggers):
        dept = _extract_department(message)
        if dept:
            return "department_deep_dive", {"dept": dept}

    # If message directly mentions a department name
    dept = _extract_department(message)
    if dept and ("why" in msg or "rate" in msg or "attrition" in msg or "doing" in msg or "status" in msg):
        return "department_deep_dive", {"dept": dept}

    # 5. Rankings
    ranking_triggers = ["rank", "ranking", "rankings", "leaderboard", "highest to lowest", "worst department", "top department"]
    if any(t in msg for t in ranking_triggers):
        if "role" in msg or "job" in msg or "position" in msg:
            return "rankings_roles", {}
        return "rankings_departments", {}

    # 6. Historical Attrition vs Future Risk
    historical_triggers = ["who left", "who has left", "historical attrition", "past attrition", "past turnover", "how many departed", "departed employees", "former employees"]
    if any(t in msg for t in historical_triggers):
        return "historical_attrition", {}

    who_leave_triggers = [
        "who is likely", "who will leave", "who might leave", "likely to leave",
        "at risk", "flight risk", "high risk", "high-risk", "who is at risk",
        "risky", "going to leave", "watchlist", "active employees at risk"
    ]
    if any(t in msg for t in who_leave_triggers):
        return "who_likely_leave", {}

    # 7. Greetings & Help (strict word boundary matching)
    if re.search(r"\b(hi|hello|hey|good morning|good afternoon|howdy)\b", msg):
        return "greeting", {}
    if re.search(r"\b(help|commands|options|menu|what can you do)\b", msg):
        return "help", {}

    # 8. Other core analytical intents
    intents = [
        ("why_leave", ["why leave", "why do they leave", "reasons for leaving", "causes", "why employees leave", "contributing factors", "root cause", "why attrition", "why turnover"], 10),
        ("recommendations", ["recommend", "recommendation", "recommendations", "suggestion", "suggestions", "how to reduce", "reduce attrition", "how to improve", "retention strategy", "retention plan", "action plan", "what to do", "prevent attrition"], 10),
        ("overtime_impact", ["overtime", "over time", "working hours", "extra hours", "overwork", "workload", "burnout"], 8),
        ("salary_impact", ["salary", "salaries", "income", "pay", "compensation", "wage", "wages", "low pay"], 8),
        ("satisfaction_impact", ["satisfaction", "happy", "unhappy", "satisfied", "dissatisfied", "engagement", "work life balance", "morale"], 8),
        ("tenure_impact", ["tenure", "years at company", "new hire", "new hires", "experience", "seniority"], 7),
        ("overall_stats", ["overall", "summary", "total", "how many", "attrition rate", "overview", "statistics", "numbers", "data", "count", "kpi", "kpis"], 6),
    ]

    best_intent = None
    best_score = 0

    for intent_name, keywords, priority in intents:
        score = 0
        for keyword in keywords:
            if re.search(r"\b" + re.escape(keyword), msg):
                score += len(keyword) * priority
        if score > best_score:
            best_score = score
            best_intent = intent_name

    if best_intent:
        return best_intent, {}

    return "unknown", {}


# ─────────────────────────────────────────────────────────────
#  Response Formatter & Unified Contract
# ─────────────────────────────────────────────────────────────

def _build_response_payload(
    intent: str,
    response_text: str,
    source: str = "deterministic_analytics",
    data: Optional[Dict[str, Any]] = None,
    operations: Optional[List[Dict[str, Any]]] = None,
    evidence: Optional[Dict[str, Any]] = None,
    citations: Optional[List[Dict[str, Any]]] = None,
    suggestions: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Return unified, backward-compatible response object containing evidence and citations."""
    return {
        "intent": intent,
        "response": response_text,
        "answer": response_text,
        "reply": response_text,
        "source": source,
        "dataset_name": dl.DATASET_NAME or "Active Dataset",
        "dataset_version": dl.get_dataset_version(),
        "data": data or {},
        "operations": operations or [],
        "evidence": evidence or {},
        "citations": citations or [],
        "suggestions": (suggestions or generate_dataset_questions())[:4],
    }


# ─────────────────────────────────────────────────────────────
#  Main Process Message Entry Point (Hybrid RAG + Analytics)
# ─────────────────────────────────────────────────────────────

def process_message(user_message, session_id="default"):
    """
    Main entry point: process a user message and return a chatbot response.
    Features:
      - Full-dataset safe analytical query planner (filtering, aggregations, distributions, correlations).
      - Selective hybrid RAG for HR handbooks, policies, and playbooks.
      - Alphanumeric employee ID lookups with flight risk vs historical exit distinction.
      - Conversational context preservation and dataset-change reference invalidation.
      - 100% offline resilient fallback when Gemini is unavailable.
    """
    session = get_session(session_id)
    session["history"].append(user_message)
    msg_clean = user_message.strip()
    msg_lower = msg_clean.lower()

    # Guard: Missing dataset check
    if dl.df is None or len(dl.df) == 0:
        dl.ensure_dataset_loaded()
        if dl.df is None or len(dl.df) == 0:
            return _build_response_payload(
                intent="no_dataset",
                response_text=(
                    "⚠️ **No employee dataset is currently loaded.**\n\n"
                    "Please upload an employee CSV file on the dashboard using the upload zone or 'Upload CSV' button. "
                    "Once uploaded, I will dynamically profile the cohort and answer questions across flight risks, correlations, distributions, and policies!"
                ),
                source="rule_based_fallback",
                suggestions=[
                    "How does employee attrition analysis work?",
                    "What CSV columns should my dataset include?",
                    "How do I upload an employee dataset?",
                ],
            )

    # ── 1. Individual Employee Lookup / Follow-Up & Pronoun Resolution ──
    emp_id = _extract_employee_id(user_message)
    pronouns = ["they", "them", "he", "she", "him", "her", "their", "theirs", "this employee", "that employee", "his"]
    if not emp_id and any(re.search(r"\b" + re.escape(p) + r"\b", msg_lower) for p in pronouns):
        emp_id = session.get("last_employee_id")

    if emp_id:
        emp = ae.get_employee_by_id(emp_id)
        if not emp:
            samples = ae.get_sample_employee_ids(limit=4)
            sample_lines = [f"• **#{s['id']}** ({s['role']}, {s['department']})" for s in samples]
            sample_str = f"\n\n**Valid sample employee IDs in this dataset:**\n" + "\n".join(sample_lines) if sample_lines else ""
            return _build_response_payload(
                intent="employee_lookup",
                response_text=(
                    f"🔍 **Employee ID `#{emp_id}` not found** in the active dataset (`{dl.DATASET_NAME or 'uploaded cohort'}`).\n\n"
                    f"There are **{dl.TOTAL_EMPLOYEES:,}** total employees in this cohort.{sample_str}\n\n"
                    f"Please verify the employee ID or check the High-Risk Watchlist table on your dashboard."
                ),
                source="rule_based_fallback",
            )

        # Update session context
        session["last_employee_id"] = emp["employee_number"]
        session["last_employee"] = emp
        session["last_department"] = emp["department"]
        session["last_role"] = emp["job_role"]
        session["last_intent"] = "employee_lookup"

        fallback_card = _format_employee_card(emp)
        emp_context = (
            f"[SPECIFIC EMPLOYEE RECORD FROM VERIFIED DATASET]\n"
            f"Employee #{emp['employee_number']}:\n"
            f"- Role: {emp['job_role']}, Department: {emp['department']}\n"
            f"- Demographics: Age {emp['age']}, Gender {emp['gender']}, Marital Status {emp['marital_status']}\n"
            f"- Compensation: ₹{emp['monthly_income']:,.0f}/mo, Stock Option Level: {emp['stock_option_level']}\n"
            f"- Tenure: {emp['years_at_company']} years at company\n"
            f"- Overtime: {emp['overtime']}\n"
            f"- Satisfaction: Job={emp['job_satisfaction']}/4, Environment={emp['env_satisfaction']}/4, Work-Life Balance={emp['work_life_balance']}/4\n"
            f"- Flight Risk Score: {emp['risk_score']}/8 ({emp['risk_level']} Flight Risk)\n"
            f"- Status: {'Left/Departed (Historical Attrition)' if emp['attrition'] == 'Yes' else 'Active Employee (Retained)'}\n"
            f"- Specific Triggers: {', '.join(emp.get('risk_reasons', [])) if emp.get('risk_reasons') else 'None'}\n\n"
            f"INSTRUCTION: Clearly state whether this employee is HISTORICALLY DEPARTED or CURRENTLY ACTIVE. "
            f"Break down their compensation, working conditions, flight risk score, and concrete retention recommendations."
        )

        gemini_reply = _call_gemini_api(user_message, custom_context=emp_context)
        return _build_response_payload(
            intent="employee_lookup",
            response_text=gemini_reply or fallback_card,
            source="gemini_ai" if gemini_reply else "rule_based_fallback",
            data={"employee": emp},
        )

    # ── 2. Check Document Knowledge & Selective Hybrid RAG ─────
    rag_keywords = [
        "policy", "policies", "handbook", "guideline", "guidelines", "procedure", "procedures",
        "playbook", "comp-time", "compensatory", "comp time", "overtime limit", "overtime pay",
        "stay interview", "5-day", "equity tier", "stock option tier", "vesting", "severance",
        "leave", "remote work", "work from home", "burnout intervention", "etl pipeline", "handbooks"
    ]
    is_policy_query = any(k in msg_lower for k in rag_keywords)
    rag_hits = rag.search_documents(user_message, top_k=3, min_score=0.10 if is_policy_query else 0.25)

    if rag_hits:
        # Check if question also requests active dataset metrics (Combined Multi-Step Flow)
        data_keywords = [
            "how many", "count", "active", "sales", "engineering", "customer support", "r&d",
            "research", "department", "rate", "turnover", "attrition", "cohort", "in this dataset",
            "current", "employees", "staff", "who are"
        ]
        is_combined = any(k in msg_lower for k in data_keywords)

        if is_combined:
            # Execute analytical lookup for department or cohort
            dept = _extract_department(user_message)
            analytical_evidence = {}
            if dept:
                dept_res = _department_deep_dive_response(dept)
                dept_stat_str = f"[CURRENT DATASET ANALYTICS FOR {dept.upper()}]\n" + dept_res.get("response", "")
                analytical_evidence = dept_res.get("data", {})
            else:
                kpis = ae.get_kpis()
                dept_stat_str = (
                    f"[DATASET COHORT METRICS]\n"
                    f"Total Workforce: {kpis.get('total_employees', 0):,}\n"
                    f"Overall Attrition Rate: {kpis.get('attrition_rate', 0)}%\n"
                    f"Overtime Attrition Rate: {kpis.get('overtime_attrition_rate', 0)}% vs Non-Overtime: {kpis.get('no_overtime_attrition_rate', 0)}%"
                )
                analytical_evidence = kpis

            rag_context = "\n\n".join([f"SOURCE CITATION: {h['citation']}\n{h['content']}" for h in rag_hits])
            combined_grounding = (
                f"{dept_stat_str}\n\n"
                f"[OFFICIAL HR POLICIES & PLAYBOOKS]\n{rag_context}\n\n"
                f"INSTRUCTION: Synthesize the verified dataset analytics with company policy rules. "
                f"1. State the exact computed dataset numbers.\n"
                f"2. Explain the governing policy or retention playbook guidance.\n"
                f"3. Cite the documents accurately using their [Title, Section] citation.\n"
                f"4. Clearly distinguish computed facts from retention recommendations."
            )

            gemini_reply = _call_gemini_api(user_message, custom_context=combined_grounding)
            if not gemini_reply:
                citations_md = "\n\n".join([
                    f"📄 **{h['title']}** — *{h.get('section', 'General')}*\n"
                    f"> {h['content']}\n"
                    f"*Source: {h['citation']}*"
                    for h in rag_hits
                ])
                combined_fallback = f"{dept_stat_str}\n\n📚 **Applicable Policy Guidance & Citations:**\n\n{citations_md}"
                return _build_response_payload(
                    intent="hybrid_analytics_and_rag",
                    response_text=combined_fallback,
                    source="deterministic_engine",
                    evidence=analytical_evidence,
                    citations=rag_hits,
                )

            return _build_response_payload(
                intent="hybrid_analytics_and_rag",
                response_text=gemini_reply,
                source="hybrid_rag",
                evidence=analytical_evidence,
                citations=rag_hits,
            )

        elif is_policy_query or (rag_hits and rag_hits[0]["score"] >= 0.28):
            # Pure RAG Knowledge Flow
            rag_context = "\n\n".join([f"SOURCE CITATION: {h['citation']}\n{h['content']}" for h in rag_hits])
            rag_prompt = (
                f"[OFFICIAL HR DOCUMENT PASSAGES]\n{rag_context}\n\n"
                f"INSTRUCTION: Answer the question accurately based on the retrieved document passages. "
                f"Always cite the document title and section using the provided citation format. "
                f"If the documents do not cover an aspect, honestly state that limitation."
            )
            gemini_reply = _call_gemini_api(user_message, custom_context=rag_prompt)
            if not gemini_reply:
                citations_md = "\n\n".join([
                    f"📄 **{h['title']}** — *{h.get('section', 'General')}*\n"
                    f"> {h['content']}\n"
                    f"*Source: {h['citation']}*"
                    for h in rag_hits
                ])
                fallback_rag = f"📖 **Company HR Policy Documentation:**\n\n{citations_md}"
                return _build_response_payload(
                    intent="document_rag",
                    response_text=fallback_rag,
                    source="deterministic_rag",
                    citations=rag_hits,
                )

            return _build_response_payload(
                intent="document_rag",
                response_text=gemini_reply,
                source="hybrid_rag",
                citations=rag_hits,
            )

    # ── 3. Full-Dataset Analytical Query Planner ─────────────
    plan = qp.compile_rule_based_plan(user_message)
    if not plan and any(k in msg_lower for k in [
        "missing", "null", "correlation", "correlate", "average", "mean", "median", "quantile", "percentile",
        "distribution", "spread", "crosstab", "cross tab", "filter", "how many employees", "data quality", "describe dataset"
    ]):
        plan = qp.compile_llm_plan(user_message, lambda p: _call_gemini_api(p))

    if plan:
        is_valid, err_msg, sanitized_plan = qp.validate_plan(plan)
        if is_valid:
            plan_res = qp.execute_plan(sanitized_plan)
            evidence_md = qp.format_plan_results_as_markdown(plan_res, sanitized_plan)

            # Gemini enhancement
            gemini_context = (
                f"[FULL DATASET DETERMINISTIC CALCULATION]\n{evidence_md}\n\n"
                f"INSTRUCTION: Synthesize these exact calculations for the user. "
                f"Retain the tables and numbers precisely without altering counts or percentages. "
                f"Highlight actionable workforce insights and business implications."
            )
            gemini_reply = _call_gemini_api(user_message, custom_context=gemini_context)
            final_text = gemini_reply if gemini_reply else evidence_md
            source = "gemini_ai" if gemini_reply else "deterministic_analytics"

            session["last_intent"] = f"analytics_{sanitized_plan.get('operation')}"
            return _build_response_payload(
                intent=f"analytics_{sanitized_plan.get('operation')}",
                response_text=final_text,
                source=source,
                operations=[sanitized_plan],
                evidence=plan_res,
            )

    # ── 4. Standard Keyword / Intent Matching ──────────────────
    intent, intent_params = _match_intent(user_message, session)

    if intent == "all_departments":
        session["last_intent"] = "all_departments"
        dept_res = _all_departments_response()
        gemini_reply = _call_gemini_api(user_message, custom_context=dept_res["response"])
        return _build_response_payload(
            intent="all_departments",
            response_text=gemini_reply or dept_res["response"],
            source="gemini_ai" if gemini_reply else "rule_based_fallback",
            data=dept_res.get("data"),
            suggestions=dept_res.get("suggestions"),
        )

    if intent == "department_deep_dive":
        dept_name = intent_params.get("dept") or _extract_department(user_message)
        if dept_name:
            session["last_department"] = dept_name
            session["last_intent"] = "department_deep_dive"
            dept_res = _department_deep_dive_response(dept_name)
            gemini_reply = _call_gemini_api(user_message, custom_context=dept_res["response"])
            return _build_response_payload(
                intent="department_deep_dive",
                response_text=gemini_reply or dept_res["response"],
                source="gemini_ai" if gemini_reply else "rule_based_fallback",
                data=dept_res.get("data"),
                suggestions=dept_res.get("suggestions"),
            )

    if intent == "department_comparison":
        dept1 = intent_params.get("dept1")
        dept2 = intent_params.get("dept2")
        if dept1 and dept2:
            session["last_department"] = dept1
            session["last_intent"] = "department_comparison"
            comp_res = _department_comparison_response(dept1, dept2)
            gemini_reply = _call_gemini_api(user_message, custom_context=comp_res["response"])
            return _build_response_payload(
                intent="department_comparison",
                response_text=gemini_reply or comp_res["response"],
                source="gemini_ai" if gemini_reply else "rule_based_fallback",
                data=comp_res.get("data"),
                suggestions=comp_res.get("suggestions"),
            )

    if intent in ("rankings_departments", "rankings_roles"):
        entity = "role" if intent == "rankings_roles" else "department"
        session["last_intent"] = intent
        rank_res = _rankings_response(entity_type=entity)
        return _build_response_payload(
            intent=intent,
            response_text=rank_res["response"],
            source="rule_based_fallback",
            data=rank_res.get("data"),
            suggestions=rank_res.get("suggestions"),
        )

    if intent == "historical_attrition":
        session["last_intent"] = intent
        hist_res = _historical_attrition_response()
        return _build_response_payload(
            intent=intent,
            response_text=hist_res["response"],
            source="rule_based_fallback",
            data=hist_res.get("data"),
            suggestions=hist_res.get("suggestions"),
        )

    if intent == "who_likely_leave":
        session["last_intent"] = intent
        who_res = _who_likely_leave_response()
        return _build_response_payload(
            intent=intent,
            response_text=who_res["response"],
            source="rule_based_fallback",
            data=who_res.get("data"),
            suggestions=who_res.get("suggestions"),
        )

    generators = {
        "why_leave": _why_leave_response,
        "overtime_impact": _overtime_response,
        "salary_impact": _salary_response,
        "satisfaction_impact": _satisfaction_response,
        "tenure_impact": _tenure_response,
        "recommendations": _recommendations_response,
        "overall_stats": _overall_stats_response,
    }

    if intent in generators:
        session["last_intent"] = intent
        res = generators[intent]()
        return _build_response_payload(
            intent=intent,
            response_text=res["response"],
            source="rule_based_fallback",
            data=res.get("data"),
            suggestions=res.get("suggestions"),
        )

    if intent == "greeting":
        kpis = ae.get_kpis()
        dynamic_q = generate_dataset_questions()
        return _build_response_payload(
            intent="greeting",
            response_text=(
                f"👋 Hello! I'm **AttritionAI**, your full-dataset workforce analytics & HR knowledge partner.\n\n"
                f"I am actively analyzing `{dl.DATASET_NAME or 'Active Dataset'}` "
                f"({kpis.get('total_employees', 0):,} employees, {kpis.get('attrition_rate', 0)}% attrition).\n\n"
                f"You can ask about:\n"
                f"• **Dataset Analytics:** Missing values, distributions, correlations, or multi-filter queries.\n"
                f"• **Employee Profiles:** In-depth flight risk reviews by employee ID.\n"
                f"• **HR Policies & Playbooks:** Company guidelines on overtime, retention, equity, and remote work."
            ),
            source="rule_based_fallback",
            suggestions=dynamic_q[:4],
        )

    if intent == "help":
        dynamic_q = generate_dataset_questions()
        return _build_response_payload(
            intent="help",
            response_text=(
                "📋 **Capabilities of AttritionAI:**\n\n"
                "• **Full-Dataset Analytics:** *\"Which columns have missing values?\"*, *\"Correlation between salary and tenure\"*, *\"Salary distribution\"*\n"
                "• **Custom Cohort Comparisons:** *\"Compare employees with overtime vs without overtime\"*, *\"Compare Sales vs Engineering\"*\n"
                "• **Employee Record Deep Dive:** *\"Tell me about employee #E02744\"*\n"
                "• **HR Policy Knowledge (RAG):** *\"What is our policy on overtime pay and workload limits?\"*, *\"What is our 5-day retention intervention playbook?\"*\n"
                "• **Combined Intelligence:** *\"What is our overtime policy and how many active employees in Sales are working overtime?\"*"
            ),
            source="rule_based_fallback",
            suggestions=dynamic_q[:4],
        )

    # ── 5. Freeform / Fallback with Grounded Gemini ───────────
    gemini_reply = _call_gemini_api(user_message)
    dynamic_q = generate_dataset_questions()

    if gemini_reply:
        return _build_response_payload(
            intent="freeform",
            response_text=gemini_reply,
            source="gemini_ai",
            suggestions=dynamic_q[:4],
        )

    return _build_response_payload(
        intent="unknown",
        response_text=(
            "🤔 I specialize in employee attrition analytics, full-dataset calculations, flight-risk modeling, and company HR policies.\n\n"
            "Try asking one of the suggested questions below based on your active dataset and documentation!"
        ),
        source="rule_based_fallback",
        suggestions=dynamic_q[:4],
    )
