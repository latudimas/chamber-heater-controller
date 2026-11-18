# AGENTS.md

Guidance for AI coding agents (and humans) working in this repository.

## What this is

A standalone ESP32 controller for a 12 V, 2 × 100 W PTC air heater with two
4-wire fans. Used as a 3D printer chamber heater and a filament dryer. **It
switches ~200 W of heat unattended.** Treat safety-related code as critical.

Start by reading `README.md`, then `docs/02-system-design.md` and `docs/06-safety.md`.

## Repository layout

```
README.md               overview + doc index
AGENTS.md               this file
docs/                   design docs (source of truth for behaviour)
  decisions.md          ADR log + open questions
hardware/kicad/         KiCad schematic (+ PDF export)
firmware/               (not yet created) ESP32 firmware
  include/config.h      pin map, limits, defaults – single source of truth
host/                   (future) Klipper macros, shell scripts
```

## Hard rules

1. **Never weaken a safety invariant** listed in `docs/06-safety.md`. That includes: outputs off at boot, fan interlock before heat, latched faults, no auto-resume, the watchdog, and the mode limits. If a task seems to need one weakened, stop and ask.
2. **The safety layer is the last stage before the outputs.** No code path may write a heater GPIO except through it.
3. **No heater logic in hosts.** Klipper / scripts send commands only (`docs/07-klipper-integration.md`).
4. **One command parser.** Transports (serial, HTTP, MQTT, UI) only move bytes. Don't add transport-specific commands.
5. **Validate, don't clamp.** Out-of-range commands return `ERR E_RANGE`; never silently change user values.
6. **Pin map changes** must update `firmware/include/config.h`, `docs/04-wiring.md` **and** the schematic in `hardware/kicad/` in the same change. Never use GPIO 0, 2, 5, 12, 14, 15 for heater gates.
7. **Behaviour changes** must update the relevant doc in `docs/`. Design decisions get a new ADR entry in `docs/decisions.md` (supersede old ones; don't rewrite history).

## Conventions

- Units in names: `_c` (°C), `_s` (seconds), `_ms`, `_pct` (0–100), `_rpm`.
- Temperatures are `float` °C internally; durations are `uint32_t` seconds.
- Sensor values carry a validity flag and a timestamp; consumers must check staleness.
- Fault codes are prefixed `F_`, API error codes `E_` (see `docs/05-command-api.md`, `docs/06-safety.md`).
- Fan PWM is **inverted** at the hardware level (open-drain driver); invert only in the HAL, never in control code.

## Testing expectations

- Pure logic (state machine, PID, allocator, interlocks, command parser) must be host-testable without hardware. Keep it free of ESP-IDF/Arduino includes.
- Every new fault path needs a unit test that triggers it and asserts the heaters are off.
- Hardware-level checks follow `docs/08-commissioning.md`.

## Open decisions

See `docs/decisions.md` → Open questions. Notably the **firmware framework (ADR-012)** is undecided. Don't scaffold a framework-specific project until it's resolved.
