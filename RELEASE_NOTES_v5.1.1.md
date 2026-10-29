# Multizone Thermostat - Release Notes & Communications v5.1.1
**Release Date:** 2026-10-29  
**Version:** 5.1.1  

---

## 1. Release Summary

Version **5.1.1** addresses a critical core issue regarding non-ASCII zone naming and delivers the complete frontend updates for the OpenTherm telemetry card, full multi-language localization (including Russian), and configurable setpoint precision.

### Key Highlights:
- **Core Engine Fix (GitHub Issue #7)**:
  - Fixed a critical bug where zones with non-ASCII characters (e.g. Cyrillic `Спальная`, accented Latin `Café`, `Büro`) never heated.
  - Replaced manual character filtering in `make_zone_entity_id()` with Home Assistant's native `slugify()` from `homeassistant.util`. This ensures that internal entity IDs generated during setup match the exact entity IDs registered in Home Assistant's Entity Registry (e.g., `Спальная` $\rightarrow$ `climate.multizone_thermostat_spalnaia`).
  - Added explicit warning log in `ZoneController.async_update_zone` when an unregistered entity ID is encountered, preventing silent failures.
  - Full test coverage added in `tests/test_issue7_non_ascii_zones.py`.
- **Lovelace Frontend Card Fixes (`multizone-thermostat-card.js` & `multizone-thermostat-card-v24.js`)**:
  - **Supply / Flow Temperature** (`ot_flow_temp`) is now permanently displayed in the OpenTherm telemetry grid alongside return temperature, giving instant visibility into boiler flow temp and condensation $\Delta T$.
  - **Full Multi-Language Localization**: Eliminated all hardcoded Italian strings in the OpenTherm card. Translated all OpenTherm telemetry keys, DHW badges, flame status, and condensation evaluation into **English (`en`)**, **Russian (`ru`)**, **German (`de`)**, **French (`fr`)**, **Spanish (`es`)**, and **Italian (`it`)**.
  - **Dynamic Setpoint Step Precision**: Supports `0.1°C` / `0.5°C` increment adjustments.
- **Backward Compatibility**: Fully backward compatible with existing configurations; ASCII zone names remain completely unchanged.

---

## 2. Updated Files

1. `custom_components/multizone_thermostat/manifest.json`:
   - Updated `"version"`: `"5.1.1"`.
2. `CHANGELOG.md`:
   - Added entry for `[5.1.1] - 2026-10-29`.
3. `custom_components/multizone_thermostat/const.py`:
   - Integrated `homeassistant.util.slugify` in `make_zone_entity_id()`.
4. `custom_components/multizone_thermostat/zone_controller.py`:
   - Added warning logging for unregistered zone entities in `async_update_zone()`.
5. `custom_components/multizone_thermostat/www/multizone-thermostat-card.js` & `multizone-thermostat-card-v24.js`:
   - Integrated supply temperature display and localized OpenTherm dictionaries (`ru`, `en`, `it`, `de`, `fr`, `es`).
6. `tests/test_issue7_non_ascii_zones.py`:
   - 6 automated regression tests verifying Cyrillic, accented names, slugify fallbacks, and zone controller integrations.

---

## 3. Communication Templates (Ready to Copy/Paste)

### A. Response to `bulanovk` on GitHub Issue #7

**Topic:** [Issue #7: Zone with a non-ASCII name never heats: internal entity_id diverges from the one HA assigns](https://github.com/alex-military/multizone-thermostat/issues/7)

```markdown
Hi @bulanovk,

Thank you very much for this exceptional issue report! Your root cause analysis was spot-on and made diagnosing and resolving this bug straightforward.

### Root Cause & What Was Fixed
As you correctly diagnosed, `make_zone_entity_id()` previously relied on Python's `str.isalnum()`, which retains non-ASCII alphanumeric characters (such as Cyrillic letters in `Спальная`). While that string was used internally as the key for thermal models, autotuners, and PID controllers, Home Assistant's Entity Registry applies its own `slugify()` function (enforcing `[a-z0-9_]`), producing `climate.multizone_thermostat_spalnaia`. 

Because of this divergence, whenever state updates arrived from Home Assistant with the slugified entity ID, `ZoneController.async_update_zone()` could not find the zone in its internal lookup tables and silently returned `0.0` heat demand, leaving the heating loop permanently idle.

### Changes Implemented in v5.1.1:
1. **Core Transliteration via `slugify`**: `make_zone_entity_id()` in `const.py` now directly imports and uses Home Assistant's native `slugify` (`from homeassistant.util import slugify`), with a safe fallback mechanism. Cyrillic and accented characters now produce identical, deterministic slugs in both the internal engine and HA's Entity Registry (e.g., `Спальная` $\rightarrow$ `climate.multizone_thermostat_spalnaia`).
2. **Explicit Warning Logging**: `ZoneController.async_update_zone()` now logs an explicit warning (`Unknown zone entity '...' not registered in thermal models, autotuners, or PIDs`) rather than failing silently if an unregistered ID is ever received.
3. **Comprehensive Regression Tests**: Added automated unit tests in `tests/test_issue7_non_ascii_zones.py` covering Cyrillic names, Latin accents, and fallback behavior.

This fix has been released in **v5.1.1**, now available on HACS and GitHub. Existing ASCII zone configurations remain 100% unaffected and backward-compatible.

Please update to **v5.1.1** and verify that your zones heat properly with their native Cyrillic names. Thanks again for your valuable contribution to the project!
```

---

### B. Response to `@serv2002` on Home Assistant Community Forum (Post #33)

**Topic:** [Multizone Thermostat v3 - Smart PID / PWM / Geofencing / 100% UI - No YAML](https://community.home-assistant.io/t/multizone-thermostat-v3-smart-pid-pwm-geofencing-100-ui-no-yaml/1018712)

```markdown
Hi @serv2002,

Thank you for following up and for sharing the screenshots!

I apologize for the confusion regarding the v5.1.0 update. Release **v5.1.0** was focused primarily on the plant backend engine (dynamic heat demand aggregation strategies, authoritative hardware synchronization for physical thermostats, and outdoor weather curve modulation). The frontend card updates were completed right after, and they are now officially published in **v5.1.1**!

Here is what is now available in **v5.1.1**:

1. **Supply / Flow Temperature in OpenTherm Telemetry Grid:**
   - The card now displays the **Supply Water Temperature** (`Подача воды` / Flow Temp) right next to the Return Water Temperature (`Обратка воды`), giving you immediate visibility into your boiler's flow temperature and condensing $\Delta T$.

2. **Complete Multilingual Localization (Full Russian Translation):**
   - We eliminated all hardcoded Italian strings from the OpenTherm card component.
   - The entire OpenTherm telemetry box, badges, and status labels are now fully localized into **Russian (`ru`)** based on your Home Assistant interface language:
     - `🚿 Acqua Calda (ACS)` $\rightarrow$ **`🚿 Горячая вода (ГВС)`**
     - `Pressione` $\rightarrow$ **`Давление`**
     - `Mandata Acqua` $\rightarrow$ **`Подача воды`**
     - `Ritorno Acqua` $\rightarrow$ **`Обратка воды`**
     - `Modulazione` $\rightarrow$ **`Модуляция`**
     - `Stato Fiamma` $\rightarrow$ **`Состояние пламени`** (`🔥 Горит` / `Выкл`)
     - `Condensazione OK` $\rightarrow$ **`Конденсация в норме`**
     - `Ritorno caldo (>54°C)` $\rightarrow$ **`Горячая обратка (>54°C)`**

3. **Dynamic Setpoint Precision:**
   - Full support for `0.1°C` / `0.5°C` temperature setpoint stepping.

### How to update:
1. Update **Multizone Thermostat** to **v5.1.1** via HACS.
2. Restart Home Assistant if prompted.
3. **Important for the Lovelace card:** Because browsers aggressively cache JavaScript cards, please perform a hard refresh (**Ctrl + F5** on Windows/Linux or **Cmd + Shift + R** on Mac), or clear the webview cache if you are using the Home Assistant Companion App.

Thank you again for your patience and for helping make the integration better for the whole community! Let me know if everything looks good on your dashboard.
```

---

## 4. Test & Quality Verification

All automated test suites executed successfully without errors or regressions:
- Total tests: **150 passed in 1.49s**.
- Full coverage for Cyrillic transliteration, fallback handling, ZoneController registration, and warning log assertions.
