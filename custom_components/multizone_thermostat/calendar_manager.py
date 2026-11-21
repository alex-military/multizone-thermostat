"""Calendar and Smart Start manager for Multizone Thermostat."""

import logging
from datetime import datetime, timedelta
import homeassistant.util.dt as dt_util

from .calendar_parser import parse_calendar_event
from .const import (
    CONF_ZONE_NAME,
    GLOBAL_PRESET_AWAY,
    HVAC_MODE_COOL,
    get_state_temp_unit,
    make_zone_entity_id,
    resolve_zone_id_safe,
    to_celsius,
)

_LOGGER = logging.getLogger(__name__)
MAX_SMART_START_HOURS = 6.0

class CalendarManager:
    """Manages Home Assistant Calendar integration and Smart Start logic."""

    def __init__(self, coordinator) -> None:
        """Initialize the Calendar Manager."""
        self.coordinator = coordinator
        
        # State variables
        self.active_event_id: str | None = None
        self.active_global_preset: str | None = None
        self.current_event_overrides: dict[str, float] = {}
        self.smart_start_overrides: dict[str, float] = {}
        self.mode_overrides: dict[str, str] = {}
        self.pre_calendar_preset: str | None = None

    @property
    def hass(self):
        """Get Home Assistant instance from coordinator."""
        return self.coordinator.hass
        
    @property
    def global_calendar_id(self):
        """Get global calendar ID from coordinator."""
        return self.coordinator.global_calendar_id
        
    @property
    def temp_overrides(self) -> dict[str, float]:
        """Combine active current event overrides with smart start overrides."""
        return {**self.current_event_overrides, **self.smart_start_overrides}

    def set_temp_override(self, climate_id: str, temp: float) -> None:
        """Update an active calendar or Smart Start override temperature."""
        climate_id = resolve_zone_id_safe(self.coordinator, climate_id)
        updated = False
        if climate_id in self.current_event_overrides:
            self.current_event_overrides[climate_id] = temp
            updated = True
        if climate_id in self.smart_start_overrides:
            self.smart_start_overrides[climate_id] = temp
            updated = True
        if not updated:
            self.current_event_overrides[climate_id] = temp

    def clear_temp_override(self, climate_id: str) -> None:
        """Clear any calendar or Smart Start temperature override for a zone."""
        climate_id = resolve_zone_id_safe(self.coordinator, climate_id)
        self.current_event_overrides.pop(climate_id, None)
        self.smart_start_overrides.pop(climate_id, None)

    def _get_thermal_model(self, climate_id: str):
        """Look up zone ThermalObserver from ZoneController or coordinator fallback."""
        climate_id = resolve_zone_id_safe(self.coordinator, climate_id)
        zc = getattr(self.coordinator, "zone_controller", None)
        if zc is not None and isinstance(getattr(zc, "thermal_models", None), dict):
            obs = zc.thermal_models.get(climate_id)
            if obs is not None:
                return obs
        models = getattr(self.coordinator, "_thermal_models", None)
        return models.get(climate_id) if isinstance(models, dict) else None

    def _parse_event_datetime(self, raw_val: str | None) -> datetime | None:
        """Parse an ISO datetime or all-day YYYY-MM-DD date string into a local timezone-aware datetime."""
        if not raw_val:
            return None
        dt = dt_util.parse_datetime(raw_val)
        if dt is None:
            # Handle all-day calendar events ("YYYY-MM-DD")
            try:
                from datetime import date as dt_date
                d = dt_date.fromisoformat(str(raw_val)[:10])
                tz = getattr(dt_util, "DEFAULT_TIME_ZONE", None)
                dt = datetime(d.year, d.month, d.day, 0, 0, 0, tzinfo=tz)
            except (ValueError, TypeError):
                return None
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=dt_util.DEFAULT_TIME_ZONE)
        return dt_util.as_local(dt)

    def _notify_climates_and_sync_trvs(self, climate_ids: set[str] | list[str] | None = None) -> None:
        """Refresh virtual climate entities and trigger physical TRV synchronization."""
        target_ids = climate_ids if climate_ids is not None else list(self.coordinator._climate_callbacks.keys())
        for cid in target_ids:
            cb = self.coordinator._climate_callbacks.get(cid)
            if cb:
                cb()
            climate_entities = getattr(self.coordinator, "_climate_entities", None)
            if isinstance(climate_entities, dict):
                ent = climate_entities.get(cid)
                if ent is not None and hasattr(ent, "_trigger_trv_sync") and hasattr(self.hass, "async_create_task"):
                    try:
                        coro = ent._trigger_trv_sync()
                        if hasattr(coro, "__await__"):
                            self.hass.async_create_task(coro)
                    except (ValueError, TypeError, AttributeError, RuntimeError):
                        pass
        
    async def async_check_global_calendar(self, now: datetime) -> None:
        """Fetch and parse calendar events for scheduling and Smart Start."""
        if not self.global_calendar_id:
            return
            
        # 1. Fetch events from now to +24 hours
        end_time = now + timedelta(hours=24)
        try:
            response = await self.hass.services.async_call(
                "calendar",
                "get_events",
                {
                    "entity_id": self.global_calendar_id,
                    "start_date_time": now.isoformat(),
                    "end_date_time": end_time.isoformat()
                },
                blocking=True,
                return_response=True
            )
            
            if not response or self.global_calendar_id not in response:
                return
                
            events = response[self.global_calendar_id].get("events", [])
            
            # Find current and future events
            current_events = []
            future_events_with_start: list[tuple[datetime, dict]] = []
            
            for event in events:
                try:
                    start = self._parse_event_datetime(event.get("start"))
                    end = self._parse_event_datetime(event.get("end"))
                    
                    if start and end:
                        if start <= now < end:
                            current_events.append(event)
                        elif now < start:
                            future_events_with_start.append((start, event))
                except Exception as ex:
                    _LOGGER.warning("Error parsing calendar event dates: %s", ex)

            future_events_with_start.sort(key=lambda item: item[0])
            future_events = [ev for _, ev in future_events_with_start]
                    
            await self._async_process_calendar_events(current_events, future_events, now)
                
        except Exception as ex:
            _LOGGER.error("Error fetching calendar events: %s", ex)

    async def _async_process_calendar_events(
        self,
        current_events: list[dict],
        next_event: dict | list[dict] | None,
        now: datetime,
    ) -> None:
        """Process current and future events."""
        # 1. Process Current Events
        if current_events:
            # We use a combined ID to track changes in overlapping events
            uids = [f"{ev.get('start', '')}_{ev.get('summary', 'Untitled')}" for ev in current_events]
            combined_uid = "|".join(sorted(uids))
            
            if self.active_event_id != combined_uid:
                titles = [ev.get("summary", "Untitled") for ev in current_events]
                _LOGGER.info("Calendar Event(s) Started/Changed: %s", ", ".join(titles))
                self.active_event_id = combined_uid
                
                if self.pre_calendar_preset is None:
                    self.pre_calendar_preset = self.coordinator.zone_manager.current_global_preset

                is_away_locked = (
                    self.coordinator.zone_manager.current_global_preset == GLOBAL_PRESET_AWAY
                    and self.active_global_preset is None
                )

                # Clear temporary overrides from previous events
                self.current_event_overrides.clear()
                self.mode_overrides.clear()
                saw_global_preset = False

                # Parse all active events (later events override earlier ones if conflict)
                for current_event in current_events:
                    parsed = parse_calendar_event(current_event.get("summary", ""))

                    # Apply Global Settings (protect geofenced AWAY unless event explicitly sets AWAY)
                    if parsed["global_preset"]:
                        saw_global_preset = True
                        if not is_away_locked or parsed["global_preset"] == GLOBAL_PRESET_AWAY:
                            self.active_global_preset = parsed["global_preset"]
                            await self.coordinator.zone_manager.async_set_global_preset(parsed["global_preset"])

                    master_mode = str(getattr(self.coordinator, "master_hvac_mode", "heat")).lower()
                    is_cool = (master_mode in ("cool", HVAC_MODE_COOL.lower()))

                    if parsed["global_temperature"] is not None and not is_away_locked:
                        for zone in self.coordinator.zones:
                            climate_id = make_zone_entity_id(zone[CONF_ZONE_NAME])
                            if is_cool and hasattr(self.coordinator, "can_zone_cool") and not self.coordinator.can_zone_cool(climate_id):
                                continue
                            self.current_event_overrides[climate_id] = parsed["global_temperature"]
                            
                    # Apply Zone Overrides
                    for zone_name, override in parsed["overrides"].items():
                        # Find real entity_id
                        climate_id = None
                        for z in self.coordinator.zones:
                            if z[CONF_ZONE_NAME].lower() == zone_name:
                                climate_id = make_zone_entity_id(z[CONF_ZONE_NAME])
                                break
                                
                        if not climate_id:
                            continue
                            
                        # Modes
                        if override.mode:
                            if override.is_permanent:
                                zone_select = self.coordinator._select_entities.get(f"zone_mode_{climate_id}")
                                if zone_select:
                                    await zone_select.async_select_option(override.mode)
                                else:
                                    self.coordinator.set_zone_mode(climate_id, override.mode)
                            else:
                                self.mode_overrides[climate_id] = override.mode
                                
                        # Temperatures
                        target_temp = override.temperature
                        if target_temp is None and getattr(override, "preset", None):
                            if hasattr(self.coordinator.zone_manager, "get_preset_temperature"):
                                target_temp = self.coordinator.zone_manager.get_preset_temperature(override.preset, climate_id)
                            else:
                                zm = self.coordinator.zone_manager
                                presets = getattr(zm, "presets", None)
                                if not isinstance(presets, dict):
                                    presets = getattr(zm, "_presets", {})
                                target_temp = presets.get(override.preset, {}).get(climate_id, {}).get("target_temp")

                        if target_temp is not None:
                            if is_cool and hasattr(self.coordinator, "can_zone_cool") and not self.coordinator.can_zone_cool(climate_id):
                                pass
                            elif override.is_permanent:
                                # Save permanently to current preset (Demeter violation fixed)
                                if self.coordinator.zone_manager.current_global_preset:
                                    self.coordinator.zone_manager.update_preset_temperature(
                                        self.coordinator.zone_manager.current_global_preset, 
                                        climate_id, 
                                        target_temp
                                    )
                            elif not is_away_locked:
                                # Save temporarily
                                self.current_event_overrides[climate_id] = target_temp

                # If overlapping transition moved to an event without global preset, restore prior preset
                if not saw_global_preset and self.active_global_preset is not None:
                    if self.pre_calendar_preset is not None and not is_away_locked:
                        if self.coordinator.zone_manager.current_global_preset != GLOBAL_PRESET_AWAY or self.active_global_preset == GLOBAL_PRESET_AWAY:
                            await self.coordinator.zone_manager.async_set_global_preset(self.pre_calendar_preset)
                    self.active_global_preset = None

                # Trigger a refresh of climate entities and sync TRVs
                self._notify_climates_and_sync_trvs()
        else:
            if self.active_event_id is not None:
                _LOGGER.info("Calendar Event Ended. Restoring base state.")
                self.active_event_id = None
                self.current_event_overrides.clear()
                self.mode_overrides.clear()
                
                if self.pre_calendar_preset is not None and self.active_global_preset is not None:
                    if self.coordinator.zone_manager.current_global_preset != GLOBAL_PRESET_AWAY or self.active_global_preset == GLOBAL_PRESET_AWAY:
                        await self.coordinator.zone_manager.async_set_global_preset(self.pre_calendar_preset)
                self.pre_calendar_preset = None
                self.active_global_preset = None
                    
                self._notify_climates_and_sync_trvs()

        # 2. Process Smart Start (Future Events)
        old_smart_start = dict(self.smart_start_overrides)
        self.smart_start_overrides.clear()

        if isinstance(next_event, dict):
            future_events = [next_event]
        elif isinstance(next_event, list):
            future_events = next_event
        else:
            future_events = []

        evaluated_zones: set[str] = set()
        master_mode = str(getattr(self.coordinator, "master_hvac_mode", "heat")).lower()
        is_cool = (master_mode in ("cool", HVAC_MODE_COOL.lower()))
        is_away_geofence = (
            getattr(self.coordinator.zone_manager, "current_global_preset", None) == GLOBAL_PRESET_AWAY
            and self.active_global_preset is None
        )
        for fut_event in future_events if not is_away_geofence else []:
            start_time = self._parse_event_datetime(fut_event.get("start"))
            if not start_time:
                continue
            parsed_next = parse_calendar_event(fut_event.get("summary", ""))
            for zone in self.coordinator.zones:
                climate_id = make_zone_entity_id(zone[CONF_ZONE_NAME])
                if climate_id in evaluated_zones:
                    continue
                if is_cool and hasattr(self.coordinator, "can_zone_cool") and not self.coordinator.can_zone_cool(climate_id):
                    continue
                target = None
                
                # Does this future event have specific temp override for this zone?
                zone_name_lower = zone[CONF_ZONE_NAME].lower()
                if zone_name_lower in parsed_next["overrides"]:
                    fut_override = parsed_next["overrides"][zone_name_lower]
                    target = fut_override.temperature
                    if target is None and getattr(fut_override, "preset", None):
                        if hasattr(self.coordinator.zone_manager, "get_preset_temperature"):
                            target = self.coordinator.zone_manager.get_preset_temperature(fut_override.preset, climate_id)
                        else:
                            zm = self.coordinator.zone_manager
                            presets = getattr(zm, "presets", None)
                            if not isinstance(presets, dict):
                                presets = getattr(zm, "_presets", {})
                            target = presets.get(fut_override.preset, {}).get(climate_id, {}).get("target_temp")
                    
                if target is None and parsed_next["global_temperature"] is not None:
                    target = parsed_next["global_temperature"]
                    
                if target is None and parsed_next["global_preset"]:
                    # Look up base preset temp for this zone
                    if hasattr(self.coordinator.zone_manager, "get_preset_temperature"):
                        target = self.coordinator.zone_manager.get_preset_temperature(parsed_next["global_preset"], climate_id)
                    else:
                        zm = self.coordinator.zone_manager
                        presets = getattr(zm, "presets", None)
                        if not isinstance(presets, dict):
                            presets = getattr(zm, "_presets", {})
                        target = presets.get(parsed_next["global_preset"], {}).get(climate_id, {}).get("target_temp")
                    
                if target is not None:
                    current_temp = None
                    c_ent = getattr(self.coordinator, "_climate_entities", {}).get(climate_id)
                    ent_cur = getattr(c_ent, "current_temperature", None) if c_ent is not None else None
                    if isinstance(ent_cur, (int, float)) and not isinstance(ent_cur, bool):
                        current_temp = float(ent_cur)
                    else:
                        state = self.hass.states.get(climate_id)
                        if state and state.attributes:
                            raw_cur = state.attributes.get("current_temperature")
                            if raw_cur is not None:
                                try:
                                    current_temp = to_celsius(
                                        float(raw_cur),
                                        get_state_temp_unit(state),
                                        self.hass,
                                    )
                                except (ValueError, TypeError):
                                    current_temp = None

                    need_smart_start = False
                    delta_t = 0.0
                    rate = 1.0
                    thermal_model = self._get_thermal_model(climate_id)

                    if is_cool:
                        if current_temp is not None and current_temp > target:
                            delta_t = current_temp - target
                            ac_rate = getattr(thermal_model, "active_cooling_rate", 0.0) if thermal_model else 0.0
                            c_rate = getattr(thermal_model, "cooling_rate", 0.0) if thermal_model else 0.0
                            if ac_rate > 0.05:
                                rate = ac_rate
                            elif c_rate > 0.05:
                                rate = c_rate
                            else:
                                h_rate = getattr(thermal_model, "heating_rate", 0.0) if thermal_model else 0.0
                                rate = h_rate if h_rate > 0.05 else 1.0
                            need_smart_start = True
                    else:
                        if current_temp is not None and current_temp < target:
                            delta_t = target - current_temp
                            h_rate = getattr(thermal_model, "heating_rate", 0.0) if thermal_model else 0.0
                            if h_rate > 0.05:
                                rate = h_rate
                                need_smart_start = True

                    if need_smart_start and rate > 0:
                        hours_needed = min(MAX_SMART_START_HOURS, max(0.0, delta_t / rate))
                        time_needed = timedelta(hours=hours_needed)

                        if now + time_needed >= start_time:
                            _LOGGER.info("Smart Start Active for %s! Target: %.1f, Need: %s", climate_id, target, time_needed)
                            # Override current target temp temporarily
                            self.smart_start_overrides[climate_id] = target
                            evaluated_zones.add(climate_id)
                            # Wake up zone if temporarily bypassed/off by calendar
                            if self.mode_overrides.get(climate_id) in ("off", "bypass"):
                                del self.mode_overrides[climate_id]
                                        
        # If smart start state changed for any zone, trigger refresh
        if old_smart_start != self.smart_start_overrides:
            changed_zones = set(old_smart_start.keys()) | set(self.smart_start_overrides.keys())
            self._notify_climates_and_sync_trvs(changed_zones)
