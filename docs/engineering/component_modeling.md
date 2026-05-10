# Component modeling

Slate pocket v1 component modeling treats each subsystem as a range of screening values, not as an exact vendor part. The component library is intended to expose packaging pressure before the project changes dimensions, commits to CAD geometry, or makes feasibility claims.

The current component data is a placeholder model. It does not represent vendor-certified specifications, production quotations, complete electrical design, thermal simulation, measured power, or proof that the Slate pocket target is feasible.

## What the model tracks

Each component carries first-pass estimates for:

- mass
- volume
- thickness
- PCB area
- idle power
- active power
- thermal relevance
- electrical relevance
- mechanical relevance
- RF relevance
- placement constraints
- unknowns and feasibility notes

Component mass, volume, area, power, and thermal load drive feasibility because phone-class devices usually fail through combined constraints rather than a single isolated number. A component can be acceptable by mass but unacceptable by z-height, routing density, heat concentration, RF keep-out, or assembly tolerance.

## PCB area pressure

PCB area pressure matters because high utilization increases routing difficulty, layer-count pressure, shielding complexity, rework risk, and heat concentration. Dense SoC, memory, storage, PMIC, radio, connector, and security routing also creates local keep-outs that are not captured by a simple rectangular area calculation.

The packaging model therefore compares estimated component PCB area against a coarse available-board assumption. That comparison is only a screening metric; it is not a replacement for ECAD placement, high-speed routing analysis, or RF coexistence work.

## Z-height pressure

Z-height matters because thin devices fail in vertical stacking before they fail in marketing diagrams. Battery swelling allowance, display stack thickness, cover glass, touch layers, thermal interfaces, vapor chambers, camera modules, connectors, speakers, haptics, adhesives, gaskets, and tolerances all compete for the same thickness envelope.

The first-pass packaging model highlights thick rigid components and checks a simplified battery plus vapor chamber plus display stack against the target thickness. Passing this check would not prove feasibility; failing it identifies where CAD stack-up work must focus first.

## Competing internal volume

Battery, display, SoC/NPU, memory, storage, thermal module, antennas, and cameras all compete for the same internal volume. They also constrain each other:

- The battery dominates volume but needs swelling and safety allowance.
- The SoC/NPU needs short memory routing and a credible heat path.
- Memory capacity increases area, power, package count, and heat density.
- Storage and security chips consume dense PCB area near compute and power rails.
- Vapor chambers and graphite spreaders need contact area but can conflict with RF windows and wireless charging.
- Antennas require keep-out zones and RF-transparent paths.
- Cameras require optical paths and often define local z-height pockets.
- Wireless charging wants rear-surface area that may conflict with metal, antennas, thermal layers, and the battery.

## Replacement path

The placeholder component library must eventually be replaced with:

- vendor datasheets and mechanical drawings
- package drawings and keep-out requirements
- measured idle, peak, and sustained workload power
- ECAD-derived board area and routing density
- CAD-derived part volumes, tolerances, and z-stack sections
- prototype thermal measurements and validated simulation inputs
- RF measurements, antenna tuning data, and certification constraints

Until those inputs exist, component modeling should be treated as an assumption ledger and screening tool, not as feasibility proof.
