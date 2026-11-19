# Architecture

## Authority

BuildSlate has four kinds of content:

1. **Intent and controlled inputs:** specifications, device profiles, engineering registries, and approved configuration decisions.
2. **Source evidence:** supplier responses, EVT0 campaigns, calibration records, and pilot bundles. Their original bytes and receipts are preserved by the intake tools.
3. **Derived models:** calculations, provisional CAD envelopes, integration contracts, and the assembly export. A derived model cannot promote an assumption to evidence.
4. **Views:** reports, program graph, dashboard, and browser viewer. Views reflect source state and do not make release decisions.

The [program manifest](engineering/program/program_model.yaml) identifies graph authorities. The [regeneration manifest](engineering/program/regeneration.yaml) identifies generated outputs and their dependencies. The [platform architecture](docs/engineering/platform_architecture.md) explains the evidence and transaction boundaries in detail.

The [repository standards](docs/standards/repository.md) define directory ownership, source and generated file classes, and change rules. Domain models remain in their existing directories until a migration has an explicit authority map and a validated replacement.

## Assembly pipeline

```text
mechanical envelope + keepouts + zone stacks + PCB floorplan
                         |
                         v
       engineering/assembly/assembly.yaml
                         |
                         v
                buildslate.assembly
                         |
                         v
      assembly.json + assembly.gltf
                         |
                         v
                 browser viewer
```

The assembly manifest assigns stable part IDs, display names, groups, and provisional z positions. It references existing mechanical and PCB placements for x/y dimensions. The generator validates IDs and envelope containment, exports a common JSON record and glTF geometry, and copies current dashboard state into the JSON view. The viewer consumes these files; it does not edit engineering inputs.

Every displayed solid is a box envelope. The glTF is a machine-readable visualization artifact, not released CAD. A supplier or design geometry import must carry its own source, revision, units, coordinate transform, evidence class, and acceptance review before replacing one of these boxes.

## Change flow

Update the authoritative input, regenerate affected outputs, run the validation gate, and review the resulting status. A source change should never be made only in a generated report or viewer asset. See [Contributing](CONTRIBUTING.md) and the [operator workflows](docs/engineering/operator_workflows.md).
