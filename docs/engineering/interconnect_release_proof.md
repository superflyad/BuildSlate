# Interconnect release proof

The present [assembly model](../../cad/slate-pocket-v1r/concept-cad/README.md) contains assumed volumes. It does not define buildable connector pinouts, flexes, coax, or harnesses. The `interconnect` entry in the [hardware gate](../../engineering/hardware/readiness.yaml) needs an actual release, not a drawing filename or a review flag.

## Released input

Place `engineering/hardware/released/interconnect/interconnect.json` under revision control. It must identify `schema_version: 1`, `device: slate-pocket-v1r`, `revision`, and `reviewed_by`. Bind the exact SHA-256 bytes of the selected BOM, exported KiCad XML netlist, electrical BOM, routed KiCad board, and released mechanical assembly STEP. The [auditor](../../buildslate/interconnect_proof.py) rejects missing or changed upstream files.

The `interfaces` array must provide contacts for the functional roles `display`, `touch`, `rear_camera`, `front_camera`, `usb`, `battery`, `antenna_main`, `antenna_diversity`, `audio_output`, `audio_input`, `haptic`, `power_button`, and `service_debug`. A contact names its `role`, `board_pin`, and `device_pin`. One physical path may carry several roles when a connector is shared. Each path has a unique `id`, a `medium` (`board`, `flex`, `coax`, or `harness`), a `board_ref`, and a distinct `device_ref`. The refs and pins must exist in the exported netlist; every mapped pair must share the same net. Duplicate or crossed contacts fail, and every required role must have at least one passing contact. For a flex, coax, or harness, the map must cover all connected pins on both named connector refs. It must also include a `drawing` with a controlled path and SHA-256 under `engineering/hardware/released/interconnect/sources/`. A planning Markdown, YAML, or JSON file cannot stand in for that drawing.

The readiness record for `interconnect` must point to the release JSON and bind its exact hash, revision, reviewer, and approved disposition. The gate reruns the technical audit and requires approved upstream records with matching selected BOM, netlist, electrical BOM, routed board, and assembly hashes. Run it directly with:

```bash
python -m buildslate.interconnect_proof --repo-root .
```

The [synthetic fault fixture](../../validation/validate_interconnect_proof.py) verifies rejection of crossed contacts, missing pins, stale drawings, a changed board, and an interconnect record tied to a different approved board. It is not a Slate Pocket design.

## Limits

This proves that the declared pin map is internally consistent with a released electrical netlist and that reviewed drawings and upstream bytes have not changed. The auditor cannot establish that a supplier connector is rated for the current and voltage, that a flex bend or route clears the enclosure, that high-speed signals meet integrity limits, or that a built unit functions. Those require supplier review, mechanical and electrical analysis, and physical EVT0 measurements. No v1R interconnect package has been released, so the [public Hardware view](https://superflyad.github.io/BuildSlate/?tab=hardware) reports it as missing.
