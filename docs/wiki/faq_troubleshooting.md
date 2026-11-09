# Troubleshooting & Frequently Asked Questions (FAQ)

A practical guide to troubleshooting common issues, analyzing behavior, and diagnosing your heating plant.

---

## ❓ Frequently Asked Questions

### 1. Why is the Room Split button disabled (grey with padlock)?
<span class="badge-beta">BETA</span>

The central split button is **designed for manual heating when Central Master Heating is OFF**.
* When Master Heating is **ON**, the whole house is managed by the central orchestrator and seasonal algorithms. The button locks to prevent accidental clicks from fighting whole-house climate control.
* When Master Heating is **OFF**, the button becomes interactive: clicking it powers on **only that room's electric split unit** for rapid comfort while leaving the gas boiler completely off.

---

### 2. Why did some room cards disappear in Summer mode?
<span class="badge-beta">BETA</span>

This is controlled by `hide_if_cannot_cool: true`:
* If a room (e.g. hallway, pantry, radiator-only bathroom) lacks cooling capabilities (no split and no reversible radiant floor), the card hides automatically in summer to keep the dashboard clean.
* Switching the seasonal slider back to **Heat 🔥** immediately restores all rooms.
* To always display all rooms year-round, set `hide_if_cannot_cool: false` in the card configuration.

---

### 3. Why did the gas boiler turn back on despite sunny weather?
<span class="badge-beta">BETA</span>

The energy engine includes the **Continuous Battery Discharge Safeguard (`battery_max_discharge_time`)**:
* If cloud cover or high appliance loads (oven, cooktop) pull energy from the household battery (> 150 W discharge) for more than 5 minutes:
* The system **immediately cuts electric heating and fires the gas boiler**, protecting battery capacity for evening and night hours.

---

### 4. Why does the TRV show a different temperature than the room wall sensor?
TRVs attached directly to hot radiators suffer from local radiant heat bias.
* Assign your eye-level wall thermometer as the room's **Primary Temperature Sensor** (`temp_sensor`).
* Under **TRV Calibration**, assign your TRV's offset entity (e.g. `number.trv_calibration_offset` in Zigbee2MQTT/ZHA).
* Multizone Thermostat will dynamically inject offset corrections to keep the room accurate.

---

### 5. How long does the Autotuner take to transition from Hysteresis to PID?
* The autotuner requires **2 to 3 stable heating cycles** (warming with a defined slope followed by natural cooling decay).
* In standard radiator systems, transition typically occurs within **24–48 hours** of normal use. Track progress via `sensor.multizone_brain_[room]_autotuning`.

---

## 🛠️ Diagnostics & Debug Logging

### Enabling Debug Logs
Add this block to your `configuration.yaml` to record detailed decision logs from `PlantOrchestrator`, `EnergyManager`, and PID loops:

```yaml
logger:
  default: warning
  logs:
    custom_components.multizone_thermostat: debug
```

Restart Home Assistant and view logs under **Settings → System → Logs**.

---

### Known Issues & Troubleshooting Table

| Symptom | Probable Cause | Recommended Solution |
|---|---|---|
| Split receives command but does not start | Split entity does not support commanded HVAC mode | Check supported `hvac_modes` under **Developer Tools → States**. Verify `split_role: heat_cool`. |
| Boiler cycles on/off too frequently | Short-cycle timers set too low | Increase `number.master_control_min_cycle_on` and `min_cycle_off` to at least 5–7 minutes. |
| "Failed to load Lovelace resource" | Browser cache holding outdated bundle | Hard refresh your browser via `Ctrl + F5` (or `Cmd + Shift + R`) or clear Home Assistant Companion app cache. |
| "Stuck Closed Valve" notification | Room demands heat for > 45 min but temperature falls | Check TRV battery, verify valve pin is not seized with limescale, and ensure manifold circulators are spinning. |
| OpenTherm pressure below 0.8 Bar | Low water pressure in heating loop | Use the boiler filling loop valve to repressurize the system to 1.2–1.5 Bar. |
