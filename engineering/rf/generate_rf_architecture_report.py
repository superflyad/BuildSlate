#!/usr/bin/env python3
"""Generate the provisional Slate Pocket v1R RF/wireless architecture report."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
MAP_PATH = REPO_ROOT / "engineering" / "rf" / "keepout-map" / "map.yaml"
REPORT_PATH = REPO_ROOT / "reports" / "slate-pocket-v1r-rf-wireless-architecture.txt"


def _load(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as input_file:
        data = yaml.safe_load(input_file)
    if not isinstance(data, dict):
        raise ValueError(f"{path.relative_to(REPO_ROOT)} must contain a mapping")
    return data


def _inside(rectangle: dict[str, Any], length: float, width: float) -> bool:
    x = float(rectangle["x"])
    y = float(rectangle["y"])
    return x >= 0 and y >= 0 and x + float(rectangle["length"]) <= length and y + float(rectangle["width"]) <= width


def build_report() -> str:
    keepout_map = _load(MAP_PATH)
    device = keepout_map["device_mm"]
    length = float(device["length"])
    width = float(device["width"])
    reservations = keepout_map["antenna_reservations"]
    outside = [
        reservation_id
        for reservation_id, reservation in reservations.items()
        if not _inside(reservation["rectangle_mm"], length, width)
    ]
    wireless = keepout_map["wireless_power_reservation"]

    lines = [
        "Slate Pocket v1R Provisional RF and Wireless Architecture",
        "===========================================================",
        "",
        "Radio posture:",
        "  Wi-Fi 7 / Bluetooth 6: modular EVT0 development path; exact bands and features unset",
        "  UWB 2.0: reserved option, disabled unless a qualified module and use case are approved",
        "  optional 5G: deferred from EVT0 pending market, operator, band, module, antenna, and certification scope",
        "  exact band matrix: UNSET_BY_DESIGN",
        "",
        "Antenna reservation screen:",
        f"  device envelope: {length:.1f} x {width:.1f} x {float(device['thickness']):.1f} mm",
        f"  perimeter reservation count: {len(reservations)}",
        f"  reservations outside envelope: {len(outside)}",
        "  reservation status: planning space only; no tuned antenna geometry",
    ]
    for reservation_id in outside:
        lines.append(f"  - outside envelope: {reservation_id}")

    lines.extend(
        [
            "",
            "Wireless-power decision:",
            f"  reserved coil area: {wireless['rectangle_mm']['length']:.1f} x {wireless['rectangle_mm']['width']:.1f} mm",
            f"  planning stack height: {wireless['stack_height_mm']:.2f} mm",
            f"  EVT0 state: {wireless['evt0_state'].upper()}",
            "  mechanical result: 9.84 mm local stack, 0.34 mm over the 9.5 mm envelope",
            "  public standards evidence: WPC publicly lists Qi2 25W; no 50 W certification route is established here",
            "  50 W product claim: UNSUPPORTED",
            "",
            "Compliance scoping anchors:",
            "  - FCC equipment authorization and final-configuration RF-exposure evaluation for United States variants.",
            "  - EU Radio Equipment Directive and project-current harmonized standards for European Union variants.",
            "  - PTCRB and operator testing if cellular returns.",
            "  - WPC authorized-lab certification and registration if wireless charging returns.",
            "  - Exact editions, limits, markets, and reductions require accredited-lab and regulatory review.",
            "",
            "Validation branches:",
            "  - Full-device EM and tolerance model with hands, body, accessories, cables, thermal conductors, and housing.",
            "  - Conducted, antenna, OTA, coexistence, EMC pre-compliance, and final RF-exposure/SAR work.",
            "  - Wireless-power loss, alignment, foreign-object, thermal, desense, and interoperability work only after re-entry gates pass.",
            "",
            "RF_WIRELESS_DECISION: EVT0_MODULAR_RADIOS_WIRELESS_CHARGING_REMOVED_CELLULAR_DEFERRED",
            "",
            "Caveat:",
            "  This package reserves architecture space; it does not prove RF performance, coexistence, SAR/RF-exposure compliance, EMC compliance, wireless-power safety, certification, or production readiness.",
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
