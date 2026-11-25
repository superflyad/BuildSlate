# Battery Evidence Review — Phase 1

Reviewed: 2026-11-24

Status: **Public evidence available; supplier package not verified**

## Decision

Retain 6000 mAh as a conditional target. No supplier path is preferred or selected. Enovix's November 2026 filing says it stopped system-level AI-1 smartphone field testing with its lead OEM and redirected development toward smaller cells. This does not rule out a future Slate-specific product, but it removes the basis for treating custom AI-1 as the near-term plan. Treat 100 W wired charging as unsupported until a supplier approves the charge curve, heat, cycle life, and complete pack.

## What the public evidence proves

- The v1R allocation asks a complete 23.1 Wh pack to fit in 28.824 cm³, or about **801 Wh/L before any pack overhead**.
- Enovix publishes an AI1-M01 preview at 7.35 Ah and 921 Wh/L with an 80 × 66.74 × 5.44 mm cell envelope. It is a density and geometry benchmark. The published cell itself occupies about 29.045 cm³—slightly more than the entire v1R pack allocation.
- A hypothetical 23.1 Wh cell at 921 Wh/L would occupy about 25.08 cm³, leaving about 3.74 cm³, or 13%, for every non-cell requirement. Supplier-specific geometry and pack CAD are still required.
- Amprius and Panasonic publish 6 Ah cylindrical cells. They confirm that 6 Ah cells exist, but their roughly 21.7 mm diameters fail the 9.5 mm device envelope.
- The 100 W target is approximately 4.33 times the target pack's nominal 23.1 Wh energy per hour. Enovix's AI1-M01 listing places “up to 2C” under **maximum continuous discharge**, so it does not establish a charge limit for that cell. Amprius SA117 lists a 0.7C maximum charge rate, but its cylindrical shape cannot fit this device. No reviewed public source validates 100 W charging for a Slate-fit cell.

## What remains missing

- A supplier-approved flat cell near 23.1 Wh with Slate-compatible length, width, thickness, tabs, and swelling behavior.
- Complete pack dimensions including protection, sensing, restraint, insulation, adhesive, and clearance.
- Charge/discharge curves, impedance, thermal behavior, cycle life, safety test evidence, price, minimum order quantity, and production lifecycle.
- A current supplier path and commitment that a Slate-fit pack can be sampled and produced.

## Supplier action

Screen current flat-cell manufacturers for a complete pack with a documented charge window and realistic production path. A future supplier inquiry should specify the 23.1 Wh target, 9.5 mm device envelope, 28.824 cm³ complete-pack ceiling, expected sustained and peak system load, desired charging time, temperature cases, and lifecycle target. Ask for a lower-risk capacity option in the same mechanical envelope. No inquiry has been sent.

## Primary sources

- [Enovix AI platform product data](https://www.enovix.com/product-category/ai-platform)
- [Enovix independent AI-1 density announcement](https://ir.enovix.com/news-releases/news-release-details/independent-testing-confirms-enovix-ai-1tm-achieves-935-whl/)
- [Enovix Q1 2026 qualification update](https://ir.enovix.com/news-releases/news-release-details/enovix-reports-first-quarter-2026-results)
- [Enovix November 2026 Form 10-Q, smartphone program update](https://ir.enovix.com/static-files/1557353f-642c-46da-a6d1-751d46e16aeb)
- [Amprius product catalog](https://amprius.com/documents/Amprius_Product_Catalog.pdf)
- [Panasonic NCR2270B product page](https://energy.panasonic.com/na/business/products/lithium-ion/cylindrical-mid-rate/models/NCR2270B)

This review is a public-source screen, not a supplier quote, cell selection, safety approval, or pack validation.
