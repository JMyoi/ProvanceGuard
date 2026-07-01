"""Provenance Guard — Flask API.

Full system (Milestone 5). POST /submit runs both signals (Groq LLM +
stylometry), combines them into a calibrated confidence score, generates a
reader-facing transparency label, writes a structured audit-log row, and returns
the verdict. POST /appeal lets a creator contest a decision (status ->
under_review, logged beside the original). Rate limiting protects /submit;
GET /log surfaces the audit trail.
"""

import uuid

from flask import Flask, jsonify, request
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

import audit
from labels import generate_label
from llm_signal import classify_llm
from scoring import combine_scores
from stylometric_signal import analyze_stylometry

app = Flask(__name__)
audit.init_db()

# Rate limiting (see README for chosen limits + reasoning). In-memory storage is
# fine for local/dev; a real deployment would use Redis so limits survive restarts
# and span multiple workers.
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=[],
    storage_uri="memory://",
)


@app.errorhandler(429)
def ratelimit_exceeded(e):
    """Return rate-limit rejections as JSON (this is a JSON API)."""
    return (
        jsonify(
            {
                "error": "Rate limit exceeded. Please slow down and try again later.",
                "limit": str(e.description),
            }
        ),
        429,
    )


@app.get("/health")
def health():
    return jsonify({"status": "ok"})


@app.post("/submit")
@limiter.limit("10 per minute;100 per day")
def submit():
    data = request.get_json(silent=True) or {}
    text = (data.get("text") or "").strip()
    creator_id = (data.get("creator_id") or "").strip()

    if not text:
        return jsonify({"error": "Field 'text' is required."}), 400
    if not creator_id:
        return jsonify({"error": "Field 'creator_id' is required."}), 400

    # Signal 1 — Groq LLM (semantic).
    try:
        llm = classify_llm(text)
    except RuntimeError as e:
        return jsonify({"error": str(e)}), 502
    llm_score = llm["score"]

    # Signal 2 — stylometry (structural).
    styl = analyze_stylometry(text)
    stylometric_score = styl["score"]

    # Combine into one calibrated confidence + attribution bucket.
    verdict = combine_scores(llm_score, stylometric_score, styl["reliable"])
    confidence = verdict["confidence"]
    attribution = verdict["attribution"]
    content_id = str(uuid.uuid4())

    transparency_label = generate_label(attribution, confidence)

    audit.log_classification(
        content_id=content_id,
        creator_id=creator_id,
        attribution=attribution,
        confidence=confidence,
        llm_score=llm_score,
        stylometric_score=stylometric_score,
    )

    return jsonify(
        {
            "content_id": content_id,
            "attribution": attribution,
            "confidence": confidence,
            "signals": {
                "llm_score": llm_score,
                "llm_rationale": llm["rationale"],
                "stylometric_score": stylometric_score,
                "stylometric_reliable": styl["reliable"],
            },
            "scoring_notes": verdict["reasons"],
            "transparency_label": transparency_label,
        }
    )


@app.post("/appeal")
def appeal():
    data = request.get_json(silent=True) or {}
    content_id = (data.get("content_id") or "").strip()
    creator_reasoning = (data.get("creator_reasoning") or "").strip()

    if not content_id:
        return jsonify({"error": "Field 'content_id' is required."}), 400
    if not creator_reasoning:
        return jsonify({"error": "Field 'creator_reasoning' is required."}), 400

    original = audit.get_latest_classification(content_id)
    if original is None:
        return jsonify({"error": f"No classification found for content_id {content_id!r}."}), 404

    audit.log_appeal(
        content_id=content_id,
        creator_id=original.get("creator_id"),
        creator_reasoning=creator_reasoning,
        original=original,
    )

    return jsonify(
        {
            "content_id": content_id,
            "status": "under_review",
            "message": (
                "Your appeal has been received and the content is now under review. "
                "The original classification has been preserved for a human reviewer."
            ),
        }
    )


@app.get("/log")
def log():
    return jsonify({"entries": audit.get_log()})


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
