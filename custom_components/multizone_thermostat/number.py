"""Number platform for Multizone Thermostat."""
from __future__ import annotations

import logging

from homeassistant.components.number import NumberEntity, RestoreNumber
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .const import (
    CONF_MIN_CYCLE_ON,
    CONF_MIN_CYCLE_OFF,
    CONF_VALVE_DELAY,
    DEFAULT_MIN_CYCLE_ON,
    DEFAULT_MIN_CYCLE_OFF,
    DEFAULT_VALVE_DELAY,
    DOMAIN,
    KEY_ANTI_SEIZE_IDLE_DAYS,
    KEY_ANTI_SEIZE_DURATION,
    KEY_WEATHER_CURVE,
    CONF_VIRTUAL_THERMOSTATS,
    CONF_VT_NAME,
    CONF_VT_PRESET_TEMPS_SUMMER,
    CONF_VT_PRESET_TEMPS_WINTER,
    SEASON_SUMMER,
    SEASON_WINTER,
    GLOBAL_PRESETS,
    DEFAULT_SUMMER_PRESET_TEMPS,
    DEFAULT_WINTER_PRESET_TEMPS,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up number entities."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]["coordinator"]

    def _make_device_info() -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, config_entry.entry_id)},
            name="Multizone Thermostat",
            manufacturer="Custom Integration",
            model="Multizone Thermostat",
        )

    device_info = _make_device_info()

    entities = [
        # Protection parameters
        MultizoneProtectionNumber(
            coordinator=coordinator,
            entry_id=config_entry.entry_id,
            key=CONF_MIN_CYCLE_ON,
            name="Min Cycle ON",
            min_value=0,
            max_value=60,
            step=1,
            unit_of_measurement="min",
            icon="mdi:timer-sand",
            default_val=DEFAULT_MIN_CYCLE_ON,
            device_info=device_info,
        ),
        MultizoneProtectionNumber(
            coordinator=coordinator,
            entry_id=config_entry.entry_id,
            key=CONF_MIN_CYCLE_OFF,
            name="Min Cycle OFF",
            min_value=0,
            max_value=60,
            step=1,
            unit_of_measurement="min",
            icon="mdi:timer-sand-empty",
            default_val=DEFAULT_MIN_CYCLE_OFF,
            device_info=device_info,
        ),
        MultizoneProtectionNumber(
            coordinator=coordinator,
            entry_id=config_entry.entry_id,
            key=CONF_VALVE_DELAY,
            name="Valve Delay",
            min_value=0,
            max_value=300,
            step=1,
            unit_of_measurement="s",
            icon="mdi:valve",
            default_val=DEFAULT_VALVE_DELAY,
            device_info=device_info,
        ),
        MultizonePersistentNumber(
            coordinator=coordinator,
            entry_id=config_entry.entry_id,
            key=KEY_ANTI_SEIZE_IDLE_DAYS,
            name="Anti-seize Idle Days",
            min_value=1,
            max_value=30,
            step=1,
            unit_of_measurement="days",
            icon="mdi:calendar-clock",
            default_val=15,
            device_info=device_info,
        ),
        MultizonePersistentNumber(
            coordinator=coordinator,
            entry_id=config_entry.entry_id,
            key=KEY_ANTI_SEIZE_DURATION,
            name="Anti-seize Duration",
            min_value=1,
            max_value=15,
            step=1,
            unit_of_measurement="min",
            icon="mdi:timer-outline",
            default_val=2,
            device_info=device_info,
        ),
        MultizonePersistentNumber(
            coordinator=coordinator,
            entry_id=config_entry.entry_id,
            key=KEY_WEATHER_CURVE,
            name="Weather Curve",
            min_value=0.0,
            max_value=3.0,
            step=0.1,
            unit_of_measurement="",
            icon="mdi:chart-bell-curve-cumulative",
            default_val=0.0,
            device_info=device_info,
        ),
    ]

    # Add preset temperature numbers for each virtual thermostat
    virtual_thermostats = config_entry.data.get(CONF_VIRTUAL_THERMOSTATS, [])
    for vt_config in virtual_thermostats:
        vt_name = vt_config[CONF_VT_NAME]
        safe_vt = vt_name.lower().replace(" ", "_").replace("-", "_")
        # Очищаем от недопустимых символов
        safe_vt = "".join(c for c in safe_vt if c.isalnum() or c == "_")
        summer_temps = vt_config.get(CONF_VT_PRESET_TEMPS_SUMMER, DEFAULT_SUMMER_PRESET_TEMPS)
        winter_temps = vt_config.get(CONF_VT_PRESET_TEMPS_WINTER, DEFAULT_WINTER_PRESET_TEMPS)
        
        # Уникальное устройство для этого VT
        vt_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{config_entry.entry_id}_vt_{safe_vt}")},
            name=f"{vt_name} Thermostat",
            manufacturer="Custom Integration",
            model="Virtual Thermostat",
            via_device=(DOMAIN, config_entry.entry_id),
        )
        
        # Сначала добавляем все летние пресеты
        for preset in GLOBAL_PRESETS:
            entities.append(
                PresetNumber(
                    hass,
                    config_entry.entry_id,
                    vt_name,
                    preset,
                    SEASON_SUMMER,
                    summer_temps.get(preset, DEFAULT_SUMMER_PRESET_TEMPS.get(preset, 20.0)),
                    vt_device_info,
                )
            )
        # Затем все зимние пресеты
        for preset in GLOBAL_PRESETS:
            entities.append(
                PresetNumber(
                    hass,
                    config_entry.entry_id,
                    vt_name,
                    preset,
                    SEASON_WINTER,
                    winter_temps.get(preset, DEFAULT_WINTER_PRESET_TEMPS.get(preset, 20.0)),
                    vt_device_info,
                )
            )

    async_add_entities(entities)


class MultizoneProtectionNumber(RestoreNumber):
    """Number entity to control boiler protection parameters."""

    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(
        self,
        coordinator,
        entry_id: str,
        key: str,
        name: str,
        min_value: float,
        max_value: float,
        step: float,
        unit_of_measurement: str,
        icon: str,
        default_val: float,
        device_info: DeviceInfo,
    ) -> None:
        """Initialize the number entity."""
        self._coordinator = coordinator
        self._key = key
        self._default_val = default_val

        self._attr_unique_id = f"{DOMAIN}_{entry_id}_{key}"
        self._attr_name = name
        self._attr_native_min_value = min_value
        self._attr_native_max_value = max_value
        self._attr_native_step = step
        self._attr_native_unit_of_measurement = unit_of_measurement
        self._attr_icon = icon
        self._attr_device_info = device_info

        self._attr_native_value = float(default_val)

    async def async_added_to_hass(self) -> None:
        """Restore previous state on startup."""
        await super().async_added_to_hass()
        last_number_data = await self.async_get_last_number_data()

        if last_number_data is not None and last_number_data.native_value is not None:
            self._attr_native_value = last_number_data.native_value
            _LOGGER.debug(
                "Restored %s to value: %s", self._attr_unique_id, self._attr_native_value
            )
        else:
            self._attr_native_value = float(self._default_val)
            
        self._update_coordinator(int(self._attr_native_value))
        self.async_write_ha_state()

    async def async_set_native_value(self, value: float) -> None:
        """Update the value."""
        self._attr_native_value = value
        self._update_coordinator(int(value))
        self.async_write_ha_state()

    def _update_coordinator(self, value: int) -> None:
        """Push value to the coordinator."""
        if self._key == CONF_MIN_CYCLE_ON:
            self._coordinator.set_min_cycle_on(value)
        elif self._key == CONF_MIN_CYCLE_OFF:
            self._coordinator.set_min_cycle_off(value)
        elif self._key == CONF_VALVE_DELAY:
            self._coordinator.set_valve_delay(value)


class MultizonePersistentNumber(NumberEntity):
    """Generic Number entity that saves its state to the coordinator persistent storage."""

    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(
        self,
        coordinator,
        entry_id: str,
        key: str,
        name: str,
        min_value: float,
        max_value: float,
        step: float,
        unit_of_measurement: str,
        icon: str,
        default_val: float,
        device_info: DeviceInfo,
    ) -> None:
        """Initialize the number entity."""
        self._coordinator = coordinator
        self._key = key
        self._default_val = default_val

        self._attr_unique_id = f"{DOMAIN}_{entry_id}_{key}"
        self._attr_name = name
        self._attr_native_min_value = min_value
        self._attr_native_max_value = max_value
        self._attr_native_step = step
        self._attr_native_unit_of_measurement = unit_of_measurement
        self._attr_icon = icon
        self._attr_device_info = device_info

    @property
    def native_value(self) -> float:
        """Return the current value."""
        return self._coordinator.get_persistent_data(self._key, self._default_val)

    async def async_set_native_value(self, value: float) -> None:
        """Update the value."""
        await self._coordinator.async_set_persistent_data(self._key, value)
        self.async_write_ha_state()


class PresetNumber(RestoreEntity, NumberEntity):
    """Number entity for a specific preset temperature (summer or winter)."""

    _attr_has_entity_name = True
    _attr_native_min_value = 5.0
    _attr_native_max_value = 35.0
    _attr_native_step = 0.5

    def __init__(
        self,
        hass: HomeAssistant,
        entry_id: str,
        vt_name: str,
        preset: str,
        season: str,
        initial_value: float,
        device_info: DeviceInfo,
    ) -> None:
        """Initialize."""
        self.hass = hass
        self._vt_name = vt_name
        self._preset = preset
        self._season = season
        self._entry_id = entry_id
        self._attr_native_value = initial_value

        safe_vt = vt_name.lower().replace(" ", "_").replace("-", "_")
        safe_vt = "".join(c for c in safe_vt if c.isalnum() or c == "_")
        self._attr_unique_id = f"{DOMAIN}_{entry_id}_vt_{safe_vt}_{season}_{preset}_temp"
        # НЕ устанавливаем entity_id вручную!

        self._attr_device_info = device_info

        # Имена на русском
        season_name = "Лето" if season == SEASON_SUMMER else "Зима"
        preset_names = {
            "manual": "Ручной",
            "eco": "Эко",
            "comfort": "Комфорт",
            "sleep": "Сон",
            "away": "Отъезд",
        }
        self._attr_name = f"{season_name} {preset_names.get(preset, preset.capitalize())}"

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return True

    async def async_set_native_value(self, value: float) -> None:
        """Update the preset temperature."""
        self._attr_native_value = value
        self.async_write_ha_state()

        # Update the config entry data
        entry = self.hass.config_entries.async_get_entry(self._entry_id)
        if not entry:
            return

        data = dict(entry.data)
        virtual_thermostats = list(data.get(CONF_VIRTUAL_THERMOSTATS, []))
        for vt in virtual_thermostats:
            if vt.get(CONF_VT_NAME) == self._vt_name:
                if self._season == SEASON_SUMMER:
                    season_key = CONF_VT_PRESET_TEMPS_SUMMER
                else:
                    season_key = CONF_VT_PRESET_TEMPS_WINTER
                if season_key not in vt:
                    vt[season_key] = {}
                vt[season_key][self._preset] = value
                break

        data[CONF_VIRTUAL_THERMOSTATS] = virtual_thermostats
        self.hass.config_entries.async_update_entry(entry, data=data)

        # Reload the entry to apply changes to the climate entities
        await self.hass.config_entries.async_reload(self._entry_id)
        _LOGGER.debug("Updated %s preset %s temp to %.1f", self._vt_name, self._preset, value)
