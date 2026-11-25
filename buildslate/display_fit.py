"""Screen the approved display rectangle against the device and CAD reserve."""

from __future__ import annotations

import argparse
import json
import math
import re
from pathlib import Path

from buildslate.io import load_yaml

PROFILE = Path("configs/devices/slate-pocket-v1r.yaml")
ENVELOPE = Path("cad/slate-pocket-v1r/envelope-model/envelope.yaml")
ASSEMBLY = Path("engineering/assembly/assembly.yaml")
CANDIDATES = Path("research/evidence/display-storage/candidate-comparison.yaml")
RESOLUTION = re.compile(r"^([1-9][0-9]*)x([1-9][0-9]*)$")
DRAWING_CANDIDATE = "hongguang_hg070fh002"


def _rectangle(
    diagonal_in: float, aspect_width: float, aspect_height: float
) -> tuple[float, float]:
    diagonal_mm = diagonal_in * 25.4
    aspect_diagonal = math.hypot(aspect_width, aspect_height)
    return (
        diagonal_mm * aspect_width / aspect_diagonal,
        diagonal_mm * aspect_height / aspect_diagonal,
    )


def _maximum_diagonal(
    length_mm: float, width_mm: float, aspect_width: float, aspect_height: float
) -> float:
    aspect_diagonal = math.hypot(aspect_width, aspect_height)
    return (
        min(
            length_mm * aspect_diagonal / aspect_width,
            width_mm * aspect_diagonal / aspect_height,
        )
        / 25.4
    )


def _screen_drawing_candidate(
    candidate: dict, display: dict, external: dict, reserve: list, internal: dict
) -> dict:
    """Compare a published panel outline, without assuming the flex envelope fits."""
    active = [float(value) for value in candidate["active_area_mm"]]
    outline = [float(value) for value in candidate["panel_outline_mm"]]
    if (
        len(active) != 2
        or len(outline) != 3
        or min(active + outline) <= 0
        or active[0] > outline[0]
        or active[1] > outline[1]
    ):
        raise ValueError("Display candidate has an invalid panel outline")
    match = RESOLUTION.fullmatch(str(candidate["resolution"]))
    if not match:
        raise ValueError("Display candidate resolution must be WIDTHxHEIGHT")
    pixels = sorted((int(match[1]), int(match[2])), reverse=True)
    divisor = math.gcd(*pixels)
    aspect = (pixels[0] // divisor, pixels[1] // divisor)
    target_aspect = float(display["aspect_width"]) / float(display["aspect_height"])
    format_match = math.isclose(
        float(candidate["diagonal_in"]), float(display["diagonal_in"]), abs_tol=1e-6
    ) and math.isclose(pixels[0] / pixels[1], target_aspect, rel_tol=1e-6)
    face_fit = outline[0] <= float(external["length"]) and outline[1] <= float(
        external["width"]
    )
    reserve_fit = outline[0] <= float(reserve[3]) and outline[1] <= float(reserve[4])
    errors = []
    if not format_match:
        errors.append(
            "Published diagonal and pixel ratio differ from the approved target"
        )
    if not face_fit:
        errors.append("Published panel outline exceeds the device face")
    if not reserve_fit:
        errors.append("Published panel outline exceeds the CAD display reserve")
    return {
        "part_number": candidate["part_number"],
        "supplier": candidate["supplier"],
        "status": "rejected" if errors else "unqualified",
        "errors": errors,
        "diagonal_in": float(candidate["diagonal_in"]),
        "resolution_px": [int(match[1]), int(match[2])],
        "pixel_aspect_ratio": f"{aspect[0]}:{aspect[1]}",
        "active_area_mm": active,
        "panel_outline_mm": outline,
        "outline_includes": candidate["outline_includes"],
        "target_format_match": format_match,
        "nominal_panel_face_fit": face_fit,
        "nominal_panel_reserve_fit": reserve_fit,
        "nominal_short_side_reserve_overrun_mm": round(
            max(0.0, outline[1] - float(reserve[4])), 4
        ),
        "minimum_device_width_mm_with_current_side_inset": round(
            outline[1] + float(external["width"]) - float(internal["width"]), 4
        ),
        "document_status": candidate["document_status"],
        "drawing_status": candidate["drawing_status"],
        "source": candidate["source"]["url"],
        "source_revision": candidate["source"]["revision"],
        "source_sha256": candidate["source"]["sha256"],
        "caveat": "The published panel outline excludes unverified flex routing, integration allowances, and tolerance stack; the A0 document is preliminary.",
    }


def audit_data(
    profile: dict,
    source_spec: dict,
    envelope: dict,
    assembly: dict,
    candidates: dict | None = None,
) -> dict:
    """Return exact active-area limits without assuming a supplier module border."""
    display = profile["display"]
    device = profile["geometry"]
    external = envelope["device"]["external_mm"]
    internal = envelope["device"]["internal_boundary_mm"]
    reserve = assembly["parts"]["enclosure"]["display_stack"]["box_mm"]
    diagonal = float(display["diagonal_in"])
    aspect_width = float(display["aspect_width"])
    aspect_height = float(display["aspect_height"])
    if min(diagonal, aspect_width, aspect_height) <= 0:
        raise ValueError("Display diagonal and aspect terms must be positive")
    match = RESOLUTION.fullmatch(
        str(display.get("resolution", source_spec["display"]["resolution"]))
    )
    if not match:
        raise ValueError("Display resolution must be WIDTHxHEIGHT")
    pixels = (int(match[1]), int(match[2]))
    divisor = math.gcd(*pixels)
    resolution_aspect = (pixels[0] // divisor, pixels[1] // divisor)
    selected_resolution_source = (
        "v1r_profile" if "resolution" in display else "source_spec"
    )
    active_length, active_width = _rectangle(diagonal, aspect_width, aspect_height)
    external_length = float(external["length"])
    external_width = float(external["width"])
    reserve_length = float(reserve[3])
    reserve_width = float(reserve[4])
    external_fit = active_length <= external_length and active_width <= external_width
    reserve_fit = active_length <= reserve_length and active_width <= reserve_width
    source_errors: list[str] = []
    if not math.isclose(
        float(device["length_mm"]), external_length, abs_tol=1e-6
    ) or not math.isclose(float(device["width_mm"]), external_width, abs_tol=1e-6):
        source_errors.append("Profile device face differs from CAD external envelope")
    if not all(
        math.isclose(float(reserve[index]), float(internal[key]), abs_tol=1e-6)
        for index, key in ((0, "x"), (1, "y"), (3, "length"), (4, "width"))
    ):
        source_errors.append("CAD display reserve differs from internal boundary")
    if not math.isclose(float(device["display_diagonal_in"]), diagonal, abs_tol=1e-6):
        source_errors.append("Profile display diagonal is inconsistent")
    errors = list(source_errors)
    if not external_fit:
        errors.append("Target active display rectangle exceeds the device face")
    if not reserve_fit:
        errors.append("Target active display rectangle exceeds the CAD display reserve")
    if not math.isclose(
        pixels[0] / pixels[1], aspect_width / aspect_height, rel_tol=1e-6
    ):
        errors.append("Declared display aspect ratio differs from resolution")
    internal_maximum = _maximum_diagonal(
        float(internal["length"]), float(internal["width"]), aspect_width, aspect_height
    )
    external_maximum = _maximum_diagonal(
        external_length, external_width, aspect_width, aspect_height
    )
    report = {
        "status": "pass" if not errors else "blocked",
        "errors": errors,
        "target_diagonal_in": diagonal,
        "target_aspect_ratio": f"{aspect_width:g}:{aspect_height:g}",
        "target_active_mm": [round(active_length, 3), round(active_width, 3)],
        "device_face_mm": [external_length, external_width],
        "cad_display_reserve_mm": [reserve_length, reserve_width],
        "device_face_fit": external_fit,
        "cad_reserve_fit": reserve_fit,
        "short_side_overrun_mm": {
            "device_face": round(max(0.0, active_width - external_width), 3),
            "cad_reserve": round(max(0.0, active_width - reserve_width), 3),
        },
        "maximum_diagonal_in_at_target_aspect": {
            "device_face": round(external_maximum, 3),
            "cad_reserve": round(internal_maximum, 3),
        },
        "minimum_device_width_mm_with_current_side_inset": round(
            active_width + external_width - float(internal["width"]), 3
        ),
        "resolution_px": list(pixels),
        "resolution_aspect_ratio": f"{resolution_aspect[0]}:{resolution_aspect[1]}",
        "resolution_source": selected_resolution_source,
        "source_spec_aspect_ratio": source_spec["display"]["aspect_ratio"],
        "source_consistency": "pass" if not source_errors else "fail",
        "source_errors": source_errors,
        "caveat": "Active pixels are a lower bound on module size. Bezel, driver, flex, bonding, corner, and tolerance allowances would need additional space.",
        "sources": [PROFILE.as_posix(), ENVELOPE.as_posix(), ASSEMBLY.as_posix()],
    }
    if candidates is not None:
        report["drawing_candidate"] = _screen_drawing_candidate(
            candidates["display_candidates"][DRAWING_CANDIDATE],
            display,
            external,
            reserve,
            internal,
        )
        report["sources"].append(CANDIDATES.as_posix())
    return report


def audit(root: Path) -> dict:
    profile = load_yaml(root / PROFILE)
    source_spec = load_yaml(root / profile["identity"]["source_spec"])
    envelope = load_yaml(root / ENVELOPE)
    assembly = load_yaml(root / ASSEMBLY)
    candidates = load_yaml(root / CANDIDATES)
    return audit_data(profile, source_spec, envelope, assembly, candidates)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo-root", type=Path, default=Path(__file__).resolve().parents[1]
    )
    args = parser.parse_args()
    print(json.dumps(audit(args.repo_root), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
