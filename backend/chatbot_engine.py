import os
import json
import urllib.request
import logging
import re

from . import data_loader as dl
from . import analytics_engine as ae

logger = logging.getLogger(__name__)


def _load_gemini_api_key():
    """Load Gemini API Key from environment or .env file."""
    # 1. Environment variables
    for var in ["GEMINI_API_KEY", "API_KEY", "API Key"]:
        val = os.environ.get(var)
        if val:
            return val.strip()

    # 2. Check .env file in backend/
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


# Load API key immediately on startup
_GEMINI_API_KEY = _load_gemini_api_key()


def _get_gemini_api_key():
    global _GEMINI_API_KEY
    if not _GEMINI_API_KEY:
        _GEMINI_API_KEY = _load_gemini_api_key()
    return _GEMINI_API_KEY



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
        f"Instructions:\n"
        f"1. When answering workforce or employee attrition questions, ALWAYS ground your answers in the numbers of this active dataset ('{dataset_name}'). Quote specific figures and percentages!\n"
        f"2. For casual greetings, random questions, chit-chat, jokes, or hypothetical scenarios, reply warmly, engagingly, and concisely.\n"
        f"3. Format your responses in clean GitHub Markdown with clear bullet points and emojis."
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

    # Dynamic system instruction giving context of the currently active dataset
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
                # API rate limit reached, break early to provide instant rule-based fallback
                break
            continue
        except Exception as e:
            logger.warning(f"Gemini call to {model} failed: {e}")
            continue

    return None


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
      - 'tell me about #E02744'
      - '#E02744' or 'E02744'
      - 'tell me about employee 101'
      - 'give details on employee ID 105'
      - 'who is employee E00005'
      - 'is emp #12 leaving?'
      - 'tell me about 104'
    """
    if not text:
        return None

    cleaned_text = text.strip()

    # 1. Direct hashtag match: #E02744, #104, #EMP-01
    m = re.search(r"#([a-zA-Z0-9_\-]+)", cleaned_text)
    if m:
        val = m.group(1).strip()
        if val.lower() not in _EMP_ID_FALSE_POSITIVES:
            return val

    # 2. Keywords followed by ID: employee [id] [:] #?E02744 / 104
    m = re.search(
        r"(?:employee|emp|worker|staff|user|id|record)\s*(?:id|number|no|#|\:)?\s*#?([a-zA-Z0-9_\-]+)",
        cleaned_text,
        re.IGNORECASE,
    )
    if m:
        val = m.group(1).strip()
        if val.lower() not in _EMP_ID_FALSE_POSITIVES:
            return val

    # 3. Alphanumeric employee ID code pattern: E02744, EMP102, EMP-01
    m = re.search(r"\b([A-Za-z]{1,4}[-_]?[0-9]{2,8})\b", cleaned_text)
    if m:
        val = m.group(1).strip()
        if val.lower() not in _EMP_ID_FALSE_POSITIVES:
            return val

    # 4. Contextual lookup verbs: 'tell me about 104', 'details for E001', 'who is 42'
    m = re.search(
        r"(?:about|for|on|who\s+is|look\s*up|check|find|status\s+of)\s+#?([a-zA-Z0-9_\-]+)",
        cleaned_text,
        re.IGNORECASE,
    )
    if m:
        val = m.group(1).strip()
        if val.lower() not in _EMP_ID_FALSE_POSITIVES:
            return val

    # 5. Direct token verification against active dataset ID columns
    if dl.df is not None and len(dl.df) > 0:
        id_candidates = ["EmployeeNumber", "EmployeeID", "id", "emp_id", "emp_number"]
        cols = [c for c in id_candidates if c in dl.df.columns]
        if cols:
            tokens = re.findall(r"#?([a-zA-Z0-9_\-]+)", cleaned_text)
            for token in tokens:
                clean_tok = token.lstrip("#").strip().lower()
                if len(clean_tok) < 2 or clean_tok in _EMP_ID_FALSE_POSITIVES:
                    continue
                for c in cols:
                    if (dl.df[c].astype(str).str.strip().str.lower() == clean_tok).any():
                        return token.lstrip("#").strip()

    return None


def _format_employee_card(emp):
    """Format a detailed, visually clear markdown profile card for an individual employee."""
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

    status_badge = "🔴 **Left Company (Attrition)**" if attrition == "Yes" else "🟢 **Active Employee (Retained)**"
    risk_badge = f"🔥 **{risk_lvl} Risk ({risk_score}/8)**" if risk_lvl == "High" else f"⚡ **{risk_lvl} Risk ({risk_score}/8)**"

    salary_str = f"₹{salary:,.0f}/month" if salary else "Not specified"

    if reasons:
        reasons_str = "\n".join([f"  • ⚠️ {r}" for r in reasons])
    else:
        reasons_str = "  • ✅ No major flight risk triggers detected (Stable profile)"

    if attrition == "Yes":
        rec_str = "📋 **Exit Review Summary**: Employee has departed. Historical drivers reflect flight risk patterns common in this role and tenure band."
    elif risk_lvl == "High":
        rec_str = f"💡 **Recommended Retention Intervention**: High flight risk! Recommend immediate 1-on-1 check-in. Focus on {reasons[0].lower() if reasons else 'workload balance'} and compensation/equity review."
    elif risk_lvl == "Medium":
        rec_str = "💡 **Recommended Retention Intervention**: Moderate risk. Monitor workload balance and conduct regular engagement check-ins."
    else:
        rec_str = "💡 **Recommended Retention Intervention**: Healthy retention signals. Continue standard career milestones and recognition."

    return (
        f"👤 **Employee Profile: #{emp_no}**\n\n"
        f"**Status:** {status_badge} &nbsp;|&nbsp; **Flight Risk:** {risk_badge}\n\n"
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
        f"🔍 **Flight Risk Diagnostics:**\n"
        f"{reasons_str}\n\n"
        f"{rec_str}"
    )


def _match_intent(message):
    """Match user message to an intent using keyword priority scoring."""
    emp_id = _extract_employee_id(message)
    if emp_id:
        return "employee_lookup"

    msg = message.lower().strip()

    # Intent definitions: (intent_name, keywords, priority)
    intents = [
        ("greeting", ["hi", "hello", "hey", "good morning", "good afternoon"], 1),
        ("help", ["help", "what can you", "what do you", "commands", "options", "menu"], 2),
        ("who_likely_leave", ["who will leave", "who is likely", "who might leave",
                              "likely to leave", "at risk", "high risk employee",
                              "who is at risk", "risky", "going to leave"], 10),
        ("why_leave", ["why leave", "why do they leave", "reasons for leaving",
                       "causes", "why employees leave", "contributing factors",
                       "root cause", "why attrition"], 9),
        ("recommendations", ["recommend", "suggestion", "what should", "how to reduce",
                              "how to improve", "how can we", "action", "strategy",
                              "prevent", "retain", "what to do"], 9),
        ("department_attrition", ["department", "which department", "dept",
                                   "sales department", "r&d", "human resources dept",
                                   "highest attrition department"], 7),
        ("role_attrition", ["role", "job role", "position", "sales rep",
                            "which role", "job position", "designation"], 7),
        ("overtime_impact", ["overtime", "over time", "working hours",
                              "extra hours", "overwork"], 7),
        ("salary_impact", ["salary", "income", "pay", "compensation",
                           "money", "earning", "wage"], 7),
        ("age_impact", ["age", "young", "old", "generation", "millennial",
                        "age group", "how old"], 6),
        ("tenure_impact", ["tenure", "how long", "years at company",
                           "new hire", "experience", "seniority", "service"], 6),
        ("satisfaction_impact", ["satisfaction", "happy", "unhappy",
                                  "satisfied", "dissatisfied", "engagement"], 7),
        ("gender_analysis", ["gender", "male", "female", "men", "women",
                              "sex", "diversity"], 6),
        ("travel_impact", ["travel", "business travel", "commute", "trip"], 6),
        ("overall_stats", ["overall", "summary", "total", "how many",
                           "attrition rate", "overview", "statistics",
                           "numbers", "data", "count"], 5),
    ]

    best_intent = None
    best_score = 0

    for intent_name, keywords, priority in intents:
        score = 0
        for keyword in keywords:
            if keyword in msg:
                # Longer keyword matches get higher scores
                score += len(keyword) * priority
        if score > best_score:
            best_score = score
            best_intent = intent_name

    return best_intent or "unknown"


def _format_response(intent):
    """Generate a formatted response for the matched intent."""
    kpis = ae.get_kpis()

    if dl.df is None or dl.TOTAL_EMPLOYEES == 0 or kpis is None:
        if intent == "greeting":
            return {
                "response": (
                    "👋 Hello! I'm **AttritionAI**, your workforce analytics assistant powered by Gemini.\n\n"
                    "Currently, **no employee CSV file is loaded**.\n\n"
                    "To get started, please upload an employee CSV file on the dashboard to calculate attrition metrics, generate 11 visual charts, and explore high-risk segments!"
                ),
                "suggestions": [
                    "How does attrition analysis work?",
                    "What are top causes of turnover?",
                    "How should I format my CSV?",
                ],
            }
        return {
            "response": (
                "⚠️ **No employee dataset is currently loaded.**\n\n"
                "Please add/upload an employee CSV file using the upload area on your dashboard. Once uploaded, I will analyze the cohort and answer questions about flight risks, department rates, and retention strategies!"
            ),
            "suggestions": [
                "How does attrition analysis work?",
                "What columns should my CSV include?",
            ],
        }

    dataset_name = dl.DATASET_NAME or "Active Dataset"

    if intent == "greeting":
        return {
            "response": (
                "👋 Hello! I'm **AttritionAI**, your HR analytics assistant.\n\n"
                f"I can help you analyze employee attrition patterns from our active dataset "
                f"**{dataset_name}** ({kpis['total_employees']:,} employees, {kpis['attrition_rate']}% attrition).\n\n"
                "Try asking me questions like the ones below!"
            ),
            "suggestions": [
                "Who is likely to leave?",
                "Why do employees leave?",
                "Which department has highest attrition?",
                "What recommendations do you have?",
            ],
        }

    if intent == "help":
        return {
            "response": (
                "📋 Here's what I can help you with:\n\n"
                "• **\"Who is likely to leave?\"** — View high-risk employees\n"
                "• **\"Why do employees leave?\"** — Top contributing factors\n"
                "• **\"Which department?\"** — Department-wise attrition\n"
                "• **\"Which role?\"** — Job role analysis\n"
                "• **\"Overtime impact\"** — OverTime vs attrition\n"
                "• **\"Salary impact\"** — Income band analysis\n"
                "• **\"Age groups\"** — Age-wise breakdown\n"
                "• **\"Tenure effect\"** — Years at company analysis\n"
                "• **\"Satisfaction\"** — Job & environment satisfaction\n"
                "• **\"Recommendations\"** — Actionable strategies"
            ),
            "suggestions": [
                "Who is likely to leave?",
                "Overall stats",
                "Recommendations",
            ],
        }

    if intent == "overall_stats":
        return {
            "response": (
                f"📊 **Overall Attrition Summary for `{dataset_name}`**\n\n"
                f"• Total Employees: **{kpis['total_employees']:,}**\n"
                f"• Attrition Count: **{kpis['attrition_count']}** employees left\n"
                f"• Retention Count: **{kpis['retention_count']:,}** stayed\n"
                f"• Overall Attrition Rate: **{kpis['attrition_rate']}%**\n"
                f"• Average Age: **{kpis['avg_age']}** years\n"
                f"• Average Monthly Income: **₹{kpis['avg_monthly_income']:,.0f}**\n"
                f"• Average Tenure: **{kpis['avg_years_at_company']}** years"
            ),
            "data": kpis,
            "suggestions": [
                "Why do employees leave?",
                "Which department is worst?",
                "Recommendations",
            ],
        }

    generators = {
        "who_likely_leave": _who_likely_leave_response,
        "why_leave": _why_leave_response,
        "department_attrition": _department_response,
        "role_attrition": _role_response,
        "overtime_impact": _overtime_response,
        "salary_impact": _salary_response,
        "age_impact": _age_response,
        "tenure_impact": _tenure_response,
        "satisfaction_impact": _satisfaction_response,
        "gender_analysis": _gender_response,
        "travel_impact": _travel_response,
        "recommendations": _recommendations_response,
    }

    if intent in generators:
        return generators[intent]()

    return {
        "response": (
            "🤔 I'm not sure I understood that. I specialize in employee attrition analysis.\n\n"
            "Try asking me about:\n"
            "• Who is likely to leave\n"
            "• Why employees leave\n"
            "• Department or role-wise attrition\n"
            "• OverTime, salary, or satisfaction impact"
        ),
        "suggestions": [
            "Help",
            "Who is likely to leave?",
            "Overall stats",
        ],
    }


def _who_likely_leave_response():
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
            f"🚨 **High-Risk Employees (Risk Score ≥ 4/8)**\n\n"
            f"There are **{total_high}** employees matching 4+ high-risk criteria.\n\n"
            f"**Top 5 highest-risk employees:**\n"
            + "\n".join(emp_lines) + "\n\n"
            f"Risk criteria include: OverTime, low income (<₹5k), short tenure (≤2 yrs), "
            f"low satisfaction, no stock options, young age (≤25), and poor work-life balance."
        ),
        "data": {"total_high_risk": total_high, "top_employees": employees[:5]},
        "suggestions": [
            "Why do they leave?",
            "Recommendations",
            "Which department is worst?",
        ],
    }


def _why_leave_response():
    factors = ae.get_contributing_factors()
    factor_lines = []
    for i, f in enumerate(factors[:5], 1):
        factor_lines.append(
            f"  {i}. **{f['factor']}** — +{f['impact']}pp impact "
            f"({f['high_risk_group']}: {f['high_risk_rate']}% vs "
            f"{f['low_risk_group']}: {f['low_risk_rate']}%)"
        )

    return {
        "response": (
            "📈 **Top Contributing Factors to Attrition**\n\n"
            "These factors have the highest differential impact on attrition rates:\n\n"
            + "\n".join(factor_lines) + "\n\n"
            "The **#1 driver is OverTime** — employees working overtime leave at "
            "nearly 3x the rate of those who don't."
        ),
        "data": {"factors": factors[:5]},
        "suggestions": [
            "How does overtime affect attrition?",
            "Recommendations",
            "Who is at risk?",
        ],
    }


def _department_response():
    dept_data = ae.get_department_data()
    dept_lines = []
    for d in dept_data:
        dept_lines.append(
            f"  • **{d['label']}**: {d['attrition']}/{d['total']} employees — **{d['rate']}%** attrition"
        )

    highest = dept_data[0]
    return {
        "response": (
            "🏢 **Department-wise Attrition Analysis**\n\n"
            + "\n".join(dept_lines) + "\n\n"
            f"**{highest['label']}** has the highest attrition rate at **{highest['rate']}%**."
        ),
        "data": {"departments": dept_data},
        "suggestions": [
            "Which role has the highest attrition?",
            "Why do employees leave?",
            "Overall stats",
        ],
    }


def _role_response():
    role_data = ae.get_job_role_data()
    role_lines = []
    for r in role_data[:5]:
        role_lines.append(
            f"  • **{r['label']}**: {r['attrition']}/{r['total']} — **{r['rate']}%**"
        )

    return {
        "response": (
            "👔 **Job Role Attrition Analysis** (Top 5 highest)\n\n"
            + "\n".join(role_lines) + "\n\n"
            f"**{role_data[0]['label']}** has the highest attrition at "
            f"**{role_data[0]['rate']}%** — nearly 1 in {100 // int(role_data[0]['rate'])} employees in this role leave."
        ),
        "data": {"roles": role_data},
        "suggestions": [
            "Which department is worst?",
            "What about salary impact?",
            "Recommendations",
        ],
    }


def _overtime_response():
    ot_data = ae.get_overtime_data()
    ot_yes = next((d for d in ot_data if d["label"] == "Yes"), {})
    ot_no = next((d for d in ot_data if d["label"] == "No"), {})

    return {
        "response": (
            "⏰ **OverTime Impact on Attrition**\n\n"
            f"• OverTime = **Yes**: {ot_yes.get('attrition', 0)}/{ot_yes.get('total', 0)} employees — "
            f"**{ot_yes.get('rate', 0)}%** attrition\n"
            f"• OverTime = **No**: {ot_no.get('attrition', 0)}/{ot_no.get('total', 0)} employees — "
            f"**{ot_no.get('rate', 0)}%** attrition\n\n"
            f"📌 Employees working overtime are **{round(ot_yes.get('rate', 0) / max(ot_no.get('rate', 1), 0.1), 1)}x "
            f"more likely to leave**. This is the single strongest predictor of attrition."
        ),
        "data": {"overtime": ot_data},
        "suggestions": [
            "What about salary impact?",
            "Who is at risk?",
            "Recommendations",
        ],
    }


def _salary_response():
    income_data = ae.get_income_data()
    lines = []
    for band in income_data:
        lines.append(
            f"  • **{band['label']}**: {band['attrition']}/{band['total']} — **{band['rate']}%**"
        )

    return {
        "response": (
            "💰 **Monthly Income vs Attrition**\n\n"
            + "\n".join(lines) + "\n\n"
            f"Lower income bands show significantly higher attrition. "
            f"The **₹1k-5k** band has the highest rate, confirming that "
            f"compensation is a critical retention factor."
        ),
        "data": {"income_bands": income_data},
        "suggestions": [
            "Stock options impact?",
            "Tenure effect?",
            "Recommendations",
        ],
    }


def _age_response():
    age_data = ae.get_age_data()
    lines = []
    for band in age_data:
        lines.append(
            f"  • **{band['label']}**: {band['attrition']}/{band['total']} — **{band['rate']}%**"
        )

    return {
        "response": (
            "🎂 **Age Group Attrition Analysis**\n\n"
            + "\n".join(lines) + "\n\n"
            "Younger employees (18-25) have the highest attrition rate, "
            "likely due to career exploration and lower organizational commitment. "
            "Mid-career employees (36-45) are the most stable."
        ),
        "data": {"age_bands": age_data},
        "suggestions": [
            "What about tenure?",
            "Gender breakdown?",
            "Recommendations",
        ],
    }


def _tenure_response():
    tenure_data = ae.get_tenure_data()
    lines = []
    for band in tenure_data:
        lines.append(
            f"  • **{band['label']}**: {band['attrition']}/{band['total']} — **{band['rate']}%**"
        )

    return {
        "response": (
            "📅 **Company Tenure vs Attrition**\n\n"
            + "\n".join(lines) + "\n\n"
            "New hires (0-2 years) have the highest attrition, suggesting the need for "
            "stronger onboarding programs and early-career engagement initiatives."
        ),
        "data": {"tenure_bands": tenure_data},
        "suggestions": [
            "Who is likely to leave?",
            "Age group analysis?",
            "Recommendations",
        ],
    }


def _satisfaction_response():
    sat_data = ae.get_satisfaction_data()
    job_lines = []
    for s in sat_data["job_satisfaction"]:
        job_lines.append(f"  • **{s['label']}**: {s['attrition']}/{s['total']} — **{s['rate']}%**")
    env_lines = []
    for s in sat_data["env_satisfaction"]:
        env_lines.append(f"  • **{s['label']}**: {s['attrition']}/{s['total']} — **{s['rate']}%**")

    return {
        "response": (
            "😊 **Satisfaction vs Attrition**\n\n"
            "**Job Satisfaction:**\n" + "\n".join(job_lines) + "\n\n"
            "**Environment Satisfaction:**\n" + "\n".join(env_lines) + "\n\n"
            "Both dimensions show a clear inverse relationship — lower satisfaction "
            "correlates with significantly higher attrition."
        ),
        "data": sat_data,
        "suggestions": [
            "Work-life balance impact?",
            "Why do employees leave?",
            "Recommendations",
        ],
    }


def _gender_response():
    gender_data = ae.get_gender_data()
    lines = []
    for g in gender_data:
        lines.append(
            f"  • **{g['label']}**: {g['attrition']}/{g['total']} — **{g['rate']}%**"
        )

    return {
        "response": (
            "👥 **Gender Attrition Analysis**\n\n"
            + "\n".join(lines) + "\n\n"
            "The difference in attrition rates between genders is relatively small, "
            "suggesting gender is not a primary driver of attrition."
        ),
        "data": {"gender": gender_data},
        "suggestions": [
            "What factors matter most?",
            "Department analysis?",
            "Overall stats",
        ],
    }


def _travel_response():
    travel_data = ae.get_travel_data()
    lines = []
    for t in travel_data:
        lines.append(
            f"  • **{t['label']}**: {t['attrition']}/{t['total']} — **{t['rate']}%**"
        )

    return {
        "response": (
            "✈️ **Business Travel Impact on Attrition**\n\n"
            + "\n".join(lines) + "\n\n"
            "Frequent travelers show notably higher attrition rates, "
            "indicating that excessive travel demands contribute to employee turnover."
        ),
        "data": {"travel": travel_data},
        "suggestions": [
            "Distance from home impact?",
            "Work-life balance?",
            "Recommendations",
        ],
    }


def _recommendations_response():
    factors = ae.get_contributing_factors()
    if not factors:
        return {
            "response": (
                "💡 **Actionable Recommendations**\n\n"
                "• Conduct 1-on-1 retention interviews with high-risk employees.\n"
                "• Benchmark team compensation against market rates.\n"
                "• Monitor and cap excessive overtime hours."
            ),
            "suggestions": ["Who is likely to leave?", "Overall stats"],
        }

    rec_items = []
    for i, f in enumerate(factors[:4], 1):
        rec_items.append(
            f"{i}. **Address {f['factor']}** — {f['description']}. "
            f"Focus targeted retention interventions on the {f['high_risk_group']} segment."
        )

    return {
        "response": (
            "💡 **Actionable Recommendations to Reduce Attrition**\n\n"
            "Based on the analyzed drivers for this dataset:\n\n"
            + "\n\n".join(rec_items) + "\n\n"
            "📊 **Suggested Strategy:** Monitor flight risks weekly, cap sustained overtime, and conduct quarterly compensation reviews."
        ),
        "suggestions": [
            "Who is likely to leave?",
            "Overall stats",
            "Which department needs attention?",
        ],
    }


def process_message(user_message):
    """
    Main entry point: process a user message and return a chatbot response.
    Powered by Google Gemini Generative AI with verified dataset grounding.
    Supports individual employee lookups by Employee ID/number.
    Falls back gracefully to pre-computed rules if Gemini API is unreachable.
    """
    # ── Check for Individual Employee Inquiry ─────────────
    emp_id = _extract_employee_id(user_message)
    if emp_id:
        emp = ae.get_employee_by_id(emp_id)
        if not emp:
            if dl.df is None or len(dl.df) == 0:
                return {
                    "intent": "employee_lookup",
                    "response": (
                        "⚠️ **No employee dataset is currently loaded.**\n\n"
                        "Please upload an employee CSV file on the dashboard first so I can save the records to Supabase and retrieve profiles."
                    ),
                    "suggestions": [
                        "How does attrition analysis work?",
                        "What columns should my CSV include?",
                    ],
                    "source": "rule_based_fallback",
                }
        if not emp:
            samples = ae.get_sample_employee_ids(limit=4)
            sample_str = ""
            if samples:
                sample_lines = [f"• **#{s['id']}** ({s['role']}, {s['department']})" for s in samples]
                sample_str = "\n\n**Valid sample employee IDs in this dataset:**\n" + "\n".join(sample_lines)

            return {
                "intent": "employee_lookup",
                "response": (
                    f"🔍 **Employee ID `#{emp_id}` not found** in the active dataset (`{dl.DATASET_NAME or 'uploaded cohort'}`).\n\n"
                    f"There are **{dl.TOTAL_EMPLOYEES:,}** total employees in this dataset.{sample_str}\n\n"
                    f"Please verify the employee ID or consult the High-Risk Watchlist table on the dashboard."
                ),
                "suggestions": [
                    f"Tell me about employee {samples[0]['id']}" if samples else "Who is likely to leave?",
                    "Who is likely to leave?",
                    "Which department has highest attrition?",
                ],
                "source": "rule_based_fallback",
            }

        # Employee was found! Build structured markdown card
        fallback_card = _format_employee_card(emp)

        # Build specific grounding context for Gemini
        emp_context = (
            f"[SPECIFIC EMPLOYEE RECORD FROM VERIFIED DATASET]\n"
            f"Employee #{emp['employee_number']}:\n"
            f"- Role: {emp['job_role']}, Department: {emp['department']}\n"
            f"- Demographics: Age {emp['age']}, Gender {emp['gender']}, Marital Status {emp['marital_status']}\n"
            f"- Compensation: ₹{emp['monthly_income']:,.0f}/mo, Stock Option Level: {emp['stock_option_level']}\n"
            f"- Tenure: {emp['years_at_company']} years at company\n"
            f"- Overtime: {emp['overtime']}\n"
            f"- Satisfaction: Job={emp['job_satisfaction']}/4 ({emp['job_satisfaction_label']}), "
            f"Environment={emp['env_satisfaction']}/4, Work-Life Balance={emp['work_life_balance']}/4\n"
            f"- Distance From Home: {emp['distance_from_home']} miles, Travel: {emp['business_travel']}\n"
            f"- Flight Risk Score: {emp['risk_score']}/8 ({emp['risk_level']} Flight Risk)\n"
            f"- Attrition Status: {emp['attrition']} ({'Departed/Left' if emp['attrition_flag'] else 'Active/Retained'})\n"
            f"- Specific Flight Risk Drivers: {', '.join(emp['risk_reasons']) if emp['risk_reasons'] else 'None (Stable profile)'}\n\n"
            f"INSTRUCTION: Give a comprehensive, structured breakdown of this specific employee. "
            f"Quote their exact role, salary, satisfaction ratings, flight risk score, key risk drivers, "
            f"and tailored HR retention recommendations for this individual. Use clean markdown bullets and emojis."
        )

        gemini_reply = _call_gemini_api(user_message, custom_context=emp_context)
        if gemini_reply:
            return {
                "intent": "employee_lookup",
                "response": gemini_reply,
                "data": {"employee": emp},
                "suggestions": [
                    "Why do employees leave?",
                    "Who is likely to leave?",
                    "What recommendations do you have?",
                ],
                "source": "gemini_ai",
            }

        return {
            "intent": "employee_lookup",
            "response": fallback_card,
            "data": {"employee": emp},
            "suggestions": [
                "Why do employees leave?",
                "Who is likely to leave?",
                "What recommendations do you have?",
            ],
            "source": "rule_based_fallback",
        }

    # ── General Query Handling ─────────────────────────────
    intent = _match_intent(user_message)
    fallback_data = _format_response(intent) if intent != "unknown" else None

    # 1. Primary path: Generate response using Google Gemini AI
    gemini_reply = _call_gemini_api(user_message)
    if gemini_reply:
        suggestions = [
            "Who is likely to leave?",
            "Why do employees leave?",
            "Which department has highest attrition?",
            "What recommendations do you have?",
        ]
        if fallback_data and fallback_data.get("suggestions"):
            suggestions = fallback_data["suggestions"]

        return {
            "intent": intent,
            "response": gemini_reply,
            "data": fallback_data.get("data") if fallback_data else None,
            "suggestions": suggestions,
            "source": "gemini_ai",
        }

    # 2. Offline / Fallback path: Pre-computed dataset responses
    response_data = _format_response(intent)
    return {
        "intent": intent,
        "response": response_data.get("response", ""),
        "data": response_data.get("data"),
        "suggestions": response_data.get("suggestions", []),
        "source": "rule_based_fallback",
    }


