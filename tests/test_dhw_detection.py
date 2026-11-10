"""Tests for Domestic Hot Water (DHW / ACS) detection and Issue #10 fixes."""
import sys
import types
from unittest.mock import MagicMock, patch
import pytest

import homeassistant
if "homeassistant.data_entry_flow" not in sys.modules:
    data_entry_flow_mod = types.ModuleType("homeassistant.data_entry_flow")
    data_entry_flow_mod.section = lambda s, o=None: s
    sys.modules["homeassistant.data_entry_flow"] = data_entry_flow_mod
    homeassistant.data_entry_flow = data_entry_flow_mod

from custom_components.multizone_thermostat.const import (
    CONF_BOILER_MODE,
    CONF_BOILER_SWITCH,
    CONF_OPENTHERM_ENTITY,
    CONF_OPENTHERM_MIN_TEMP,
    CONF_OPENTHERM_MAX_TEMP,
    CONF_DHW_ACTIVE_SENSOR,
    MODE_RELAY,
    MODE_OPENTHERM,
)
from custom_components.multizone_thermostat.coordinator import MultizoneCoordinator
from custom_components.multizone_thermostat.plant_diagnostics.anomalies import (
    get_opentherm_diagnostics,
    find_suggested_dhw_sensor,
)
from custom_components.multizone_thermostat.config_flow.options_flow import MultizoneOptionsFlow


class DummyState:
    def __init__(self, state: str, attributes: dict | None = None):
        self.state = state
        self.attributes = attributes or {}


class DummyRegistryEntry:
    def __init__(self, entity_id: str, device_id: str | None = None, config_entry_id: str | None = None, domain: str = "binary_sensor"):
        self.entity_id = entity_id
        self.device_id = device_id
        self.config_entry_id = config_entry_id
        self.domain = domain
        self.original_device_class = None
        self.device_class = None


def test_dhw_detection_explicit_sensor_binary_and_sensor_states():
    """Verify explicit dhw_active_sensor takes priority and parses binary/text states."""
    hass = MagicMock()
    states_map = {
        "binary_sensor.my_custom_dhw": DummyState("on"),
    }
    hass.states.get = MagicMock(side_effect=lambda eid: states_map.get(eid))

    entry = MagicMock()
    entry.entry_id = "test_entry"
    entry.data = {
        CONF_BOILER_MODE: MODE_RELAY,
        CONF_BOILER_SWITCH: "switch.boiler",
        CONF_DHW_ACTIVE_SENSOR: "binary_sensor.my_custom_dhw",
    }
    entry.options = {}

    coord = MultizoneCoordinator(hass, entry)
    assert coord.is_dhw_active is True

    # State turns off
    states_map["binary_sensor.my_custom_dhw"] = DummyState("off")
    assert coord.is_dhw_active is False

    # Text sensor states: charging, heat, active
    for st_val in ("charging", "heat", "heating", "active", "true", "1"):
        states_map["binary_sensor.my_custom_dhw"] = DummyState(st_val)
        assert coord.is_dhw_active is True

    # Idle / off states
    for st_val in ("idle", "off", "standby", "false", "0"):
        states_map["binary_sensor.my_custom_dhw"] = DummyState(st_val)
        assert coord.is_dhw_active is False


def test_dhw_detection_ems_esp_multi_device_discovery():
    """Verify auto-discovery finds EMS-ESP boiler_dhw_charging across companion devices under same config_entry."""
    hass = MagicMock()
    states_map = {
        "climate.boiler_thermostat": DummyState("heat", {"current_temperature": 21.0}),
        "binary_sensor.boiler_dhw_charging": DummyState("on"),
    }
    hass.states.get = MagicMock(side_effect=lambda eid: states_map.get(eid))

    # Entity registry setup:
    # climate.boiler_thermostat is on device_thermostat
    # binary_sensor.boiler_dhw_charging is on device_boiler
    # BOTH belong to config_entry "ems_esp_gateway_123"
    ent_thermostat = DummyRegistryEntry("climate.boiler_thermostat", device_id="dev_thermostat", config_entry_id="ems_esp_123", domain="climate")
    ent_dhw = DummyRegistryEntry("binary_sensor.boiler_dhw_charging", device_id="dev_boiler", config_entry_id="ems_esp_123", domain="binary_sensor")

    ent_reg = MagicMock()
    ent_reg.async_get = MagicMock(side_effect=lambda eid: ent_thermostat if eid == "climate.boiler_thermostat" else None)
    ent_reg.async_entries_for_device = MagicMock(side_effect=lambda reg, did: [ent_thermostat] if did == "dev_thermostat" else [ent_dhw])
    ent_reg.async_entries_for_config_entry = MagicMock(side_effect=lambda reg, cid: [ent_thermostat, ent_dhw] if cid == "ems_esp_123" else [])

    coord = MagicMock()
    coord.opentherm_entity = "climate.boiler_thermostat"
    coord.dhw_active_sensor = None

    with patch("homeassistant.helpers.entity_registry.async_get", return_value=ent_reg):
        diag = get_opentherm_diagnostics(coord, hass)
        assert diag["dhw_active"] is True

        # When DHW cycle finishes (charging goes off)
        states_map["binary_sensor.boiler_dhw_charging"] = DummyState("off")
        diag2 = get_opentherm_diagnostics(coord, hass)
        assert diag2["dhw_active"] is False


def test_dhw_detection_prevention_of_false_positive_activated():
    """Verify binary_sensor.boiler_dhw_activated (hardware enabled flag) does NOT trigger false DHW active."""
    hass = MagicMock()
    states_map = {
        "climate.boiler_thermostat": DummyState("heat"),
        # Setting is ON in boiler settings, but NO hot water is being drawn/charged!
        "binary_sensor.boiler_dhw_activated": DummyState("on"),
    }
    hass.states.get = MagicMock(side_effect=lambda eid: states_map.get(eid))

    ent_thermostat = DummyRegistryEntry("climate.boiler_thermostat", device_id="dev_boiler", config_entry_id="ot_1", domain="climate")
    ent_setting = DummyRegistryEntry("binary_sensor.boiler_dhw_activated", device_id="dev_boiler", config_entry_id="ot_1", domain="binary_sensor")

    ent_reg = MagicMock()
    ent_reg.async_get = MagicMock(return_value=ent_thermostat)
    ent_reg.async_entries_for_device = MagicMock(return_value=[ent_thermostat, ent_setting])
    ent_reg.async_entries_for_config_entry = MagicMock(return_value=[ent_thermostat, ent_setting])

    coord = MagicMock()
    coord.opentherm_entity = "climate.boiler_thermostat"
    coord.dhw_active_sensor = None

    with patch("homeassistant.helpers.entity_registry.async_get", return_value=ent_reg):
        diag = get_opentherm_diagnostics(coord, hass)
        # MUST BE FALSE! The boiler is not charging DHW, dhw_activated is just a configuration setting!
        assert diag["dhw_active"] is False


def test_dhw_fallback_detection_in_relay_mode():
    """Verify coordinator detects standard EMS-ESP DHW charging entity even in Relay mode with zero config."""
    hass = MagicMock()
    states_map = {
        "switch.boiler_relay": DummyState("on"),
        "binary_sensor.boiler_dhw_charging": DummyState("on"),
    }
    hass.states.get = MagicMock(side_effect=lambda eid: states_map.get(eid))

    entry = MagicMock()
    entry.entry_id = "relay_entry"
    entry.data = {
        CONF_BOILER_MODE: MODE_RELAY,
        CONF_BOILER_SWITCH: "switch.boiler_relay",
    }
    entry.options = {}

    coord = MultizoneCoordinator(hass, entry)
    assert coord.is_dhw_active is True

    states_map["binary_sensor.boiler_dhw_charging"] = DummyState("off")
    assert coord.is_dhw_active is False


def test_find_suggested_dhw_sensor_helper():
    """Verify find_suggested_dhw_sensor identifies well-known candidates."""
    hass = MagicMock()
    states_map = {
        "binary_sensor.boiler_dhw_charging": DummyState("off"),
    }
    hass.states.get = MagicMock(side_effect=lambda eid: states_map.get(eid))

    suggested = find_suggested_dhw_sensor(hass)
    assert suggested == "binary_sensor.boiler_dhw_charging"

    # None if no match
    states_map.clear()
    assert find_suggested_dhw_sensor(hass) is None


@pytest.mark.asyncio
async def test_options_flow_dhw_active_sensor_roundtrip():
    """Verify options flow saves dhw_active_sensor properly into config entry options."""
    flow = MultizoneOptionsFlow()
    hass = MagicMock()
    flow.hass = hass
    entry = MagicMock()
    entry.entry_id = "entry_dhw"
    entry.data = {
        CONF_BOILER_MODE: MODE_OPENTHERM,
        CONF_OPENTHERM_ENTITY: "climate.my_boiler",
        CONF_OPENTHERM_MIN_TEMP: 35.0,
        CONF_OPENTHERM_MAX_TEMP: 75.0,
    }
    entry.options = {}
    entry.update_listeners = [MagicMock()]
    flow.config_entry = entry

    flow.async_create_entry = MagicMock(side_effect=lambda title, data: {"type": "create_entry", "data": data})
    flow.async_show_form = MagicMock(side_effect=lambda step_id, data_schema, **kwargs: {"type": "form", "step_id": step_id})

    # Step init
    await flow.async_step_init()
    assert flow._dhw_active_sensor is None

    # Step boiler_opentherm with DHW sensor input
    res = await flow.async_step_boiler_opentherm({
        CONF_OPENTHERM_ENTITY: "climate.my_boiler",
        CONF_OPENTHERM_MIN_TEMP: 35.0,
        CONF_OPENTHERM_MAX_TEMP: 75.0,
        CONF_DHW_ACTIVE_SENSOR: "binary_sensor.boiler_dhw_charging",
    })

    assert res["type"] == "create_entry"
    update_data = hass.config_entries.async_update_entry.call_args[1]["data"]
    assert update_data[CONF_DHW_ACTIVE_SENSOR] == "binary_sensor.boiler_dhw_charging"
