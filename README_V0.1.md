# RIGEL Ground Station V0.1 – MAVLink UDP Telemetry

## Scope
V0.1 focuses on receiving live MAVLink telemetry from the RIGEL Drone Simulator over UDP and displaying it in the existing GCS UI.

## Communication model
MAVLink is the application protocol. UDP/Serial are communication transports/channels carrying MAVLink.

### Simulator
- MAVLink over UDP
- Simulator TX target: `127.0.0.1:14550`
- GCS listener: `udpin:0.0.0.0:14550`

### GCS flow
`UDP -> MAVLink -> TelemetryParser -> TelemetryData -> UI`

## Telemetry currently parsed
- HEARTBEAT: SYSID, COMPID, armed state, flight mode
- GLOBAL_POSITION_INT: latitude, longitude, altitude, relative altitude, speed, climb, heading
- ATTITUDE: roll, pitch, yaw
- VFR_HUD: speed, heading, climb, altitude
- GPS_RAW_INT: fix type, satellites, HDOP, VDOP
- SYS_STATUS: battery voltage/current/remaining
- BATTERY_STATUS: battery voltage/current/remaining
- RADIO_STATUS: RSSI/noise

## V0.1 behavior
- UDP and Serial connection controls are available.
- UDP is the default transport in the Telemetry Link panel.
- Demo flight loop is disabled. Live MAVLink telemetry is the single source of truth.
- Vehicle commands are not transmitted yet; command buttons are logged as telemetry-only placeholders.
- UI callbacks are marshalled to Tkinter's main thread using `root.after()`.

## Run
```powershell
pip install -r requirements.txt
python main.py
```

Then in **TELEMETRY LINK**:
1. Select `UDP`.
2. Keep bind address `0.0.0.0`.
3. Keep port `14550`.
4. Start the RIGEL Drone Simulator.
5. Click `CONNECT`.

Expected result: heartbeat/telemetry messages update the HUD, map UAV marker, system telemetry and GCS status.
