"""Verify a released STEP assembly against its controlled part geometry."""

from __future__ import annotations

import argparse
import hashlib
import json
from itertools import combinations
from pathlib import Path

from .io import load_yaml
from .program import DEFAULT_REPO_ROOT

ASSEMBLY = Path("engineering/hardware/released/mechanical/assembly.step")
MANIFEST = Path("engineering/hardware/released/mechanical/assembly.manifest.yaml")
REPORT = Path("viewer/public/mechanical-proof.json")
PROFILE = Path("configs/devices/slate-pocket-v1r.yaml")
REQUIRED_ROLES = (
    "enclosure_structure",
    "display_module",
    "cover_glass",
    "touch_digitizer",
    "main_pcb",
    "soc_package",
    "memory_packages",
    "storage_package",
    "battery_pack",
    "vapor_chamber",
    "graphite_spreader",
    "phase_change_material",
    "rear_camera_module",
    "front_camera_module",
    "antenna_modules",
    "speakers",
    "microphones",
    "haptics",
    "usb_c_port",
    "sensors",
    "tpm_or_security_chip",
    "fasteners_adhesives_gaskets",
)
BOUNDS_TOLERANCE_MM = 0.05
OVERLAP_THRESHOLD_MM3 = 0.01


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _controlled(root: Path, name: str) -> Path:
    base = (root / ASSEMBLY.parent).resolve()
    target = (root / name).resolve()
    if not target.is_relative_to(base) or not target.is_file():
        raise ValueError(f"Missing or uncontrolled mechanical source: {name}")
    return target


def _bounds(shape) -> list[float]:
    box = shape.BoundingBox()
    return [box.xmin, box.ymin, box.zmin, box.xmax, box.ymax, box.zmax]


def _dimensions(shape) -> list[float]:
    box = shape.BoundingBox()
    return [box.xlen, box.ylen, box.zlen]


def _signature_matches(first, second) -> bool:
    if abs(first.Volume() - second.Volume()) > max(0.01, first.Volume() * 1e-6):
        return False
    return all(
        abs(a - b) <= BOUNDS_TOLERANCE_MM
        for a, b in zip(_bounds(first), _bounds(second), strict=True)
    )


def audit(
    root: Path,
    *,
    required_roles: tuple[str, ...] = REQUIRED_ROLES,
    expected_envelope: tuple[float, float, float] | None = None,
) -> dict:
    """Audit released geometry; absence is a blocked state, never a pass."""
    import cadquery as cq

    root = root.resolve()
    assembly_path, manifest_path = root / ASSEMBLY, root / MANIFEST
    if not assembly_path.is_file() or not manifest_path.is_file():
        return {
            "schema_version": 1,
            "device": "slate-pocket-v1r",
            "status": "missing",
            "assembly_sha256": None,
            "manifest_sha256": None,
            "part_count": 0,
            "roles_covered": [],
            "findings": ["No released mechanical STEP assembly and manifest"],
            "caveat": "Concept CAD and supplier envelopes do not establish released fit.",
        }
    manifest = load_yaml(manifest_path)
    if (
        manifest.get("schema_version") != 1
        or manifest.get("device") != "slate-pocket-v1r"
    ):
        raise ValueError("Unknown released mechanical manifest")
    if manifest.get("units") != "mm":
        raise ValueError("Released mechanical dimensions must be millimeters")
    if manifest.get("assembly_frame") != "lower_left_rear_xyz_mm":
        raise ValueError("Released assembly coordinate frame is undefined")
    parts = manifest.get("parts")
    if not isinstance(parts, list) or not parts:
        raise ValueError("Released mechanical assembly has no parts")
    if len(parts) < len(required_roles):
        raise ValueError("Released mechanical assembly has too few distinct solids")
    ids = [part["id"] for part in parts]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate released mechanical part ID")
    covered = {role for part in parts for role in part["roles"]}
    if set(required_roles) - covered:
        raise ValueError(
            "Released mechanical role coverage incomplete: "
            + ", ".join(sorted(set(required_roles) - covered))
        )
    envelope = manifest.get("envelope_mm")
    if (
        not isinstance(envelope, list)
        or len(envelope) != 3
        or any(float(value) <= 0 for value in envelope)
    ):
        raise ValueError("Missing positive device envelope")
    if expected_envelope is None:
        geometry = load_yaml(root / PROFILE)["geometry"]
        expected_envelope = (
            float(geometry["length_mm"]),
            float(geometry["width_mm"]),
            float(geometry["thickness_mm"]),
        )
    if any(
        abs(float(actual) - expected) > 0.01
        for actual, expected in zip(envelope, expected_envelope, strict=True)
    ):
        raise ValueError(
            "Released assembly envelope differs from the active v1R profile"
        )
    min_clearance = float(manifest["minimum_clearance_mm"])
    contact_gap = float(manifest["maximum_contact_gap_mm"])
    if min_clearance < 0 or contact_gap < 0:
        raise ValueError("Clearance and contact limits must be nonnegative")
    contacts = [frozenset(pair) for pair in manifest.get("contact_pairs", [])]
    if len(contacts) != len(set(contacts)) or any(
        len(pair) != 2 or not pair.issubset(ids) for pair in contacts
    ):
        raise ValueError("Invalid or duplicate mechanical contact pair")
    assembled = {}
    part_reports = []
    findings = []
    for part in parts:
        part_id = part["id"]
        for field in (
            "manufacturer",
            "part_number",
            "revision",
            "source_frame",
            "geometry_license",
        ):
            if not isinstance(part.get(field), str) or not part[field].strip():
                raise ValueError(f"{part_id}: missing {field}")
        if part.get("distribution_scope") != "public":
            raise ValueError(f"{part_id}: public distribution rights are unconfirmed")
        source = _controlled(root, part["step"])
        drawing = _controlled(root, part["drawing"])
        if (
            _sha256(source) != part["step_sha256"]
            or _sha256(drawing) != part["drawing_sha256"]
        ):
            raise ValueError(f"{part_id}: STEP or drawing hash mismatch")
        solids = cq.importers.importStep(str(source)).solids().vals()
        if len(solids) != 1 or not solids[0].isValid() or solids[0].Volume() <= 0:
            raise ValueError(
                f"{part_id}: expected one valid positive-volume STEP solid"
            )
        source_shape = solids[0]
        declared = part["dimensions_mm"]
        if len(declared) != 3 or any(
            abs(actual - float(expected)) > BOUNDS_TOLERANCE_MM
            for actual, expected in zip(
                _dimensions(source_shape), declared, strict=True
            )
        ):
            raise ValueError(f"{part_id}: declared dimensions differ from STEP")
        translation = part["translation_mm"]
        rotation = part["rotation_deg"]
        if len(translation) != 3 or len(rotation) != 3:
            raise ValueError(f"{part_id}: incomplete placement transform")
        uncertainty = float(part["radial_uncertainty_mm"])
        if uncertainty < 0:
            raise ValueError(f"{part_id}: negative position or size uncertainty")
        shape = source_shape
        for axis, degrees in zip(
            ((1, 0, 0), (0, 1, 0), (0, 0, 1)), rotation, strict=True
        ):
            shape = shape.rotate((0, 0, 0), axis, float(degrees))
        shape = shape.translate(cq.Vector(*(float(value) for value in translation)))
        bounds = _bounds(shape)
        if any(bounds[axis] < -BOUNDS_TOLERANCE_MM for axis in range(3)) or any(
            bounds[axis + 3] > float(envelope[axis]) + BOUNDS_TOLERANCE_MM
            for axis in range(3)
        ):
            findings.append(f"{part_id}: placed shape leaves device envelope")
        assembled[part_id] = (shape, uncertainty)
        part_reports.append(
            {
                "id": part_id,
                "roles": part["roles"],
                "source_sha256": part["step_sha256"],
                "volume_mm3": round(shape.Volume(), 3),
                "bounds_mm": [round(value, 3) for value in bounds],
            }
        )
    enclosure_bounds = [
        item["bounds_mm"]
        for item in part_reports
        if "enclosure_structure" in item["roles"]
    ]
    if "enclosure_structure" in required_roles and (
        not enclosure_bounds
        or min(item[0] for item in enclosure_bounds) > BOUNDS_TOLERANCE_MM
        or min(item[1] for item in enclosure_bounds) > BOUNDS_TOLERANCE_MM
        or max(item[3] for item in enclosure_bounds)
        < float(envelope[0]) - BOUNDS_TOLERANCE_MM
        or max(item[4] for item in enclosure_bounds)
        < float(envelope[1]) - BOUNDS_TOLERANCE_MM
    ):
        findings.append("Enclosure structure does not span the active outer planform")
    released_solids = cq.importers.importStep(str(assembly_path)).solids().vals()
    unmatched = list(released_solids)
    if len(unmatched) != len(assembled):
        findings.append("Released assembly solid count differs from its part manifest")
    else:
        for part_id, (shape, _) in assembled.items():
            match = next(
                (item for item in unmatched if _signature_matches(shape, item)), None
            )
            if match is None:
                findings.append(
                    f"{part_id}: assembled STEP geometry or placement differs"
                )
            else:
                unmatched.remove(match)
    for (first_id, (first, first_tol)), (
        second_id,
        (second, second_tol),
    ) in combinations(assembled.items(), 2):
        pair = frozenset((first_id, second_id))
        overlap = first.intersect(second).Volume()
        if overlap > OVERLAP_THRESHOLD_MM3:
            findings.append(f"{first_id} / {second_id}: {overlap:.3f} mm3 penetration")
            continue
        distance = first.distance(second)
        if pair in contacts:
            if distance > contact_gap:
                findings.append(
                    f"{first_id} / {second_id}: declared contact gap {distance:.3f} mm"
                )
        elif distance + 1e-6 < first_tol + second_tol + min_clearance:
            findings.append(
                f"{first_id} / {second_id}: tolerance clearance {distance:.3f} mm"
            )
    return {
        "schema_version": 1,
        "device": "slate-pocket-v1r",
        "status": "pass" if not findings else "fail",
        "assembly_sha256": _sha256(assembly_path),
        "manifest_sha256": _sha256(manifest_path),
        "part_count": len(parts),
        "roles_covered": sorted(covered),
        "parts": part_reports,
        "findings": findings,
        "caveat": (
            "This checks source STEP identity, nominal assembly geometry, exact penetration, "
            "and conservative clearance allowances. It does not prove supplier tolerances, "
            "flex motion, material response, thermal expansion, assembly process, or physical fit."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=DEFAULT_REPO_ROOT)
    parser.add_argument(
        "--write", action="store_true", help="update public proof report"
    )
    parser.add_argument(
        "--require-release", action="store_true", help="fail unless proof passes"
    )
    args = parser.parse_args()
    report = audit(args.repo_root)
    serialized = json.dumps(report, indent=2) + "\n"
    if args.write:
        (args.repo_root / REPORT).write_text(serialized, encoding="utf-8")
    else:
        print(serialized, end="")
    return int(args.require_release and report["status"] != "pass")


if __name__ == "__main__":
    raise SystemExit(main())
