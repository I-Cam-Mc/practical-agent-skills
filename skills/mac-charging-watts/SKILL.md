---
name: mac-charging-watts
description: Measure and explain a Mac laptop's live charging power, separating adapter capacity, system input and battery power. Use for current charging-watt questions, not electrical certification or charger buying advice.
---

# Mac Charging Watts

Measure charging power with repeated, read-only samples. Do not infer live
charging watts from the adapter's name or advertised rating.

## Measure

Run the bundled helper from this skill directory:

```bash
python3 scripts/measure_charging.py
```

Use `--json` when structured output will help. The default five samples are a
good baseline. Increase the count only when readings vary, and keep collection
bounded.

If the helper is unavailable, inspect `AppleSmartBattery` with `ioreg` and
extract only the necessary power fields. Do not print or retain the full I/O
Registry record because it can contain identifiers.

## Interpret

Keep these values distinct:

- The adapter model is a product label, not a live measurement.
- Adapter-reported capacity is what macOS says the source can make available.
- `SystemPowerIn` is live power entering the Mac, in milliwatts.
- Battery power is battery voltage in millivolts multiplied by signed battery
  current in milliamps, divided by one million.
- While charging, system input minus battery power is approximately the Mac's
  own consumption plus conversion loss. Telemetry timing can make this derived
  remainder noisy.

Report the median and range, the charging state, and the sampling count. Say
when a field is unavailable instead of substituting a different quantity.

## Boundaries

- Treat the result as internal telemetry, not a wall-socket measurement.
- Never claim a charger's maximum USB-C Power Delivery capability from one
  battery snapshot.
- Do not change power settings, disconnect hardware or stress the computer.
- Stop cleanly on non-macOS systems, desktops without a battery, disconnected
  chargers or missing telemetry.
- For electrical safety, certification or billing-grade measurements,
  recommend suitable test hardware or a qualified professional.
