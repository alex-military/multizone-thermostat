# Multizone Thermostat — Home Assistant Custom Integration

[![GitHub Release](https://img.shields.io/github/v/release/alex-military/multizone-thermostat?color=cyan&style=flat-square)](https://github.com/alex-military/multizone-thermostat/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg?style=flat-square)](LICENSE)
[![HACS](https://img.shields.io/badge/HACS-Custom_Integration-orange.svg?style=flat-square)](https://hacs.xyz/)
[![Official Wiki](https://img.shields.io/badge/Official%20Wiki-EN%20%2F%20IT-0ea5e9?style=flat-square&logo=googlechrome&logoColor=white)](https://alex-military.github.io/multizone-thermostat/)
[![Support on Ko-fi](https://img.shields.io/badge/Ko--fi-Support%20Me-FF5E5B?style=flat-square&logo=ko-fi&logoColor=white)](https://ko-fi.com/Z8L52A8URQ)
[![GitHub Sponsors](https://img.shields.io/badge/Sponsor-GitHub-EA4AAA?style=flat-square&logo=GitHub-Sponsors&logoColor=white)](https://github.com/sponsors/alex-military)

A comprehensive, 100% UI-configured custom integration for Home Assistant providing **multi-zone climate control**, **central plant supervision**, **adaptive PID autotuning**, and **building energy diagnostics** — with zero YAML automations required.

<table>
  <tr>
    <td align="center" width="50%">
      <b>🔥 Winter Heating (Gas Boiler &amp; Split Heat)</b><br><br>
      <img src="docs/wiki/images/dashboard_winter.jpg" alt="Winter Heating Dashboard" width="100%">
    </td>
    <td align="center" width="50%">
      <b>❄️ Summer Cooling (Electric Split &amp; Dual-Track)</b><br><br>
      <img src="docs/wiki/images/dashboard_summer.jpg" alt="Summer Cooling Dashboard" width="100%">
    </td>
  </tr>
</table>

---

## ✨ Key Features

### Core Climate & Zone Management
- 🖥️ **100% UI Config & Options Flow**: Guided setup wizard with collapsible sections and per-zone **`0.5°` / `0.1°`** setpoint step precision — no YAML editing required.
- 🔥 **Dual Boiler & Anti-Chattering Drive**: Supports **ON/OFF Relay (PWM)** (single-pulse anti-chattering latch, `95%` continuous-ON threshold, adaptive phase-locked cycle period), **Modulating OpenTherm**, and **Centralized Condo / District Heating**.
- 🧠 **Adaptive SIMC Autotuning & Sensorless Thermal Model**: Starts safely in Hysteresis, passively learns room response via OLS regression to derive **SIMC (Skogestad IMC)** gains with **trapezoidal PID**, dynamic zero-offset Smart Stop, and **weekly overshoot auto-rollback**, plus a sensorless `ThermalObserver` with draft lockout and weather-invariant Newton `k_loss`.
- 🏠 **Hierarchical Zone Modes**: Per-zone `Primary`, `Secondary` (passive heat sharing), and `Bypass` selector directly on Lovelace cards.
- 🎛️ **Broad Actuator Support**: Smart TRVs (`climate.*`, multi-TRV aggregation, physical dial sync, `external_temperature_input` feed, `select.*` sensor-source switching, `Disabled` mode for native Matter/Zigbee binding, offset anti-ratchet protection, and **Demand-Driven** bounded overdrive), **0–100% / 0–10V proportional valves**, and **PWM relay actuators** — all supporting **Normally Open (NO) / inverted output logic** (`invert_switch`, `invert_valve`).
- 📅 **Weekly Scheduling, Geofencing & Smart Return**: Visual 24h schedule matrix, Local Calendar integration, presence-based presets, and predictive pre-heating based on room inertia.

### Hybrid Plant, Cooling & Solar *(v6.1.0-beta)*
- 🔄 **Bivalent Central Plant**: Arbitrates between Gas Boiler and Central Hydronic Heat Pump across **7 priority modes** (`auto`, `hybrid`, `combined`, `electric_only`, `gas_only`, `gas_priority`, `electric_priority`).
- ❄️ **Room Split AC Integration**: Per-zone split units with ceiling sensor bypass (target injection), Quick Heat Boost, and automatic hydronic decoupling.
- ☀️ **Off-Grid & Solar Self-Consumption**: Inverter anti-clipping, battery discharge safeguard, night SoC reserve, and EMHASS / Predbat bridge.
- 🌡️ **Four-Season Dual-Track Engine**: Independent winter/summer preset memories, dual-track PID loops, indoor dew-point anti-condensation, and automatic summer card filtering.

### Safety, Diagnostics & Lovelace UI
- 🛡️ **Plant & Pipe Safeguards**: Anti-short-cycle timers (boiler & heat pump), motorized valve opening delay & **TRV hydraulic valve-readiness guard (`HOLD_TRV_CLOSED`)**, summer anti-seize exercise, persistent anti-frost protection, and window-open cutouts.
- 🚨 **Hydraulic & Energy Diagnostics**: Live per-zone P/I/D telemetry directly on `sensor.<zone>_demand` attributes (`p_term`, `i_term`, `d_term`, `error`, `kp/ki/kd`) and JSON `pid_state`, stuck-valve (`> 75 min`), TRV non-opening (`trv_not_opening`), and ghost-heating detection, wireless sensor watchdog with TRV fallback, OpenTherm telemetry & DHW priority, Newton `k_loss` European Energy Class (`A4`–`G`), and thermal retention metrics.
- 🎨 **Visual Twin Lovelace Cards, Telemetry Studio & Auto-Dashboards**: Custom cards matching Home Assistant native styling, an auto-discovered 2×2 **Charts & Telemetry** subview (`custom:multizone-thermostat-telemetry-card` with zero-dependency SVG charts and **`📋 Copy Support Snapshot`**), and auto-generated dashboard strategies in **6 languages** (`EN`, `IT`, `ES`, `FR`, `DE`, `RU`).

---

## 📚 Official Documentation Wiki & Live Simulator

All detailed guides, configuration references, services, YAML examples, and troubleshooting live in our **Official Bilingual Wiki**:

[![Launch Official Wiki & Simulator](https://img.shields.io/badge/Official%20Wiki%20%26%20Simulator-GitHub%20Pages-0ea5e9?style=for-the-badge&logo=googlechrome&logoColor=white)](https://alex-military.github.io/multizone-thermostat/)

- 📖 **Official Wiki (English)**: [https://alex-military.github.io/multizone-thermostat/](https://alex-military.github.io/multizone-thermostat/)
- 📖 **Wiki Ufficiale (Italiano)**: [https://alex-military.github.io/multizone-thermostat/wiki/index.html#/it/home](https://alex-military.github.io/multizone-thermostat/wiki/index.html#/it/home)
- 🎮 **Interactive Live Simulator**: [https://alex-military.github.io/multizone-thermostat/wiki/simulator.html](https://alex-military.github.io/multizone-thermostat/wiki/simulator.html) (6 languages)
- 🚀 **[Project Roadmap](ROADMAP.md)** &nbsp;|&nbsp; 📋 **[Changelog](CHANGELOG.md)**

---

## 📥 Installation

### Via HACS (Recommended)

[![Open your Home Assistant instance and open HACS.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=alex-military&repository=multizone-thermostat&category=integration)

1. Open **HACS** → **Custom repositories** → add `https://github.com/alex-military/multizone-thermostat` as **Integration**.
2. Search for **"Multizone Thermostat"**, click **Download**, and restart Home Assistant.

### Manual Installation
1. Copy `custom_components/multizone_thermostat` into your Home Assistant `custom_components/` directory.
2. Restart Home Assistant.

---

## Acknowledgments

A special thanks to the creators of [SmartThermostat](https://github.com/ScratMan/HASmartThermostat) and [vindaalex/multizone-thermostat](https://github.com/vindaalex/multizone-thermostat) for inspiring the core PID and autotuning logic.

## Support & Donations

If you find this integration helpful and would like to support its ongoing development, consider buying a coffee!

<p align="left">
  <a href="https://github.com/sponsors/alex-military" target="_blank">
    <img src="https://img.shields.io/badge/Sponsor-GitHub-30363D?style=for-the-badge&logo=GitHub-Sponsors&logoColor=EA4AAA" alt="Sponsor on GitHub" height="38">
  </a>
  &nbsp;&nbsp;
  <a href="https://ko-fi.com/Z8L52A8URQ" target="_blank">
    <img src="https://storage.ko-fi.com/cdn/kofi2.png?v=3" alt="Support on Ko-fi" height="38">
  </a>
</p>

---

## License

This project is licensed under the MIT License.
