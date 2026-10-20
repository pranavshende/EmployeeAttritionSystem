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


# ─────────────────────────────────────────────────────────────
#  HR Document & Policy Knowledge (RAG) Endpoints
# ─────────────────────────────────────────────────────────────

@chatbot_bp.route("/api/documents", methods=["GET"])
def get_documents():
    """List all indexed HR policies, handbooks, and knowledge documents."""
    from .. import rag_engine as rag
    docs = rag.list_documents()
    return jsonify({"documents": docs, "total": len(docs)})


@chatbot_bp.route("/api/documents/upload", methods=["POST"])
def upload_document():
    """Upload and index a new HR document (PDF, DOCX, TXT, MD) into RAG store."""
    from .. import rag_engine as rag
    import os

    if "file" not in request.files:
        return jsonify({"error": "No file uploaded. Please attach a document."}), 400

    file = request.files["file"]
    if not file.filename:
        return jsonify({"error": "Empty filename."}), 400

    filename = file.filename
    allowed_exts = {".pdf", ".docx", ".doc", ".txt", ".md", ".json", ".html"}
    ext = os.path.splitext(filename)[1].lower()
    if ext not in allowed_exts:
        return jsonify({"error": f"Unsupported format. Allowed: {', '.join(allowed_exts)}"}), 400

    save_path = os.path.join(rag.DOCS_DIR, filename)
    file.save(save_path)

    title = request.form.get("title") or os.path.splitext(filename)[0].replace("_", " ").title()
    category = request.form.get("category", "Policy")

    result = rag.ingest_document(save_path, filename, title=title, metadata={"category": category})
    if "error" in result:
        return jsonify(result), 400

    return jsonify({
        "status": "success",
        "message": f"Successfully indexed '{filename}' ({result['chunks_created']} chunks).",
        "document": result,
    })


@chatbot_bp.route("/api/documents/<doc_id>", methods=["DELETE"])
def delete_document(doc_id):
    """Delete a document and its chunks from the RAG store."""
    from .. import rag_engine as rag
    success = rag.delete_document(doc_id)
    return jsonify({"status": "success" if success else "not_found", "doc_id": doc_id})


@chatbot_bp.route("/api/documents/search", methods=["GET"])
def search_documents():
    """Perform ad-hoc semantic search across HR documents."""
    from .. import rag_engine as rag
    query = request.args.get("q", "").strip()
    if not query:
        return jsonify({"error": "Missing 'q' query parameter"}), 400
    top_k = request.args.get("limit", 4, type=int)
    hits = rag.search_documents(query, top_k=top_k)
    return jsonify({"query": query, "results": hits, "total": len(hits)})
