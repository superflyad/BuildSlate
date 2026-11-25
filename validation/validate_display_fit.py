"""Keep the display target's active-area conflict visible and fail closed."""

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from buildslate.display_fit import (  # noqa: E402
    ASSEMBLY,
    CANDIDATES,
    DRAWING_CANDIDATE,
    ENVELOPE,
    PROFILE,
    audit,
    audit_data,
)
from buildslate.io import load_yaml  # noqa: E402


def main() -> int:
    report = audit(ROOT)
    if (
        report["status"] != "blocked"
        or report["target_active_mm"] != [161.544, 100.965]
        or report["short_side_overrun_mm"]
        != {"device_face": 5.965, "cad_reserve": 11.965}
        or report["maximum_diagonal_in_at_target_aspect"]
        != {"device_face": 7.057, "cad_reserve": 6.611}
        or report["resolution_aspect_ratio"] != "16:9"
        or report["target_aspect_ratio"] != "16:10"
        or report["device_face_fit"]
        or report["cad_reserve_fit"]
        or report["source_consistency"] != "pass"
        or report["drawing_candidate"]["status"] != "rejected"
        or report["drawing_candidate"]["pixel_aspect_ratio"] != "16:9"
        or report["drawing_candidate"]["target_format_match"]
        or report["drawing_candidate"]["nominal_panel_reserve_fit"]
        or not report["drawing_candidate"]["nominal_panel_face_fit"]
        or report["drawing_candidate"]["nominal_short_side_reserve_overrun_mm"]
        != 0.1344
    ):
        raise ValueError("Current display target conflict was lost")
    published = json.loads(
        (ROOT / "viewer/public/hardware-readiness.json").read_text(encoding="utf-8")
    )
    if published["display_fit"] != report or published["design_release"] != "blocked":
        raise ValueError("Public display geometry gate is stale or misleading")
    profile = load_yaml(ROOT / PROFILE)
    spec = load_yaml(ROOT / profile["identity"]["source_spec"])
    envelope = load_yaml(ROOT / ENVELOPE)
    assembly = load_yaml(ROOT / ASSEMBLY)
    candidates = load_yaml(ROOT / CANDIDATES)
    candidate = candidates["display_candidates"][DRAWING_CANDIDATE]
    if candidate["panel_outline_mm"] != [160.9056, 89.1344, 1.028]:
        raise ValueError("Published panel outline changed without drawing review")
    if candidate["source"]["revision"] != "A0" or candidate["source"]["sha256"] != (
        "a60b9b3d9caf2e8d0f2a5841c267911095f850a2af80c728fab11d576b7c7b83"
    ):
        raise ValueError("Display drawing provenance changed without review")
    fallback = copy.deepcopy(profile)
    fallback["display"]["diagonal_in"] = 7.0
    fallback["display"]["resolution"] = "3200x2000"
    fallback["geometry"]["display_diagonal_in"] = 7.0
    if audit_data(fallback, spec, envelope, assembly)["cad_reserve_fit"]:
        raise ValueError("Seven-inch 16:10 panel falsely fits current reserve")
    wider = copy.deepcopy(profile)
    wider_envelope = copy.deepcopy(envelope)
    wider_assembly = copy.deepcopy(assembly)
    wider["geometry"]["width_mm"] = 107.0
    wider["display"]["resolution"] = "3200x2000"
    wider_envelope["device"]["external_mm"]["width"] = 107.0
    wider_envelope["device"]["internal_boundary_mm"]["width"] = 101.0
    wider_assembly["parts"]["enclosure"]["display_stack"]["box_mm"][4] = 101.0
    recovered = audit_data(wider, spec, wider_envelope, wider_assembly)
    if recovered["status"] != "pass" or not recovered["cad_reserve_fit"]:
        raise ValueError(
            "Explicit width and resolution recovery did not clear geometry"
        )
    del wider["display"]["resolution"]
    if audit_data(wider, spec, wider_envelope, wider_assembly)["status"] != "blocked":
        raise ValueError("Original source resolution mismatch was silently accepted")
    mismatched = copy.deepcopy(assembly)
    mismatched["parts"]["enclosure"]["display_stack"]["box_mm"][4] = 90.0
    if audit_data(profile, spec, envelope, mismatched)["source_consistency"] != "fail":
        raise ValueError("CAD reserve and envelope disagreement was accepted")
    bad_candidate = copy.deepcopy(candidates)
    bad_candidate["display_candidates"][DRAWING_CANDIDATE]["active_area_mm"][1] = 90.0
    try:
        audit_data(profile, spec, envelope, assembly, bad_candidate)
    except ValueError:
        pass
    else:
        raise ValueError("Candidate active area larger than outline was accepted")
    print("PASS: display target conflict, drawing candidate, and recovery screen")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
