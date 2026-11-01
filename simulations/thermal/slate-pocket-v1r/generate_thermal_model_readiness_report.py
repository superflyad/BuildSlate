#!/usr/bin/env python3
"""Generate the Slate Pocket v1R thermal model and test readiness screen."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
PACKAGE_ROOT = REPO_ROOT / "simulations" / "thermal" / "slate-pocket-v1r"
MODEL_PATH = PACKAGE_ROOT / "model" / "model.yaml"
TEST_MATRIX_PATH = PACKAGE_ROOT / "test-matrix.yaml"
REPORT_PATH = REPO_ROOT / "reports" / "slate-pocket-v1r-thermal-model-readiness.txt"


def _load(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as input_file:
        data = yaml.safe_load(input_file)
    if not isinstance(data, dict):
        raise ValueError(f"{path.relative_to(REPO_ROOT)} must contain a mapping")
    return data


def _inside_enclosure(rectangle: dict[str, Any], length: float, width: float) -> bool:
    x = float(rectangle["x"])
    y = float(rectangle["y"])
    return x >= 0 and y >= 0 and x + float(rectangle["length"]) <= length and y + float(rectangle["width"]) <= width


def _count_nulls(value: Any) -> int:
    if value is None:
        return 1
    if isinstance(value, dict):
        return sum(_count_nulls(item) for item in value.values())
    if isinstance(value, list):
        return sum(_count_nulls(item) for item in value)
    return 0


def build_report() -> str:
    model = _load(MODEL_PATH)
    matrix = _load(TEST_MATRIX_PATH)
    enclosure = model["enclosure"]["external_mm"]
    length = float(enclosure["length"])
    width = float(enclosure["width"])
    sources = model["heat_sources"]
    outside_sources = [
        source_id
        for source_id, source in sources.items()
        if not _inside_enclosure(source["planform_mm"], length, width)
    ]
    unset_model_values = _count_nulls(model["material_regions"]) + _count_nulls(model["interfaces"]) + _count_nulls(
        model["boundary_conditions"]
    )

    cases = matrix["cases"]
    state_counts: dict[str, int] = {}
    for case in cases.values():
        state = case["state"]
        state_counts[state] = state_counts.get(state, 0) + 1
    categories = sorted({case["category"] for case in cases.values()})
    required_categories = {"sustained", "peak", "hot_ambient", "handheld", "pocket", "bag", "charging_overlap"}
    missing_categories = sorted(required_categories - set(categories))

    lines = [
        "Slate Pocket v1R Thermal Model and Test Readiness",
        "===================================================",
        "",
        "Geometry and source map:",
        f"  enclosure: {length:.1f} x {width:.1f} x {float(enclosure['thickness']):.1f} mm",
        f"  mapped heat sources: {len(sources)}",
        f"  mapped temperature sensors: {len(model['sensor_map'])}",
        f"  sources outside enclosure: {len(outside_sources)}",
        f"  unset material/interface/boundary values: {unset_model_values}",
        f"  solver status: {model['metadata']['solver_status']}",
    ]
    for source_id in outside_sources:
        lines.append(f"  - outside enclosure: {source_id}")

    lines.extend(
        [
            "",
            "Thermal source boundaries:",
            f"  compute target: {sources['compute_soc']['sustained_w']:.1f} W sustained / {sources['compute_soc']['peak_w']:.1f} W peak (not measured)",
            f"  128 GB memory estimate: {sources['memory_128gb_group']['sustained_w']:.1f} W sustained / {sources['memory_128gb_group']['peak_w']:.1f} W peak",
            "  wired charger losses: unset pending selected charger and measured loss map",
            "  wireless charger losses: unset; wireless disabled for EVT0",
            "",
            "Test matrix:",
            f"  total cases: {len(cases)}",
            f"  categories: {', '.join(categories)}",
            f"  missing required categories: {', '.join(missing_categories) if missing_categories else 'none'}",
        ]
    )
    for state, count in sorted(state_counts.items()):
        lines.append(f"  state {state}: {count}")

    lines.extend(
        [
            "",
            "Control gates:",
            f"  maximum skin screen: {matrix['screening_limits']['maximum_skin_c']:.1f} C",
            f"  skin caution: {matrix['screening_limits']['skin_caution_c']:.1f} C",
            f"  pre-supplier battery test abort: {matrix['screening_limits']['battery_test_abort_c']:.1f} C",
            "  pocket sustained AI: PROHIBITED_UNTIL_CONTROLS_VALIDATED",
            "  bag high-power operation: PROHIBITED_UNTIL_CONTROLS_VALIDATED",
            "  full-power charge plus sustained AI: PROHIBITED_UNTIL_VALIDATED",
            "  EVT0 wireless charging: DISABLED",
            "",
            "Correlation gates:",
            "  exterior steady-state target: +/-2 C by mapped sensor",
            "  internal steady-state target: +/-3 C where placement is controlled",
            "  time-to-40 C target: +/-15%",
            "  steady-state model energy imbalance target: below 3%",
            "  validation cases must remain separate from calibration cases",
            "",
            "THERMAL_MODEL_DECISION: BLOCKED_ON_TRACEABLE_PROPERTIES_SOLVER_BUILD_AND_INSTRUMENTED_HARDWARE",
            "",
            "Caveat:",
            "  This package defines a model and correlation program; it does not prove CFD/FEA completion, skin-temperature compliance, sustained performance, charging safety, or prototype readiness.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    try:
        report = build_report()
    except (KeyError, TypeError, ValueError) as exc:
        print(f"FAIL: {exc}")
        return 1
    REPORT_PATH.write_text(report, encoding="utf-8")
    print(f"Wrote {REPORT_PATH.relative_to(REPO_ROOT)}")
    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
