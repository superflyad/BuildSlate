# Roadmap

## Repository quality

- [x] Curated documentation index, archive boundary, and directory ownership rules
- [x] All validators registered; local links, placeholder READMEs, and dependency pins checked in CI
- [x] Python name analysis and formatting gate across the repository
- [x] Contributor issue routes, support and security policies, and editor defaults
- [ ] Establish a package/install contract and verify commands outside the repository checkout
- [ ] Add documentation style checks with a clean baseline for maintained guidance
- [ ] Define versioned releases and a changelog once a supported interface is ready
- [ ] Expand static analysis beyond name errors after the legacy modules are migrated
- [ ] Define a reviewed import contract for supplier and released CAD geometry

## Current release: provisional assembly review

- [x] Stable part IDs and a documented coordinate system
- [x] Generated JSON and glTF from existing engineering sources
- [x] Viewer with rotation, selection, filtering, cutaway, explode, keepouts, and gate context
- [x] Generation and build checks in CI

## Next engineering inputs

- Supplier complete-pack battery drawing and protection geometry
- Selected compute and memory package drawings, reference design, and routing constraints
- Selected display, camera, storage, connector, speaker, and antenna drawings
- Released mechanical sections, tolerances, fasteners, seals, and assembly sequence
- Routed ECAD and measured thermal/RF data

Replace a provisional solid only when the source includes revision, units, coordinate frame, geometry license, and engineering review. The [program dashboard](reports/program/dashboard.md) tracks external blockers and gates.

## Future viewer capabilities

- Import reviewed supplier and design meshes alongside planning envelopes
- Cross-section tools and interference overlays tied to the mechanical validation result
- Electrical and thermal paths tied to released netlists and measured data
- Build and service sequences tied to authorized manufacturing instructions

These require source data that is not yet present. They are not represented as completed engineering work.
