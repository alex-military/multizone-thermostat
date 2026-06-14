# Changelog

All notable changes to this project will be documented in this file.

## [2.1.0] - 2026-06-14

### Added
- **Categorization of Entities:** Organized the device page in Home Assistant. Security parameters and bypass switches are now neatly grouped under the "Configuration" section, keeping the "Controls" section clean for the Master Switch and Virtual Thermostats.
- **Official Versioning:** The integration now uses proper semantic versioning (starting from v2.1.0) and maintains a changelog.

### Fixed
- **CRITICAL - Options Flow Saving:** Fixed a critical bug where changes made via the Options menu (e.g., modifying zones, adding/removing virtual thermostats) were not being properly saved to `entry.data` and would be silently lost upon a system restart.
- **High - Valve Delay Logic:** Fixed a bug where the boiler would turn on unconditionally after the valve delay expired, even if the zone had already reached its target temperature and stopped demanding heat.
- **High - Boiler Lock Reset:** Fixed an issue where changing the security parameters (Min Cycle ON/OFF) from the UI would not clear existing timer locks, causing the new settings to wait until the next cycle to take effect.
- **Moderate - Zone Edit Form:** Fixed a bug where returning to the edit zone form could accidentally modify the wrong zone due to stale state in the config flow.
- **Translations:** Fixed an issue with the Master Switch translation key not working properly. Added the missing entity translation section to `strings.json` and removed hardcoded English names.
- **Code Duplication:** Unified the logic that generates Virtual Thermostat entity IDs (`make_vt_entity_id`) into a single shared function to prevent future bugs.
- **Clean Up:** Removed unused variables, dead code, and old imports from multiple files (`const.py`, `coordinator.py`, `config_flow.py`, `__init__.py`).
