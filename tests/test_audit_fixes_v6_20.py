"""Regression tests for audit findings on master (hysteresis collapse, full Fahrenheit I/O, anti-seize, migration)."""
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.components.climate import HVACMode

from custom_components.multizone_thermostat import async_migrate_entry
from custom_components.multizone_thermostat.boiler.opentherm_backend import OpenThermBoilerBackend
from custom_components.multizone_thermostat.boiler.relay_backend import RelayBoilerBackend
from custom_components.multizone_thermostat.const import (
    CONF_BOILER_MODE,
    CONF_ZONE_NAME,
    CONF_ZONES,
    HVAC_MODE_HEAT,
    KEY_ANTI_FROST_ENABLED,
    KEY_FROST_PROTECTION_TEMP,
    KEY_PHYSICAL_SYNC_PREFIX,
    MODE_RELAY,
    from_celsius,
    make_zone_entity_id,
)
from custom_components.multizone_thermostat.safety.anti_seize import (
    ANTI_SEIZE_MODULATING_DEMAND,
    AntiSeizeManager,
)
from custom_components.multizone_thermostat.safety.frost import FrostManager
from custom_components.multizone_thermostat.sync_manager import ZoneSyncManager
from custom_components.multizone_thermostat.zone_controller import ZoneController


def _make_fahrenheit_hass(states_map=None):
    hass = MagicMock()
    hass.config.units.temperature_unit = "°F"
    hass.services.async_call = AsyncMock()
    states = dict(states_map or {})
    hass.states.get = MagicMock(side_effect=lambda eid: states.get(eid))
    return hass, states


@pytest.mark.asyncio
async def test_hysteresis_band_does_not_collapse_with_high_inertia():
    """Hysteresis learning keeps at least 0.3C band even when thermal_inertia >= 0.55C."""
    hass = MagicMock()
    demands = {}
    coord = MagicMock()
    coord.zones = [{"name": "Salotto"}]
    coord.demand_aggregator = MagicMock()
    coord.demand_aggregator.get_zone_demand = MagicMock(side_effect=lambda cid: demands.get(cid, 0.0))
    coord.demand_aggregator.set_zone_demand = MagicMock(side_effect=lambda cid, d: demands.update({cid: d}))
    coord.get_zone_mode = MagicMock(return_value="primary")
    coord.plant_diagnostics = MagicMock()
    coord.plant_diagnostics.has_critical_sensor_fault = MagicMock(return_value=False)
    coord.weather_sensor_id = None
    coord.is_dhw_active = False

    zc = ZoneController(hass, coord)
    cid = make_zone_entity_id("Salotto")

    for inertia in (0.55, 1.0):
        demands.clear()
        zc.get_thermal_model(cid).thermal_inertia = inertia

        d_on = await zc.async_update_zone(
            cid, SimpleNamespace(state="heat", attributes={"current_temperature": 19.70, "temperature": 20.0})
        )
        assert d_on == 100.0

        d_hold_low = await zc.async_update_zone(
            cid, SimpleNamespace(state="heat", attributes={"current_temperature": 19.75, "temperature": 20.0})
        )
        d_hold_high = await zc.async_update_zone(
            cid, SimpleNamespace(state="heat", attributes={"current_temperature": 19.95, "temperature": 20.0})
        )
        assert d_hold_low == 100.0
        assert d_hold_high == 100.0

        d_off = await zc.async_update_zone(
            cid, SimpleNamespace(state="heat", attributes={"current_temperature": 20.0, "temperature": 20.0})
        )
        assert d_off == 0.0


@pytest.mark.asyncio
async def test_fahrenheit_opentherm_inbound_and_outbound():
    """OpenTherm converts outdoor F sensor to C and sends F setpoints to climate (and F number if entity uses F)."""
    states = {
        "weather.home": SimpleNamespace(
            state="cloudy",
            domain="weather",
            attributes={"temperature": 32.0, "temperature_unit": "°F"},
        ),
        "climate.ot_boiler": SimpleNamespace(state="heat", attributes={"temperature": 80.0}),
        "number.ot_ch_c": SimpleNamespace(state="40.0", attributes={"unit_of_measurement": "°C", "min": 0.0}),
        "number.ot_ch_f": SimpleNamespace(state="100.0", attributes={"unit_of_measurement": "°F", "min": 0.0}),
    }
    hass, _ = _make_fahrenheit_hass(states)
    coord = MagicMock()
    coord.weather_sensor_id = "weather.home"
    coord._thermal_models = {}
    coord.get_persistent_data = MagicMock(side_effect=lambda k, d=None: 1.0 if k == "weather_curve" else d)
    coord.plant_diagnostics = None

    ot = OpenThermBoilerBackend(hass, coord, "climate.ot_boiler", 35.0, 75.0)
    await ot.async_update(50.0, "Salotto", False)
    set_temp_calls = [
        c for c in hass.services.async_call.call_args_list if c.args[1] == "set_temperature"
    ]
    assert len(set_temp_calls) == 1
    assert set_temp_calls[0].args[2]["temperature"] > 95.0

    hass.services.async_call.reset_mock()
    ot_num_c = OpenThermBoilerBackend(hass, coord, "number.ot_ch_c", 35.0, 75.0)
    await ot_num_c.async_update(50.0, "Salotto", False)
    val_c = hass.services.async_call.call_args_list[0].args[2]["value"]
    assert 35.0 <= val_c <= 75.0

    hass.services.async_call.reset_mock()
    ot_num_f = OpenThermBoilerBackend(hass, coord, "number.ot_ch_f", 35.0, 75.0)
    await ot_num_f.async_update(50.0, "Salotto", False)
    val_f = hass.services.async_call.call_args_list[0].args[2]["value"]
    assert val_f > 95.0


@pytest.mark.asyncio
async def test_fahrenheit_frost_manager_sends_fahrenheit_not_8f():
    """FrostManager converts TRV fallback F -> C and sends frost target in F."""
    cid = make_zone_entity_id("Cantina")
    states = {
        cid: SimpleNamespace(state=HVAC_MODE_HEAT, attributes={"temperature": 68.0}),
        "climate.trv_cantina": SimpleNamespace(state=HVAC_MODE_HEAT, attributes={"current_temperature": 41.0}),  # 5°C
    }
    hass, _ = _make_fahrenheit_hass(states)
    coord = MagicMock()
    coord.zones = [{CONF_ZONE_NAME: "Cantina", "climate_entities": ["climate.trv_cantina"]}]
    coord.zone_manager.get_zone.return_value = coord.zones[0]
    coord.plant_diagnostics.has_critical_sensor_fault.return_value = False
    coord._async_set_hvac_mode = AsyncMock()
    coord.get_persistent_data = MagicMock(
        side_effect=lambda k, d=None: (
            True if k == KEY_ANTI_FROST_ENABLED else (8.0 if k == KEY_FROST_PROTECTION_TEMP else d)
        )
    )

    fm = FrostManager(hass, coord)
    assert await fm.async_handle_frost_emergencies() is True

    # 8.0°C + 3.0°C = 11.0°C -> 51.8°F
    call_args = hass.services.async_call.call_args_list[0].args
    assert call_args[1] == "set_temperature"
    assert call_args[2]["temperature"] == pytest.approx(from_celsius(11.0, unit="°F"), abs=0.1)


@pytest.mark.asyncio
async def test_fahrenheit_sync_manager_outbound_and_inbound_delta():
    """ZoneSyncManager sends TRV targets in F and computes knob delta in C."""
    cid = make_zone_entity_id("Cucina")
    trv = "climate.trv_cucina"
    states = {
        trv: SimpleNamespace(
            state=HVACMode.HEAT,
            attributes={
                "temperature": 66.0,
                "current_temperature": 66.0,
                "min_temp": 41.0,
                "max_temp": 95.0,
                "target_temp_step": 0.5,
            },
        )
    }
    hass, _ = _make_fahrenheit_hass(states)
    coord = MagicMock()
    coord.get_persistent_data = MagicMock(side_effect=lambda k, d=None: True if k.startswith(KEY_PHYSICAL_SYNC_PREFIX) else d)

    mgr = ZoneSyncManager(hass, coord, "Cucina", cid, [trv], [], {})
    await mgr.async_sync_trvs(HVACMode.HEAT, 20.0, 19.0, False, False)
    sent_calls = [c for c in hass.services.async_call.call_args_list if c.args[1] == "set_temperature"]
    assert len(sent_calls) == 1
    assert sent_calls[0].args[2]["temperature"] == pytest.approx(68.0, abs=0.1)

    confirm_evt = SimpleNamespace(
        context=SimpleNamespace(id="ext"),
        data={
            "entity_id": trv,
            "old_state": SimpleNamespace(state=HVACMode.HEAT, attributes={"temperature": 66.0}),
            "new_state": SimpleNamespace(state=HVACMode.HEAT, attributes={"temperature": 68.0}),
        },
    )
    assert await mgr.process_trv_change(confirm_evt, "master_ctx", HVACMode.HEAT, 5.0, 35.0) == (None, None)

    knob_evt = SimpleNamespace(
        context=SimpleNamespace(id="user_ctx"),
        data={
            "entity_id": trv,
            "old_state": SimpleNamespace(state=HVACMode.HEAT, attributes={"temperature": 68.0}),
            "new_state": SimpleNamespace(state=HVACMode.HEAT, attributes={"temperature": 69.8}),
        },
    )
    _, delta_c = await mgr.process_trv_change(knob_evt, "master_ctx", HVACMode.HEAT, 5.0, 35.0)
    assert delta_c == pytest.approx(1.0, abs=0.05)


@pytest.mark.asyncio
async def test_anti_seize_uses_low_demand_for_modulating_backends():
    """Anti-seize commands minimum flow (5%) on modulating backends and 100% on relay boilers."""
    hass = MagicMock()
    coord = MagicMock()

    ot = OpenThermBoilerBackend(hass, coord, "climate.ot", 35.0, 75.0)
    ot.is_modulating = True
    ot.async_update = AsyncMock()
    coord.boiler_backend = ot
    mgr = AntiSeizeManager(hass, coord)
    await mgr._turn_boiler_on()
    ot.async_update.assert_awaited_once_with(ANTI_SEIZE_MODULATING_DEMAND, "Anti-Seize", False)

    relay = RelayBoilerBackend(hass, coord, "switch.boiler", 3, 3, 0)
    relay.async_update = AsyncMock()
    coord.boiler_backend = relay
    await mgr._turn_boiler_on()
    relay.async_update.assert_awaited_once_with(100.0, "Anti-Seize", False)


@pytest.mark.asyncio
async def test_async_migrate_entry_v1_to_v2():
    """async_migrate_entry upgrades legacy v1 config entries cleanly to v2."""
    hass = MagicMock()
    hass.config_entries.async_update_entry = MagicMock()
    entry = SimpleNamespace(
        version=1,
        data={
            "virtual_thermostats": [{"name": "Bagno", "heater_switch": "switch.bagno", "temperature_sensor": "sensor.t"}],
            CONF_ZONES: [{"name": "Salotto", "climate_entity": "climate.trv_salotto"}],
        },
        options={},
    )

    assert await async_migrate_entry(hass, entry) is True
    hass.config_entries.async_update_entry.assert_called_once()
    kwargs = hass.config_entries.async_update_entry.call_args.kwargs
    assert kwargs["version"] == 2
    migrated = kwargs["data"]
    assert "virtual_thermostats" not in migrated
    assert migrated[CONF_BOILER_MODE] == MODE_RELAY
    assert len(migrated[CONF_ZONES]) == 2
    assert migrated[CONF_ZONES][0]["climate_entities"] == ["climate.trv_salotto"]
    assert migrated[CONF_ZONES][1]["switch_entities"] == ["switch.bagno"]
