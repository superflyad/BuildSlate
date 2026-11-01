# Battery Evidence Review — Phase 1

Reviewed: 2026-10-31  
Status: **Public evidence available; supplier package not verified**

## Decision

Retain 6000 mAh as a conditional target and open a custom-cell conversation with Enovix. Do not select a battery yet. Treat 100 W wired charging as unsupported until a supplier approves the charge curve, heat, cycle life, and complete pack.

## What the public evidence proves

- The v1R allocation asks a complete 23.1 Wh pack to fit in 28.824 cm³, or about **801 Wh/L before any pack overhead**.
- Enovix publishes an AI1-M01 preview at 7.35 Ah and 921 Wh/L with an 80 × 66.74 × 5.44 mm cell envelope. That establishes a credible high-density supplier conversation, but the published cell itself occupies about 29.045 cm³—slightly more than the entire v1R pack allocation.
- A hypothetical 23.1 Wh cell at 921 Wh/L would occupy about 25.08 cm³, leaving about 3.74 cm³, or 13%, for every non-cell requirement. Supplier-specific geometry and pack CAD are still required.
- Amprius and Panasonic publish 6 Ah cylindrical cells. They confirm that 6 Ah cells exist, but their roughly 21.7 mm diameters fail the 9.5 mm device envelope.
- The 100 W target is approximately 4.33C against a 23.1 Wh pack. The reviewed public candidates list no comparable validated charge rate: Enovix AI1-M01 lists up to 2C and Amprius SA117 lists 0.7C.

## What remains missing

- A supplier-approved flat cell near 23.1 Wh with Slate-compatible length, width, thickness, tabs, and swelling behavior.
- Complete pack dimensions including protection, sensing, restraint, insulation, adhesive, and clearance.
- Charge/discharge curves, impedance, thermal behavior, cycle life, safety test evidence, price, minimum order quantity, and production lifecycle.
- A supplier commitment that the custom geometry can be sampled and produced.

## Supplier action

Request an Enovix product brief and engineering discussion for a custom AI-1 cell. The request should specify the 23.1 Wh target, 9.5 mm device envelope, 28.824 cm³ complete-pack ceiling, expected sustained/peak system load, desired charging time, temperature cases, and lifecycle target. Ask for a lower-risk capacity option in the same mechanical envelope.

## Primary sources

- [Enovix AI platform product data](https://www.enovix.com/product-category/ai-platform)
- [Enovix independent AI-1 density announcement](https://ir.enovix.com/news-releases/news-release-details/independent-testing-confirms-enovix-ai-1tm-achieves-935-whl/)
- [Enovix Q1 2026 qualification update](https://ir.enovix.com/news-releases/news-release-details/enovix-reports-first-quarter-2026-results)
- [Amprius product catalog](https://amprius.com/documents/Amprius_Product_Catalog.pdf)
- [Panasonic NCR2270B product page](https://energy.panasonic.com/na/business/products/lithium-ion/cylindrical-mid-rate/models/NCR2270B)

This review is a public-source screen, not a supplier quote, cell selection, safety approval, or pack validation.
