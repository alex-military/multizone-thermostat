"""Logic to restore the MultizoneVirtualThermostat state across reboots."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.climate import HVACMode
from homeassistant.const import ATTR_TEMPERATURE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.restore_state import RestoreEntity

_LOGGER = logging.getLogger(__name__)

class ZoneStateRestorer:
    """Handles restoring the virtual thermostat state from HA storage."""

    @staticmethod
    async def async_restore_state(
        entity: RestoreEntity,
        default_hvac_mode: HVACMode = HVACMode.OFF,
        default_target_temp: float = 20.0
    ) -> tuple[HVACMode, float]:
        """
        Fetch the last state from HA's RestoreEntity facility.
        Returns a tuple of (hvac_mode, target_temperature).
        """
        hvac_mode = default_hvac_mode
        target_temp = default_target_temp

        last_state = await entity.async_get_last_state()
        if last_state is not None:
            if last_state.state in (HVACMode.HEAT, HVACMode.OFF):
                hvac_mode = HVACMode(last_state.state)
            if last_state.attributes.get(ATTR_TEMPERATURE) is not None:
                try:
                    target_temp = float(last_state.attributes[ATTR_TEMPERATURE])
                except (ValueError, TypeError):
                    _LOGGER.warning(
                        "Could not restore target temperature %s, falling back to %s",
                        last_state.attributes.get(ATTR_TEMPERATURE),
                        default_target_temp
                    )

        return hvac_mode, target_temp
