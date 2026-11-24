# Routed PCB proof

There is no released v1R board. The [PCB floorplan](../../engineering/pcb/slate-pocket-v1r-floorplan/floorplan.yaml) is a placement plan, not copper, a stackup release, or a fabrication package. The [PCB auditor](../../buildslate/pcb_proof.py) is ready to run against a real KiCad project when selected parts, a reviewed schematic, and a routed board exist.

## Release input

Place `board.kicad_pcb`, `board.kicad_sch`, and the released `board.xml` KiCad XML netlist in `engineering/hardware/released/`. They must share a basename. The schematic and netlist must each have separate approved records in [hardware readiness](../../engineering/hardware/readiness.yaml). The `routed_pcb` record must name the editable board and bind its SHA-256, `schematic_sha256`, and `netlist_sha256`, with a revision, reviewer, and approved disposition. The latter hashes must agree with the approved upstream records and actual files.

Run `python -m buildslate.pcb_proof board.kicad_pcb board.kicad_sch board.xml` with `kicad-cli` available. The readiness gate repeats this audit on the released files. The audit uses [KiCad's documented CLI](https://docs.kicad.org/9.0/en/cli/cli.html) to:

1. Export a fresh KiCad XML netlist and compare every component reference, footprint, value, and connected pin to the released electrical netlist.
2. Run PCB DRC with schematic parity, all violation severities, and a nonzero exit on violations. A failed command or missing JSON report rejects the board.
3. Read the board's configured layer table, then export every copper layer plus both masks and the board edge as separate Gerbers, along with Excellon drill data and assembly position CSV from the same board source. Missing or empty outputs reject the release. A multilayer board cannot pass with only front and back copper exports.

The audit reports the configured copper layer count and hashes of the generated outputs. These exports are rebuilt during proof; the command does not store a manufacturing handoff archive. An engineer must review the stackup, layer mapping, fabrication notes, output alignment, and assembly package before procurement. The [synthetic 12-layer fault fixture](../../validation/validate_pcb_proof.py) checks that a missing internal copper Gerber fails; it is not a v1R PCB or a claim that KiCad ran on a physical design.

This check establishes netlist currency, automated design-rule status, and basic manufacturing exportability. It does not prove power integrity, signal integrity, antenna performance, thermal behavior, fabrication yield, or a functioning phone. Those require design analysis, supplier review, and measured prototypes.
