# Composite Chassis Strategy

Slate likely requires mixed-material construction rather than a single perfect chassis material. A phone-class AI device has conflicting needs: a stiff enclosure, a heat path from the SoC and power electronics, RF-transparent antenna windows, manufacturable joints and coatings, and mass low enough to fit a handheld target. The composite chassis model exists to quantify those tradeoffs before CAD and supplier data are mature.

## Why mixed materials are likely

A continuous metal shell can be mechanically useful and thermally attractive, but it can block or detune antennas. A fully glass, ceramic, or polymer enclosure can improve RF transparency, but it does not spread heat well enough for sustained local compute without a separate heat path. A plausible Slate architecture therefore needs some combination of:

- an internal aluminum, magnesium, or hybrid metal heat frame;
- RF-friendly glass, ceramic, or polymer windows near antenna volumes;
- graphite sheets for in-plane heat spreading;
- copper straps, copper foils, or vapor-chamber structures to move heat from hotspots;
- adhesives, coatings, insulation, fasteners, and isolation gaps that are not captured by a simple volume model.

## Material tradeoffs

### Aluminum

Aluminum is strong for phone-scale heat spreading and is broadly manufacturable. It is a useful candidate for internal frames, midplates, and heat-spreading structures. The drawback is RF behavior: aluminum is conductive and RF-hostile unless the design includes antenna breaks, nonmetal windows, tuned slots, isolation gaps, or separate antenna modules.

### Magnesium

Magnesium lowers mass versus aluminum for the same nominal volume, which is attractive when the product has a tight mass budget. However, magnesium conducts less heat than aluminum and introduces manufacturing, corrosion, coating, joining, galvanic compatibility, and process-safety concerns. It should be treated as a candidate that needs supplier and process validation, not as a simple drop-in replacement.

### Glass, ceramic, and polymer

Glass, ceramic, and polymer sections can help RF transparency and wireless communication paths. They are useful for antenna windows, rear-cover regions, inserts, and isolation features. Their thermal penalty is significant: they are generally poor heat spreaders compared with aluminum, copper, or in-plane graphite, so they need a dedicated internal thermal path if sustained compute or charging heat is expected.

### Graphite sheets

Graphite sheets can spread heat very well in-plane, making them useful for moving hotspot heat across a larger area. That benefit is directionally dependent. Through-thickness conduction, contact resistance, adhesive layers, bends, cutouts, nearby RF keepouts, and electrical insulation can dominate real performance. The model therefore treats graphite conductivity as a screening value only.

### Copper and vapor-chamber paths

Copper and vapor-chamber paths can move hotspot heat effectively and are common candidates for local thermal hardware. The mass cost rises quickly because copper is dense. Copper should usually be reserved for targeted heat straps, vapor-chamber walls, shields, coils, or local spreaders rather than broad structural shell volume.

## What the model estimates

`engineering/models/composite_chassis.py` estimates:

- material volume by class;
- mass by material from density and volume;
- total composite volume and mass;
- volume fractions;
- RF-friendly material percentage;
- metal percentage;
- thermal-path material percentage;
- weighted thermal conductivity as a crude screening approximation;
- a simplified one-dimensional conduction estimate using `Q = k * A * deltaT / L`.

Weighted conductivity is a screening approximation only. It does not represent true anisotropic heat spreading, layered stack orientation, vapor-chamber two-phase behavior, thermal contact resistance, adhesive bond lines, fastener conduction, local hotspots, skin-temperature limits, or the antenna impact of conductive sheets.

## Validation required before material selection

The goal is not to select a final material yet and not to claim that a composite stack proves feasibility. The goal is to quantify tradeoffs so the design team can decide which architectures deserve deeper modeling.

Real validation requires:

- CAD volume reservation for the frame, windows, thermal hardware, antennas, battery, PCB, speakers, cameras, seals, and fasteners;
- thermal contact modeling for TIMs, adhesives, graphite interfaces, vapor-chamber contacts, and mechanical preload;
- antenna layout and RF simulation with keepouts, windows, hand effects, coatings, and nearby conductive graphite/copper layers;
- structural and drop analysis for glass, ceramic, polymer, magnesium, aluminum, joints, and cutouts;
- manufacturability review for casting, machining, stamping, coating, bonding, corrosion control, and assembly yield;
- eventually CFD/FEA and prototype measurements to replace the first-order screening assumptions.

Use the model to compare architectures, identify mass/RF/thermal risks early, and preserve uncertainty. Do not use it as a production thermal model or as proof that any Slate enclosure architecture is ready for manufacture.
