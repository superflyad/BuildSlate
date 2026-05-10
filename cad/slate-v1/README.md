# Slate v1 CAD Scope

The `cad/slate-v1/` directory is reserved for mechanical CAD artifacts for the first Slate v1 digital-twin iteration.

Initial CAD work is limited to dimensional and blocking models. These models define envelope size, board keep-out regions, thermal-stack volume, display stack assumptions, and major component placement. They are not manufacturing-ready mechanical designs and should not be treated as released tooling data.

Target CAD files:

- `enclosure.step` — external envelope, display opening, rear cover, and chassis blocking geometry.
- `thermal-stack.step` — SoC contact area, vapor chamber, graphite layers, and chassis heat-spreading interfaces.
- `pcb-placeholder.step` — board outline, connector keep-outs, antenna keep-outs, and high-level component volumes.
