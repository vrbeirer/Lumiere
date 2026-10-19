from flask import Blueprint, request, jsonify, session
import uuid

GREETINGS = {"hi", "hello", "hey", "good morning", "good evening", "good afternoon", "greetings"}

chat_bp = Blueprint("chat", __name__)


@chat_bp.route("/chat", methods=["POST"])
def chat():
    from backend.core.llm import generate, clear_session

    data = request.get_json(silent=True)
    if not data or not data.get("message", "").strip():
        return jsonify({"error": "Message is required."}), 400

    query = data["message"].strip()

    if "session_id" not in session:
        session["session_id"] = str(uuid.uuid4())

    session_id = session["session_id"]

    if query.lower() in GREETINGS:
        answer = "Good day! Welcome to The Leela. I'm your personal concierge — how may I assist you today?"
        sources = []
    else:
        answer, sources = generate(query, session_id)

    return jsonify({"answer": answer, "sources": sources})


@chat_bp.route("/reset", methods=["POST"])
def reset():
    from backend.core.llm import clear_session
    session_id = session.pop("session_id", None)
    if session_id:
        clear_session(session_id)
    return jsonify({"status": "ok"})