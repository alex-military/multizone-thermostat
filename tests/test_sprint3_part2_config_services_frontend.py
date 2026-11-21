"""Regression tests for Sprint 3 Wave 2 (#16-#19): Config/Options Flow, Services/Schemas, Translations & Frontend."""
from __future__ import annotations

import json
from pathlib import Path
import re
import subprocess
import sys
from unittest.mock import AsyncMock, MagicMock

import pytest
import voluptuous as vol

# Ensure dummy_ha modules are used cleanly if earlier tests injected mocks
sys.meta_path[:] = [
    f for f in sys.meta_path if f.__class__.__name__ != "HomeAssistantMockFinder"
]
for _mod_name in (
    "homeassistant.components.select",
    "homeassistant.helpers.restore_state",
    "homeassistant.helpers.entity",
):
    if _mod_name in sys.modules and isinstance(sys.modules[_mod_name], MagicMock):
        del sys.modules[_mod_name]

from custom_components.multizone_thermostat import (
    SERVICE_ACTIVATE_SCHEDULE_PROFILE_SCHEMA,
    SERVICE_CANCEL_SMART_RETURN_SCHEMA,
    SERVICE_CLEAR_ZONE_OVERRIDE_SCHEMA,
    SERVICE_DUPLICATE_SCHEDULE_PROFILE_SCHEMA,
    SERVICE_SAVE_SCHEDULE_PROFILE_SCHEMA,
    SERVICE_SET_MASTER_OPERATION_MODE_SCHEMA,
    SERVICE_SET_PID_SCHEMA,
    SERVICE_SET_PRESET_TEMPERATURE_SCHEMA,
    SERVICE_SET_SMART_RETURN_SCHEMA,
    _async_register_services,
)
from custom_components.multizone_thermostat.config_flow import MultizoneConfigFlow
from custom_components.multizone_thermostat.config_flow.options_flow import MultizoneOptionsFlow
from custom_components.multizone_thermostat.config_flow.schemas import get_options_edit_zone_schema
from custom_components.multizone_thermostat.const import (
    CONF_HEAT_PUMP_COOLING,
    CONF_HEAT_PUMP_COOL_MAX_TEMP,
    CONF_HEAT_PUMP_COOL_MIN_TEMP,
    CONF_HEAT_PUMP_ENTITY,
    CONF_HEAT_PUMP_MAX_TEMP,
    CONF_HEAT_PUMP_MIN_TEMP,
    CONF_HEAT_PUMP_TYPE,
    CONF_ZONE_CLIMATES,
    CONF_ZONE_HUMIDITY_SENSOR,
    CONF_ZONE_NAME,
    CONF_ZONE_SWITCHES,
    DOMAIN,
    HP_TYPE_CLIMATE,
    HVAC_MODE_COOL,
    HVAC_MODE_HEAT,
    make_zone_entity_id,
)
from custom_components.multizone_thermostat.zone_controller import ZoneController


ROOT_DIR = Path(__file__).resolve().parents[1]
CC_DIR = ROOT_DIR / "custom_components" / "multizone_thermostat"


def _make_flow_hass():
    hass = MagicMock()
    hass.data = {DOMAIN: {}}
    hass.states = MagicMock()
    hass.states.async_all.return_value = []
    hass.config_entries = MagicMock()
    hass.config_entries.async_update_entry = MagicMock()
    hass.config_entries.async_reload = AsyncMock()
    hass.async_create_task = MagicMock(side_effect=lambda c: c.close() if hasattr(c, "close") else MagicMock())
    return hass


# ---------------------------------------------------------------------------
# #16: Config Flow & Options Flow
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_16_config_and_options_flow_humidity_hp_cool_and_clear_options():
    """#16: CONF_ZONE_HUMIDITY_SENSOR persisted/cleared cleanly, edit schema builds without TypeError, HP cool temps validated, _save_options clears options={}."""
    hass = _make_flow_hass()

    # 1. ConfigFlow validates HP cool min/max when cooling enabled
    cfg = MultizoneConfigFlow()
    cfg.hass = hass
    cfg.async_show_form = MagicMock(side_effect=lambda **kw: {"type": "form", **kw})
    res_hp = await cfg.async_step_heat_pump(
        {
            CONF_HEAT_PUMP_TYPE: HP_TYPE_CLIMATE,
            CONF_HEAT_PUMP_ENTITY: "climate.hp",
            CONF_HEAT_PUMP_MIN_TEMP: 25.0,
            CONF_HEAT_PUMP_MAX_TEMP: 55.0,
            CONF_HEAT_PUMP_COOLING: True,
            CONF_HEAT_PUMP_COOL_MIN_TEMP: 20.0,
            CONF_HEAT_PUMP_COOL_MAX_TEMP: 15.0,  # invalid! min >= max
        }
    )
    assert res_hp["type"] == "form"
    assert res_hp["errors"]

    # 2. ConfigFlow.async_step_add_zone saves CONF_ZONE_HUMIDITY_SENSOR
    res_zone = await cfg.async_step_add_zone(
        {
            CONF_ZONE_NAME: "Bath",
            CONF_ZONE_SWITCHES: ["switch.bath_valve"],
            CONF_ZONE_HUMIDITY_SENSOR: "sensor.bath_humidity",
        }
    )
    assert len(cfg._zones) == 1
    assert cfg._zones[0][CONF_ZONE_HUMIDITY_SENSOR] == "sensor.bath_humidity"
    assert res_zone["type"] == "form"  # advances to another_zone

    # 3. OptionsFlow.async_step_add_zone saves CONF_ZONE_HUMIDITY_SENSOR
    opt = MultizoneOptionsFlow()
    opt.hass = hass
    entry = MagicMock()
    entry.entry_id = "e1"
    entry.data = {}
    entry.options = {"stale_key": 123}
    opt.config_entry = entry
    opt.async_show_form = MagicMock(side_effect=lambda **kw: {"type": "form", **kw})
    opt.async_create_entry = MagicMock(side_effect=lambda **kw: {"type": "create_entry", **kw})

    res_opt_add = await opt.async_step_add_zone(
        {
            CONF_ZONE_NAME: "Laundry",
            "trv_settings": {CONF_ZONE_CLIMATES: ["climate.laundry_trv"]},
            CONF_ZONE_HUMIDITY_SENSOR: "sensor.laundry_humidity",
        }
    )
    assert res_opt_add["type"] == "create_entry"
    assert opt._zones[0][CONF_ZONE_HUMIDITY_SENSOR] == "sensor.laundry_humidity"
    # Verify _save_options cleared stale entry.options and returned empty options data
    update_kwargs = hass.config_entries.async_update_entry.call_args[1]
    assert update_kwargs["options"] == {}
    assert res_opt_add["data"] == {}

    # 4. get_options_edit_zone_schema handles existing CONF_ZONE_HUMIDITY_SENSOR without TypeError
    schema = get_options_edit_zone_schema(opt._zones[0], {}, {})
    hum_opt = next(k for k in schema.schema if getattr(k, "schema", None) == CONF_ZONE_HUMIDITY_SENSOR)
    assert hum_opt.description == {"suggested_value": "sensor.laundry_humidity"}

    # 5. OptionsFlow.async_step_edit_zone updates and then removes CONF_ZONE_HUMIDITY_SENSOR
    opt._current_zone_name = "Laundry"
    await opt.async_step_edit_zone(
        {
            "trv_settings": {CONF_ZONE_CLIMATES: ["climate.laundry_trv"]},
            CONF_ZONE_HUMIDITY_SENSOR: "sensor.new_humidity",
        }
    )
    assert opt._zones[0][CONF_ZONE_HUMIDITY_SENSOR] == "sensor.new_humidity"

    opt._current_zone_name = "Laundry"
    await opt.async_step_edit_zone(
        {
            "trv_settings": {CONF_ZONE_CLIMATES: ["climate.laundry_trv"]},
        }
    )
    assert CONF_ZONE_HUMIDITY_SENSOR not in opt._zones[0]


# ---------------------------------------------------------------------------
# #17: Services & Voluptuous Schemas
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_17_service_schemas_and_lock_all():
    """#17: All 11 services register with Voluptuous schemas; set_pid_parameters accepts lock_parameter='all' and 'ALL'."""
    hass = MagicMock()
    hass.data = {DOMAIN: {}}
    hass.services = MagicMock()
    registered = {}

    def _reg(domain, name, handler, schema=None):
        registered[name] = (handler, schema)

    hass.services.async_register = MagicMock(side_effect=_reg)

    cid = make_zone_entity_id("Living")
    coord = MagicMock()
    coord.zones = [{CONF_ZONE_NAME: "Living"}]
    coord.master_hvac_mode = HVAC_MODE_HEAT
    coord.resolve_zone_id = lambda x: x
    coord.async_set_persistent_data = AsyncMock()
    coord.async_set_pid_manual_unlock = AsyncMock()
    coord.storage = None
    coord.async_notify_pid_entities = MagicMock()
    coord.plant_orchestrator = None

    zc = ZoneController(hass, coord)
    tuner = zc.get_autotuner(cid)
    tuner.set_manual_pid(kp=12.0, ki=0.05, kd=10.0)
    assert set(tuner.manual_overrides.keys()) == {"Kp", "Ki", "Kd"}
    coord.zone_controller = zc
    hass.data[DOMAIN]["e1"] = {"coordinator": coord}

    await _async_register_services(hass)

    expected_services = {
        "save_schedule_profile",
        "activate_schedule_profile",
        "duplicate_schedule_profile",
        "set_smart_return",
        "cancel_smart_return",
        "clear_zone_override",
        "set_preset_temperature",
        "set_master_operation_mode",
        "set_pid_parameters",
        "reset_autotune",
        "restore_autotune",
    }
    assert set(registered.keys()) == expected_services
    for svc_name, (_, schema) in registered.items():
        assert schema is not None, f"Service {svc_name} must register a non-None schema"

    # Schema validations (valid + invalid)
    SERVICE_SAVE_SCHEDULE_PROFILE_SCHEMA({"profile_id": "p1", "baseline_preset": "eco", "days": {}})
    SERVICE_SAVE_SCHEDULE_PROFILE_SCHEMA({"profile": {"id": "p2", "name": "P2", "days": {}}})
    with pytest.raises(vol.Invalid):
        SERVICE_SAVE_SCHEDULE_PROFILE_SCHEMA({"name": "missing_id"})

    SERVICE_ACTIVATE_SCHEDULE_PROFILE_SCHEMA({"profile_id": "standard", "expires_at": ""})
    SERVICE_DUPLICATE_SCHEDULE_PROFILE_SCHEMA({"source_profile_id": "standard", "target_profile_id": "copy1"})
    SERVICE_SET_SMART_RETURN_SCHEMA({"arrival_time": "18:30", "preset": "comfort"})
    SERVICE_CANCEL_SMART_RETURN_SCHEMA({})
    SERVICE_CLEAR_ZONE_OVERRIDE_SCHEMA({"entity_id": None})
    SERVICE_SET_PRESET_TEMPERATURE_SCHEMA({"preset": "comfort", "entity_id": cid, "temperature": 71.6, "hvac_mode": "heat"})
    with pytest.raises(vol.Invalid):
        SERVICE_SET_PRESET_TEMPERATURE_SCHEMA({"preset": "comfort", "entity_id": cid, "temperature": 120.0})

    SERVICE_SET_MASTER_OPERATION_MODE_SCHEMA({"operation_mode": HVAC_MODE_COOL})
    SERVICE_SET_MASTER_OPERATION_MODE_SCHEMA({"hvac_mode": HVAC_MODE_HEAT})
    with pytest.raises(vol.Invalid):
        SERVICE_SET_MASTER_OPERATION_MODE_SCHEMA({})

    # lock_parameter "all" and "ALL" accepted by schema and clears all overrides
    SERVICE_SET_PID_SCHEMA({"climate_entity": cid, "lock_parameter": "all", "ki": 10.0})
    SERVICE_SET_PID_SCHEMA({"climate_entity": cid, "lock_parameter": "ALL"})
    handler_pid, _ = registered["set_pid_parameters"]
    await handler_pid(MagicMock(data={"climate_entity": cid, "lock_parameter": "all"}))
    assert tuner.manual_overrides == {}

    # services.yaml ki max matches 10.0
    yaml_text = (CC_DIR / "services.yaml").read_text(encoding="utf-8")
    assert "max: 10.0" in yaml_text


# ---------------------------------------------------------------------------
# #18: Translations & strings.json Parity
# ---------------------------------------------------------------------------


def _flat_keys(d: dict, prefix: str = "") -> set[str]:
    out: set[str] = set()
    for k, v in d.items():
        np = f"{prefix}.{k}" if prefix else k
        if isinstance(v, dict):
            out |= _flat_keys(v, np)
        else:
            out.add(np)
    return out


def test_18_translations_parity_and_required_keys():
    """#18: strings.json and all 6 translation files share 100% key parity including humidity_sensor, hp_temps_invalid, zone_not_found."""
    strings = json.loads((CC_DIR / "strings.json").read_text(encoding="utf-8"))
    base_keys = _flat_keys(strings)

    for loc in ("de", "en", "es", "fr", "it", "ru"):
        tr = json.loads((CC_DIR / "translations" / f"{loc}.json").read_text(encoding="utf-8"))
        assert _flat_keys(tr) == base_keys, f"Parity mismatch in translations/{loc}.json"
        for top, step in (("config", "add_zone"), ("options", "add_zone"), ("options", "edit_zone")):
            assert "humidity_sensor" in tr[top]["step"][step]["data"]
            assert "humidity_sensor" in tr[top]["step"][step]["data_description"]
        assert "hp_temps_invalid" in tr["config"]["error"]
        assert "zone_not_found" in tr["options"]["abort"]


# ---------------------------------------------------------------------------
# #19: Frontend Lovelace Bundles, Post #52 UI Fixes, °F & XSS
# ---------------------------------------------------------------------------


def test_19_frontend_bundle_up_to_date_xss_fahrenheit_and_post52():
    """#19: Frontend bundles synchronized, XSS/°F/null helpers present, Post #52 pill CSS & localization fixed."""
    res = subprocess.run(
        [sys.executable, str(ROOT_DIR / "frontend" / "build.py"), "--check"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert res.returncode == 0, res.stderr or res.stdout

    bundle_main = (CC_DIR / "www" / "multizone-thermostat-card.js").read_text(encoding="utf-8")
    bundle_v24 = (CC_DIR / "www" / "multizone-thermostat-card-v24.js").read_text(encoding="utf-8")
    bundle_wiki = (ROOT_DIR / "docs" / "wiki" / "multizone-thermostat-card.js").read_text(encoding="utf-8")
    bundle_docs = (ROOT_DIR / "docs" / "multizone-thermostat-card.js").read_text(encoding="utf-8")
    assert bundle_main == bundle_v24 == bundle_wiki == bundle_docs

    for fn in ("function escapeHtml(", "function celsiusToDisplay(", "function celsiusDeltaToDisplay(", "function isFahrenheit("):
        assert fn in bundle_main

    # Post #52: no navigator.language anywhere in bundle; Russian pid_modal_cancel present
    assert "navigator.language" not in bundle_main
    assert 'pid_modal_cancel: "Отмена"' in bundle_main

    # 6-language translation parity inside 01_translations.js
    tr_src = (ROOT_DIR / "frontend" / "src" / "01_translations.js").read_text(encoding="utf-8")
    langs: dict[str, set[str]] = {}
    cur = None
    for line in tr_src.splitlines():
        m = re.match(r"^\s{2}(it|en|ru|fr|de|es):\s*\{", line)
        if m:
            cur = m.group(1)
            langs[cur] = set()
            continue
        if cur:
            km = re.match(r"^\s{4}([a-zA-Z0-9_]+)\s*:", line)
            if km:
                langs[cur].add(km.group(1))
            elif re.match(r"^\s{2}\}", line):
                cur = None
    all_js_keys = set().union(*langs.values())
    for l, ks in langs.items():
        assert ks == all_js_keys, f"01_translations.js mismatch for {l}: missing {all_js_keys - ks}"

    # Post #52: plant_card.js and simulator.html enforce ha-card { display: block; }
    plant_src = (ROOT_DIR / "frontend" / "src" / "components" / "plant_card.js").read_text(encoding="utf-8")
    sim_html = (ROOT_DIR / "docs" / "wiki" / "simulator.html").read_text(encoding="utf-8")
    assert re.search(r"ha-card\s*\{[^}]*display:\s*block;", plant_src, re.S)
    assert re.search(r"ha-card\s*\{\s*display:\s*block;", sim_html, re.S)
    assert 'v=6.1.0-beta.17' in sim_html

    # null temp guard & XSS guards
    btn_src = (ROOT_DIR / "frontend" / "src" / "components" / "button_card.js").read_text(encoding="utf-8")
    assert "currentTemp !== undefined && currentTemp !== null" in btn_src
    assert "escapeHtml(a.zone)" in plant_src and "escapeHtml(a.description)" in plant_src
