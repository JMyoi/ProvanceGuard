"""Shared configuration constants for Provenance Guard.

Centralizing these keeps the scoring thresholds identical everywhere they're
referenced (scoring logic, labels, docs) so nothing silently drifts from
planning.md.
"""

# --- Groq LLM signal ---
GROQ_MODEL = "llama-3.3-70b-versatile"
LLM_TEMPERATURE = 0.0  # deterministic-ish classification

# --- Confidence scoring (see planning.md ss.2) ---
# combined = LLM_WEIGHT * llm_score + STYLOMETRIC_WEIGHT * stylometric_score
LLM_WEIGHT = 0.65
STYLOMETRIC_WEIGHT = 0.35

# If the two signals disagree by more than this, force "uncertain".
DISAGREEMENT_THRESHOLD = 0.40

# Attribution buckets on the combined score (asymmetric on purpose:
# it takes more evidence to call something AI than to leave it alone).
AI_THRESHOLD = 0.75      # >= 0.75           -> likely_ai
HUMAN_THRESHOLD = 0.45   # <  0.45           -> likely_human
                         # in between        -> uncertain

# Below this word count the stylometric signal is statistically unreliable.
MIN_WORDS_FOR_STYLOMETRY = 40

# --- Storage ---
DB_PATH = "provenance.db"
