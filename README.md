# Dreame Smart Life for Home Assistant

Custom integration for Dreame Smart Life devices in Home Assistant.

Users log in from the Home Assistant UI with their own Dreame Smart Life account and password. No account details are hardcoded in the integration.

## Features

- config flow setup from the Home Assistant UI
- cloud login with account and password
- automatic region detection with manual override
- device picker during setup
- property polling and raw command support
- configurable fan, sensor, switch, select, and number entities
- built-in defaults for supported purifier models

## Installation

### HACS

1. Push this repository to GitHub.
2. In HACS, add it as a custom repository with category `Integration`.
3. Install `Dreame Smart Life`.
4. Restart Home Assistant.

### Manual

1. Copy `custom_components/dreame_smartlife` into your Home Assistant configuration directory.
2. Restart Home Assistant.

## Setup

1. Go to `Settings` -> `Devices & Services` -> `Add Integration`.
2. Search for `Dreame Smart Life`.
3. Enter your Dreame Smart Life account and password.
4. Leave region on `Auto detect` unless you already know it.
5. Select the device you want to add.

## Notes

- The integration stores the selected device and the resolved cloud region in the config entry.
- If your model is not fully mapped yet, fill the mapping JSON fields in the integration options.
- This repository already includes `hacs.json` and a `.gitignore` suitable for publishing the integration without accidentally committing APK and other local reverse-engineering artifacts.
