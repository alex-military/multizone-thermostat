# Changelog

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
