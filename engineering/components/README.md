# Component property library

`component_library.yaml` is a first-pass component property library for Slate pocket v1 subsystem packaging studies.

The values are intentionally conservative placeholders. They are **not** vendor-certified component specifications, quotations, CAD-derived part volumes, thermal simulation results, measured power values, or proof of device feasibility.

## Profiles

- `conservative` — higher mass, volume, thickness, area, or power burden.
- `nominal` — midpoint planning assumption for early trade studies.
- `aggressive` — optimistic integration assumption that still requires vendor and prototype validation.

## Intended use

Use this library to estimate which subsystems dominate mass, volume, PCB area, z-height, thermal load, and placement constraints before changing Slate dimensions or creating detailed CAD.

Replace these placeholders with vendor datasheets, ECAD/MCAD measurements, and lab data as soon as real components are selected.
