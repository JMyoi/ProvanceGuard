"""Signal 2 — Stylometric analyzer (structural / statistical, pure Python).

Measures three length-and-structure statistics that differ between human and AI
writing (planning.md ss.1) and maps them to a single 0-1 AI-likelihood score:

  1. Sentence-length variance (burstiness) - AI is uniform, humans are bursty.  [weight 0.50]
  2. Punctuation density (marks per word)  - AI is moderate/tidy.               [weight 0.30]
  3. Type-token ratio (vocabulary diversity)                                    [weight 0.20]

Burstiness is weighted highest: it's the most reliable discriminator. TTR is
weighted lowest because it's the noisiest (heavily length-dependent, and casual
human text can look repetitive) - see README known limitations.

Output contract:
    { "score": float in [0,1], "reliable": bool, "metrics": {...} }
`reliable` is False for very short text (< MIN_WORDS_FOR_STYLOMETRY), where the
statistics are too sparse to trust.
"""

import re
import statistics

from config import MIN_WORDS_FOR_STYLOMETRY

# Within-signal weights (sum to 1.0).
_W_BURSTINESS = 0.50
_W_PUNCTUATION = 0.30
_W_TTR = 0.20

_SENTENCE_SPLIT = re.compile(r"[.!?]+")
_WORD = re.compile(r"\b[\w']+\b")
_PUNCT = re.compile(r"[.,;:!?\"'()\-—]")


def _lin(x, lo, hi):
    """Linear ramp: 0 at lo, 1 at hi, clamped to [0,1]. (hi may be < lo.)"""
    if hi == lo:
        return 0.0
    return max(0.0, min(1.0, (x - lo) / (hi - lo)))


def _split_sentences(text):
    return [s for s in (p.strip() for p in _SENTENCE_SPLIT.split(text)) if s]


def analyze_stylometry(text):
    words = _WORD.findall(text)
    word_count = len(words)
    sentences = _split_sentences(text)

    # Degenerate/empty input: no structural signal at all.
    if word_count == 0 or len(sentences) == 0:
        return {"score": 0.5, "reliable": False,
                "metrics": {"word_count": word_count, "note": "too little text"}}

    # --- Metric 1: sentence-length burstiness (coefficient of variation) ---
    lengths = [len(_WORD.findall(s)) for s in sentences]
    mean_len = statistics.mean(lengths)
    if len(lengths) >= 2 and mean_len > 0:
        cv = statistics.pstdev(lengths) / mean_len
    else:
        cv = 0.0  # single sentence -> no variance information
    # Low CV (uniform) -> AI. cv<=0.25 => 1.0 (AI), cv>=0.75 => 0.0 (human).
    burstiness_ai = 1.0 - _lin(cv, 0.25, 0.75)

    # --- Metric 2: punctuation density (marks per word) ---
    punct_count = len(_PUNCT.findall(text))
    density = punct_count / word_count
    # Casual human text is sparsely punctuated; tidy AI prose is moderately so.
    # density<=0.03 => human (0.0), density>=0.15 => AI (1.0).
    punctuation_ai = _lin(density, 0.03, 0.15)

    # --- Metric 3: type-token ratio (vocabulary diversity) ---
    ttr = len({w.lower() for w in words}) / word_count
    # Weakest signal. Only strong repetition (low TTR) nudges toward AI/uniform;
    # high diversity nudges toward human. ttr<=0.35 => 1.0, ttr>=0.75 => 0.0.
    ttr_ai = 1.0 - _lin(ttr, 0.35, 0.75)

    score = (
        _W_BURSTINESS * burstiness_ai
        + _W_PUNCTUATION * punctuation_ai
        + _W_TTR * ttr_ai
    )

    return {
        "score": max(0.0, min(1.0, score)),
        "reliable": word_count >= MIN_WORDS_FOR_STYLOMETRY,
        "metrics": {
            "word_count": word_count,
            "sentence_count": len(sentences),
            "sentence_length_cv": round(cv, 3),
            "punctuation_density": round(density, 3),
            "type_token_ratio": round(ttr, 3),
            "burstiness_ai": round(burstiness_ai, 3),
            "punctuation_ai": round(punctuation_ai, 3),
            "ttr_ai": round(ttr_ai, 3),
        },
    }


if __name__ == "__main__":
    samples = {
        "clearly AI": (
            "Artificial intelligence represents a transformative paradigm shift in "
            "modern society. It is important to note that while the benefits of AI "
            "are numerous, it is equally essential to consider the ethical "
            "implications. Furthermore, stakeholders across various sectors must "
            "collaborate to ensure responsible deployment."
        ),
        "clearly human": (
            "ok so i finally tried that new ramen place downtown and honestly? "
            "underwhelming. the broth was fine but they put WAY too much sodium in "
            "it and i was thirsty for like three hours after. my friend got the "
            "spicy version and said it was better. probably won't go back unless "
            "someone drags me there"
        ),
        "formal human": (
            "The relationship between monetary policy and asset price inflation has "
            "been extensively studied in the literature. Central banks face a "
            "fundamental tension between their mandate for price stability and the "
            "unintended consequences of prolonged low interest rates on equity and "
            "real estate valuations."
        ),
        "edited AI": (
            "I've been thinking a lot about remote work lately. There are genuine "
            "tradeoffs - flexibility and no commute on one side, isolation and "
            "blurred work-life boundaries on the other. Studies show productivity "
            "varies widely by individual and role type."
        ),
    }
    for label, txt in samples.items():
        r = analyze_stylometry(txt)
        print(f"[{label}] score={r['score']:.2f} reliable={r['reliable']}")
        print(f"    {r['metrics']}")
