# Electrical netlist proof

The [power tree](../../engineering/pcb/power-tree.yaml) and [PCB floorplan](../../engineering/pcb/slate-pocket-v1r-floorplan/floorplan.yaml) are planning inputs. Neither describes a connected circuit. The [netlist auditor](../../buildslate/netlist_proof.py) is prepared for a released electrical package; there is no v1R netlist to audit yet.

## Input contract

Export the selected schematic as **KiCad XML** (`kicadxml`) using [KiCad's documented CLI](https://docs.kicad.org/9.0/en/cli/cli.html#schematic-netlist-export). An XML file named `board.xml` must have two sibling files in `engineering/hardware/released/`:

- `board.contract.yaml` — `schema_version: 1`, `device: slate-pocket-v1r`, component `roles` mapped to exported references, ten required `connections`, and one required `isolation`. Each connection has an `id` and exactly two `{ref, pin}` endpoints. Required IDs and endpoint roles are fixed in the auditor so an empty contract or a connection between unrelated parts cannot pass.
- `board.bom.csv` — one row for every exported component reference, with `ref`, `manufacturer`, and `mpn` columns. Blank or placeholder part identities are rejected.

Use `python -m buildslate.netlist_proof board.xml board.contract.yaml board.bom.csv` to check the package. The audit parses the actual exported node membership, rejects duplicate components, net names, or pin assignments, and verifies each declared critical connection or isolation against the netlist. It also reconciles the electrical BOM to the exported component references. A failed check exits nonzero and names the affected path.

The `schematic_netlist` evidence record in [hardware readiness](../../engineering/hardware/readiness.yaml) must bind the XML, contract, and BOM with `sha256`, `contract_sha256`, and `bom_sha256`, plus revision, reviewer, and approved disposition. The build-to-function gate runs the electrical auditor again on those exact bytes; a hash mismatch or failed technical check rejects the record. The separate `schematic_source` record requires the editable KiCad schematic, and `erc_report` requires a reviewed electrical rules report and deviations.

## What this proves

The audit establishes that the named pins share or do not share nets as required and that each listed electrical component has a selected part identity. It does **not** establish rail voltage compatibility, current capacity, protection behavior, timing, signal integrity, routed PCB parity, firmware support, or physical function. KiCad ERC, PCB DRC, supplier design review, and energized measurements are additional release and EVT0 evidence. The [synthetic fault fixture](../../validation/validate_netlist_proof.py) checks that missing endpoints, incomplete contracts, and mismatched bundle hashes fail closed; its fixture is not a v1R schematic.
