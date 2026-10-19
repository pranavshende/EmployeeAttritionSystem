"""
Chatbot API Routes
REST endpoints for processing messages, retrieving dynamic dataset questions,
and managing conversational context.
"""

from flask import Blueprint, jsonify, request
from .. import chatbot_engine

chatbot_bp = Blueprint("chatbot", __name__)


@chatbot_bp.route("/api/chatbot/suggestions", methods=["GET"])
def get_suggestions():
    """Retrieve pregenerated dynamic questions derived strictly from the active dataset."""
    questions = chatbot_engine.generate_dataset_questions()
    return jsonify({"suggestions": questions})


@chatbot_bp.route("/api/chatbot/message", methods=["POST"])
def chat_message():
    """Process a user message with session-aware conversational context."""
    data = request.get_json()
    if not data or "message" not in data:
        return jsonify({"error": "Missing 'message' field"}), 400

    user_message = data["message"].strip()
    if not user_message:
        return jsonify({"error": "Empty message"}), 400

    session_id = data.get("session_id", "default")
    result = chatbot_engine.process_message(user_message, session_id=session_id)
    return jsonify(result)


@chatbot_bp.route("/api/chatbot/reset", methods=["POST"])
def reset_chat():
    """Clear conversation history and session context."""
    chatbot_engine.clear_sessions()
    return jsonify({"status": "success", "message": "Chat sessions cleared."})
