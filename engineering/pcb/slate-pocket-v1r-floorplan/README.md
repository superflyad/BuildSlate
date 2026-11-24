# Slate Pocket v1R Provisional ECAD Floorplan

This directory is a pre-supplier placement and routing pressure model for the locked Slate Pocket v1R envelope. It is not a schematic, routed board, reference design, or component selection.

The model deliberately uses the 128 GB memory fallback as four 32 GB planning sites. The reviewed public evidence does not support a 512 GB pocket topology, and no 256 GB topology is modeled. All package rectangles except the public 1 TB UFS outline are planning reserves that must be replaced by supplier drawings.

`floorplan.yaml` records:

- a 78 x 55 mm rigid-board planning outline aligned to the mechanical blocking model;
- provisional compute, memory, power, wireless, and security sites plus the public 9 x 13 x 0.85 mm KIOXIA THGJFRT3E88BATW UFS package outline;
- an assumed 12-layer 0.8 mm HDI stack and via strategy for routing-pressure review;
- interface groups, adjacency intent, edge reserves, and missing reference-design inputs.

No net names, pins, escape geometry, impedance values, trace rules, or decoupling quantities are released for layout. Those require the selected platform reference design and approved component data.

The storage outline is screened by `python -m buildslate.storage_fit`. It has only 0.5 mm nominal clearance to the component boundary and nearest planning block. That arithmetic does not account for the 153-ball land pattern, solder mask, assembly keepouts, decoupling, or escape routing. The VCC and VCCQ rails remain undefined.
