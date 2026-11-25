# Assembly and first-power release proof

The [hardware gate](../../engineering/hardware/readiness.yaml) requires separate
controlled procedures for assembly and first power. The current repository has
neither; both remain **missing** in the [public Hardware view](https://superflyad.github.io/BuildSlate/?tab=hardware).
The [auditor](../../buildslate/build_procedure_proof.py) checks release identity,
source hashes, limits, inspection coverage, and ordering. It does not authorize
a build or prove that an operator followed the instructions.

## First-power safety

Release `engineering/hardware/released/assembly/bench-safety.json` with
`schema_version: 1`, `device: slate-pocket-v1r`, `revision`, and `reviewed_by`.
Bind SHA-256 bytes for the selected BOM, routed PCB, power-safety design, and
firmware bundle using the fields named in
[`BENCH_SOURCES`](../../buildslate/build_procedure_proof.py). The readiness
`bench_safety` record must identify that exact file and match its hash,
revision, and reviewer. Every bound upstream record must already be approved.

The `supply` section specifies an **isolated battery emulator** for initial
energization: the pack is disconnected, and charging, radio, and wireless
operation are disabled. Its voltage range, current limit, and temperature stop
must remain within the released power-design limits. The `hard_stops` map
includes overvoltage, overcurrent, overtemperature, telemetry loss, and visible
smoke or swelling. Numeric thresholds cannot exceed the bench supply limits.
The rail sequence must match the released power design, and every rail needs a
voltage acceptance window and settling timeout for first-power logging.
Voltage, current, and temperature instruments each need a model, calibration
identifier, and positive sampling period. The emergency section names an
accessible disconnect, quarantine location, operator role, witness, and a
response time of at most five seconds.

The release audit proves only that those limits are coherent and traceable.
Instrumentation calibration, emergency response, protection trips, and thermal
behavior must still be observed during authorized physical testing.

## Assembly procedure

Release `engineering/hardware/released/assembly/assembly-procedure.json`
with the same identity fields. Bind exact hashes for the selected BOM, routed
PCB, power design, firmware, mechanical STEP assembly, interconnect release,
thermal release, and the approved bench procedure using
[`ASSEMBLY_SOURCES`](../../buildslate/build_procedure_proof.py). The
`assembly_release` readiness record must name this JSON file and match its
hash, revision, and reviewer. Every upstream evidence record must be approved.

The procedure declares these stages in order:

1. Incoming part and lot inspection.
2. PCBA shorts and polarity inspection.
3. Current-limited first board power using the isolated emulator.
4. Isolated programming and flash readback.
5. Thermal interface installation with a measured bondline range.
6. Mechanical fit of the disconnected pack, with insulation and compression checks.
7. Interconnect pinout and retention inspection.
8. Enclosure closure with clearance and seal inspection.
9. Integrated power, boot, and radio-kill check using the same isolated supply.
10. Final configuration and defect disposition.

Each stage requires a work instruction, operator role, tools, a hold-on-failure
rule, and fields for operator, time, measurements, and disposition. Required
inspections need a named method, evidence field, and either a numeric acceptance
range with unit or an explicit binary pass criterion. The first-board-power
and integrated-power current ceilings cannot exceed the bench limit. A reordered
or missing step fails the release proof.

The [EVT0 build traveler](../../validation/evt0/build-traveler.md) records what
was actually built. Physical authorization, incoming part inspection, measured
clearances, rail logs, charge/discharge testing, deviations, and reviewer
disposition remain separate requirements. A structurally passing procedure is
not a completed traveler or a functioning phone.
