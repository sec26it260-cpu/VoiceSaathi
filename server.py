from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import time
import requests

app = Flask(__name__)

CORS(app)

API_KEY = os.environ.get("GEMINI_API_KEY")

MODEL = "gemini-2.5-flash"

# Simple request limit
request_log = {}

@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "project": "VoiceSaathi Edu",
        "status": "Backend running"
    })


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "healthy"})


@app.route("/api/ask", methods=["POST"])
def ask():

    if not API_KEY:
        return jsonify({
            "error": "AI service is not configured"
        }), 503

    ip = request.remote_addr or "unknown"
    now = time.time()

    recent = [
        t for t in request_log.get(ip, [])
        if now - t < 600
    ]

    if len(recent) >= 10:
        return jsonify({
            "error": "Request limit reached. Try again later."
        }), 429

    recent.append(now)
    request_log[ip] = recent

    data = request.get_json(silent=True) or {}

    question = str(data.get("question", "")).strip()
    subject = str(data.get("subject", "General")).strip()[:40]
    language = str(data.get("language", "English")).strip()[:20]

    if not question:
        return jsonify({"error": "Question is required"}), 400

    if len(question) > 800:
        return jsonify({"error": "Question is too long"}), 400

    prompt = f"""
You are VoiceSaathi Edu, a friendly educational AI tutor
for Indian students.

Subject: {subject}
Preferred language: {language}

Student question: {question}

Instructions:
1. Answer in the selected language.
2. Explain concepts in simple student-friendly words.
3. For mathematics, show steps clearly.
4. Give one simple example when useful.
5. Use headings when helpful.
6. Do not invent facts or pretend uncertain answers are certain.
7. If the question is outside education, politely redirect
   the student to learning topics.
8. Keep the answer concise and understandable.
9. Do not request personal information from students.
"""

    url = (
        "https://generativelanguage.googleapis.com/"
        f"v1beta/models/{MODEL}:generateContent"
    )

    try:
        response = requests.post(
            url,
            headers={
                "x-goog-api-key": API_KEY,
                "Content-Type": "application/json"
            },
            json={
                "contents": [{
                    "parts": [{"text": prompt}]
                }],
                "generationConfig": {
                    "temperature": 0.4,
                    "maxOutputTokens": 700
                }
            },
            timeout=35
        )

        if not response.ok:
            return jsonify({
                "error": "AI service temporarily unavailable"
            }), 502

        result = response.json()

        answer = "".join(
            part.get("text", "")
            for part in result["candidates"][0]
                ["content"]["parts"]
            if "text" in part
        ).strip()

        if not answer:
            return jsonify({
                "error": "No answer received"
            }), 502

        return jsonify({
            "answer": answer,
            "engine": "Gemini AI",
            "subject": subject
        })

    except requests.RequestException:
        return jsonify({
            "error": "Could not connect to AI service"
        }), 502

    except (KeyError, IndexError, TypeError):
        return jsonify({
            "error": "Unexpected AI response"
        }), 502


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000))
    )
