# Feasibility Methodology

BuildSlate separates source intent from validated engineering data. The Slate v1 PDF is treated as the canonical source-intent document: it captures the target product concept, industrial-design direction, and desired subsystem capabilities. It does not, by itself, prove that every target can be manufactured in the stated form factor.

Normalized YAML specifications capture the engineering assumptions derived from that source intent. The YAML layer gives downstream tools stable field names for dimensions, memory capacity, compute targets, battery assumptions, security features, and feasibility labels.

Python scripts derive first-order estimates from the normalized specs. These scripts are intentionally simple: they estimate model memory, runtime, heat density, and packaging constraints so contradictions become visible early. A script warning is not a final engineering verdict, but it is a prompt to refine assumptions with measured data, vendor information, CAD volume studies, or thermal simulation.

Feasibility labels prevent overclaiming. BuildSlate uses conservative validation wherever possible and marks each major subsystem with one of the following statuses:

- `feasible_today` means the capability is commercially available or demonstrably manufacturable with current technology, though integration work may still be required.
- `near_term` means the direction is credible with current or emerging parts, but Slate-specific integration, thermals, sourcing, or packaging remain unresolved.
- `conceptual_extrapolation` means the direction appears physically plausible, but it should not be described as commercially available today in the target form factor.
- `research_required` means there is not enough evidence yet to claim feasibility; more modeling, vendor data, experiments, or prototypes are required.

The goal is not to prove Slate is buildable today. The goal is to identify exactly what must become true for Slate to be buildable: which densities must improve, which power envelopes must close, which thermal paths must be demonstrated, and which package volumes must be reserved in CAD.
