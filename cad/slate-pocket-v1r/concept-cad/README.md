# Slate Pocket v1R concept CAD

`assembly.step` is an editable, 41-solid concept assembly in millimeters. It covers every role in the component library and includes the exterior, display stack, board, battery, cameras, audio, radios, charging, thermal elements, seal path, and deferred wireless charging reserve. Individual solids retain stable part IDs.

`memory-8x16.step` is a separate editable, 45-solid reference alternative. It replaces the four assumed 32 GB DRAM solids with eight 14 × 14 × 1.1 mm outlines of Micron `MT62F2G64D8EK-023 WT:C`, four on each PCB side. The package dimensions are public; placement, controller compatibility, reverse-side assembly, and routing are not qualified. The floorplan, mechanical board, and compute stack agree on a provisional 0.8 mm PCB thickness, with no fabricator stackup or assembly review. The [eight-package outline study](../../../docs/engineering/memory_package_fit.md) explains the screen and its limits.

The [concept manifest](../../../engineering/assembly/concept-cad.yaml) records every added placement and its engineering basis. The [source assembly](../../../engineering/assembly/assembly.yaml) supplies the original 26 planning envelopes. The [CAD generator](../../../buildslate/cad.py) produces this STEP file and the matching viewer JSON/glTF from those inputs. Board mounting holes, package recesses, speaker grilles, the battery tray, camera lens wells, the rear aperture, and the gasket seat are concept details.

## Regenerate

Use Python 3.12 and an isolated environment:

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt -r requirements-cad.txt
.venv/bin/python -m buildslate.cad
.venv/bin/python scripts/check_cad_proof_geometry.py
python validation/validate_concept_cad.py
```

On Windows, replace `.venv/bin/python` with `.venv/Scripts/python.exe`.

Both STEP files are suitable for editing and replacing concept solids in a CAD application. Their glTF files are tessellated browser representations of the same solids. The baseline [proof report](../../../viewer/public/proof.json) and [memory alternative proof](../../../viewer/public/memory-8x16-proof.json) measure every solid, check source anchors and exports, and report exact nominal intersections and gaps, camera pupil path conflicts, 2D keepout conflicts, and local thickness screens. The [proofing method](../../../docs/engineering/cad_proofing.md) defines its thresholds and limits.

Neither format contains validated supplier geometry or a released mechanical design. The [CAD budget](../../../reports/slate-pocket-v1r-cad-budget.txt) records source keepout conflicts and a wireless charging thickness failure. The pack tray, RF reservations, front camera path, ports, gasket, and thermal patches are explicit design assumptions. Zero nominal solid intersections does not establish clearance or tolerance fit.
