# Released selected BOM proof

The [part selection auditor](../../buildslate/part_selection.py) reads `engineering/hardware/released/selected-bom.json`. That file does not exist yet. Candidate comparison files and the [EVT0 sourcing strategy](../../validation/evt0/bom-strategy.yaml) do not select components.

The release file must identify `schema_version: 1`, `device: slate-pocket-v1r`, a revision, a named engineering reviewer, and a `parts` object containing exactly the five core roles. Add `cellular` only after that role is changed through the approved configuration process. The `selected_bom` evidence record in [readiness.yaml](../../engineering/hardware/readiness.yaml) must name this exact JSON file, match its SHA-256, revision, and reviewer, and carry an approved disposition.

Each part entry needs its manufacturer, exact manufacturer part number (`mpn`), revision, `lifecycle: active`, positive integer quantity, machine-readable capabilities, and an `evidence` mapping. Separately purchased parts need `availability: purchasable`. DRAM included in the selected compute package instead needs `availability: included_in_compute_sku`, with the compute SKU itself purchasable. The strategy's `selected_candidate` must equal the released MPN and `selected_parts` must equal the number of selected roles. Every selected role requires a lifecycle source, including compute, memory, battery, and cellular. Each required evidence key in the sourcing strategy must map to a source file under `engineering/hardware/released/parts/<role>/` with a matching SHA-256. Accepted source containers are PDF, STEP, and ZIP. The [source screen](../../buildslate/supplier_source.py) parses each PDF with `pypdf`, checks STEP header and terminator markers, or checks ZIP member integrity. A renamed text file, Markdown plan, YAML status, or JSON summary cannot stand in for supplier documentation. These format checks cannot authenticate the issuer or validate the claims inside a document.

The capability fields checked by code are:

| Role | Required fields | Cross-check |
| --- | --- | --- |
| `compute_platform` | `memory_interface`, `max_memory_bytes`, `supported_memory_placements`, `storage_interfaces`, `display_interfaces`; `configured_memory_bytes` for on-package DRAM; `cellular_interfaces` if cellular is selected | Host-side limits, actual package capacity, and interfaces |
| `memory` | `interface`, `capacity_bytes_per_package`, `placement`, `qualified_topology`; `included_in_compute_sku: true` for on-package DRAM | Exact controller and memory MPNs, package count, placement, capacity, and hashes of supplier controller-support and reference-design files must agree with the selected parts; total capacity is at least 128 GB and within the controller limit |
| `storage` | `interface`, `capacity_bytes` | At least 1 TB and interface listed by compute |
| `display_module` | `interface`, `diagonal_in` | Compute interface matches; diagonal is within the 7–8.4 inch fallback |
| `battery_pack` | `energy_wh`, `maximum_validated_charge_w` | Both are positive; the charge test separately enforces the 30 W EVT cap |
| `cellular` | `interface` | Compute platform lists the modem interface |

For example, a memory part entry has this shape; replace every illustrative value with an actual reviewed supplier revision and provide every required evidence type:

```json
{
  "manufacturer": "Supplier name",
  "mpn": "Exact manufacturer part number",
  "revision": "Supplier revision",
  "availability": "purchasable",
  "lifecycle": "active",
  "quantity": 4,
  "capabilities": {
    "interface": "LPDDR5X",
    "placement": "board",
    "capacity_bytes_per_package": 32000000000,
    "qualified_topology": {
      "id": "Supplier topology identifier",
      "controller_mpn": "Exact selected compute MPN",
      "memory_mpn": "Exact selected memory MPN",
      "package_count": 4,
      "capacity_bytes_per_package": 32000000000,
      "total_capacity_bytes": 128000000000,
      "placement": "board",
      "controller_support_sha256": "Hash of memory controller_support evidence",
      "reference_design_sha256": "Hash of compute reference_design evidence"
    }
  },
  "evidence": {
    "package_drawings": {
      "path": "engineering/hardware/released/parts/memory/package-drawing.pdf",
      "sha256": "SHA-256 of the actual supplier file"
    }
  }
}
```

For memory on package, use `placement: on_package` in both the memory capabilities and qualified topology, set `availability: included_in_compute_sku`, and set `included_in_compute_sku: true`. The selected compute part must name that placement in `supported_memory_placements` and declare `configured_memory_bytes` equal to the complete memory topology. The `memory` role still identifies the actual supplier DRAM and its internal package count. A 48 GB orderable compute SKU cannot pass a 128 GB memory claim by adding separate planning boxes. Mixed on-package and board memory is not covered by either current release mode and needs a supplier-supported architecture and an explicit contract change.

The code verifies identity, file integrity, role coverage, selected capacity, declared interface agreement, and whether the topology record is bound to the exact selected parts and supplier source bytes. A published controller maximum or four-package arithmetic cannot pass without that record. The code cannot independently read a supplier PDF to establish that its topology is actually qualified, whether timing and routing close, whether the battery is safe, or whether the parts fit the enclosure. Those questions remain behind engineering review, electrical, mechanical, thermal, and physical EVT0 gates. Keep restricted supplier files in an authorized controlled system; do not publish material without distribution rights. A public release gate remains blocked if it cannot verify the exact source bytes.

Design release also requires the battery, compute/memory, and display/storage supplier evidence packages in the [evidence registry](../../engineering/evidence/evidence_registry.yaml) to be marked verified after engineering review. A passing machine check of the part set alone cannot promote those packages.
