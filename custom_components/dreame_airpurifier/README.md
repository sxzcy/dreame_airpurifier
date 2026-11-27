# Dreame FP10 Air Purifier

Home Assistant custom integration (`cloud_push`) for the Dreame FP10 Pet Air Purifier (`dreame.airp.u2513`).

## Features

- Cloud authentication via Dreame Smart Life with automatic region detection, `refresh_token` renewal, and re-authentication flow
- Real-time Dreame Cloud MQTT push (`aiomqtt` over TLS) with automatic HTTP fallback polling (300 s connected / 15–300 s disconnected)
- Automatic dual-firmware adaptation (`1.9.3_1072+` and legacy `1.8.x` fallback) with firmware version exposed on the device registry
- Main `fan` entity with power control, real 1–10 speed percentage mapping, and purification preset modes
- Dedicated controls: fan speed & auto-off timer (`number`), purification mode / ambient light brightness / color temperature (`select`), child lock / ambient breathing / key sound (`switch`), self-cleaning & filter reset (`button`)
- 17 sensors (PM2.5, PM10, TVOC, AQ, air quality level, display value, current speed, temperature, humidity, self-cleaning status, HEPA & hair collector life/days, operating status, error code, Wi-Fi RSSI) + cloud push connectivity `binary_sensor`
- Redacted diagnostics download and zero-drift upgrade from v1.0.0

## Setup

1. Copy `custom_components/dreame_airpurifier` into your Home Assistant `config/custom_components/` directory.
2. Restart Home Assistant.
3. Add **Dreame FP10 Air Purifier** from **Settings -> Devices & Services -> Add Integration**.
4. Sign in with your Dreame Smart Life account and pick your FP10 air purifier.
