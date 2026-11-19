# 06 – Safety

This device runs ~200 W of heat unattended, next to a fabric enclosure and
plastic filament. Safety is layered so that no single failure (firmware, sensor,
MOSFET, fan) can cause uncontrolled heating.

## Layers

| Layer | Protects against | Mechanism |
|---|---|---|
| 1. PTC physics | runaway element temperature | PTC self-limits as it heats |
| 2. Firmware safety layer | bad commands, fan failure, sensor failure, overheating | interlocks + latched faults |
| 3. Watchdog | firmware hang | hardware WDT → reset → outputs default off |
| 4. Gate pull-downs | boot, reset, floating pins | 10 kΩ gate-to-source |
| 5. Thermal cutoff (TCO) | MOSFET shorted on, firmware fully wrong | one-shot fuse in series with each heater |
| 6. Electrical fuses | short circuit, wiring overload | per-channel and main fuses |
| 7. Master heater relay | heater MOSFET shorted, GPIO stuck high | relay K1 feeds the heaters only; firmware opens it on any fault (ADR-013) |

Layers 5 and 6 are **not optional**. A MOSFET usually fails shorted, and no
software can switch off a shorted MOSFET. Layer 7 lets firmware cut a shorted
MOSFET's supply; it does not replace the TCO, because the relay and its driver
can fail too.

Per-component failure modes, how each is detected, and the open gaps are in
[09-fmea.md](09-fmea.md).

## Invariants (must always hold)

1. Every heater output is **off** at boot, until the state machine explicitly enables it.
2. No heater is on unless every fan required by the interlock is powered **and** its tach shows RPM ≥ `min_rpm`.
3. No heater is on if any required sensor reading is missing, stale (> 3 s), or out of plausible range.
4. No heater is on while the outlet temperature is ≥ `outlet_max`.
5. Fans keep running after the heaters stop until the outlet temperature is below `cooldown_temp` (and at least `cooldown_min_s`), including in `FAULT`.
6. A fault is **latched**. It needs `CLEAR`, and `CLEAR` is refused while the cause is still present or the outlet is still above `cooldown_temp`.
7. No auto-resume after a reboot or power loss.
8. Mode limits (`max_target`, `max_duration`) cannot be exceeded by any command.
9. The master relay K1 is closed only in the check phase of `PREHEAT` and in `RUN`, and only after both fans are confirmed by tach. It closes with every heater gate low, at least one control tick before any gate may turn on (the stuck-heater check window). When it opens, the gates are written low first, in the same control tick. Fans and logic are never powered through K1.

## Formal model

The state machine and invariants 2–9 are model-checked with TLA+ in
[`spec/`](../spec/README.md) (`make -C spec check`). The model also shows
that, with K1, a heater MOSFET that fails shorted can only produce heat while
heating with airflow, and is cut within one tick of being commanded off.
Hardware layers 1, 3–6 are outside the model.

## Fault codes

| Code | Trigger |
|---|---|
| `F_FAN_STALL` | required fan RPM < `min_rpm` for > 2 s while heating |
| `F_OUTLET_OVERTEMP` | outlet ≥ `outlet_max` |
| `F_CHAMBER_OVERTEMP` | chamber ≥ `max_target + 5 °C` |
| `F_SENSOR` | SHT40 or DS18B20 missing, stale, CRC error, or implausible |
| `F_NO_HEAT` | chamber rises < `min_gain` °C within `heat_check_s` while demand is high (dead heater, open enclosure, wrong sensor placement) |
| `F_RUNTIME` | absolute max runtime exceeded (independent of the user timer) |
| `F_HEATER_STUCK` | outlet temperature rises by > `stuck_rise_c` within `stuck_check_s` while K1 is closed and every heater gate is low (shorted MOSFET or GPIO stuck high) |
| `F_BROWNOUT` | supply voltage dropped (if monitored) |

## Fault behaviour

```
fault detected
  → heaters OFF immediately (gates low)
  → master relay K1 opens (after the gates are low)
  → fans 100 % (if powered and not themselves the fault cause) until outlet cool
  → state = FAULT, code recorded, published on all transports
  → OLED shows the fault; status LED blinks
```

## Physical rules

- The PTC never touches the enclosure fabric or printed plastic. Mount it on a metal or ceramic frame with standoffs.
- Aim the outlet low and toward the centre, not at the fabric walls.
- PSU outside the enclosure, earthed.
- The duct sections near the PTC are made of a material rated well above the expected fin temperature.

## Things to verify in commissioning

- Measure fin and outlet temperatures with both fans at full and reduced PWM. This sets `outlet_max` and `min_fan_pwm`. (1-fan heating is not allowed: ADR-019.)
- Pull a fan connector while heating → expect `F_FAN_STALL` within 2 s.
- Unplug each sensor → expect `F_SENSOR`.
- Hold the firmware in a loop (test build) → expect a watchdog reset with outputs off.
- Bridge a heater MOSFET drain to source while K1 is closed and the gates are low → expect `F_HEATER_STUCK` and K1 opening.
