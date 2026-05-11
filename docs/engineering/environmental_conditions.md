# Environmental Operating Conditions

BuildSlate environmental models make external operating conditions visible before device profiles or optimization are introduced. They are screening tools that show how ambient temperature, hand contact, enclosure state, sunlight, and charging overlap can collapse thermal and runtime margin.

These models are not compliance tests, safety certifications, product firmware, or validated thermal simulations. They exist to prevent ideal-lab assumptions from being mistaken for real operating feasibility.

## Why environment matters

Thermal feasibility depends on ambient condition. A sustained AI workload that appears plausible at room temperature in open air can become infeasible in a hot room, pocket, bag, car console, or direct sunlight. Runtime estimates also shift because extra display power, charging losses, and forced throttling consume battery energy or reduce useful performance.

## Ambient temperature

Skin temperature margin shrinks quickly in hot environments because exterior skin temperature is modeled as ambient temperature plus workload-driven skin rise. At a fixed 18 C skin rise and 43 C maximum skin target, moving from 25 C ambient to 35 C ambient changes the estimate from exactly at the target to 10 C over the target.

Use:

```bash
python engineering/environment_models/ambient_temperature.py
python engineering/environment_models/ambient_temperature.py --ambient-c 35
```

## Hand contact

Hand contact reduces useful heat-spreading area. The first-pass model removes the contacted percentage of exterior area from effective dissipation area, then applies an insulation factor to reflect reduced convection and increased perceived warmth. This is intentionally conservative for handheld use, but still optimistic for local hotspots because it assumes the remaining area spreads heat uniformly.

Use:

```bash
python engineering/environment_models/hand_contact.py
```

## Pocket, bag, and car-console conditions

Pocket and bag operation should not allow sustained AI workloads. Enclosed conditions reduce heat escape, block airflow, add insulation, and can trap heat against skin, fabric, or other objects. Car-console sunlight is even higher risk because solar heating can combine with poor airflow and high ambient temperature.

Use:

```bash
python engineering/environment_models/enclosure_condition.py
python engineering/environment_models/enclosure_condition.py --condition pocket
```

The enclosure model clearly flags pocket and bag sustained AI as a condition that should be disallowed or aggressively throttled. Charging under enclosed conditions is treated as unsafe without throttling.

## Sunlight display load

Sunlight increases display load because higher brightness is required for readability. That display power becomes additional thermal load and competes with sustained AI power and battery runtime. High brightness combined with charging and AI workload is a high-risk overlap case.

Use:

```bash
python engineering/environment_models/sunlight_display_load.py
python engineering/environment_models/sunlight_display_load.py --brightness-mode sunlight
```

## Charging overlap

Charging plus AI workload can exceed safe thermal limits because charger conversion losses and battery charge heat stack on top of the AI workload. Wireless charging is especially risky because coil alignment, lower efficiency, and rear-surface heating can worsen thermal concentration.

Use:

```bash
python engineering/environment_models/charging_overlap.py
python engineering/environment_models/charging_overlap.py --wireless true
```

The charging model flags sustained AI plus charging as a condition that should throttle, and it flags wireless charging plus sustained AI as high risk.

## Throttle policy screening

The throttle policy model converts skin, battery, and SoC temperature thresholds into an initial recommended mode: unrestricted, reduce AI power, burst only, stop charging, or emergency cooldown. These thresholds are engineering placeholders, not product firmware or certified limits.

Use:

```bash
python engineering/environment_models/thermal_throttle_policy.py
```

## Run all models

Run the default models plus hot ambient, pocket, sunlight, and wireless-charging stress cases with:

```bash
python engineering/environment_models/run_all_environment_models.py
```

## Interpretation rules

- Treat environmental conditions as constraints, not afterthoughts.
- Treat hot ambient, hand contact, pocket/bag enclosure, sunlight, and charging overlap as compounding risks.
- Do not claim sustained AI feasibility without stating the environmental condition.
- Do not allow pocket or bag sustained AI operation without an explicit throttle or disallow policy.
- Do not treat these screening outputs as compliance results; replace assumptions with measured thermal chamber, sunlight, grip, charging, and enclosure tests.
