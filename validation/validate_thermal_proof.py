"""Check thermal release bindings, loads, solver tables, and limit failures."""

from __future__ import annotations

import copy
import csv
import hashlib
import io
import json
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from buildslate.hardware_readiness import _evidence_result  # noqa: E402
from buildslate.io import dump_yaml  # noqa: E402
from buildslate.power_safety_proof import RELEASE as POWER_RELEASE  # noqa: E402
from buildslate.power_safety_proof import audit as audit_power  # noqa: E402
from buildslate.thermal_proof import (  # noqa: E402
    ASSEMBLY,
    BOARD,
    BOUNDARIES,
    CASES,
    INTERFACES,
    MANIFEST,
    MATERIALS,
    MODEL,
    RELEASE,
    RESULTS,
    RESULT_FIELDS,
    SELECTED_BOM,
    audit,
)
from validation.validate_power_safety_proof import _fixture as power_fixture  # noqa: E402


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def _publish(root: Path, release: dict, model: dict, rows: list[dict]) -> None:
    _json(root / MODEL, model)
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=RESULT_FIELDS, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    (root / RESULTS).write_text(output.getvalue(), encoding="utf-8")
    release["solver_input_sha256"] = _sha(root / MODEL)
    release["solver_results_sha256"] = _sha(root / RESULTS)
    _json(root / RELEASE, release)


def _fixture(root: Path) -> tuple[dict, dict, list[dict]]:
    power = power_fixture(root)
    selected = root / SELECTED_BOM
    parts = json.loads(selected.read_text(encoding="utf-8"))
    parts["parts"]["compute_platform"] = {
        "mpn": "FIXTURE-COMPUTE",
        "capabilities": {"maximum_junction_temperature_c": 90.0},
    }
    _json(selected, parts)
    power["selected_bom_sha256"] = _sha(selected)
    _json(root / POWER_RELEASE, power)
    assembly = root / ASSEMBLY
    assembly.parent.mkdir(parents=True, exist_ok=True)
    assembly.write_bytes(b"fixture assembly STEP bytes")
    geometry = {
        "compute_platform": "soc_package",
        "memory_128gb": "memory_packages",
        "storage_1tb": "storage_package",
        "display": "display_module",
        "radios": "main_pcb",
        "cameras": "rear_camera_module",
        "system_io_and_controls": "main_pcb",
    }
    roles = sorted(set(MATERIALS) | set(geometry.values()) | {"front_camera_module"})
    manifest = root / MANIFEST
    manifest.write_text(
        dump_yaml({"parts": [{"id": role, "roles": [role]} for role in roles]}),
        encoding="utf-8",
    )
    evidence = root / "engineering/hardware/released/thermal/sources/supplier-data.pdf"
    evidence.parent.mkdir(parents=True, exist_ok=True)
    evidence.write_bytes(b"fixture thermal source bytes")
    source = {
        "evidence_path": evidence.relative_to(root).as_posix(),
        "evidence_sha256": _sha(evidence),
    }
    material = {
        "conductivity_x_w_mk": 10.0,
        "conductivity_y_w_mk": 10.0,
        "conductivity_z_w_mk": 2.0,
        "density_kg_m3": 2000.0,
        "heat_capacity_j_kgk": 800.0,
        **source,
    }
    interface = {"resistance_m2k_w": 0.0002, "bondline_mm": 0.1, **source}
    power_result = audit_power(root)
    if power_result["status"] != "pass":
        raise ValueError("Synthetic power fixture is invalid")
    cases: dict[str, dict] = {}
    rows = []
    for case, (ambient, column, charging) in CASES.items():
        sources = {}
        heat = 0.0
        for load in power["loads"]:
            role = load["id"]
            watts = (
                (1.5 if role == "system_io_and_controls" else 0.0)
                if charging
                else load["peak_w" if column == "peak" else "continuous_w"]
            )
            deposits = (
                [
                    {"geometry_role": "rear_camera_module", "heat_w": watts / 2},
                    {"geometry_role": "front_camera_module", "heat_w": watts / 2},
                ]
                if role == "cameras"
                else [{"geometry_role": geometry[role], "heat_w": watts}]
            )
            sources[role] = {"heat_deposits": deposits, "exported_w": 0.0}
            heat += watts
        charger_heat = 8.0 * (1 / 0.85 - 1) if charging else 0.0
        battery_current = (
            2.0
            if charging
            else power_result[
                "peak_battery_current_a"
                if column == "peak"
                else "continuous_battery_current_a"
            ]
        )
        battery_heat = battery_current**2 * 0.01
        heat += charger_heat + battery_heat
        cases[case] = {
            "ambient_c": ambient,
            "boundary_id": BOUNDARIES[case],
            "charger_heat_w": charger_heat,
            "battery_heat_w": battery_heat,
            "battery_geometry_role": "battery_pack",
            "sources": sources,
        }
        if charging:
            cases[case]["charger_geometry_role"] = "main_pcb"
        if column == "peak":
            cases[case]["duration_s"] = 60
        for mesh, offset in (("medium", 0.4), ("fine", 0.0)):
            rows.append(
                {
                    "case": case,
                    "mesh": mesh,
                    "simulated_duration_s": 60 if column == "peak" else 0,
                    "ambient_c": ambient,
                    "input_heat_w": heat,
                    "outbound_heat_w": 0.0 if column == "peak" else heat,
                    "max_skin_c": (42.0 if ambient == 35 else 40.0) + offset,
                    "max_battery_c": (39.0 if ambient == 35 else 36.0) + offset,
                    "max_junction_c": 80.0 + offset,
                }
            )
    model = {
        "schema_version": 1,
        "device": "slate-pocket-v1r",
        "mechanical_assembly_sha256": _sha(assembly),
        "power_safety_sha256": _sha(root / POWER_RELEASE),
        "materials": {role: copy.deepcopy(material) for role in MATERIALS},
        "battery_internal_loss": {"resistance_ohm": 0.01, **source},
        "interfaces": {name: copy.deepcopy(interface) for name in INTERFACES},
        "boundary_conditions": {
            name: {
                "convection_w_m2k": 10.0,
                "emissivity": 0.8,
                **source,
                **(
                    {"contact_area_mm2": 5000.0, "contact_conductance_w_m2k": 30.0}
                    if name == "handheld_25c"
                    else {}
                ),
            }
            for name in set(BOUNDARIES.values())
        },
        "meshes": {"medium": {"cells": 1000}, "fine": {"cells": 2000}},
        "cases": cases,
    }
    release = {
        "schema_version": 1,
        "device": "slate-pocket-v1r",
        "revision": "T1",
        "reviewed_by": "fixture reviewer",
        "solver_name": "fixture solver",
        "solver_version": "fixture-1",
        "mechanical_assembly_sha256": _sha(assembly),
        "mechanical_manifest_sha256": _sha(manifest),
        "routed_pcb_sha256": _sha(root / BOARD),
        "power_safety_sha256": _sha(root / POWER_RELEASE),
        "selected_bom_sha256": _sha(selected),
    }
    _publish(root, release, model, rows)
    return release, model, rows


def main() -> int:
    if audit(ROOT)["status"] != "missing":
        raise ValueError("Public checkout must not imply a released thermal design")
    with TemporaryDirectory() as temp:
        root = Path(temp)
        baseline_release, baseline_model, baseline_rows = _fixture(root)
        if audit(root)["status"] != "pass":
            raise ValueError(f"Valid thermal fixture was rejected: {audit(root)}")
        mutations = (
            ("material coverage", "model", lambda x: x["materials"].pop(MATERIALS[0])),
            (
                "material source",
                "model",
                lambda x: x["materials"][MATERIALS[0]].update(evidence_sha256="0" * 64),
            ),
            (
                "geometry binding",
                "model",
                lambda x: x.update(mechanical_assembly_sha256="0" * 64),
            ),
            (
                "mesh refinement",
                "model",
                lambda x: x["meshes"]["fine"].update(cells=1100),
            ),
            ("case coverage", "model", lambda x: x["cases"].pop(next(iter(CASES)))),
            (
                "grip boundary",
                "model",
                lambda x: x["boundary_conditions"]["handheld_25c"].pop(
                    "contact_area_mm2"
                ),
            ),
            (
                "wrong boundary",
                "model",
                lambda x: x["cases"]["T05_handheld_sustained_ramp"].update(
                    boundary_id="open_air_25c"
                ),
            ),
            (
                "source heat",
                "model",
                lambda x: x["cases"]["T02_sustained_ai_open_air_25c"]["sources"][
                    "compute_platform"
                ]["heat_deposits"][0].update(heat_w=2.0),
            ),
            (
                "charge overlap",
                "model",
                lambda x: x["cases"]["T08_wired_charge_evt0_cap"]["sources"][
                    "compute_platform"
                ]["heat_deposits"][0].update(heat_w=28.0),
            ),
            (
                "charge loss",
                "model",
                lambda x: x["cases"]["T08_wired_charge_evt0_cap"].update(
                    charger_heat_w=0.2
                ),
            ),
            (
                "wrong heat location",
                "model",
                lambda x: x["cases"]["T02_sustained_ai_open_air_25c"]["sources"][
                    "compute_platform"
                ]["heat_deposits"][0].update(geometry_role="battery_pack"),
            ),
            (
                "missing front camera heat",
                "model",
                lambda x: x["cases"]["T03_peak_ai_burst_25c"]["sources"]["cameras"][
                    "heat_deposits"
                ].pop(),
            ),
            (
                "battery heat omitted",
                "model",
                lambda x: x["cases"]["T02_sustained_ai_open_air_25c"].update(
                    battery_heat_w=0.0
                ),
            ),
            (
                "battery resistance source",
                "model",
                lambda x: x["battery_internal_loss"].update(evidence_sha256="0" * 64),
            ),
            ("missing result", "rows", lambda x: x.pop()),
            (
                "short burst",
                "rows",
                lambda x: next(
                    row for row in x if row["case"] == "T03_peak_ai_burst_25c"
                ).update(simulated_duration_s=20),
            ),
            ("energy balance", "rows", lambda x: x[0].update(outbound_heat_w=2.0)),
            ("skin limit", "rows", lambda x: x[0].update(max_skin_c=44.0)),
            ("mesh convergence", "rows", lambda x: x[0].update(max_junction_c=85.0)),
            (
                "battery charge limit",
                "rows",
                lambda x: next(
                    row for row in x if row["case"] == "T08_wired_charge_evt0_cap"
                ).update(max_battery_c=50.0),
            ),
        )
        for name, kind, mutate in mutations:
            release = copy.deepcopy(baseline_release)
            model = copy.deepcopy(baseline_model)
            rows = copy.deepcopy(baseline_rows)
            mutate(model if kind == "model" else rows)
            _publish(root, release, model, rows)
            if audit(root)["status"] == "pass":
                raise ValueError(f"Invalid thermal fixture passed: {name}")
        _publish(root, baseline_release, baseline_model, baseline_rows)
        record = {
            "path": RELEASE.as_posix(),
            "sha256": _sha(root / RELEASE),
            "revision": "T1",
            "reviewed_by": "fixture reviewer",
            "disposition": "approved",
        }
        related = {
            "selected_bom": {
                "disposition": "approved",
                "sha256": baseline_release["selected_bom_sha256"],
            },
            "routed_pcb": {
                "disposition": "approved",
                "sha256": baseline_release["routed_pcb_sha256"],
            },
            "mechanical_release": {
                "disposition": "approved",
                "sha256": baseline_release["mechanical_assembly_sha256"],
                "manifest_sha256": baseline_release["mechanical_manifest_sha256"],
            },
            "power_safety": {
                "disposition": "approved",
                "sha256": baseline_release["power_safety_sha256"],
            },
        }
        selection = {
            "status": "pass",
            "sha256": baseline_release["selected_bom_sha256"],
        }
        requirement = {"id": "thermal_release", "stage": "design_release"}
        if (
            _evidence_result(root, requirement, record, selection, related)["status"]
            != "accepted"
        ):
            raise ValueError("Approved bound thermal fixture was rejected")
        related["power_safety"]["sha256"] = "0" * 64
        if (
            _evidence_result(root, requirement, record, selection, related)["status"]
            == "accepted"
        ):
            raise ValueError("Thermal release accepted an unapproved power design")
    print("PASS: thermal cases, limits, mesh, energy, and release bindings checked")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
