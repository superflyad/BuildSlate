# Device Profiles

Device profiles are YAML inputs for repeatable BuildSlate engineering screening runs. Each profile captures a specific set of Slate hardware assumptions and feeds those values into existing math-backed validation and model scripts.

Profiles are not optimized answers and do not claim manufacturability. Aggressive profiles are allowed when clearly labeled, and conservative profiles are useful for grounded comparisons.

Run validation with:

```bash
python validation/validate_device_profiles.py
```

Generate a profile report with:

```bash
python engineering/run_device_profile.py --profile configs/devices/slate-pocket-v1.yaml
```
