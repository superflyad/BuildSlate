# Slate Pocket Supplier RFQ/RFI Packets

These packets convert BuildSlate's public-source Phase 1 screening into structured supplier requests. They are prepared engineering artifacts, not evidence that any supplier has been contacted, approved the design, quoted a part, or committed supply.

## Status

- Request status: `prepared_not_sent`
- Product baseline: `slate-pocket-v1r`
- Decision source: `docs/engineering/slate-pocket-v1r-decision-baseline.md`
- Candidate screen: `reports/slate-pocket-phase1-candidate-screen.txt`

Sending a packet, accepting an NDA, disclosing confidential information, requesting paid samples, or making a purchase requires explicit user authorization.

## Packet set

- `battery/` — custom cell and complete-pack request, initially aimed at Enovix.
- `compute-memory/` — platform, memory topology, power, software, and supply request, initially aimed at Qualcomm.
- `display/` — module RFI for BOE, Tianma, and Samsung Display.
- `storage/` — embedded UFS and compact NVMe request for Samsung Semiconductor, KIOXIA, and Micron.

Each packet includes a human-readable request and a YAML response template. Suppliers may answer under NDA, but BuildSlate must keep public, NDA-restricted, measured, and inferred claims visibly separate.

## Response handling

1. Save the supplier response without rewriting supplier claims.
2. Record the document identifier, revision, date, confidentiality, and source contact.
3. Mark every unanswered field explicitly; do not infer a favorable value.
4. Compare responses against the acceptance criteria in `engineering/evidence/evidence_registry.yaml`.
5. Update candidate status only after mechanical, electrical, thermal, software, commercial, and lifecycle review.
6. Do not mark an evidence package `verified` until every acceptance criterion is supported.

## Claim classes

- `public_supplier`: published manufacturer material.
- `nda_supplier`: supplier-controlled documentation received under agreement.
- `measured`: data produced by a documented test.
- `modeled`: calculation based on declared inputs.
- `inferred`: engineering interpretation that must not be presented as supplier fact.
- `unknown`: missing evidence.
