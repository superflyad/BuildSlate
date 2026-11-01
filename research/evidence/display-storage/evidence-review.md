# Display and Storage Evidence Review — Phase 1

Reviewed: 2026-10-31  
Status: **Public evidence available; candidates not verified**

## Display decision

Issue RFQs to BOE, Tianma, and Samsung Display. No reviewed public product exactly matches the 7.5-inch, 16:10, 3200×1800, 120 Hz LTPO AMOLED target with a usable module drawing and power curve.

The public market proves that neighboring technologies exist:

- Samsung has commercialized 7.6-inch foldable OLED panels, but the reviewed 2208×1768 part is not the required 16:10 flat module.
- Tianma has demonstrated 7.92-inch LTPO foldable OLED technology, but public information is insufficient for integration.
- BOE advertises a 7.0–18.5-inch tablet portfolio and a flat 8.4-inch reference product, making it useful for an RFQ and EVT fallback even though the public listing does not establish the target OLED specification.

The Phase 1 decision is therefore to preserve the 7.5-inch workspace outcome while allowing small size, resolution, refresh, or technology changes if the RFQ cannot supply the exact target.

## Storage decision

Use 1 TB as the verified single-package market unit for architecture work. Keep 2 TB as the locked product fallback only if the selected host and board can support multiple devices or a compact NVMe solution. Do not treat 4 TB as a credible embedded package until a supplier provides a matching part.

- Samsung lists 1 TB UFS 4.1 and UFS 5.0 products; UFS 5.0 is 7.5 × 13 × 0.9 mm, with public mass-production timing in Q4 2026.
- KIOXIA lists a 1 TB UFS 4.1 package at 9 × 13 × 0.85 mm.
- Micron's reviewed 2230 NVMe family reaches 1 TB in a 22 × 30 × 1.5 mm board, which adds controller, connector/assembly, area, and thermal pressure.

No reviewed mobile product provides 2 TB or 4 TB in one package. Multiple-device support, boot architecture, power, sustained-write temperature, board space, availability, and lifecycle remain open.

## Primary sources

- [Samsung Display 7.6-inch foldable OLED](https://global.samsungdisplay.com/25871)
- [Tianma 7.92-inch LTPO demonstration](https://usa.tianma.com/wp-content/uploads/2024/12/Tianma-Smart-Phone-Technology-at-Display-Week-2024-1.pdf)
- [BOE tablet display portfolio](https://www.boe.com/en/Enterprise/TabletDisplay)
- [Samsung UFS portfolio](https://semiconductor.samsung.com/estorage/ufs/)
- [Samsung UFS 5.0 announcement](https://news.samsung.com/global/samsung-unveils-industrys-fastest-ufs-5-0-solution-for-next-gen-on-device-ai-applications)
- [KIOXIA UFS 4.0/4.1 product table](https://apac.kioxia.com/en-apac/business/memory/mlc-nand/ufs4.html)
- [Micron 2650 NVMe technical specification](https://assets.micron.com/adobe/assets/urn:aaid:aem:25c43d17-622f-4be5-a33f-8e599da55043/renditions/original/as/2650-nvme-ssd-tech-prod-spec.pdf)

This review is a public-source market screen, not a supplier quote, component selection, host-compatibility proof, or lifecycle commitment.
