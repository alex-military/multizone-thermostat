"""Tests for per-zone configurable target temperature step (Issue #20 / Post #57)."""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
from unittest.mock import AsyncMock, MagicMock

import pytest

# Ensure dummy_ha modules are used cleanly if earlier tests injected mocks
sys.meta_path[:] = [
    f for f in sys.meta_path if f.__class__.__name__ != "HomeAssistantMockFinder"
]
for _mod_name in (
    "homeassistant.components.select",
    "homeassistant.helpers.restore_state",
    "homeassistant.helpers.entity",
    "homeassistant.helpers.selector",
    "homeassistant.data_entry_flow",
):
    if _mod_name in sys.modules and isinstance(sys.modules[_mod_name], MagicMock):
        del sys.modules[_mod_name]

from homeassistant.const import ATTR_TEMPERATURE

from custom_components.multizone_thermostat.climate import MultizoneVirtualThermostat
from custom_components.multizone_thermostat.config_flow import MultizoneConfigFlow
from custom_components.multizone_thermostat.config_flow.options_flow import MultizoneOptionsFlow
from custom_components.multizone_thermostat.config_flow.schemas import (
    get_add_zone_schema,
    get_options_edit_zone_schema,
)
from custom_components.multizone_thermostat.const import (
    CONF_ZONES,
    CONF_ZONE_CLIMATES,
    CONF_ZONE_NAME,
    CONF_ZONE_SWITCHES,
    CONF_ZONE_TARGET_TEMP,
    CONF_ZONE_TEMP_STEP,
    DEFAULT_ZONE_TEMP_STEP,
    DOMAIN,
    make_zone_entity_id,
    normalize_zone_temp_step,
)
from custom_components.multizone_thermostat.coordinator import MultizoneCoordinator
from custom_components.multizone_thermostat.diagnostics import async_get_config_entry_diagnostics
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
    hass.async_create_task = MagicMock(
        side_effect=lambda c: c.close() if hasattr(c, "close") else MagicMock()
    )
    return hass


def _make_climate_hass():
    hass = MagicMock()
    hass.states.get.return_value = None
    hass.async_create_task = MagicMock(
        side_effect=lambda c: c.close() if hasattr(c, "close") else MagicMock()
    )
    coord = MagicMock()
    coord.hass = hass
    coord.boiler_switch = None
    coord.get_zone_mode.return_value = "primary"
    coord.get_zone_demand.return_value = 0.0
    coord.get_master_state.return_value = True
    coord.get_global_preset.return_value = "none"
    coord.schedule_manager = None
    coord.calendar_manager = MagicMock(temp_overrides={})
    coord.zone_controller = None
    coord.demand_aggregator = MagicMock()
    coord.demand_aggregator.get_zone_weight.return_value = 1.0
    coord.zone_manager = MagicMock()
    coord.zone_manager.is_passive_heat_allowed.return_value = False
    hass.data = {DOMAIN: {"e1": {"coordinator": coord}}}
    return hass


def test_normalize_zone_temp_step():
    """normalize_zone_temp_step accepts 0.1 / 0.5 (str or float) and falls back to 0.5."""
    assert normalize_zone_temp_step("0.1") == 0.1
    assert normalize_zone_temp_step(0.1) == 0.1
    assert normalize_zone_temp_step("0.5") == 0.5
    assert normalize_zone_temp_step(0.5) == 0.5
    assert normalize_zone_temp_step(None) == DEFAULT_ZONE_TEMP_STEP == 0.5
    assert normalize_zone_temp_step("0.2") == 0.5
    assert normalize_zone_temp_step("bad") == 0.5


@pytest.mark.asyncio
async def test_virtual_thermostat_per_zone_step_and_precision():
    """Each zone exposes its configured step (0.1 vs 0.5) and keeps 0.1 precision."""
    hass = _make_climate_hass()

    legacy_zone = {
        CONF_ZONE_NAME: "Hallway",
        CONF_ZONE_SWITCHES: ["switch.hallway"],
    }
    fine_zone = {
        CONF_ZONE_NAME: "Living Room",
        CONF_ZONE_SWITCHES: ["switch.living"],
        CONF_ZONE_TEMP_STEP: "0.1",
    }
    fine_float_zone = {
        CONF_ZONE_NAME: "Study",
        CONF_ZONE_SWITCHES: ["switch.study"],
        CONF_ZONE_TEMP_STEP: 0.1,
    }

    t_legacy = MultizoneVirtualThermostat(hass, "e1", legacy_zone)
    t_fine = MultizoneVirtualThermostat(hass, "e1", fine_zone)
    t_fine_float = MultizoneVirtualThermostat(hass, "e1", fine_float_zone)

    assert t_legacy.target_temperature_step == 0.5
    assert t_legacy._attr_target_temperature_step == 0.5
    assert t_fine.target_temperature_step == 0.1
    assert t_fine._attr_target_temperature_step == 0.1
    assert t_fine_float.target_temperature_step == 0.1

    t_fine.async_write_ha_state = MagicMock()
    t_fine._trigger_trv_sync = AsyncMock()
    await t_fine.async_set_temperature(**{ATTR_TEMPERATURE: 19.8})
    assert t_fine.target_temperature == pytest.approx(19.8)


@pytest.mark.asyncio
async def test_config_and_options_flow_target_temp_step():
    """Schemas expose 0.5/0.1 dropdown + step=0.1 base target; flows persist & edit cleanly."""
    # 1. Add schema structure
    add_schema = get_add_zone_schema()
    step_key = next(
        k for k in add_schema.schema if getattr(k, "schema", None) == CONF_ZONE_TEMP_STEP
    )
    assert step_key.default() == "0.5"
    step_sel = add_schema.schema[step_key]
    assert [opt["value"] for opt in step_sel.config["options"]] == ["0.5", "0.1"]

    target_key = next(
        k for k in add_schema.schema if getattr(k, "schema", None) == CONF_ZONE_TARGET_TEMP
    )
    assert add_schema.schema[target_key].config["step"] == 0.1

    # 2. ConfigFlow add_zone saves float 0.1 and 19.8
    hass = _make_flow_hass()
    cfg = MultizoneConfigFlow()
    cfg.hass = hass
    cfg.async_show_form = MagicMock(side_effect=lambda **kw: {"type": "form", **kw})
    await cfg.async_step_add_zone(
        {
            CONF_ZONE_NAME: "Living",
            CONF_ZONE_SWITCHES: ["switch.living"],
            CONF_ZONE_TARGET_TEMP: 19.8,
            CONF_ZONE_TEMP_STEP: "0.1",
        }
    )
    assert len(cfg._zones) == 1
    assert cfg._zones[0][CONF_ZONE_TEMP_STEP] == 0.1
    assert isinstance(cfg._zones[0][CONF_ZONE_TEMP_STEP], float)
    assert cfg._zones[0][CONF_ZONE_TARGET_TEMP] == pytest.approx(19.8)

    # 3. OptionsFlow add_zone & edit_zone schema/persistence
    opt = MultizoneOptionsFlow()
    opt.hass = hass
    entry = MagicMock()
    entry.entry_id = "e1"
    entry.data = {}
    entry.options = {}
    opt.config_entry = entry
    opt.async_show_form = MagicMock(side_effect=lambda **kw: {"type": "form", **kw})
    opt.async_create_entry = MagicMock(side_effect=lambda **kw: {"type": "create_entry", **kw})

    await opt.async_step_add_zone(
        {
            CONF_ZONE_NAME: "Kitchen",
            CONF_ZONE_CLIMATES: ["climate.trv_kitchen"],
            CONF_ZONE_TARGET_TEMP: 19.8,
            CONF_ZONE_TEMP_STEP: "0.1",
        }
    )
    assert opt._zones[0][CONF_ZONE_TEMP_STEP] == 0.1

    # Edit schema defaults to "0.1" when zone has 0.1, and "0.5" for legacy zone
    edit_schema = get_options_edit_zone_schema(opt._zones[0], {}, {})
    edit_step_key = next(
        k for k in edit_schema.schema if getattr(k, "schema", None) == CONF_ZONE_TEMP_STEP
    )
    assert edit_step_key.default() == "0.1"
    edit_target_key = next(
        k for k in edit_schema.schema if getattr(k, "schema", None) == CONF_ZONE_TARGET_TEMP
    )
    assert edit_schema.schema[edit_target_key].config["step"] == 0.1

    legacy_edit_schema = get_options_edit_zone_schema({CONF_ZONE_NAME: "Legacy"}, {}, {})
    legacy_step_key = next(
        k for k in legacy_edit_schema.schema if getattr(k, "schema", None) == CONF_ZONE_TEMP_STEP
    )
    assert legacy_step_key.default() == "0.5"

    # Edit back to "0.5"
    opt._current_zone_name = "Kitchen"
    await opt.async_step_edit_zone(
        {
            CONF_ZONE_CLIMATES: ["climate.trv_kitchen"],
            CONF_ZONE_TARGET_TEMP: 20.0,
            CONF_ZONE_TEMP_STEP: "0.5",
        }
    )
    assert opt._zones[0][CONF_ZONE_TEMP_STEP] == 0.5


@pytest.mark.asyncio
async def test_diagnostics_reports_target_temp_step_per_zone():
    """Diagnostics reports target_temp_step per zone (0.1 vs default 0.5)."""
    hass = MagicMock()
    hass.states.get.return_value = None
    entry = MagicMock()
    entry.entry_id = "diag_step_entry"
    entry.version = 1
    entry.domain = DOMAIN
    entry.title = "Diag Step Master"
    entry.data = {
        CONF_ZONES: [
            {CONF_ZONE_NAME: "Cucina", CONF_ZONE_TEMP_STEP: 0.1},
            {CONF_ZONE_NAME: "Bagno"},
        ]
    }
    entry.options = {}
    coord = MultizoneCoordinator(hass, entry)
    coord.zone_controller = ZoneController(hass, coord)
    coord._pids = coord.zone_controller.pids
    hass.data = {DOMAIN: {entry.entry_id: {"coordinator": coord}}}

    result = await async_get_config_entry_diagnostics(hass, entry)
    assert result["zones"][make_zone_entity_id("Cucina")]["target_temp_step"] == 0.1
    assert result["zones"][make_zone_entity_id("Bagno")]["target_temp_step"] == 0.5


def _flat_keys(d: dict, prefix: str = "") -> set[str]:
    out: set[str] = set()
    for k, v in d.items():
        np = f"{prefix}.{k}" if prefix else k
        if isinstance(v, dict):
            out |= _flat_keys(v, np)
        else:
            out.add(np)
    return out


def test_translations_parity_and_target_temp_step_keys():
    """strings.json and all 6 translation files include target_temp_step with 100% key parity."""
    strings = json.loads((CC_DIR / "strings.json").read_text(encoding="utf-8"))
    base_keys = _flat_keys(strings)

    for loc in ("de", "en", "es", "fr", "it", "ru"):
        tr = json.loads((CC_DIR / "translations" / f"{loc}.json").read_text(encoding="utf-8"))
        assert _flat_keys(tr) == base_keys, f"Parity mismatch in translations/{loc}.json"
        for top, step in (("config", "add_zone"), ("options", "add_zone"), ("options", "edit_zone")):
            assert CONF_ZONE_TEMP_STEP in tr[top]["step"][step]["data"]
            assert CONF_ZONE_TEMP_STEP in tr[top]["step"][step]["data_description"]


def test_frontend_bundle_dial_card_respects_dynamic_step():
    """Master frontend bundle is up-to-date and dial drag uses getStep() instead of 0.5."""
    res = subprocess.run(
        [sys.executable, str(ROOT_DIR / "frontend" / "build.py"), "--check"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert res.returncode == 0, res.stderr or res.stdout

    bundle = (CC_DIR / "www" / "multizone-thermostat-card.js").read_text(encoding="utf-8")
    dial_start = bundle.index("class MultizoneThermostatDialCard")
    dial_end = bundle.index("class MultizoneThermostatCardEditor")
    dial_section = bundle[dial_start:dial_end]
    assert "getStep()" in dial_section
    assert "Math.round(temp * 2) / 2" not in dial_section
