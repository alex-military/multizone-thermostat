"""OpenTherm boiler backend."""
import logging

from homeassistant.core import HomeAssistant
from .base import BoilerBackend

_LOGGER = logging.getLogger(__name__)

class OpenThermBoilerBackend(BoilerBackend):
    """Handles OpenTherm modulating boilers."""

    def __init__(
        self,
        hass: HomeAssistant,
        coordinator,
        opentherm_entity: str,
        min_temp: float,
        max_temp: float,
    ) -> None:
        """Initialize OpenTherm backend."""
        self.hass = hass
        self.coordinator = coordinator
        self.opentherm_entity = opentherm_entity
        self.opentherm_min_temp = min_temp
        self.opentherm_max_temp = max_temp
        self._status_reason = "INIT"

    @property
    def status_reason(self) -> str:
        """Return the current status reason."""
        return self._status_reason

    async def async_update(self, demand: float, peak_zone: str | None, frost_emergency: bool) -> None:
        """Map demand to OpenTherm target temperature."""
        if not self.opentherm_entity:
            return

        # Normalize demand from 0-100 to 0.0-1.0 and clamp
        norm_demand = max(0.0, min(1.0, demand / 100.0))

        target_temp = self.opentherm_min_temp + (norm_demand * (self.opentherm_max_temp - self.opentherm_min_temp))
        target_temp = round(target_temp, 1)

        domain = self.opentherm_entity.split(".")[0]

        _LOGGER.debug("OpenTherm: Demand %.1f%% -> Target Water Temp: %.1f°C", norm_demand * 100, target_temp)
        self.coordinator.plant_diagnostics.record_boiler_state(norm_demand > 0.0)

        self._status_reason = f"MODULATING - Target water: {target_temp}°C (Demand: {round(demand, 1)}% from {peak_zone or 'None'})"

        try:
            st = self.hass.states.get(self.opentherm_entity)
            if domain in ["climate", "water_heater"]:
                current_target = st.attributes.get("temperature") if st else None
                if current_target != target_temp:
                    await self.hass.services.async_call(
                        domain,
                        "set_temperature",
                        {"entity_id": self.opentherm_entity, "temperature": target_temp},
                        blocking=False,
                    )

                # Turn OFF if demand is 0, otherwise HEAT
                if domain == "climate":
                    hvac_mode = "off" if norm_demand <= 0.0 else "heat"
                    current_mode = st.state if st else None
                    if current_mode != hvac_mode:
                        await self.hass.services.async_call(
                            "climate",
                            "set_hvac_mode",
                            {"entity_id": self.opentherm_entity, "hvac_mode": hvac_mode},
                            blocking=False,
                        )
            elif domain == "number":
                current_val = float(st.state) if st and st.state not in ("unknown", "unavailable") else None
                if current_val != target_temp:
                    await self.hass.services.async_call(
                        "number",
                        "set_value",
                        {"entity_id": self.opentherm_entity, "value": target_temp},
                        blocking=False,
                    )
        except Exception as err:
            _LOGGER.error("Failed to update OpenTherm entity %s: %s", self.opentherm_entity, err)

    async def async_emergency_off(self) -> None:
        """Force OpenTherm boiler off immediately."""
        self._status_reason = "OFF - Emergency/Master OFF"
        await self.async_update(0.0, None, False)
