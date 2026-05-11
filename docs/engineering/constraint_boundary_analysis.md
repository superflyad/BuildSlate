# Constraint Boundary Analysis

Constraint boundary analysis identifies transition points where a single mutated profile parameter changes an explicit engineering constraint from failing to passing, or from passing to failing. It is a structured screening workflow that sits after configurable device profiles, profile comparison, and one-parameter scenario sweeps.

## What Boundary Analysis Does

A boundary scan:

1. Loads a source device profile.
2. Mutates one dot-path parameter in memory over a numeric range.
3. Evaluates one named pass/fail constraint at every scan point.
4. Records warnings and model outputs for each evaluated row.
5. Reports the first passing value, the last failing value before that pass, and the fail/pass sequence.

This makes transition points visible. For example, a scan can show the first thickness where the current zone stackup stops failing, the first battery capacity that reaches a one-hour runtime target, or the first ambient temperature where skin-temperature margin fails.

## What Boundary Analysis Does Not Do

Boundary analysis does **not** optimize device architecture. It does not automatically redesign Slate, change source profiles, choose components, resize boards, reroute thermal paths, or declare a globally best configuration.

A passing boundary only means that one explicit constraint passed under the current simplified model assumptions at that scan point. It should not be treated as a production-ready device target.

## Explicit, Model-Dependent Constraints

Every constraint is named and intentionally narrow:

- `zone_stackup_pass` checks whether worst zone stackup margin is non-negative.
- `thermal_risk_not_extreme` checks whether the simplified thermal-risk classifier is below `EXTREME`.
- `skin_temp_pass` checks estimated skin temperature against the profile's max skin temperature.
- `runtime_minimum` checks battery runtime against an explicit target.
- `mass_within_engineering_range` checks estimated mass against the profile's acceptable maximum when available.
- `memory_runtime_pass` checks runtime memory demand against available memory.

Because these constraints depend on first-pass equations and profile assumptions, boundaries will move as CAD volume studies, vendor package data, prototype thermal measurements, battery characterization, and runtime implementation data improve.

## Direction and Non-Monotonic Behavior

Some scans tend to pass as values increase, such as thickness improving stackup margin or capacity improving runtime. Other scans tend to fail as values increase, such as sustained power increasing thermal risk or ambient temperature reducing skin-temperature margin.

The boundary system does not assume perfect monotonic behavior. It evaluates every row and reports the sequence of failures and passes in scan order so reviewers can spot irregular transitions or model artifacts.

## Screening Classification Only

Pass/fail output is a screening classification, not certification. Boundary reports must be read as **screening result, not production validation**. A real device decision still requires detailed mechanical CAD, tolerance stackups, thermal simulation and measurements, battery safety review, supplier-backed packages, manufacturing studies, and regulatory validation.
