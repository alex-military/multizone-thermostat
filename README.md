# Multizone Thermostat — Home Assistant Custom Integration

A custom integration for Home Assistant that provides **multi-zone heating management** with **centralized boiler control**. No YAML scripting or manual automations required — everything is configured through the HA UI.

## Features

- 🖥️ **UI Config Flow** — Select your boiler relay and climate entities directly from the HA interface
- 🔘 **Master Switch** — One switch to enable/disable the entire heating system
- 🏠 **Per-Zone Switches** — Individual switches for each room/zone, persistent across restarts
- 🔥 **Automatic Boiler Control** — Boiler turns ON when any zone is heating, OFF when all zones are idle
- 🌡️ **TRV Preset Sync** — Optional per-zone preset synchronization for physical TRV valves
- ⚙️ **Options Flow** — Add/remove zones and change settings after installation

## Installation

### Via HACS (recommended)
1. Add this repository as a custom repository in HACS
2. Install "Multizone Thermostat"
3. Restart Home Assistant

### Manual
1. Copy the `custom_components/multizone_thermostat` folder to your HA `custom_components` directory
2. Restart Home Assistant

## Configuration

1. Go to **Settings → Devices & Services → Add Integration**
2. Search for **"Multizone Thermostat"**
3. Follow the setup wizard:
   - **Step 1**: Select your boiler switch/relay entity
   - **Step 2**: Add heating zones (climate entity + zone name)
   - **Step 3**: Confirm and finish

## Entities Created

| Entity | Description |
|--------|-------------|
| `switch.multizone_master` | Master on/off for the entire heating system |
| `switch.multizone_[zone_name]` | Per-zone on/off switch (one per configured zone) |

## How It Works

```
Master Switch ON
    └── Zone Switch ON  → climate.set_hvac_mode(heat)
    └── Zone Switch OFF → climate.set_hvac_mode(off)

Master Switch OFF
    └── ALL zones → climate.set_hvac_mode(off)
    └── Boiler   → switch.turn_off()

Any zone hvac_action = heating → Boiler ON
All zones hvac_action = idle/off → Boiler OFF
```

## Options (Post-Installation)

Go to **Settings → Devices & Services → Multizone Thermostat → Configure** to:
- Change the boiler switch
- Add a new zone
- Remove an existing zone
- Enable/disable TRV preset sync per zone

## TRV Preset Sync

When enabled for a zone, the integration automatically syncs the TRV preset mode:
- HVAC mode `heat` → preset `manual`
- HVAC mode `off` → preset `off`

Only enable this for zones with physical TRV valves that support preset modes.

## Requirements

- Home Assistant 2023.x or newer
- At least one `climate` entity (thermostat/TRV)
- At least one `switch` entity (boiler relay)

## Future Roadmap

- [ ] Diagnostic sensors (zones heating count, boiler demand)
- [ ] Lovelace card for zone control
- [ ] ESPHome panel integration support
