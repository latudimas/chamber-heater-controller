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
| ADR-007 | Shared airflow channel, fans stacked in series | Superseded by ADR-019 |
| ADR-008 | Digital sensors only (SHT40, DS18B20) | Accepted |
| ADR-009 | No auto-resume after reboot | Accepted |
| ADR-010 | Mode profiles: heater / dry / vent | Accepted |
| ADR-011 | Skip the W3230 thermostat | Accepted |
| ADR-012 | Firmware framework | **Open** |
| ADR-013 | Master relay upstream of the heater MOSFETs | Accepted |
| ADR-014 | Detect a stuck heater from temperature, no current sensing (for now) | Accepted |
| ADR-015 | Schematic in KiCad (`hardware/kicad/`) | Accepted |
| ADR-016 | Formal verification: TLA+ model of the safety state machine now, CBMC on the C later; Nix dev shell | Accepted |
| ADR-017 | Build v1 on perfboard, no custom PCB | Accepted |
| ADR-018 | Duct v1: printed cold side, metal hot side, floor-standing | Proposed (draft) |
| ADR-019 | Fans side by side in one shared tunnel, no backflow flaps; heat needs both fans | Accepted |
| ADR-020 | Heater channel fuses 15 A | Accepted |
| ADR-021 | Three duct layouts (horizontal, vertical upflow, folded slab), one folder each | Proposed (draft) |

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

### ADR-016: Formal verification with TLA+, then CBMC
**Context:** The controller switches ~200 W unattended. Unit tests check the cases someone thought of; a model checker checks every interleaving of inputs, commands and resets.
**Decision:** The safety state machine is modelled in TLA+ (`spec/HeaterSafety.tla`) and checked with TLC (`make -C spec check`). A mutation script (`make -C spec mutants`) breaks the design on purpose to prove the properties can fail. Once the firmware exists, CBMC harnesses check the C safety layer against the same invariants. Tooling comes from a Nix flake (`nix develop`).
**Why:** TLA+ works before any code exists and finds design bugs while they are cheap. The first run changed the design: `PREHEAT` gained a fan spin-up phase before K1 closes, and `CLEAR` now also needs a cool outlet.
**Cost:** The model is an abstraction (booleans, ticks) and can drift from the docs and code; keep them in step. KiCad is not in the flake (the nixpkgs build is broken here); use the KiCad app.

### ADR-017: Build v1 on perfboard
**Context:** One unit; open questions (gate drive at 3.3 V, commissioning thresholds) may change the circuit.
**Decision:** v1 is built on perfboard with the ESP32 dev board. Heater current (8–12 A per channel) stays on 14 AWG wire, screw terminals, inline fuse holders and a socketed automotive relay, never on perfboard tracks. Only logic, drivers and sensor headers go on the board.
**Why:** Fast to build and change; avoids designing high-current PCB traces.
**Revisit:** after commissioning. The KiCad schematic carries over to a PCB if one is wanted; heater current would still stay off the board.

### ADR-018: Duct v1 layout and materials (proposed)
**Context:** Fin temperatures can exceed what printed plastic tolerates. The unit stands on the shelter floor next to the printer. Parts are printed on an Ender-3 V3 KE (220 × 220) and the metal is cut by hand from scrap.
**Decision:** Air path: guard → 2 fans side by side (ADR-019) → printed taper (77 × 37 → 60 × 60) → silicone gasket → flat metal plate holding both PTCs by their tabs (windows = fin area, so no bypass) → bent sheet-metal outlet box. Plastic only upstream of the gasket. 4 M3 bolts clamp flange, gasket, plate and box tabs. The transition has its own feet. Design: `hardware/duct/` (SolidCraft, parametric) with 1:1 templates for the metal parts.
**Why:** The hot zone is metal only; the flat plate and simple bent box suit hand fabrication; one print, no supports.
**Open:** PTC sizes come from the previous project's 220 V 50 W heater, not the 12 V 100 W heaters this controller is designed for. The fin window, tab position and fan screw pitch are estimates. Status stays *Proposed* until those are measured and a cold fit passes.

### ADR-019: Fans side by side in a shared tunnel (supersedes ADR-007)
**Context:** Stacking the fans (ADR-007) makes the unit longer and feeds a wide PTC face through a small 40 × 40 opening. The owner wants the fans side by side, with either fan able to blow across both PTCs.
**Decision:** Both fans sit side by side (80 × 40) and feed one shared tunnel in front of both PTCs. No backflow flaps in v1. Because a stopped fan lets the other fan's air leak back out, **any heating requires both fans running**; a stall of either fan latches `F_FAN_STALL` and stops both heaters. `START` with heat and `fans=1` returns `E_INTERLOCK`.
**Why:** Shorter unit; the fan outlet matches the wide PTC face better; simpler than flaps for a first build.
**Cost:** No redundancy: losing one fan stops heating (safely). Backflow flaps (FMEA A16) are the planned improvement that would allow 1-fan operation.
**Model:** `spec/HeaterSafety.tla` requires both fans for any gate (`InvAirflow`, `InvHeatHasAirflow`); a mutant that allows one fan is caught.

### ADR-020: Heater channel fuses 15 A
**Context:** The docs said 10–12 A per heater. Blade fuses come in 10 A or 15 A, not 12 A. Each heater runs at ~8.3 A, with ~12.5 A for a few seconds from cold.
**Decision:** 15 A blade fuse per heater channel (F2, F3). Main fuse stays 25 A, fans + logic 3 A.
**Why:** The fuse's job is to protect the 14 AWG silicone wire against a short, which 15 A does. Overheating is handled by the TCO, K1 and the firmware, not the fuse. A 10 A fuse would run at 83 % of its rating and take a 125 % overload on every cold start, risking nuisance blows (and the temptation to fit a bigger fuse without thinking).


### ADR-021: Three duct layouts, one folder each (proposed)
**Context:** The horizontal duct (ADR-018) is about 162 × 131 × 100 mm, mostly because of its taper and flange, and it only suits a floor-standing unit. The owner wants a smaller unit that can be reused inside a filament dryer box or another printer's enclosure. The 12 V 100 W PTCs have not arrived, so all sizes still come from the previous project's 220 V 50 W heater.
**Decision:** Keep three parametric designs side by side, each in its own folder with the same structure (`hardware/duct/horizontal/`, `vertical/`, `folded/`; the ADR-018 files moved to `horizontal/`):
- **Vertical upflow:** printed inlet base with side slots → fan deck with both fans side by side blowing up → plenum → gasket → PTC plate → metal hood with a side outlet. About 100 × 86 × 126 mm.
- **Folded slab:** fans behind the front wall blowing to the back, one under each PTC → air turns up through the PTC plate → metal hood → outlet on the same front face. About 196 × 50 × 114 mm.
All three keep ADR-018's materials rule (plastic only upstream of the gasket, metal plate and metal outlet part downstream) and ADR-019's shared plenum, so heating still needs both fans. The folded design places the fans apart, but in one plenum, so ADR-019's reasoning is unchanged. No firmware, spec or safety rule changes.
**Why:** Upward flow keeps the fans in the coolest air (they cap dry mode at 65 °C) and lets residual heat rise away from the fans and printed parts after a stop. The folded slab trades two turns and some risk of recirculation for a 50 mm depth. Keeping all three lets the real PTC size and the target host decide.
**Recommended first build:** vertical.
**Open:** Same as ADR-018: PTC sizes, fin window, tab width and fan screw pitch are placeholders or estimates. Status stays *Proposed* until the 12 V 100 W PTCs are measured, the chosen design is updated and a cold fit passes. For the folded design, also measure the fan intake temperature in dry mode (hot outlet air on the same face).

---

## Open questions

- Firmware framework (ADR-012).
- Fan wire colours, confirmed with a multimeter.
- Which printer goes inside the shelter (sets the heater-mode `max_target`).
- Exact PTC part and its size compared with the duct cross-section. All three duct designs use the previous project's 220 V 50 W PTC dimensions as placeholders; confirm the 12 V 100 W parts (see each design's README in `hardware/duct/` → Verify first).
- Duct material near the PTC: proposed in ADR-018 (metal hot side, silicone gasket); confirm with commissioning temperatures.
- Which duct layout to build first (ADR-021): vertical recommended; depends on the real PTC size and where the unit goes.
- Dry-mode vent: passive hole vs exhaust fan vs servo flap.
- Backflow flaps (FMEA A16) to allow heating on one fan; until then any heating needs both fans (ADR-019).
- Heater MOSFET: is the IRLB8721 fully on at a 3.3 V gate, or is a gate driver needed? (FMEA A3)
- `F_HEATER_STUCK` thresholds: outlet rise and time window (set in commissioning).
- A watchdog reset loses the latched fault (RAM) and switches the fans off even if the outlet is hot. Persist the fault code across resets (RTC memory / NVS), and run the fans at boot while the outlet is hot? (Found while modelling; the TLA+ `Reboot` action currently assumes power-loss behaviour.)
