"""Audit a geometry-bound thermal release and its raw solver result table.

This verifies release integrity and numerical consistency, not solver fidelity or
physical temperature. Supplier limits and measured correlation remain separate.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path

from buildslate.io import load_yaml
from buildslate.power_safety_proof import RELEASE as POWER_RELEASE
from buildslate.power_safety_proof import audit as audit_power

RELEASE = Path("engineering/hardware/released/thermal/thermal-release.json")
MODEL = Path("engineering/hardware/released/thermal/solver-input.json")
RESULTS = Path("engineering/hardware/released/thermal/solver-results.csv")
ASSEMBLY = Path("engineering/hardware/released/mechanical/assembly.step")
MANIFEST = Path("engineering/hardware/released/mechanical/assembly.manifest.yaml")
BOARD = Path("engineering/hardware/released/board.kicad_pcb")
SELECTED_BOM = Path("engineering/hardware/released/selected-bom.json")
PROFILE = Path("configs/devices/slate-pocket-v1r.yaml")
CASES = {
    "T02_sustained_ai_open_air_25c": (25.0, "sustained", False),
    "T03_peak_ai_burst_25c": (25.0, "peak", False),
    "T04_sustained_ai_hot_ambient_35c": (35.0, "sustained", False),
    "T05_handheld_sustained_ramp": (25.0, "sustained", False),
    "T08_wired_charge_evt0_cap": (25.0, "charge", True),
}
BOUNDARIES = {
    "T02_sustained_ai_open_air_25c": "open_air_25c",
    "T03_peak_ai_burst_25c": "open_air_25c",
    "T04_sustained_ai_hot_ambient_35c": "open_air_35c",
    "T05_handheld_sustained_ramp": "handheld_25c",
    "T08_wired_charge_evt0_cap": "charging_open_air_25c",
}
LOAD_GEOMETRY = {
    "compute_platform": ("soc_package",),
    "memory_128gb": ("memory_packages",),
    "storage_1tb": ("storage_package",),
    "display": ("display_module",),
    "radios": ("main_pcb", "antenna_modules"),
    "cameras": ("rear_camera_module", "front_camera_module"),
    "system_io_and_controls": (
        "main_pcb",
        "usb_c_port",
        "speakers",
        "haptics",
        "sensors",
    ),
}
MATERIALS = (
    "enclosure_structure",
    "display_module",
    "battery_pack",
    "vapor_chamber",
    "graphite_spreader",
    "phase_change_material",
)
INTERFACES = (
    "soc_to_tim",
    "tim_to_spreader",
    "spreader_to_frame",
    "battery_to_structure",
    "rear_cover_bond",
)
RESULT_FIELDS = (
    "case",
    "mesh",
    "simulated_duration_s",
    "ambient_c",
    "input_heat_w",
    "outbound_heat_w",
    "max_skin_c",
    "max_battery_c",
    "max_junction_c",
)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _number(value: object) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _positive(value: object) -> bool:
    return _number(value) and value > 0


def _text(value: object) -> bool:
    return (
        isinstance(value, str)
        and bool(value.strip())
        and value.strip().lower()
        not in {
            "unknown",
            "placeholder",
            "tbd",
        }
    )


def _result_table(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8-sig", newline="") as source:
        reader = csv.DictReader(source)
        if not reader.fieldnames or set(reader.fieldnames) != set(RESULT_FIELDS):
            raise ValueError("Thermal results need the exact documented columns")
        rows: list[dict] = []
        for row in reader:
            item = {key: row[key] for key in RESULT_FIELDS}
            for key in RESULT_FIELDS[2:]:
                item[key] = float(item[key])
                if not _number(item[key]):
                    raise ValueError("Thermal result has a nonfinite number")
            rows.append(item)
        return rows


def _source(root: Path, item: dict) -> bool:
    name = item.get("evidence_path")
    digest = item.get("evidence_sha256")
    if not _text(name) or not _text(digest):
        return False
    source = (root / name).resolve()
    allowed = tuple(
        (root / path).resolve()
        for path in (
            "engineering/hardware/released/thermal/sources",
            "engineering/hardware/released/parts",
        )
    )
    return (
        any(source.is_relative_to(directory) for directory in allowed)
        and source.is_file()
        and source.suffix.lower() not in {".json", ".yaml", ".yml", ".md"}
        and _sha(source) == digest
    )


def audit(root: Path) -> dict:
    """Require controlled model inputs and a complete, limit-bound case table."""
    release_path = root / RELEASE
    if not release_path.is_file():
        return {"status": "missing", "errors": ["No released thermal design"]}
    upstream = {
        "mechanical_assembly_sha256": root / ASSEMBLY,
        "mechanical_manifest_sha256": root / MANIFEST,
        "routed_pcb_sha256": root / BOARD,
        "power_safety_sha256": root / POWER_RELEASE,
        "selected_bom_sha256": root / SELECTED_BOM,
        "solver_input_sha256": root / MODEL,
        "solver_results_sha256": root / RESULTS,
    }
    missing = [name for name, path in upstream.items() if not path.is_file()]
    if missing:
        return {
            "status": "fail",
            "errors": [f"Missing thermal source: {name}" for name in missing],
        }
    try:
        release = json.loads(release_path.read_text(encoding="utf-8"))
        model = json.loads((root / MODEL).read_text(encoding="utf-8"))
        selected = json.loads((root / SELECTED_BOM).read_text(encoding="utf-8"))
        power = json.loads((root / POWER_RELEASE).read_text(encoding="utf-8"))
        profile = load_yaml(root / PROFILE)
        manifest = load_yaml(root / MANIFEST)
        rows = _result_table(root / RESULTS)
    except (
        OSError,
        UnicodeError,
        json.JSONDecodeError,
        ValueError,
        TypeError,
    ) as error:
        return {"status": "fail", "errors": [f"Thermal source cannot be read: {error}"]}
    if not all(
        isinstance(item, dict) for item in (release, model, selected, power, manifest)
    ):
        return {"status": "fail", "errors": ["Thermal release inputs must be objects"]}
    errors: list[str] = []
    if (
        release.get("schema_version") != 1
        or release.get("device") != "slate-pocket-v1r"
    ):
        errors.append("Unknown thermal release schema or device")
    for field in ("revision", "reviewed_by", "solver_name", "solver_version"):
        if not _text(release.get(field)):
            errors.append(f"Missing thermal release {field}")
    for field, source in upstream.items():
        if release.get(field) != _sha(source):
            errors.append(f"Thermal release is not bound to {field}")
    power_result = audit_power(root)
    if power_result["status"] != "pass":
        return {
            "status": "fail",
            "errors": errors
            + ["Referenced power design does not pass its release audit"],
        }
    if not isinstance(manifest.get("parts"), list):
        return {
            "status": "fail",
            "errors": errors + ["Released mechanical manifest has no part list"],
        }
    geometry_roles = {
        role
        for part in manifest.get("parts", [])
        if isinstance(part, dict) and isinstance(part.get("roles"), list)
        for role in part["roles"]
        if _text(role)
    }
    if not geometry_roles or not set(MATERIALS).issubset(geometry_roles):
        errors.append("Released mechanical roles do not cover thermal materials")
    parts = selected.get("parts")
    battery = parts.get("battery_pack") if isinstance(parts, dict) else None
    compute = parts.get("compute_platform") if isinstance(parts, dict) else None
    if not isinstance(battery, dict) or not isinstance(compute, dict):
        return {
            "status": "fail",
            "errors": errors + ["Selected battery and compute are missing"],
        }
    battery_caps = battery.get("capabilities")
    compute_caps = compute.get("capabilities")
    if not isinstance(battery_caps, dict) or not isinstance(compute_caps, dict):
        return {
            "status": "fail",
            "errors": errors + ["Selected thermal limits are missing"],
        }
    battery_max = battery_caps.get("maximum_operating_temperature_c")
    charge_max = battery_caps.get("charge_temperature_max_c")
    junction_max = compute_caps.get("maximum_junction_temperature_c")
    if not all(_positive(value) for value in (battery_max, charge_max, junction_max)):
        return {
            "status": "fail",
            "errors": errors + ["Supplier thermal limits are incomplete"],
        }
    if charge_max > battery_max:
        errors.append("Battery charge temperature exceeds operating limit")
    if power.get("selected_bom_sha256") != release.get(
        "selected_bom_sha256"
    ) or power.get("routed_pcb_sha256") != release.get("routed_pcb_sha256"):
        errors.append("Thermal and power releases use different hardware")
    if model.get("schema_version") != 1 or model.get("device") != "slate-pocket-v1r":
        errors.append("Unknown thermal solver input schema or device")
    if model.get("mechanical_assembly_sha256") != release.get(
        "mechanical_assembly_sha256"
    ):
        errors.append("Solver input is not bound to released geometry")
    if model.get("power_safety_sha256") != release.get("power_safety_sha256"):
        errors.append("Solver input is not bound to released power design")
    materials = model.get("materials")
    if not isinstance(materials, dict) or set(materials) != set(MATERIALS):
        materials = {}
        errors.append("Thermal material map is incomplete")
    for role in MATERIALS:
        material = materials.get(role)
        if (
            not isinstance(material, dict)
            or any(
                not _positive(material.get(field))
                for field in (
                    "conductivity_x_w_mk",
                    "conductivity_y_w_mk",
                    "conductivity_z_w_mk",
                    "density_kg_m3",
                    "heat_capacity_j_kgk",
                )
            )
            or not _source(root, material)
        ):
            errors.append(f"Material properties or source are incomplete: {role}")
    battery_loss = model.get("battery_internal_loss")
    if (
        not isinstance(battery_loss, dict)
        or not _positive(battery_loss.get("resistance_ohm"))
        or not _source(root, battery_loss)
    ):
        errors.append("Battery resistance and source are incomplete")
        battery_resistance = 0.0
    else:
        battery_resistance = battery_loss["resistance_ohm"]
    interfaces = model.get("interfaces")
    if not isinstance(interfaces, dict) or set(interfaces) != set(INTERFACES):
        interfaces = {}
        errors.append("Thermal interface map is incomplete")
    for name in INTERFACES:
        item = interfaces.get(name)
        if (
            not isinstance(item, dict)
            or not _positive(item.get("resistance_m2k_w"))
            or not _positive(item.get("bondline_mm"))
            or not _source(root, item)
        ):
            errors.append(f"Thermal interface is incomplete: {name}")
    boundaries = model.get("boundary_conditions")
    if not isinstance(boundaries, dict) or set(boundaries) != set(BOUNDARIES.values()):
        boundaries = {}
        errors.append("Thermal boundary condition coverage is incomplete")
    for name in set(BOUNDARIES.values()):
        boundary = boundaries.get(name)
        if (
            not isinstance(boundary, dict)
            or not _positive(boundary.get("convection_w_m2k"))
            or not _number(boundary.get("emissivity"))
            or not 0 < boundary["emissivity"] <= 1
            or not _source(root, boundary)
        ):
            errors.append(f"Thermal boundary is incomplete: {name}")
        if name == "handheld_25c" and (
            not isinstance(boundary, dict)
            or not _positive(boundary.get("contact_area_mm2"))
            or not _positive(boundary.get("contact_conductance_w_m2k"))
        ):
            errors.append("Handheld boundary has no contact model")
    meshes = model.get("meshes")
    if (
        not isinstance(meshes, dict)
        or set(meshes) != {"medium", "fine"}
        or not all(
            isinstance(meshes.get(name), dict)
            and isinstance(meshes[name].get("cells"), int)
            and meshes[name]["cells"] > 0
            for name in ("medium", "fine")
        )
        or meshes["fine"]["cells"] < meshes["medium"]["cells"] * 1.5
    ):
        errors.append("Thermal mesh refinement is incomplete")
    case_inputs = model.get("cases")
    if not isinstance(case_inputs, dict) or set(case_inputs) != set(CASES):
        case_inputs = {}
        errors.append("Thermal model case coverage is incomplete")
    power_loads = power.get("loads")
    loads = (
        {
            item["id"]: item
            for item in power_loads
            if isinstance(item, dict) and _text(item.get("id"))
        }
        if isinstance(power_loads, list)
        else {}
    )
    by_case: dict[str, dict[str, dict]] = {}
    for row in rows:
        case = row["case"]
        mesh = row["mesh"]
        if (
            case not in CASES
            or mesh not in ("medium", "fine")
            or mesh in by_case.get(case, {})
        ):
            errors.append("Thermal results contain an unknown or duplicate case mesh")
            continue
        by_case.setdefault(case, {})[mesh] = row
    skin_limit = profile["thermal"]["max_skin_c"]
    for case, (ambient, load_column, charging) in CASES.items():
        declared = case_inputs.get(case)
        results = by_case.get(case, {})
        if not isinstance(declared, dict) or set(results) != {"medium", "fine"}:
            errors.append(f"Thermal case input or mesh results are incomplete: {case}")
            continue
        sources = declared.get("sources")
        if not isinstance(sources, dict) or set(sources) != set(loads):
            errors.append(f"Thermal heat source map is incomplete: {case}")
            continue
        heat = 0.0
        charge_load_w = 0.0
        for role, source in sources.items():
            if not isinstance(source, dict) or not _number(source.get("exported_w")):
                errors.append(f"Thermal heat source is incomplete: {case}/{role}")
                continue
            deposits = source.get("heat_deposits")
            if not isinstance(deposits, list) or not deposits:
                errors.append(f"Thermal heat deposits are incomplete: {case}/{role}")
                continue
            deposit_roles: list[str] = []
            deposit_heat = 0.0
            for deposit in deposits:
                if (
                    not isinstance(deposit, dict)
                    or not _text(deposit.get("geometry_role"))
                    or deposit["geometry_role"] not in LOAD_GEOMETRY.get(role, ())
                    or deposit["geometry_role"] not in geometry_roles
                    or not _number(deposit.get("heat_w"))
                    or deposit["heat_w"] < 0
                ):
                    errors.append(f"Thermal heat location is invalid: {case}/{role}")
                    continue
                deposit_roles.append(deposit["geometry_role"])
                deposit_heat += deposit["heat_w"]
            if len(deposit_roles) != len(set(deposit_roles)) or (
                role == "cameras"
                and set(deposit_roles) != set(LOAD_GEOMETRY["cameras"])
            ):
                errors.append(
                    f"Thermal heat location coverage is invalid: {case}/{role}"
                )
            available = loads[role][
                "peak_w" if load_column == "peak" else "continuous_w"
            ]
            used = deposit_heat + source["exported_w"]
            if (
                source["exported_w"] < 0
                or (charging and used > available)
                or (not charging and abs(used - available) > 0.01)
            ):
                errors.append(
                    f"Thermal source energy does not match power release: {case}/{role}"
                )
            if source["exported_w"] > 0 and not _source(root, source):
                errors.append(
                    f"Exported thermal energy lacks source evidence: {case}/{role}"
                )
            charge_load_w += used
            heat += deposit_heat
        battery_current_a = (
            power["limits"]["charge_current_limit_a"]
            if charging
            else power_result[
                "peak_battery_current_a"
                if load_column == "peak"
                else "continuous_battery_current_a"
            ]
        )
        expected_battery_heat = battery_current_a**2 * battery_resistance
        if (
            not _number(declared.get("battery_heat_w"))
            or abs(declared["battery_heat_w"] - expected_battery_heat) > 0.02
            or declared.get("battery_geometry_role") != "battery_pack"
        ):
            errors.append(f"Battery internal heat is incomplete: {case}")
        else:
            heat += declared["battery_heat_w"]
        if charging:
            if charge_load_w > power["limits"]["idle_system_w"] + 0.01:
                errors.append("Charge-case system loads exceed approved idle draw")
            charger_heat = declared.get("charger_heat_w")
            if (
                declared.get("charger_geometry_role") != "main_pcb"
                or "main_pcb" not in geometry_roles
            ):
                errors.append("Charge heat is not located on the released board")
            if not _positive(charger_heat):
                errors.append(f"Charge loss heat is missing: {case}")
            else:
                charge_output_w = (
                    power["limits"]["charge_current_limit_a"]
                    * power["limits"]["normal_charge_termination_v"]
                )
                expected_loss_w = charge_output_w * (
                    1 / power["limits"]["charge_path_efficiency"] - 1
                )
                if abs(charger_heat - expected_loss_w) > 0.01:
                    errors.append("Charge-case heat differs from approved path loss")
                heat += charger_heat
        elif declared.get("charger_heat_w") != 0:
            errors.append(f"Charging heat is unexpected: {case}")
        if declared.get("ambient_c") != ambient:
            errors.append(f"Thermal ambient differs from test matrix: {case}")
        if declared.get("boundary_id") != BOUNDARIES[case]:
            errors.append(f"Thermal case uses the wrong boundary: {case}")
        if case == "T03_peak_ai_burst_25c" and declared.get("duration_s") != 60:
            errors.append("Peak burst must cover the 60 second test window")
        for row in results.values():
            if (
                row["simulated_duration_s"] < 60
                if case == "T03_peak_ai_burst_25c"
                else row["simulated_duration_s"] != 0
            ):
                errors.append(f"Solver result duration is invalid: {case}")
            if row["input_heat_w"] < 0 or row["outbound_heat_w"] < 0:
                errors.append(f"Solver result has negative energy: {case}")
            if (
                abs(row["ambient_c"] - ambient) > 0.01
                or abs(row["input_heat_w"] - heat) > 0.01
            ):
                errors.append(f"Solver result does not match case input: {case}")
            if any(
                row[field] < ambient
                for field in ("max_skin_c", "max_battery_c", "max_junction_c")
            ):
                errors.append(f"Solver result is cooler than ambient: {case}")
            if (
                row["max_skin_c"] > skin_limit
                or row["max_battery_c"] > (charge_max if charging else battery_max)
                or row["max_junction_c"] > junction_max
            ):
                errors.append(f"Thermal limit is exceeded: {case}")
            if (
                case != "T03_peak_ai_burst_25c"
                and heat > 0
                and abs(row["outbound_heat_w"] - heat) / heat > 0.03
            ):
                errors.append(f"Solver energy balance exceeds 3 percent: {case}")
        if set(results) == {"medium", "fine"} and any(
            abs(results["medium"][field] - results["fine"][field]) > 1.0
            for field in ("max_skin_c", "max_battery_c", "max_junction_c")
        ):
            errors.append(f"Thermal mesh convergence exceeds 1 C: {case}")
    return {
        "status": "pass" if not errors else "fail",
        "source": RELEASE.as_posix(),
        "revision": release.get("revision"),
        "reviewed_by": release.get("reviewed_by"),
        **{field: release.get(field) for field in upstream},
        "cases_checked": len(by_case),
        "results_checked": len(rows),
        "errors": errors,
        "caveat": "A reviewed solver table and internal checks do not establish model fidelity, supplier limits, physical temperature, or safe operation.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    result = audit(args.repo_root)
    print(json.dumps(result, indent=2))
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
