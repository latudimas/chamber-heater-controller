# 09 – FMEA (Failure Modes and Effects Analysis)

For each part, this lists how it can fail, what happens, how we notice, and what
stops it from becoming a hazard. It is a living document: add rows when parts,
wiring, or firmware change. Rows marked **GAP** have no adequate detection or
mitigation yet. Each gap has an action in [Open actions](#open-actions).

The first version was written from the design docs alone, before hardware was
assembled or firmware written. Detection entries that name a fault code describe
**intended** behaviour (see [06-safety.md](06-safety.md)) until firmware and
commissioning prove them.

## Severity scale

| Sev | Meaning | Example |
|---|---|---|
| **4** | Fire, burn, or smoke hazard | heater on with no airflow and no cutoff |
| **3** | Damage to the printer, enclosure, PSU, or filament | chamber overheats the printer's plastic parts |
| **2** | Loss of function, but the system stops in a safe state | false fault, heater won't start |
| **1** | Nuisance | wrong value on the OLED |

No likelihood or RPN numbers yet. Severity plus "is it detected?" is enough to
prioritise at this stage.

## Layer references

`L1` PTC physics · `L2` firmware safety layer · `L3` watchdog · `L4` gate
pull-downs · `L5` thermal cutoff (TCO) · `L6` electrical fuses · `L7` master heater relay K1 ·
`C` commissioning check ([08-commissioning.md](08-commissioning.md)).

## 1. Heater power path

| ID | Item | Failure mode | Effect | Sev | Detection | Mitigation | Status |
|---|---|---|---|---|---|---|---|
| FM-01 | Heater N-MOSFET | Fails **shorted** (most common MOSFET failure) | Heater on regardless of firmware. Fans still forced on by L2, so the PTC self-limits; if fans also fail, only the TCO stops it | 4 | `F_HEATER_STUCK` (outlet rises with gates low), planned | L7: firmware opens master relay K1; L5 (TCO) as backstop; L2 keeps fans at 100 % | Mitigated in design (A2). Detection pending firmware (A1) |
| FM-02 | Heater N-MOSFET | Fails open | Heater never heats | 2 | `F_NO_HEAT` | Replace part | OK |
| FM-03 | Heater N-MOSFET | Not fully enhanced at 3.3 V gate (wrong part / threshold) | MOSFET runs in linear region, overheats; may then fail shorted (→ FM-01) | 3 | None in firmware | Logic-level part spec'd at V_GS ≤ 3.3 V, or gate driver; C: measure V_DS and MOSFET temp at full load | **GAP** – A3 |
| FM-04 | Gate pull-down (10 kΩ) | Missing, open, or bad solder | Gate floats at boot / reset; heater may turn on with no airflow | 4 | None | L5; C: check gate-to-source resistance with power off | **GAP** – A4 |
| FM-05 | Gate series / GPIO | GPIO stuck high (ESP32 damaged) | Same as FM-01 | 4 | Same as FM-01 | Same as FM-01 | Same as FM-01 |
| FM-06 | TCO | Mounted too far from PTC / poor thermal contact | Doesn't trip in time; L5 ineffective | 4 | None | C: verify TCO placement and that its rating sits above `outlet_max` and normal fin temps but below duct material limits | **GAP** – A5 |
| FM-07 | TCO | Nuisance trip (rating too close to normal temps) | Heater channel dead until TCO replaced | 2 | `F_NO_HEAT` | Choose rating from commissioning fin-temp data | OK |
| FM-08 | Fuse | Wrong rating (too high) | Wiring overheats before fuse blows | 4 | None | Rate fuses to the wire gauge, not just the load; C: check ratings vs. 04-wiring | OK (design) |
| FM-09 | High-current connectors / crimps | High-resistance joint | Connector heats locally; fuse does **not** see this | 4 | None | Proper crimps / ferrules, rated connectors; C: touch/IR check of every joint after 30 min at full load | **GAP** – A6 |
| FM-10 | PTC element | Internal short | Fuse blows | 2 | `F_NO_HEAT` | L6 | OK |
| FM-11 | PTC element | Degrades (lower output) | Slower heat-up | 2 | `F_NO_HEAT` if severe | – | OK |
| FM-12 | Master relay K1 | Contacts welded closed | L7 lost; latent until a MOSFET also fails | 3 | None while MOSFETs work | K1 only switches with the gates low (no arcing); TCO still in place | Accepted (latent, low likelihood) |
| FM-13 | K1 driver (BC337) / GPIO17 | Shorted or stuck high | K1 always closed; L7 lost | 3 | None | 10 kΩ pull-down; TCO still in place | Accepted (latent) |
| FM-14 | Master relay K1 | Coil open / contacts never close | Heaters never heat | 2 | `F_NO_HEAT` | – | OK |
| FM-15 | K1 flyback diode | Missing or open | Coil kickback damages BC337 → FM-13 | 3 | None | 1N4007 across the coil; C: check polarity | OK (design) |

## 2. Airflow (fans)

| ID | Item | Failure mode | Effect | Sev | Detection | Mitigation | Status |
|---|---|---|---|---|---|---|---|
| FM-20 | Fan | Stalls / bearing seized | Fans share one tunnel with no backflow flaps: the other fan's air leaks back out through the stopped fan and flow over the PTCs collapses | 4 | `F_FAN_STALL` (RPM < `min_rpm` > 2 s) | Any heating needs both fans; a stall of either stops both heaters (ADR-019). Backflow flaps planned (A16) | OK |
| FM-21 | Fan tach wire | Broken / disconnected | Tach reads 0 → false stall | 2 | `F_FAN_STALL` (fails safe) | – | OK |
| FM-22 | Fan tach line | Noise / crosstalk counted as pulses | **Stalled fan reads as spinning**; interlock defeated | 4 | None | 10 kΩ pull-up + 10 nF filter, glitch filter in PCNT, plausibility check (RPM must be consistent with commanded PWM; RPM above fan max → invalid) | **GAP** – A7 |
| FM-23 | Fan / duct | Inlet or outlet blocked (RPM normal or high) | Low airflow while tach looks fine | 4 | `F_OUTLET_OVERTEMP` (DS18B20) | L1 (PTC self-limits), L5 | OK – relies on FM-31 being covered |
| FM-24 | Fan power P-MOSFET | Fails shorted | Fan can't be switched off (always on) | 1 | None needed | – | OK (safe) |
| FM-25 | Fan power P-MOSFET / NPN | Fails open | Fan off | 3 | `F_FAN_STALL` | – | OK |
| FM-26 | Fan PWM transistor | Shorted (PWM held low) | Fan at minimum speed or stopped | 3 | `F_FAN_STALL` if below `min_rpm`; otherwise outlet temp | Interlock uses RPM, not commanded PWM | OK |
| FM-27 | Fan | Air above 70 °C rating | Early fan failure | 2 | – | `dry` max target 65 °C; fans upstream of PTC | OK |
| FM-28 | Tach filter capacitor | Too large (e.g. 100 nF with 10 kΩ) | Pulses smeared at high RPM; tach reads low or zero → false stall | 2 | `F_FAN_STALL` (fails safe) | 10 nF in the schematic | OK (design) |
| FM-29 | Fan P-MOSFET gate | Full 12 V on the gate (no divider) | V_GS at the part's ±12 V limit; gate oxide failure → FM-24 or FM-25 | 2 | – | 10 kΩ / 10 kΩ divider, V_GS ≈ −6 V | OK (design) |

## 3. Sensors

| ID | Item | Failure mode | Effect | Sev | Detection | Mitigation | Status |
|---|---|---|---|---|---|---|---|
| FM-30 | DS18B20 (outlet) | Missing / CRC error / no response | No overheat backstop | 3 | `F_SENSOR` | Heaters off | OK |
| FM-31 | DS18B20 (outlet) | Probe dislodged out of the air stream | Reads low; outlet overheat undetected | 4 | None | Fix probe mechanically; plausibility: while heating, outlet must be ≥ chamber + margin within N s, else fault | **GAP** – A8 |
| FM-32 | DS18B20 | Returns 85.0 °C power-on default | Spurious reading | 2 | Should be rejected as invalid | Treat exactly 85.0 °C right after a conversion error / power-up as invalid | **GAP** – A9 |
| FM-33 | SHT40 (chamber) | Missing / I2C error | No control input | 2 | `F_SENSOR` | Heaters off | OK |
| FM-34 | SHT40 | Reads **low** (misplaced near cold spot, drifted) | PID over-heats chamber; `F_CHAMBER_OVERTEMP` uses the **same sensor**, so it won't fire | 3 | None independent | Mount per 01-components; outlet limit bounds air temp; C: compare with a reference thermometer | **GAP** – A10 |
| FM-35 | SHT40 / DS18B20 | Value frozen (sensor answers, but value never changes) | Staleness check (timestamp) passes; control blind | 3 | None | Treat "unchanged to the last bit for > N s while heating" as implausible | **GAP** – A11 |
| FM-36 | I2C bus (shared with OLED) | Bus hang (OLED or SHT40 holds SDA) | SHT40 goes stale | 2 | `F_SENSOR` | I2C bus recovery (clock out 9 pulses) before latching fault | OK |

## 4. Power supply

| ID | Item | Failure mode | Effect | Sev | Detection | Mitigation | Status |
|---|---|---|---|---|---|---|---|
| FM-40 | PSU | Voltage sag under load | ESP32 brownout reset | 2 | ESP32 brownout detector | L4 → outputs off; no auto-resume (ADR-009) | OK |
| FM-41 | PSU | Overload at cold start (both heaters) | PSU trips / sags | 2 | – | Staggered start | OK |
| FM-42 | PSU | Fails completely | Everything off | 2 | – | Safe by default | OK |
| FM-43 | Supply voltage | Not monitored | `F_BROWNOUT` can't fire; sag that doesn't reset the ESP32 goes unseen | 2 | None | Optional divider on an ADC1 pin | **GAP** – A12 (low priority) |
| FM-44 | Buck 12→5 V | Fails off | ESP32 off; pull-downs hold heaters off | 2 | – | L4 | OK |
| FM-45 | Star ground | Broken / heater current through ESP32 ground | Ground bounce; false readings, resets | 2 | Sensor faults, resets | Star ground at PSU; C: inspect | OK |

## 5. Controller and firmware

| ID | Item | Failure mode | Effect | Sev | Detection | Mitigation | Status |
|---|---|---|---|---|---|---|---|
| FM-50 | Firmware | Hang / infinite loop | Outputs frozen in last state | 4 | L3 hardware watchdog | Reset → outputs off | OK |
| FM-51 | Firmware | One task hangs (e.g. safety task) while another keeps feeding the watchdog | Safety checks stop; watchdog doesn't fire | 4 | None if watchdog fed from one place | Feed WDT only when **every** critical task has checked in | **GAP** – A13 |
| FM-52 | Firmware | Reset loop | Repeated boots | 2 | Boot counter | No auto-resume, so heaters stay off | OK |
| FM-53 | Stored config (NVS) | Corrupted / out of range | Wrong limits (e.g. `outlet_max` too high) | 4 | None | CRC on config + range-check on **load**, not only on command; fall back to defaults and latch a fault | **GAP** – A14 |
| FM-54 | Firmware | Logic bug in state machine / safety layer | Any invariant violated | 4 | Unit tests | TLA+ model of the safety state machine, checked with TLC plus mutation tests (`spec/`); CBMC on the C later | Design verified (model); code pending |
| FM-55 | Firmware | Wi-Fi / web stack starves CPU | Control or safety loop late | 3 | Task watchdog | Safety task at higher priority, pinned to a core | OK (design) |

## 6. Commands and environment

| ID | Item | Failure mode | Effect | Sev | Detection | Mitigation | Status |
|---|---|---|---|---|---|---|---|
| FM-60 | Command API | Out-of-range / malformed command | – | 1 | `ERR E_RANGE` | Validate, don't clamp | OK |
| FM-61 | Network | Anyone on the LAN can send `START` | Unwanted heating (bounded by mode limits) | 3 | None | Mode limits cap target and duration; consider auth token for HTTP/MQTT | **GAP** – A15 (low priority) |
| FM-62 | Host (Klipper) | Disconnects mid-run | Controller keeps running until timer/`STOP` | 2 | – | `max_duration` and `F_RUNTIME` bound it | OK |
| FM-63 | Enclosure | Left open / large leak | Can't reach target; heaters at 100 % for long | 2 | `F_NO_HEAT` | – | OK |
| FM-64 | Duct / mounts | Printed parts soften near PTC | Duct deforms, PTC touches plastic or fabric | 4 | None | Physical rules in 06-safety.md; C: measure fin temp, check materials | OK (design) |

## Open actions

Ordered by priority. Close an action by updating the row's Status and, if it
changes behaviour, the relevant doc and an ADR.

| # | Action | Closes | Type |
|---|---|---|---|
| A1 | Implement `F_HEATER_STUCK`: outlet temp rising with K1 closed and all gates low (temperature-based, ADR-014). Fault defined in 06-safety.md; needs firmware + unit test | FM-01, FM-05 | firmware |
| ~~A2~~ | ~~Add a firmware-controllable upstream disconnect~~ **Done in design:** master relay K1 (ADR-013, schematic) | FM-01, FM-05 | hardware |
| A3 | Pick the heater MOSFET (or driver) with R_DS(on) specified at V_GS = 3.3 V or less; add MOSFET temperature check to commissioning | FM-03 | hardware + C |
| A4 | Commissioning step: measure gate-to-source resistance (~10 kΩ) on each heater channel before first power-up | FM-04 | C |
| A5 | Commissioning step: verify TCO placement and rating against measured fin and outlet temps | FM-06 | C |
| A6 | Commissioning step: thermal check of every high-current joint after 30 min at full load | FM-09 | C |
| A7 | Tach plausibility: filter, reject RPM above fan max, require RPM consistent with commanded PWM | FM-22 | firmware + hardware |
| A8 | Outlet plausibility: while heating, outlet must exceed chamber by a margin within N s, else `F_SENSOR` | FM-31 | firmware |
| A9 | Reject DS18B20 85.0 °C power-on value | FM-32 | firmware |
| A10 | Decide whether an independent chamber overtemp check is needed (second sensor, or rely on outlet limit) | FM-34 | design |
| A11 | Frozen-value detection for both sensors | FM-35 | firmware |
| A12 | Optional supply voltage monitor on an ADC1 pin | FM-43 | hardware (low) |
| A13 | Multi-task watchdog check-in | FM-51 | firmware |
| A14 | Config CRC + range check on load | FM-53 | firmware |
| A15 | Optional auth for HTTP/MQTT | FM-61 | firmware (low) |
| A16 | Backflow flaps on each fan, so one fan can carry the heaters; then add FMEA rows for a flap stuck open/closed | FM-20 | hardware (improvement) |

Firmware actions (A1, A7–A9, A11, A13, A14) add fault paths. Per
[AGENTS.md](../AGENTS.md), each needs a unit test that triggers it and asserts
the heaters are off, and new fault codes must be added to
[06-safety.md](06-safety.md).
