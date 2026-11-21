"""Tests for native TRV external temperature input feed, heartbeat, and sensor select fallback."""
from __future__ import annotations

import asyncio
import sys
import types
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from homeassistant.components.climate import HVACMode
from homeassistant.const import ATTR_TEMPERATURE, STATE_UNAVAILABLE, STATE_UNKNOWN

from custom_components.multizone_thermostat.const import (
    CONF_ZONE_CLIMATES,
    CONF_ZONE_NAME,
    CONF_ZONE_TEMP_SENSOR,
    CONF_ZONE_TRV_CALIBRATION_MODE,
    CONF_ZONE_TRV_SENSOR_SELECTS,
    CONF_ZONE_CALIBRATIONS,
    TRV_CALIB_MODE_AUTO,
    TRV_CALIB_MODE_EXTERNAL,
    TRV_CALIB_MODE_OFFSET,
)
from custom_components.multizone_thermostat.config_flow.helpers import (
    TRV_SENSOR_SELECT_SUFFIX,
    parse_trv_calibration_input,
)
from custom_components.multizone_thermostat.sync_manager import ZoneSyncManager


def _setup_clean_ha_environment():
    """Ensure clean Home Assistant config_flow environment while preserving other loaded modules."""
    saved_meta_path = list(sys.meta_path)
    saved_modules = dict(sys.modules)
    sys.meta_path = [f for f in sys.meta_path if f.__class__.__name__ != "HomeAssistantMockFinder"]
    for mod_name in list(sys.modules.keys()):
        if (
            mod_name in (
                "homeassistant",
                "homeassistant.data_entry_flow",
                "homeassistant.config_entries",
                "homeassistant.helpers",
                "homeassistant.helpers.selector",
            )
            or "config_flow" in mod_name
        ):
            del sys.modules[mod_name]

    data_entry_flow_mod = types.ModuleType("homeassistant.data_entry_flow")
    data_entry_flow_mod.section = lambda s, o=None: s
    sys.modules["homeassistant.data_entry_flow"] = data_entry_flow_mod
    return saved_meta_path, saved_modules


def _restore_ha_environment(saved_meta_path, saved_modules):
    """Restore original sys.meta_path and sys.modules."""
    sys.meta_path[:] = saved_meta_path
    sys.modules.clear()
    sys.modules.update(saved_modules)


def _make_sync_manager(
    *,
    calibration_mode: str = TRV_CALIB_MODE_AUTO,
    calibrations: dict[str, str] | None = None,
    trv_sensor_selects: dict[str, str] | None = None,
    ext_temp_heartbeat_s: float = 1200.0,
    ext_temp_min_interval_s: float = 60.0,
) -> ZoneSyncManager:
    hass = MagicMock()
    hass.services.async_call = AsyncMock()
    coordinator = MagicMock()
    coordinator.get_persistent_data.return_value = True
    return ZoneSyncManager(
        hass=hass,
        coordinator=coordinator,
        zone_name="Soggiorno",
        entity_id="climate.multizone_thermostat_soggiorno",
        climates=["climate.sonoff_trv"],
        switches=[],
        calibrations=calibrations if calibrations is not None else {"climate.sonoff_trv": "number.sonoff_trv_external_temperature_input"},
        calibration_mode=calibration_mode,
        trv_sensor_selects=trv_sensor_selects,
        ext_temp_heartbeat_s=ext_temp_heartbeat_s,
        ext_temp_min_interval_s=ext_temp_min_interval_s,
    )


def test_resolve_calibration_mode_auto_and_overrides():
    """Verify auto-detection by entity_id keywords, min/max heuristics, and explicit overrides."""
    mgr_auto = _make_sync_manager(calibration_mode=TRV_CALIB_MODE_AUTO)

    assert mgr_auto.resolve_calibration_mode("number.trv_local_temperature_calibration", None) == TRV_CALIB_MODE_OFFSET
    assert mgr_auto.resolve_calibration_mode("number.trv_1_cal", None) == TRV_CALIB_MODE_OFFSET
    assert mgr_auto.resolve_calibration_mode("number.sonoff_external_temperature_input", None) == TRV_CALIB_MODE_EXTERNAL
    assert mgr_auto.resolve_calibration_mode("number.danfoss_external_measured_room_sensor", None) == TRV_CALIB_MODE_EXTERNAL

    st_ext_bounds = MagicMock(state="20.0", attributes={"min": 0.0, "max": 50.0})
    assert mgr_auto.resolve_calibration_mode("number.custom_room_input", st_ext_bounds) == TRV_CALIB_MODE_EXTERNAL

    st_off_bounds = MagicMock(state="0.0", attributes={"min": -5.0, "max": 5.0})
    assert mgr_auto.resolve_calibration_mode("number.custom_entity", st_off_bounds) == TRV_CALIB_MODE_OFFSET

    # Explicit overrides ignore keywords/heuristics
    mgr_force_offset = _make_sync_manager(calibration_mode=TRV_CALIB_MODE_OFFSET)
    assert mgr_force_offset.resolve_calibration_mode("number.sonoff_external_temperature_input", st_ext_bounds) == TRV_CALIB_MODE_OFFSET

    mgr_force_ext = _make_sync_manager(calibration_mode=TRV_CALIB_MODE_EXTERNAL)
    assert mgr_force_ext.resolve_calibration_mode("number.trv_1_cal", st_off_bounds) == TRV_CALIB_MODE_EXTERNAL


@pytest.mark.asyncio
async def test_push_external_temp_c_f_step_clamp_and_unknown_vs_unavailable():
    """Verify °C/°F conversion, step rounding, min/max clamp, and unknown vs unavailable states."""
    mgr = _make_sync_manager(calibrations={"climate.sonoff_trv": "number.sonoff_external_temperature_input"})
    trv_state = MagicMock(
        state=HVACMode.HEAT,
        attributes={ATTR_TEMPERATURE: 20.0, "current_temperature": 19.0, "min_temp": 5.0, "max_temp": 35.0},
    )
    ext_state = MagicMock(
        state=STATE_UNKNOWN,
        attributes={"min": 0.0, "max": 35.0, "step": 0.5, "unit_of_measurement": "°C"},
    )
    mgr.hass.states.get.side_effect = lambda eid: trv_state if eid == "climate.sonoff_trv" else ext_state

    await mgr.async_sync_trvs(
        master_hvac_mode=HVACMode.HEAT,
        master_target_temp=20.0,
        master_current_temp=19.74,
        safety_fallback_active=False,
        has_external_sensor=True,
    )
    set_calls = [
        c for c in mgr.hass.services.async_call.call_args_list
        if c.args[0] == "number" and c.args[1] == "set_value"
    ]
    assert len(set_calls) == 1
    assert set_calls[0].args[2] == {"entity_id": "number.sonoff_external_temperature_input", "value": 19.5}

    trv_temp_calls = [
        c for c in mgr.hass.services.async_call.call_args_list
        if c.args[0] == "climate" and c.args[1] == "set_temperature"
    ]
    assert trv_temp_calls == []

    # Unavailable calibration entity must be skipped
    mgr.hass.services.async_call.reset_mock()
    ext_state.state = STATE_UNAVAILABLE
    await mgr.async_sync_trvs(
        master_hvac_mode=HVACMode.HEAT,
        master_target_temp=20.0,
        master_current_temp=21.0,
        safety_fallback_active=False,
        has_external_sensor=True,
    )
    assert not any(c.args[0] == "number" for c in mgr.hass.services.async_call.call_args_list)

    # Fahrenheit input_number conversion + clamp check
    mgr_f = _make_sync_manager(
        calibrations={"climate.sonoff_trv": "input_number.trv_external_temp"},
        calibration_mode=TRV_CALIB_MODE_EXTERNAL,
    )
    ext_f = MagicMock(
        state="65.0",
        attributes={"min": 32.0, "max": 95.0, "step": 0.5, "unit_of_measurement": "°F"},
    )
    mgr_f.hass.states.get.side_effect = lambda eid: trv_state if eid == "climate.sonoff_trv" else ext_f
    await mgr_f.async_sync_trvs(
        master_hvac_mode=HVACMode.HEAT,
        master_target_temp=20.0,
        master_current_temp=20.0,
        safety_fallback_active=False,
        has_external_sensor=True,
    )
    f_calls = [
        c for c in mgr_f.hass.services.async_call.call_args_list
        if c.args[0] == "input_number" and c.args[1] == "set_value"
    ]
    assert len(f_calls) == 1
    assert f_calls[0].args[2]["value"] == 68.0


@pytest.mark.asyncio
async def test_external_temp_rate_limit_and_heartbeat_in_off_mode():
    """Verify rate-limit blocks tiny jitter <60s, allows >=0.5°C jumps, and heartbeat pushes after 20 min even in OFF mode."""
    mgr = _make_sync_manager(
        calibrations={"climate.sonoff_trv": "number.sonoff_external_temperature_input"},
        ext_temp_heartbeat_s=1200.0,
        ext_temp_min_interval_s=60.0,
    )
    trv_state = MagicMock(
        state=HVACMode.OFF,
        attributes={ATTR_TEMPERATURE: 20.0, "current_temperature": None},
    )
    ext_state = MagicMock(
        state="20.0",
        attributes={"min": 0.0, "max": 50.0, "step": 0.1, "unit_of_measurement": "°C"},
    )
    mgr.hass.states.get.side_effect = lambda eid: trv_state if eid == "climate.sonoff_trv" else ext_state

    with patch("custom_components.multizone_thermostat.sync_manager.time.monotonic") as mock_mono:
        # t = 1000: initial push works even in HVACMode.OFF and with trv current_temperature=None
        mock_mono.return_value = 1000.0
        await mgr.async_sync_trvs(
            master_hvac_mode=HVACMode.OFF,
            master_target_temp=20.0,
            master_current_temp=20.0,
            safety_fallback_active=False,
            has_external_sensor=True,
        )
        assert mgr.hass.services.async_call.call_count == 1
        mgr.hass.services.async_call.reset_mock()

        # t = 1020 (+20s): tiny +0.1°C jitter is rate-limited
        mock_mono.return_value = 1020.0
        await mgr.async_external_temp_heartbeat(
            master_current_temp=20.1,
            safety_fallback_active=False,
            has_external_sensor=True,
        )
        assert mgr.hass.services.async_call.call_count == 0

        # t = 1025 (+25s): big +0.6°C jump bypasses rate-limit and pushes immediately
        mock_mono.return_value = 1025.0
        await mgr.async_external_temp_heartbeat(
            master_current_temp=20.6,
            safety_fallback_active=False,
            has_external_sensor=True,
        )
        assert mgr.hass.services.async_call.call_count == 1
        assert mgr.hass.services.async_call.call_args.args[2]["value"] == 20.6
        ext_state.state = "20.6"
        mgr.hass.services.async_call.reset_mock()

        # t = 1090 (+65s): small +0.1°C change after min_interval pushes cleanly
        mock_mono.return_value = 1090.0
        await mgr.async_external_temp_heartbeat(
            master_current_temp=20.7,
            safety_fallback_active=False,
            has_external_sensor=True,
        )
        assert mgr.hass.services.async_call.call_count == 1
        assert mgr.hass.services.async_call.call_args.args[2]["value"] == 20.7
        ext_state.state = "20.7"
        mgr.hass.services.async_call.reset_mock()

        # t = 1600 (+510s < 1200s): unchanged temp does NOT push before heartbeat interval
        mock_mono.return_value = 1600.0
        await mgr.async_external_temp_heartbeat(
            master_current_temp=20.7,
            safety_fallback_active=False,
            has_external_sensor=True,
        )
        assert mgr.hass.services.async_call.call_count == 0

        # t = 2300 (+1210s >= 1200s): unchanged temp DOES push keep-alive heartbeat
        mock_mono.return_value = 2300.0
        await mgr.async_external_temp_heartbeat(
            master_current_temp=20.7,
            safety_fallback_active=False,
            has_external_sensor=True,
        )
        assert mgr.hass.services.async_call.call_count == 1
        assert mgr.hass.services.async_call.call_args.args[2]["value"] == 20.7


@pytest.mark.asyncio
async def test_sensor_select_switch_and_safety_fallback_recovery():
    """Verify temperature_sensor_select switches to remote (never remote_source_offline) and falls back to local on fault."""
    mgr = _make_sync_manager(
        calibrations={"climate.sonoff_trv": "number.sonoff_external_temperature_input"},
        trv_sensor_selects={"climate.sonoff_trv": "select.sonoff_trv_temperature_sensor_select"},
    )
    trv_state = MagicMock(
        state=HVACMode.HEAT,
        attributes={ATTR_TEMPERATURE: 20.0, "current_temperature": 19.8, "min_temp": 5.0, "max_temp": 35.0},
    )
    ext_state = MagicMock(
        state="19.5",
        attributes={"min": 0.0, "max": 35.0, "step": 0.1, "unit_of_measurement": "°C"},
    )
    # Intentionally put remote_source_offline FIRST to prove it is never chosen
    sel_state = MagicMock(
        state="local_temperature",
        attributes={"options": ["remote_source_offline", "local_temperature", "remote_temperature"]},
    )

    def get_state(eid):
        return {
            "climate.sonoff_trv": trv_state,
            "number.sonoff_external_temperature_input": ext_state,
            "select.sonoff_trv_temperature_sensor_select": sel_state,
        }.get(eid)

    mgr.hass.states.get.side_effect = get_state

    # 1. Normal sync -> switches select to remote_temperature and pushes external temp
    await mgr.async_sync_trvs(
        master_hvac_mode=HVACMode.HEAT,
        master_target_temp=20.0,
        master_current_temp=19.8,
        safety_fallback_active=False,
        has_external_sensor=True,
    )
    select_calls = [
        c for c in mgr.hass.services.async_call.call_args_list
        if c.args[0] == "select" and c.args[1] == "select_option"
    ]
    assert len(select_calls) == 1
    assert select_calls[0].args[2]["option"] == "remote_temperature"
    assert any(c.args[0] == "number" and c.args[2]["value"] == 19.8 for c in mgr.hass.services.async_call.call_args_list)

    # 2. Sensor fault / timeout -> safety_fallback_active=True switches back to local_temperature and stops pushing
    sel_state.state = "remote_temperature"
    mgr.hass.services.async_call.reset_mock()
    await mgr.async_external_temp_heartbeat(
        master_current_temp=19.8,
        safety_fallback_active=True,
        has_external_sensor=True,
    )
    assert len(mgr.hass.services.async_call.call_args_list) == 1
    assert mgr.hass.services.async_call.call_args.args[0] == "select"
    assert mgr.hass.services.async_call.call_args.args[2]["option"] == "local_temperature"
    assert "climate.sonoff_trv" not in mgr._last_ext_temp_push

    # 3. Sensor recovers -> switches back to remote_temperature and pushes fresh reading
    sel_state.state = "local_temperature"
    ext_state.state = "20.2"
    mgr.hass.services.async_call.reset_mock()
    await mgr.async_sync_trvs(
        master_hvac_mode=HVACMode.HEAT,
        master_target_temp=20.0,
        master_current_temp=20.2,
        safety_fallback_active=False,
        has_external_sensor=True,
    )
    select_calls2 = [
        c for c in mgr.hass.services.async_call.call_args_list
        if c.args[0] == "select" and c.args[1] == "select_option"
    ]
    number_calls2 = [
        c for c in mgr.hass.services.async_call.call_args_list
        if c.args[0] == "number" and c.args[1] == "set_value"
    ]
    assert len(select_calls2) == 1 and select_calls2[0].args[2]["option"] == "remote_temperature"
    assert len(number_calls2) == 1 and number_calls2[0].args[2]["value"] == 20.2


def test_parse_trv_calibration_input_and_config_options_flows():
    """Verify parse_trv_calibration_input and ConfigFlow/OptionsFlow persist calibration mode and sensor selects."""
    calibs, selects = parse_trv_calibration_input(
        {
            "climate.trv_a": "number.trv_a_external_temperature_input",
            f"climate.trv_a{TRV_SENSOR_SELECT_SUFFIX}": "select.trv_a_temperature_sensor_select",
            "climate.removed_trv": "number.old_cal",
            f"climate.removed_trv{TRV_SENSOR_SELECT_SUFFIX}": "select.old_sel",
            "climate.trv_b": None,
        },
        climates=["climate.trv_a", "climate.trv_b"],
    )
    assert calibs == {"climate.trv_a": "number.trv_a_external_temperature_input"}
    assert selects == {"climate.trv_a": "select.trv_a_temperature_sensor_select"}

    saved_meta, saved_mods = _setup_clean_ha_environment()
    try:
        from custom_components.multizone_thermostat.config_flow import (
            MultizoneConfigFlow,
            MultizoneOptionsFlow,
        )
        from custom_components.multizone_thermostat.config_flow.schemas import (
            get_add_zone_schema,
            get_options_edit_zone_schema,
            get_options_trv_calibration_edit_schema,
        )

        # Schemas expose trv_calibration_mode and sensor_select
        add_schema = get_add_zone_schema()
        assert CONF_ZONE_TRV_CALIBRATION_MODE in add_schema.schema["trv_settings"].schema

        # Config flow add_zone -> trv_calibration
        flow = MultizoneConfigFlow()
        flow.hass = MagicMock()
        flow.async_show_form = MagicMock(return_value={"type": "form"})

        async def _run_cfg():
            res1 = await flow.async_step_add_zone({
                CONF_ZONE_NAME: "Studio",
                CONF_ZONE_TEMP_SENSOR: "sensor.studio_temp",
                "trv_settings": {
                    CONF_ZONE_CLIMATES: ["climate.sonoff_studio"],
                    CONF_ZONE_TRV_CALIBRATION_MODE: TRV_CALIB_MODE_EXTERNAL,
                },
            })
            assert res1["type"] == "form"
            return await flow.async_step_trv_calibration({
                "climate.sonoff_studio": "number.sonoff_studio_external_temperature_input",
                f"climate.sonoff_studio{TRV_SENSOR_SELECT_SUFFIX}": "select.sonoff_studio_temperature_sensor_select",
            })

        asyncio.run(_run_cfg())
        assert len(flow._zones) == 1
        zone = flow._zones[0]
        assert zone[CONF_ZONE_TRV_CALIBRATION_MODE] == TRV_CALIB_MODE_EXTERNAL
        assert zone[CONF_ZONE_CALIBRATIONS] == {
            "climate.sonoff_studio": "number.sonoff_studio_external_temperature_input"
        }
        assert zone[CONF_ZONE_TRV_SENSOR_SELECTS] == {
            "climate.sonoff_studio": "select.sonoff_studio_temperature_sensor_select"
        }

        # Options flow edit_zone -> trv_calibration_edit
        opt_flow = MultizoneOptionsFlow()
        opt_flow.hass = MagicMock()
        opt_flow.config_entry = MagicMock()
        opt_flow.config_entry.data = {}
        opt_flow.config_entry.options = {}
        opt_flow._zones = [dict(zone)]
        opt_flow._current_zone_name = "Studio"
        opt_flow._save_options = MagicMock(return_value={"type": "create_entry"})
        opt_flow.async_show_form = MagicMock(return_value={"type": "form"})

        edit_schema = get_options_edit_zone_schema(zone, {}, {})
        assert CONF_ZONE_TRV_CALIBRATION_MODE in edit_schema.schema["trv_settings"].schema
        cal_edit_schema = get_options_trv_calibration_edit_schema(zone)
        assert f"climate.sonoff_studio{TRV_SENSOR_SELECT_SUFFIX}" in cal_edit_schema.schema

        async def _run_opt_edit():
            step_res = await opt_flow.async_step_edit_zone({
                "trv_settings": {
                    CONF_ZONE_CLIMATES: ["climate.sonoff_studio"],
                    CONF_ZONE_TRV_CALIBRATION_MODE: TRV_CALIB_MODE_AUTO,
                },
                CONF_ZONE_TEMP_SENSOR: "sensor.studio_temp",
            })
            assert step_res["type"] == "form"
            return await opt_flow.async_step_trv_calibration_edit({
                "climate.sonoff_studio": "number.sonoff_studio_external_temperature_input",
                f"climate.sonoff_studio{TRV_SENSOR_SELECT_SUFFIX}": "select.sonoff_studio_temperature_sensor_select",
            })

        opt_res = asyncio.run(_run_opt_edit())
        assert opt_res == {"type": "create_entry"}
        edited = opt_flow._zones[0]
        assert edited[CONF_ZONE_TRV_CALIBRATION_MODE] == TRV_CALIB_MODE_AUTO
        assert edited[CONF_ZONE_TRV_SENSOR_SELECTS] == {
            "climate.sonoff_studio": "select.sonoff_studio_temperature_sensor_select"
        }
    finally:
        _restore_ha_environment(saved_meta, saved_mods)


@pytest.mark.asyncio
async def test_climate_entity_wires_trv_calibration_mode_selects_and_heartbeat():
    """Verify MultizoneVirtualThermostat passes trv_calibration_mode and trv_sensor_selects and runs heartbeat tick."""
    from custom_components.multizone_thermostat.climate import MultizoneVirtualThermostat
    from custom_components.multizone_thermostat.const import DOMAIN

    hass = MagicMock()
    coord = MagicMock()
    coord.boiler_switch = "switch.boiler"
    coord.get_zone_mode.return_value = "primary"
    coord.demand_aggregator.get_zone_weight.return_value = 1.0
    coord.zone_manager.is_passive_heat_allowed.return_value = False
    coord.plant_diagnostics = MagicMock()
    coord.plant_diagnostics.get_zone_battery_level.return_value = None
    coord.schedule_manager = None
    coord.master_device_id = "master_dev"
    coord.get_autotuner.return_value = None
    hass.data = {DOMAIN: {"entry_1": {"coordinator": coord}}}

    zone_data = {
        CONF_ZONE_NAME: "Studio",
        CONF_ZONE_CLIMATES: ["climate.sonoff_trv"],
        CONF_ZONE_TEMP_SENSOR: "sensor.studio_temp",
        CONF_ZONE_CALIBRATIONS: {"climate.sonoff_trv": "number.sonoff_external_temperature_input"},
        CONF_ZONE_TRV_CALIBRATION_MODE: TRV_CALIB_MODE_EXTERNAL,
        CONF_ZONE_TRV_SENSOR_SELECTS: {"climate.sonoff_trv": "select.sonoff_temperature_sensor_select"},
    }

    entity = MultizoneVirtualThermostat(hass=hass, entry_id="entry_1", zone_data=zone_data)
    assert entity._sync_manager._calibration_mode == TRV_CALIB_MODE_EXTERNAL
    assert entity._sync_manager._trv_sensor_selects == {
        "climate.sonoff_trv": "select.sonoff_temperature_sensor_select"
    }

    attrs = entity.extra_state_attributes
    assert attrs["trv_calibration_mode"] == TRV_CALIB_MODE_EXTERNAL
    assert attrs["trv_sensor_selects"] == {
        "climate.sonoff_trv": "select.sonoff_temperature_sensor_select"
    }

    entity._current_temperature = 20.5
    entity._safety_fallback_active = False
    entity.check_sensor_staleness = MagicMock(return_value=False)
    entity._sync_manager.async_external_temp_heartbeat = AsyncMock()

    await entity._async_ext_temp_heartbeat_tick(None)
    entity.check_sensor_staleness.assert_called_once()
    entity._sync_manager.async_external_temp_heartbeat.assert_awaited_once_with(
        master_current_temp=20.5,
        safety_fallback_active=False,
        has_external_sensor=True,
    )
