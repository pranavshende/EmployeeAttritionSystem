"""
Dashboard API Routes
REST endpoints for KPIs, chart data, high-risk employees, filters, and filtered analytics.
"""

from flask import Blueprint, jsonify, request
from .. import analytics_engine as ae

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/api/health", methods=["GET"])
def health():
    from .. import data_loader as dl
    return jsonify({
        "status": "ok",
        "rows": dl.TOTAL_EMPLOYEES,
        "columns": 35,
    })


@dashboard_bp.route("/api/kpis", methods=["GET"])
def kpis():
    return jsonify(ae.get_kpis())


# ── Chart Endpoints ──────────────────────────

@dashboard_bp.route("/api/charts/department", methods=["GET"])
def charts_department():
    return jsonify(ae.get_department_data())


@dashboard_bp.route("/api/charts/job-role", methods=["GET"])
def charts_job_role():
    return jsonify(ae.get_job_role_data())


@dashboard_bp.route("/api/charts/age", methods=["GET"])
def charts_age():
    return jsonify(ae.get_age_data())


@dashboard_bp.route("/api/charts/income", methods=["GET"])
def charts_income():
    return jsonify(ae.get_income_data())


@dashboard_bp.route("/api/charts/tenure", methods=["GET"])
def charts_tenure():
    return jsonify(ae.get_tenure_data())


@dashboard_bp.route("/api/charts/distance", methods=["GET"])
def charts_distance():
    return jsonify(ae.get_distance_data())


@dashboard_bp.route("/api/charts/overtime", methods=["GET"])
def charts_overtime():
    return jsonify(ae.get_overtime_data())


@dashboard_bp.route("/api/charts/gender", methods=["GET"])
def charts_gender():
    return jsonify(ae.get_gender_data())


@dashboard_bp.route("/api/charts/marital", methods=["GET"])
def charts_marital():
    return jsonify(ae.get_marital_data())


@dashboard_bp.route("/api/charts/travel", methods=["GET"])
def charts_travel():
    return jsonify(ae.get_travel_data())


@dashboard_bp.route("/api/charts/education", methods=["GET"])
def charts_education():
    return jsonify(ae.get_education_data())


@dashboard_bp.route("/api/charts/education-field", methods=["GET"])
def charts_education_field():
    return jsonify(ae.get_education_field_data())


@dashboard_bp.route("/api/charts/stock-options", methods=["GET"])
def charts_stock_options():
    return jsonify(ae.get_stock_options_data())


@dashboard_bp.route("/api/charts/satisfaction", methods=["GET"])
def charts_satisfaction():
    return jsonify(ae.get_satisfaction_data())


@dashboard_bp.route("/api/charts/work-life-balance", methods=["GET"])
def charts_work_life_balance():
    return jsonify(ae.get_work_life_balance_data())


@dashboard_bp.route("/api/charts/factors", methods=["GET"])
def charts_factors():
    return jsonify(ae.get_contributing_factors())


# ── High-Risk Employees ─────────────────────

@dashboard_bp.route("/api/high-risk", methods=["GET"])
def high_risk():
    min_score = request.args.get("min_score", 3, type=int)
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)
    return jsonify(ae.get_high_risk_employees(min_score, page, per_page))


@dashboard_bp.route("/api/employee/<emp_id>", methods=["GET"])
def get_employee(emp_id):
    emp = ae.get_employee_by_id(emp_id)
    if not emp:
        return jsonify({"error": f"Employee '{emp_id}' not found in active dataset."}), 404
    return jsonify(emp)


# ── Filters ──────────────────────────────────

@dashboard_bp.route("/api/filters", methods=["GET"])
def filters():
    return jsonify(ae.get_filter_options())


@dashboard_bp.route("/api/filtered", methods=["GET"])
def filtered():
    filter_params = {
        "department": request.args.get("department"),
        "job_role": request.args.get("job_role"),
        "gender": request.args.get("gender"),
        "overtime": request.args.get("overtime"),
        "marital_status": request.args.get("marital_status"),
        "age_min": request.args.get("age_min"),
        "age_max": request.args.get("age_max"),
        "income_min": request.args.get("income_min"),
        "income_max": request.args.get("income_max"),
    }
    # Remove None values
    filter_params = {k: v for k, v in filter_params.items() if v is not None}
    return jsonify(ae.get_filtered_analytics(filter_params))


# ── Dataset Upload & Management Endpoints ─────

@dashboard_bp.route("/api/dataset/info", methods=["GET"])
def dataset_info():
    from .. import data_loader as dl
    from .. import chatbot_engine as ce
    info = dict(dl.DATASET_INFO)
    info["suggested_questions"] = ce.generate_dataset_questions()
    return jsonify(info)


@dashboard_bp.route("/api/dataset/upload", methods=["POST"])
def upload_dataset():
    from .. import data_loader as dl
    from .. import chatbot_engine as ce

    if "file" not in request.files:
        return jsonify({"error": "No file uploaded. Please attach a CSV file."}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "Empty filename."}), 400

    if not file.filename.lower().endswith(".csv"):
        return jsonify({"error": "Only CSV files are supported."}), 400

    filename = file.filename
    try:
        # 1. Load and normalize CSV dynamically
        dl.load_custom_csv(file, filename)

        # 2. Reset chatbot conversational sessions for new dataset
        ce.clear_sessions()

        # 3. Generate on-the-spot AI executive summary using Gemini
        ai_summary = ce.generate_ai_dataset_summary(filename)
        suggested_q = ce.generate_dataset_questions()

        info = dict(dl.DATASET_INFO)
        info["suggested_questions"] = suggested_q

        return jsonify({
            "status": "success",
            "message": f"Successfully loaded '{filename}' ({dl.TOTAL_EMPLOYEES:,} records)",
            "dataset_info": info,
            "suggested_questions": suggested_q,
            "ai_summary": ai_summary,
            "kpis": ae.get_kpis(),
        })
    except Exception as e:
        return jsonify({"error": f"Failed to parse CSV file: {str(e)}"}), 500


@dashboard_bp.route("/api/dataset/reset", methods=["POST"])
@dashboard_bp.route("/api/dataset/clear", methods=["POST"])
def clear_or_reset_dataset():
    from .. import data_loader as dl
    from .. import chatbot_engine as ce
    dl.clear_dataset()
    ce.clear_sessions()
    info = dict(dl.DATASET_INFO)
    info["suggested_questions"] = ce.generate_dataset_questions()
    return jsonify({
        "status": "success",
        "message": "Dataset cleared. Ready for new CSV upload.",
        "dataset_info": info,
        "suggested_questions": info["suggested_questions"],
    })


@dashboard_bp.route("/api/dataset/load-sample", methods=["POST"])
def load_sample_dataset():
    from .. import data_loader as dl
    from .. import chatbot_engine as ce
    dl.load_default_dataset()
    ce.clear_sessions()
    ai_summary = ce.generate_ai_dataset_summary()
    suggested_q = ce.generate_dataset_questions()
    info = dict(dl.DATASET_INFO)
    info["suggested_questions"] = suggested_q
    return jsonify({
        "status": "success",
        "message": "Sample dataset loaded successfully",
        "dataset_info": info,
        "suggested_questions": suggested_q,
        "ai_summary": ai_summary,
        "kpis": ae.get_kpis(),
    })

