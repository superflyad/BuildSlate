# Display active-area fit

The approved v1R target is a 7.5-inch, 16:10 workspace inside a 180 × 95 mm body. The current [CAD envelope](../../cad/slate-pocket-v1r/envelope-model/envelope.yaml) reserves 174 × 89 mm for the display, matching the [assembly box](../../engineering/assembly/assembly.yaml). The [geometry screen](../../buildslate/display_fit.py) derives the minimum active rectangle directly from the [profile](../../configs/devices/slate-pocket-v1r.yaml):

| Quantity | Result |
| --- | ---: |
| 7.5-inch, 16:10 active rectangle | 161.544 × 100.965 mm |
| External body face | 180 × 95 mm |
| CAD display reserve | 174 × 89 mm |
| Active short-side overrun beyond body | 5.965 mm |
| Active short-side overrun beyond reserve | 11.965 mm |
| Maximum 16:10 diagonal in current reserve | 6.611 inches |
| Minimum body width with current 3 mm side insets | 106.965 mm |

These are active-pixel dimensions. A real module needs additional border, driver, flex, bonding, corner, and tolerance space. The approved 7.0-inch lower search range still needs a 94.234 mm active short side at 16:10, more than the 89 mm reserve. Therefore changing only to a 7.0-inch panel does not close the current package.

The [source-intent specification](../../specs/slate-pocket-v1.yaml) also pairs `16:10` with `3200x1800` pixels. That pixel ratio is 16:9. The v1R profile has no explicit resolution override, so the screen reports the source mismatch rather than treating both claims as compatible.

## Drawing-based candidate screen

[Hongguang's preliminary A0 HG070FH002 specification](https://www.hongguangdisplay.com/wp-content/uploads/2025/02/7.0-inch-AMOLED-Display-1080x1920-ResolutionMIPI-HG070FH002-.pdf) publishes a 7.0-inch touch AMOLED with a 154.9056 × 87.1344 mm active area and a 160.9056 × 89.1344 × 1.028 mm panel outline including polarizer and foam. Its 1080 × 1920 pixels are 16:9. The panel outline fits the 180 × 95 mm body face nominally, but the short side exceeds the existing 89 mm CAD reserve by 0.1344 mm. Retaining the current 3 mm side insets would require a body at least 95.1344 mm wide for the nominal panel outline alone. This is a dimensional comparison, not a feasible enclosure design.

The A0 document is preliminary. The complete flex routing envelope, tolerances, optical openings, bonding, host interface, power design, availability, and procurement are unqualified. This candidate also misses the approved 7.5-inch 16:10 format and is **rejected for the current design**. Its values and the source PDF's SHA-256 are recorded in the [candidate evidence](../../research/evidence/display-storage/candidate-comparison.yaml); the [geometry screen](../../buildslate/display_fit.py) recalculates the nominal fit and the public Hardware view exposes the result. No display is selected.

[Kadi's revision 1.0 KD070BWU01HN specification](https://www.kadidisplay.com/wp-content/uploads/2024/08/KD070BWU01HN-V1.0-SPEC.pdf) is a second manufacturer-drawing screen. It identifies a 7.0-inch, 1080 × 1920 AMOLED with on-cell touch and a 161.11 ± 0.15 × 89.04 ± 0.15 mm panel planform. The drawing's 0.822 ± 0.1 mm profile is measured from polarizer to PET; it is not a complete installed thickness including the flex and component region. The nominal short side exceeds the 89 mm reserve by 0.04 mm; at the published panel maximum it exceeds by 0.19 mm. With the current 3 mm side insets, a body at least 95.19 mm wide would accommodate that maximum panel width before assembly clearance or tolerance of the enclosure. Its 16:9 format also differs from the approved target. These calculations do not establish a buildable fallback or an orderable part; flex routing, host power and signal integration, attachment, lifecycle, and supply remain open. The exact source PDF hash is recorded in the candidate evidence.

The [public Hardware view](https://superflyad.github.io/BuildSlate/?tab=hardware) reports `blocked`, and the build-to-function design gate cannot become ready while this geometric conflict remains. Run `python -m buildslate.display_fit` to recompute the result. The [validator](../../validation/validate_display_fit.py) proves that simply moving to 7.0 inches does not fit the current reserve and that an explicit wider-body and resolution change clears the mathematical screen. That synthetic recovery is not an approved product change.

Resolution requires a product-owner decision under the [baseline change rule](slate-pocket-v1r-decision-baseline.md). Possible directions include widening the body enough for the selected module, revising the diagonal or aspect ratio with a documented workspace review, or changing the display architecture. The current targets and CAD remain unchanged until a decision is approved. A supplier module drawing, flex and border details, tolerance review, and a released assembly are still required after the active rectangle fits.
