"""Calibration harness (Milestone 4).

Runs the 4 deliberately-chosen assignment inputs through both signals + the
confidence scorer and prints each signal separately, so we can see which signal
drives each verdict and confirm scores match intuition. Run:

    python test_calibration.py
"""

from llm_signal import classify_llm
from scoring import combine_scores
from stylometric_signal import analyze_stylometry

CASES = [
    ("clearly AI  (expect likely_ai)",
     "Artificial intelligence represents a transformative paradigm shift in modern "
     "society. It is important to note that while the benefits of AI are numerous, it "
     "is equally essential to consider the ethical implications. Furthermore, "
     "stakeholders across various sectors must collaborate to ensure responsible "
     "deployment."),
    ("clearly human  (expect likely_human)",
     "ok so i finally tried that new ramen place downtown and honestly? underwhelming. "
     "the broth was fine but they put WAY too much sodium in it and i was thirsty for "
     "like three hours after. my friend got the spicy version and said it was better. "
     "probably won't go back unless someone drags me there"),
    ("borderline: formal human  (expect uncertain-ish, not likely_ai)",
     "The relationship between monetary policy and asset price inflation has been "
     "extensively studied in the literature. Central banks face a fundamental tension "
     "between their mandate for price stability and the unintended consequences of "
     "prolonged low interest rates on equity and real estate valuations."),
    ("borderline: lightly edited AI  (expect mid-range/uncertain)",
     "I've been thinking a lot about remote work lately. There are genuine tradeoffs - "
     "flexibility and no commute on one side, isolation and blurred work-life "
     "boundaries on the other. Studies show productivity varies widely by individual "
     "and role type."),
]


def main():
    for label, text in CASES:
        llm = classify_llm(text)
        styl = analyze_stylometry(text)
        verdict = combine_scores(llm["score"], styl["score"], styl["reliable"])
        print(f"\n=== {label} ===")
        print(f"  llm_score        = {llm['score']:.2f}   ({llm['rationale']})")
        print(f"  stylometric_score= {styl['score']:.2f}   (reliable={styl['reliable']})")
        print(f"  -> confidence    = {verdict['confidence']:.2f}")
        print(f"  -> attribution   = {verdict['attribution']}")
        if verdict["reasons"]:
            print(f"  -> notes         = {verdict['reasons']}")


if __name__ == "__main__":
    main()
