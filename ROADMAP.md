# 🗺️ Multizone Thermostat — Public Project Roadmap

Welcome to the **Multizone Thermostat** project roadmap! This document outlines our completed milestones, current engineering focus, and upcoming functional enhancements.

---

## 🌟 Vision & Architecture

Multizone Thermostat transforms Home Assistant into an **autonomous, self-learning thermal orchestrator**. Following our **v5.0.0 Modular Architecture refactoring**, every subsystem (Plant Orchestrator, Zone Controllers, Safety Watchdogs, Diagnostics, and Storage) operates under the Single Responsibility Principle, backed by automated integration test suites.

---

## ✅ Completed Milestones

### Core Releases (v3.0 → v4.7)
- [x] **Dynamic Autotuning (Hysteresis → Silent PID)**: Automatically learns room thermal dispersion and transitions to self-tuned PID regulation.
- [x] **PWM Regulation & Hardware Hard Locks**: Proportional ON/OFF duty cycles with strict `min_cycle_on` and `min_cycle_off` physical boiler switch protection.
- [x] **Hierarchical Zone Modes**: Primary (boiler-igniting), Secondary (passive heat stealing), and Bypass zones.
- [x] **Valve Opening Delay & Safety Verification**: Protects circulator pumps from pumping against closed thermoelectric actuators; re-verifies safety conditions before ignition.
- [x] **Summer Anti-Seize & Anti-Frost Overrides**: Periodic valve exercising during idle months and emergency 100% frost heating.
- [x] **Dual Boiler Drive (Relay PWM & OpenTherm Modulating)**: Linear mapping of house Heat Demand (0–100%) to water flow temperature ($35^\circ\text{C} - 75^\circ\text{C}$).
- [x] **Advanced Boiler Supervision & Diagnostics**: Telemetry tracking (cycles/hour, 24h runtime), anomaly engine (stuck valves, ghost heating), and European energy class estimation.
- [x] **Sensor Timeout Watchdog & TRV Fallback**: Immediate fallback to TRV internal sensors when wireless sensors disconnect or deplete batteries.

### Modular Core & Refactored Foundation (v5.0.0 → v5.0.3)
- [x] **Modular SRP Architecture (v5.0.0)**: Decomposed monolithic coordinator into modular services (`zone_controller`, `demand_aggregator`, `zone_manager`, `calendar_manager`, `routine_manager`).
- [x] **Post-DHW Bumpless Recovery (v5.0.0)**: Automatic zero-demand suppression and bumpless PID integral reset upon domestic hot water tap closure.
- [x] **Monotonic Clock Discipline (v5.0.0)**: Internal timings migrated to `time.monotonic()` for total immunity against NTP jumps and DST changes.
- [x] **Proportional & 0–10V Valve Actuation (v5.0.1)**: Direct opening percentage (0–100%) and analog voltage (0.0–10.0 V) control for underfloor heating, fancoil valves, or direct-pin TRVs (`valve` & `number` entities) with command anti-jitter deadband.
- [x] **Collapsible Config Flow UI (v5.0.1)**: Accordion sections for clean setup of TRVs, Proportional valves, Relays, and Protections.
- [x] **Preset Manual Memory & Cooldown Hardening (v5.0.2)**: Dynamic retention of manual setpoint modifications and relay protection.
- [x] **Config Flow Robustness (v5.0.3)**: Fully resilient entity discovery and validation on Home Assistant's `EntityRegistry`.

---

## 🚀 Active Roadmap & Upcoming Features

### Phase 6 — Advanced Weekly Scheduling & Multi-Profile Engine
*Derived from community collaboration in [GitHub Issue #5](https://github.com/alex-military/multizone-thermostat/issues/5).*

- [ ] **Independent Per-Zone Presets per Time Block**:
  - Ability to assign distinct presets to different rooms within the same scheduled block (e.g., 18:00–22:00: *Living Room at Comfort*, *Bedrooms at Eco*, *Bathroom at Comfort 19:00–20:00*).
  - Schedule blocks reference existing zone preset temperature matrices, avoiding duplicated temperature settings.
- [ ] **Deterministic Baseline Preset for Schedule Gaps**:
  - Configurable default preset (e.g., `Eco`) automatically applied to all zones outside scheduled time blocks, eliminating unpredictable fallback states.
- [ ] **Multi-Profile Management (*Standard*, *Holiday/Festivo*, *Smart Working*)**:
  - Define and save distinct weekly schedules.
  - Edit and prepare inactive profiles in the background without disturbing the currently active schedule.
- [ ] **Temporary Profile Activation with Auto-Reversion**:
  - Activate an alternate profile with an expiration timestamp (e.g., activate *Holiday* until Sunday 23:59).
  - Automatically reverts to *Standard* upon expiry, with persistent storage across Home Assistant restarts.
- [ ] **Predictive Smart Start Schedule Synchronization**:
  - Dedicated scheduler-to-engine interface passing upcoming target temperatures and scheduled arrival times.
  - Multizone's thermal model calculates early staggered heating start times per room, guaranteeing target comfort at the exact scheduled minute.
- [ ] **Smart Override vs. Deliberate OFF Rules**:
  - *Temperature adjustments (knob or card)*: Temporary override active until the next scheduled block transition or manual reset.
  - *Explicit Zone OFF*: High-priority manual shutdown preserved across schedule transitions without unwanted re-activation.

---

### Phase 7 — Next-Gen Scheduler UI & "Smart Return" Arrival Planner
*Visual and mobile user experience enhancements.*

- [ ] **Dedicated Mobile-Optimized Weekly Timeline Card**:
  - Whole-house synchronized 24-hour matrix view displaying thermal schedules for all zones on a single screen.
  - Fast *"Preset Brush"* interaction to apply presets with one tap, minimizing nested dialogs.
  - Visual badges for zones running temporary manual overrides with one-click *"Resume Schedule"* reset.
- [ ] **"Smart Return" (Pianifica Rientro) Arrival Planner**:
  - Quick action card/panel to set an estimated arrival time (e.g., *"Arriving home at 18:30"*).
  - Automatic calculation of staggered zone ignition times based on individual room thermal inertia (slower rooms start earlier, fast rooms later) to reach target comfort simultaneously at arrival while minimizing fuel consumption.

---

### Phase 8 — Dual OpenTherm Drive Distinction
*Derived from community feedback in [Community Post #22](https://community.home-assistant.io/t/multizone-thermostat-v3-smart-pid-pwm-geofencing-100-ui-no-yaml/1018712/22).*

- [ ] **Guided Dual-Path Setup in Config Flow**:
  - **Option 1 — Climate-Based OpenTherm Gateway**:
    - Direct selection of an existing boiler `climate` entity.
    - Sends target modulation via `climate.set_temperature` and mode via `climate.set_hvac_mode`.
    - Automatically extracts telemetry (flame active, DHW production status, modulation %, return temp) directly from climate entity attributes, requiring zero manual auxiliary sensor configuration.
  - **Option 2 — Standard Decoupled OpenTherm Gateway**:
    - Tailored for DIY/ESPHome gateways exposing discrete entities (`number` flow setpoint, `switch` central heating enable, and independent diagnostic sensors).

---

### Phase 9 — Authoritative Hardware Climate Sync
*Derived from physical wall thermostat integration in [GitHub Issue #2](https://github.com/alex-military/multizone-thermostat/issues/2).*

- [ ] **Per-Zone Authoritative Mode Source (Opt-in)**:
  - For zones driven by a primary physical wall thermostat (e.g., Vimar, Bticino), allow the physical device to act as an authoritative mode source.
  - Physical OFF actions propagate directly to the virtual zone without being misinterpreted as knob adjustments to 5 °C.
  - Retains the virtual preset target across OFF transitions and filters out transient `idle` or network reconnection states.

---

### Phase 10 — Advanced Plant Regulation & Efficiency
- [ ] **Configurable Demand Aggregator Strategies**:
  - Choice of plant-wide heat demand aggregation formulas:
    - `MAX`: Highest-demand zone dictates boiler power.
    - `WEIGHTED_AVERAGE`: Demand weighted by radiator emitter wattage or room volume.
    - `SUM_CAPPED`: Cumulative sum of zone demands with a 100% saturation ceiling.
- [ ] **Dynamic Feed-Forward Weather Curve ($T_{\text{ext}} \rightarrow T_{\text{flow}}$)**:
  - Continuously adapts boiler flow temperature based on real outdoor temperature and building thermal retention time.
- [ ] **Air-in-Radiator Anomaly Detection (`ANOMALY_AIR_IN_RADIATOR`)**:
  - Automated supervision identifying valves opened at 100% with abnormally slow heat-up rates compared to historic baseline, indicating trapped air or restricted flow.

---

### Phase 11 — Long-Term Research & System Evolutions
- [ ] **Hydraulic Zone Clustering**: Grouping zones by physical manifolds/floors to maintain minimum loop flow and prevent overpressure.
- [ ] **Hybrid Multi-Generator Management**: Coordinated staging between primary Heat Pumps and auxiliary/peak Gas Boilers.
- [ ] **Dynamic Energy Tariff & Solar Preheating**: Integration with hourly electricity pricing (Nord Pool, PUN) and PV solar excess to dynamically pre-heat zones during low-cost or high-production windows.

---

## 💬 Community Feedback & Contributions

We actively encourage feedback, real-world hardware test reports, and feature proposals!
- Submit bug reports and architectural discussions on [GitHub Issues](https://github.com/alex-military/multizone-thermostat/issues).
- Join the project discussion thread on the [Home Assistant Community Forum](https://community.home-assistant.io/t/multizone-thermostat-v3-smart-pid-pwm-geofencing-100-ui-no-yaml/1018712).
