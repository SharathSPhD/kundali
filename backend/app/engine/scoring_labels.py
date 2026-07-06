"""Shared score-to-label mapping for predictions and interpretation.

Thresholds must stay in sync across all callers — do not duplicate these
bounds elsewhere.
"""


def favorability_label(score: float) -> str:
    """Map a tanh-squashed area score in [-1, 1] to a human-readable label."""
    if score >= 0.5:
        return "strongly favourable"
    if score >= 0.15:
        return "moderately favourable"
    if score > -0.15:
        return "mixed"
    if score > -0.5:
        return "somewhat strained"
    return "notably strained"
