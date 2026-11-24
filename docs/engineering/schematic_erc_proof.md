# Schematic ERC release proof

There is no released Slate Pocket schematic or ERC report. The [hardware readiness gate](build_to_function.md) requires a fresh KiCad electrical rules check before it accepts an `erc_report` record. A PDF or a manually written result cannot satisfy this requirement.

## Release files

Place `board.kicad_sch`, `board.kicad_pro`, and `board.erc.json` under `engineering/hardware/released/`. The `schematic_source` record binds the editable schematic. The `erc_report` record binds the reviewed JSON report and carries `schematic_sha256` and `project_sha256` for the exact source and project settings, plus the report's own SHA-256, revision, reviewer, and approved disposition. The schematic record must be approved and name the same source bytes.

The [ERC auditor](../../buildslate/erc_proof.py) rejects project exclusions and requires critical connection, power, annotation, and dangling-wire rule severities to be enabled. It then runs KiCad's [documented `sch erc` command](https://docs.kicad.org/9.0/en/cli/cli.html#schematic-erc) with JSON output, all severities, millimeter units, and a nonzero exit for violations. The generated report must have schematic sheets and zero findings. Its KiCad version, units, and sheet results must match the reviewed report; generation timestamps and source directory names may differ.

```bash
python -m buildslate.erc_proof engineering/hardware/released/board.kicad_sch engineering/hardware/released/board.erc.json
python validation/validate_erc_proof.py
buildslate hardware --require-design-release
```

The [fault fixture](../../validation/validate_erc_proof.py) checks a failed KiCad command, warning finding, missing fresh output, stale reviewed report, ERC exclusion, disabled critical rule, and stale schematic or project binding. The fixture uses synthetic KiCad output and is not a Slate Pocket circuit.

ERC checks the schematic against its configured rule set. A clean result does not establish rail voltage or current margin, power sequencing, component compatibility, signal integrity, board routing, thermal behavior, or a working device. The [netlist proof](electrical_netlist_proof.md), [routed PCB proof](routed_pcb_proof.md), engineering review, and serialized EVT0 measurements remain separate requirements.
