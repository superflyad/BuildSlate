# Released mechanical CAD proof

The [concept STEP](../../cad/slate-pocket-v1r/concept-cad/README.md) is editable planning geometry. The [released CAD auditor](../../buildslate/mechanical_proof.py) evaluates a separate, controlled assembly under `engineering/hardware/released/mechanical/`. No released assembly or supplier part drawings are in the repository, so the [current report](../../viewer/public/mechanical-proof.json) is `missing`.

## Release package

`assembly.step` and `assembly.manifest.yaml` are the required top-level files. The manifest declares millimeters, the `lower_left_rear_xyz_mm` assembly frame, the device envelope, global minimum clearance, maximum allowed contact gap, explicit contact pairs, and at least 22 distinct part solids covering all active component-library roles plus the enclosure structure. The envelope must match the active [v1R profile](../../configs/devices/slate-pocket-v1r.yaml); the enclosure structure must span its outer length and width. Each part record identifies its manufacturer, part number, revision, source frame, geometry license, public distribution scope, roles, source STEP and drawing paths with SHA-256, nominal source dimensions, rotation, translation, and conservative radial uncertainty. All sources must resolve inside the controlled mechanical release directory.

The source STEP for each part must contain one valid, positive-volume solid. The auditor compares its bounds to the declared source dimensions, applies the reviewed placement, checks the device envelope, and matches every placed solid by bounds and volume to the released `assembly.step`. It then measures exact positive-volume penetrations and pairwise clearances. Non-contact pairs must retain the declared minimum clearance after both parts' radial uncertainties are charged against the gap. Declared contact pairs must meet the maximum contact-gap limit and still have no positive-volume penetration.

```bash
# Python 3.12 with requirements-cad.txt installed
python -m buildslate.mechanical_proof --write
python scripts/check_mechanical_proof_geometry.py
python validation/validate_mechanical_proof.py
```

The hardware gate accepts a `mechanical_release` evidence record only when it names the controlled `assembly.step`, binds its hash and the manifest hash, and the regenerated CAD proof passes. The Python 3.12 CAD CI job imports the real STEP files and rejects a stale proof report. The synthetic fixture checks a valid assembly, source hash changes, wrong assembly placement, penetration, inadequate tolerance clearance, and missing role coverage.

This check does not parse the supplier drawing, independently establish its tolerance values, model flex motion or thermal expansion, determine assembly order, or prove the physical device fits. Those remain engineering review and EVT0 tasks. Controlled supplier files may require an authorized private repository; a public model cannot be promoted by copying NDA material without rights to distribute it.
