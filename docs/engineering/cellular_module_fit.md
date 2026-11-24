# Cellular module outline screen

The phone-function gate needs a selected cellular platform and measured calling and data. The present EVT0 configuration defers cellular. To test whether its [128 GB eight-package board study](../../engineering/pcb/slate-pocket-v1r-floorplan/memory-8x16-study.yaml) leaves a credible module site, the [geometry screen](../../buildslate/cellular_fit.py) uses one public, unselected 5G reference: Quectel `RG255C-GL`.

Quectel's [RG255C Series specification, revision 1.1](https://www.quectel.com/content/uploads/2024/03/Quectel_RG255C_Series_5G_Module_Specification_V1.1.pdf) lists a 29 × 32 × 2.4 mm LGA outline, 3.3–4.3 V supply, USB 2.0 and other host interfaces, two cellular antenna ports, and optional VoNR/VoLTE. The specification calls the series industrial/commercial and marks listed carrier and regulatory certifications as in progress. The exact voice-enabled variant, firmware, carrier support, handheld suitability, power transients, and current certification state require supplier confirmation. This reference is **not** a selected modem or a phone-function proof.

## Current board result

| Screen | Result |
| --- | --- |
| Provisional board outline | 78 × 55 × 0.8 mm |
| Nominal component boundary | 74 × 51 mm, 2 mm inset |
| Public module outline | 29 × 32 mm, both in-plane orientations tested |
| Assumed minimum package-to-package gap | 1 mm |
| Component side | No outline position among four 16 GB memory outlines and current non-memory planning rectangles |
| Reverse side | No outline position among the four 16 GB memory outlines, even with no other reverse-side components counted |

The screen tests boundary coordinates and obstacle edges where an axis-aligned rectangle can first fit. It checks both module rotations and both board sides. This is a necessary 2D package test, not land-pattern, escape-routing, or enclosure clearance. Run `python -m buildslate.cellular_fit` for exact machine-readable inputs and results. The public [Hardware view](https://superflyad.github.io/BuildSlate/?tab=hardware) reports `outline_blocked`.

The result means this particular 5G reference cannot simply be added to the present 128 GB concept board. The wider-body or display decision may create room for a board redesign, but board area alone does not establish the memory topology, X2 host interface, modem power, RF feeds, SIM/eSIM, audio, antennas, regulatory compliance, or a working phone. A different module could have a different result. The [phone-function gate](build_to_function.md) stays blocked until a selected design and physical results exist.

## Next design evidence

1. Obtain the supported 128 GB compute and memory reference design, then redesign board placement around the selected packages and required escapes.
2. Establish target markets and operators; request a voice-enabled modem variant, host/audio/SIM design files, power transient limits, antenna requirements, and current carrier/regulatory scope.
3. Bind the selected module to the released BOM, schematic, routed board, RF design, firmware, and full assembly with measured clearances.
4. Build a serialized unit and record registered calls, audio in both directions, data transfer, emergency-call behavior, RF exposure, and required approvals under reviewed test procedures.
