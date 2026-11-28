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

### 4. Why does the TRV show a different temperature, or why do offsets drift with Matter/Zigbee binding?
TRVs attached directly to hot radiators suffer from local radiant heat bias, and TRVs natively bound to external sensors must not receive competing offset writes.
* Assign your eye-level wall thermometer as the room's **Primary Temperature Sensor** (`temp_sensor`).
* Under **Thermostatic Radiator Valves (TRV)**, configure `trv_calibration_mode` (`"auto"` default, `"offset"`, `"external_temperature"`, or `"disabled"`):
  * In `"auto"`, the integration auto-detects external temperature inputs (matching keywords such as `external_temperature_input`, `external_temp`, `remote_temp`, `external_measured_room_sensor`, `room_sensor_temp`, `external_sensor`, or wide `[-10..50]` bounds); otherwise it uses offset mode.
  * In `"offset"`, local calibration writes are protected by a `0.25 °C` deadband, `180 s` minimum cooldown, `300 s` anti-ratchet settle window, external manual reset detection, and **`offset_stalled`** protection (pausing writes after 2 unresponsive attempts).
  * In `"external_temperature"` (e.g. Sonoff TRVZB, Aqara, Tuya/Zigbee2MQTT TRVs with `number.*external_temperature_input`), it writes the room sensor temperature directly in °C (rounded to step, clamped to min/max) with a `1200 s` (20 min) anti-offline heartbeat keep-alive and a `60 s` jitter rate-limit on `<= 0.1 °C` deltas.
  * In **`"disabled"`** *(recommended for TRVs using **native Matter or Zigbee binding** to room sensors, such as Eve Thermo + IKEA Timmerflotte)*: disables all offset writes and external temperature heartbeats while still allowing **Demand-Driven Valve (`demand_driven`)** Bounded Overdrive to open/close the TRVs.
* Optionally map each TRV `climate.*` entity to its `select.*` sensor-source entity via `trv_sensor_selects`: the TRV switches to the external/remote sensor when active (excluding `"offline"` options like `remote_source_offline`) and reverts cleanly to the internal/local sensor if `safety_fallback_active` triggers.

---

### 5. How long does the Autotuner take to transition from Hysteresis to PID?
* The autotuner requires **2 to 3 stable heating cycles** (warming with a defined slope followed by natural cooling decay).
* In standard radiator systems, transition typically occurs within **24–48 hours** of normal use. Track progress via `sensor.multizone_brain_[room]_autotuning`.

---

### 6. Why does my smart TRV close too early before the room reaches target? (Demand-Driven Mode)
Many smart TRVs use an aggressive internal proportional loop that pinches the valve prematurely as the radiator warms up.
* Set `trv_control_mode` to `"demand_driven"` (vs `"standard"` default) and tune `trv_open_boost` (default `+1.5 °C`, range `0.0–5.0 °C`) and `trv_close_offset` (default `1.0 °C`, range `0.0–5.0 °C`).
* The zone uses PID demand hysteresis (`>= 5.0%` opens, `<= 0.0%` closes), `60 s` anti-chatter debounce, a `10 s` evaluation tick, and an idle no-chatter guard.
* Open targets use **Smart Bounded Overdrive** (`min(trv_max, room_temp + trv_open_boost, zone_target + trv_open_boost)`, never blasting 30 °C); close targets use `max(trv_min, min(zone_target, room_temp - trv_close_offset))`.
* Compatible with `physical_sync` relative deltas, and automatically reverts to `"standard"` mode if `safety_fallback_active` triggers (stale/unavailable room sensor).

---

### 7. What are `HOLD_TRV_CLOSED` and the `trv_not_opening` anomaly?
* **`HOLD_TRV_CLOSED` (Plant Hydraulic Guard)**: `HOLD_TRV_CLOSED` automatically holds heat generator ignition up to **120 s max** while demanding zone TRVs report closed—checking valve position attributes (`position`, `valve_position`, `pi_heating_demand`, `heating_demand` > 10%) and `hvac_action` fallback (`"heating"` vs `"idle"`/`"off"`), followed by the optional motorized `valve_delay` (`number.master_control_valve_delay`) if `> 0 s`. Applies to **Relay Boiler**, **OpenTherm cold-start only** (never kills an already-running burner), and **Central Heat Pump in HEAT mode**.
* **`trv_not_opening` (*"TRV valve not opening despite active zone heating demand"*)**: A **non-blocking** diagnostic alert raised when zone heating demand `> 20%` and the central generator is active (`boiler_on`) for `> 5` minutes while all zone TRVs still report closed/`idle`, allowing the plant to keep serving other zones.

---

### 8. How do I configure Normally Open (NO) relays or reverse-acting 0–10V valves?
* Under **Configure → Edit a zone → [Room] → Relay Actuators (PWM)**, enable **`invert_switch`**: PWM active demand sends `switch.turn_off` (de-energizing to open an NO electrothermal actuator), while idle/`OFF` sends `switch.turn_on` (energizing to close).
* Under **Proportional & 0-10V Valves**, enable **`invert_valve`**: demand is inverted as `effective_pct = 100.0 - target_pct` on both `0–100%` and `0.0–10.0 V` scales.

---

### 9. Why does PID demand stay at 100% very close to setpoint?
This usually happens if `Ki` was inflated by an anomalous fast-start autotuning cycle before upgrading, causing the integral (`I`) term to wind up and dominate even at small errors (`+0.1 °C`).
* Inspect `sensor.multizone_brain_[room]_demand` directly (now exposing live `p_term`, `i_term`, `d_term`, `integral_accumulator`, `error`, `raw_output`, and `clamped_output` attributes ready for ApexCharts plotting) or download Home Assistant JSON diagnostics (`pid_state`).
* Since `v6.0.24` / `v6.0.26` / `v6.1.0-beta.21` (adding comfort-tuned **SIMC** FOPDT derivation with `Ti >= 900 s` / `Ki <= 0.15`, trapezoidal integration with `0.03 °C` deadband, dynamic zero-offset Smart Stop, and the weekly overshoot guardrail with automatic rollback), existing gains stored in `.storage` are preserved automatically: press **`Reset Autotuner`** on that zone (or seed a balanced **`Baseline Auto EMA`** from the Zone Energy Card) to clear skewed legacy gains.

---

### 10. Why did room heat loss / Energy Class look too high, and how does it work without window sensors?
Brief drafts, open windows, or `0.1 °C` wireless sensor quantization jitter used to contaminate natural cool-down EMA estimates. Starting with **`v6.0.26` / `v6.1.0-beta.21`**:
* Open-window periods (both internal window manager and configured `window_sensor`) are automatically excluded from thermal learning and autotuner ramps.
* Even **without window sensors**, `ThermalObserver` requires quiet cooling windows (`>= 30 min`, `>= 0.25 °C` drop outside post-shutdown thermal inertia), checks **OLS linearity (`R² >= 0.65`)**, detects **fast drafts (`> 2.0 °C/h`)**, verifies **10-minute wall thermal rebound** (`40-minute` lockout on detected drafts), applies asymmetric outlier rejection + a 35th-percentile rolling estimator, and uses weather-invariant Newton **`k_loss`** (`1/h`) for Energy Class.
* On startup after updating, previously corrupted/out-of-range stored cooling/heating rates automatically reset and self-heal cleanly.

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
| Boiler cycles on/off too frequently | Short-cycle timers set too low or legacy PWM window | Update to `v6.0.26+` (enforces single-pulse-per-cycle PWM, `95%` continuous-ON threshold, and phase-locked adaptive period `max(900s, 2*(min_on+min_off))` = 20 min default) and keep `min_cycle_on`/`min_cycle_off` at 5–7 minutes. |
| "Failed to load Lovelace resource" | Browser cache holding outdated bundle | Hard refresh your browser via `Ctrl + F5` (or `Cmd + Shift + R`) or clear Home Assistant Companion app cache. |
| "Stuck Closed Valve" notification | Room demands `>= 99%` heat for > 75 min with `< 0.2 °C` rise | Check TRV battery, verify valve pin is not seized with limescale, and ensure manifold circulators are spinning. |
| `offset_stalled` in diagnostics / Matter TRV offset drift | TRV uses native Matter/Zigbee external sensor binding or ignores offset writes | Reset TRV calibration entity to `0` and set zone `trv_calibration_mode` to **`disabled`** (keeps `demand_driven` overdrive active). |
| `HOLD_TRV_CLOSED` delays generator start | Demanding zone TRVs still report closed (`<= 10%` or `idle`/`off`) | `HOLD_TRV_CLOSED` holds start up to 120 s max until TRVs open, followed by `valve_delay` if > 0 s; verify TRV responsiveness and `trv_control_mode`. |
| `trv_not_opening` diagnostic alert | Zone demand > 20% & `boiler_on` > 5 min while all zone TRVs remain closed/`idle` | Non-blocking alert: check TRV batteries, Zigbee/Thread link, valve pin, or `trv_sensor_selects` / calibration entities. |
| OpenTherm pressure below 0.8 Bar | Low water pressure in heating loop | Use the boiler filling loop valve to repressurize the system to 1.2–1.5 Bar. |
