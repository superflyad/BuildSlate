"""Keep the public battery geometry and charge interpretation source bound."""

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from buildslate.battery_fit import (  # noqa: E402
    CONCEPT,
    ENVELOPE,
    EVIDENCE,
    PACK_ENVELOPE,
    PROFILE,
    audit,
    audit_data,
)
from buildslate.io import load_yaml  # noqa: E402


def main() -> int:
    report = audit(ROOT)
    if (
        report["product"] != "AI1-M01"
        or report["cell_over_allocation_mm3"] != 221.248
        or report["concept_pack_over_allocation_mm3"] != 6001.4
        or report["public_charge_limit"] != "not_published_for_this_cell"
        or report["source_consistency"] != "pass"
        or report["integration_status"] != "blocked"
    ):
        raise ValueError("Current battery source or pack contradiction was lost")
    published = json.loads(
        (ROOT / "viewer/public/hardware-readiness.json").read_text(encoding="utf-8")
    )
    if published["battery_fit"] != report:
        raise ValueError("Published battery fit screen is stale")
    data = [
        load_yaml(ROOT / path)
        for path in (PROFILE, EVIDENCE, ENVELOPE, CONCEPT, PACK_ENVELOPE)
    ]
    altered = copy.deepcopy(data)
    altered[2]["placements"]["battery_reference"]["height_mm"] = 5.0
    if audit_data(*altered)["source_consistency"] != "fail":
        raise ValueError("Incorrect CAD cell dimensions passed")
    altered = copy.deepcopy(data)
    altered[1]["candidates"]["enovix_ai1_m01"]["charge_rate"] = "up_to_2c"
    if audit_data(*altered)["source_consistency"] != "fail":
        raise ValueError("Discharge limit was accepted as a charge rating")
    altered = copy.deepcopy(data)
    altered[0]["battery"]["physical_volume_mm3"] = 30000
    if audit_data(*altered)["source_consistency"] != "fail":
        raise ValueError("Conflicting pack allocations passed")
    altered = copy.deepcopy(data)
    altered[4]["charge_pressure"]["public_candidate_charge_limits"][
        "enovix_ai1_m01"
    ] = "2c"
    if audit_data(*altered)["source_consistency"] != "fail":
        raise ValueError("Pack study accepted a discharge limit as charge evidence")
    print("PASS: battery cell, pack allocation, and charge interpretation")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
