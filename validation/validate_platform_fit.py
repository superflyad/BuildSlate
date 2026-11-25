"""Keep the public platform decision tied to published capacity limits."""

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from buildslate.platform_fit import CANDIDATES, PROFILE, audit  # noqa: E402


def _write(root: Path, profile: dict, candidates: dict) -> None:
    for name, data in ((PROFILE, profile), (CANDIDATES, candidates)):
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")


def _must_fail(root: Path) -> None:
    try:
        audit(root)
    except ValueError:
        return
    raise ValueError("Invalid platform input passed")


def main() -> int:
    report = audit(ROOT)
    if (
        report["status"] != "supplier_proof_required"
        or report["memory_floor_gb"] != 128
        or report["integrated_phone_matches"]
        or len(report["candidates"]) != 11
        or report["largest_reviewed_x2_oem_memory_gb"] != 64
        or report["largest_reviewed_x2_oem_part"] != "X2E-90-100"
        or report["remaining_to_memory_floor_gb"] != 64
    ):
        raise ValueError("Current 128 GB phone platform gap is misstated")
    mobile = [item for item in report["candidates"] if item["integrated_phone_path"]]
    if len(mobile) != 3 or any(
        item["public_maximum_memory_gb"] != 24 for item in mobile
    ):
        raise ValueError("Published mobile memory ceilings changed unexpectedly")
    if any(item["combined_public_fit"] for item in report["candidates"]):
        raise ValueError("An unproven platform was credited with full phone fit")
    x2 = next(
        item
        for item in report["candidates"]
        if item["id"] == "qualcomm_snapdragon_x2_elite_extreme"
    )
    if not x2["published_capacity_permits_floor"] or x2["public_128gb_configuration"]:
        raise ValueError("X2 public maximum was promoted to a 128 GB build")
    if (
        x2["observed_oem_memory_gb"] != 48
        or x2["observed_oem_memory_placement"] != "memory_on_package"
        or not x2["observed_oem_source"]
        or not x2["physical_package_source"]
    ):
        raise ValueError("Observed ASUS X2 package evidence is absent")
    elite90 = next(
        item
        for item in report["candidates"]
        if item["id"] == "qualcomm_snapdragon_x2_elite_90"
    )
    if (
        elite90["public_maximum_memory_gb"] != 128
        or elite90["public_memory_bus_width_bits"] != 128
        or elite90["observed_oem_memory_gb"] != 64
        or elite90["observed_oem_memory_placement"] != "unspecified"
        or elite90["observed_oem_board_spare_part"] != "P84650-601"
        or not elite90["observed_oem_service_source"]
        or elite90["public_128gb_configuration"]
        or elite90["combined_public_fit"]
    ):
        raise ValueError("HP 64 GB system board was promoted to a 128 GB platform")
    n1x = next(
        item
        for item in report["candidates"]
        if item["id"] == "nvidia_rtx_spark_n1x_128gb_reference"
    )
    references = report["reviewed_external_128gb_oem_configurations"]
    if (
        n1x["observed_oem_product_sku"] != "H7407BA-XB99T"
        or n1x["observed_oem_memory_gb"] != 128
        or n1x["observed_oem_memory_placement"] != "board_soldered"
        or not n1x["public_128gb_configuration"]
        or n1x["integrated_phone_path"]
        or n1x["combined_public_fit"]
        or len(references) != 1
        or references[0]["product_sku"] != "H7407BA-XB99T"
        or references[0]["memory_gb"] != 128
    ):
        raise ValueError(
            "128 GB N1X laptop reference was mistaken for Slate phone proof"
        )
    plus = {
        item["id"]: item
        for item in report["candidates"]
        if item["id"].startswith("qualcomm_snapdragon_x2_plus_")
    }
    if set(plus) != {
        "qualcomm_snapdragon_x2_plus_10_core",
        "qualcomm_snapdragon_x2_plus_6_core",
    } or any(
        item["public_maximum_memory_gb"] != 128
        or item["public_memory_bus_width_bits"] != 128
        or item["public_128gb_configuration"]
        or item["observed_oem_memory_gb"] != 32
        or not item["observed_oem_source"]
        or item["physical_package_source"] is not None
        or item["integrated_phone_path"]
        or item["minimum_published_power_mode_w"] is not None
        for item in plus.values()
    ):
        raise ValueError("X2 Plus controller maximum was promoted to a build")
    if (
        plus["qualcomm_snapdragon_x2_plus_10_core"]["cpu_cores"] != 10
        or plus["qualcomm_snapdragon_x2_plus_6_core"]["cpu_cores"] != 6
        or plus["qualcomm_snapdragon_x2_plus_10_core"]["observed_oem_product_sku"]
        != "DZ1U2UA#ABA"
        or plus["qualcomm_snapdragon_x2_plus_10_core"]["observed_oem_memory_placement"]
        != "unspecified"
        or plus["qualcomm_snapdragon_x2_plus_6_core"]["observed_oem_memory_placement"]
        != "board_soldered"
    ):
        raise ValueError("X2 Plus platform identities changed")
    congatec = next(
        item
        for item in report["candidates"]
        if item["id"] == "congatec_conga_hpc_crx1_x199_128g"
    )
    if (
        not congatec["public_128gb_configuration"]
        or congatec["module_outline_fits_body_face"] is not False
        or congatec["minimum_published_mode_over_slate_w"] != 17
        or congatec["combined_public_fit"]
    ):
        raise ValueError("Cataloged 128 GB module was credited with Slate fit")
    thor = next(
        item for item in report["candidates"] if item["id"] == "nvidia_jetson_agx_thor"
    )
    if (
        thor["module_outline_fits_body_face"] is not True
        or thor["minimum_published_mode_over_slate_w"] != 12
    ):
        raise ValueError("Jetson module outline or power screen changed")
    committed = json.loads(
        (ROOT / "viewer/public/hardware-readiness.json").read_text(encoding="utf-8")
    )
    if committed["platform_fit"] != report:
        raise ValueError("Published platform decision is stale")
    profile = yaml.safe_load((ROOT / PROFILE).read_text(encoding="utf-8"))
    candidates = yaml.safe_load((ROOT / CANDIDATES).read_text(encoding="utf-8"))
    with TemporaryDirectory() as temporary:
        root = Path(temporary)
        altered = copy.deepcopy(candidates)
        altered["candidates"]["nvidia_rtx_spark_n1x_128gb_reference"][
            "observed_oem_configuration"
        ]["memory_gb"] = 64
        _write(root, profile, altered)
        if audit(root)["reviewed_external_128gb_oem_configurations"]:
            raise ValueError("Reduced N1X laptop memory still counts as 128 GB")
        altered = copy.deepcopy(candidates)
        altered["candidates"]["qualcomm_snapdragon_x2_elite_90"][
            "observed_oem_configuration"
        ]["service_source"] = None
        _write(root, profile, altered)
        _must_fail(root)
        altered = copy.deepcopy(candidates)
        altered["candidates"]["qualcomm_snapdragon_x2_plus_6_core"][
            "observed_oem_configuration"
        ]["platform_part"] = "X2P-64-100"
        _write(root, profile, altered)
        _must_fail(root)
        altered = copy.deepcopy(candidates)
        altered["candidates"]["qualcomm_snapdragon_x2_plus_10_core"][
            "physical_package_observation"
        ] = {"dram_package_count": 4}
        _write(root, profile, altered)
        _must_fail(root)
        altered = copy.deepcopy(candidates)
        altered["candidates"]["congatec_conga_hpc_crx1_x199_128g"][
            "module_outline_mm"
        ] = [160, 0]
        _write(root, profile, altered)
        _must_fail(root)
        widened = copy.deepcopy(profile)
        widened["geometry"]["width_mm"] = 120
        _write(root, widened, candidates)
        widened_screen = audit(root)
        widened_module = next(
            item
            for item in widened_screen["candidates"]
            if item["id"] == "congatec_conga_hpc_crx1_x199_128g"
        )
        if widened_module["module_outline_fits_body_face"] is not True:
            raise ValueError("Module outline did not respond to changed body geometry")
        altered = copy.deepcopy(candidates)
        altered["candidates"]["qualcomm_snapdragon_x2_elite_extreme"][
            "physical_package_observation"
        ]["dram_package_count"] = 4
        _write(root, profile, altered)
        _must_fail(root)
        altered = copy.deepcopy(candidates)
        altered["candidates"]["qualcomm_snapdragon_8_elite_gen_6"][
            "maximum_memory_gb"
        ] = 128
        _write(root, profile, altered)
        changed = audit(root)
        if changed["integrated_phone_matches"] != ["qualcomm_snapdragon_8_elite_gen_6"]:
            raise ValueError("Candidate capacity change did not affect the decision")
        altered["candidates"]["qualcomm_snapdragon_8_elite_gen_6"][
            "modem_integration"
        ] = "unknown"
        _write(root, profile, altered)
        _must_fail(root)
        altered = copy.deepcopy(candidates)
        altered["candidates"]["qualcomm_snapdragon_8_elite_gen_6"].pop(
            "maximum_memory_gb"
        )
        _write(root, profile, altered)
        _must_fail(root)
        altered_profile = copy.deepcopy(profile)
        altered_profile["integration_configuration"]["memory_gb"] = 24
        _write(root, altered_profile, candidates)
        _must_fail(root)
    print("PASS: public platform capacity and phone integration decision")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
