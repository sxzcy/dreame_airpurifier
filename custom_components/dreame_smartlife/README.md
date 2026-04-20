# Dreame Air Purifier FP10

Home Assistant custom integration for the Dreame Air Purifier FP10.

Implemented:

- cloud login with user-provided account and password
- automatic region detection, or manual region selection
- device list selection during setup
- OTC info polling
- property polling through `dreame-user-iot/iotstatus/props`
- raw command transport through `dreame-iot-com-<host>/device/sendCommand`
- configurable fan, sensor, switch, select, and number mappings

## Quick start

1. Copy `custom_components/dreame_smartlife` into your Home Assistant config directory.
2. Restart Home Assistant.
3. Add the `Dreame Air Purifier FP10` integration from the UI.
4. Sign in with your own Dreame Smart Life account.
5. Leave the region on `Auto detect` unless you already know the correct region.
6. Select your device.

This integration is intended for the FP10 model family, currently mapped as `dreame.airp.u2513`. If your device still needs manual tuning, adjust the mapping JSON fields in the integration options.

## Mapping examples

`sensor_mappings`

```json
{
  "pm25": {
    "key": "4.2",
    "name": "PM2.5",
    "unit": "ug/m3",
    "icon": "mdi:blur"
  },
  "temperature": {
    "key": "4.8",
    "name": "Temperature",
    "unit": "°C",
    "device_class": "temperature"
  }
}
```

`switch_mappings`

```json
{
  "anion": {
    "key": "4.20",
    "name": "Anion",
    "on": 1,
    "off": 0,
    "icon": "mdi:atom"
  }
}
```

`select_mappings`

```json
{
  "mode": {
    "key": "4.3",
    "name": "Mode",
    "options": {
      "auto": 0,
      "sleep": 1,
      "strong": 2
    }
  }
}
```

`fan_speed_map`

```json
{
  "sleep": 1,
  "auto": 2,
  "strong": 3
}
```
