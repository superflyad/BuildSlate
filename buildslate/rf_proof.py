"""Audit a selected EVT0 radio design and reproducible RF sweep evidence.

The result screens design data. It cannot replace chamber measurements,
coexistence tests, RF exposure review, or equipment authorization.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path

from buildslate.firmware_proof import RELEASE as FIRMWARE_RELEASE
from buildslate.io import load_yaml
from buildslate.netlist_proof import _netlist

RELEASE = Path("engineering/hardware/released/rf/rf-release.json")
PARTS = Path("engineering/hardware/released/rf/radio-parts.json")
SWEEPS = Path("engineering/hardware/released/rf/sweep-manifest.json")
COEXISTENCE = Path("engineering/hardware/released/rf/coexistence.csv")
BOARD = Path("engineering/hardware/released/board.kicad_pcb")
NETLIST = Path("engineering/hardware/released/board.xml")
ELECTRICAL_BOM = Path("engineering/hardware/released/board.bom.csv")
SELECTED_BOM = Path("engineering/hardware/released/selected-bom.json")
ASSEMBLY = Path("engineering/hardware/released/mechanical/assembly.step")
MECHANICAL_MANIFEST = Path(
    "engineering/hardware/released/mechanical/assembly.manifest.yaml"
)
MECHANICAL_PROOF = Path("viewer/public/mechanical-proof.json")
KEEP_OUT = Path("engineering/rf/keepout-map/map.yaml")
CONDITIONS = ("free_space", "handheld", "usb_cable", "wired_charging")
COEXISTENCE_CASES = (
    "wifi_bluetooth",
    "wifi_compute_memory_storage",
    "wifi_usb_cable",
    "wifi_wired_charging",
)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _text(value: object) -> bool:
    return (
        isinstance(value, str)
        and bool(value.strip())
        and value.strip().lower() not in {"unknown", "placeholder", "tbd"}
    )


def _number(value: object) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _file(
    root: Path,
    relative: object,
    digest: object,
    folder: str,
    suffixes: set[str] | None = None,
) -> Path | None:
    if not _text(relative) or not _text(digest):
        return None
    path = (root / relative).resolve()
    allowed = (root / "engineering/hardware/released/rf" / folder).resolve()
    if (
        not path.is_relative_to(allowed)
        or not path.is_file()
        or (
            folder == "sources"
            and path.suffix.lower() in {".md", ".yaml", ".yml", ".json"}
        )
        or (suffixes is not None and path.suffix.lower() not in suffixes)
        or _sha(path) != digest
    ):
        return None
    return path


def _sweep(path: Path, ports: int, marker: str) -> list[tuple[float, float]]:
    """Read the supported Touchstone 1.0 subset: MHz S RI R 50."""
    if path.stat().st_size > 10_000_000:
        raise ValueError("RF sweep exceeds 10 MB")
    values: list[tuple[float, float]] = []
    header = False
    lines = path.read_text(encoding="ascii").splitlines()
    if not lines or lines[0].strip() != marker:
        raise ValueError("RF sweep condition or antenna identity is missing")
    for raw in lines:
        line = raw.split("!", 1)[0].strip()
        if not line:
            continue
        if line.startswith("#"):
            if header or line.upper().split() != ["#", "MHZ", "S", "RI", "R", "50"]:
                raise ValueError("RF sweep needs # MHz S RI R 50")
            header = True
            continue
        if not header or line.startswith("["):
            raise ValueError("Unsupported RF sweep format")
        cells = line.split()
        if len(cells) != (3 if ports == 1 else 9):
            raise ValueError("RF sweep row has the wrong port count")
        numbers = [float(cell) for cell in cells]
        if not all(math.isfinite(item) for item in numbers):
            raise ValueError("RF sweep has nonfinite data")
        frequency = numbers[0]
        if frequency <= 0 or (values and frequency <= values[-1][0]):
            raise ValueError("RF sweep frequency is not increasing")
        index = (
            1 if ports == 1 else 3
        )  # Touchstone two-port order is S11, S21, S12, S22.
        magnitude = math.hypot(numbers[index], numbers[index + 1])
        if magnitude > 1.000001:
            raise ValueError("Passive RF sweep magnitude exceeds one")
        values.append((frequency, -20 * math.log10(max(magnitude, 1e-12))))
    if not header or not values:
        raise ValueError("RF sweep is empty or has no option line")
    return values


def _band_errors(
    samples: list[tuple[float, float]], band: dict, limit: str
) -> list[str]:
    start, end = band["start_mhz"], band["end_mhz"]
    inside = [
        (frequency, value) for frequency, value in samples if start <= frequency <= end
    ]
    if (
        len(inside) < 2
        or abs(inside[0][0] - start) > 1e-6
        or abs(inside[-1][0] - end) > 1e-6
        or any(
            second[0] - first[0] > band["max_step_mhz"] + 1e-6
            for first, second in zip(inside, inside[1:], strict=False)
        )
    ):
        return [f"Sweep does not cover band {band['id']} at the required step"]
    if min(value for _, value in inside) < band[limit]:
        return [f"Sweep misses {limit} for band {band['id']}"]
    return []


def _bom(path: Path) -> dict[str, str]:
    with path.open("r", encoding="utf-8-sig", newline="") as source:
        reader = csv.DictReader(source)
        if not reader.fieldnames or not {"ref", "manufacturer", "mpn"}.issubset(
            reader.fieldnames
        ):
            raise ValueError("Electrical BOM needs ref, manufacturer, and mpn")
        parts: dict[str, str] = {}
        for row in reader:
            ref, mpn = (row["ref"] or "").strip(), (row["mpn"] or "").strip()
            if not ref or ref in parts or not mpn:
                raise ValueError(
                    "Electrical BOM contains blank or duplicate part identity"
                )
            parts[ref] = mpn
        return parts


def _efficiency(
    path: Path, condition: str, antenna_id: str
) -> list[tuple[float, float]]:
    if path.stat().st_size > 10_000_000:
        raise ValueError("Radiation efficiency table exceeds 10 MB")
    with path.open("r", encoding="utf-8-sig", newline="") as source:
        reader = csv.DictReader(source)
        if not reader.fieldnames or set(reader.fieldnames) != {
            "condition",
            "antenna_id",
            "frequency_mhz",
            "efficiency_percent",
        }:
            raise ValueError("Radiation efficiency table has incomplete columns")
        values = []
        for row in reader:
            if row["condition"] != condition or row["antenna_id"] != antenna_id:
                raise ValueError("Radiation efficiency identity differs from sweep")
            frequency, efficiency = (
                float(row["frequency_mhz"]),
                float(row["efficiency_percent"]),
            )
            if (
                not math.isfinite(frequency)
                or not math.isfinite(efficiency)
                or frequency <= 0
                or not 0 <= efficiency <= 100
                or (values and frequency <= values[-1][0])
            ):
                raise ValueError("Radiation efficiency row is invalid")
            values.append((frequency, efficiency))
        if not values:
            raise ValueError("Radiation efficiency table is empty")
        return values


def audit(root: Path) -> dict:
    """Require selected radio parts, connected feeds, placement, and RF margins."""
    if not (root / RELEASE).is_file():
        return {"status": "missing", "errors": ["No released RF design"]}
    upstream = {
        "radio_parts_sha256": root / PARTS,
        "sweep_manifest_sha256": root / SWEEPS,
        "coexistence_sha256": root / COEXISTENCE,
        "routed_pcb_sha256": root / BOARD,
        "netlist_sha256": root / NETLIST,
        "electrical_bom_sha256": root / ELECTRICAL_BOM,
        "selected_bom_sha256": root / SELECTED_BOM,
        "firmware_bundle_sha256": root / FIRMWARE_RELEASE,
        "mechanical_assembly_sha256": root / ASSEMBLY,
        "mechanical_manifest_sha256": root / MECHANICAL_MANIFEST,
        "mechanical_proof_sha256": root / MECHANICAL_PROOF,
    }
    missing = [field for field, path in upstream.items() if not path.is_file()]
    if missing:
        return {
            "status": "fail",
            "errors": [f"Missing RF source: {field}" for field in missing],
        }
    try:
        release = json.loads((root / RELEASE).read_text(encoding="utf-8"))
        selected = json.loads((root / SELECTED_BOM).read_text(encoding="utf-8"))
        firmware = json.loads((root / FIRMWARE_RELEASE).read_text(encoding="utf-8"))
        parts = json.loads((root / PARTS).read_text(encoding="utf-8"))
        sweep_manifest = json.loads((root / SWEEPS).read_text(encoding="utf-8"))
        mechanical = json.loads((root / MECHANICAL_PROOF).read_text(encoding="utf-8"))
        manifest = load_yaml(root / MECHANICAL_MANIFEST)
        keepout = load_yaml(root / KEEP_OUT)
        bom = _bom(root / ELECTRICAL_BOM)
        _, net_pins = _netlist(root / NETLIST)
    except (
        OSError,
        UnicodeError,
        json.JSONDecodeError,
        ValueError,
        TypeError,
    ) as error:
        return {"status": "fail", "errors": [f"RF source cannot be read: {error}"]}
    if not all(
        isinstance(item, dict)
        for item in (
            release,
            parts,
            sweep_manifest,
            mechanical,
            manifest,
            keepout,
            selected,
            firmware,
        )
    ):
        return {"status": "fail", "errors": ["RF release inputs must be objects"]}
    errors: list[str] = []
    if (
        release.get("schema_version") != 1
        or release.get("device") != "slate-pocket-v1r"
    ):
        errors.append("Unknown RF release schema or device")
    for field in ("revision", "reviewed_by", "solver_name", "solver_version"):
        if not _text(release.get(field)):
            errors.append(f"Missing RF release {field}")
    for field, path in upstream.items():
        if release.get(field) != _sha(path):
            errors.append(f"RF release is not bound to {field}")
    if (
        release.get("cellular_enabled") is not False
        or release.get("uwb_enabled") is not False
        or release.get("wireless_charging_enabled") is not False
    ):
        errors.append("EVT0 deferred radios or wireless charging are enabled")
    if (
        mechanical.get("status") != "pass"
        or mechanical.get("assembly_sha256")
        != release.get("mechanical_assembly_sha256")
        or mechanical.get("manifest_sha256")
        != release.get("mechanical_manifest_sha256")
    ):
        errors.append("RF release lacks a passing mechanical proof for these bytes")
    if parts.get("schema_version") != 1 or parts.get("device") != "slate-pocket-v1r":
        errors.append("Unknown radio part set schema or device")
    module = parts.get("module")
    antennas = parts.get("antennas")
    if (
        not isinstance(module, dict)
        or not isinstance(antennas, list)
        or len(antennas) != 2
    ):
        return {
            "status": "fail",
            "errors": errors
            + ["EVT0 needs one Wi-Fi/Bluetooth module and two antennas"],
        }
    selected_parts = selected.get("parts")
    compute = (
        selected_parts.get("compute_platform")
        if isinstance(selected_parts, dict)
        else None
    )
    capabilities = compute.get("capabilities") if isinstance(compute, dict) else None
    host_interfaces = (
        capabilities.get("radio_interfaces") if isinstance(capabilities, dict) else None
    )
    if (
        not _text(module.get("host_interface"))
        or not isinstance(host_interfaces, list)
        or module["host_interface"] not in host_interfaces
    ):
        errors.append(
            "Selected compute platform does not support the radio host interface"
        )
    images = firmware.get("images")
    drivers = firmware.get("drivers")
    image_ids = (
        {
            item.get("id")
            for item in images
            if isinstance(item, dict) and _text(item.get("id"))
        }
        if isinstance(images, list)
        else set()
    )
    if (
        not _text(module.get("driver_image_id"))
        or module["driver_image_id"] not in image_ids
        or not isinstance(drivers, list)
        or not any(
            isinstance(item, dict)
            and item.get("role") == "antenna_modules"
            and item.get("image_id") == module["driver_image_id"]
            for item in drivers
        )
    ):
        errors.append("Selected radio has no matching firmware driver image")
    radio_kill = firmware.get("radio_kill")
    states = radio_kill.get("states") if isinstance(radio_kill, dict) else None
    if (
        not isinstance(radio_kill, dict)
        or radio_kill.get("image_id") not in image_ids
        or bom.get(radio_kill.get("hardware_ref")) is None
        or radio_kill.get("hardware_ref") == module.get("board_ref")
        or not _text(radio_kill.get("hardware_action"))
        or not isinstance(states, list)
        or any(not _text(state) for state in states)
        or set(states) != {"boot", "fault", "update", "suspend", "resume"}
    ):
        errors.append("Radio-kill control lacks firmware and hardware state coverage")
    if (
        not all(
            _text(module.get(field)) for field in ("manufacturer", "mpn", "board_ref")
        )
        or not isinstance(module.get("wifi_generation"), int)
        or module["wifi_generation"] < 7
        or not isinstance(module.get("bluetooth_major"), int)
        or module["bluetooth_major"] < 6
        or not _file(
            root, module.get("evidence_path"), module.get("evidence_sha256"), "sources"
        )
    ):
        errors.append(
            "Selected radio module identity or target capability is incomplete"
        )
    if bom.get(module.get("board_ref")) != module.get("mpn"):
        errors.append("Radio module differs from selected electrical BOM")
    mechanical_list = (
        mechanical.get("parts") if isinstance(mechanical.get("parts"), list) else []
    )
    manifest_list = (
        manifest.get("parts") if isinstance(manifest.get("parts"), list) else []
    )
    mechanical_parts = {
        item.get("id"): item
        for item in mechanical_list
        if isinstance(item, dict) and _text(item.get("id"))
    }
    manifest_parts = {
        item.get("id"): item
        for item in manifest_list
        if isinstance(item, dict) and _text(item.get("id"))
    }
    zones = keepout.get("antenna_reservations", {})
    if not isinstance(zones, dict):
        zones = {}
    ids: set[str] = set()
    antenna_by_id: dict[str, dict] = {}
    centers: list[tuple[float, float]] = []
    for antenna in antennas:
        if not isinstance(antenna, dict) or any(
            not _text(antenna.get(field))
            for field in (
                "id",
                "manufacturer",
                "mpn",
                "feed_ref",
                "feed_pin",
                "feed_mpn",
                "mechanical_part_id",
                "reservation",
            )
        ):
            errors.append("Antenna identity or feed is incomplete")
            continue
        identifier = antenna["id"]
        if (
            identifier in ids
            or antenna["reservation"] not in zones
            or not _file(
                root,
                antenna.get("evidence_path"),
                antenna.get("evidence_sha256"),
                "sources",
            )
        ):
            errors.append(
                f"Antenna identity, reservation, or supplier source is invalid: {identifier}"
            )
            continue
        ids.add(identifier)
        antenna_by_id[identifier] = antenna
        part = mechanical_parts.get(antenna["mechanical_part_id"])
        source_part = manifest_parts.get(antenna["mechanical_part_id"])
        if (
            not isinstance(part, dict)
            or not isinstance(source_part, dict)
            or source_part.get("part_number") != antenna["mpn"]
            or "antenna_modules" not in part.get("roles", [])
        ):
            errors.append(
                f"Antenna has no matching released mechanical part: {identifier}"
            )
            continue
        bounds = part.get("bounds_mm")
        zone = zones[antenna["reservation"]]["rectangle_mm"]
        if (
            not isinstance(bounds, list)
            or len(bounds) != 6
            or any(not _number(value) for value in bounds)
        ):
            errors.append(f"Antenna has invalid released bounds: {identifier}")
            continue
        x0, y0, _, x1, y1, _ = bounds
        if (
            x0 < zone["x"]
            or y0 < zone["y"]
            or x1 > zone["x"] + zone["length"]
            or y1 > zone["y"] + zone["width"]
        ):
            errors.append(f"Antenna leaves its reserved edge zone: {identifier}")
        centers.append(((x0 + x1) / 2, (y0 + y1) / 2))
        if bom.get(antenna["feed_ref"]) != antenna.get("feed_mpn"):
            errors.append(
                f"Antenna feed connector differs from electrical BOM: {identifier}"
            )
        path = antenna.get("rf_path")
        matching = antenna.get("matching_parts")
        if (
            not isinstance(path, list)
            or len(path) < 4
            or not isinstance(matching, dict)
            or not matching
        ):
            errors.append(f"Antenna has no connected matching path: {identifier}")
            continue
        endpoints = []
        for point in path:
            if (
                not isinstance(point, dict)
                or not _text(point.get("ref"))
                or not _text(point.get("pin"))
            ):
                errors.append(f"Malformed RF path endpoint: {identifier}")
                break
            endpoints.append((point["ref"], point["pin"]))
        if (
            len(endpoints) != len(path)
            or len(set(endpoints)) != len(endpoints)
            or endpoints[0][0] != module.get("board_ref")
            or endpoints[-1] != (antenna["feed_ref"], antenna["feed_pin"])
        ):
            errors.append(f"RF path endpoints or order are invalid: {identifier}")
            continue
        if any(bom.get(ref) != mpn for ref, mpn in matching.items()) or not set(
            matching
        ).issubset({ref for ref, _ in endpoints}):
            errors.append(f"RF matching parts differ from electrical BOM: {identifier}")
        used_matching: set[str] = set()
        for first, second in zip(endpoints, endpoints[1:], strict=False):
            if (
                first not in net_pins
                or second not in net_pins
                or (first[0] != second[0] and net_pins[first] != net_pins[second])
                or (
                    first[0] == second[0]
                    and (first[0] not in matching or first[1] == second[1])
                )
            ):
                errors.append(f"RF feed path is disconnected: {identifier}")
                break
            if first[0] == second[0]:
                used_matching.add(first[0])
        if used_matching != set(matching):
            errors.append(f"RF matching path omits a selected part: {identifier}")
    separation = release.get("minimum_antenna_separation_mm")
    if (
        not _number(separation)
        or separation <= 0
        or not _file(
            root,
            release.get("separation_evidence_path"),
            release.get("separation_evidence_sha256"),
            "sources",
        )
    ):
        errors.append("Antenna separation requirement lacks a supplier source")
    elif (
        len(centers) == 2
        and (centers[0][0] - centers[1][0]) ** 2 + (centers[0][1] - centers[1][1]) ** 2
        < separation**2
    ):
        errors.append("Antenna centers miss the selected separation requirement")
    bands = sweep_manifest.get("bands")
    sweeps = sweep_manifest.get("sweeps")
    isolation = sweep_manifest.get("isolation")
    if (
        sweep_manifest.get("schema_version") != 1
        or not isinstance(bands, list)
        or not bands
        or not isinstance(sweeps, list)
        or not isinstance(isolation, list)
    ):
        return {
            "status": "fail",
            "errors": errors + ["RF sweep manifest is incomplete"],
        }
    band_by_id: dict[str, dict] = {}
    for band in bands:
        if (
            not isinstance(band, dict)
            or not _text(band.get("id"))
            or band["id"] in band_by_id
            or any(
                not _number(band.get(field))
                for field in (
                    "start_mhz",
                    "end_mhz",
                    "max_step_mhz",
                    "min_return_loss_db",
                    "min_isolation_db",
                    "min_efficiency_percent",
                    "max_desense_db",
                )
            )
            or not _file(
                root, band.get("evidence_path"), band.get("evidence_sha256"), "sources"
            )
        ):
            errors.append("RF band or supplier acceptance source is invalid")
            continue
        if not (
            0 < band["start_mhz"] < band["end_mhz"]
            and 0 < band["max_step_mhz"] <= band["end_mhz"] - band["start_mhz"]
            and band["min_return_loss_db"] > 0
            and band["min_isolation_db"] > 0
            and 0 < band["min_efficiency_percent"] <= 100
            and band["max_desense_db"] >= 0
        ):
            errors.append(f"RF band limits are invalid: {band['id']}")
            continue
        band_by_id[band["id"]] = band
    if (
        not isinstance(module.get("band_ids"), list)
        or any(not _text(value) for value in module["band_ids"])
        or set(module["band_ids"]) != set(band_by_id)
    ):
        errors.append("Selected radio module bands differ from release scope")
    markets = release.get("markets")
    if not isinstance(markets, list) or not markets:
        errors.append("RF release has no selected market and lab plan")
    else:
        covered: set[str] = set()
        seen_markets: set[str] = set()
        for market in markets:
            if (
                not isinstance(market, dict)
                or not _text(market.get("id"))
                or market["id"] in seen_markets
                or not isinstance(market.get("band_ids"), list)
                or not market["band_ids"]
                or not _file(
                    root,
                    market.get("lab_plan_path"),
                    market.get("lab_plan_sha256"),
                    "sources",
                )
            ):
                errors.append("RF market or lab scope is incomplete")
                continue
            seen_markets.add(market["id"])
            if any(not _text(band_id) for band_id in market["band_ids"]):
                errors.append("RF market has an invalid band identifier")
            else:
                covered.update(market["band_ids"])
        if covered != set(band_by_id):
            errors.append("RF market scope and selected bands differ")
    expected_sweeps = {
        (antenna_id, condition)
        for antenna_id in antenna_by_id
        for condition in CONDITIONS
    }
    seen_sweeps: set[tuple[str, str]] = set()
    for item in sweeps:
        if (
            not isinstance(item, dict)
            or not _text(item.get("antenna_id"))
            or not _text(item.get("condition"))
        ):
            errors.append("Malformed RF antenna sweep")
            continue
        key = item["antenna_id"], item["condition"]
        if key not in expected_sweeps or key in seen_sweeps:
            errors.append(f"Unknown or duplicate RF antenna sweep: {key}")
            continue
        seen_sweeps.add(key)
        path = _file(root, item.get("path"), item.get("sha256"), "sweeps", {".s1p"})
        efficiency_path = _file(
            root,
            item.get("efficiency_path"),
            item.get("efficiency_sha256"),
            "sweeps",
            {".csv"},
        )
        if path is None or efficiency_path is None:
            errors.append(f"RF sweep file or efficiency coverage is incomplete: {key}")
            continue
        try:
            samples = _sweep(
                path, 1, f"! buildslate condition={key[1]} antenna={key[0]}"
            )
            efficiency = _efficiency(efficiency_path, key[1], key[0])
        except (OSError, UnicodeError, ValueError) as error:
            errors.append(f"Invalid antenna sweep {key}: {error}")
            continue
        for band in band_by_id.values():
            errors.extend(_band_errors(samples, band, "min_return_loss_db"))
            errors.extend(_band_errors(efficiency, band, "min_efficiency_percent"))
    if seen_sweeps != expected_sweeps:
        errors.append("RF antenna and use-condition sweep coverage is incomplete")
    seen_isolation: set[str] = set()
    for item in isolation:
        if (
            not isinstance(item, dict)
            or item.get("condition") not in CONDITIONS
            or item["condition"] in seen_isolation
        ):
            errors.append("Unknown or duplicate RF isolation condition")
            continue
        seen_isolation.add(item["condition"])
        antenna_ids = item.get("antenna_ids")
        if (
            not isinstance(antenna_ids, list)
            or any(not _text(value) for value in antenna_ids)
            or set(antenna_ids) != set(antenna_by_id)
        ):
            errors.append("RF isolation ports do not match selected antennas")
        path = _file(root, item.get("path"), item.get("sha256"), "sweeps", {".s2p"})
        if path is None:
            errors.append("RF isolation sweep is missing or stale")
            continue
        try:
            pair = ",".join(item["antenna_ids"])
            samples = _sweep(
                path, 2, f"! buildslate condition={item['condition']} antennas={pair}"
            )
        except (OSError, UnicodeError, ValueError) as error:
            errors.append(f"Invalid RF isolation sweep: {error}")
            continue
        for band in band_by_id.values():
            errors.extend(_band_errors(samples, band, "min_isolation_db"))
    if seen_isolation != set(CONDITIONS):
        errors.append("RF isolation use-condition coverage is incomplete")
    with (root / COEXISTENCE).open("r", encoding="utf-8-sig", newline="") as source:
        reader = csv.DictReader(source)
        if not reader.fieldnames or set(reader.fieldnames) != {
            "scenario",
            "band_id",
            "desense_db",
        }:
            errors.append("RF coexistence table has incomplete columns")
        else:
            seen_coexistence: set[tuple[str, str]] = set()
            for row in reader:
                key = row["scenario"], row["band_id"]
                if (
                    key in seen_coexistence
                    or key[0] not in COEXISTENCE_CASES
                    or key[1] not in band_by_id
                ):
                    errors.append("RF coexistence case is unknown or duplicated")
                    continue
                seen_coexistence.add(key)
                try:
                    desense = float(row["desense_db"])
                except (TypeError, ValueError):
                    errors.append(f"RF coexistence result is invalid: {key}")
                    continue
                if (
                    not math.isfinite(desense)
                    or desense < 0
                    or desense > band_by_id[key[1]]["max_desense_db"]
                ):
                    errors.append(f"RF coexistence misses supplier limit: {key}")
            expected_coexistence = {
                (scenario, band_id)
                for scenario in COEXISTENCE_CASES
                for band_id in band_by_id
            }
            if seen_coexistence != expected_coexistence:
                errors.append("RF coexistence case coverage is incomplete")
    return {
        "status": "pass" if not errors else "fail",
        "source": RELEASE.as_posix(),
        "revision": release.get("revision"),
        "reviewed_by": release.get("reviewed_by"),
        **{field: release.get(field) for field in upstream},
        "antennas_checked": len(antenna_by_id),
        "bands_checked": len(band_by_id),
        "conditions_checked": len(seen_sweeps),
        "errors": errors,
        "caveat": "Nominal feed connectivity, CAD placement, and simulated RF sweep margins do not prove radiated performance, coexistence, exposure, compliance, or working radios.",
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
