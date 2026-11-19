# Dreame FP10 Air Purifier

Home Assistant custom integration for the Dreame FP10 Pet Air Purifier (`dreame.airp.u2513`).

## Features

- Cloud authentication via Dreame Smart Life with automatic region detection and re-authentication support
- Main `fan` entity with power control, real 1-10 speed percentage mapping, and purification preset modes
- Dedicated `number` (fan speed 1-10), `select` (purification mode), and `switch` (child lock) entities
- 13 air-quality, filter-life, and device-status sensors with native Home Assistant device classes, state classes, and units
- Redacted diagnostics download and configurable polling interval (15-300 s)

## Setup

1. Copy `custom_components/dreame_airpurifier` into your Home Assistant `config/custom_components/` directory.
2. Restart Home Assistant.
3. Add **Dreame FP10 Air Purifier** from **Settings -> Devices & Services -> Add Integration**.
4. Sign in with your Dreame Smart Life account and pick your FP10 air purifier.
