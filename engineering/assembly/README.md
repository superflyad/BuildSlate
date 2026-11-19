# Provisional assembly contract

`assembly.yaml` maps existing mechanical and PCB placements into one coordinate frame. The generator reads the envelope, keepouts, local zone stacks, floorplan, and program dashboard, then writes `viewer/public/assembly.json` and `viewer/public/assembly.gltf`.

The origin is the lower-left corner of the rear view. `x` follows device length, `y` width, and `z` thickness. All distances are millimeters. Boxes use `[x, y, z, length, width, height]` and stable IDs. PCB placement x/y values are relative to the board origin and translated by the generator.

Run `python -m buildslate.assembly` to generate, or `python -m buildslate.assembly --check` to verify currency. The regeneration DAG includes the export after the dashboard.

An envelope box is not a part drawing. `evidence_class` and `source` identify the basis for each box. The `active: false` entries represent deferred concepts and are hidden by default. The viewer must keep them separate from the current build.
