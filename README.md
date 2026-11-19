# Chamber Heater Controller

A standalone, ESP32-based controller for a 12 V PTC air heater. Primary use is
heating a 3D printer enclosure (BIQU Panda Shelter) for ABS/ASA; secondary use is
filament drying. The controller owns **all** heating logic and safety. Hosts such
as Klipper, a phone, or a script only send high-level commands.

> Status: **design phase**. No firmware yet. Hardware partially sourced.

## At a glance

| Item | Choice |
|---|---|
| MCU | ESP32-WROOM-32 (classic ESP32) |
| Heaters | 2 × 12 V 100 W PTC, independently switched |
| Fans | 2 × Nidec W40S12BS4A5-07 (40×28 mm, 12 V, 0.73 A, 4-wire PWM + tach), side by side in one shared tunnel (both required for heat, ADR-019) |
| Airflow | Single shared channel: chamber air → fans → PTC grills → chamber |
| PSU | 12 V 24 A |
| Sensors | SHT40 (chamber temp + RH), DS18B20 (heater outlet) |
| Switching | Logic-level N-MOSFETs (heaters), high-side P-MOSFETs (fan power) |
| Control | PID on chamber temp, split-range across 2 heaters, staggered start |
| Modes | `heater`, `dry`, `vent` |
| Interfaces | Wi-Fi (HTTP + web UI, MQTT), USB serial; same command set on all |
| Klipper | Optional. Macros send commands only; no heater logic in Klipper |

## Docs

| Doc | Contents |
|---|---|
| [docs/01-components.md](docs/01-components.md) | Bill of materials and component notes |
| [docs/02-system-design.md](docs/02-system-design.md) | Architecture, state machine, control loop |
| [docs/03-modes.md](docs/03-modes.md) | Heater / dry / vent mode profiles and presets |
| [docs/04-wiring.md](docs/04-wiring.md) | Power budget, pin map, circuits |
| [docs/05-command-api.md](docs/05-command-api.md) | Command set over HTTP / MQTT / serial |
| [docs/06-safety.md](docs/06-safety.md) | Safety invariants, faults, hardware protections |
| [docs/07-klipper-integration.md](docs/07-klipper-integration.md) | How Klipper talks to the controller |
| [docs/08-commissioning.md](docs/08-commissioning.md) | Bring-up and test plan |
| [docs/09-fmea.md](docs/09-fmea.md) | Failure modes and effects analysis, open safety actions |
| [hardware/duct/](hardware/duct/README.md) | Duct v1 draft: printed + sheet-metal parts, STL/STEP, cutting templates |
| [hardware/kicad/](hardware/kicad/) | KiCad schematic ([PDF](hardware/kicad/chamber-heater.pdf)) |
| [spec/](spec/README.md) | TLA+ model of the safety state machine |
| [docs/decisions.md](docs/decisions.md) | Decision log (ADR-style) and open questions |
| [AGENTS.md](AGENTS.md) | Guidance for coding agents working in this repo |

## Development

Tooling comes from a Nix flake. With direnv the shell loads on `cd`; otherwise:

```bash
nix develop
make -C spec check     # model-check the safety state machine (TLA+)
make -C spec mutants   # prove the checks can fail
python docs/diagrams/gen_diagrams.py
```

KiCad is not in the flake; use the KiCad app.

## Roadmap

1. **Phase 1 – Hardware:** duct, PTC mounting, power distribution, MOSFET boards, fuses.
2. **Phase 2 – Firmware MVP:** state machine, safety layer, PID, serial command interface.
3. **Phase 3 – Network:** web UI, HTTP API, MQTT, OTA.
4. **Phase 4 – Integration:** Klipper macros, Moonraker sensor, dryer-box presets.
