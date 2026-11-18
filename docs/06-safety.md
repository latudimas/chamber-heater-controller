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

Layers 5 and 6 are **not optional**. A MOSFET usually fails shorted, and no
software can switch off a shorted MOSFET.

## Invariants (must always hold)

1. Every heater output is **off** at boot, until the state machine explicitly enables it.
2. No heater is on unless every fan required by the interlock is powered **and** its tach shows RPM ≥ `min_rpm`.
3. No heater is on if any required sensor reading is missing, stale (> 3 s), or out of plausible range.
4. No heater is on while the outlet temperature is ≥ `outlet_max`.
5. Fans keep running after the heaters stop until the outlet temperature is below `cooldown_temp` (and at least `cooldown_min_s`), including in `FAULT`.
6. A fault is **latched**. It needs `CLEAR`, and `CLEAR` is refused while the cause is still present.
7. No auto-resume after a reboot or power loss.
8. Mode limits (`max_target`, `max_duration`) cannot be exceeded by any command.

## Fault codes

| Code | Trigger |
|---|---|
| `F_FAN_STALL` | required fan RPM < `min_rpm` for > 2 s while heating |
| `F_OUTLET_OVERTEMP` | outlet ≥ `outlet_max` |
| `F_CHAMBER_OVERTEMP` | chamber ≥ `max_target + 5 °C` |
| `F_SENSOR` | SHT40 or DS18B20 missing, stale, CRC error, or implausible |
| `F_NO_HEAT` | chamber rises < `min_gain` °C within `heat_check_s` while demand is high (dead heater, open enclosure, wrong sensor placement) |
| `F_RUNTIME` | absolute max runtime exceeded (independent of the user timer) |
| `F_BROWNOUT` | supply voltage dropped (if monitored) |

## Fault behaviour

```
fault detected
  → heaters OFF immediately (gates low)
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

- Measure fin and outlet temperatures with 1 fan, 2 fans, and reduced PWM. This sets `outlet_max`, `min_fan_pwm_*`, and whether 1-fan + 2-heater is allowed.
- Pull a fan connector while heating → expect `F_FAN_STALL` within 2 s.
- Unplug each sensor → expect `F_SENSOR`.
- Hold the firmware in a loop (test build) → expect a watchdog reset with outputs off.
