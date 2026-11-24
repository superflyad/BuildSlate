# Slate Pocket v1R concept CAD

`assembly.step` is an editable, 41-solid concept assembly in millimeters. It covers every role in the component library and includes the exterior, display stack, board, battery, cameras, audio, radios, charging, thermal elements, seal path, and deferred wireless charging reserve. Individual solids retain stable part IDs.

The [concept manifest](../../../engineering/assembly/concept-cad.yaml) records every added placement and its engineering basis. The [source assembly](../../../engineering/assembly/assembly.yaml) supplies the original 26 planning envelopes. The [CAD generator](../../../buildslate/cad.py) produces this STEP file and the matching viewer JSON/glTF from those inputs.

## Regenerate

Use Python 3.12 and an isolated environment:

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt -r requirements-cad.txt
.venv/bin/python -m buildslate.cad
```

On Windows, replace `.venv/bin/python` with `.venv/Scripts/python.exe`.

The STEP is suitable for editing and replacing concept solids in a CAD application. The glTF is a tessellated browser representation of the same solids. Neither format contains validated supplier geometry or a released mechanical design. The [CAD budget](../../../reports/slate-pocket-v1r-cad-budget.txt) still records keepout conflicts and a wireless charging thickness failure. The pack shell, RF reservations, front camera path, ports, gasket, and thermal patches are explicit design assumptions. Do not treat an apparent fit in the viewer as an interference or tolerance result.
