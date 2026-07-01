"""Provenance Guard — Flask API.

Milestone 4 scope: POST /submit runs both signals (Groq LLM + stylometry),
combines them into a calibrated confidence score, writes a structured audit-log
row (both signal scores + combined), and returns the verdict. The transparency
label is still a PLACEHOLDER here; label variants arrive in M5.
"""

import uuid

from flask import Flask, jsonify, request

import audit
from llm_signal import classify_llm
from scoring import combine_scores
from stylometric_signal import analyze_stylometry

app = Flask(__name__)
audit.init_db()


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

    # Label still a placeholder until M5.
    transparency_label = "(placeholder label — implemented in Milestone 5)"

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


@app.get("/log")
def log():
    return jsonify({"entries": audit.get_log()})


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
