# Shopping BOM (v1, perfboard build)

What to buy for the first build: the controller on perfboard (ADR-017), the
power wiring, and the duct hardware. Part references (R1, Q2, …) match the
KiCad schematic in [`kicad/`](kicad/chamber-heater.pdf). Quantities include a
few spares where parts are cheap and easy to lose or damage.

Tick the **Have** column for what you already own. Prices and shops are left
out on purpose: buy wherever is convenient, but read the *Look for* column.

> Heater current (8–12 A per channel) never runs on perfboard tracks
> (ADR-017). The heater MOSFETs sit on a heatsink with the heater wires
> attached directly to their legs; only the gate wire goes to the perfboard.

## 1. Main parts

| Have | Qty | Part | Look for | Notes |
|---|---|---|---|---|
| [ ] | 1 | ESP32 dev board (U1) | **ESP32-DevKitC V4, 38-pin, ESP32-WROOM-32** (classic ESP32, not S2/S3/C3) | The 30-pin clones have a different pinout; the schematic uses the 38-pin one |
| [ ] | 2 | PTC heater (HT1, HT2) | **12 V 100 W** finned PTC air heater, with mounting tabs | Measure it when it arrives: the duct uses placeholder sizes |
| [ ] | 2 | Fan | Nidec W40S12BS4A5-07, 40×40×28, 12 V, 4-wire | Measure the screw pitch (duct assumes 32 mm) |
| [ ] | 1 | PSU | 12 V 24 A (≈ 300 W), enclosed metal case, with earth terminal | Mounted outside the shelter |
| [ ] | 1 | Buck converter (U2) | 12 V → 5 V module, ≥ 1 A (e.g. MP1584 or LM2596 module) | Set it to 5.0 V **before** connecting the ESP32 |
| [ ] | 1 | Master heater relay (K1) | **12 V automotive relay, 4-pin SPST-NO, 30/40 A** (pins 30/87/85/86) + **socket with leads** | Coil ~150 mA. Contacts 30/87 = heater supply, 85/86 = coil |

## 2. Sensors and UI

| Have | Qty | Part | Look for | Notes |
|---|---|---|---|---|
| [ ] | 1 | Chamber temp + RH (J6) | **SHT40** breakout, I2C, 3.3 V (SHT31 also works) | Most breakouts include I2C pull-ups |
| [ ] | 1 (+1 spare) | Outlet temperature (J7) | **DS18B20 waterproof probe, stainless tip, with silicone or PTFE cable** | The cheap PVC-cable probes are rated ~85 °C; the outlet can run hotter. Spare is for `F_SENSOR` tests |
| [ ] | 1 | Display (J8, optional) | 0.96" SSD1306 OLED, **I2C**, 4-pin (GND VCC SCL SDA) | Check the pin order on yours |
| [ ] | 1 | Rotary encoder (J9, optional) | EC11 encoder with push button, or KY-040 module | |
| [ ] | 1 | Vent servo (J10, optional) | SG90 / MG90S micro servo | Dry mode only; can wait |

## 3. Semiconductors and passives (on the perfboard)

| Have | Qty to buy | Refs | Part | Notes |
|---|---|---|---|---|
| [ ] | 2 (+2) | Q2, Q3 | **IRLB8721PBF** N-MOSFET, TO-220 | Heater switches. Open question: fully on at a 3.3 V gate? (FMEA A3). Spares let you test |
| [ ] | 2 | – | TO-220 heatsink, small clip-on or bolt-on | One per heater MOSFET. The tab is the drain (heater −): don't let the two tabs touch, or use insulating pads |
| [ ] | 2 (+2) | Q4, Q6 | **AO3401A** P-MOSFET, SOT-23 | Fan power switches |
| [ ] | 2 (+2) | Q8, Q9 | **2N7002** N-MOSFET, SOT-23 | Fan PWM (open-drain) |
| [ ] | 4 | – | **SOT-23 to DIP/SIP adapter board** | So the SOT-23 parts fit the 2.54 mm perfboard |
| [ ] | 1 (+1) | Q1 | **BC337** NPN, TO-92 | Relay coil driver |
| [ ] | 2 (+2) | Q5, Q7 | **BC547** NPN, TO-92 | Fan power-cut drivers |
| [ ] | 1 (+2) | D1 | **1N4007** diode | Flyback across the relay coil. Mandatory |
| [ ] | 13 (+5) | R2, R4, R6, R7, R8, R10, R12–R15, R17, R19, R20 | 10 kΩ, ¼ W | Pull-downs, pull-ups, gate divider |
| [ ] | 4 (+2) | R3, R5, R11, R18 | 100 Ω, ¼ W | Gate series resistors |
| [ ] | 2 (+2) | R9, R16 | 1 kΩ, ¼ W | Fan driver base resistors |
| [ ] | 1 (+1) | R1 | 470 Ω, ¼ W | Relay driver base |
| [ ] | 1 (+1) | R21 | 4.7 kΩ, ¼ W | 1-Wire pull-up |
| [ ] | 2 (+2) | C1, C2 | 10 nF ceramic | Tach filters. **Not 100 nF** |

A ¼ W resistor assortment kit covers all of these and is often cheaper than
buying values one by one.

## 4. Protection

| Have | Qty | Part | Look for | Notes |
|---|---|---|---|---|
| [ ] | 1 holder + 2 fuses | F1, main | Inline blade (ATO/ATC) fuse holder for **12 AWG**, **25 A** fuse | Right after the PSU |
| [ ] | 2 holders + 4 fuses | F2, F3, heaters | Inline blade fuse holder for 14 AWG, **15 A** fuse | One per heater channel (ADR-020) |
| [ ] | 1 holder + 2 fuses | F4, fans + logic | Inline blade fuse holder, **3 A** fuse | Feeds the fans and the buck module, not through K1 |
| [ ] | 2 + spares | TCO1, TCO2 | **One-shot thermal fuse (thermal cutoff), ≥ 10 A**, in a metal or axial package | Buy a small set of ratings (e.g. 102, 115, 121 °C): the right one is picked from commissioning fin/outlet temperatures (FMEA A5) |

**Why 15 A per heater (ADR-020):** the fuse protects the 14 AWG wire against
a short; overheating is caught by the TCO, K1 and the firmware. 15 A runs at
55 % at 8.3 A and doesn't age on the ~12.5 A cold start, while 10 A would sit
at 83 % and risk nuisance blows. There is no 12 A blade fuse.

## 5. Connectors, board and wiring

| Have | Qty | Part | Look for | Notes |
|---|---|---|---|---|
| [ ] | 1 | Perfboard | Double-sided FR4, 2.54 mm pitch, about 9 × 15 cm | |
| [ ] | 2 | ESP32 socket | 1×19 female header, 2.54 mm | Lets you unplug the DevKit. Check the row spacing on your board |
| [ ] | 2 | Fan headers (J4, J5) | 4-pin 2.54 mm header + housing (PC-fan style or JST-XH 4-pin) | Pin 1 GND, 2 +12 V switched, 3 tach, 4 PWM. Check your fan wire colours with a meter |
| [ ] | 1 set | Sensor/UI headers (J6–J10) | JST-XH 3/4/5-pin sockets + pre-crimped leads, or 2.54 mm male headers + Dupont leads | J6/J8 4-pin, J7/J10 3-pin, J9 5-pin |
| [ ] | 1 | Power distribution | Lever connectors (e.g. Wago 221) or a small barrier terminal strip | +12 V split and the **star ground** at the PSU, off the perfboard |
| [ ] | 2 m each | 12 AWG wire, red + black | Silicone insulation | PSU → main fuse → relay / branches |
| [ ] | 2 m each | 14 AWG wire, red + black | **Silicone** insulation (heat-resistant) | Heater runs, MOSFET drain/source |
| [ ] | 1 set | 22–24 AWG hookup wire | Several colours | Signals, fans, sensors |
| [ ] | 1 set | Ring terminals, ferrules, heat-shrink | For 12 and 14 AWG | Crimp properly; the FMEA flags loose high-current joints (FM-09) |
| [ ] | 4 | M3 standoffs + screws | 10 mm | Mounting the perfboard |

## 6. Duct hardware

This list is for the **horizontal** duct; see [`duct/horizontal/README.md`](duct/horizontal/README.md)
for where each one goes. The [vertical](duct/vertical/README.md) and
[folded](duct/folded/README.md) designs list their own hardware.

| Have | Qty | Part | Notes |
|---|---|---|---|
| [ ] | 8 (+4) | M3 heat-set inserts, ≤ 6 mm long | Fan flange, 4 per fan |
| [ ] | 8 | M3 × 35–40 socket screws | Guard + fan + insert; length depends on the real fan depth |
| [ ] | 4 | M3 × 16 screws + nuts + washers | Clamp: printed flange, gasket, plate, outlet-box tabs |
| [ ] | 4 | M3 × 6 screws + nuts | PTC tabs to the metal plate |
| [ ] | 2+ | M3 screws or pop rivets | Outlet-box seam |
| [ ] | 1 | High-temperature silicone sheet, ~3 mm (or ceramic-fibre paper) | Gasket, about 130 × 90 mm |
| [ ] | – | Scrap aluminium or steel sheet, ~1 mm | PTC plate (124 × 80) and outlet box (354 × 46 strip + tabs) |
| [ ] | 1 roll | ASA filament | Transition and fan guard |
| [ ] | – | Thermal paste | TCO-to-metal contact |

## Not on this list yet

- An enclosure for the controller board (not designed yet).
- Backflow flaps for the fans (later improvement, FMEA A16).
- Current sensing (ADR-014 decided against it for v1).
