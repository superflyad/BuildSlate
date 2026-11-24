"""Screen the 128 GB memory plan against an exact public LPDDR5X package."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

from buildslate.io import load_yaml

PROFILE = Path("configs/devices/slate-pocket-v1r.yaml")
CANDIDATES = Path("research/evidence/compute/platform-comparison.yaml")
FLOORPLAN = Path("engineering/pcb/slate-pocket-v1r-floorplan/floorplan.yaml")
ASSEMBLY = Path("engineering/assembly/assembly.yaml")
PUBLIC_PART = "micron_lpddr5x_16gb_public_part"


def audit_data(
    profile: dict, candidates: dict, floorplan: dict, assembly: dict
) -> dict:
    memory = profile["memory"]
    target = int(memory["capacity_gb"])
    assumed_per_site = int(memory["gb_per_package"])
    sites = {
        name: placement
        for name, placement in floorplan["placements"].items()
        if placement["function"] == "lpddr5x_32gb_planning_site"
    }
    part = candidates["memory_supplier_context"][PUBLIC_PART]
    capacity = int(part["capacity_gb"])
    package = [float(value) for value in part["package_mm"]]
    required = math.ceil(target / capacity)
    geometry = []
    for name, placement in sites.items():
        rectangle = placement["rectangle_mm"]
        width, length = float(rectangle["length"]), float(rectangle["width"])
        fits = (package[0] <= width and package[1] <= length) or (
            package[1] <= width and package[0] <= length
        )
        modeled_height = float(
            assembly["parts"]["pcb"]["parts"][name].get(
                "height_mm", assembly["parts"]["pcb"]["default_height_mm"]
            )
        )
        geometry.append(
            {
                "site": name,
                "reserve_mm": [width, length, modeled_height],
                "public_part_outline_fits": fits,
                "public_part_height_fits": package[2] <= modeled_height,
            }
        )
    boundary = floorplan["board"]["component_side_boundary_mm"]
    boundary_area = float(boundary["length"]) * float(boundary["width"])
    reserved_area = sum(
        float(item["rectangle_mm"]["length"]) * float(item["rectangle_mm"]["width"])
        for item in sites.values()
    )
    public_part_area = required * package[0] * package[1]
    errors = []
    if floorplan["metadata"]["modeled_memory_tier_gb"] != target:
        errors.append("Floorplan and profile memory capacities differ")
    if len(sites) * assumed_per_site != target:
        errors.append("Planning site count does not cover the target memory")
    if any(item["evidence_class"] != "placeholder" for item in sites.values()):
        errors.append("Unqualified memory site was promoted beyond placeholder")
    if part["density_gbit"] != capacity * 8:
        errors.append("Manufacturer gigabit density was confused with gigabytes")
    return {
        "target_gb": target,
        "planning_sites": len(sites),
        "assumed_gb_per_site": assumed_per_site,
        "public_reference_part": part["part_number"],
        "public_reference_capacity_gb": capacity,
        "public_reference_density_gbit": part["density_gbit"],
        "public_reference_package_mm": package,
        "public_reference_ball_count": part["ball_count"],
        "required_public_reference_packages": required,
        "reserved_memory_area_mm2": reserved_area,
        "public_reference_package_area_mm2": public_part_area,
        "additional_nominal_area_mm2": public_part_area - reserved_area,
        "public_reference_board_area_percent": round(
            public_part_area / boundary_area * 100, 1
        ),
        "site_geometry": geometry,
        "source_consistency": "pass" if not errors else "fail",
        "source_errors": errors,
        "integration_status": "blocked",
        "missing_design_evidence": [
            "Exact 32 GB package MPN, drawing, and availability, or a new eight-package board architecture",
            "X2-qualified 128 GB channel topology, bus width, ranks, and signal rules",
            "Memory rails, power sequence, routed SI/PI, and thermal measurements",
            "Booted Slate unit with hash-bound 128 GB resident-memory test",
        ],
        "source": part["source"]["url"],
        "caveat": "This 16 GB part is a public geometry reference, not an X2-qualified memory selection. Eight packages do not prove a routable or bootable 128 GB Slate board.",
    }


def audit(root: Path) -> dict:
    return audit_data(
        *(load_yaml(root / path) for path in (PROFILE, CANDIDATES, FLOORPLAN, ASSEMBLY))
    )


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
