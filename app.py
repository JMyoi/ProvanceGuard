"""Provenance Guard — Flask API.

Milestone 3 scope: POST /submit runs Signal 1 (Groq LLM), writes a structured
audit-log row, and returns a content_id + attribution. Confidence and the
transparency label are PLACEHOLDERS here; real multi-signal confidence scoring
arrives in M4 and the label variants in M5.
"""

import uuid

from flask import Flask, jsonify, request

import audit
from config import AI_THRESHOLD, HUMAN_THRESHOLD
from llm_signal import classify_llm

app = Flask(__name__)
audit.init_db()


def _interim_attribution(score):
    """M3 placeholder: bucket a single-signal score until M4 scoring lands."""
    if score >= AI_THRESHOLD:
        return "likely_ai"
    if score < HUMAN_THRESHOLD:
        return "likely_human"
    return "uncertain"


@app.get("/health")
def health():
    return jsonify({"status": "ok"})


@app.post("/submit")
def submit():
    data = request.get_json(silent=True) or {}
    text = (data.get("text") or "").strip()
    creator_id = (data.get("creator_id") or "").strip()

    if not text:
        return jsonify({"error": "Field 'text' is required."}), 400
    if not creator_id:
        return jsonify({"error": "Field 'creator_id' is required."}), 400

    # Signal 1 — Groq LLM.
    try:
        llm = classify_llm(text)
    except RuntimeError as e:
        return jsonify({"error": str(e)}), 502

    llm_score = llm["score"]
    attribution = _interim_attribution(llm_score)
    content_id = str(uuid.uuid4())

    # PLACEHOLDERS until M4/M5.
    confidence = llm_score  # replaced by combined score in M4
    transparency_label = "(placeholder label — implemented in Milestone 5)"

    audit.log_classification(
        content_id=content_id,
        creator_id=creator_id,
        attribution=attribution,
        confidence=confidence,
        llm_score=llm_score,
    )

    return jsonify(
        {
            "content_id": content_id,
            "attribution": attribution,
            "confidence": confidence,
            "signals": {"llm_score": llm_score, "llm_rationale": llm["rationale"]},
            "transparency_label": transparency_label,
        }
    )


@app.get("/log")
def log():
    return jsonify({"entries": audit.get_log()})


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
