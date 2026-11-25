# Cellular module outline screen

The phone-function gate needs a selected cellular platform and measured calling and data. The present EVT0 configuration defers cellular. To test whether its [128 GB eight-package board study](../../engineering/pcb/slate-pocket-v1r-floorplan/memory-8x16-study.yaml) leaves a credible module site, the [geometry screen](../../buildslate/cellular_fit.py) uses one public, unselected 5G reference: Quectel `RG255C-GL`.

Quectel's [RG255C Series specification, revision 1.1](https://www.quectel.com/content/uploads/2024/03/Quectel_RG255C_Series_5G_Module_Specification_V1.1.pdf) lists a 29 × 32 × 2.4 mm LGA outline, 3.3–4.3 V supply, USB 2.0 and other host interfaces, two cellular antenna ports, and optional VoNR/VoLTE. The specification calls the series industrial/commercial and marks listed carrier and regulatory certifications as in progress. The exact voice-enabled variant, firmware, carrier support, handheld suitability, power transients, and current certification state require supplier confirmation. This reference is **not** a selected modem or a phone-function proof.

## Larger-package board result

| Screen | Result |
| --- | --- |
| Provisional board outline | 78 × 55 × 0.8 mm |
| Nominal component boundary | 74 × 51 mm, 2 mm inset |
| Public module outline | 29 × 32 mm, both in-plane orientations tested |
| Assumed minimum package-to-package gap | 1 mm |
| Component side | No outline position among four 16 GB memory outlines and current non-memory planning rectangles |
| Reverse side | No outline position among the four 16 GB memory outlines, even with no other reverse-side components counted |

The screen tests boundary coordinates and obstacle edges where an axis-aligned rectangle can first fit. It checks both module rotations and both board sides. This is a necessary 2D package test, not land-pattern, escape-routing, or enclosure clearance. Run `python -m buildslate.cellular_fit` for exact machine-readable inputs and results. The public [Hardware view](https://superflyad.github.io/BuildSlate/?tab=hardware) reports `outline_blocked` for this larger-package arrangement.

This result applies to the 14 × 14 mm memory outlines. It does not apply to the compact Micron outline below. Board area alone does not establish the memory topology, X2 host interface, modem power, RF feeds, SIM/eSIM, audio, antennas, regulatory compliance, or a working phone. The [phone-function gate](build_to_function.md) stays blocked until a selected design and physical results exist.

## Compact-memory outline recovery

The separate [compact study](../../engineering/pcb/slate-pocket-v1r-floorplan/memory-8x16-compact-study.yaml) rotates Micron's 8 × 12.4 × 1.2 mm package to 12.4 × 8 mm on the board. Its reverse-side left column moves from x = 10 to 8 mm, and the right column from x = 51 to 52 mm. The component-side packages remain at their earlier coordinates. This is a nominal placement experiment, not a routed 128 GB architecture.

With these coordinates, the 29 × 32 × 2.4 mm Quectel reference has one reverse-side outline location at local board origin **(21.4, 2) mm** under the assumed 1 mm planar gap rule. The board remains **78 × 55 × 0.8 mm**. The modem box starts at global **(113.4, 14, 0.8) mm**, leaving **0.25 mm** nominal vertical gap above the modeled rear-cover top. The [46-solid editable STEP](../../cad/slate-pocket-v1r/concept-cad/phone-fit-compact-outline.step) and [public CAD proof](https://superflyad.github.io/BuildSlate/?model=compactphone&tab=proof) find **zero positive-volume intersections** in this assumed assembly. The same proof retains keepout and wireless-charge stack findings. A zero-intersection nominal box model is not a tolerance, land-pattern, or assembly clearance study.

The compact memory has no supplier-qualified X2 channel and rank map, and its 1.2 mm body exceeds the original 1.0 mm memory block. The module is unselected; no voice-enabled orderable variant, host/power/audio/SIM design, antenna path, carrier support, handheld regulatory route, or measured call is established. The board, modem, and phone-function gates remain blocked. Run `python -m buildslate.cellular_fit` for the larger-package screen and `python -m buildslate.cellular_fit --compact` for this alternative.

## Larger-package board extension and enclosure conflict

Holding the eight memory package outlines and the current board origin fixed, the first whole-millimeter reverse-side board width that admits the rotated 32 × 29 mm module outline at a 1 mm nominal package gap is **78 mm**, up from 55 mm. The module's local origin is (2, 47) mm; the hypothetical 78 × 78 mm board remains inside the present internal XY boundary. Its reverse-side module bottom is 0.25 mm above the nominal rear-cover top before solder, tolerance, shielding, or protection allowances.

The same 3D box screen finds that the expanded PCB intersects the current rear-camera and speaker-A envelopes and the haptic actuator concept. The module itself intersects the rear-camera envelope. The [editable 46-solid STEP study](../../cad/slate-pocket-v1r/concept-cad/phone-fit-conflict.step) confirms four positive-volume intersections with exact CAD solids; inspect them in the [public 3D Proof view](https://superflyad.github.io/BuildSlate/?model=phonefit&tab=proof). This is a rejected layout, not a ready alternative. It also leaves the separate [display active-area conflict](display_geometry_fit.md) unresolved. Moving any of these parts requires a new whole-device layout and review of optical path, acoustics, RF, thermal contact, service access, and stack height. Run `python -m buildslate.cellular_fit` for the machine-readable extension and collision coordinates; the public Hardware view reports the result.

## Next design evidence

1. Obtain the supported 128 GB compute and memory reference design, then redesign board placement around the selected packages and required escapes.
2. Establish target markets and operators; request a voice-enabled modem variant, host/audio/SIM design files, power transient limits, antenna requirements, and current carrier/regulatory scope.
3. Bind the selected module to the released BOM, schematic, routed board, RF design, firmware, and full assembly with measured clearances.
4. Build a serialized unit and record registered calls, audio in both directions, data transfer, emergency-call behavior, RF exposure, and required approvals under reviewed test procedures.
