"""Confidence scoring — combine the two signals into one calibrated verdict.

Implements planning.md ss.2 exactly:

  combined = 0.65 * llm_score + 0.35 * stylometric_score

  * Disagreement guard: if the signals differ by more than DISAGREEMENT_THRESHOLD
    (0.40), the attribution is forced to "uncertain" regardless of the average -
    two blind detectors that conflict shouldn't produce a confident verdict.
  * Short text: if the stylometric signal is unreliable (text too short), we lean
    entirely on the LLM for the combined score rather than trusting sparse stats.
  * Thresholds are asymmetric (AI at 0.75, human at 0.45): it takes more evidence
    to call something AI than to leave it alone, because a false "AI" accusation
    is the costlier error on a writing platform.

`confidence` is always P(AI-generated) in [0,1]; `attribution` is the bucket the
label is built from.
"""

from config import (
    AI_THRESHOLD,
    DISAGREEMENT_THRESHOLD,
    HUMAN_THRESHOLD,
    LLM_WEIGHT,
    STYLOMETRIC_WEIGHT,
)


def _bucket(score):
    if score >= AI_THRESHOLD:
        return "likely_ai"
    if score < HUMAN_THRESHOLD:
        return "likely_human"
    return "uncertain"


def combine_scores(llm_score, stylometric_score, stylometry_reliable=True):
    """Return the combined confidence verdict.

    Returns dict: {
        confidence, attribution, disagreement (bool), reasons (list[str])
    }
    """
    reasons = []

    if not stylometry_reliable:
        # Too little text for structural stats -> trust the semantic signal alone.
        combined = llm_score
        disagreement = False
        reasons.append(
            "Stylometric signal unreliable (text too short); using LLM signal only."
        )
    else:
        combined = LLM_WEIGHT * llm_score + STYLOMETRIC_WEIGHT * stylometric_score
        disagreement = abs(llm_score - stylometric_score) > DISAGREEMENT_THRESHOLD
        if disagreement:
            reasons.append(
                f"Signals disagree by more than {DISAGREEMENT_THRESHOLD:.2f} "
                f"(llm={llm_score:.2f}, stylometric={stylometric_score:.2f}); "
                "forcing 'uncertain'."
            )

    combined = max(0.0, min(1.0, combined))

    if disagreement:
        attribution = "uncertain"
    else:
        attribution = _bucket(combined)

    return {
        "confidence": round(combined, 3),
        "attribution": attribution,
        "disagreement": disagreement,
        "reasons": reasons,
    }
