"""Verify parsed LLM claims against exported engine facts."""
from __future__ import annotations

# Numeric tolerance: +/-0.05 absolute OR +/-10% relative (whichever is larger).
_ABS_TOLERANCE = 0.05
_REL_TOLERANCE = 0.10


def _numeric_close(expected: float | None, claimed: float) -> bool:
    if expected is None:
        return False
    tol = max(_ABS_TOLERANCE, abs(expected) * _REL_TOLERANCE)
    return abs(expected - claimed) <= tol


def verify_claims(claims: list[dict], facts: dict) -> dict:
    """Return verification outcome.

    `verified` is True only when claims were found AND all checked out.
    `verified` is None when no checkable claims were parsed.
    `verified` is False when at least one claim was rejected.
    """
    if not claims:
        return {
            "verified": None,
            "checked": [],
            "rejected_claims": [],
            "verification_warnings": ["no checkable claims found in text"],
        }

    checked: list[dict] = []
    rejected: list[dict] = []
    warnings: list[str] = []

    active_yogas = facts.get("yogas.active") or []

    for claim in claims:
        ctype = claim.get("type")
        ok = False
        detail = ""

        if ctype == "planet_in_sign":
            key = f"planets.{claim['planet']}.sign_name"
            expected = facts.get(key)
            ok = expected is not None and expected.lower() == claim["sign"].lower()
            detail = f"{key}={expected!r}, claimed {claim['sign']!r}"

        elif ctype == "dasha_lord":
            maha = facts.get("dasha.mahadasha_lord")
            antar = facts.get("dasha.antardasha_lord")
            ok = claim["lord"] in (maha, antar)
            detail = f"maha={maha!r}, antar={antar!r}, claimed {claim['lord']!r}"

        elif ctype == "yoga_present":
            ok = claim["yoga_name"] in active_yogas
            detail = f"active={active_yogas}, claimed {claim['yoga_name']!r}"

        elif ctype == "score_claim":
            key = f"areas.{claim['area']}.score"
            expected = facts.get(key)
            ok = _numeric_close(expected, claim["value"])
            detail = f"{key}={expected}, claimed {claim['value']}"

        elif ctype == "shadbala_claim":
            key = f"shadbala.{claim['planet']}.total_rupas"
            expected = facts.get(key)
            ok = _numeric_close(expected, claim["value"])
            detail = f"{key}={expected}, claimed {claim['value']}"

        else:
            warnings.append(f"unknown claim type: {ctype}")
            continue

        entry = {"claim": claim, "detail": detail, "ok": ok}
        checked.append(entry)
        if not ok:
            rejected.append(entry)

    if not checked:
        return {
            "verified": None,
            "checked": [],
            "rejected_claims": [],
            "verification_warnings": warnings or ["no checkable claims found in text"],
        }

    return {
        "verified": len(rejected) == 0,
        "checked": checked,
        "rejected_claims": rejected,
        "verification_warnings": warnings,
    }
