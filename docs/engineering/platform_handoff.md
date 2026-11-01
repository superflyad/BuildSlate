# BuildSlate platform handoff

## Canonical commands

- Full CI-equivalent gate: `python scripts/ci_validate.py`
- Program state: `python -m buildslate dashboard`
- External blockers: `python -m buildslate blockers`
- Configuration authority: `python -m buildslate configuration validate`
- Phase 2 interfaces: `python -m buildslate contracts validate`
- Generated currency: `python -m buildslate stale`
- Migration map: `python -m buildslate migrations audit`

## Protected baseline

The baseline remains Slate Pocket v1R with 128 GB operational memory, 1 TB internal storage reference, 2 TB modular/external product fallback, 80 TOPS INT8 public reference, 30 W EVT0 wired-input cap, wireless charging removed from EVT0, and cellular deferred. These are classified planning inputs, not selected or qualified parts.

## Empty evidence stores

Supplier response receipts, EVT0 campaigns, calibration evidence, and pilot campaigns are intentionally empty. README files are not evidence. Do not add sample measurements to these stores.

## External boundary

The exact missing evidence, requested action, authorization, and active fallback for every remaining blocker are generated in `reports/program/dashboard.md`. No operator is authorized by this repository to contact suppliers, accept an NDA, purchase material, build or energize hardware, engage a lab, claim certification, or release production.

## Change handoff checklist

1. Inspect the dashboard and relevant review queue.
2. Validate staged evidence without ingesting it.
3. Preserve authorization metadata and source bytes during ingestion.
4. Resolve configuration/contract violations through their authoritative inputs.
5. Regenerate affected nodes.
6. Run `python scripts/ci_validate.py`.
7. Commit generated outputs and their regeneration state together.

