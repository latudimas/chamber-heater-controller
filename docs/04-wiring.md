# 04 – Wiring

## Power budget (12 V 24 A PSU)

| Load | Running | Notes |
|---|---|---|
| H1 PTC 100 W | 8.3 A | ~1.5× for a few seconds when cold |
| H2 PTC 100 W | 8.3 A | same |
| F1 + F2 | 1.5 A | 0.73 A each |
| ESP32, sensors, OLED | < 0.3 A | via a 12 V → 5 V buck |
| **Total** | **~18.2 A (~76 %)** | |

- **Both heaters starting cold together (~25–30 A) exceeds the PSU.** The firmware staggers the start (see [02-system-design.md](02-system-design.md)).
- `max_power` per channel (e.g. 0.85) adds headroom if the PSU sags.

## Schematic

The full schematic is a KiCad project in [`hardware/kicad/`](../hardware/kicad/)
([PDF](../hardware/kicad/chamber-heater.pdf)). The sections below summarise it.
If they disagree, fix both in the same change.

The diagrams in `docs/diagrams/` are simplified explanations, not the design
source. Regenerate them with `python docs/diagrams/gen_diagrams.py` (needs
`schemdraw`) when the circuit they show changes.

## Power distribution

```
 PSU +12V ──[F_main 20–25 A]──┬──[K1 relay]── HEAT_12V ──┬──[F_h1 10–12 A]──[TCO_1]── H1 (+)   H1 (−) ── Q_H1 drain
                              │                          └──[F_h2 10–12 A]──[TCO_2]── H2 (+)   H2 (−) ── Q_H2 drain
                              └──[F_aux 3 A]── 12V_AUX ──┬── Q_F1 (P-MOSFET) ── F1 red    F1 black ── GND
                                                         ├── Q_F2 (P-MOSFET) ── F2 red    F2 black ── GND
                                                         └── buck 12→5 V ── ESP32 5V/VIN
 PSU GND  ──────── star ground: heater MOSFET sources, fans, buck, ESP32 GND
```

- **K1 feeds the heaters only.** Fans and logic come from `12V_AUX` so they keep running in `COOLDOWN` and `FAULT`.

- 12 AWG from the PSU to the distribution point, 14 AWG per heater.
- TCO = thermal cutoff (one-shot), mounted on the duct next to each PTC.
- Keep the heater return current off the ESP32 ground trace: use a star point at the PSU.

## Heater switch (×2)

![Heater channel: K1 contact, fuse, TCO, PTC, low-side MOSFET with gate resistor and pull-down](diagrams/heater-channel.svg)

```
 GPIO ──[100 Ω]──┬── Gate
                 │           N-MOSFET (logic-level, ≥30 A)
               [10 kΩ]       Drain ── Heater (−)
                 │           Source ── GND
 GND ────────────┴──
```

- The 10 kΩ pull-down holds the heater off during boot, reset, or a floating pin. **Mandatory.**
- If the MOSFET isn't fully on at 3.3 V, add a driver stage (NPN + pull-up to 12 V, gate clamped to ≤ 15 V).
- The load is resistive, so no flyback diode is needed.

## Master heater relay (K1)

![Master relay: BC337 drives the K1 coil with a flyback diode; K1 contact feeds HEAT_12V](diagrams/master-relay.svg)

```
 +12V ──┬── K1 coil A1          K1 contact 14 ── +12V
        │                       K1 contact 13 ── HEAT_12V (to heater fuses)
   1N4007 (cathode to +12V)
        │
        └── K1 coil A2 ── BC337 collector
                          BC337 emitter ── GND
 GPIO17 ──[470 Ω]── BC337 base
 GPIO17 ──[10 kΩ]── GND   (default OFF at boot)
```

- 12 V automotive relay, 30/40 A contacts, ~150 mA coil. The flyback diode is mandatory.
- Firmware closes K1 only with all heater gates low, and opens it only after they are low. The contacts never switch load current.

## Fan PWM (×2, open-drain)

```
 GPIO ──[100 Ω]── 2N7002 gate     gate ──[10 kΩ]── GND
                 drain ── fan blue (PWM)   (fan has internal pull-up)
                 source ── GND
```

- 25 kHz LEDC. **Inverted logic:** GPIO high pulls PWM low, which means slower. Handle this in the HAL.

## Fan tach (×2)

```
 3V3 ──[10 kΩ]──┬── GPIO 34 / 35 (input-only)
 fan yellow ────┘
```

- 2 pulses per revolution → `rpm = pulses_per_s × 30`.
- 10 nF to GND for noise filtering. **Not 100 nF:** 10 kΩ × 100 nF smears the ~450 Hz tach pulses at full speed.

## Fan power cut (×2, high-side)

```
 +12V ── P-MOSFET source
         gate ──[10 kΩ to source]  (default OFF)
         gate ──[10 kΩ]── NPN collector; NPN emitter ── GND
         NPN base ──[1 kΩ]── GPIO;  GPIO ──[10 kΩ]── GND
         drain ── fan red
```

- High-side, so the fan's ground stays solid and the tach reads correctly.
- The 10 kΩ / 10 kΩ divider holds V_GS at about −6 V. Small P-MOSFETs such as the AO3401A are rated ±12 V, so the full 12 V on the gate would be at the limit.

## Pin map (ESP32-WROOM-32)

| Function | GPIO | Notes |
|---|---|---|
| H1 gate | 25 | 10 kΩ pull-down |
| H2 gate | 26 | 10 kΩ pull-down |
| F1 PWM | 18 | via NPN / 2N7002, inverted |
| F2 PWM | 19 | via NPN / 2N7002, inverted |
| F1 tach | 34 | input-only, external 10 kΩ pull-up |
| F2 tach | 35 | input-only, external 10 kΩ pull-up |
| F1 power | 32 | → high-side P-MOSFET |
| F2 power | 33 | → high-side P-MOSFET |
| I2C SDA | 21 | SHT40, OLED |
| I2C SCL | 22 | |
| 1-Wire | 4 | DS18B20, 4.7 kΩ pull-up |
| Encoder A / B | 13 / 27 | optional |
| Encoder button | 23 | optional |
| Vent fan / servo | 16 | optional, dry mode |
| Master heater relay K1 | 17 | → BC337, 10 kΩ pull-down (open at boot) |

**Do not use:** GPIO 0, 2, 5, 12, 15 (strapping pins; GPIO12 sets the flash voltage); 1, 3 (USB serial); 6–11 (flash); 5, 14, 15 for heaters (they pulse or go high at boot).

The pin map lives in `firmware/include/config.h` (not created yet; it must include GPIO17). Keep this table and the schematic in sync with it.
