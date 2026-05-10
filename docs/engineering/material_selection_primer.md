# Material Selection Primer

Phone-class AI devices are packaging-limited systems. The enclosure material is not just a cosmetic choice: it changes mass, thermal headroom, durability, antenna design, bonding reliability, manufacturability, cost, and repair strategy. BuildSlate treats material selection as a tradeoff space rather than a single-material optimization.

## Why material choice matters

A chassis or rear housing usually participates in several jobs at once:

- It carries bending, drop, torsion, and point-load stresses.
- It sets a large fraction of the product's perceived weight and feel.
- It can spread heat from the SoC, memory, charging coil, battery, and power electronics.
- It can block, detune, or enable antennas and wireless charging.
- It defines bonding, fastening, gasketing, coating, and repair constraints.

Because these jobs conflict, a material that is good for one requirement can be poor for another.

## Density affects mass

Density converts part volume into mass. For a fixed chassis volume, a denser material directly increases enclosure mass unless wall thickness or geometry can be reduced enough to compensate. Magnesium can reduce mass relative to aluminum, titanium, steel, or dense ceramics. Steel and copper can become unacceptable if used over large shell volumes, even when they are useful for small brackets, fasteners, shields, or thermal parts.

## Thermal conductivity affects passive heat spreading

Thermal conductivity controls how effectively a material spreads heat from a hotspot to a larger surface area. Higher conductivity helps reduce local hot spots, but it does not remove heat by itself; the device still needs surface area, acceptable skin temperature, radiation/convection paths, and good thermal interfaces.

A simplified screening relation is:

```text
Q = k * A * deltaT / L
```

where `Q` is heat transfer in watts, `k` is thermal conductivity, `A` is cross-section area, `deltaT` is temperature difference, and `L` is heat-path length. This relation is useful for comparisons but ignores contact resistance, anisotropy, heat spreading geometry, and user-touch limits.

## Stiffness and yield strength affect durability

Young's modulus indicates stiffness: higher stiffness generally reduces deflection for the same geometry. Yield strength indicates the stress where permanent deformation begins. These properties matter for pocket bending, drops, screw bosses, button cutouts, camera islands, and display support.

Strength alone is not enough. A strong but heavy or thermally poor material can still be a bad fit for a given phone-class package. Geometry, wall thickness, ribs, bonding, and local reinforcements can matter as much as raw material strength.

## RF behavior affects antenna design

Metals such as aluminum, magnesium, titanium, steel, and copper block or attenuate RF energy. Metal enclosures usually require antenna windows, frame breaks, isolation gaps, tuned slots, plastic sections, or nonmetal rear covers. These features can conflict with stiffness, cosmetics, water resistance, and manufacturing yield.

Glass, glass-ceramic, many ceramics, and many polymers are generally more RF-friendly than metals, but they still need validation for thickness, additives, coatings, adhesives, and nearby conductive layers.

## Coefficient of thermal expansion affects bonding and reliability

Coefficient of thermal expansion describes how much a material expands with temperature. Mismatches between glass, metal, ceramic, PCB, adhesive, and battery structures can stress bonds and solder joints during charging, compute workloads, environmental cycling, and drop events. A material stack that looks acceptable at room temperature can fail after repeated thermal cycling if expansion mismatch, adhesive modulus, and bond-line thickness are not controlled.

## Premium feel can conflict with thermal and RF requirements

Premium feel is a system outcome rather than a single property. Dense, hard, glossy, or cool-to-touch materials may feel premium, but those same properties can increase mass, reduce impact tolerance, block antennas, or impair passive heat spreading. Cosmetic requirements should therefore be reviewed alongside mass, thermal, RF, structural, manufacturing, repairability, and cost requirements.

## Common phone-class material tradeoffs

### Titanium

Titanium alloys can be strong, corrosion-resistant, and premium-feeling, but titanium is not automatically better. It is denser than aluminum and magnesium, is relatively poor at passive heat spreading, can be difficult and costly to machine or form, and remains conductive enough to create RF antenna challenges. Titanium may make sense for specific high-strength features, but it should not be assumed to improve the whole device.

### Aluminum

Aluminum alloys are thermally useful and broadly manufacturable. They can be strong enough for many frame and housing structures while remaining much lighter than steel or copper. However, aluminum is RF-hostile: a continuous aluminum shell or frame can block or detune antennas unless the design includes antenna breaks, nonmetal windows, isolation, or tuned structures.

### Magnesium

Magnesium alloys are attractive where mass is highly constrained. Their low density can reduce chassis mass, but magnesium brings concerns around corrosion protection, coating durability, lower stiffness than aluminum, joining, galvanic compatibility, and manufacturing fire risk from chips or dust. Magnesium requires careful process and supplier validation rather than a simple material swap.

### Stainless steel

Stainless steel is strong, stiff, durable, and cosmetically familiar, but it is heavy and thermally mediocre compared with aluminum or copper. It can be useful for local high-strength parts, edge bands, brackets, or fasteners, but broad use in large shell volumes can quickly consume the mass budget.

### Ceramic and glass

Ceramic and glass materials can support RF and wireless charging paths better than metal housings, and they can provide scratch resistance or a premium surface. They may also complicate impact durability, edge reliability, repair, bonding, cost, yield, and passive heat spreading. Ceramic and glass backs often need separate internal heat-spreading hardware if the SoC or charging system produces substantial heat.

## How to use this primer

Use this document with:

- `engineering/ontology/material_taxonomy.yaml` for property ranges and qualitative notes.
- `engineering/constants/materials.yaml` for screening constants used by scripts.
- `engineering/models/material_compare.py` for one-material mass and conduction estimates.
- `engineering/models/material_screen.py` for a coarse multi-material tradeoff table.

No single material is universally best. BuildSlate should select or reject materials only after the target geometry, antenna layout, thermal path, mechanical load cases, manufacturability assumptions, and vendor data are explicit.
