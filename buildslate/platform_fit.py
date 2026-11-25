"""Screen public compute limits against Slate's approved memory and phone needs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from buildslate.io import load_yaml

PROFILE = Path("configs/devices/slate-pocket-v1r.yaml")
CANDIDATES = Path("research/evidence/compute/platform-comparison.yaml")
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


def audit(root: Path) -> dict:
    profile = load_yaml(root / PROFILE)
    source = load_yaml(root / CANDIDATES)
    floor = profile["decision_baseline"]["locked_trade_rules"]["memory"][
        "fallback_tiers_gb"
    ][-1]
    configured = profile["integration_configuration"]["memory_gb"]
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
        observed = candidate.get("observed_oem_configuration")
        physical = candidate.get("physical_package_observation")
        if (observed is None) != (physical is None):
            raise ValueError(
                f"{identifier}: OEM and package observations must be paired"
            )
        observed_memory = None
        observed_source = None
        physical_source = None
        if observed is not None:
            if not isinstance(observed, dict) or not isinstance(physical, dict):
                raise ValueError(f"{identifier}: malformed OEM package observation")
            observed_memory = observed.get("memory_gb")
            observed_record = observed.get("source")
            physical_record = physical.get("source")
            observed_source = (
                observed_record.get("url")
                if isinstance(observed_record, dict)
                else None
            )
            physical_source = (
                physical_record.get("url")
                if isinstance(physical_record, dict)
                else None
            )
            package_count = physical.get("dram_package_count")
            package_capacity = physical.get("capacity_gb_per_package")
            if (
                not isinstance(observed_memory, int)
                or isinstance(observed_memory, bool)
                or observed_memory <= 0
                or observed_memory > maximum
                or observed.get("platform_part") != candidate.get("representative_part")
                or observed.get("placement") != "memory_on_package"
                or physical.get("placement") != "co_packaged_with_soc"
                or not isinstance(package_count, int)
                or isinstance(package_count, bool)
                or package_count <= 0
                or not isinstance(package_capacity, int)
                or isinstance(package_capacity, bool)
                or package_capacity <= 0
                or package_count * package_capacity != observed_memory
                or not isinstance(observed_source, str)
                or not observed_source.startswith("https://")
                or not isinstance(physical_source, str)
                or not physical_source.startswith("https://")
            ):
                raise ValueError(f"{identifier}: OEM package evidence is inconsistent")
        rows.append(
            {
                "id": identifier,
                "part": candidate.get(
                    "part_numbers", [candidate.get("representative_part")]
                )[0],
                "platform_class": candidate.get("platform_class"),
                "public_maximum_memory_gb": maximum,
                "public_configured_memory_gb": configured,
                "observed_oem_memory_gb": observed_memory,
                "observed_oem_memory_placement": (
                    observed["placement"] if observed is not None else None
                ),
                "observed_oem_source": observed_source,
                "physical_package_source": physical_source,
                "published_capacity_permits_floor": capacity_permits_floor,
                "integrated_phone_path": phone_integration,
                "combined_public_fit": capacity_permits_floor and phone_integration,
                "public_128gb_configuration": any(
                    value is not None and value >= floor
                    for value in (configured, observed_memory)
                ),
                "source": reference["url"],
            }
        )
    matches = [item["id"] for item in rows if item["combined_public_fit"]]
    return {
        "status": "public_candidate_found" if matches else "supplier_proof_required",
        "memory_floor_gb": floor,
        "integrated_phone_matches": matches,
        "candidates": rows,
        "decision": (
            "The 128 GB floor is retained. X2 publishes controller capacity for it, "
            "but the reviewed ASUS X2 system has 48 GB on package, with three "
            "16 GB DRAM packages observed in physical analysis. No reviewed public 128 GB "
            "X2 configuration or pocket phone integration is established. "
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
