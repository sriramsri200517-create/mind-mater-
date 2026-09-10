import os

import requests
from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request

from chatbot_config import (
    CHATBOT_EMOJI,
    CHATBOT_TAGLINE,
    CHATBOT_TITLE,
    DOMAIN_SHORT,
    GEMINI_MODEL,
    GREETING,
    SUGGESTED_QUESTIONS,
    SYSTEM_PROMPT,
    THEME,
)

load_dotenv()

app = Flask(__name__)

API_KEY = os.environ.get("GEMINI_API_KEY", "")
API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"


@app.route("/")
def home():
    return render_template(
        "index.html",
        title=CHATBOT_TITLE,
        tagline=CHATBOT_TAGLINE,
        emoji=CHATBOT_EMOJI,
        greeting=GREETING,
        suggestions=SUGGESTED_QUESTIONS,
        theme=THEME,
        domain_short=DOMAIN_SHORT,
    )


def ask_gemini(message, history):
    contents = []
    for turn in history[-10:]:
        role = turn.get("role")
        text = str(turn.get("text", "")).strip()
        if role in ("user", "model") and text:
            contents.append({"role": role, "parts": [{"text": text}]})
    contents.append({"role": "user", "parts": [{"text": message}]})

    payload = {
        "system_instruction": {"parts": [{"text": SYSTEM_PROMPT}]},
        "contents": contents,
        "generationConfig": {"temperature": 0.7, "topP": 0.9, "maxOutputTokens": 1024},
    }
    response = requests.post(API_URL, json=payload, params={"key": API_KEY}, timeout=60)
    response.raise_for_status()
    data = response.json()

    fallback = "I'm sorry, I couldn't generate an answer right now. Please rephrase and try again."
    candidates = data.get("candidates") or []
    if not candidates:
        return fallback
    parts = candidates[0].get("content", {}).get("parts", [])
    reply = "".join(part.get("text", "") for part in parts).strip()
    return reply or fallback


@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.get_json(silent=True) or {}
    message = str(data.get("message", "")).strip()
    history = data.get("history") or []

    if not message:
        return jsonify({"reply": "Please type a question first."}), 400
    if not API_KEY:
        return jsonify({"reply": "Server is missing the GEMINI_API_KEY. Add it to the .env file and restart."}), 500

    try:
        reply = ask_gemini(message, history)
    except requests.exceptions.Timeout:
        return jsonify({"reply": "That took too long. Please try again."}), 504
    except requests.exceptions.RequestException:
        return jsonify({"reply": "I could not reach the AI service. Please try again in a moment."}), 502

    return jsonify({"reply": reply})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
