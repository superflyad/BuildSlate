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
