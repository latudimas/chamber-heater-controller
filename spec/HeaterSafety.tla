---------------------------- MODULE HeaterSafety ----------------------------
(***************************************************************************)
(* Safety state machine of the chamber heater controller.                  *)
(*                                                                         *)
(* Source of truth for the behaviour: docs/02-system-design.md and         *)
(* docs/06-safety.md. This model checks the invariants listed there.       *)
(*                                                                         *)
(* Abstractions (what this model does NOT prove):                          *)
(*  - Time is a sequence of control ticks. Debouncing (2 s fan stall,      *)
(*    3 s staleness, stuck_check_s) is folded into the boolean inputs:     *)
(*    an input is the firmware's already-debounced view.                   *)
(*  - The PID is nondeterministic: it may ask for any heater on or off.    *)
(*    The model shows the safety layer filters every possible request.    *)
(*  - Temperatures are booleans (outlet hot, outlet cool).                 *)
(*  - One heater MOSFET (H1) may fail shorted at any time.                 *)
(*  - Hardware layers (TCO, fuses, pull-downs, watchdog) are not modelled; *)
(*    a watchdog reset is the Reboot action.                               *)
(*  - The relay K1 and its driver never fail (FMEA FM-12, FM-13).          *)
(***************************************************************************)
EXTENDS Naturals

CONSTANTS
    MinT, MaxT,     \* mode limits: valid targets are MinT..MaxT
    CmdTargets      \* target values a command may carry, valid or not

States  == {"IDLE", "SPINUP", "CHECK", "RUN", "COOLDOWN", "FAULT"}
Heating == {"SPINUP", "CHECK", "RUN"}       \* the three PREHEAT/RUN phases
Codes   == {"NONE", "F_SENSOR", "F_OUTLET_OVERTEMP", "F_FAN_STALL",
            "F_OTHER", "F_HEATER_STUCK"}

VARIABLES
    \* ---- inputs: the firmware's debounced view of the world ----
    fanOk1, fanOk2,  \* tach RPM >= min_rpm
    sensOk,          \* all sensors present, fresh, plausible
    outHot,          \* outlet >= outlet_max
    outCool,         \* outlet <  cooldown_temp
    otherFault,      \* F_NO_HEAT / F_RUNTIME / F_CHAMBER_OVERTEMP condition
    coolMin,         \* cooldown_min_s has elapsed
    shorted,         \* (physical, not observable) H1 MOSFET failed shorted
    \* ---- controller ----
    state, code, target,
    g1prev,          \* H1 gate was on last tick (stagger: H2 only after H1)
    act,             \* name of the last action, for the action properties
    \* ---- outputs ----
    relay,           \* master heater relay K1 closed
    g1, g2,          \* heater gates
    f1, f2           \* fan power

inputs == <<fanOk1, fanOk2, sensOk, outHot, outCool, otherFault, coolMin, shorted>>
ctrl   == <<state, code, target, g1prev, act>>
outs   == <<relay, g1, g2, f1, f2>>
vars   == <<inputs, ctrl, outs>>

ValidTarget(t) == t \in MinT..MaxT

\* Is heat actually being produced? A shorted MOSFET heats whenever K1 is closed.
Energized == relay /\ (g1 \/ g2 \/ shorted)

\* Airflow the interlock requires for one / two heaters.
Air1 == (f1 /\ fanOk1) \/ (f2 /\ fanOk2)
Air2 == f1 /\ fanOk1 /\ f2 /\ fanOk2

\* Is the cause of a latched fault still present (for CLEAR)?
\* A shorted MOSFET can't be observed with K1 open; the CHECK phase of the
\* next start finds it again.
CausePresent(c) ==
    CASE c = "F_SENSOR"          -> ~sensOk
      [] c = "F_OUTLET_OVERTEMP" -> outHot
      [] c = "F_FAN_STALL"       -> ~(fanOk1 /\ fanOk2)
      [] c = "F_OTHER"           -> otherFault
      [] OTHER                   -> FALSE

-----------------------------------------------------------------------------
(* Output stage: outputs are a function of the new state and the inputs.    *)
(* want1/want2 are the PID's (arbitrary) requests. Primed inputs are used    *)
(* because the firmware reads inputs, then writes outputs, in one tick.     *)

SetOutputs(s, want1, want2) ==
    LET fans    == s \in Heating \/ s = "COOLDOWN" \/ (s = "FAULT" /\ ~outCool')
        air1    == fanOk1' \/ fanOk2'
        air2    == fanOk1' /\ fanOk2'
        okHeat  == s = "RUN" /\ sensOk' /\ ~outHot'
        h1      == want1 /\ okHeat /\ air1
        h2      == want2 /\ okHeat /\ air2 /\ g1prev /\ h1
    IN  /\ f1' = fans
        /\ f2' = fans
        /\ relay' = (s \in {"CHECK", "RUN"})
        /\ g1' = h1
        /\ g2' = h2
        /\ g1prev' = h1

AllOff == ~relay /\ ~g1 /\ ~g2 /\ ~f1 /\ ~f2

-----------------------------------------------------------------------------
Init ==
    /\ fanOk1 \in BOOLEAN /\ fanOk2 \in BOOLEAN /\ sensOk \in BOOLEAN
    /\ outHot \in BOOLEAN /\ outCool \in BOOLEAN /\ ~(outHot /\ outCool)
    /\ otherFault \in BOOLEAN /\ coolMin \in BOOLEAN /\ shorted \in BOOLEAN
    /\ state = "IDLE" /\ code = "NONE" /\ target = MinT /\ g1prev = FALSE
    /\ act = "Boot"
    /\ relay = FALSE /\ g1 = FALSE /\ g2 = FALSE /\ f1 = FALSE /\ f2 = FALSE

\* Fault detection while heating, on the new inputs.
\* Stuck heater: K1 was closed and both gates were low last tick, yet heat
\* was produced (outlet rising). Uses last tick's outputs.
DetectFault ==
    CASE ~sensOk'                                   -> "F_SENSOR"
      [] outHot'                                    -> "F_OUTLET_OVERTEMP"
      [] state \in {"CHECK", "RUN"} /\ ~(fanOk1' /\ fanOk2') -> "F_FAN_STALL"
      [] otherFault'                                -> "F_OTHER"
      [] relay /\ ~g1 /\ ~g2 /\ shorted             -> "F_HEATER_STUCK"
      [] OTHER                                      -> "NONE"

\* One control tick: the world changes, the controller reacts.
Tick ==
    /\ fanOk1' \in BOOLEAN /\ fanOk2' \in BOOLEAN /\ sensOk' \in BOOLEAN
    /\ outHot' \in BOOLEAN /\ outCool' \in BOOLEAN /\ ~(outHot' /\ outCool')
    /\ otherFault' \in BOOLEAN /\ coolMin' \in BOOLEAN
    /\ shorted' \in {shorted, TRUE}             \* a MOSFET can fail; never heals
    /\ act' = "Tick"
    /\ UNCHANGED target
    /\ \E want1, want2 \in BOOLEAN :
        LET f == IF state \in Heating THEN DetectFault ELSE "NONE"
            s == IF f # "NONE" THEN "FAULT"
                 ELSE CASE state = "SPINUP" /\ fanOk1' /\ fanOk2' -> "CHECK"
                        [] state = "CHECK"                         -> "RUN"
                        [] state = "COOLDOWN" /\ outCool' /\ coolMin' -> "IDLE"
                        [] OTHER                                   -> state
        IN  /\ state' = s
            /\ code'  = IF f # "NONE" THEN f ELSE code
            /\ SetOutputs(s, want1, want2)

\* START <mode> <target>. Rejected (ERR E_RANGE) unless the target is valid.
Start(t) ==
    /\ state = "IDLE"
    /\ UNCHANGED inputs
    /\ IF ValidTarget(t)
       THEN /\ state' = "SPINUP" /\ target' = t /\ act' = "Start"
            /\ UNCHANGED code
            /\ SetOutputs("SPINUP", FALSE, FALSE)
       ELSE /\ act' = "Reject" /\ UNCHANGED <<state, code, target, g1prev, outs>>

\* SET target while running.
Set(t) ==
    /\ state \in Heating
    /\ UNCHANGED <<inputs, state, code, g1prev, outs>>
    /\ IF ValidTarget(t) THEN target' = t /\ act' = "Set"
                         ELSE UNCHANGED target /\ act' = "Reject"

Stop ==
    /\ state \in Heating
    /\ UNCHANGED <<inputs, code, target>>
    /\ state' = "COOLDOWN" /\ act' = "Stop"
    /\ SetOutputs("COOLDOWN", FALSE, FALSE)

\* CLEAR: refused while the cause is present; the outlet must be cool too,
\* otherwise the fans would stop while the PTC is still hot.
Clear ==
    /\ state = "FAULT"
    /\ ~CausePresent(code)
    /\ outCool
    /\ UNCHANGED <<inputs, target>>
    /\ state' = "IDLE" /\ code' = "NONE" /\ act' = "Clear"
    /\ SetOutputs("IDLE", FALSE, FALSE)

\* Power loss or watchdog reset: RAM is lost, outputs go to their hardware
\* default (off), the firmware boots to IDLE. The world is unchanged.
Reboot ==
    /\ UNCHANGED <<inputs, target>>
    /\ state' = "IDLE" /\ code' = "NONE" /\ g1prev' = FALSE /\ act' = "Reboot"
    /\ relay' = FALSE /\ g1' = FALSE /\ g2' = FALSE /\ f1' = FALSE /\ f2' = FALSE

Next ==
    \/ Tick
    \/ \E t \in CmdTargets : Start(t) \/ Set(t)
    \/ Stop
    \/ Clear
    \/ Reboot

Spec == Init /\ [][Next]_vars

-----------------------------------------------------------------------------
(* Invariants. Numbers refer to docs/06-safety.md.                          *)

TypeOK ==
    /\ state \in States /\ code \in Codes
    /\ {relay, g1, g2, f1, f2, g1prev} \subseteq BOOLEAN

\* (2) No heater gate on without the airflow the interlock requires.
InvAirflow == (g1 => Air1) /\ (g2 => Air2)

\* (3)(4) No heater gate on with bad sensors or a hot outlet.
InvSensorsOutlet == (g1 \/ g2) => (sensOk /\ ~outHot)

\* Stagger: H2 never on without H1.
InvStagger == g2 => g1

\* (9) Gates need K1; K1 is closed only while heating.
InvGatesNeedRelay == (g1 \/ g2) => relay
InvRelayOnlyHeating == relay => state \in {"CHECK", "RUN"}

\* Even with a shorted MOSFET, heat flows only while heating, with airflow.
InvHeatOnlyWhenHeating == Energized => state \in {"CHECK", "RUN"}
InvHeatHasAirflow == Energized => Air1

\* (5) Fans run in COOLDOWN, and in FAULT while the outlet is hot.
InvCooldownFans == (state = "COOLDOWN" \/ (state = "FAULT" /\ ~outCool)) => (f1 /\ f2)

\* (8) Mode limits.
InvTarget == state \in Heating => ValidTarget(target)

\* A latched fault always carries its code.
InvFaultCode == (state = "FAULT") <=> (code # "NONE")

-----------------------------------------------------------------------------
(* Action properties.                                                       *)

\* (6) A fault is latched: FAULT is left only by CLEAR (cause gone) or a reboot.
PropLatched ==
    [][state = "FAULT" /\ state' # "FAULT" =>
         (act' = "Clear" /\ ~CausePresent(code)) \/ act' = "Reboot"]_vars

\* (7) No auto-resume: heating starts only from an explicit START.
PropNoAutoResume ==
    [][state \notin Heating /\ state' \in Heating => act' = "Start"]_vars

\* (1) Outputs are off after a reboot.
PropBootOff == [][act' = "Reboot" => (state' = "IDLE" /\ AllOff')]_vars

\* (9) K1 closes only with both gates low (stuck-heater check window), and
\* when it opens the gates are already low.
PropRelayClosesFirst == [][~relay /\ relay' => ~g1' /\ ~g2']_vars
PropRelayOpensAfterGates == [][relay /\ ~relay' => ~g1' /\ ~g2']_vars

\* F_HEATER_STUCK: uncommanded heat (K1 closed, gates low, heater still on)
\* lasts at most one tick; the next tick opens K1.
PropStuckCut ==
    [][relay /\ ~g1 /\ ~g2 /\ shorted /\ act' = "Tick" => ~relay']_vars

\* (5) The fans stop only when the outlet is cool (except power loss).
PropFansStopCool ==
    [][(f1 \/ f2) /\ ~f1' /\ ~f2' /\ act' # "Reboot" => outCool']_vars

=============================================================================
