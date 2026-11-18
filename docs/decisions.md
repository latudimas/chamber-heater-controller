# Decision Log

Lightweight ADRs. Append new decisions; supersede old ones rather than editing them.

| ID | Decision | Status |
|---|---|---|
| ADR-001 | 12 V system instead of mains PTC | Accepted |
| ADR-002 | 2 × 100 W PTC instead of 1×50, 1×100 or 2×50 | Accepted |
| ADR-003 | Standalone controller, decoupled from Klipper | Accepted |
| ADR-004 | ESP32 (WROOM-32) instead of RP2040 | Accepted |
| ADR-005 | MOSFET switching instead of relay / SSR | Accepted |
| ADR-006 | PID with split-range + staggered start | Accepted |
| ADR-007 | Shared airflow channel, fans stacked in series | Accepted |
| ADR-008 | Digital sensors only (SHT40, DS18B20) | Accepted |
| ADR-009 | No auto-resume after reboot | Accepted |
| ADR-010 | Mode profiles: heater / dry / vent | Accepted |
| ADR-011 | Skip the W3230 thermostat | Accepted |
| ADR-012 | Firmware framework | **Open** |
| ADR-013 | Master relay upstream of the heater MOSFETs | Accepted |
| ADR-014 | Detect a stuck heater from temperature, no current sensing (for now) | Accepted |
| ADR-015 | Schematic in KiCad (`hardware/kicad/`) | Accepted |

---

### ADR-001: 12 V system
**Context:** A mains (220 V) PTC was available. Fans are 12 V.
**Decision:** Everything runs on 12 V DC.
**Why:** Safer to build and touch, simple MOSFET switching, one supply for fans and heaters.
**Cost:** High current (~17 A for heaters), so thick wiring and staggered starts are needed.

### ADR-002: 2 × 100 W PTC
**Context:** BIQU Panda Shelter, 84 × 58 × 58 cm (~0.28 m³), single-layer foil-lined fabric, leaky seams. Estimated loss ~160–240 W at a 15 K rise (30 °C room → 45 °C), minus ~50–80 W from the bed.
**Decision:** Two 100 W elements, independently switched.
**Why:** 2×50 W would be marginal (and real PTC output is below rated with small fans). Two channels give staging, redundancy, and a low-power mode for dryer boxes.
**Cost:** Exceeds the 24 A PSU on a simultaneous cold start → staggered start is mandatory. A `max_power` cap is available.

### ADR-003: Standalone controller
**Context:** It should also work for filament drying and other uses; Klipper should not be a dependency.
**Decision:** The controller owns all logic and safety. Hosts send high-level commands (`START`, `STOP`, `SET`, `STATUS`).
**Why:** Reusable, testable on its own, and a host crash doesn't affect heater safety.
**Cost:** Klipper's built-in heater features (verify_heater, PID UI) aren't used, so the controller reimplements them.

### ADR-004: ESP32 over RP2040
**Options:** RP2040 (clean boot pins, good USB, no Wi-Fi) vs ESP32 (Wi-Fi web UI, MQTT/HTTP, OTA, PCNT for tach, weak ADC, strapping-pin pitfalls).
**Decision:** ESP32. The board on hand is an ESP32-WROOM-32 (classic ESP32).
**Why:** Standalone use needs phone control; Klipper integration over HTTP is trivial. ADC weakness avoided by ADR-008; boot glitches avoided by the pin selection and pull-downs.

### ADR-005: MOSFET switching
**Decision:** Logic-level N-MOSFETs (low side) for heaters; high-side P-MOSFETs for fan power.
**Why:** Silent, no contact wear, PWM-capable. Relays wear and can't do PID; DC SSRs run hotter with more voltage drop.
**Note:** MOSFETs usually fail shorted, hence the thermal cutoff fuses (06-safety).

### ADR-006: PID, split-range, staggered start
**Decision:** One PID loop on chamber temperature → demand 0–200 %. H1 takes 0–100 %; H2 adds 100–200 %. H2 only enables after `stagger_s`.
**Why:** Smooth control, minimum number of active heaters, and the cold-start surge stays within the PSU limit.
**Alternatives:** Bang-bang (watermark) would be adequate for a chamber, but PID was requested and gives smoother dry-mode control.

### ADR-007: Shared channel, fans in series
**Decision:** One duct; both fans stacked push-push; both PTCs across the same channel.
**Why:** Any fan/heater combination is possible. In series, a stopped fan still passes air, whereas side by side in a shared plenum air leaks back out and flow collapses.
**Consequence:** The interlock is airflow-based (fan count, PWM, RPM, outlet temperature), not fixed pairs.

### ADR-008: Digital sensors only
**Decision:** SHT40 (chamber temp + RH) and DS18B20 (outlet).
**Why:** The ESP32 ADC is non-linear and ADC2 conflicts with Wi-Fi. RH is valuable for dry mode.

### ADR-009: No auto-resume
**Decision:** Always boot to `IDLE`.
**Why:** After an unexpected reset nobody may be present; restarting a heater silently is unsafe.

### ADR-010: Mode profiles
**Decision:** `heater`, `dry` and `vent` are data profiles over one state machine.
**Why:** Avoids duplicating logic; each mode has its own hard limits (e.g. dry capped at 65 °C by the fans' 70 °C rating).

### ADR-011: Skip the W3230
**Decision:** No interim W3230 thermostat phase.
**Why:** It can't do staging, fan interlocks, timers or modes; it would be throwaway work.

### ADR-012: Firmware framework (open)
**Options:**
- **ESPHome:** fastest; has `climate.pid`, fan, timer and web_server components. Less control over the custom state machine, split-range logic and fault latching.
- **Arduino-ESP32 (PlatformIO):** quick to start, enough control.
- **ESP-IDF (C) or Rust (esp-idf-hal):** full control, best for the watchdog/RTOS-task design; more effort.
**Leaning:** to be decided.

### ADR-013: Master relay upstream of the heater MOSFETs
**Context:** FMEA FM-01/FM-05: a heater MOSFET usually fails shorted, and a GPIO can be stuck high. Until now the one-shot TCO was the only thing that could stop the heater.
**Decision:** One 12 V automotive relay (K1, 30/40 A contacts) feeds both heater channels. The ESP32 drives it through a BC337 (GPIO17, 10 kΩ pull-down, so it is open at boot). Fans and logic are **not** behind K1. K1 is closed only in `PREHEAT` and `RUN`; it closes before any gate turns on and opens after the gates are low, so its contacts never switch load current.
**Why:** Cheap, simple, independent of the MOSFETs, and gives firmware a way to cut a heater it can no longer switch off. Supplements ADR-005 (the MOSFETs still do the PWM); does not replace it.
**Cost:** One relay, one transistor, one GPIO, ~150 mA coil current while heating. A welded relay is a latent failure; switching without load makes it unlikely.
**Alternatives:** A second high-side MOSFET per channel (no moving parts, more parts, shares the MOSFET failure mode); relying on the TCO alone (rejected).

### ADR-014: Detect a stuck heater from temperature
**Context:** FMEA action A1. With K1 in place, firmware still has to notice that a heater is on when it shouldn't be.
**Decision:** New fault `F_HEATER_STUCK`: the outlet temperature rises while every heater gate is low and K1 is closed. No current sensing for now.
**Why:** No extra hardware. K1 closes with the gates still low at the start of `PREHEAT`, which gives a natural check window before any heater is enabled.
**Cost:** Slower and less precise than current sensing. Revisit (INA219 or a shunt amplifier per channel) if commissioning shows the temperature check is too slow or noisy.

### ADR-015: Schematic in KiCad
**Decision:** The schematic lives in `hardware/kicad/` as a KiCad project, with a PDF export next to it for reading without KiCad.
**Why:** ERC checks connectivity, and the same project can later become a PCB.
**Note:** The pin map in the schematic must match `docs/04-wiring.md` and, once it exists, `firmware/include/config.h`.

---

## Open questions

- Firmware framework (ADR-012).
- Fan wire colours, confirmed with a multimeter.
- Which printer goes inside the shelter (sets the heater-mode `max_target`).
- Exact PTC part and its size compared with the duct cross-section.
- Duct material near the PTC.
- Dry-mode vent: passive hole vs exhaust fan vs servo flap.
- Whether `2 heaters + 1 fan` is allowed (depends on commissioning data).
- Heater MOSFET: is the IRLB8721 fully on at a 3.3 V gate, or is a gate driver needed? (FMEA A3)
- `F_HEATER_STUCK` thresholds: outlet rise and time window (set in commissioning).
