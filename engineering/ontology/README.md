# Hardware Ontology

This directory defines the measurable vocabulary for phone-class AI-device tradeoff modeling.

- `device_attributes.yaml` defines canonical attribute names, units, descriptions, model usage, and whether an attribute is required for feasibility review.
- `component_taxonomy.yaml` defines the phone-class component set and the mass, volume, thermal, electrical, mechanical, and RF relevance of each component.
- `material_taxonomy.yaml` defines conservative material property ranges and qualitative feasibility notes for structural, thermal, RF, and manufacturing review.

The ontology is intentionally separate from model formulas and numeric constants:

1. Attributes describe what must be measured or estimated.
2. Components identify where those attributes are used.
3. Materials define property ranges and tradeoff notes.
4. `engineering/constants/` supplies reusable screening values.
5. `engineering/models/` turns those values into explicit calculations.

Future design changes should add or update ontology entries before introducing new assumptions in specs, CAD, simulations, or feasibility documentation.
