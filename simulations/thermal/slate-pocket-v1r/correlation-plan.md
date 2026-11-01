# Slate Pocket v1R Thermal Correlation Plan

Status: planned; no solver model or instrumented Slate hardware exists.

## Purpose

Correlate a geometry-specific thermal model to instrumented EVT hardware before using predictions for power, skin-temperature, charge-rate, or mechanical decisions. The current model definition locates heat sources and sensors, but intentionally leaves material properties, interface resistance, contact pressure, convection, radiation, and enclosure-contact inputs unset.

## Build and data control

Every correlation run records unit serial, enclosure revision, board revision, thermal-module lot, TIM lot and application, fastener/contact condition, battery lot, firmware, workload build, ambient, orientation, fixture, sensor calibration, and raw power/temperature logs. Changes to those inputs create a new correlation configuration rather than silently updating the baseline.

## Model workflow

1. Import released enclosure, board, thermal-module, battery, display, and major-component geometry.
2. Assign traceable material properties with temperature dependence and anisotropy where applicable.
3. Map measured component and rail losses to their physical locations; do not use headline input power as heat without an energy balance.
4. Define interface resistance from supplier data or coupon measurement and record assembly pressure/bondline assumptions.
5. Apply chamber, radiation, grip, pocket, bag, and solar boundaries from characterized fixtures.
6. Demonstrate mesh independence, solver convergence, and energy balance before tuning uncertain inputs.

## Correlation gates

The initial engineering targets below are model-quality gates, not product safety limits:

- steady-state exterior sensor error: within ±2 °C for every mapped skin location;
- steady-state internal sensor error: within ±3 °C where sensor placement uncertainty is controlled;
- time to cross the 40 °C skin caution level: within ±15%;
- peak-temperature location: same modeled region as the measured hotspot;
- steady-state model energy imbalance: below 3%;
- no single tuned property outside its traceable range;
- validation cases remain separate from calibration cases.

Failure at one location cannot be hidden by average error. The team records residuals by sensor and case, investigates systematic bias, and reruns sensitivity analysis after each material, interface, or boundary update.

## Calibration and validation sequence

- Calibrate with idle, controlled heater/coupon, and one open-air sustained workload at 25 °C.
- Validate without retuning against peak burst, hot ambient, alternate orientation, and grip-fixture cases.
- Add charging only after battery/charger selection and standalone electrical/thermal characterization.
- Add pocket, bag, human-contact, and solar cases only under approved fixtures and fault-containment procedures.

## Control and pass/fail posture

The 43 °C skin target remains a locked screen. Firmware must reduce AI power before that target is exceeded. The current 40 °C battery test-abort value is a conservative pre-supplier lab gate, not a product limit; the selected cell and pack supplier's lower limit controls. Pocket and bag operation must inhibit sustained high power, and full-power charging may not overlap sustained AI until validated.

## Exit evidence

- Released geometry and traceable material/interface inputs.
- Reviewed mesh/convergence/energy-balance package.
- Raw calibrated sensor and electrical logs for every case.
- Sensor-by-sensor residual report and sensitivity analysis.
- Independent validation cases meeting the correlation gates.
- Approved firmware throttle table and fault-response evidence.
- Thermal, electrical, battery-safety, mechanical, human-factors, and test signoff.

This plan does not claim CFD/FEA completion, model correlation, skin-temperature compliance, charging safety, sustained-performance capability, or prototype readiness.
