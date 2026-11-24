# Design decisions

## ADR-001: Keep evidence status in the existing registries

**Status:** Accepted

The viewer reads generated status and part provenance. It does not assign verified, selected, or released status. This prevents a visually complete model from being mistaken for an approved design.

## ADR-002: Generate provisional geometry from controlled inputs

**Status:** Accepted

The first 3D model uses the existing mechanical and PCB planning rectangles. A small assembly manifest supplies the missing names and z positions. The generator exports JSON for inspection and glTF for geometry. All current solids remain explicitly provisional.

## ADR-003: Keep the browser interface read only

**Status:** Accepted

The viewer can filter, inspect, hide, explode, and rotate the assembly. It cannot alter device profiles, evidence, or decisions. Engineering changes go through the repository's validated source files and regeneration flow.

## ADR-004: Treat the viewer as a local static application

**Status:** Accepted

Vite produces a static build with no server-side account or database. This keeps the engineering data reviewable from a checkout. The Python generator owns asset currency; the web build owns presentation.

## ADR-005: Enforce repository wiring in CI

**Status:** Accepted

Every `validation/validate_*.py` script must be registered in the suite. CI also checks local documentation links, placeholder READMEs, pinned Python requirements, undefined and unused Python names, repository-wide Python formatting, generated currency, and the viewer build. This closes a gap where three existing validators were present but not executed.

## ADR-006: Package code separately from engineering inputs

**Status:** Accepted

The Python wheel contains the CLI and its runtime dependency. Engineering files remain in a checkout selected by `--repo-root`; the package does not snapshot or promote source evidence. CI tests the installed command from outside the checkout. Software tags identify code and viewer builds, while the program dashboard retains engineering gate authority.

## ADR-007: Separate visual inspection from engineering validation

**Status:** Accepted

Section cuts, isolation, focus, and expanded view operate only on generated planning geometry in the browser. The component library is shown in full, including roles without geometry. These controls expose the model's limits; they do not create a fit, interference, or release result. A geometry count mismatch stops loading rather than silently presenting an incomplete assembly.

## ADR-008: Keep the 128 GB reference layout separate from the baseline

**Status:** Accepted

The exact public 16 GB memory package needs eight outlines to reach the approved 128 GB capacity. The baseline retains four assumed 32 GB sites. A separate CAD variant replaces those four solids with eight two-sided reference boxes and receives its own STEP, glTF, and proof report. This allows geometry review without treating the public package as X2-qualified or silently changing the baseline board architecture. PCB fabrication, routing, power, thermal path, and boot proof remain unresolved.

## ADR-009: Use one provisional v1R board thickness across models

**Status:** Accepted

The v1R floorplan and compute-zone stack specify a 0.8 mm PCB. The mechanical envelope still carried a 1.2 mm generic board allowance. Align the v1R envelope and assembly to 0.8 mm while keeping the board top at z = 4.0 mm, and enforce envelope/floorplan equality in the integration contract. This is an internal model correction. A fabricator-reviewed 12-layer stack, two-sided assembly limits, and physical tolerance evidence remain required.

## ADR-010: Model provisional camera openings

**Status:** Accepted for concept review

The camera pupil proof found a rear cover opening smaller than the assumed pupil and a continuous display and touch film over the front pupil. Widen the modeled rear cover opening to 5.0 mm radius and add a 3.1 mm radius punch-hole to the display stack and touch film at the front camera axis. Screen all three modeled layers with exact solid intersections. These dimensions are concept assumptions, not a selected panel or camera design. Supplier panel construction, black mask, cover optics, seals, alignment tolerances, and measured image performance are required before the optical path can be qualified.

## ADR-011: Bind firmware release to hardware identities

**Status:** Accepted

The `firmware_boot` hardware record must name a controlled JSON release bundle with exact image hashes, boot and recovery order, required interface drivers, and a flash readback plan. The bundle revision and reviewer must match its evidence record, and its selected BOM and routed PCB hashes must match approved upstream records. This checks release integrity and configuration consistency; it does not claim that the images boot or recover on a physical Slate Pocket. Serialized EVT0 results remain necessary.

## ADR-012: Reproduce schematic ERC from controlled settings

**Status:** Accepted

The `erc_report` record must bind the approved editable schematic, KiCad project settings, and reviewed JSON report by hash. Rerun ERC with all severities and reject any findings, project exclusions, or ignored critical connection rules. Compare the fresh and reviewed sheet results while allowing generation timestamps to differ. A clean ERC remains a rule check, not proof that the circuit can operate safely.

## ADR-013: Share controlled KiCad rules across ERC and PCB DRC

**Status:** Accepted

The routed PCB record must bind the same `.kicad_pro` bytes as the approved ERC record. The PCB auditor rejects DRC exclusions, ignored critical board rules, and zero fabrication design minima. It inspects the fresh DRC JSON for rule, unconnected-item, and schematic-parity findings in addition to checking KiCad's exit code. This establishes rule-set consistency and reproducible screening; fabricator review, signal and power integrity, and physical validation remain required.

## ADR-014: Bind power safety calculations to selected hardware

**Status:** Accepted

The `power_safety` record must name a controlled JSON release whose revision and reviewer match the evidence record. Its battery ratings come from the selected part set; its charger, PMIC, protection, and USB PD references match the electrical BOM. It binds the part set, BOM, and board by hash and checks charge input power, complete subsystem loads, rail capacity and startup order, pack current, and fault-control declarations. This makes a reviewed power analysis reproducible but does not prove supplier ratings or physical fault behavior. EVT0 measurements and safety review remain required.
