# Plant Safeguards & Hydraulic Diagnostics

<span class="badge-stable">STABLE</span>

Multizone Thermostat acts as a supervisory controller for your hydronic plant, protecting boilers from short-cycling wear and catching mechanical faults before they cause damage or waste energy.

---

## 1. Mechanical Fault Surveillance

The diagnostic engine continuously inspects room temperature trajectories against historical learning:

```mermaid
flowchart TD
    Diagnosi["Continuous Hydraulic Supervisor"]
    Diagnosi --> CheckBlocco{"Heat Requested >45 min<br>but Temperature Falls?"}
    CheckBlocco -->|Yes| AllarmeBlocco["⚠️ Stuck Closed Valve Detected"]
    
    Diagnosi --> CheckTrafilamento{"Valve Sealed at 0%<br>but Temperature Rises?"}
    CheckTrafilamento -->|Yes| AllarmeTrafilamento["⚠️ Ghost Heating / Valve Leakage"]
    
    Diagnosi --> CheckAria{"Valve Open at 100%<br>but Heating Rate << Historical?"}
    CheckAria -->|Yes| AllarmeAria["⚠️ Trapped Air in Radiator (Bleeding Needed)"]
    
    Diagnosi --> CheckSonda{"No Sensor Updates<br>for > 240 Minutes?"}
    CheckSonda -->|Yes| AllarmeSonda["⚠️ Wireless Sensor Watchdog Timeout<br>-> Fallback to TRV Internal Sensor"]
    
    Diagnosi --> CheckTrvOpen{"Zone Demand > 20% & Generator ON > 5 min<br>but All Zone TRVs Closed/Idle?"}
    CheckTrvOpen -->|Yes| AllarmeTrvOpen["⚠️ trv_not_opening<br>(Non-Blocking Alert)"]
```

### The 5 Core Mechanical Anomalies

| Anomaly | Trigger Criteria | Automated System Response |
|---|---|---|
| **Stuck Closed Valve** | Room demands heat for > 45 minutes with boiler running, but room temperature continues to drop. | Red alert on Lovelace card, persistent notification in Home Assistant, and activation of `binary_sensor.heating_zones_[room]_anomaly`. |
| **TRV Valve Not Opening (`trv_not_opening`)** | *"TRV valve not opening despite active zone heating demand"*: zone heating demand > 20% and central boiler/heat generator is active (`boiler_on`) for > 5 minutes while all zone TRVs still report closed/`idle`. | **Non-blocking diagnostic alert**: flags the affected zone without halting the central plant so other zones continue to be served. |
| **Ghost Heating (Leakage)** | Room temperature rises significantly while the room valve/relay is commanded to 0%. | Warns of damaged valve seats, poor actuator seating, or faulty bypass valves. |
| **Trapped Radiator Air** | Valve is open 100% but warm-up rate is less than 30% of historical rate $R$. | Flags radiator as needing manual air bleeding to restore heat transfer. |
| **Sensor Watchdog Timeout** | Wireless sensor battery dies or loses signal for > 240 minutes (`CONF_ZONE_SENSOR_TIMEOUT`). | **Instant graceful fallback (`safety_fallback_active`)**: automatically regulates using the TRV's internal sensor, reverts `trv_sensor_selects` to the internal/local sensor, and reverts `demand_driven` TRVs to `standard` mode. |

---

## 2. Mechanical Plant Protections

### 1. Boiler & Heat Pump Anti-Short-Cycle Protection
Frequent starts reduce efficiency and wear out burners or compressors:
* **Gas Boiler**: `number.master_control_min_cycle_on` / `min_cycle_off` (default: **5 minutes**).
* **Central Heat Pump**: Dedicated `number.master_control_hp_min_cycle_on` / `hp_min_cycle_off` (independent from boiler cycles).
* **Plant Diagnostics**: Cycle frequency (`cycles/hour`) and 24h runtime tracking work for both gas boilers and heat-pump-only plants.

### 2. Motorized Valve Opening Delay & Hydraulic TRV Guard (`number.master_control_valve_delay`)
Wax thermal actuators require 90 to 180 seconds to stroke open.
Setting a delay (e.g. **120 seconds**) ensures the boiler/heat pump and circulator start only when valves are fully open, eliminating water hammer and pipe overpressure.
* **Unified TRV Valve-Readiness Guard (`HOLD_TRV_CLOSED`)**: `HOLD_TRV_CLOSED` automatically holds heat generator ignition up to **120 s max** while demanding zone TRVs still report closed—inspecting valve position attributes (`position`, `valve_position`, `pi_heating_demand`, `heating_demand` > 10%) as well as `hvac_action` fallback (`"heating"` vs `"idle"`/`"off"`), followed by the optional motorized `valve_delay` (`number.master_control_valve_delay`) if `> 0 s`. Applies to **Relay Boiler**, **OpenTherm cold-start only** (never kills an already-running burner), and **Central Heat Pump in HEAT mode**.

### 3. Summer Anti-Seize Exercise
During warm months, valves and circulators sit dormant, risking calcification and seizing:
* If idle for > 15 days (`number.master_control_anti_seize_idle_days`), the integration strokes all valves open for 2 minutes (`number.master_control_anti_seize_duration`), closing them immediately after. Protected by a concurrency guard and compatible with both boiler and heat pump backends (`anti_seize_boiler`).

### 4. Emergency Anti-Frost Protection & Persistent Recovery
If any room falls below `number.master_control_anti_frost_temperature` (default: **7.0 °C**):
* The system forces 100% emergency heating at a configurable `number.master_control_frost_flow_temp`, overriding window cutouts, master off states, or away presets to protect pipes from freezing.
* **Persistent Recovery**: Pre-frost targets (`pre_frost_targets`) are persisted across Home Assistant restarts.
* **L5 Frost Emergency Fallback**: If both room sensor and TRVs become unavailable while outdoor temperature (weather or numeric `sensor.*`) drops below **2.0 °C**, conservative frost protection engages automatically.

### 5. Underfloor 40.0 °C Ceiling, Dew-Point & Window Safety
* **Underfloor Hard Thermal Ceiling**: Enforces a strict **40.0 °C** max water temperature on unmixed underfloor radiant systems, even in mixed radiator/underfloor setups.
* **Indoor Dew-Point Anti-Condensation**: Keeps chilled cooling water at least **+2.0 °C** above the worst-case indoor dew point across zones actively demanding cooling.
* **Window Open Cutout**: Opening a window immediately clears zone demand and cancels any local split manual override.

### 6. TRV Demand-Driven Bounded Overdrive & Safety Reversion
* **Bounded Overdrive (`trv_control_mode: demand_driven`)**: Prevents smart TRVs from pinching/closing early via PID demand hysteresis (`>= 5.0%` opens, `<= 0.0%` closes), `60 s` anti-chatter debounce, `10 s` evaluation tick, and an idle no-chatter guard. Open target is strictly bounded to `min(trv_max, room_temp + trv_open_boost, zone_target + trv_open_boost)` (never blasts a fixed 30 °C), and close target to `max(trv_min, min(zone_target, room_temp - trv_close_offset))`.
* **Automatic Safety Reversion (`safety_fallback_active`)**: If the primary room sensor is lost or stale, `demand_driven` TRVs automatically revert to `standard` mode (direct zone setpoint) and `trv_sensor_selects` switches back to the TRV's internal/local sensor so each valve regulates autonomously.

---

## 3. Advanced OpenTherm Bus Telemetry

* **Water Pressure (Bar)**: Continuous pressure monitoring with low pressure warning under 0.8 Bar.
* **Flow & Return Temperatures (°C)**: Real-time $\Delta T = (T_{\text{flow}} - T_{\text{return}})$ to monitor condensing performance.
* **Flame Modulation (%)**: Real-time percentage burner firing rate.
* **Boiler OEM Fault Codes**: Direct capture and display of manufacturer trouble codes.
* **Domestic Hot Water Priority (DHW Freeze)**: When hot water taps open (including EMS-ESP multi-device charging detection and custom DHW entities), the system **freezes PID error integration**, preventing false error accumulation while the boiler diverts output to domestic water.
