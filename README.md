# Dreame Air Purifier FP10 for Home Assistant

Home Assistant custom integration (`cloud_push`) for the **Dreame FP10 Pet Air Purifier** (`dreame.airp.u2513`).

Users sign in from the Home Assistant UI with their own Dreame Smart Life account and password. No credentials or device identifiers are hardcoded.

## What's New in v2.0.0

- **Real-time Cloud MQTT Push (`cloud_push`)**: Connects directly to the Dreame IoT MQTT broker over TLS (`aiomqtt`) for sub-second `properties_changed` updates, automatically relaxing HTTP polling to 300 s while connected and falling back to your configured scan interval on disconnect.
- **Dual-Firmware Adaptation (`1.9.3_1072` + Legacy `1.8.x` Fallback)**: Automatically detects firmware version (`ver` -> `DeviceInfo.sw_version`) and routes child lock (`6.10` / `2.5`) and key sound (`6.17` / `6.7`) accordingly.
- **Full Official FP10 Controls & Sensors**:
  - **Fan**: Power, 1–10 speed percentage mapping, and purification preset modes (`auto`, `强净化`, `睡眠净化`, `自定义`, `宠物模式`) for HomeKit Bridge compatibility.
  - **Numbers**: Fan speed (1–10), auto-off countdown timer (0–12 h).
  - **Selects**: Purification mode, ambient light brightness (`off` / `dim` / `natural` / `bright`), ambient light color temperature (`2700K` / `4000K` / `5700K`, requires MCU > 62 / `1.9.3_1072+`).
  - **Switches**: Child lock, ambient light breathing mode, key sound.
  - **Buttons**: Start self-cleaning, confirm self-cleaning complete, plus HEPA filter & hair collector reset buttons (disabled by default for safety).
  - **Sensors (17)**: PM2.5, PM10, TVOC, AQ index, air quality level, display value, current speed, temperature, humidity, self-cleaning status, HEPA filter life & remaining days, hair collector life & remaining days, operating status, error code, Wi-Fi signal strength (RSSI).
  - **Binary Sensor**: Cloud MQTT push connectivity diagnostic.
- **Zero-Drift Upgrade from v1.0.0**: Preserves `DOMAIN`, device identifiers, and all 17 existing entity `unique_id`s.

## Installation

### HACS

1. In HACS, add `https://github.com/sxzcy/dreame_airpurifier` as a custom repository with category `Integration`.
2. Install **Dreame FP10 Air Purifier**.
3. Restart Home Assistant.

### Manual

1. Copy `custom_components/dreame_airpurifier` into your Home Assistant `config/custom_components/` directory.
2. Restart Home Assistant.

## Setup

1. Go to **Settings** -> **Devices & Services** -> **Add Integration**.
2. Search for **Dreame FP10 Air Purifier**.
3. Enter your Dreame Smart Life account and password.
4. Leave region on `Auto detect` unless you already know it (`cn`, `eu`, `us`, `ru`, `sg`, `kr`).
5. Select your FP10 device.

## Notes

- Tested with `dreame.airp.u2513` firmware `1.8.30_1055` and `1.9.3_1072` on Home Assistant Core 2026.x.
- Local LAN takeover is not supported by FP10 hardware/firmware because the Wi-Fi module only opens an outbound CA-pinned TLS MQTT connection to the Dreame cloud broker.
