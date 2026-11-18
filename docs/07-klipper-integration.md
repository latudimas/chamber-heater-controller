# 07 – Klipper Integration

**Principle:** Klipper only sends commands. The controller owns PID, staging,
interlocks and safety. If Klipper, Moonraker or the host crashes, the controller
keeps running its current job and its own timer, and stays safe.

## Host

The printer host is a Creality Nebula Pad (rooted). It needs:
- `gcode_shell_command` (Klipper extra, often installed by community helper scripts), **or**
- a Moonraker-side integration.

## Transport options

| Option | How | Pros / cons |
|---|---|---|
| HTTP (recommended) | the shell script runs `curl` against the ESP32 | simple; works over Wi-Fi; no cable |
| USB serial | the shell script writes to `/dev/ttyUSB0` | no Wi-Fi dependency; needs a cable and port permissions |
| MQTT | Moonraker or a script publishes to `heater/<id>/cmd` | good if you already run a broker |

## Example: shell script

`/usr/data/printer_data/scripts/chamber.sh` (the path depends on the host):

```sh
#!/bin/sh
# usage: chamber.sh START mode=heater target=45
HOST="http://chamber-heater.local"
curl -s -m 3 -X POST --data "$*" "$HOST/api/cmd"
```

## Example: Klipper macros

```ini
[gcode_shell_command chamber]
command: sh /usr/data/printer_data/scripts/chamber.sh
timeout: 5.
verbose: False

[gcode_macro CHAMBER_HEAT]
description: Start chamber heating
gcode:
  {% set temp = params.TEMP|default(45)|int %}
  {% set heaters = params.HEATERS|default(2)|int %}
  RUN_SHELL_COMMAND CMD=chamber PARAMS="START mode=heater target={temp} heaters={heaters} fans=2"

[gcode_macro CHAMBER_OFF]
description: Stop chamber heating (controller handles cooldown)
gcode:
  RUN_SHELL_COMMAND CMD=chamber PARAMS="STOP"

[gcode_macro CHAMBER_VENT]
gcode:
  RUN_SHELL_COMMAND CMD=chamber PARAMS="START mode=vent duration={params.MIN|default(10)|int}"
```

Use in the slicer's start G-code: `CHAMBER_HEAT TEMP=45`, then heat-soak. In the end G-code: `CHAMBER_OFF`, optionally followed by `CHAMBER_VENT`.

## Showing chamber temperature in Mainsail

Two options:
1. **MQTT + Moonraker `[sensor]`**: Moonraker subscribes to `heater/<id>/status` and shows the temperature and RH.
2. **Polling script**: keep it read-only. Klipper never needs to act on this data.

## Waiting for the chamber before printing (optional)

Klipper can't natively wait on an external HTTP value. Options:
- a fixed heat-soak `G4` delay in the start G-code (simplest), or
- a shell script that polls `/api/status` until `temp >= target - 1` (with a timeout), called before the print starts.

## Notes

- Creality firmware updates may overwrite `printer.cfg`. Keep these macros in a separate included file and back it up.
- Klipper's own `heater_generic` / `verify_heater` are **not** used for this heater. Don't configure the heater in Klipper.
