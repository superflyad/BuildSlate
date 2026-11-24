# Build to function: hardware evidence gate

The current Slate Pocket v1R repository cannot be handed to a hardware builder as a functional phone design. The [concept CAD](../../cad/slate-pocket-v1r/concept-cad/README.md) shows assumed volumes and nominal placement. It has no selected v1R BOM, released circuit design, routed board, complete interconnect drawings, boot firmware, or measured prototype results. Cutting an enclosure and placing representative parts at those coordinates would not produce a demonstrated device.

## Why placeholders exist

The planning geometry was created before supplier selection and controlled drawings. The project has prepared RFQs, component comparisons, preliminary PCB rectangles and power architecture, and test plans. Those are useful for feasibility review but cannot determine exact footprints, pin assignments, tolerances, assembly processes, or software support. The [EVT0 BOM strategy](../../validation/evt0/bom-strategy.yaml) still records zero selected parts. The [program dashboard](../../reports/program/dashboard.md) lists the supplier and physical evidence blockers.

## Three gates

| Gate | Required outcome | Current state |
| --- | --- | --- |
| Design release | Selected and reviewed part set, complete electrical and mechanical manufacturing package, power safety analysis, firmware and controlled bring-up instructions | Blocked |
| Functional EVT0 | A serialized unit built from that release, with calibrated power, interface, thermal, RF, and mechanical results and reviewed deviations; cellular is deferred from this configuration | Blocked |
| Phone function | Selected cellular design and software, measured calling and data, emergency behavior, and applicable regulatory evidence | Blocked |

The [readiness manifest](../../engineering/hardware/readiness.yaml) lists the required artifacts. The [gate code](../../buildslate/hardware_readiness.py) checks the selected sourcing roles and each evidence record. A record must identify an approved revision, reviewer, controlled file path, and matching SHA-256. Planning Markdown/YAML and files outside the controlled release or test directories are rejected. An accepted record means the listed file and review metadata exist; the gate cannot independently verify that the engineering judgment or test result is correct. Its positive state is therefore **ready for review**, not certification.

The selected BOM record is bound to the [part selection proof](selected_bom_proof.md). A status flag or candidate name cannot select a part: the proof requires a controlled released JSON BOM, exact manufacturer part numbers, hashed supplier artifacts for every required evidence type, and basic compute, memory, storage, display, and battery compatibility checks. Memory also needs a 128 GB topology record bound to the exact controller, memory part, supplier support file, and compute reference design. Cellular requires its own released part and interface proof before the phone-function gate can use it.

The [platform reference proof](platform_reference_proof.md) then binds the selected compute, memory, and storage MPNs and supplier files to a PMIC selection and a per-package memory channel, rank, and data-lane map. It reconciles those part references and MPNs with the approved electrical BOM, and rejects missing or overlapping lanes and stale supplier bytes. No v1R supplier reference package or map exists yet.

The approved memory floor remains 128 GB. The [compute path screen](compute_platform_decision.md) distinguishes an X2 controller maximum from an actual qualified 128 GB configuration. Current public mobile platforms cannot meet that floor; no reviewed public X2 package proves a pocket phone implementation. The Hardware view publishes this conflict without changing the product decision.

The [memory package screen](memory_package_fit.md) also shows that a reviewed exact 16 GB LPDDR5X part needs eight packages and cannot fit the current four memory planning rectangles. Public 32 GB capacity claims lack a reviewed exact package and X2 topology. The rectangles remain assumptions, not build coordinates.

The [battery candidate screen](battery_candidate_fit.md) exposes a separate mechanical and safety conflict: the published AI1-M01 bare-cell box is larger than the current complete-pack allocation, and no charge rating is published for that candidate. Its listed 2C band is a discharge category. The 100 W target cannot enter a build design without a supplier charge curve and complete-pack review.

The schematic netlist record has an additional [electrical proof](electrical_netlist_proof.md): its selected electrical BOM, critical endpoint contract, and exported XML netlist are checked together before that record can be accepted.

The ERC record has a separate [schematic rule proof](schematic_erc_proof.md). It reruns KiCad against the approved schematic and hashed project settings, rejects exclusions or disabled critical rules, and compares the clean result with the reviewed report. No released v1R schematic exists yet.

The [routed PCB proof](routed_pcb_proof.md) requires that same approved KiCad project settings hash, enabled critical DRC rules, positive fabrication design minima, zero DRC and parity findings, netlist parity, and complete copper-layer exports. No released v1R board exists yet.

The [power safety proof](power_safety_proof.md) requires selected battery ratings, a charge and discharge limit table, complete subsystem load coverage, rail capacity and sequence, fault response declarations, and exact bindings to the approved part set, electrical BOM, and routed board. No released v1R power design exists yet. The arithmetic is a consistency screen; supplier limits and protection behavior still need review and physical verification.

The [thermal release proof](thermal_release_proof.md) requires released mechanical and power identities, sourced material and boundary properties, case-specific heat maps, reviewed solver tables, and temperature-limit screens. It checks mesh refinement and energy balance, while the separate EVT0 gate requires calibrated physical temperature measurements and model correlation. No released v1R thermal model exists yet.

The [RF release proof](rf_release_proof.md) requires a selected Wi-Fi/Bluetooth module and two antennas, released board and mechanical identities, connected schematic matching paths, region-specific bands and lab scope, and source-backed RF sweep and coexistence margins. It does not substitute for conducted, chamber, RF-exposure, EMC, or certification evidence. No released v1R RF design exists yet.

The mechanical release record has a separate [STEP assembly proof](mechanical_release_proof.md). It requires source part and drawing hashes, released assembly identity, complete role coverage, and nominal interference and clearance checks. There is no released assembly to check yet.

The firmware boot record has a separate [firmware bundle proof](firmware_release_proof.md). It requires exact image hashes, boot and recovery order, driver coverage, flash readback instructions, and binding to the approved selected BOM and routed board. There is no released firmware bundle; the proof cannot establish boot or recovery on hardware.

The functional gate also reads the [EVT0 campaign](../../reports/program/evt0-campaign.yaml) directly. Passing required tests must belong to one serialized unit, build revision, configuration, and campaign. Each required test has a raw measurement contract, including integrated display, touch, camera, audio playback/capture, and USB activity; charge input power; and separately measured memory capacity and allocation. These checks confirm the presence and internal consistency of recorded evidence; engineering review and physical observation remain necessary.

```bash
buildslate hardware
buildslate hardware --format json
buildslate hardware --require-design-release
buildslate hardware --require-functional-evt0
buildslate hardware --require-phone-function
```

The `--require` switches return a nonzero exit code while blocked. CI checks that the [published status JSON](../../viewer/public/hardware-readiness.json) matches source inputs and tests that a stale hash, unreviewed record, missing file, or planning path cannot pass. A blocked gate is the correct, successful repository validation result until real evidence arrives.

## Evidence sequence

1. Obtain supplier responses and controlled drawings through the [intake workflow](operator_workflows.md). Select purchasable compute, memory, storage, battery, and display parts, with lifecycle and software support evidence. Keep confidential supplier material in an authorized controlled system; do not copy it into this public repository without distribution rights.
2. Resolve the actual device configuration and release the selected BOM, reference design, power and safety design, schematic, routed PCB, flexes, enclosure, thermal/RF designs, firmware, assembly instructions, and safe bring-up procedure. Engineering owners review the artifacts together; each approved public artifact can then be bound into the manifest by hash and revision.
3. Build serialized EVT0 units from that release. Capture raw, calibrated measurements and failures using the [EVT0 test workflow](../../validation/evt0/README.md). Review deviations before any claim that the device functions.

This gate tracks an integrated *Slate Pocket* build, not merely whether individual modules can operate on developer boards. Wireless charging and cellular are outside the present EVT0 configuration. The phone-function gate requires cellular selection, integration, measured phone behavior, and regulatory evidence. The public [Hardware view](https://superflyad.github.io/BuildSlate/?tab=hardware) exposes the current gate and every missing artifact.
