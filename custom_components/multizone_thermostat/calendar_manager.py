"""Calendar and Smart Start manager for Multizone Thermostat."""

import logging
from datetime import datetime, timedelta
import homeassistant.util.dt as dt_util

from .calendar_parser import parse_calendar_event
from .const import CONF_ZONE_NAME, make_zone_entity_id

_LOGGER = logging.getLogger(__name__)

class CalendarManager:
    """Manages Home Assistant Calendar integration and Smart Start logic."""

    def __init__(self, coordinator) -> None:
        """Initialize the Calendar Manager."""
        self.coordinator = coordinator
        
        # State variables
        self.active_event_id: str | None = None
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
            
            # Find current and next event
            current_events = []
            next_event = None
            
            for event in events:
                try:
                    start = dt_util.parse_datetime(event["start"])
                    if start:
                        if start.tzinfo is None:
                            start = start.replace(tzinfo=dt_util.DEFAULT_TIME_ZONE)
                        start = dt_util.as_local(start)
                    
                    end = dt_util.parse_datetime(event["end"])
                    if end:
                        if end.tzinfo is None:
                            end = end.replace(tzinfo=dt_util.DEFAULT_TIME_ZONE)
                        end = dt_util.as_local(end)
                    
                    if start and end:
                        if start <= now < end:
                            current_events.append(event) # Bug 9 FIX: Collect ALL overlapping events
                        elif now < start:
                            if not next_event:
                                next_event = event
                                # Don't break, allow finding all concurrent current events
                except Exception as ex:
                    _LOGGER.warning("Error parsing calendar event dates: %s", ex)
                    
            await self._async_process_calendar_events(current_events, next_event, now)
                
        except Exception as ex:
            _LOGGER.error("Error fetching calendar events: %s", ex)

    async def _async_process_calendar_events(self, current_events: list[dict], next_event: dict | None, now: datetime) -> None:
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
                
                # Clear temporary overrides from previous events
                self.current_event_overrides.clear()
                self.mode_overrides.clear()
                
                # Parse all active events (later events override earlier ones if conflict)
                for current_event in current_events:
                    parsed = parse_calendar_event(current_event.get("summary", ""))
                    
                    # Apply Global Settings
                    if parsed["global_preset"]:
                        await self.coordinator.zone_manager.async_set_global_preset(parsed["global_preset"])
                        
                    if parsed["global_temperature"]:
                        for zone in self.coordinator.zones:
                            climate_id = make_zone_entity_id(zone[CONF_ZONE_NAME])
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
                                self.mode_overrides[climate_id] = override.mode
                                
                        # Temperatures
                        if override.temperature is not None:
                            if override.is_permanent:
                                # Save permanently to current preset (Demeter violation fixed)
                                if self.coordinator.zone_manager.current_global_preset:
                                    self.coordinator.zone_manager.update_preset_temperature(
                                        self.coordinator.zone_manager.current_global_preset, 
                                        climate_id, 
                                        override.temperature
                                    )
                            else:
                                # Save temporarily
                                self.current_event_overrides[climate_id] = override.temperature
                                
                # Trigger a refresh of climate entities
                for cb in self.coordinator._climate_callbacks.values():
                    cb()
        else:
            if self.active_event_id is not None:
                _LOGGER.info("Calendar Event Ended. Restoring base state.")
                self.active_event_id = None
                self.current_event_overrides.clear()
                self.mode_overrides.clear()
                
                if self.pre_calendar_preset is not None:
                    await self.coordinator.zone_manager.async_set_global_preset(self.pre_calendar_preset)
                    self.pre_calendar_preset = None
                    
                for cb in self.coordinator._climate_callbacks.values():
                    cb()

        # 2. Process Smart Start (Next Event)
        # Bug 8 FIX: Always recalculate smart_start_overrides from scratch. 
        # If the future event is cancelled or we warmed up, this clears the old overrides!
        old_smart_start = dict(self.smart_start_overrides)
        self.smart_start_overrides.clear()
        
        if next_event:
            start_time = dt_util.as_local(dt_util.parse_datetime(next_event["start"]))
            if start_time:
                parsed_next = parse_calendar_event(next_event.get("summary", ""))
                # We only preheat if there is a target temperature shift
                # For each zone, calculate if we need to start
                for zone in self.coordinator.zones:
                    climate_id = make_zone_entity_id(zone[CONF_ZONE_NAME])
                    target = None
                    
                    # Does next event have specific temp override?
                    zone_name_lower = zone[CONF_ZONE_NAME].lower()
                    if zone_name_lower in parsed_next["overrides"]:
                        target = parsed_next["overrides"][zone_name_lower].temperature
                        
                    if target is None and parsed_next["global_temperature"]:
                        target = parsed_next["global_temperature"]
                        
                    if target is None and parsed_next["global_preset"]:
                        # Look up base preset temp for this zone
                        target = self.coordinator.zone_manager._presets.get(parsed_next["global_preset"], {}).get(climate_id, {}).get("target_temp")
                        
                    if target is not None:
                        current_temp = None
                        state = self.hass.states.get(climate_id)
                        if state:
                            current_temp = state.attributes.get("current_temperature")
                            
                        if current_temp is not None and current_temp < target:
                            # We need to heat. Calculate time.
                            thermal_model = self.coordinator._thermal_models.get(climate_id)
                            if thermal_model and thermal_model.heating_rate > 0.05: # At least 0.05 deg/hour
                                delta_t = target - current_temp
                                hours_needed = delta_t / thermal_model.heating_rate
                                time_needed = timedelta(hours=hours_needed)
                                
                                if now + time_needed >= start_time:
                                    _LOGGER.info("Smart Start Active for %s! Target: %.1f, Need: %s", climate_id, target, time_needed)
                                    # Override current target temp temporarily
                                    self.smart_start_overrides[climate_id] = target
                                    # Wake up zone if in Sleep/Eco
                                    if self.mode_overrides.get(climate_id) == "off":
                                        del self.mode_overrides[climate_id]
                                        
        # If smart start state changed for any zone, trigger refresh
        if old_smart_start != self.smart_start_overrides:
            changed_zones = set(old_smart_start.keys()) | set(self.smart_start_overrides.keys())
            for cid in changed_zones:
                if cid in self.coordinator._climate_callbacks:
                    self.coordinator._climate_callbacks[cid]()
