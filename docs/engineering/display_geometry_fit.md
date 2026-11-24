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

The [public Hardware view](https://superflyad.github.io/BuildSlate/?tab=hardware) reports `blocked`, and the build-to-function design gate cannot become ready while this geometric conflict remains. Run `python -m buildslate.display_fit` to recompute the result. The [validator](../../validation/validate_display_fit.py) proves that simply moving to 7.0 inches does not fit the current reserve and that an explicit wider-body and resolution change clears the mathematical screen. That synthetic recovery is not an approved product change.

Resolution requires a product-owner decision under the [baseline change rule](slate-pocket-v1r-decision-baseline.md). Possible directions include widening the body enough for the selected module, revising the diagonal or aspect ratio with a documented workspace review, or changing the display architecture. The current targets and CAD remain unchanged until a decision is approved. A supplier module drawing, flex and border details, tolerance review, and a released assembly are still required after the active rectangle fits.
