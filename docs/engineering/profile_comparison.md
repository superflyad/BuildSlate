# Profile Comparison and Engineering Tradeoff Analysis

BuildSlate device profiles can be compared with the same first-pass engineering model framework used for single-profile feasibility screening. The comparison tools read profile YAML files from `configs/devices/`, normalize key assumptions, and present engineering pressure points side by side.

## Purpose

Profile comparison is exploratory engineering analysis. It highlights tradeoffs, warnings, and blockers; it does **not** optimize a design, auto-solve constraints, or declare a winning profile.

The comparison workflow is useful when reviewing profiles with different intent:

- **Canonical profiles** provide a repeatable baseline for discussion.
- **Aggressive profiles** are allowed and useful because they preserve ambitious targets and make blockers visible.
- **Conservative profiles** are useful grounding references because they show how relaxed targets, thicker envelopes, lower power, or lower capacity affect pressure categories.
- **Experimental profiles** can test specific assumptions without implying product readiness.

## Tools

Run a side-by-side profile report with:

```bash
python engineering/comparison/compare_profiles.py \
  --profiles \
  configs/devices/slate-pocket-v1.yaml \
  configs/devices/slate-pocket-aggressive.yaml \
  configs/devices/slate-pocket-conservative.yaml
```

By default, the command prints readable tables and saves `reports/profile-comparisons/comparison-report.txt`. Use `--no-save` to print without writing a report.

Generate a compact matrix with:

```bash
python engineering/comparison/profile_matrix.py
```

The matrix uses qualitative categories of `LOW`, `MODERATE`, `HIGH`, and `EXTREME` for thermal risk, mass pressure, stackup pressure, runtime memory pressure, manufacturing pressure, and environmental sensitivity.

Generate qualitative summaries with:

```bash
python engineering/comparison/tradeoff_summary.py
```

The summary describes tradeoffs such as compute ambition versus thermal risk, thinner chassis pressure, memory-package complexity, and the grounding value of conservative assumptions.

## Compared categories

The comparison report covers:

- Geometry: thickness and display size.
- Mass: aspirational target, engineering estimate, and acceptable range.
- Battery: capacity, charging power, and estimated runtime.
- Compute: sustained power, peak power, and NPU TOPS.
- Memory: capacity, bandwidth, and package/interconnect assumptions.
- Storage: capacity and active power.
- Thermal: sustained watts and qualitative thermal risk.
- Runtime: model size, context length, and memory reserve pressure.
- Environment: ambient assumptions and operating condition.

## Profile metadata

Profiles may include optional top-level metadata:

```yaml
profile_class: aggressive # aggressive, canonical, conservative, or experimental
feasibility_status: research_required # conceptual, research_required, or screening_candidate
review_notes:
  - Engineering review note shown in comparison reports.
```

`validation/validate_device_profiles.py` validates this metadata when present.

## Interpretation rules

Comparison output should be read conservatively:

- A lower pressure category is not a proof of feasibility.
- A higher pressure category is not an automatic rejection; it identifies where engineering evidence is needed.
- Aggressive profiles should remain visible so their blockers can be reviewed explicitly.
- Conservative profiles should not be treated as final recommendations; they are grounding references.
- The comparison workflow is not optimization and does not choose the best profile.
