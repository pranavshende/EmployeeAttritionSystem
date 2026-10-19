"""
Flask Application Entry Point
Serves the backend API and static frontend files.
"""

import os
import sys

# Ensure project root is in sys.path
_current_dir = os.path.dirname(os.path.abspath(__file__))
_parent_dir = os.path.dirname(_current_dir)
if _parent_dir not in sys.path:
    sys.path.insert(0, _parent_dir)

from flask import Flask, send_from_directory
from flask_cors import CORS

try:
    from .api.dashboard_routes import dashboard_bp
    from .api.chatbot_routes import chatbot_bp
except (ImportError, ValueError):
    from backend.api.dashboard_routes import dashboard_bp
    from backend.api.chatbot_routes import chatbot_bp


def create_app():
    # Resolve paths
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    dist_dir = os.path.join(base_dir, "frontend", "dist")
    frontend_dir = dist_dir if os.path.exists(dist_dir) else os.path.join(base_dir, "frontend")

    app = Flask(__name__, static_folder=frontend_dir, static_url_path="")
    CORS(app)

    # Register API blueprints
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(chatbot_bp)

    # Serve frontend
    @app.route("/")
    def serve_index():
        if os.path.exists(os.path.join(frontend_dir, "index.html")):
            return send_from_directory(frontend_dir, "index.html")
        return {"status": "backend ready", "api": "/api/health"}, 200

    @app.route("/<path:path>")
    def serve_static(path):
        if os.path.exists(os.path.join(frontend_dir, path)):
            return send_from_directory(frontend_dir, path)
        # SPA fallback
        if os.path.exists(os.path.join(frontend_dir, "index.html")):
            return send_from_directory(frontend_dir, "index.html")
        return {"error": "Not found"}, 404


    return app


app = create_app()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
