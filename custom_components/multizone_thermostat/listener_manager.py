"""Manager for Home Assistant event listeners, state tracking, and periodic timers."""
from __future__ import annotations

from datetime import timedelta
import inspect
import logging
from typing import Any

import homeassistant.util.dt as dt_util
from homeassistant.helpers.event import (
    async_track_state_change_event,
    async_track_time_interval,
)

from .const import (
    CONF_ZONE_NAME,
    CONF_ZONE_WINDOW_SENSOR,
    make_zone_entity_id,
)

_LOGGER = logging.getLogger(__name__)


class ListenerManager:
    """Coordinates lifecycle event listeners, state triggers, and periodic timers."""

    def __init__(self, coordinator: Any) -> None:
        """Initialize the ListenerManager."""
        self.coordinator = coordinator
        self.hass = coordinator.hass
        self._unsub_listeners: list = coordinator._unsub_listeners

    def async_setup_listeners(self) -> None:
        """Set up state change listeners for all climate entities and timers."""
        coord = self.coordinator
        tracked_ids: set[str] = {
            make_zone_entity_id(z[CONF_ZONE_NAME])
            for z in coord.zones
            if z.get(CONF_ZONE_NAME)
        }
        aliases = getattr(coord, "_entity_id_aliases", None)
        if isinstance(aliases, dict):
            tracked_ids.update(aliases.keys())
        climates = getattr(coord, "_climate_entities", None)
        if isinstance(climates, dict):
            for ent in climates.values():
                eid = getattr(ent, "entity_id", None)
                if eid:
                    tracked_ids.add(eid)
        climate_entities = sorted(tracked_ids)

        if climate_entities:
            self._unsub_listeners.append(
                async_track_state_change_event(
                    self.hass,
                    climate_entities,
                    self.async_on_climate_state_changed,
                )
            )
            _LOGGER.debug("Listening to climate state changes for: %s", climate_entities)

        # Listen for window sensors
        window_sensors = [
            z[CONF_ZONE_WINDOW_SENSOR]
            for z in coord.zones
            if z.get(CONF_ZONE_WINDOW_SENSOR) and z[CONF_ZONE_WINDOW_SENSOR] != "none"
        ]

        if window_sensors:
            self._unsub_listeners.append(
                async_track_state_change_event(
                    self.hass,
                    window_sensors,
                    coord.zone_manager.async_on_window_state_changed,
                )
            )
            _LOGGER.debug("Listening to window state changes for: %s", window_sensors)

        # Start periodic PWM evaluation (every 10 seconds)
        self._unsub_listeners.append(
            async_track_time_interval(
                self.hass,
                coord.plant_orchestrator.async_tick,
                timedelta(seconds=10),
            )
        )

        coord.routine_manager.async_setup_listeners()

        # Listen every minute for Schedule Profile evaluation
        if hasattr(coord, "schedule_manager"):
            self._unsub_listeners.append(
                async_track_time_interval(
                    self.hass,
                    coord.schedule_manager.async_evaluate_schedule,
                    timedelta(minutes=1),
                )
            )

        # Listen every hour for Anti-Seize check
        self._unsub_listeners.append(
            async_track_time_interval(
                self.hass,
                coord.anti_seize_manager.check_anti_seize,
                timedelta(hours=1),
            )
        )

        # Phase 11: Start EnergyManager tracking
        if hasattr(coord, "energy_manager") and coord.energy_manager:
            self.hass.async_create_task(coord.energy_manager.async_start())

        # Listen every 5 minutes for Calendar API checks
        if coord.global_calendar_id:
            self._unsub_listeners.append(
                async_track_time_interval(
                    self.hass,
                    coord.calendar_manager.async_check_global_calendar,
                    timedelta(minutes=5),
                )
            )
            # Check immediately on startup
            self.hass.async_create_task(coord.calendar_manager.async_check_global_calendar(dt_util.now()))

    def async_teardown_listeners(self) -> None:
        """Remove all state change listeners and cancel background tasks."""
        coord = self.coordinator
        if hasattr(coord, "routine_manager") and coord.routine_manager:
            coord.routine_manager.cleanup()
        if hasattr(coord, "anti_seize_manager") and coord.anti_seize_manager:
            if hasattr(coord.anti_seize_manager, "stop"):
                coord.anti_seize_manager.stop()
            else:
                anti_seize_task = getattr(coord.anti_seize_manager, "_task", None)
                if anti_seize_task and not anti_seize_task.done():
                    anti_seize_task.cancel()
        if hasattr(coord, "boiler_backend") and coord.boiler_backend:
            if hasattr(coord.boiler_backend, "cancel_pending_tasks"):
                coord.boiler_backend.cancel_pending_tasks()
            else:
                backend_task = getattr(coord.boiler_backend, "_pending_boiler_task", None)
                if backend_task and not backend_task.done():
                    backend_task.cancel()
                    coord.boiler_backend._pending_boiler_task = None

        if hasattr(coord, "energy_manager") and coord.energy_manager:
            coord.energy_manager.async_stop()

        for unsub in self._unsub_listeners:
            unsub()
        self._unsub_listeners.clear()

    async def async_on_climate_state_changed(self, event: Any) -> None:
        """Handle temperature or preset changes on individual zone climate entities."""
        entity_id = event.data.get("entity_id")
        new_state = event.data.get("new_state")
        if not new_state:
            return
        resolve_fn = getattr(self.coordinator, "resolve_zone_id", None)
        resolved = resolve_fn(entity_id) if callable(resolve_fn) else None
        canon_id = resolved if isinstance(resolved, str) else entity_id
        demand = await self.coordinator.zone_controller.async_update_zone(canon_id, new_state)
        self.coordinator.demand_aggregator.set_zone_demand(canon_id, demand)
        # Immediately trigger boiler update to improve UI responsiveness when lowering target
        if hasattr(self.coordinator, "plant_orchestrator") and self.coordinator.plant_orchestrator:
            orch = self.coordinator.plant_orchestrator
            from .boiler.plant_orchestrator import PlantOrchestrator
            if isinstance(orch, PlantOrchestrator):
                await orch.async_refresh()
            elif "async_refresh" in getattr(orch, "_mock_children", {}) or "async_refresh" in getattr(orch, "__dict__", {}):
                res = orch.async_refresh()
                if inspect.isawaitable(res):
                    await res
            elif hasattr(orch, "_async_update_boiler"):
                res = orch._async_update_boiler()
                if inspect.isawaitable(res):
                    await res
            elif hasattr(orch, "async_refresh"):
                res = orch.async_refresh()
                if inspect.isawaitable(res):
                    await res
