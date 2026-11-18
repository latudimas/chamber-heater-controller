# 05 – Command API

One command set, parsed by one module, available on every transport.

## Transports

| Transport | Format | Notes |
|---|---|---|
| USB serial | line-based text, `\n` terminated, 115200 8N1 | Appears as `/dev/ttyUSB*` on the host |
| HTTP | `POST /api/cmd` body = command line; `GET /api/status` | Same text commands; JSON responses |
| MQTT | publish to `heater/<id>/cmd`; status on `heater/<id>/status` (retained) | Optional |
| Local UI | encoder + OLED build the same command internally | |

## Commands

```
START mode=<heater|dry|vent> [target=<°C>] [duration=<min>] [heaters=<1|2>] [fans=<1|2>] [fan=<%>]
START mode=dry preset=<PLA|TPU|PETG|ABS|ASA>
SET   target=<°C> | duration=<min> | duration=+<min>
STOP
STATUS
CLEAR                      # clear a latched fault (only if the cause is gone)
PRESETS                    # list presets
VERSION
```

- Arguments are `key=value`, order-independent, case-insensitive keys.
- Defaults come from the mode profile; preset values can be overridden (`preset=PETG duration=360`).
- Validation happens **before** any output changes. Out-of-range values are rejected, never clamped silently.

## Responses

```
OK
ERR <code> <message>
```

| Code | Meaning |
|---|---|
| `E_BUSY` | already running; use `SET` or `STOP` |
| `E_RANGE` | value outside the mode profile limits |
| `E_INTERLOCK` | heater/fan combination not allowed |
| `E_FAULT` | controller is in `FAULT`; `CLEAR` first |
| `E_ARGS` | unknown or missing argument |
| `E_SENSOR` | required sensor unavailable |

## STATUS

```json
{
  "state": "RUN",
  "mode": "heater",
  "target": 45.0,
  "temp": 44.8,
  "rh": 18.2,
  "outlet": 62.5,
  "heaters": { "h1": 100, "h2": 35 },
  "fans": { "f1": { "pwm": 100, "rpm": 13100 }, "f2": { "pwm": 100, "rpm": 12900 } },
  "remaining_s": 5340,
  "fault": null,
  "uptime_s": 7200
}
```

When faulted: `"state": "FAULT", "fault": { "code": "F_OUTLET_OVERTEMP", "at": 1234 }`.

## Examples

```
START mode=heater target=45 heaters=2 fans=2
START mode=dry preset=PETG
START mode=dry target=50 duration=240 heaters=1 fans=1 fan=60
START mode=vent duration=10
SET duration=+30
STOP
```
