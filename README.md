# BuildSlate

BuildSlate is a hardware digital-twin repository for the Slate Ecosystem. It turns the Slate v1 source-intent concept into structured engineering data, validation checks, derived calculations, CAD planning, and feasibility documentation.

The repository tracks both target concept specs and feasibility constraints. Target specs describe what Slate is intended to become; feasibility constraints describe what must be validated before those targets can be treated as buildable engineering claims.

## Four engineering layers

1. **Source intent**
   - `specs/Slate_v1_Specifications.pdf` captures the canonical Slate v1 product concept and source intent.

2. **Normalized machine-readable specs**
   - `specs/slate-pocket-v1.yaml` converts the pocket Slate v1 concept into structured engineering assumptions.
   - `specs/schema/slate.schema.yaml` documents required top-level sections, expected fields, and feasibility metadata.
   - `specs/slate-v1.yaml` is preserved as the existing tablet-class baseline/reference spec.

3. **Derived engineering models**
   - `simulations/derived_metrics/` contains first-order calculators for model memory, battery runtime, and thermal density.
   - These scripts expose contradictions and sizing pressure early; they are not substitutes for measured hardware data, CAD volume studies, or thermal simulation.

4. **Validation**
   - `validation/` checks required spec fields, feasibility metadata, allowed feasibility labels, and first-pass dimensional constraints.

## Engineering Foundation

BuildSlate's engineering foundation keeps future specs, CAD, simulations, SlateOS claims, and feasibility statements traceable to first-principles inputs instead of unsupported assertions.

- `engineering/constants/` contains conservative constants, units, notes, and profile ranges for battery, material, thermal, and compute estimates.
- `engineering/models/` contains first-pass calculators that print their inputs, assumptions, formulas, outputs, confidence, basis, and primary blocker.
- Composite chassis modeling:
  - `engineering/models/composite_chassis.py` estimates mixed-material mass, RF-friendly volume, metal percentage, and first-order thermal conduction.
  - It is a screening tool, not a production thermal model.
- `engineering/assumptions/` contains assumption registries that separate known source-intent values, modeled estimates, aggressive assumptions, conceptual extrapolations, and research blockers.
- `validation/` contains repository checks that keep specs and dimensional constraints machine-checkable.
- Future features must trace claims back to these foundations, a measured fact, an industry reference, or an explicit unresolved blocker.



## Local AI Runtime Models

BuildSlate includes first-pass local AI runtime screening models in `engineering/runtime_models/`. These scripts estimate model residency, KV cache memory, context scaling, model load time, multimodal overhead, and a combined runtime memory budget.

Run the grouped default report with:

```bash
python engineering/runtime_models/run_all_runtime_models.py
```

The models are conservative memory and load-time screens. They account for quantized weight residency, KV cache pressure, long-context growth, local storage load assumptions, multimodal resident components, OS reserve, and safety reserve. They do not predict real tokens/sec; real throughput still depends on memory bandwidth, compute kernels, NPU/GPU support, scheduling, thermal throttling, and runtime implementation.


## Manufacturing and Reliability Models

BuildSlate includes first-pass manufacturing and reliability screening models in `engineering/manufacturing_models/`. These scripts estimate tolerance stackup, thermal expansion mismatch, battery swelling allowance, assembly complexity, repairability pressure, reliability hotspots, and yield risk indicators for thin AI-device architectures.

Run the grouped default report with:

```bash
python engineering/manufacturing_models/run_all_manufacturing_models.py
```

The models are conservative screening tools. They do not predict factory yield, certify durability, or claim manufacturing feasibility; they make tolerance, swelling, bonded-material, assembly, repair, and integration pressure visible for later CAD, supplier, and validation work.

## Interconnect and Power Delivery Models

BuildSlate includes first-pass interconnect and power delivery screening models in `engineering/interconnect_models/`. These scripts estimate memory bandwidth pressure, PCB routing density, power delivery current, transient current and voltage droop, and package adjacency constraints before detailed board layout or SI/PI simulation exists.

Run the grouped default report with:

```bash
python engineering/interconnect_models/run_all_interconnect_models.py
```

The models are conservative engineering screens. They do not predict real inference performance, fabricate PCB traces, or replace supplier-backed package, memory, PMIC, battery, thermal, and signal-integrity data.

## Component Modeling

- `engineering/components/component_library.yaml` defines subsystem properties.
- `engineering/models/component_packaging.py` estimates packaging pressure.
- `engineering/models/component_mass_budget.py` estimates mass drivers.
- `engineering/models/component_power_budget.py` estimates power and runtime pressure.


## Component Physics Models

BuildSlate includes first-pass component physics screening models in `engineering/component_models/`. These scripts cover the battery pack, display, PCB, SoC/NPU, memory, storage, thermal module, camera system, antennas/RF, wireless charging, and structural stackup.

Run the grouped default report with:

```bash
python engineering/component_models/run_all_component_models.py
```

These models are used before device profiles or optimization. They make assumptions, equations, warnings, confidence, basis, and primary blockers explicit so future CAD, BOM, datasheet, and validation work can replace placeholders with measured or supplier-backed values.


## Environmental Operating Models

BuildSlate includes first-pass environmental operating condition models in `engineering/environment_models/`. These scripts show how external conditions change thermal risk, skin-temperature margin, display load, charging risk, and throttling pressure before device profiles or optimization are introduced.

Run the grouped default and stress-case report with:

```bash
python engineering/environment_models/run_all_environment_models.py
```

The environmental models cover:

- ambient temperature and shrinking skin-temperature margin in hot environments;
- hand contact reducing useful heat-spreading area;
- pocket, bag, handheld, open-air, and car-console-sun operating conditions;
- sunlight display load and high-brightness power pressure;
- charging overlap with sustained AI workload, including wireless charging risk;
- first-pass throttle policy recommendations for skin, battery, and SoC temperature thresholds.

These scripts are screening tools, not compliance tests. Pocket/bag sustained AI and charging plus AI thermal overlap are treated as constraints that must be throttled, disallowed, or validated with measured hardware data. See `docs/engineering/environmental_conditions.md` for interpretation guidance.

## Thermal and Stackup Screening

- `engineering/component_models/thermal_resistance_network.py` estimates first-pass heat path risk from a hotspot through TIM, spreaders, frame material, and exterior skin.
- `engineering/component_models/zone_stackup.py` checks local z-height conflicts across display, battery, SoC/memory, storage, camera, wireless charging, and antenna zones.
- `engineering/assumptions/source_registry.yaml` tracks assumption confidence so constants, targets, and unresolved blockers remain visible during review.

## Hardware Ontology

BuildSlate now separates hardware vocabulary, constants, formulas, and interpretation so future design changes remain traceable.

- `engineering/ontology/` defines measurable attributes, component taxonomy, and material taxonomy for phone-class AI-device analysis.
- `engineering/constants/` defines conservative values and ranges used by screening models.
- `engineering/models/` uses explicit formulas to turn ontology-backed constants into mass, thermal, electrical, packaging, and material tradeoff estimates.
- `docs/engineering/` explains how to interpret the model outputs and why no material, battery, chassis, or cooling decision should be treated as universally best.
- Future design changes to thickness, chassis material, battery size, cooling strategy, or packaging must use these definitions before claiming feasibility.

## Repository areas

- `specs/` — PDF source intent, normalized YAML specs, baseline specs, and schema references.
- `specs/components/` — component-level specification files and interface notes.
- `cad/slate-v1/` — mechanical CAD workspace and CAD planning for enclosure, thermal stack, PCB placeholders, battery blocks, and camera paths.
- `bom/` — structured bill-of-materials files with component categories, quantities, placeholder parts, and engineering notes.
- `simulations/derived_metrics/` — derived feasibility estimates for local model memory, battery runtime, and thermal density.
- `simulations/thermal/` — thermal models, assumptions, and future solver inputs.
- `simulations/power/` — battery and workload runtime estimates.
- `simulations/model-fit/` — memory-fit estimates for local model parameter counts and quantization levels.
- `diagrams/` — system diagrams, mechanical stack diagrams, and architecture sketches.
- `validation/` — scripts that verify specs and other digital-twin inputs are complete enough for downstream tooling.
- `docs/` — design notes, feasibility methodology, decisions, and engineering documentation.
- `scripts/` — repository automation and utility scripts.

## Feasibility labels

BuildSlate uses conservative feasibility labels to avoid implying that the Slate pocket target is already buildable:

- `feasible_today` — commercially available or demonstrably manufacturable with current technology.
- `near_term` — credible with current or emerging parts, but integration risk remains.
- `conceptual_extrapolation` — physically plausible direction, not commercially available today in the target form factor.
- `research_required` — insufficient evidence to claim feasibility; more modeling, vendor data, experiments, or prototypes are needed.

## Current checks

Run the normalized validation and derived-metric scripts from the repository root:

```bash
python validation/validate_specs.py
python validation/dimensional_constraints.py
python simulations/derived_metrics/model_memory.py
python simulations/derived_metrics/model_memory.py --params-billions 70 --quant-bits 4
python simulations/derived_metrics/battery_runtime.py
python simulations/derived_metrics/thermal_density.py
python engineering/models/battery_energy.py
python engineering/models/model_memory.py
python engineering/models/surface_area.py
python engineering/models/thermal_limits.py
python engineering/models/mass_budget.py
python engineering/models/material_compare.py --material aluminum_alloy
python engineering/models/material_screen.py
python engineering/models/composite_chassis.py --preset aluminum_heat_frame_glass_windows
```

These scripts are first-order engineering tools. They are intended to keep assumptions explicit and machine-checkable while the CAD, BOM, and simulation models mature.

## Constants Provenance

BuildSlate tracks engineering constants and assumptions in `engineering/provenance/constants_provenance.yaml`. The registry records each constant's source category, confidence, units, rationale, limitations, future validation path, and citation status so reviewers can distinguish measured facts, industry references, modeled estimates, conceptual extrapolations, and unresolved blockers.

Use `python validation/validate_provenance.py` to validate the provenance schema. Use `python engineering/provenance/provenance_report.py` to print counts by category and confidence, citation gaps, conceptual extrapolations, unresolved research blockers, and the highest-risk assumptions.
