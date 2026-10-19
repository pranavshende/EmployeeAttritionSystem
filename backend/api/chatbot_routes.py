"""
Chatbot API Routes
POST endpoint for processing chatbot messages.
"""

from flask import Blueprint, jsonify, request
from .. import chatbot_engine

chatbot_bp = Blueprint("chatbot", __name__)


@chatbot_bp.route("/api/chatbot/message", methods=["POST"])
def chat_message():
    data = request.get_json()
    if not data or "message" not in data:
        return jsonify({"error": "Missing 'message' field"}), 400

    user_message = data["message"].strip()
    if not user_message:
        return jsonify({"error": "Empty message"}), 400

    result = chatbot_engine.process_message(user_message)
    return jsonify(result)
