# Battery Cell and Complete-Pack RFQ

Status: **Prepared, not sent**  
Initial target: **Enovix AI-1/custom smartphone cell team**

## Purpose

Determine whether a supplier-backed flat lithium-ion cell and complete pack can meet the Slate Pocket v1R energy, envelope, safety, lifecycle, and thermal requirements. A lower-capacity proposal is explicitly acceptable when the 6000 mAh target cannot be supported safely.

## Device context

- Device envelope: 180 × 95 × 9.5 mm.
- Complete battery-pack allocation: no more than 28,824 mm³ before CAD refinement.
- Target: 6000 mAh at approximately 3.85 V nominal, or 23.1 Wh.
- Calculated complete-pack density pressure: approximately 801 Wh/L before non-cell overhead.
- Current public-source direction: Enovix AI-1-class custom flat cell.
- Battery safety, lifecycle, and validated charging limits take precedence over capacity and charge-power headlines.

## Requested proposals

Please propose at least two options when possible:

1. Highest defensible capacity within the complete-pack allocation.
2. Lower-risk option prioritizing cycle life, swelling margin, availability, and qualification maturity.

For each option, provide the response-template fields and identify whether each value is public, NDA-restricted, measured, modeled, or preliminary.

## Required engineering data

- Minimum, typical, and end-of-life energy and capacity; nominal/minimum/maximum voltage.
- Cell body, tabs, seals, protection, sensing, insulation, restraint, adhesive, and complete-pack dimensions with tolerances.
- Thickness and planform change versus state of charge, cycle count, temperature, storage, and abuse conditions.
- Mass, center-of-mass information if asymmetric, AC/DC resistance, and allowable compression.
- Continuous and pulse discharge limits with duration, temperature, state of charge, and cycle-life conditions.
- Recommended charge curve, maximum validated charge rate and power, thermal limits, fast-charge degradation, and charger requirements.
- Cycle-life curves, calendar aging, storage limits, low/high-temperature behavior, and derating.
- Safety architecture, protection requirements, failure modes, transport status, and applicable certification evidence.
- Sample maturity, custom-development scope, qualification plan, production site, yield maturity, lead time, MOQ, pricing basis, and lifecycle.

## Decision thresholds

- The complete pack—not bare-cell volume—must fit the proposed envelope.
- 100 W is not mandatory. Quote only supplier-validated charging levels and state the charge-time/cycle-life tradeoff.
- A claimed 6000 mAh solution must include full geometry, swelling, protection, and safety evidence.
- Any unsupported field remains `unknown`; it is not an assumed pass.

## Requested deliverables

- Completed YAML response template.
- Datasheet and mechanical drawing with revision identifiers.
- Pack construction proposal and tolerance/swelling stack.
- Charge/discharge and lifecycle data under stated conditions.
- Safety/certification matrix and sample/production plan.

This request is exploratory and does not constitute a purchase commitment or component selection.
