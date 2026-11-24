# Slate Pocket v1R concept CAD

`assembly.step` is an editable, 41-solid concept assembly in millimeters. It covers every role in the component library and includes the exterior, display stack, board, battery, cameras, audio, radios, charging, thermal elements, seal path, and deferred wireless charging reserve. Individual solids retain stable part IDs.

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

The STEP is suitable for editing and replacing concept solids in a CAD application. The glTF is a tessellated browser representation of the same solids. The [proof report](../../../viewer/public/proof.json) measures every solid, checks source anchors and exports, and reports exact nominal intersections, 2D keepout conflicts, and local thickness screens. The [proofing method](../../../docs/engineering/cad_proofing.md) defines its thresholds and limits.

Neither format contains validated supplier geometry or a released mechanical design. The [CAD budget](../../../reports/slate-pocket-v1r-cad-budget.txt) records source keepout conflicts and a wireless charging thickness failure. The pack tray, RF reservations, front camera path, ports, gasket, and thermal patches are explicit design assumptions. Zero nominal solid intersections does not establish clearance or tolerance fit.
