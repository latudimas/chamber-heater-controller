# 02 – System Design

## Goals

- **Standalone.** Works with no host attached. Usable as a chamber heater, filament dryer, or vent fan.
- **Host-agnostic.** Klipper, a phone, MQTT or a script all send the same small command set. No host implements heater logic.
- **Safe by default.** Every output is off at boot, on fault, and on firmware hang.
- **Flexible.** Run with 1 or 2 heaters and 1 or 2 fans, within airflow interlocks.

## Physical layout

```
          chamber air
              │
              ▼
   ┌──────────┬───────────┐
   │ F1 40×28 │ F2 40×28  │   fans side by side, one shared tunnel
   ├──────────┴───────────┤   (no backflow flaps: both must run to heat)
   │  H1 PTC  │  H2 PTC   │   both grills across one shared channel
   ├──────────────────────┤
   │  DS18B20 outlet probe│
   └──────────┬───────────┘
              ▼
     warm air → chamber (aimed low/centre, not at the fabric)

   SHT40 elsewhere in the chamber, ~print height
```

The fans sit side by side and feed one shared tunnel, so either fan can blow
across both PTCs. There are no backflow flaps yet: if one fan stops, the other
fan's air leaks back out through it and the flow over the PTCs collapses.
Therefore **any heating needs both fans running**, and a stall of either fan
stops both heaters. Backflow flaps, which would allow 1-fan operation, are a
planned improvement. See ADR-019 (supersedes ADR-007).

## Logical architecture

```
 ┌──────────── Transports ────────────┐
 │ HTTP/Web UI │ MQTT │ USB serial │ UI│   (encoder + OLED)
 └──────┬─────────────────────────────┘
        │  Command (parsed + validated)
        ▼
 ┌──────────────── Command layer ────────────────┐
 │ validate against mode profile limits          │
 └──────┬────────────────────────────────────────┘
        ▼
 ┌──────────────── State machine ────────────────┐
 │ IDLE → PREHEAT → RUN → COOLDOWN → IDLE        │
 │          any ──fault──▶ FAULT (latched)       │
 └──────┬────────────────────────────────────────┘
        │ setpoint, fan profile, timer
        ▼
 ┌──── PID (chamber temp) ───▶ demand 0–200 % ───┐
 │                                               │
 │        Channel allocator (split-range,        │
 │        staggered start, 1 or 2 heaters)       │
 └──────┬────────────────────────────────────────┘
        ▼
 ┌──────────────── Safety layer ─────────────────┐
 │ fan RPM ok? outlet temp ok? sensors ok?       │
 │ runtime ok? watchdog fed? → else force OFF    │
 └──────┬────────────────────────────────────────┘
        ▼
   H1, H2 gates (slow PWM)   F1, F2 PWM + power
```

The safety layer is **last** before the outputs and can override everything
above it. Nothing upstream can bypass it.

## State machine

| State | Heaters | Fans | Exit |
|---|---|---|---|
| `IDLE` | off | off | valid `START` → `PREHEAT` |
| `PREHEAT` | off. Two phases: **spin-up** (K1 open) until both tachs read ≥ `min_rpm` (timeout → `F_FAN_STALL`); then **check** (K1 closes, gates still low) for one stuck-heater check window | mode profile, verified by tach | check passed → `RUN` |
| `RUN` | PID-driven | mode profile | timer expired, `STOP`, or end condition → `COOLDOWN` |
| `COOLDOWN` | off | 100 % | outlet < `cooldown_temp` **and** ≥ `cooldown_min_s` → `IDLE` |
| `FAULT` | off (forced) | 100 % while outlet is hot, then off | `CLEAR` with the cause resolved and outlet < `cooldown_temp` → `IDLE` |

Rules:
- `START` while in `RUN` is rejected. Use `SET` to change the target or duration.
- `STOP` from any non-fault state → `COOLDOWN`.
- A fault from any state → `FAULT`. The fault is latched and needs an explicit `CLEAR`.
- A reboot always lands in `IDLE`. There is no auto-resume (ADR-009).
- The master heater relay K1 is closed only in the check phase of `PREHEAT` and in `RUN` (ADR-013, safety invariant 9). Every other state and phase, including spin-up, `COOLDOWN` and `FAULT`, has K1 open.
- `CLEAR` is accepted only when the fault's cause is gone **and** the outlet is below `cooldown_temp`; otherwise the fans would stop while the PTC is still hot.
- These rules are model-checked in [`spec/`](../spec/README.md).

## Control loop

- **Process variable:** SHT40 chamber temperature, sampled every 1 s.
- **Controller:** PID with anti-windup (clamped integrator, plus integration frozen while the output is saturated). The PTC limits itself, so the plant is non-linear. Expect conservative gains.
- **Output:** demand `0–100 %` with one heater, `0–200 %` with two heaters.
- **Split-range allocation (2 heaters):**
  - H1 duty = `min(demand, 100)`
  - H2 duty = `max(demand − 100, 0)`
  - H2 only runs when H1 alone isn't enough.
  - Optional later: alternate which element leads, to spread wear.
- **Heater PWM:** slow time-proportioning, 1–10 Hz. The PTC's thermal mass smooths it out, and there are no switching-loss concerns.
- **`max_power`:** a per-channel duty cap, configurable. It is the PSU-headroom knob.
- **Fans are not PID-controlled.** Fan duty comes from the mode profile. Never run two loops that fight each other.

## Staggered start

Cold PTCs draw ~1.5× running current. Two together is ~25–30 A, which is above the 24 A PSU.

- When `RUN` starts, H1 switches on first (optionally ramping 30 % → 100 % over `ramp_s`).
- H2 is enabled only after `stagger_s` (default 8 s) **and** only if PID demand is above 100 %.
- The same rule applies whenever H2 turns on later from cold, e.g. after a long idle in `RUN`.

## Airflow interlock (shared channel)

| Heaters requested | Required |
|---|---|
| 0 | none |
| 1 or 2 | **both** fans powered, at ≥ `min_fan_pwm`, and both tachs ≥ `min_rpm` |

One fan is never enough while heating (shared tunnel without backflow flaps,
ADR-019). A `START` asking for heat with `fans=1` is refused with `E_INTERLOCK`;
a stall of either fan while heating latches `F_FAN_STALL`.

These are checked when a command is accepted **and** continuously while running.
The outlet temperature (`outlet_max`) is the backstop when the fan numbers are
wrong. See [06-safety.md](06-safety.md).

## Firmware structure (proposed)

```
firmware/
  src/
    main            – boot: outputs off, watchdog on, tasks start
    hal/            – gpio, ledc pwm, pcnt tach, i2c, onewire
    sensors/        – sht40, ds18b20, fan_tach (with validity + staleness)
    control/        – pid, allocator (split-range + stagger)
    core/           – state_machine, mode_profiles, timer
    safety/         – interlocks, fault latch, limits
    api/            – command parser (shared), serial, http, mqtt
    ui/             – oled, encoder (optional)
  include/config.h  – pin map, limits, defaults (single source of truth)
```

The command parser is **one** module. The transports only move bytes in and out.
