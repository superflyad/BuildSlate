"""Screen public compute limits against Slate's approved memory and phone needs."""

from __future__ import annotations

import argparse
import json
import math
import re
from pathlib import Path

from buildslate.io import load_yaml

PROFILE = Path("configs/devices/slate-pocket-v1r.yaml")
CANDIDATES = Path("research/evidence/compute/platform-comparison.yaml")
FLOORPLAN = Path("engineering/pcb/slate-pocket-v1r-floorplan/floorplan.yaml")
ENVELOPE = Path("cad/slate-pocket-v1r/envelope-model/envelope.yaml")
MODES = {"integrated", "external_supported_not_designed", "none"}


def _capacity(candidate: dict) -> int:
    for key in ("maximum_memory_gb", "maximum_unified_memory_gb", "memory_gb"):
        value = candidate.get(key)
        if isinstance(value, int) and not isinstance(value, bool) and value > 0:
            return value
        if isinstance(value, str) and value.endswith("_plus"):
            prefix = value.removesuffix("_plus")
            if prefix.isdigit() and int(prefix) > 0:
                return int(prefix)
    raise ValueError("Candidate has no public memory capacity bound")


def _rectangle(data: dict, label: str) -> tuple[float, float, float, float]:
    if not isinstance(data, dict):
        raise ValueError(f"{label}: invalid rectangle")
    try:
        values = tuple(float(data[key]) for key in ("x", "y", "length", "width"))
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError(f"{label}: invalid rectangle") from exc
    if any(not math.isfinite(value) for value in values) or any(
        value <= 0 for value in values[2:]
    ):
        raise ValueError(f"{label}: invalid rectangle")
    return values


def _free_strips(
    boundary: tuple[float, float, float, float],
    occupied: tuple[float, float, float, float],
) -> list[tuple[float, float]]:
    bx, by, bl, bw = boundary
    ox, oy, ol, ow = occupied
    if ox < bx or oy < by or ox + ol > bx + bl or oy + ow > by + bw:
        raise ValueError("Battery reference exceeds the internal boundary")
    return [
        (ox - bx, bw),
        (bx + bl - ox - ol, bw),
        (bl, oy - by),
        (bl, by + bw - oy - ow),
    ]


def _fits_any_strip(sides: list[float], strips: list[tuple[float, float]]) -> bool:
    return any(
        length <= free_length and width <= free_width
        for length, width in (sides, sides[::-1])
        for free_length, free_width in strips
    )


def audit(root: Path) -> dict:
    profile = load_yaml(root / PROFILE)
    source = load_yaml(root / CANDIDATES)
    floorplan = load_yaml(root / FLOORPLAN)
    envelope = load_yaml(root / ENVELOPE)
    floor = profile["decision_baseline"]["locked_trade_rules"]["memory"][
        "fallback_tiers_gb"
    ][-1]
    configured = profile["integration_configuration"]["memory_gb"]
    face = sorted(
        (
            float(profile["geometry"]["length_mm"]),
            float(profile["geometry"]["width_mm"]),
        ),
        reverse=True,
    )
    if any(not math.isfinite(side) or side <= 0 for side in face):
        raise ValueError("Slate body face is invalid")
    board_outline = floorplan["board"]["outline_mm"]
    board_face = sorted(
        (float(board_outline["length"]), float(board_outline["width"])),
        reverse=True,
    )
    if any(not math.isfinite(side) or side <= 0 for side in board_face):
        raise ValueError("Current PCB face is invalid")
    boundary = _rectangle(
        envelope["device"]["internal_boundary_mm"], "Internal boundary"
    )
    battery = _rectangle(
        envelope["placements"]["battery_reference"]["rectangle_mm"],
        "Battery reference",
    )
    strips = _free_strips(boundary, battery)
    sustained_target = float(profile["compute"]["sustained_power_w"])
    if not math.isfinite(sustained_target) or sustained_target <= 0:
        raise ValueError("Slate sustained power screen is invalid")
    body_thickness = float(profile["geometry"]["thickness_mm"])
    device_mass_ceiling = float(profile["mass_targets"]["acceptable_range_g"]["max"])
    if any(
        not math.isfinite(value) or value <= 0
        for value in (body_thickness, device_mass_ceiling)
    ):
        raise ValueError("Slate thickness or mass limit is invalid")
    if not isinstance(floor, int) or floor <= 0 or configured != floor:
        raise ValueError("Operational memory differs from the approved fallback floor")
    candidates = source.get("candidates")
    if not isinstance(candidates, dict) or not candidates:
        raise ValueError("No public platform candidates")
    rows = []
    for identifier, candidate in candidates.items():
        if not isinstance(candidate, dict):
            raise ValueError(f"{identifier}: malformed platform candidate")
        mode = candidate.get("modem_integration")
        if mode not in MODES:
            raise ValueError(f"{identifier}: unknown modem integration status")
        reference = candidate.get("source")
        if (
            not isinstance(reference, dict)
            or not str(reference.get("url", "")).startswith("https://")
            or not reference.get("accessed")
        ):
            raise ValueError(f"{identifier}: manufacturer source is missing")
        maximum = _capacity(candidate)
        bus_width = candidate.get("memory_bus_width_bits")
        if bus_width is not None and (
            not isinstance(bus_width, int)
            or isinstance(bus_width, bool)
            or bus_width <= 0
        ):
            raise ValueError(f"{identifier}: invalid memory bus width")
        cpu_cores = candidate.get("cpu_cores")
        if cpu_cores is not None and (
            not isinstance(cpu_cores, int)
            or isinstance(cpu_cores, bool)
            or cpu_cores <= 0
        ):
            raise ValueError(f"{identifier}: invalid CPU core count")
        outline = candidate.get("module_outline_mm")
        outline_fit = None
        board_fit = None
        board_overrun = None
        battery_fit = None
        if outline is not None:
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
                raise ValueError(f"{identifier}: invalid module outline")
            module_sides = sorted((float(value) for value in outline), reverse=True)
            outline_fit = all(
                module <= available
                for module, available in zip(module_sides, face, strict=True)
            )
            board_fit = all(
                module <= available
                for module, available in zip(module_sides, board_face, strict=True)
            )
            board_overrun = [
                round(max(0, module - available), 2)
                for module, available in zip(module_sides, board_face, strict=True)
            ]
            battery_fit = _fits_any_strip(module_sides, strips)
        height = candidate.get("module_height_mm")
        mass = candidate.get("module_nominal_mass_g")
        mass_tolerance = candidate.get("module_mass_tolerance_percent")
        detailed = candidate.get("detailed_datasheet")
        if detailed is not None or any(
            value is not None for value in (height, mass, mass_tolerance)
        ):
            if (
                outline is None
                or not isinstance(detailed, dict)
                or not str(detailed.get("url", "")).startswith("https://")
                or not isinstance(detailed.get("revision"), str)
                or not detailed["revision"].strip()
                or not detailed.get("accessed")
                or not re.fullmatch(r"[0-9a-f]{64}", str(detailed.get("sha256", "")))
            ):
                raise ValueError(f"{identifier}: module geometry source is missing")
        if height is not None and (
            not isinstance(height, (int, float))
            or isinstance(height, bool)
            or not math.isfinite(height)
            or height <= 0
        ):
            raise ValueError(f"{identifier}: invalid module height")
        if (mass is None) != (mass_tolerance is None):
            raise ValueError(f"{identifier}: incomplete module mass specification")
        if mass is not None and (
            not isinstance(mass, (int, float))
            or isinstance(mass, bool)
            or not math.isfinite(mass)
            or mass <= 0
            or not isinstance(mass_tolerance, (int, float))
            or isinstance(mass_tolerance, bool)
            or not math.isfinite(mass_tolerance)
            or not 0 <= mass_tolerance < 100
        ):
            raise ValueError(f"{identifier}: invalid module mass specification")
        mass_min = mass * (1 - mass_tolerance / 100) if mass is not None else None
        power_range = candidate.get("power_range_w", candidate.get("tdp_range_w"))
        power_basis = (
            "advertised_power_range"
            if "power_range_w" in candidate
            else "tdp_range"
            if "tdp_range_w" in candidate
            else None
        )
        published_lower_power = None
        if power_range is not None:
            if (
                not isinstance(power_range, list)
                or len(power_range) != 2
                or any(
                    not isinstance(value, (int, float))
                    or isinstance(value, bool)
                    or not math.isfinite(value)
                    or value <= 0
                    for value in power_range
                )
                or power_range[0] > power_range[1]
            ):
                raise ValueError(f"{identifier}: invalid published power range")
            published_lower_power = float(power_range[0])
        stock_modes = candidate.get("stock_power_modes_w")
        stock_source = candidate.get("stock_modes_source")
        if (stock_modes is None) != (stock_source is None):
            raise ValueError(f"{identifier}: stock power mode source is incomplete")
        if stock_modes is not None and (
            not isinstance(stock_modes, list)
            or not stock_modes
            or any(
                not isinstance(value, (int, float))
                or isinstance(value, bool)
                or not math.isfinite(value)
                or value <= 0
                for value in stock_modes
            )
            or stock_modes != sorted(set(stock_modes))
            or power_range is None
            or stock_modes[0] < power_range[0]
            or stock_modes[-1] > power_range[1]
            or not isinstance(stock_source, str)
            or not stock_source.startswith("https://")
        ):
            raise ValueError(f"{identifier}: invalid stock power modes")
        capacity_permits_floor = maximum >= floor
        phone_integration = mode == "integrated"
        configured = candidate.get(
            "public_configured_memory_gb",
            candidate.get("configured_capacity_gb_in_brief"),
        )
        if configured is not None and (
            not isinstance(configured, int)
            or isinstance(configured, bool)
            or configured <= 0
            or configured > maximum
        ):
            raise ValueError(f"{identifier}: invalid public configured capacity")
        arrangement = candidate.get("published_memory_arrangement")
        if arrangement is not None and (
            not isinstance(arrangement, dict)
            or not isinstance(detailed, dict)
            or configured is None
            or any(
                not isinstance(arrangement.get(key), int)
                or isinstance(arrangement[key], bool)
                or arrangement[key] <= 0
                for key in (
                    "package_count",
                    "package_capacity_gb",
                    "module_bus_width_bits",
                )
            )
            or arrangement["package_count"] * arrangement["package_capacity_gb"]
            != configured
        ):
            raise ValueError(f"{identifier}: invalid published memory arrangement")
        observed = candidate.get("observed_oem_configuration")
        physical = candidate.get("physical_package_observation")
        if physical is not None and observed is None:
            raise ValueError(f"{identifier}: physical observation has no OEM system")
        observed_memory = None
        observed_source = None
        service_source = None
        board_spare_part = None
        physical_source = None
        if observed is not None:
            if not isinstance(observed, dict):
                raise ValueError(f"{identifier}: malformed OEM configuration")
            observed_memory = observed.get("memory_gb")
            observed_record = observed.get("source")
            observed_source = (
                observed_record.get("url")
                if isinstance(observed_record, dict)
                else None
            )
            board_spare_part = observed.get("board_spare_part")
            service_record = observed.get("service_source")
            service_source = (
                service_record.get("url") if isinstance(service_record, dict) else None
            )
            if (
                not isinstance(observed_memory, int)
                or isinstance(observed_memory, bool)
                or observed_memory <= 0
                or observed_memory > maximum
                or not isinstance(observed.get("product"), str)
                or not observed["product"].strip()
                or observed.get("platform_part") != candidate.get("representative_part")
                or observed.get("placement")
                not in {"memory_on_package", "board_soldered", "unspecified"}
                or not isinstance(observed_source, str)
                or not observed_source.startswith("https://")
                or ((board_spare_part is None) != (service_record is None))
                or (
                    board_spare_part is not None
                    and (
                        not isinstance(board_spare_part, str)
                        or not board_spare_part.strip()
                        or not isinstance(service_source, str)
                        or not service_source.startswith("https://")
                    )
                )
            ):
                raise ValueError(f"{identifier}: OEM configuration is inconsistent")
        if physical is not None:
            if not isinstance(physical, dict):
                raise ValueError(
                    f"{identifier}: malformed physical package observation"
                )
            physical_record = physical.get("source")
            physical_source = (
                physical_record.get("url")
                if isinstance(physical_record, dict)
                else None
            )
            package_count = physical.get("dram_package_count")
            package_capacity = physical.get("capacity_gb_per_package")
            if (
                observed.get("placement") != "memory_on_package"
                or physical.get("placement") != "co_packaged_with_soc"
                or not isinstance(package_count, int)
                or isinstance(package_count, bool)
                or package_count <= 0
                or not isinstance(package_capacity, int)
                or isinstance(package_capacity, bool)
                or package_capacity <= 0
                or package_count * package_capacity != observed_memory
                or not isinstance(physical_source, str)
                or not physical_source.startswith("https://")
            ):
                raise ValueError(
                    f"{identifier}: physical package evidence is inconsistent"
                )
        rows.append(
            {
                "id": identifier,
                "part": candidate.get(
                    "part_numbers", [candidate.get("representative_part")]
                )[0],
                "platform_class": candidate.get("platform_class"),
                "public_maximum_memory_gb": maximum,
                "public_memory_bus_width_bits": bus_width,
                "cpu_cores": cpu_cores,
                "public_configured_memory_gb": configured,
                "published_memory_arrangement": arrangement,
                "observed_oem_product": (
                    observed["product"] if observed is not None else None
                ),
                "observed_oem_product_sku": (
                    observed.get("product_sku") if observed is not None else None
                ),
                "observed_oem_memory_gb": observed_memory,
                "observed_oem_memory_placement": (
                    observed["placement"] if observed is not None else None
                ),
                "observed_oem_source": observed_source,
                "observed_oem_board_spare_part": board_spare_part,
                "observed_oem_service_source": service_source,
                "physical_package_source": physical_source,
                "published_capacity_permits_floor": capacity_permits_floor,
                "integrated_phone_path": phone_integration,
                "combined_public_fit": capacity_permits_floor and phone_integration,
                "public_128gb_configuration": any(
                    value is not None and value >= floor
                    for value in (configured, observed_memory)
                ),
                "module_outline_mm": outline,
                "module_outline_fits_body_face": outline_fit,
                "module_outline_fits_current_board_face": board_fit,
                "module_over_current_board_mm": board_overrun,
                "module_outline_fits_with_battery_reference": battery_fit,
                "module_height_mm": height,
                "module_height_fits_body": (
                    height <= body_thickness if height is not None else None
                ),
                "module_height_over_body_mm": (
                    round(max(0, height - body_thickness), 2)
                    if height is not None
                    else None
                ),
                "module_nominal_mass_g": mass,
                "module_minimum_mass_g": (
                    round(mass_min, 2) if mass_min is not None else None
                ),
                "device_mass_remaining_at_module_min_g": (
                    round(device_mass_ceiling - mass_min, 2)
                    if mass_min is not None
                    else None
                ),
                "detailed_datasheet_source": (
                    detailed["url"] if isinstance(detailed, dict) else None
                ),
                "detailed_datasheet_revision": (
                    detailed["revision"] if isinstance(detailed, dict) else None
                ),
                "detailed_datasheet_sha256": (
                    detailed["sha256"] if isinstance(detailed, dict) else None
                ),
                "published_power_lower_bound_w": published_lower_power,
                "published_power_lower_bound_basis": power_basis,
                "published_power_lower_bound_over_slate_w": (
                    round(published_lower_power - sustained_target, 2)
                    if published_lower_power is not None
                    else None
                ),
                "stock_power_modes_w": stock_modes,
                "minimum_stock_power_mode_w": stock_modes[0] if stock_modes else None,
                "minimum_stock_mode_over_slate_w": (
                    round(stock_modes[0] - sustained_target, 2) if stock_modes else None
                ),
                "stock_modes_source": stock_source,
                "source": reference["url"],
            }
        )
    matches = [item["id"] for item in rows if item["combined_public_fit"]]
    reviewed_x2 = [
        item
        for item in rows
        if item["id"].startswith("qualcomm_snapdragon_x2_")
        and item["observed_oem_memory_gb"] is not None
    ]
    if not reviewed_x2:
        raise ValueError("No reviewed X2 OEM memory configuration")
    largest_x2_oem = max(reviewed_x2, key=lambda item: item["observed_oem_memory_gb"])
    external_128gb_oem = [
        {
            "part": item["part"],
            "product": item["observed_oem_product"],
            "product_sku": item["observed_oem_product_sku"],
            "memory_gb": item["observed_oem_memory_gb"],
            "source": item["observed_oem_source"],
        }
        for item in rows
        if not item["integrated_phone_path"]
        and item["observed_oem_memory_gb"] is not None
        and item["observed_oem_memory_gb"] >= floor
    ]
    return {
        "status": "public_candidate_found" if matches else "supplier_proof_required",
        "memory_floor_gb": floor,
        "slate_body_face_mm": face,
        "slate_current_board_face_mm": board_face,
        "slate_internal_boundary_mm": list(boundary),
        "battery_reference_mm": list(battery),
        "slate_sustained_screen_w": sustained_target,
        "slate_external_thickness_mm": body_thickness,
        "slate_device_mass_ceiling_g": device_mass_ceiling,
        "integrated_phone_matches": matches,
        "largest_reviewed_x2_oem_memory_gb": largest_x2_oem["observed_oem_memory_gb"],
        "largest_reviewed_x2_oem_part": largest_x2_oem["part"],
        "remaining_to_memory_floor_gb": max(
            0, floor - largest_x2_oem["observed_oem_memory_gb"]
        ),
        "reviewed_external_128gb_oem_configurations": external_128gb_oem,
        "candidates": rows,
        "decision": (
            "The 128 GB floor is retained. X2 Elite and Plus publish controller "
            "capacity for it, but "
            f"{largest_x2_oem['observed_oem_product']} with "
            f"{largest_x2_oem['part']} has documented "
            f"{largest_x2_oem['observed_oem_memory_gb']} GB system memory, "
            f"{max(0, floor - largest_x2_oem['observed_oem_memory_gb'])} GB below "
            "Slate's floor. The reviewed ASUS X2 Extreme has "
            "48 GB on package; reviewed X2 Plus systems have 32 GB. "
            "A reviewed N1X laptop SKU is configured with 128 GB, but it does not "
            "establish a Slate compute package or phone integration. No reviewed "
            "public 128 GB X2 configuration or pocket phone integration is established. "
            "Obtain an orderable 128 GB package and supplier topology, "
            "power, software, and modem evidence before selection."
            if not matches
            else "A public capacity match is not a selected or qualified build platform."
        ),
        "caveat": "Published maximum memory and modem features do not prove a supported memory topology, purchasability, thermal fit, or a working phone.",
    }


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
