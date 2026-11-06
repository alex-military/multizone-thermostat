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

### Plant Regulation, Climate Sync & Dual OpenTherm (v5.1.0 → v5.1.2)
- [x] **Guided Dual-Path Setup in Config Flow (Phase 8)**: Option 1 for climate-based OpenTherm gateways (auto attribute telemetry extraction); Option 2 for decoupled discrete gateways (`number` + `switch`).
- [x] **Authoritative Hardware Climate Sync (Phase 9)**: Opt-in authoritative mode source for physical wall thermostats (e.g., Vimar, Bticino) propagating manual OFF states without setpoint corruption.
- [x] **Configurable Demand Aggregator Strategies & Zone Weights (Phase 10)**: Selection of plant formulas (`MAX`, `WEIGHTED_AVERAGE`, `SUM_CAPPED`) with live entity selector and zone weight multipliers.
- [x] **Dynamic Feed-Forward Weather Curve ($T_{\text{ext}} \rightarrow T_{\text{flow}}$) (Phase 10)**: Continuously adapts boiler flow temperature based on real outdoor temperature and building thermal retention time.
- [x] **Air-in-Radiator Anomaly Detection (`ANOMALY_AIR_IN_RADIATOR`) (Phase 10)**: Automated supervision identifying valves opened at 100% with abnormally slow heat-up rates.
- [x] **Startup Availability Guards & Command De-Duplication (v5.1.2)**: Entity readiness verification during late Zigbee2MQTT startup and suppression of duplicate 10s OFF MQTT spam.

### Advanced Weekly Scheduling & Next-Gen Lovelace UI (v6.0.0 → v6.0.2)
- [x] **Independent Per-Zone Presets per Time Block (Phase 6)**: Ability to assign distinct presets to different rooms within the same scheduled block without duplicated temperature matrices.
- [x] **Deterministic Baseline Preset for Schedule Gaps (Phase 6)**: Configurable default preset (e.g. `Eco`) automatically applied outside scheduled time blocks.
- [x] **Multi-Profile Management (Phase 6)**: Native storage-backed engine supporting *Standard*, *Holiday/Festivo*, *Smart Working*, and custom profiles with background editing.
- [x] **Temporary Profile Activation with Auto-Reversion (Phase 6)**: Activate alternate profiles with expiration timestamps and automated fallback to baseline.
- [x] **Predictive Smart Start Schedule Synchronization (Phase 6)**: 12h thermal horizon calculating staggered pre-heating times per room to reach target comfort at the exact scheduled minute.
- [x] **Smart Override vs. Explicit OFF Rules (Phase 6)**: Temporary overrides expire at next slot transition, while intentional manual OFF (`HVACMode.OFF`) is permanently protected from unwanted re-activation.
- [x] **Dedicated Mobile-Optimized Weekly Timeline Card (Phase 7)**: Synchronized 24h matrix view, quick duration pills, batch multi-day slot modal, and full multi-language localization.
- [x] **"Smart Return" (Pianifica Rientro) Arrival Planner & Auto-Wake (Phase 7)**: Arrival planner with thermal radar and automatic plant wake-up from master OFF.
- [x] **UI Polish, Single-Column Wrapping & Strategy View Compatibility (v6.0.1 / v6.0.2 - PR #8)**: Responsive layout stacking for top header cards, robust navigation fallback, and seamless support for Lovelace strategy views.

---

## 🚀 Active Roadmap & Upcoming Features

### Phase 11 — Hybrid Multi-Generator, Room Split Climate & Solar Self-Consumption (Next Target)
*Complete architectural design and technical specifications available in [`PHASE_11_SPECIFICATION.md`](PHASE_11_SPECIFICATION.md).*

- [ ] **Dual-Level Heating Architecture (Central Hydronic + Room Air Splits)**:
  - **Central Hydronic Drive**: Coordinated bivalent staging between primary Heat Pump (PDC) and auxiliary/peak Gas Boiler on the shared water loop.
  - **Room Direct Expansion Actuators**: Integration of room-level AC/heat pump split units (`climate.*` entities) as secondary/auxiliary climate actuators.
- [ ] **Configurable Split Operational Roles & Runtime Master Controls**:
  - Per-zone role configuration: *Heating Only*, *Cooling Only*, or *Both (Heat & Cool)*.
  - Global Dashboard Master Switches for immediate runtime control without re-configuration:
    - `switch.multizone_master_allow_split_heating` (Toggle Split Heating ON/OFF globally).
    - `switch.multizone_master_allow_split_cooling` (Toggle Split Cooling ON/OFF globally).
  - Per-zone toggle options for 3 independent runtime behaviors: *Solar Priority*, *Thermal Shock / Quick Heat Boost*, and *Real Room Sensor Injection* (bypassing the ceiling probe).
- [ ] **Optional Solar Self-Consumption & Inverter Clipping Engine**:
  - Fully optional and bypassable for installations without solar; provides a runtime source selector (`select.multizone_heat_source_priority`: *Gas Priority*, *Electric Priority*, *Gas Only*, *Electric Only*).
  - Multiple solar detection methods:
    - **Inverter Clipping / Curtailment detection**: Native evaluation ($SOC \ge 98\%$, battery `idle`, $|P_{PV} - P_{Load}| < 80\text{ W}$, $P_{PV} > 300\text{ W}$) or custom template sensor state (`Limitazione`).
    - **Grid Export**: Configurable export power threshold ($P_{export} > X\text{ W}$).
    - **Predictive Optimizer**: Signal input from EMHASS or Predbat for pre-scheduled solar thermal charging.
  - Two operational modes during solar surplus:
    - *Global Hybrid Mode*: Gas boiler fires only for rooms without splits, while rooms with splits bypass radiators and heat for free via splits.
    - *Solar Self-Consumption Only (Zero Gas)*: Gas boiler strictly locked OFF; only splits engage to dump surplus energy into thermal mass.
  - Battery Protection Guard & Anti-Chatter: Minimum continuous run time (10–15 min) and automatic shutoff if battery discharges past threshold.
- [ ] **Foundations for Summer Cooling Mode**:
  - Seasonal Master Mode Switch (`HVACMode.HEAT` / `HVACMode.COOL`).
  - Active cooling management for AC splits and dew-point controlled hydronic cooling manifolds.

---

### Phase 12 — Long-Term Research & System Evolutions
- [ ] **Hydraulic Zone Clustering**: Grouping zones by physical manifolds/floors to maintain minimum loop flow and prevent overpressure on circuits without differential bypass.
- [ ] **Dynamic Hourly Energy Tariffs (Nord Pool / PUN)**: Automated thermal storage shifting based on variable day-ahead electricity prices.

---

## 💬 Community Feedback & Contributions

We actively encourage feedback, real-world hardware test reports, and feature proposals!
- Submit bug reports and architectural discussions on [GitHub Issues](https://github.com/alex-military/multizone-thermostat/issues).
- Join the project discussion thread on the [Home Assistant Community Forum](https://community.home-assistant.io/t/multizone-thermostat-v3-smart-pid-pwm-geofencing-100-ui-no-yaml/1018712).
