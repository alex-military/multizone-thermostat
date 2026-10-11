"""Regression: sensor going unknown/unavailable triggers immediate TRV fallback (roadmap 1.2)."""
from unittest.mock import MagicMock

import pytest

from custom_components.multizone_thermostat.climate import MultizoneVirtualThermostat as Z


def _make_zone(sensor_state: str, trv_temp: float):
    zone = MagicMock()
    zone._name = "z"
    zone._temp_sensor = "sensor.t"
    zone._climates = ["climate.trv1"]
    zone._sensor_timeout_min = 30
    zone._safety_fallback_active = False
    zone._current_temperature = 21.0

    states = {
        "sensor.t": MagicMock(state=sensor_state),
        "climate.trv1": MagicMock(state="heat", attributes={"current_temperature": trv_temp}),
    }
    zone.hass.states.get.side_effect = states.get
    zone._update_current_temp = lambda: Z._update_current_temp(zone)
    return zone


@pytest.mark.parametrize("bad", ["unavailable", "unknown"])
def test_invalid_sensor_state_triggers_immediate_fallback(bad):
    zone = _make_zone(bad, trv_temp=18.5)
    event = MagicMock()
    event.data = {"new_state": MagicMock(state=bad)}

    Z._on_temp_changed(zone, event)

    assert zone._safety_fallback_active is True
    assert zone._current_temperature == pytest.approx(18.5)
    zone.async_write_ha_state.assert_called_once()


def test_valid_sensor_state_does_not_use_fallback():
    zone = _make_zone("20.0", trv_temp=18.5)
    event = MagicMock()
    event.data = {"new_state": MagicMock(state="20.0")}

    Z._on_temp_changed(zone, event)

    assert zone._safety_fallback_active is False
    assert zone._current_temperature == pytest.approx(20.0)
