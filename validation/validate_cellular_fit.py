"""Check that the public 5G reference cannot be mistaken for a phone design."""

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from buildslate.cellular_fit import (  # noqa: E402
    CANDIDATE,
    FLOORPLAN,
    MEMORY_CANDIDATES,
    MEMORY_STUDY,
    audit,
    audit_data,
)
from buildslate.io import load_yaml  # noqa: E402


def main() -> int:
    report = audit(ROOT)
    if (
        report["status"] != "outline_blocked"
        or report["candidate"] != "RG255C-GL"
        or report["candidate_role"] != "public_reference_not_selected"
        or report["package_mm"] != [29.0, 32.0, 2.4]
        or report["board_outline_mm"] != [78.0, 55.0, 0.8]
        or report["voice"] != "optional_VoNR_and_VoLTE"
        or report["source_errors"]
        or any(side["outline_fits"] for side in report["sides"].values())
    ):
        raise ValueError("Current 5G reference board conflict was lost")
    published = json.loads(
        (ROOT / "viewer/public/hardware-readiness.json").read_text(encoding="utf-8")
    )
    if published["cellular_reference_fit"] != report:
        raise ValueError("Public 5G reference fit report is stale")
    inputs = [
        load_yaml(ROOT / path)
        for path in (CANDIDATE, MEMORY_CANDIDATES, FLOORPLAN, MEMORY_STUDY)
    ]
    wider = copy.deepcopy(inputs)
    wider[2]["board"]["outline_mm"]["length"] = 114.0
    wider[2]["board"]["outline_mm"]["width"] = 74.0
    wider[2]["board"]["component_side_boundary_mm"]["length"] = 110.0
    wider[2]["board"]["component_side_boundary_mm"]["width"] = 70.0
    recovered = audit_data(*wider)
    if (
        recovered["status"] != "outline_possible_unqualified"
        or not recovered["sides"]["reverse"]["outline_fits"]
    ):
        raise ValueError(
            "Synthetic board enlargement did not recover nominal outline fit"
        )
    bad_source = copy.deepcopy(inputs)
    bad_source[3]["metadata"]["reference_part"] = "unknown"
    if audit_data(*bad_source)["status"] != "source_conflict":
        raise ValueError("Mismatched memory package source was accepted")
    print("PASS: public 5G module outline conflict and recovery screen")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
