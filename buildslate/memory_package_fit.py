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
STUDY = Path("engineering/pcb/slate-pocket-v1r-floorplan/memory-8x16-study.yaml")
PUBLIC_PART = "micron_lpddr5x_16gb_public_part"
OBSOLETE_32GB_PART = "micron_lpddr5x_32gb_obsolete_reference"
ADATA_PARTS = ("adata_lpddr5x_32gbit", "adata_lpddr5x_64gbit")


def _rectangle_gap(a: list[float], b: list[float]) -> float:
    """Nominal edge distance between axis-aligned package outlines."""
    dx = max(b[0] - a[0] - a[2], a[0] - b[0] - b[2], 0.0)
    dy = max(b[1] - a[1] - a[3], a[1] - b[1] - b[3], 0.0)
    return math.hypot(dx, dy)


def _adata_unit_screen(
    context: dict, target: int, sites: dict, controller_widths: dict
) -> dict:
    """Reconcile conflicting ADATA page units with the published organization."""
    rows = []
    errors = []
    for identifier in ADATA_PARTS:
        part = context[identifier]
        words = part["organization_megawords"]
        width = part["organization_width_bits"]
        uk_gbit = part["uk_labeled_density_gbit"]
        us_gb = part["us_labeled_capacity_gb"]
        outline = part["package_outline_mm"]
        if any(
            not isinstance(value, int) or isinstance(value, bool) or value <= 0
            for value in (words, width, uk_gbit, us_gb)
        ):
            errors.append(f"{identifier}: invalid organization or source capacity")
            continue
        if (
            not isinstance(outline, list)
            or len(outline) != 2
            or any(
                not isinstance(value, (int, float))
                or isinstance(value, bool)
                or not math.isfinite(value)
                or value <= 0
                for value in outline
            )
        ):
            errors.append(f"{identifier}: invalid package outline")
            continue
        if any(
            not isinstance(part.get(key), str)
            or not part[key].startswith("https://www.adata.com/")
            for key in ("source_us", "source_uk")
        ):
            errors.append(f"{identifier}: manufacturer source missing")
            continue
        organization_gbit = words * width // 1024
        if words * width % 1024 or organization_gbit != uk_gbit:
            errors.append(f"{identifier}: organization disagrees with UK density")
        if uk_gbit % 8:
            errors.append(f"{identifier}: density is not whole gigabytes")
            continue
        actual_gb = uk_gbit // 8
        if us_gb != uk_gbit or us_gb == actual_gb:
            errors.append(f"{identifier}: expected US Gb/GB label conflict changed")
        required = math.ceil(target / actual_gb)
        fits_sites = all(
            (
                outline[0] <= float(site["rectangle_mm"]["length"])
                and outline[1] <= float(site["rectangle_mm"]["width"])
            )
            or (
                outline[1] <= float(site["rectangle_mm"]["length"])
                and outline[0] <= float(site["rectangle_mm"]["width"])
            )
            for site in sites.values()
        )
        independent_width = required * width
        rows.append(
            {
                "id": identifier,
                "part_number": part["part_number"],
                "us_labeled_capacity_gb": us_gb,
                "uk_labeled_density_gbit": uk_gbit,
                "organization": f"{words}M x{width}",
                "capacity_from_organization_gb": organization_gbit // 8,
                "reconciled_package_capacity_gb": actual_gb,
                "four_package_capacity_gb": 4 * actual_gb,
                "packages_for_target": required,
                "package_outline_mm": outline,
                "planning_sites_fit": fits_sites,
                "independent_data_width_bits": independent_width,
                "independent_width_fits_controllers": {
                    name: independent_width <= bus_width
                    for name, bus_width in controller_widths.items()
                },
                "source_us": part["source_us"],
                "source_uk": part["source_uk"],
                "status": "source_unit_conflict_not_x2_qualified",
            }
        )
    return {
        "status": "source_unit_conflict" if not errors else "source_data_invalid",
        "parts": rows,
        "source_errors": errors,
        "caveat": "Organization arithmetic resolves the displayed unit mismatch; it does not establish availability, X2 qualification, channel/rank support, or a routed board.",
    }


def _placement_study(
    study: dict,
    floorplan: dict,
    assembly: dict,
    board_height: float,
    package: list[float],
    required: int,
) -> dict:
    boundary = floorplan["board"]["component_side_boundary_mm"]
    limit = [
        float(boundary["x"]),
        float(boundary["y"]),
        float(boundary["length"]),
        float(boundary["width"]),
    ]
    clearance = float(study["assumed_planar_clearance_mm"])
    board = assembly["parts"]["mechanical"]["main_pcb_placeholder"]
    board_z = float(board["z_mm"])
    top_z = float(assembly["parts"]["pcb"]["z_mm"])
    origin = floorplan["board"]["origin_in_mechanical_model_mm"]
    placed = []
    conflicts = []
    if study["metadata"]["reference_part"] != PUBLIC_PART:
        conflicts.append("Study reference part does not match the screened package")
    if len(study["placements"]) != required:
        conflicts.append("Study package count does not cover the memory target")
    for name, item in study["placements"].items():
        side = item["side"]
        if side not in {"component", "reverse"}:
            conflicts.append(f"{name}: unknown PCB side")
            continue
        rect = [float(item["x_mm"]), float(item["y_mm"]), package[0], package[1]]
        z = top_z if side == "component" else round(board_z - package[2], 3)
        placed.append(
            {
                "id": name,
                "side": side,
                "rect_mm": rect,
                "assembly_box_mm": [
                    float(origin["x"]) + rect[0],
                    float(origin["y"]) + rect[1],
                    z,
                    *package,
                ],
            }
        )
        if (
            rect[0] < limit[0]
            or rect[1] < limit[1]
            or rect[0] + rect[2] > limit[0] + limit[2]
            or rect[1] + rect[3] > limit[1] + limit[3]
        ):
            conflicts.append(f"{name}: outside component-side boundary")
        if z < 0:
            conflicts.append(f"{name}: below device rear datum")
    occupied = [
        (name, [float(rect[key]) for key in ("x", "y", "length", "width")])
        for name, item in floorplan["placements"].items()
        if item["function"] != "lpddr5x_32gb_planning_site"
        for rect in (item["rectangle_mm"],)
    ]
    gaps = []
    for index, item in enumerate(placed):
        neighbours = placed[index + 1 :]
        for other in neighbours:
            if item["side"] != other["side"]:
                continue
            gap = _rectangle_gap(item["rect_mm"], other["rect_mm"])
            gaps.append(gap)
            if gap < clearance:
                conflicts.append(f"{item['id']} / {other['id']}: {gap:.2f} mm gap")
        if item["side"] == "component":
            for name, rect in occupied:
                gap = _rectangle_gap(item["rect_mm"], rect)
                gaps.append(gap)
                if gap < clearance:
                    conflicts.append(f"{item['id']} / {name}: {gap:.2f} mm gap")
    sides = {
        side: sum(item["side"] == side for item in placed)
        for side in ("component", "reverse")
    }
    if sides != {"component": required // 2, "reverse": required // 2}:
        conflicts.append(
            "Study must distribute the eight reference packages across both sides"
        )
    stack_issues = []
    floorplan_thickness = float(floorplan["board"]["outline_mm"]["thickness"])
    if not math.isclose(board_height, floorplan_thickness, abs_tol=1e-6):
        stack_issues.append(
            "Mechanical board height differs from floorplan stack thickness"
        )
    if not math.isclose(board_z + board_height, top_z, abs_tol=1e-6):
        stack_issues.append("Component Z does not meet the mechanical board top")
    return {
        "status": "outline_clear_stack_unresolved"
        if not conflicts and stack_issues
        else ("outline_clear" if not conflicts else "outline_conflict"),
        "package_count": len(placed),
        "packages_per_side": sides,
        "assumed_planar_clearance_mm": clearance,
        "minimum_screened_planar_gap_mm": round(min(gaps), 3) if gaps else None,
        "board_outline_mm": [
            float(floorplan["board"]["outline_mm"]["length"]),
            float(floorplan["board"]["outline_mm"]["width"]),
        ],
        "component_side_placements": [
            {"id": name, "rect_mm": rect} for name, rect in occupied
        ],
        "floorplan_board_thickness_mm": floorplan_thickness,
        "mechanical_board_height_mm": board_height,
        "board_z_mm": [board_z, board_z + board_height],
        "placement_conflicts": conflicts,
        "stack_issues": stack_issues,
        "placements": placed,
        "source": STUDY.as_posix(),
        "caveat": "Planar package boxes do not include solder lands, via escape, decoupling, shields, thermal contacts, or X2 memory-channel rules.",
    }


def audit_data(
    profile: dict,
    candidates: dict,
    floorplan: dict,
    assembly: dict,
    study: dict,
    board_height: float,
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
    obsolete = candidates["memory_supplier_context"][OBSOLETE_32GB_PART]
    controller = candidates["candidates"]["qualcomm_snapdragon_x2_elite_extreme"]
    capacity = int(part["capacity_gb"])
    package = [float(value) for value in part["package_mm"]]
    required = math.ceil(target / capacity)
    controller_width = controller["memory_bus_width_bits"]
    package_width = part["bus_width_bits"]
    widths_valid = all(
        isinstance(value, int) and not isinstance(value, bool) and value > 0
        for value in (controller_width, package_width)
    )
    independent_width = required * package_width if widths_valid else None
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
    if obsolete["density_gbit"] != obsolete["capacity_gb"] * 8:
        errors.append("Obsolete 32 GB package density was confused with gigabytes")
    adata = _adata_unit_screen(
        candidates["memory_supplier_context"],
        target,
        sites,
        {
            "x2_elite_extreme": controller_width,
            "x2_plus": candidates["candidates"]["qualcomm_snapdragon_x2_plus_10_core"][
                "memory_bus_width_bits"
            ],
        },
    )
    errors.extend(adata["source_errors"])
    if not widths_valid:
        errors.append("Controller or memory package bus width is invalid")
    else:
        transfer_rate = controller["memory_transfer_rate_mt_s"]
        bandwidth = controller["memory_bandwidth_gb_s"]
        if not all(
            isinstance(value, (int, float))
            and not isinstance(value, bool)
            and math.isfinite(value)
            and value > 0
            for value in (transfer_rate, bandwidth)
        ):
            errors.append("X2 transfer rate or bandwidth is invalid")
        elif abs(controller_width * transfer_rate / 8 / 1000 - bandwidth) > 1:
            errors.append("X2 bus width, transfer rate, and bandwidth disagree")
    return {
        "target_gb": target,
        "planning_sites": len(sites),
        "assumed_gb_per_site": assumed_per_site,
        "public_reference_part": part["part_number"],
        "public_reference_capacity_gb": capacity,
        "public_reference_density_gbit": part["density_gbit"],
        "public_reference_package_mm": package,
        "public_reference_ball_count": part["ball_count"],
        "obsolete_32gb_reference": {
            "part_number": obsolete["part_number"],
            "capacity_gb": obsolete["capacity_gb"],
            "density_gbit": obsolete["density_gbit"],
            "package_mm": obsolete["package_mm"],
            "ball_count": obsolete["ball_count"],
            "public_part_status": obsolete["public_part_status"],
            "packages_for_128gb": math.ceil(target / obsolete["capacity_gb"]),
            "site_outline_fits": all(
                (
                    obsolete["package_mm"][0] <= float(site["rectangle_mm"]["length"])
                    and obsolete["package_mm"][1]
                    <= float(site["rectangle_mm"]["width"])
                )
                or (
                    obsolete["package_mm"][1] <= float(site["rectangle_mm"]["length"])
                    and obsolete["package_mm"][0]
                    <= float(site["rectangle_mm"]["width"])
                )
                for site in sites.values()
            ),
            "site_nominal_height_fits": all(
                obsolete["package_mm"][2]
                <= float(
                    assembly["parts"]["pcb"]["parts"][name].get(
                        "height_mm", assembly["parts"]["pcb"]["default_height_mm"]
                    )
                )
                for name in sites
            ),
            "independent_bus_width_bits": (
                math.ceil(target / obsolete["capacity_gb"]) * obsolete["bus_width_bits"]
            ),
            "independent_bus_width_fits": (
                math.ceil(target / obsolete["capacity_gb"]) * obsolete["bus_width_bits"]
                <= controller_width
            ),
            "status": "rejected_obsolete_not_x2_qualified",
            "source": obsolete["source"]["url"],
            "caveat": "This exact 32 GB part is obsolete; package capacity does not establish X2 channel/rank support or procurement.",
        },
        "adata_unit_reconciliation": adata,
        "bus_topology_screen": {
            "controller_bus_width_bits": controller_width,
            "public_reference_package_bus_width_bits": package_width,
            "independent_connection_width_bits": independent_width,
            "independent_connection_possible": (
                independent_width <= controller_width if widths_valid else None
            ),
            "shared_channel_or_other_topology_required": (
                independent_width > controller_width if widths_valid else None
            ),
            "caveat": "The width comparison only rules out one independent host connection per reference package. It cannot prove whether shared channels, ranks, timing, routing, or boot are supported.",
            "controller_source": controller["source"]["url"],
        },
        "required_public_reference_packages": required,
        "reserved_memory_area_mm2": reserved_area,
        "public_reference_package_area_mm2": public_part_area,
        "additional_nominal_area_mm2": public_part_area - reserved_area,
        "public_reference_board_area_percent": round(
            public_part_area / boundary_area * 100, 1
        ),
        "site_geometry": geometry,
        "eight_package_study": _placement_study(
            study, floorplan, assembly, board_height, package, required
        ),
        "source_consistency": "pass" if not errors else "fail",
        "source_errors": errors,
        "integration_status": "blocked",
        "missing_design_evidence": [
            "Current-production 32 GB package MPN, drawing, and availability, or a new eight-package board architecture",
            "X2-qualified 128 GB shared-channel or other package topology, ranks, and signal rules",
            "Fabricator-reviewed 0.8 mm 12-layer HDI stack and two-sided assembly limits",
            "Memory rails, power sequence, routed SI/PI, and thermal measurements",
            "Booted Slate unit with hash-bound 128 GB resident-memory test",
        ],
        "source": part["source"]["url"],
        "caveat": "This 16 GB part is a public geometry reference, not an X2-qualified memory selection. Eight packages do not prove a routable or bootable 128 GB Slate board.",
    }


def audit(root: Path) -> dict:
    profile, candidates, floorplan, assembly, study = (
        load_yaml(root / path)
        for path in (PROFILE, CANDIDATES, FLOORPLAN, ASSEMBLY, STUDY)
    )
    envelope = load_yaml(root / assembly["sources"]["envelope"])
    board_height = float(envelope["placements"]["main_pcb_placeholder"]["height_mm"])
    return audit_data(profile, candidates, floorplan, assembly, study, board_height)


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
