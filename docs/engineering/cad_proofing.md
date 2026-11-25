# Concept CAD proofing

The [concept assemblies](../../cad/slate-pocket-v1r/concept-cad/README.md) are checked as geometry, not certified as devices. `buildslate.cad` builds the baseline from the [source assembly](../../engineering/assembly/assembly.yaml) and [concept manifest](../../engineering/assembly/concept-cad.yaml), then replaces the four planning DRAM solids with the [eight-package study](memory_package_fit.md) for a separate alternative. A third variant extends that board and places a public modem outline to expose the [phone integration collisions](cellular_module_fit.md). A fourth substitutes a drawing-derived [USB connector mounting envelope](usb_interconnect_fit.md) for the assumed port. Each receives STEP, glTF, and its own proof report. The [public Proof view](https://superflyad.github.io/BuildSlate/?tab=proof) presents the selected model's report.

## Checks

| Check | Code | Result and limit |
| --- | --- | --- |
| Part identity and role coverage | `buildslate.cad.build_concept` and `validation/validate_concept_cad.py` | Every concept part has a unique ID and every component library role has at least one representation. Coverage does not mean a selected part exists. |
| Source anchors | `buildslate.cad_proof._source_exists` | Each part's engineering basis and geometry manifest path resolve to a tracked YAML node. An anchor proves traceability, not the correctness of the source value. |
| Solid integrity | `buildslate.cad_proof.build_proof` | Every CadQuery solid is valid, has positive volume, and matches its declared bounds within 0.01 mm. |
| STEP round trip | `buildslate.cad.generate` and `buildslate.cad_proof.build_proof` | Reimported STEP has the same solid count and aggregate volume within 0.01 mm³ or one part in ten million, whichever is larger. This does not verify every CAD feature semantically. |
| Viewer geometry | `buildslate.cad_proof.build_proof` and `viewer/scripts/validate-model.mjs` | glTF IDs and mesh bounds match the BREP parts; the browser loader opens every mesh. Mesh tolerance is at most 0.25 mm and tightens to 5% of a thin feature's size. The display remains a tessellation. |
| Solid intersection | `buildslate.cad_proof.measure_intersections` | A box broad phase precedes exact BREP Boolean volume. Overlaps greater than 0.01 mm³ are reported. Deferred and reserved geometry is classified separately. Zero nominal intersections does not establish clearance or tolerance fit. |
| Nominal solid gaps | `buildslate.cad_proof.measure_nominal_gaps` | Exact BREP distance is calculated for active solid pairs whose bounding boxes are within 0.5 mm. Contacts at or below 0.005 mm and gaps through 0.5 mm are reported separately. These are nominal positions, not tolerance clearances. |
| Camera pupil paths | `buildslate.cad_proof.measure_optical_paths` | Cylindrical nominal pupils are intersected with the rear cover, display stack, and touch film. The report gives prism overlap and modeled aperture radial margin for each layer. This is a geometry screen, not a light-transmission or image-quality test. |
| Planform keepouts | `buildslate.cad_proof.build_proof` | Active parts are screened against applicable 2D keepout rectangles by layer. The report gives overlap area, not 3D RF, acoustic, or connector clearance. |
| Local thickness | `buildslate.cad_proof._zone_screen` | Each source stack is summed against the 9.5 mm envelope and its source decision rules. These are local estimates, not section drawings or a tolerance analysis. |

The [CAD proof fixture](../../scripts/check_cad_proof_geometry.py) checks positive overlap, face contact, a 0.25 mm gap, reservation exclusion, a clipped rear pupil, a clear aperture, and a continuous panel over the front pupil. Standard CI validates the committed report's identity and internal consistency without installing CadQuery. The Python 3.12 CAD job regenerates the STEP, glTF, and proof report, reruns the fixture, and rejects a stale proof report.

## Read a finding

`proof.json` records every part's volume, surface area, face and edge counts, six integrity checks, intersecting and nearby part IDs, and keepout IDs. All 22 component roles have linked checked solids and retain their source library's unresolved evidence list. The report also lists exact nominal contacts and small gaps, measured overlaps, and local stack results. Select a finding in the viewer's **Proof** tab to inspect its parts and source basis.

The baseline and eight-package reference variant have no positive volume intersections between active solids at nominal placement. The phone integration study has four deliberate intersections: expanded PCB with rear camera, speaker A, and haptic actuator, plus modem with rear camera. The revised baseline concept has no overlap between either camera's nominal pupil prism and its adjacent opaque modeled layers. The assumed rear pupil radius is 4.16 mm within a 5.0 mm cover opening, leaving 0.84 mm radial margin. The assumed front pupil radius is 2.56 mm within 3.1 mm openings in the display stack and touch film, leaving 0.54 mm radial margin at each. The cover glass is modeled as intact and optically transparent, not tested. Supplier panel punch-hole construction, black mask, optical transmission, rear camera cover, sealing, tolerance stack, alignment, and measured image performance remain unresolved. These are concept geometry screens, not proof of functional cameras. The models also retain keepout conflicts, deferred wireless charging reservation overlaps, a failed wireless charging thickness stack, and unverified component evidence. The v1R mechanical board matches the provisional 0.8 mm floorplan stack, but its fabricability and two-sided assembly are unreviewed. All three report statuses remain `review_required`. Replacing an assumed shape or moving a part requires a manifest change, CAD regeneration, proof review, and the normal repository gate.

The older [CAD budget](../../reports/slate-pocket-v1r-cad-budget.txt) screens seven source placements. The proof report also screens applicable concept and board parts, so its keepout count can be higher without contradicting that source report.

## Run locally

With Python 3.12 and `requirements-cad.txt` installed:

```bash
python -m buildslate.cad
python scripts/check_cad_proof_geometry.py
python validation/validate_concept_cad.py
npm run check:model --prefix viewer
```

The proof does not cover routed interconnects, flex bends, fasteners, adhesive compression, assembly order, temperature, mass, structural loading, emissions, RF performance, acoustic paths, supplier tolerances, or physical qualification. The [program dashboard](../../reports/program/dashboard.md) remains the source for readiness and external evidence gates.
