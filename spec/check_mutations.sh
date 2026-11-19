#!/usr/bin/env bash
# Mutation check: break the design on purpose and make sure TLC notices.
# Each mutant is "description|sed expression". A mutant that still passes
# means the properties have a blind spot.
set -u
cd "$(dirname "$0")"
TLC=${TLC:-tlc}
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT

mutants=(
  "K1 closes as soon as START (before fans confirmed)|s/relay' = (s \\\\in {\"CHECK\", \"RUN\"})/relay' = (s \\\\in Heating)/"
  "CLEAR allowed while the outlet is hot|s/^    \/\\\\ outCool$/    \/\\\\ TRUE/"
  # Airflow is guarded twice (interlock filter AND F_FAN_STALL), so each
  # alone is an equivalent mutant. Removing both must be caught.
  "no airflow interlock and no fan-stall fault|s/h1      == want1 \/\\\\ okHeat \/\\\\ air$/h1      == want1 \/\\\\ okHeat/; s/state \\\\in {\"CHECK\", \"RUN\"} \/\\\\ ~(fanOk1' \/\\\\ fanOk2')/FALSE/"
  "no stuck-heater detection|s/relay \/\\\\ ~g1 \/\\\\ ~g2 \/\\\\ shorted             -> \"F_HEATER_STUCK\"/FALSE -> \"F_HEATER_STUCK\"/"
  "no stagger for H2|s/air \/\\\\ g1prev \/\\\\ h1/air/"
  # Without backflow flaps one fan is not enough (ADR-019): allowing heat on
  # one fan, and faulting only when both stop, must be caught.
  "heat allowed on one fan|s/        air     == fanOk1' \/\\\\ fanOk2'/        air     == fanOk1' \\\\\/ fanOk2'/; s/~(fanOk1' \/\\\\ fanOk2')/~(fanOk1' \\\\\/ fanOk2')/"
  "fans not forced on in FAULT while hot|s/(s = \"FAULT\" \/\\\\ ~outCool')/FALSE/"
  "START accepts any target|s/IF ValidTarget(t)$/IF TRUE/"
  "fault can be cleared with its cause present|s/~CausePresent(code)$/TRUE/"
)

fail=0
for m in "${mutants[@]}"; do
  name=${m%%|*}; expr=${m#*|}
  sed "$expr" HeaterSafety.tla > "$work/HeaterSafety.tla"
  cp HeaterSafety.cfg "$work/"
  if cmp -s HeaterSafety.tla "$work/HeaterSafety.tla"; then
    echo "SED DID NOT APPLY: $name"; fail=1; continue
  fi
  out=$(cd "$work" && $TLC -workers auto -cleanup -metadir "$work/meta" -config HeaterSafety.cfg HeaterSafety.tla 2>&1)
  if grep -q "No error has been found" <<<"$out"; then
    echo "SURVIVED (blind spot!): $name"; fail=1
  else
    why=$(grep -m1 -E "^Error: (Invariant|Action property) .* is violated|^Error: Temporal properties were violated" <<<"$out" || echo "(see TLC output)")
    echo "killed: $name -> ${why#Error: }"
  fi
done
exit $fail
