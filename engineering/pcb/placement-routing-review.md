# Slate Pocket v1R Placement, Routing, and Power Review

Status: provisional architecture screen; blocked before schematic or layout release.

## Review outcome

The 78 x 55 mm board placeholder can contain the current planning rectangles without same-side overlap. That is not a routing result. Only about half of the component-side planform is occupied by the listed blocks, but the remainder must absorb escape routing, passives, shields, connectors, flexes, test access, RF isolation, mechanical keepouts, and manufacturing clearances.

The only memory configuration modeled is the locked 128 GB fallback: four 32 GB planning sites around the compute package. Public supplier evidence supports 32 GB package capacity, but the exact package drawings, controller topology, pinout, signal rules, power, and platform qualification are missing. The 512 GB target is not carried into this floorplan.

The 1 TB UFS outline is a public geometry reference. A 2 TB product fallback would require a second qualified device or another architecture; 4 TB remains unsupported by the reviewed embedded candidates. Neither multi-device host support nor routing has been established.

## Routing posture

The 12-layer, 0.8 mm HDI stack is an assumption used to expose fabrication pressure. It is not a vendor stackup. Memory escape and matching, storage link integrity, display/camera interfaces, RF feeds, USB, debug, test, and security partitioning cannot be reviewed until the platform and peripheral pin maps exist.

Before layout release, the team must review the preliminary netlist, pin swaps, breakouts, return paths, reference-plane transitions, via structures, impedance/loss budgets, length and skew rules, crosstalk limits, ESD paths, test coverage, and fabrication coupons.

## Power posture

The conservative sustained screen totals compute, 128 GB memory, storage, display, radios, and system controls. It drives a battery-current estimate well above the level that can be accepted without a selected pack, protection path, connector system, regulator design, and thermal map. The peak-all-subsystems case is a boundary condition, not an allowed operating mode.

The 100 W wired and 50 W wireless figures remain unsupported targets. Full-power charging plus sustained AI is prohibited by the provisional policy. EVT0 starts with wireless charging disabled and a 30 W wired-input cap, with the supplier's lower limit always controlling. Even that cap is not authorized until a selected battery, charger, cable, connector, protection design, and thermal test plan exist.

## Exit conditions

- Replace every planning rectangle with approved package and keepout data.
- Obtain the platform reference schematic, ball map, memory topology, rail map, power sequence, and load-step data.
- Select the storage architecture and prove host support at the chosen capacity.
- Complete schematic, netlist, escape, stackup, SI/PI, PDN, protection, and testability reviews.
- Correlate power losses and charge limits with the mechanical and thermal models.
- Record signoff from electrical, layout, mechanical, thermal, RF, firmware, battery-safety, test, and manufacturing owners.

This review does not prove electrical feasibility, routing closure, signal integrity, power integrity, charging safety, thermals, manufacturability, or component availability.
