# 03 – Modes

A mode is a **profile**: limits, fan behaviour, end condition. All modes share
the same state machine and safety layer.

## Profile summary

| Field | `heater` (chamber) | `dry` (filament) | `vent` |
|---|---|---|---|
| Purpose | Warm the enclosure for ABS/ASA | Dry filament in the shelter or a dryer box | Fans only: cool or air out |
| `target` range | 35–55 °C | 40–65 °C | n/a |
| `max_target` (hard) | 55 °C* | 65 °C (fan limit 70 °C) | n/a |
| Timer | optional | **required** | required (default 10 min) |
| Heaters | 1 or 2 | 1 or 2 (usually 1) | 0 |
| Fan duty | 80–100 % | 50–70 % (≥ interlock minimum) | 100 % |
| Humidity | reported | **actively used** (purge, end condition) | reported |
| End | `STOP` / timer → `COOLDOWN` | timer **or** RH-dry condition → `COOLDOWN` → optional `KEEP_WARM` | timer → `IDLE` |
| Typical source | Klipper macro | Web UI / encoder | Klipper end-of-print / web UI |

\* Limited further by the printer inside. A Bambu A1 / A1 mini is an open printer with plastic toolhead parts. Keep it at ≤ 45 °C, and keep PLA spools out.

## Heater mode

- Fans high for good mixing, so the chamber sensor reads the real average.
- Runs until `STOP` (e.g. sent from Klipper's end-of-print macro) or a timer.
- An exhaust/ventilation fan, if one is fitted, must be **off** while heating.

## Dry mode

- **Moisture purge:** warm air holds the moisture, but it has to leave the box.
  - Option A: a passive small vent hole.
  - Option B: an active exhaust fan or servo flap, opened for `purge_s` every `purge_interval_s`, or whenever RH > `purge_rh`.
- **End conditions:** `duration` elapsed, **or** (optional) RH < `dry_rh` sustained for `dry_rh_hold_s`.
- **KEEP_WARM (optional):** after drying, hold 35–40 °C at low power until stopped.
- Small insulated dryer boxes are much more efficient than the 0.28 m³ shelter.

### Material presets (starting points; check the filament maker's data)

| Preset | Target | Duration | Notes |
|---|---|---|---|
| `PLA` | 45 °C | 5 h | |
| `TPU` | 50 °C | 5 h | |
| `PETG` | 62 °C | 5 h | |
| `ABS` / `ASA` | 65 °C | 4 h | Hardware cap; ideally hotter |
| `PA` / Nylon | n/a | n/a | **Not supported**: needs 70–80 °C, beyond the fan limit |

## Vent mode

- Heaters locked off. Fans at 100 % for `duration`.
- Use after ABS/ASA prints, or to cool the enclosure before opening it.

## Example profile (config)

```c
static const ModeProfile MODE_DRY = {
  .name              = "dry",
  .min_target_c      = 40.0f,
  .max_target_c      = 65.0f,
  .timer_required    = true,
  .max_duration_s    = 12 * 3600,
  .fan_duty_pct      = 60,
  .min_fan_pwm_1h    = 50,
  .min_fan_pwm_2h    = 70,
  .outlet_max_c      = 95.0f,   // tune in commissioning
  .humidity_active   = true,
};
```
