# mac-charging-watts

A Codex skill for measuring a Mac laptop's live charging power without
confusing charger branding, adapter-reported capacity, system input and power
flowing into the battery.

The included helper takes repeated, read-only samples from macOS I/O Registry
telemetry. It reports only selected power fields and never emits the complete
registry record, which may contain device identifiers.

## Install

Copy this directory to `~/.codex/skills/mac-charging-watts`, then restart Codex.

## Use with Codex

```text
Use $mac-charging-watts to tell me how many watts this Mac is charging at.
```

## Use the helper directly

```bash
python3 scripts/measure_charging.py
python3 scripts/measure_charging.py --samples 8 --interval 0.5 --json
```

Requirements: a Mac laptop, macOS, and Python 3. The script does not require
administrator access and does not change power settings.

## What the figures mean

- **Adapter model** is a label and may contain a marketed wattage.
- **Adapter-reported capacity** is the power macOS says the connected adapter
  can make available.
- **System input** is live power entering the computer according to battery
  telemetry.
- **Battery power** is derived from battery voltage multiplied by signed
  current. The rest of the input is being used by the computer or lost in
  conversion.

These are internal telemetry estimates, not wall-socket measurements. Use a
hardware power meter when billing-grade or electrical-safety accuracy matters.

## Verify

```bash
python3 -m unittest discover -s tests -v
python3 /path/to/skill-creator/scripts/quick_validate.py .
```

## Licence

MIT
