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
        or len(report["candidates"]) != 6
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
