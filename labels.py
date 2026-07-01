"""Transparency label generator.

Maps a confidence verdict to the reader-facing label text. Three variants
(planning.md ss.3), one per attribution bucket. Copy leans cautious and never
states a verdict as fact; confidence is shown as a rounded percentage framed as
"probability this is AI-generated" so a low number reads reassuringly on the
human label.
"""


def generate_label(attribution, confidence):
    """Return the plain-language transparency label for a verdict.

    attribution: 'likely_ai' | 'likely_human' | 'uncertain'
    confidence:  float in [0,1] = P(AI-generated)
    """
    pct = round(confidence * 100)

    if attribution == "likely_ai":
        return (
            f"⚠️ Likely AI-generated. Our analysis suggests this content was "
            f"probably created with AI assistance (confidence: {pct}%). This is an "
            f"automated estimate, not a certainty — the creator can appeal if they "
            f"believe this is wrong."
        )
    if attribution == "likely_human":
        return (
            f"✅ Likely human-written. Our analysis found no strong signs of AI "
            f"generation (confidence: {pct}% that this is AI). This is an automated "
            f"estimate and not a guarantee of authorship."
        )
    # uncertain
    return (
        f"❓ Uncertain origin. Our signals disagree or are inconclusive, so we "
        f"can't reliably say whether this was written by a human or AI (confidence: "
        f"{pct}% that this is AI). We're showing this openly rather than guessing. "
        f"The creator can provide context via an appeal."
    )
