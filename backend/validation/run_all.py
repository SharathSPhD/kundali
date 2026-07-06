"""Run the full external validation suite and print a JSON report.

    cd backend && python -m validation.run_all > /tmp/validation_report.json

Needs network for the Horizons check (~70 calls, ~2 min with the politeness
delay) and expects `validation/data/{birth_location.csv,marriage.csv}` and
`validation/data/c_sample/c_sample.xml` to already be downloaded (see
VALIDATION.md "Reproducing this report" for the fetch commands).
"""
from __future__ import annotations

import json

from validation import validate_astrodatabank, validate_horizons, validate_vedastro_birth, validate_vedastro_marriage


def main() -> dict:
    print("Running JPL Horizons cross-check (network, ~2 min)...")
    horizons_results = validate_horizons.run()
    horizons_summary = validate_horizons.summarize(horizons_results)

    print("Running vedastro birth-location smoke test + distribution sanity...")
    birth = {
        "smoke_test": validate_vedastro_birth.smoke_test(),
        "distribution_sanity": validate_vedastro_birth.distribution_sanity(),
    }

    print("Running vedastro marriage-date predictive backtest...")
    marriage = validate_vedastro_marriage.run()

    print("Running AstroDatabank C-sample tropical sign cross-check...")
    astrodatabank = validate_astrodatabank.run()

    return {
        "horizons": {"summary": {k: v for k, v in horizons_summary.items() if k != "worst"},
                    "worst": horizons_summary.get("worst").__dict__ if horizons_summary.get("worst") else None},
        "vedastro_birth_location": birth,
        "vedastro_marriage_backtest": marriage,
        "astrodatabank_c_sample": astrodatabank,
    }


if __name__ == "__main__":
    print(json.dumps(main(), indent=2))
