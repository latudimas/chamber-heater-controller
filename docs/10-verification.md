# Verification flow

How a safety rule goes from words to a checked model to checked code. This is
the workflow for **everyone** changing safety behaviour: people, Claude, Codex,
Cursor, Copilot or any other agent. `AGENTS.md` summarises it; this file is the
detail.

Background: ADR-016 (TLA+ now, CBMC later), [docs/06-safety.md](06-safety.md)
(the rules), [spec/README.md](../spec/README.md) (what the model covers).

## The chain

```
docs/06-safety.md          the rules in plain words (requirements)
        │
        ▼
spec/HeaterSafety.tla      the same rules as a model
        │  make -C spec check     TLC explores every reachable state
        │  make -C spec mutants   deliberate design bugs must all be caught
        ▼
firmware safety core       plain C, no ESP-IDF/Arduino includes
        │  safety_step(state, inputs, pid_request) -> new state + outputs
        │  one C check function per TLA+ property (same name, see below)
        │
        ├─► unit tests      on the host; one per property and per fault path
        ├─► CBMC harness    any state, any inputs -> safety_step() -> assert
        │                   every check; covers the real C, not the model
        ▼
docs/08-commissioning.md   bench tests on the real hardware
```

Each stage catches what the one before cannot:

| Stage | Catches | Cannot catch |
|---|---|---|
| TLA+ / TLC | design errors: wrong state order, missing interlock, a fault that can be skipped | bugs in the C; timing; physics |
| Mutants | a property too weak to ever fail (a blind spot) | anything not written as a property |
| Unit tests | C bugs on the cases someone thought of | cases nobody thought of |
| CBMC | C bugs for **all** inputs within the bound (overflow, wrong branch, missed case) | hardware; anything longer than the bound |
| Commissioning | wiring, parts, real temperatures and timings | rare combinations (those are the jobs above) |

TLA+ does **not** generate code, and nothing proves automatically that the C
matches the model. The link is kept by the rules below.

## Rules that tie the code to the spec

1. **Order of work.** Docs → TLA+ (green, mutants caught) → C → tests → CBMC.
   Never change the C first and then adjust the spec to match.
2. **Same shape.** The C uses the spec's state names (`IDLE`, `SPINUP`,
   `CHECK`, `RUN`, `COOLDOWN`, `FAULT`) and one function, `safety_step()`,
   plays the role of the spec's `Tick` / `SetOutputs`. Outputs are written
   only from its result (AGENTS.md hard rule 2).
3. **Same names.** A TLA+ property maps to one pure C function:
   - `InvFooBar` (holds in every state) → `bool inv_foo_bar(const state_t *s)`
   - `PropFooBar` (about one step) → `bool prop_foo_bar(const state_t *prev, const state_t *next)`

   `state_t` here means everything the check needs: controller state, the
   latest inputs (tachs, sensors) and the outputs. A `Prop` check gets the
   value before and after one `safety_step()`.

   These functions live in one header (planned: `firmware/.../safety_checks.h`)
   and are used by the unit tests, the CBMC harness and, in debug builds, as
   runtime asserts. Write the check once and use it everywhere.
4. **Traceability.** Every property has a row in the table below. Adding,
   removing or renaming a property means updating its row in the same change.
5. **New properties come with a mutant.** A new property comes with a
   deliberate bug in `spec/check_mutations.sh` that the property catches.
   (The 9 existing mutants cover the main rules, not one per property.)
6. **A counterexample is a design bug.** If TLC finds a violation, fix the
   design (and the docs) or ask. Never weaken or delete a property to make it
   pass (AGENTS.md hard rule 1). Record the finding in `spec/README.md` →
   *What the model found*.

## Changing safety behaviour, step by step

1. Write the rule change in `docs/06-safety.md` (and `02-system-design.md` if
   states change). If it is a decision, add an ADR in `docs/decisions.md`.
2. Update `spec/HeaterSafety.tla` and, for a new property, `HeaterSafety.cfg`.
3. `make -C spec check`: must pass.
4. Add a mutant for any new property; `make -C spec mutants`: every mutant
   must be killed.
5. Change the C safety core. *(Once firmware exists.)*
6. Add or update the unit test(s): trigger the case, assert heaters off.
7. Add or update the CBMC check: `make -C firmware cbmc`. *(Planned.)*
8. Update the traceability table below.
9. If the change is physical (timings, temperatures, wiring), add a step to
   `docs/08-commissioning.md`.

If the docs and the spec disagree, stop and resolve it before writing code.

## Traceability

C and test names are **planned** (no firmware yet, ADR-012). Fill them in as
they are written; a dash means "not yet".

| Safety rule (06-safety) | TLA+ property | C check | Unit test | CBMC |
|---|---|---|---|---|
| 1. Outputs off at boot | `PropBootOff` | `prop_boot_off` | – | – |
| 2. Heat needs both fans (ADR-019) | `InvAirflow` | `inv_airflow` | – | – |
| 3, 4. Sensors valid, outlet not hot | `InvSensorsOutlet` | `inv_sensors_outlet` | – | – |
| 5. Fans run until outlet is cool | `InvCooldownFans`, `PropFansStopCool` | `inv_cooldown_fans`, `prop_fans_stop_cool` | – | – |
| 6. Faults latched, CLEAR needs cause gone + cool outlet | `PropLatched`, `InvFaultCode` | `prop_latched`, `inv_fault_code` | – | – |
| 7. No auto-resume | `PropNoAutoResume` | `prop_no_auto_resume` | – | – |
| 8. Mode limits | `InvTarget` | `inv_target` | – | – |
| 9. K1 only in CHECK/RUN, gates need K1 | `InvGatesNeedRelay`, `InvRelayOnlyHeating` | `inv_gates_need_relay`, `inv_relay_only_heating` | – | – |
| 9. K1 closes with gates low, opens after gates low | `PropRelayClosesFirst`, `PropRelayOpensAfterGates` | `prop_relay_closes_first`, `prop_relay_opens_after_gates` | – | – |
| Staggered start | `InvStagger` | `inv_stagger` | – | – |
| Layer 7: shorted MOSFET heats only while heating, with airflow | `InvHeatOnlyWhenHeating`, `InvHeatHasAirflow` | *(model only: needs a physical short)* | – | – |
| `F_HEATER_STUCK` cuts uncommanded heat | `PropStuckCut` | `prop_stuck_cut` | – | – |
| Type sanity | `TypeOK` | *(C types)* | – | – |

Not in the model, checked elsewhere: the watchdog, gate pull-downs, TCO and
fuses (commissioning); debounce and staleness timing (unit tests);
command-range validation `E_RANGE` (parser unit tests).

## Tooling

| Tool | Where | Status |
|---|---|---|
| TLA+ tools (`tlc`, `tlasany`) | Nix flake, `make -C spec check / mutants` | in use |
| C compiler + unit-test runner | Nix flake | planned, with the firmware |
| CBMC | Nix flake, `make -C firmware cbmc` | planned (ADR-016) |

The safety core has no framework includes, so the unit tests and CBMC do not
depend on the framework decision (ADR-012).
