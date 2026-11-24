# Display Module RFI

Status: **Prepared, not sent; body and display geometry decision required**
Targets: **BOE, Tianma, Samsung Display**

## Purpose

Identify the closest supplyable display module to Slate Pocket's 7.5-inch 16:10 workspace outcome and obtain enough mechanical, electrical, optical, power, thermal, and lifecycle data for CAD.

## Target and allowed trade space

- Source intent: 7.5-inch, 16:10, 3200 × 1800, 120 Hz, LTPO AMOLED. These values are not a coherent single panel requirement: 3200 × 1800 is 16:9.
- Current 180 × 95 mm body and 174 × 89 mm CAD display reserve cannot hold a 7.5-inch 16:10 active rectangle of 161.544 × 100.965 mm. The 7.0-inch lower search bound also exceeds the current 89 mm reserve at 16:10. See the [active-area screen](../../../docs/engineering/display_geometry_fit.md).
- The product owner must approve a body-width, diagonal, aspect, or resolution change before a production panel target is frozen. Please state the exact active and module outlines for each proposed trade; do not treat the present body and panel targets as simultaneously feasible.
- Acceptable search range: approximately 7.0–8.4 inches.
- Small changes to diagonal, resolution, refresh rate, or panel technology are allowed when they preserve the workspace intent and materially improve availability, power, integration, or lifecycle.
- Flat modules are preferred. Foldable panels may be proposed only with complete support/cover-stack and durability requirements.

## Required engineering data

- Active area, module outline, thickness and tolerances, corner radii, bezel, cover-stack assumptions, and mass.
- Flex location, bend/keepout rules, connector, pinout, interface, lane count, timing, driver IC, initialization, and touch integration.
- Resolution, subpixel layout, refresh modes, LTPO range, luminance, contrast, color gamut, HDR, viewing angle, and PWM/dimming behavior.
- Power curves versus luminance, content, refresh rate, ambient mode, and temperature; peak and sustained thermal limits.
- Under-display camera compatibility if available, optical transmission, mura/uniformity limits, aging/burn-in behavior, and compensation.
- Shock, drop, bend, torsion, humidity, temperature, ESD, and lifetime qualification.
- Sample/production status, customization/NRE, MOQ, lead time, price basis, lifecycle, PCN/EOL policy, and geographic restrictions.

## Requested proposals

1. Closest production module to the target.
2. Lower-power or higher-availability fallback.
3. EVT module available soonest, even if resolution or technology differs.

## Decision thresholds

- A part without a mechanical drawing, flex/interface definition, and power curves cannot enter detailed CAD.
- Demonstration panels are not production candidates unless sample and lifecycle status are stated.
- Deviations must be explicit and tied to product impact.
- No proposed panel is accepted merely because its diagonal is in range; the complete module and flex must fit the approved enclosure revision.

This request is exploratory and does not constitute a purchase commitment or module selection.
