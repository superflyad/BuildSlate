# Routed PCB proof

There is no released v1R board. The [PCB floorplan](../../engineering/pcb/slate-pocket-v1r-floorplan/floorplan.yaml) is a placement plan, not copper, a stackup release, or a fabrication package. The [PCB auditor](../../buildslate/pcb_proof.py) is ready to run against a real KiCad project when selected parts, a reviewed schematic, and a routed board exist.

## Release input

Place `board.kicad_pcb`, `board.kicad_sch`, `board.kicad_pro`, and the released `board.xml` KiCad XML netlist in `engineering/hardware/released/`. They must share a basename. The schematic, netlist, and ERC report must each have separate approved records in [hardware readiness](../../engineering/hardware/readiness.yaml). The `routed_pcb` record must name the editable board and bind its SHA-256, `schematic_sha256`, `netlist_sha256`, and `project_sha256`, with a revision, reviewer, and approved disposition. Those hashes must agree with the actual files and approved upstream records; the project hash must also match the approved ERC record.

Run `python -m buildslate.pcb_proof board.kicad_pcb board.kicad_sch board.xml` with `kicad-cli` available. The readiness gate repeats this audit on the released files. The audit uses [KiCad's documented CLI](https://docs.kicad.org/9.0/en/cli/cli.html) to:

1. Export a fresh KiCad XML netlist and compare every component reference, footprint, value, and connected pin to the released electrical netlist.
2. Read the hashed project settings, reject DRC exclusions or ignored critical rules, and require positive fabrication design minima. Run PCB DRC with schematic parity, all violation severities, full track findings, and a nonzero exit on violations. Parse the JSON report and reject any rule violation, unconnected item, or schematic parity finding even if the tool returns success.
3. Read the board's configured layer table, then export every copper layer plus both masks and the board edge as separate Gerbers, along with Excellon drill data and assembly position CSV from the same board source. Missing or empty outputs reject the release. A multilayer board cannot pass with only front and back copper exports.

The audit reports the configured copper layer count, project settings hash, and hashes of the generated outputs. These exports are rebuilt during proof; the command does not store a manufacturing handoff archive. An engineer must review the stackup, layer mapping, fabrication notes, output alignment, and assembly package before procurement. The [synthetic 12-layer fault fixture](../../validation/validate_pcb_proof.py) checks missing internal copper Gerbers, DRC report findings, disabled rules, exclusions, zero design minima, and stale project bindings. It is not a v1R PCB or a claim that KiCad ran on a physical design.

This check establishes netlist currency, automated design-rule status, and basic manufacturing exportability. It does not prove power integrity, signal integrity, antenna performance, thermal behavior, fabrication yield, or a functioning phone. Those require design analysis, supplier review, and measured prototypes.
