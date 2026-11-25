# Changelog

Changes to the BuildSlate software and repository workflow are recorded here. Engineering claim status remains in the generated program dashboard and source registries.

## Unreleased

- Screen an exact production-cataloged compact Micron 16 GB LPDDR5X package and its separate eight-package editable CAD and browser proof; publish the improved nominal fit and the still-blocked X2 topology, height, routing, and procurement status.
- Reject selected-part and platform-reference supplier files whose bytes do not parse as PDF or match their declared STEP or ZIP format, even when release hashes are updated to match the mislabeled file.
- Screen Hongguang's preliminary HG070FH002 display drawing against the body and CAD reserve; publish its nominal overrun and format mismatch in hardware readiness, with the target and design release still blocked.
- Allow a source-bound 128 GB memory-on-package release path with exact compute SKU capacity and internal DRAM map, while rejecting a 48 GB package or on-package DRAM represented as separate board parts.
- Record ASUS's 48 GB X2 memory-on-package configuration and physical three-package analysis; distinguish the external 128 GB CAD study from an orderable X2 package.
- Audit released interconnect pin maps against the KiCad netlist, controlled cable drawings, selected BOM, routed board, and mechanical assembly; expose missing status in the public viewer.
- Add an editable 46-solid phone integration collision study and exact CAD proof of board, camera, speaker, haptic, and modem overlaps in the public viewer.
- Screen the minimum whole-millimeter board extension for the public 5G reference and identify its camera and speaker collisions in the full enclosure.
- Require hashed lifecycle source evidence for every selected BOM role and correct the build-to-function memory summary.
- Record and reject an exact obsolete 32 GB Micron LPDDR5X part; show its four-site and 192-bit bus conflicts in hardware readiness.
- Screen a public 5G voice-optional module outline against both sides of the 128 GB concept board and publish the unresolved phone package conflict.
- Require hash-bound, build-matched raw phone test records before the phone-function evidence gate can become review ready.
- Added a display active-area fit gate: the 7.5-inch 16:10 target exceeds the current body and CAD reserve, and the source 3200×1800 resolution is 16:9; design release remains blocked pending an approved geometry decision.
- Added a platform reference audit that binds selected compute, memory, storage, and PMIC sources to the electrical BOM and an explicit 128 GB channel, rank, and data-lane map; public release status remains missing.
- Published the X2 Extreme 192-bit versus eight x64 package bus-width screen in hardware readiness; independent wiring fails the width check, while shared-channel qualification remains unresolved.
- Bound 128 GB selected-memory topology claims to exact compute and memory MPNs, package count and capacity, and hashes of the controller support and compute reference-design sources; a controller maximum alone cannot pass part selection.
- Added an RF release audit for selected radio and antenna parts, host and firmware compatibility, schematic matching paths, released edge placement, Touchstone impedance and isolation sweeps, radiation efficiency, coexistence, and market scoping; public status remains missing.
- Added a geometry- and power-bound thermal release audit with source-backed material and boundary properties, case heat maps, mesh and energy checks, supplier temperature limits, and public missing status.
- Added a released power-design audit for selected pack ratings, charge input and conversion budget, complete rail and battery current loads, sequencing, fault-control declarations, and approved BOM/board bindings; public status remains missing.
- Bound routed PCB proof to the approved KiCad project settings and rejected DRC exclusions, disabled critical rules, zero fabrication minima, and report findings across all three DRC categories.
- Made ERC evidence reproducible from the released KiCad schematic and hashed project settings, with a clean JSON report and no excluded or ignored critical rules.
- Required a controlled firmware bundle with hashed images, boot/recovery sequence, driver coverage, flash readback plan, and approved BOM/PCB bindings before firmware evidence can enter the hardware gate.
- Added nominal camera pupil path checks, then revised the concept rear cover and front display/touch openings to clear the assumed pupils; supplier optics and physical qualification remain open.
- Added exact nominal contact and small-gap findings to both CAD proof reports and the public viewer.
- Made routed PCB proof export and require every configured copper layer; a missing internal Gerber now blocks release.
- Strengthened the guarded 128 GB memory exercise to write and verify every allocated byte and made M20 reject page-marker-only probe evidence.
- Aligned the provisional v1R mechanical PCB with the 0.8 mm floorplan and compute-zone stack; added a cross-domain thickness contract.
- Added a separately proofed eight-package 128 GB reference CAD variant and 3D viewer switch; kept the fabrication and hardware qualification gates blocked.
- Added per-solid CAD proofing with anchored source checks, BREP/mesh bounds, STEP round-trip volume, exact intersections, planform keepouts, and local stack results; exposed findings in the viewer.
- Detailed the concept board, packages, battery tray, cameras, speakers, rear cover, frame, and gasket while preserving each added feature's assumption status.
- Published the concept CAD viewer through GitHub Pages after the validation and CAD export jobs pass.
- Added a 41-solid editable Slate Pocket v1R concept STEP assembly generated from the source envelopes and explicit assumptions for every component library role.
- Added a matching browser CAD view, preserved the source-envelope comparison, and validated geometry identity, coverage, and regeneration in CI.
- Completed the assembly review controls with an expanded canvas, axis section cuts, part focus and isolation, and navigation across every component library role; kept unplaced and deferred roles explicit.
- Made viewer asset loading follow the configured Vite base path and reject mismatched JSON and glTF part counts at runtime.
- Reworked the README, architecture, contribution, viewer, and documentation guides around the actual review and change workflows; added a schematic cover and mobile-friendly repository entry points.
- Indexed all active engineering guides and added a documentation coverage check; expanded CI to Windows and strengthened maintained Python checks.
- Made generated text writers use LF consistently so Windows validation does not dirty tracked reports.

## 0.1.0 - 2026-11-19

- Added an installable Python CLI for reading and validating a BuildSlate data checkout from any working directory.
- Added a provisional 3D assembly viewer with source and evidence context. Its solids remain planning envelopes.
- Established repository-wide Python formatting, static checks, documentation linting, deterministic regeneration checks, and installed-package verification in CI.
- Added contributor, support, security, and release procedures.
