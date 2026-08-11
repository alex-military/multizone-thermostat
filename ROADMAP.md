# Multizone Thermostat - Roadmap & Evolution

The project is structured in phases to evolve from a simple aggregator to a full-fledged smart climate manager.

## ✅ Completed Phases (Core V3)

### PHASE 1 — System Safety
- [x] **Anti-short Cycle (`min_cycle_duration`)**: Prevents rapid boiler oscillations with minimum ON/OFF times.
- [x] **Boiler Ignition Delay (`valve_opening_delay`)**: Delay in seconds to allow thermoelectric valves to open fully before firing the boiler.
- [x] **Open Window Detection (`window_sensor`)**: Automatic zone bypass upon window opening, with state restoration.

### PHASE 2 — Architectural Evolution & UI
- [x] **Virtual Thermostats via UI**: Automatic creation of `climate` entities from a temperature sensor and a simple switch without YAML.
- [x] **Global Presets (Dynamic Memory)**: Presets (Manual / Eco / Comfort / Sleep / Away) act as "global scenes" with dynamic memory per individual zone.
- [x] **Geofencing Zero-Code**: Automatic preset switching based on home occupancy (Away/Comfort).
- [x] **Room Priority Selector**: Multi-state selector (Primary / Secondary / Bypassed) for advanced heat distribution.

### PHASE 3 — Quality of Life & Dashboards
- [x] **Summer Valve Protection (Anti-seize)**: Cyclical safety activation during summer to prevent mechanical seizing of valves and circulator pumps.
- [x] **Auto-Generated Lovelace Dashboard**: Instantly generate a full Home Assistant dashboard page with premium climate-dedicated graphics.
- [x] **Custom Lovelace Cards**: Dedicated Master Status, Dial, Button, and Global Preset cards.

### PHASE 4 — Advanced Energy Optimization (PID & Weather)
- [x] **Self-Learning PID Auto-Tuning**: Advanced self-learning PID algorithm that studies the thermal inertia of the house and regulates proportional modulation (PWM) autonomously.
- [x] **PWM Engine**: Translates proportional demand into precise ON/OFF cycles.
- [x] **Global Heat Demand (%)**: Calculates the exact percentage of load required by the house.
- [x] **Weather Compensation Curve**: Dynamic adjustment of the heating demand based on an outdoor temperature sensor (Feed-Forward algorithm).
- [x] **Adaptive Climate Curve (SAT Logic)**: The system learns the thermal dispersion of your rooms and automatically shapes the weather compensation multiplier for perfect efficiency.
- [x] **External Sensor TRV Override (Calibration/Fake Target)**: The PID engine intercepts TRVs attached to hot radiators and injects mathematical offsets based on a pure external room sensor, forcing perfect ambient temperatures.

### PHASE 5 — Advanced Algorithms & Analytics
- [x] **Advanced Room Thermal Model (SAT)**: Learning of thermal capacity and dispersion, heating/cooling speed, and thermal inertia.
- [x] **Future Temperature Prediction (SAT) & Smart Start**: Predictive early start based on thermal data and calendar events.
- [x] **Global Calendar Integration**: Scheduling of global presets and dynamic overrides natively tied into the Home Assistant Local Calendar.

---

## 🚀 Future Roadmap & Next Priorities

### PHASE 6 — Advanced AI & Optimization
- [ ] **Adaptive Climate Curve**: Self-learning and continuous adaptation of the weather compensation curve based on history.
- [ ] **Full OpenTherm Support**: Modulation of flame flow temperature, diagnostic reading, and DHW management, mapping the Demand % (0-100%).
- [ ] **Advanced Diagnostics & Anomaly Analysis**: Detection of stuck valves, overshoots, PID cycles, and reporting for each room.


### 🤝 Community Requests & Pull Requests
Features proposed or requested by the community that we plan to implement:
- [x] **Russian Translation (`ru.json`)**: Full Russian localization added natively.
- [ ] **Hybrid Cooling & Summer Management**:
  - **Split AC / Cooling Aggregation**: Allow adding independent AC units via the Config Flow strictly for UI grouping and dashboard integration. They will not be managed by the central PID, but can be controlled via manual overrides or grouped by a "Cooling Master".
  - **Summer/Winter Switch**: Native transition logic between Heating and Cooling seasons (manual switch, scheduled, or linked to HA's season integration).
  - **Dual Seasonal Presets**: Independent sets of Global Presets (Comfort, Eco, etc.) for Winter (Heating targets) and Summer (Cooling targets).

### 📋 Additional Priorities
  - **Intelligent Multi-Sensor Management:** Weighted average and priorities among multiple sensors in a room.
  - **Advanced Dashboards & Statistics:** Graphical display of efficiency, PID, PWM, histories.

### 🔬 Future Research
- [ ] **Hybrid Support (Heating / Cooling)**: Complete rewrite of the configuration engine to simultaneously manage and easily switch between Winter (Heating) and Summer (Cooling) modes, supporting reversible heat pumps.
- [ ] **External AI Integration (Predictive Optimization)**: Dedicated API/Sensors interface allowing external AIs to read historical data and constantly optimize PID parameters, weather compensation curves, and predictive geofencing.


