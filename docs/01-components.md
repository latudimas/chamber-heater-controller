# 01 – Components

## Bill of materials

| # | Part | Qty | Notes |
|---|---|---|---|
| 1 | ESP32-WROOM-32 dev board | 1 | Classic ESP32 (not S3/C6). USB via on-board CP2102/CH340. |
| 2 | 12 V 100 W PTC air heater (finned) | 2 | Face sized to the duct. Prefer ceramic/aluminium frame. |
| 3 | Nidec W40S12BS4A5-07 fan | 2 | 40×40×28 mm, 12 V, 0.73 A, 4-wire (PWM + tach). Side by side in one shared tunnel (ADR-019). |
| 4 | 12 V 24 A PSU | 1 | Mounted **outside** the enclosure. Earthed. |
| 5 | Logic-level N-MOSFET (heater switch) | 2 | Fully on at V_GS ≤ 3.3 V (e.g. IRLB8721, IRLR7843) **or** a gate driver stage. ≥ 30 A rating, low R_DS(on). |
| 6 | P-MOSFET + NPN driver (fan power cut) | 2 | High-side so the tach ground reference stays intact. e.g. AO3401A + BC547, with a gate divider (V_GS ±12 V limit). |
| 7 | Small N-MOSFET / NPN (fan PWM, open-drain) | 2 | e.g. 2N7002 / BC547. |
| 8 | SHT40 (or SHT31) breakout | 1 | Chamber air temp + RH, I2C. |
| 9 | DS18B20 (wired probe) | 1 | Heater outlet temperature, 1-Wire. Max 125 °C. |
| 9a | 12 V automotive relay (master heater relay K1) | 1 | 30/40 A contacts, ~150 mA coil. Driven by a BC337 + 1N4007 flyback diode. See ADR-013. |
| 10 | Thermal cutoff fuse, one-shot | 2 | One in series with each heater. ~100–120 °C, mounted on the duct near the PTC. |
| 11 | Blade/inline fuse + holder | 4 | ~10–12 A per heater channel, ~20–25 A main, 3 A for fans + logic. |
| 12 | SSD1306 0.96" OLED (I2C) | 1 | Optional local display. |
| 13 | Rotary encoder with push button | 1 | Optional local control. |
| 14 | Resistors, capacitors | – | 10 kΩ gate pull-downs, 100 Ω gate series, 10 kΩ tach pull-ups, 10 nF tach filters, 4.7 kΩ 1-Wire pull-up, 470 Ω relay base. Full list in the schematic. |
| 14a | 12 V → 5 V buck module | 1 | ≥ 1 A. Powers the ESP32 dev board. |
| 15 | Wire | – | 12 AWG main 12 V run, 14 AWG per heater, 22–24 AWG signals. |
| 16 | Duct | 1 | Draft v1 in [`hardware/duct/`](../hardware/duct/README.md): printed ASA cold side, sheet-metal hot side, silicone gasket between (ADR-018). |
| 17 | Vent (dry mode) | 1 | Optional small exhaust fan or servo flap to purge moist air. |

## Component notes

### Fans: Nidec W40S12BS4A5-07
- Reseller listings give 12 V, 0.73 A, ~13 500 RPM, ~28 CFM, ~1.2 inH₂O static pressure, 55 dBA. These are **not from a Nidec datasheet**, so verify them on the bench.
- Nidec lists an operating range of **−10 to 70 °C** for this fan family. The fans sit upstream of the PTC and see chamber air only, so this caps drying mode at **65 °C**.
- 4-wire. The usual Nidec colours are red = +12 V, black = GND, yellow = tach, blue = PWM. **Confirm with a multimeter.**
- Server fans often keep spinning at minimum speed with 0 % PWM. Real "off" needs the power cut.

### PTC heaters
- PTC elements limit themselves: output drops as airflow drops. Expect real output below the rated 100 W with 40 mm fans.
- Cold elements draw roughly 1.5× their running current for a few seconds. Two cold elements together can exceed the PSU's 24 A, which is why the start is staggered.
- Fin temperature with poor airflow can exceed what printed plastics tolerate.

### Sensors
- The ESP32's ADC is non-linear, and ADC2 is unusable while Wi-Fi is on. **All temperature sensing is digital.**
- SHT40: the chamber reference sensor for the PID loop. Mount it at roughly print height, away from the heater outlet jet.
- DS18B20: the outlet sensor right after the PTC. It is the main airflow/overheat safety signal.

### PSU: 12 V 24 A
- The running load is ~18.2 A (see [04-wiring.md](04-wiring.md)). That is fine continuously, but the cold-start surge of both heaters together is not.
- Verify the voltage stays ≥ 11.4 V at full load. If it sags, lower `max_power`.
