# Creating a Virtual Thermostat

If you don't have a pre-existing `climate` entity (e.g., you have a standalone temperature sensor and a relay/switch controlling a fancoil, radiator valve, or underfloor heating), you can create a **Virtual Thermostat** directly from the wizard without writing any YAML:

## During Initial Setup
1. In the "Choose zone type" step of the wizard, select **"Create virtual thermostat"**
2. Fill in:
   - **Zone Name**: A friendly name for the zone (e.g., "Camera", "Studio")
   - **Temperature Sensor**: The `sensor` entity that reads the room temperature (must have `device_class: temperature`)
   - **Heater Switch**: The `switch` entity that controls the heater/relay in that zone
   - **Target Temperature**: Initial target temperature (default: 20°C)
   - **Tolerance**: Hysteresis in °C (default: 0.5°C) — the heater turns ON when temperature drops below `target - tolerance`, and turns OFF when it rises above `target + tolerance`
   - **Window Sensor** _(optional)_: A `binary_sensor` to auto-bypass the zone when a window is open
3. The integration will automatically create a `climate` entity and register it as a zone.

## After Installation
Virtual thermostats can also be created **after installation** from the Options menu:
1. Go to **Settings → Devices & Services → Multizone Thermostat**
2. Click **Configure**
3. Select **"Create a new virtual thermostat"**

## Virtual Thermostat Logic
The virtual thermostat operates using a simple ON/OFF logic with hysteresis:
- `current_temp < target - tolerance` → heater switch ON
- `current_temp > target + tolerance` → heater switch OFF
- Reports `hvac_action` = `heating` or `idle` to the Multizone coordinator.
