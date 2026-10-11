import logging
import datetime
from datetime import time as dt_time, timedelta
from typing import Any, Callable, Awaitable

from homeassistant.core import HomeAssistant, Event, callback
from homeassistant.helpers.event import async_track_state_change_event, async_track_time_interval
import homeassistant.util.dt as dt_util

from .const import (
    KEY_NIGHT_TIME,
    KEY_MORNING_TIME,
    KEY_AUTO_NIGHT_MODE,
    KEY_GEOFENCING_TOGGLE,
    KEY_PRE_AWAY_PRESET,
    KEY_PRE_NIGHT_PRESET,
    GLOBAL_PRESET_SLEEP,
    GLOBAL_PRESET_AWAY,
    GLOBAL_PRESET_COMFORT,
    GLOBAL_PRESET_MANUAL,
)

_LOGGER = logging.getLogger(__name__)

class RoutineManager:
    """Manages Geofencing and Auto Night/Morning routines."""

    def __init__(
        self,
        hass: HomeAssistant,
        presence_sensor: str | None,
        get_persistent_data: Callable[[str, Any], Any],
        async_set_persistent_data: Callable[[str, Any], Awaitable[None]],
        get_current_global_preset: Callable[[], str],
        async_set_global_preset: Callable[[str], Awaitable[None]],
    ) -> None:
        self.hass = hass
        self.presence_sensor = presence_sensor
        self._get_persistent_data = get_persistent_data
        self._async_set_persistent_data = async_set_persistent_data
        self._get_current_global_preset = get_current_global_preset
        self._async_set_global_preset = async_set_global_preset
        
        self._last_night_trigger_date: datetime.date | None = None
        self._last_morning_trigger_date: datetime.date | None = None
        
        self._unsub_listeners: list[Callable[[], None]] = []
        # Last reliable presence value (never "unknown"/"unavailable")
        self._last_known_presence: str | None = None
        
    def async_setup_listeners(self) -> None:
        """Initialize listeners."""
        if self.presence_sensor:
            self._unsub_listeners.append(
                async_track_state_change_event(
                    self.hass,
                    [self.presence_sensor],
                    self._async_on_presence_changed,
                )
            )
            _LOGGER.debug("Listening to presence sensor: %s", self.presence_sensor)

        # Listen every minute for Schedule check (Night / Morning)
        self._unsub_listeners.append(
            async_track_time_interval(
                self.hass,
                self._async_check_schedule,
                timedelta(minutes=1),
            )
        )

    def cleanup(self) -> None:
        """Unsubscribe listeners."""
        for unsub in self._unsub_listeners:
            unsub()
        self._unsub_listeners.clear()

    @callback
    def _async_on_presence_changed(self, event: Event) -> None:
        """Handle presence sensor state changes (Geofencing logic)."""
        if not self._get_persistent_data(KEY_GEOFENCING_TOGGLE, True):
            return

        new_state = event.data.get("new_state")
        old_state = event.data.get("old_state")
        
        if not new_state:
            return
            
        invalid = ("unavailable", "unknown")
        new_val = new_state.state
        old_val = old_state.state if old_state else None
        
        # Unknown/unavailable never trigger Away: keep the last reliable condition.
        if new_val in invalid:
            return

        if old_val in invalid:
            old_val = None
        # Compare with the last RELIABLE value so home -> unavailable -> not_home is still detected
        if self._last_known_presence is not None:
            old_val = self._last_known_presence
        self._last_known_presence = new_val

        if old_val is None or old_val == new_val:
            return
            
        _LOGGER.info("Presence changed: %s -> %s", old_val, new_val)
        
        is_away = new_val != "home"
        was_away = old_val != "home"
        
        if is_away and not was_away:
            _LOGGER.info("Geofencing: Everyone left. Setting to Away mode.")
            self.hass.async_create_task(
                self._async_set_persistent_data(KEY_PRE_AWAY_PRESET, self._get_current_global_preset())
            )
            self.hass.async_create_task(self._async_set_global_preset(GLOBAL_PRESET_AWAY))
            
        elif not is_away and was_away:
            _LOGGER.info("Geofencing: Someone returned.")
            
            night_time_str = self._get_persistent_data(KEY_NIGHT_TIME, "22:30")
            morning_time_str = self._get_persistent_data(KEY_MORNING_TIME, "07:00")
            is_night = False
            
            try:
                n_hour, n_minute = map(int, night_time_str.split(":"))
                m_hour, m_minute = map(int, morning_time_str.split(":"))
                now = dt_util.now().time()
                night_time = dt_time(n_hour, n_minute)
                morning_time = dt_time(m_hour, m_minute)
                
                if night_time > morning_time:
                    if now >= night_time or now <= morning_time:
                        is_night = True
                else:
                    if now >= night_time and now <= morning_time:
                        is_night = True
                        
                _LOGGER.debug("Geofencing schedule: night_time=%s, morning_time=%s, now=%s, is_night=%s", night_time, morning_time, now, is_night)
            except Exception as ex:
                _LOGGER.error("Geofencing schedule exception (invalid format): %s", ex, exc_info=True)
                
            if is_night:
                _LOGGER.info("Geofencing: Returned at night. Setting Sleep mode.")
                pre_away = self._get_persistent_data(KEY_PRE_AWAY_PRESET, GLOBAL_PRESET_COMFORT)
                self.hass.async_create_task(self._async_set_persistent_data(KEY_PRE_NIGHT_PRESET, pre_away))
                self.hass.async_create_task(self._async_set_global_preset(GLOBAL_PRESET_SLEEP))
            else:
                pre_away = self._get_persistent_data(KEY_PRE_AWAY_PRESET, GLOBAL_PRESET_COMFORT)
                _LOGGER.info("Geofencing: Restoring previous mode: %s", pre_away)
                self.hass.async_create_task(self._async_set_global_preset(pre_away))

    @callback
    def _async_check_schedule(self, now: datetime.datetime) -> None:
        """Check if it's time to trigger Auto Night Mode or Morning Mode."""
        if not self._get_persistent_data(KEY_AUTO_NIGHT_MODE, False):
            return

        local_now = dt_util.now()
        current_date = local_now.date()

        # Check Night Time
        night_time_str = self._get_persistent_data(KEY_NIGHT_TIME, "22:30")
        try:
            hour, minute = map(int, night_time_str.split(":"))
            target_dt = local_now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            time_diff = (local_now - target_dt).total_seconds()
            
            # Bug 10 FIX: Trigger if we are within a 5 minute window of the target (avoids missed minute drift)
            if 0 <= time_diff < 300:
                if self._last_night_trigger_date != current_date:
                    self._last_night_trigger_date = current_date
                    current_preset = self._get_current_global_preset()
                    if current_preset in (GLOBAL_PRESET_MANUAL, "none"):
                        _LOGGER.info("Auto Night Mode skipped because system is in Manual mode.")
                    elif current_preset != GLOBAL_PRESET_SLEEP:
                        _LOGGER.info("Auto Night Mode triggered. Setting Sleep mode.")
                        self.hass.async_create_task(
                            self._async_set_persistent_data(KEY_PRE_NIGHT_PRESET, current_preset)
                        )
                        self.hass.async_create_task(self._async_set_global_preset(GLOBAL_PRESET_SLEEP))
        except Exception as ex:
            _LOGGER.error("Routine Manager exception checking Night Time schedule: %s", ex, exc_info=True)

        # Check Morning Time
        morning_time_str = self._get_persistent_data(KEY_MORNING_TIME, "07:00")
        try:
            hour, minute = map(int, morning_time_str.split(":"))
            target_dt = local_now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            time_diff = (local_now - target_dt).total_seconds()
            
            if 0 <= time_diff < 300:
                if self._last_morning_trigger_date != current_date:
                    self._last_morning_trigger_date = current_date
                    current_preset = self._get_current_global_preset()
                    if current_preset in (GLOBAL_PRESET_MANUAL, "none"):
                        _LOGGER.info("Auto Morning Mode skipped because system is in Manual mode.")
                    else:
                        pre_night = self._get_persistent_data(KEY_PRE_NIGHT_PRESET, GLOBAL_PRESET_COMFORT)
                        _LOGGER.info("Auto Morning Mode triggered. Restoring mode: %s", pre_night)
                        self.hass.async_create_task(self._async_set_global_preset(pre_night))
        except Exception as ex:
            _LOGGER.error("Routine Manager exception checking Morning Time schedule: %s", ex, exc_info=True)
