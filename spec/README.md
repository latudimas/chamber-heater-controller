# Formal model: safety state machine

`HeaterSafety.tla` models the controller's state machine and safety layer in
TLA+. TLC explores every reachable combination of inputs, commands and resets
and checks the safety invariants from [docs/06-safety.md](../docs/06-safety.md).

```bash
nix develop            # provides tlc, tlasany
make -C spec check     # model-check (a few seconds)
make -C spec mutants   # break the design on purpose; every mutant must be caught
```

## What is modelled

| Part | How |
|---|---|
| States | `IDLE`, `PREHEAT` (as two phases: `SPINUP`, `CHECK`), `RUN`, `COOLDOWN`, `FAULT` |
| Commands | `START t`, `SET t` (valid and invalid targets), `STOP`, `CLEAR` |
| Inputs | fan tach OK ×2, sensors OK, outlet hot, outlet cool, other fault, cooldown time elapsed. All change arbitrarily every tick |
| PID | Nondeterministic: may request any heater on or off. The safety layer must filter every request |
| Outputs | K1, both heater gates, both fan power switches |
| Failures | H1 MOSFET may fail shorted at any time; watchdog reset / power loss (`Reboot`) |

## What is checked

| Check | Safety doc |
|---|---|
| `InvAirflow`: a gate is on only with both fans running (shared tunnel, ADR-019) | invariant 2 |
| `InvSensorsOutlet`: no gate on with bad sensors or a hot outlet | 3, 4 |
| `InvStagger`: H2 never on without H1 | staggered start |
| `InvGatesNeedRelay`, `InvRelayOnlyHeating` | 9 |
| `InvHeatOnlyWhenHeating`, `InvHeatHasAirflow`: even with a shorted MOSFET, heat flows only while heating, with both fans | layer 7 (K1) |
| `InvCooldownFans`, `PropFansStopCool`: fans run until the outlet is cool | 5 |
| `InvTarget`: mode limits | 8 |
| `PropLatched`: `FAULT` is left only by `CLEAR` (cause gone) or reboot | 6 |
| `PropNoAutoResume`: heating starts only from `START` | 7 |
| `PropBootOff`: outputs off after reboot | 1 |
| `PropRelayClosesFirst`, `PropRelayOpensAfterGates` | 9 |
| `PropStuckCut`: uncommanded heat is cut within one tick | `F_HEATER_STUCK` |

## What the model found

Writing the model against the docs exposed three gaps, now fixed in the docs.
The mutation check keeps the old, doc-literal behaviour as mutants, so TLC
shows each one failing:

1. **K1 closed before the fans were confirmed.** The old `PREHEAT` closed K1
   straight away. With a shorted MOSFET and a fan that hadn't spun up, the
   heater would run with no airflow (TLC: `InvHeatHasAirflow` violated).
   `PREHEAT` now has a spin-up phase (K1 open) and closes K1 only after both
   tachs read OK.
2. **`CLEAR` while hot stopped the fans.** `CLEAR` went straight to `IDLE`
   (fans off) even if the outlet was still hot. `CLEAR` now also requires the
   outlet to be below `cooldown_temp`.
3. **K1 opening order.** "Opens only after every gate is low" is met within
   one control tick: the firmware writes the gates low first, then K1. This is
   an ordering rule for the output code (and a unit test), not a delay.

One open question was found and left for later: see `docs/decisions.md`
→ Open questions (a watchdog reset loses the latched fault).

## Limits: what this does NOT prove

- **Timing.** Ticks are abstract; debounce times (2 s stall, 3 s staleness,
  `stuck_check_s`) are folded into the inputs. Stuck-heater detection is
  assumed to take one tick.
- **Physics.** Temperatures are booleans. The model doesn't know that a PTC
  self-limits or how fast the chamber heats.
- **Hardware.** TCO, fuses, gate pull-downs and the watchdog are not modelled.
  K1 and its driver are assumed not to fail (FMEA FM-12, FM-13).
- **Code.** This checks the design, not the firmware. Once the C exists, CBMC
  harnesses check the code against the same invariants (ADR-016).

## Mutation check

`check_mutations.sh` applies one deliberate bug at a time and expects TLC to
fail. A mutant that survives means a property has a blind spot. Airflow is
guarded twice (interlock filter **and** `F_FAN_STALL`), so removing only one of
them survives by design; the mutant removes both.
