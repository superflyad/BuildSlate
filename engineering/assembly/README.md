# Provisional assembly contract

`assembly.yaml` maps existing mechanical and PCB placements into one coordinate frame. The generator reads the envelope, keepouts, local zone stacks, floorplan, and program dashboard, then writes `viewer/public/assembly.json` and `viewer/public/assembly.gltf`.

The origin is the lower-left corner of the rear view. `x` follows device length, `y` width, and `z` thickness. All distances are millimeters. Boxes use `[x, y, z, length, width, height]` and stable IDs. PCB placement x/y values are relative to the board origin and translated by the generator.

Run `python -m buildslate.assembly` to generate, or `python -m buildslate.assembly --check` to verify currency. The regeneration DAG includes the export after the dashboard.

An envelope box is not a part drawing. `evidence_class` and `source` identify the basis for each box. The `active: false` entries represent deferred concepts and are hidden by default. The viewer must keep them separate from the current build.

## Editable concept CAD

`concept-cad.yaml` adds explicitly assumed solids for library roles absent from the source assembly and assigns editable profiles to selected source envelopes. `python -m buildslate.cad` exports [41 STEP solids](../../cad/slate-pocket-v1r/concept-cad/README.md), `viewer/public/concept.json`, `viewer/public/concept.gltf`, and `viewer/public/proof.json` from that manifest and the source assembly. Python 3.12 and `requirements-cad.txt` are required for regeneration. The Python and viewer gates check that committed concept assets still match the manifest and contain every part ID. The [proofing guide](../../docs/engineering/cad_proofing.md) defines the measured checks and their limits.

Each added solid has `evidence_class: design_assumption`, a source path, and an assumption note. Source parts retain their original evidence classes. Concept coverage means every component role has geometry; it does not change the program's source evidence status or release gates. The original 26 boxes remain available in the viewer as **Source envelopes**.
