# 08 – Commissioning & Test Plan

Do these in order. Don't skip ahead to full power.

## 1. Power & wiring (no MCU)

- [ ] Check continuity and polarity on every 12 V branch.
- [ ] Fuses fitted; TCOs in series with each heater.
- [ ] PSU no-load voltage 12.0–12.3 V.
- [ ] Each heater on directly (no MOSFET), one at a time, fan running: measure current (cold surge + steady state) and the voltage at the PSU.
- [ ] Both heaters, **staggered by hand**: steady-state voltage ≥ 11.4 V.

## 2. Fan bring-up

- [ ] Identify the wire colours with a multimeter; record them in `docs/01-components.md`.
- [ ] PWM sweep 0–100 %: record RPM at each step, and the minimum speed at 0 % PWM.
- [ ] Power cut: the fan really stops.
- [ ] Tach: counts match a phone stroboscope/tachometer app within ~5 %.

## 3. Switching stage

- [ ] Heater MOSFET temperature at full current after 10 min (should stay warm, not hot).
- [ ] MCU unpowered / in reset → heaters stay off (pull-downs working).
- [ ] MCU unpowered / in reset → K1 open (no 12 V on `HEAT_12V`).
- [ ] K1 closed, gates low, fans on → heaters stay cold (no MOSFET leakage).
- [ ] Boot sequence watched on a scope or LED → no glitch on the heater gates.

## 4. Airflow & temperature limits (this sets the config)

For each combination, run 10 min at 100 % heater duty and record the outlet and fin temperatures:

| Heaters | Fans | Fan PWM | Outlet °C | Fin °C | OK? |
|---|---|---|---|---|---|
| 1 | 1 | 100 | | | |
| 1 | 1 | 50 | | | |
| 1 | 2 | 100 | | | |
| 2 | 2 | 100 | | | |
| 2 | 2 | 70 | | | |
| 2 | 1 | 100 | | | (only if safe) |

→ Set `outlet_max`, `min_fan_pwm_1h`, `min_fan_pwm_2h`, and whether `2 heaters + 1 fan` is allowed.

## 5. Safety tests (firmware)

- [ ] Pull a fan connector while heating → `F_FAN_STALL` within 2 s; heaters off.
- [ ] Unplug the SHT40 → `F_SENSOR`.
- [ ] Unplug the DS18B20 → `F_SENSOR`.
- [ ] Heat the outlet probe with a heat gun → `F_OUTLET_OVERTEMP`.
- [ ] Open the enclosure fully at high demand → `F_NO_HEAT` after `heat_check_s`.
- [ ] Test build with an infinite loop → watchdog reset, outputs off, boots to `IDLE`.
- [ ] Power-cycle mid-run → boots to `IDLE`, no auto-resume.
- [ ] `CLEAR` refused while the cause is still present.
- [ ] `CLEAR` refused while the outlet is still above `cooldown_temp`.
- [ ] `START` with a fan unplugged → stays in `PREHEAT` spin-up with K1 open, then faults; heaters never energised.
- [ ] Bridge a heater MOSFET drain to source (fans on) → `F_HEATER_STUCK`, K1 opens, heater goes cold.

## 6. Enclosure characterisation

- [ ] Bed only at 100 °C, enclosure closed: where does the chamber settle after 45 min?
- [ ] 1 heater: steady-state chamber temperature and time to reach it.
- [ ] 2 heaters: same.
- [ ] Record these, then tune PID (start with P only, add I slowly; D is probably unnecessary).

## 7. Dry mode

- [ ] Dryer box: time to reach 50 / 60 °C; how RH falls over time.
- [ ] Purge behaviour: RH drop after each purge.
- [ ] Fan inlet temperature stays ≤ 65 °C.
