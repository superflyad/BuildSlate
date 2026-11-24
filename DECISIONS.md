# Design decisions

## ADR-001: Keep evidence status in the existing registries

**Status:** Accepted

The viewer reads generated status and part provenance. It does not assign verified, selected, or released status. This prevents a visually complete model from being mistaken for an approved design.

## ADR-002: Generate provisional geometry from controlled inputs

**Status:** Accepted

The first 3D model uses the existing mechanical and PCB planning rectangles. A small assembly manifest supplies the missing names and z positions. The generator exports JSON for inspection and glTF for geometry. All current solids remain explicitly provisional.

## ADR-003: Keep the browser interface read only

**Status:** Accepted

The viewer can filter, inspect, hide, explode, and rotate the assembly. It cannot alter device profiles, evidence, or decisions. Engineering changes go through the repository's validated source files and regeneration flow.

## ADR-004: Treat the viewer as a local static application

**Status:** Accepted

Vite produces a static build with no server-side account or database. This keeps the engineering data reviewable from a checkout. The Python generator owns asset currency; the web build owns presentation.

## ADR-005: Enforce repository wiring in CI

**Status:** Accepted

Every `validation/validate_*.py` script must be registered in the suite. CI also checks local documentation links, placeholder READMEs, pinned Python requirements, undefined and unused Python names, repository-wide Python formatting, generated currency, and the viewer build. This closes a gap where three existing validators were present but not executed.

## ADR-006: Package code separately from engineering inputs

**Status:** Accepted

The Python wheel contains the CLI and its runtime dependency. Engineering files remain in a checkout selected by `--repo-root`; the package does not snapshot or promote source evidence. CI tests the installed command from outside the checkout. Software tags identify code and viewer builds, while the program dashboard retains engineering gate authority.

## ADR-007: Separate visual inspection from engineering validation

**Status:** Accepted

Section cuts, isolation, focus, and expanded view operate only on generated planning geometry in the browser. The component library is shown in full, including roles without geometry. These controls expose the model's limits; they do not create a fit, interference, or release result. A geometry count mismatch stops loading rather than silently presenting an incomplete assembly.

## ADR-008: Keep the 128 GB reference layout separate from the baseline

**Status:** Accepted

The exact public 16 GB memory package needs eight outlines to reach the approved 128 GB capacity. The baseline retains four assumed 32 GB sites. A separate CAD variant replaces those four solids with eight two-sided reference boxes and receives its own STEP, glTF, and proof report. This allows geometry review without treating the public package as X2-qualified or silently changing the baseline board architecture. The thickness discrepancy, routing, power, thermal path, and boot proof remain unresolved.
