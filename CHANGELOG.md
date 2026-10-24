# Changelog

## [5.1.0] - 2026-10-24
### Feat: Demand Aggregation Strategies, Zone Weights, Authoritative Hardware Sync & OpenTherm Weather Curve (Phases 8, 9 & 10)
- **Demand Aggregation Strategies & Zone Weights (Phase 10)**:
  - Added configurable plant-wide heat demand aggregation formulas in `DemandAggregator`:
    - `MAX`: Highest-demand zone dictates boiler power (classic behavior).
    - `WEIGHTED_AVERAGE`: Demand weighted by room emitter wattage, thermal volume, or configured zone weight.
    - `SUM_CAPPED`: Cumulative sum of zone demands with a 100% saturation ceiling.
  - Dynamic frontend selector entity (`select.multizone_thermostat_demand_aggregation_strategy`) allowing real-time switching between aggregation strategies without restarting Home Assistant.
  - Per-zone weight multiplier (`CONF_ZONE_WEIGHT`, default `1.0`, range `0.1`–`10.0`) configurable in zone options flow and schemas.
- **Authoritative Hardware Climate Sync (Phase 9)**:
  - Opt-in authoritative mode source (`authoritative_mode_source`) for zones driven by physical wall thermostats (e.g., Vimar, Bticino).
  - Physical `OFF` switch actions propagate cleanly to the virtual climate zone without being misinterpreted as knob setpoint adjustments to 5 °C.
  - Preserves virtual zone preset target across physical `OFF` transitions.
  - Filters out transient `idle` or network reconnection states to prevent state flutter.
- **Guided Dual-Path OpenTherm Setup & Dynamic Weather Compensation (Phases 8 & 10)**:
  - Guided dual-path OpenTherm setup in config and options flow: Climate-based OpenTherm Gateway vs Number/Sensor-based OpenTherm Gateway.
  - Dynamic Feed-Forward Weather Curve ($T_{\text{ext}} \rightarrow T_{\text{flow}}$) in OpenTherm backend: continuously modulates boiler flow temperature setpoint according to outdoor temperature readings and building thermal retention time, proactively matching heat loss before indoor temperatures drop.
- **Air-in-Radiator Anomaly Detection (Phase 10)**:
  - Automated supervision (`ANOMALY_AIR_IN_RADIATOR`) identifying valves opened at 100% with abnormally slow heat-up rates compared to historic baseline, alerting users to trapped air or restricted flow.
- **Full Localization Synchronization**:
  - Added translations for all Phase 8, 9, and 10 config options, strategy selectors, and anomaly messages across English (`en`), Italian (`it`), German (`de`), Spanish (`es`), French (`fr`), and Russian (`ru`).
- **Comprehensive Test Coverage**:
  - Added full test coverage in `tests/test_phase8_9_10_features.py` and `tests/test_config_flow_phase9_10.py` (169 total tests passing).

## [5.0.5] - 2026-10-24
### Release: Critical Sensor Fail-Safe, Battery Sensor Anomaly Fixes, Anti-Seize & Unload Safety, Translations Sync
- **Critical Sensor Fail-Safe & Plant Orchestrator Hardening**:
  - Zero-demand fail-safe: if a zone's primary temperature sensor drops out (becomes `unavailable`, `unknown`, or exceeds timeout) without an active TRV fallback, the zone demand is immediately forced to 0% and virtual thermostat sets `current_temperature = None`, preventing heating runaway on stale readings.
  - Guarded `PlantOrchestrator.async_tick` against unhandled inner exceptions to ensure continuous evaluation loops without freezing plant state.
  - Plant orchestrator enforces 0% zone demand whenever critical sensor faults are diagnosed.
- **Anti-Seize & Cycle Protection Safety**:
  - If the boiler is in a `HOLD_ON` minimum cycle lock when summer anti-seize routine completes, forces `async_emergency_off` immediately to prevent runaway heating cycles.
  - Full exception handling in `AntiSeizeManager.async_execute()` guarantees all zone valves and boiler demand are restored to previous states (`HVAC_MODE_OFF` / 0% demand) even if an unexpected communication fault occurs.
  - Persists `last_active_wall_time` to storage and restores monotonic idle offset across Home Assistant restarts, avoiding spurious anti-seize triggers after reboot.
- **Integration Unload Safety & Clean Storage Flushes**:
  - `async_unload_entry` now triggers `boiler_backend.async_emergency_off()` immediately upon unload/reload, preventing orphaned boiler activation during integration updates.
  - Explicitly flushes window, preset, and coordinator settings stores to disk prior to platform teardown.
  - Guaranteed cleanup of all active event listeners on config entry unload.
- **Diagnostics & Battery Sensor Anomaly Filtering**:
  - Relaxed staleness checks for sleeping zigbee/z-wave battery temperature sensors (< 24h) unless the zone is actively calling for heat.
  - Eliminated false-positive `STALE_SENSOR` warnings for rooms with steady temperatures when no heating is being requested.
  - Properly handles OpenTherm fault sensors reporting `unknown` state to avoid false `fault_active` warnings.
- **Full Localization Synchronization**:
  - Synchronized translation keys across English (`en`), Italian (`it`), German (`de`), Spanish (`es`), French (`fr`), and Russian (`ru`).

## [5.0.1] - 2026-10-13
### Feat: Proportional & 0-10V Valve Control and Collapsible UI Sections
- **Proportional & 0-10V Valve Support**:
  - Direct opening percentage (0–100%) and analog voltage (0.0–10.0 V) control for underfloor heating, fancoil valves, or direct-pin TRVs.
  - Automatic entity domain detection (`valve` with `set_valve_position` and `number` / `input_number` with `set_value`).
  - Integrated command deadband (>=0.5% or 0.05V) to protect Zigbee/Z-Wave/Wi-Fi buses from high-frequency micro-jitter.
  - Automatic safety shutdown: valves are immediately forced to 0% / 0V when the zone is set to `OFF` or placed in `bypass` (e.g. open window).
- **Collapsible UI Sections in Config & Options Flow**:
  - Reorganized zone configuration into intuitive collapsible accordion sections:
    - *Thermostatic Radiator Valves (TRV)*
    - *Proportional & 0-10V Valves*
    - *Relay Actuators (PWM)*
    - *Protections & Advanced Settings*
- **Test Suite Expansion**:
  - Added full test coverage in `tests/test_proportional_valves.py` (all 109 integration tests passing).

## [5.0.0] - 2026-10-11
### Major Release: Modular Architecture, End-to-End Hardening & Comprehensive Testing Suite
- **Monolith Decomposition & Modular Architecture**:
  - coordinator.py refactored into Single Responsibility Principle services (zone_controller, demand_aggregator, zone_manager, calendar_manager, 
outine_manager).
  - Specialized subsystem packages: oiler/ (Relay & OpenTherm backends, Plant Orchestrator), safety/ (Watchdog, Frost Manager, Anti-Seize), plant_diagnostics/, storage/, and config_flow/.
- **OpenTherm CH Switch Support**: Dedicated opentherm_ch_switch configuration option to cleanly toggle central heating on/off without disturbing flow temperature setpoints; safe fallback to entity min attribute or zero.
- **Immediate TRV Fallback**: Sensor offline/unavailable transitions trigger immediate onboard TRV averaging (_update_current_temp), preventing heating dropouts during network transitions.
- **Bumpless Post-DHW Recovery**: Automatic detection of DHW falling edge resets PID samples, timestamps, and integrals (clear_samples()), eliminating thermal surges after prolonged DHW usage.
- **Boiler Command Confirmation & Hardware Watchdog**: Diagnostics track confirmed hardware switch state; unconfirmed commands raise BOILER_COMMAND_TIMEOUT after 60s and retry intelligently if demand persists.
- **Safe Valve Delay & State Re-Verification**: Re-evaluates Master switch, DHW status, and heat demand after valve opening delays before igniting the boiler.
- **Storage Isolation & Clean Lifecycle**: Storage isolated per entry ID ({DOMAIN}_{entry_id}_*) with automatic migration from legacy structures; clean setup, options reload, and unload without dangling callbacks.
- **Monotonic Clock Discipline**: In-process durations in PWM, PID, thermal model, and diagnostics use 	ime.monotonic(), making regulation immune to NTP time jumps and DST transitions.
- **Comprehensive Quality Assurance**:
  - Full automated suite of 105 integration unit tests running under -W error.
  - Deterministic Virtual Testing Lab (multizone_lab) covering priority scenarios P1–P10, full 7-day minute-by-minute simulation, and invariant validation.

## [4.7.3] - 2026-10-07
### ?? Bug Fixes & Code Cleanup
- **Physical Sync Switch**: Improved entity identity handling to prevent orphaned sync switches when renaming zones.
- **Anti-Frost Emergency**: Fixed race condition during frost-protection forced heating by appropriately awaiting mode switch before injecting targets.
- **TRV Command Robustness**: Fixed issue where failed API calls to unresponsive TRVs would permanently wedge the sync status as pending.
- **Calendar Parsing**: Replaced unsafe datetime operations, enforcing localized timezone conversion for naive events retrieved via Home Assistant calendar integrations.
- **Codebase Audit**: Evaluated and removed legacy bug markers confirming the implementation logic is structurally intact.

## [4.7.2] - 2026-10-06
### 🛠️ Bug Fixes
- **Frontend Strategy Registration**: Fixed a JavaScript syntax escape error in card translations that prevented custom element and dashboard strategy registration.

## [4.7.1] - 2026-10-06
### 🌍 Internationalization
- **New Languages Added**: Full support for French, German, and Spanish added for the UI Cards and Config Flow.

## [4.7.0] - 2026-10-06
### 🚀 Major Features & Boiler Supervision
- **Sensor Timeout Watchdog & TRV Fallback**: Added configurable per-zone timeout watchdog (`sensor_timeout_min`, default 60 min). If an external wireless temperature sensor disconnects or runs out of battery, the zone automatically falls back to the TRV's internal temperature probe, keeping the room heated and recording a diagnostic event. Automatically resumes normal precision control when the external sensor recovers.
- **OpenTherm Advanced Telemetry & Fault Code Bus**: Automatically discovers and monitors OpenTherm gateway registers: Water Pressure (Bar, alert < 0.8 Bar), Flow and Return Temperatures (°C), Burner Flame ignition status, Burner Modulation percentage (0-100%), and OEM Boiler Error Codes.
- **DHW Priority PID Freeze**: Automatically detects Domestic Hot Water (DHW) production on combination boilers. Freezes zone PID demands and pauses heating calls while showers/taps are running, preventing false integral windup overshoot and spurious anomaly alerts.
- **Universal Battery Surveillance**: Multi-step battery resolver automatically locates battery charge percentages for all wireless room thermometers and radiator valves across Zigbee2MQTT, ZHA, and Tuya/Avatto.
- **Battery Health in Cards & Thermostats**: Live battery percentage is exposed directly in zone thermostat `extra_state_attributes` (`battery_level`) and visually integrated into the `ZoneEnergyCard` with color-coded health icons.

## [4.6.0] - 2026-10-05
### 🚀 Features
- **OpenTherm Modulating Dual-Drive**: Complete dual-drive architecture supporting both classic ON/OFF relay boilers (PWM duty cycles) and modulating OpenTherm gateways. Linearly maps house Heat Demand % (0-100%) to boiler water flow temperature (35°C - 75°C).
- **Setup Flow Wizard for OpenTherm**: Dedicated configuration steps to select OpenTherm gateway entities and set minimum/maximum water temperature limits without YAML.

## [4.5.0] - 2026-10-01
### 🚀 Features
- **Central Plant Health Monitoring**: Real-time tracking of burner ignition cycles per hour (<5 c/h optimal, >5 c/h wear warning) and cumulative 24h runtime hours.
- **Mechanical Anomaly Engine**: Automatic surveillance detecting stuck closed valves (heat called >45m with falling temperature) and ghost heating leakage (closed valve with rising temperature).
- **Passive Heat Intake (Apporto Passivo)**: Dedicated toggle per zone (`allow_passive_heat`) for open lofts and unvalved fan coils to suppress false ghost-heating alerts.
- **European Building Energy Metrics**: Real-time calculation of room theoretical energy class (A4 through G), thermal retention time (hours to drop 1.0°C), and radiator power sizing evaluation.
- **Interactive Lovelace Cards**: Central Plant Health card, Zone Energy Efficiency card, and automated diagnostics dashboard strategy view.

## [4.4.0] - 2026-09-25
### 🛠️ Diagnostics & Reliability
- **Home Assistant Native Diagnostics**: Downloadable device diagnostic dumps directly from Home Assistant settings.
- **Event Trace Ring Buffer**: Rolling history buffer recording state changes, TRV syncs, and boiler triggers for fail-safe debugging.

## [4.3.0] - 2026-09-15
### 🚀 Safety & TRV Hardware Sync
- **Anti-Frost Protection Safety Override**: Dedicated switch (`switch.multizone_thermostat_anti_frost_protection`) and threshold control (`number.frost_protection_temp`). Forces emergency heating at 100% demand when room temperature drops below frost threshold, ignoring open window and master off blocks.
- **Bidirectional TRV Hardware Sync**: Dynamic switches allowing physical setpoint and mode adjustments made on the TRV knob to reflect back into the virtual thermostat without echo loops.
- **Calendar Parsing Engine**: Enhanced parser supporting multi-command events, individual zone overrides, and persistent preset updates via the `SET` keyword.

## [3.1.0] - 2026-07-28
### 🚀 Features
- **Weather Compensation (Feed-Forward)**: Added dynamic adjustment of heating demand based on outdoor temperature sensor. This allows the system to proactively adjust boiler PWM cycles when it gets colder outside, preventing the house from losing temperature before the PID reacts. Configurable natively from the integration's Options Flow via a dedicated `Number` entity (Weather Curve).
## [3.0.1] - 2026-07-26
### 🛠️ Improvements
- **UI Config Flow**: Upgraded all dropdown menus in the configuration and options flow to use the native Home Assistant `EntitySelector`. This introduces a search bar, entity icons, and area grouping for much easier device selection (resolving community feedback).

## [3.0.0] - 2026-07-25
### 🚀 Major Features & Full Rewrite
- **Dynamic Autotuning (Hysteresis → PID)**: Starts in Hysteresis mode to learn the room's thermal behavior, then seamlessly switches to a highly precise PID algorithm for zero-swing temperature control.
- **PWM Engine**: Converts PID output percentage into mathematically perfect proportional ON/OFF cycles.
- **Ironclad Hardware Protection (Hard Locks)**: Strict enforcement of min_cycle_on and min_cycle_off directly on the boiler switch state changes, completely eliminating short-cycling risks.
- **Summer Anti-Seize**: Prevents mechanical seizing of valves and pumps during long summer inactivity (e.g. opens valves periodically after 7 days without triggering the boiler).
- **AutoNight / Sleep Mode**: Automatic scheduler integrated directly with Geofencing.
- **Global Presets Memory**: The system now dynamically memorizes the state (temperature & bypass) of every single room per preset (Comfort, Eco, Sleep, Away) without any YAML automation.
- **Primary vs Secondary Zones**: Secondary zones (like bathrooms or closets) can passively open their valves to steal heat, but can no longer trigger the boiler on their own.

### 🛠️ Refactoring & Optimizations
- **100% Async Event-Driven**: Polling loops have been eliminated. The coordinator only awakens upon real state changes, dramatically reducing CPU footprint.
- **Pylint & Flake8 Perfect Score**: Codebase fully audited and modernized, achieving 10.00/10 PEP8 compliance.
