# Component Physics Models

BuildSlate now includes first-pass physics screening models for every major phone-class component category:

- battery pack
- display module
- PCB stack
- SoC/NPU package
- memory package
- storage package
- thermal module
- camera system
- antennas and RF
- wireless charging
- structural stackup

The models live in `engineering/component_models/`. Each script exposes command-line inputs, prints its assumptions and formulas, reports outputs in practical units, lists warnings, states confidence and basis, and names the primary blocker. The intent is to make component-level arithmetic explicit before any device profile or optimization pass is introduced.

## Screening purpose

These are screening models, not vendor-validated designs. They should be used to identify physical pressure in mass, volume, thickness, power, thermals, RF, routing, and placement. Passing one of these scripts does not mean the component can be manufactured, sourced, certified, or integrated in a production device.

## Assumption replacement path

The default values are conservative placeholders chosen to expose feasibility blockers early. Future CAD, BOM, vendor datasheets, measured prototypes, antenna simulations, thermal simulations, and supplier stack drawings should replace these assumptions. When better data exists, update the model input defaults or constants and preserve the basis for the change.

## Running the models

Run every component model with defaults:

```bash
python engineering/component_models/run_all_component_models.py
```

Run an individual model to inspect or override inputs:

```bash
python engineering/component_models/battery_pack.py --capacity-mah 6000 --workload-w 28
```

The grouped runner is intended to provide a quick engineering report before broader profile generation, optimization, CAD detailing, or BOM lock decisions.
