"""TRV and Switch synchronization logic for Multizone Thermostat."""
from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

import homeassistant.util.dt as dt_util
from homeassistant.components.climate import HVACMode
from homeassistant.const import ATTR_ENTITY_ID, ATTR_TEMPERATURE, SERVICE_TURN_OFF, SERVICE_TURN_ON, STATE_ON, STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import HomeAssistant, Context, State, Event

from .pwm_engine import PWMEngine
from .const import KEY_PHYSICAL_SYNC_PREFIX

_LOGGER = logging.getLogger(__name__)

class ZoneSyncManager:
    """Manages the synchronization of state from virtual zone to physical TRVs and Switches."""

    def __init__(
        self,
        hass: HomeAssistant,
        coordinator: Any,
        zone_name: str,
        entity_id: str,
        climates: list[str],
        switches: list[str],
        calibrations: dict[str, str],
    ) -> None:
        """Initialize the sync manager."""
        self.hass = hass
        self._coordinator = coordinator
        self._zone_name = zone_name
        self._entity_id = entity_id
        self._climates = climates
        self._switches = switches
        self._calibrations = calibrations

        self._sync_lock = asyncio.Lock()
        self._trv_event_lock = asyncio.Lock()
        self._last_known_trv_targets: dict[str, float] = {}
        self._pending_trv_targets: dict[str, float] = {}
        self._internal_context = Context()

        self._local_pwm = PWMEngine(pwm_interval=900.0, min_on=0.0, min_off=0.0)
        self._local_pwm_state = False

        self.trv_health: dict[str, dict[str, Any]] = {
            trv: {
                "sync_status": "INITIALIZED",
                "last_command_target": None,
                "last_command_mode": None,
                "last_command_time": None,
                "last_ack_time": None,
                "last_reported_temp": None,
                "latency_s": None,
                "consecutive_timeouts": 0,
                "last_error": None,
            }
            for trv in self._climates
        }

    @property
    def internal_context(self) -> Context:
        """Return the internal context used to flag self-generated events."""
        return self._internal_context

    @property
    def _sync_switch_key(self) -> str:
        """Return the dynamic key for physical sync persistence."""
        safe_name = self._zone_name.lower().replace(" ", "_").replace("-", "_")
        safe_name = "".join(c for c in safe_name if c.isalnum() or c == "_")
        return f"{KEY_PHYSICAL_SYNC_PREFIX}{safe_name}"

    def get_trv_health(self) -> dict[str, Any]:
        """Return sanitized TRV health statistics."""
        sanitized = {}
        for trv, health in self.trv_health.items():
            entry = dict(health)
            entry.pop("last_command_time_monotonic", None)
            sanitized[trv] = entry
        return sanitized

    def init_known_targets(self) -> None:
        """Initialize known targets from HA states."""
        for trv in self._climates:
            st = self.hass.states.get(trv)
            if st and st.attributes.get(ATTR_TEMPERATURE) is not None:
                self._last_known_trv_targets[trv] = float(st.attributes[ATTR_TEMPERATURE])

    async def async_sync_trvs(
        self,
        master_hvac_mode: HVACMode,
        master_target_temp: float | None,
        master_current_temp: float | None,
        safety_fallback_active: bool,
        has_external_sensor: bool,
    ) -> None:
        """Sync target temperature and mode to all sub-slave TRVs."""
        if not self._climates:
            return

        async with self._sync_lock:
            try:
                # If Master is OFF force TRVs OFF
                target_hvac_mode = HVACMode.HEAT if master_hvac_mode != HVACMode.OFF else HVACMode.OFF

                for trv in self._climates:
                    st = self.hass.states.get(trv)
                    if not st:
                        continue

                    mode_changed = (st.state != target_hvac_mode)
                    # Sync HVAC Mode
                    if mode_changed:
                        await self.hass.services.async_call(
                            "climate",
                            "set_hvac_mode",
                            {"entity_id": trv, "hvac_mode": target_hvac_mode},
                            blocking=True,
                            context=self._internal_context,
                        )

                    # When syncing OFF, update last_known so delta is correct on resume
                    if target_hvac_mode == HVACMode.OFF:
                        device_target = st.attributes.get(ATTR_TEMPERATURE)
                        if device_target is not None:
                            self._last_known_trv_targets[trv] = float(device_target)
                        continue

                    # Sync Target Temp & Calibration
                    if master_target_temp is not None:
                        trv_target = master_target_temp
                        calib_entity = self._calibrations.get(trv)
                        trv_current = st.attributes.get("current_temperature")

                        if has_external_sensor and not safety_fallback_active and master_current_temp is not None and trv_current is not None:
                            if calib_entity:
                                calib_state = self.hass.states.get(calib_entity)
                                current_calib_value = float(calib_state.state) if calib_state and calib_state.state not in (STATE_UNAVAILABLE, STATE_UNKNOWN) else 0.0
                                offset = current_calib_value + (master_current_temp - float(trv_current))
                                
                                domain = "number" if not calib_entity.startswith("input_number.") else "input_number"
                                await self.hass.services.async_call(
                                    domain,
                                    "set_value",
                                    {"entity_id": calib_entity, "value": offset},
                                    blocking=True,
                                    context=self._internal_context,
                                )
                            else:
                                trv_target = master_target_temp + (float(trv_current) - master_current_temp)
                                trv_target = max(5.0, min(35.0, trv_target))
                        
                        step = st.attributes.get("target_temp_step", 0.5)
                        if step and float(step) > 0:
                            trv_target = round(trv_target / float(step)) * float(step)

                        trv_min = st.attributes.get("min_temp", 5.0)
                        trv_max = st.attributes.get("max_temp", 35.0)
                        trv_target = max(float(trv_min), min(float(trv_max), trv_target))

                        current_device_target = st.attributes.get(ATTR_TEMPERATURE)
                        if mode_changed or current_device_target != trv_target:
                            health = self.trv_health.setdefault(trv, {})
                            try:
                                await self.hass.services.async_call(
                                    "climate",
                                    "set_temperature",
                                    {"entity_id": trv, "temperature": trv_target},
                                    blocking=True,
                                    context=self._internal_context,
                                )
                                health["last_command_target"] = trv_target
                                health["last_command_mode"] = str(target_hvac_mode)
                                health["last_command_time"] = dt_util.now().isoformat()
                                health["last_command_time_monotonic"] = time.monotonic()
                                health["sync_status"] = "PENDING_CONFIRMATION"

                                self._pending_trv_targets[trv] = trv_target
                                self._coordinator.record_diagnostic_event("TRV_COMMAND_SENT", {
                                    "zone": self._zone_name,
                                    "trv": trv,
                                    "target": trv_target,
                                    "mode": str(target_hvac_mode),
                                })
                            except Exception as err:
                                _LOGGER.error("Failed to send temperature to TRV %s: %s", trv, err)
                                health["sync_status"] = "FAILED"
                                health["consecutive_timeouts"] = health.get("consecutive_timeouts", 0) + 1
                                health["last_error"] = str(err)
                                self._coordinator.record_diagnostic_event("TRV_COMMAND_FAILED", {
                                    "zone": self._zone_name,
                                    "trv": trv,
                                    "error": str(err),
                                })
                                self._pending_trv_targets.pop(trv, None)

                        self._last_known_trv_targets[trv] = trv_target
            except Exception as err:
                _LOGGER.error("Error syncing TRVs in zone %s: %s", self._zone_name, err)

    async def async_pwm_tick(self, master_hvac_mode: HVACMode) -> bool:
        """Evaluate local PWM for switches. Returns True if state changed."""
        if not self._switches:
            return False

        if master_hvac_mode == HVACMode.OFF:
            new_pwm_state = False
        else:
            demand = self._coordinator.get_zone_demand(self._entity_id)
            new_pwm_state = self._local_pwm.calculate(demand)

        if new_pwm_state != self._local_pwm_state:
            self._local_pwm_state = new_pwm_state
            await self.async_sync_switches()
            return True
        return False

    async def async_sync_switches(self) -> None:
        """Turn local switches ON or OFF based on PWM state."""
        if not self._switches:
            return

        service = SERVICE_TURN_ON if self._local_pwm_state else SERVICE_TURN_OFF
        
        for switch in self._switches:
            st = self.hass.states.get(switch)
            if st and st.state != (STATE_ON if self._local_pwm_state else "off"):
                await self.hass.services.async_call(
                    "switch",
                    service,
                    {ATTR_ENTITY_ID: switch},
                    context=self._internal_context,
                )

    async def process_trv_change(
        self,
        event: Event,
        master_context_id: str | None,
        master_hvac_mode: HVACMode,
        master_min_temp: float,
        master_max_temp: float
    ) -> tuple[HVACMode | None, float | None]:
        """
        Handle a physical TRV change.
        Returns (new_hvac_mode, delta_target_temp) if the master needs to update.
        """
        async with self._trv_event_lock:
            if event.context.id in (master_context_id, self._internal_context.id):
                return None, None

            entity_id = event.data.get("entity_id")
            new_state: State | None = event.data.get("new_state")
            old_state: State | None = event.data.get("old_state")

            if not new_state or not old_state:
                return None, None

            new_temp = new_state.attributes.get(ATTR_TEMPERATURE)
            old_temp = self._last_known_trv_targets.get(entity_id)

            physical_sync_enabled = self._coordinator.get_persistent_data(self._sync_switch_key, True)

            if physical_sync_enabled:
                if new_state.state == HVACMode.OFF and old_state.state != HVACMode.OFF:
                    if new_temp is not None:
                        self._last_known_trv_targets[entity_id] = float(new_temp)
                    return HVACMode.OFF if master_hvac_mode != HVACMode.OFF else None, None

                elif new_state.state == HVACMode.HEAT and old_state.state == HVACMode.OFF:
                    if master_hvac_mode != HVACMode.HEAT:
                        return HVACMode.HEAT, None

            if not physical_sync_enabled or master_hvac_mode == HVACMode.OFF or new_state.state == HVACMode.OFF or old_state.state == HVACMode.OFF:
                if new_temp is not None:
                    self._last_known_trv_targets[entity_id] = float(new_temp)
                return None, None

            if entity_id in self._pending_trv_targets:
                pending = self._pending_trv_targets[entity_id]
                if new_temp is not None and abs(float(new_temp) - pending) < 0.01:
                    self._pending_trv_targets.pop(entity_id, None)
                    self._last_known_trv_targets[entity_id] = float(new_temp)
                    health = self.trv_health.setdefault(entity_id, {})
                    sent_mono = health.get("last_command_time_monotonic")
                    latency = round(time.monotonic() - sent_mono, 2) if sent_mono else None
                    health["sync_status"] = "IN_SYNC"
                    health["latency_s"] = latency
                    health["last_ack_time"] = dt_util.now().isoformat()
                    health["last_reported_temp"] = float(new_temp)
                    health["consecutive_timeouts"] = 0
                    self._coordinator.record_diagnostic_event("TRV_CONFIRMED", {
                        "zone": self._zone_name,
                        "trv": entity_id,
                        "target": float(new_temp),
                        "latency_s": latency,
                    })
                    return None, None
                else:
                    return None, None

            if new_temp is not None and old_temp is not None:
                new_temp = float(new_temp)
                old_temp = float(old_temp)
                if abs(new_temp - old_temp) > 0.01:
                    delta = new_temp - old_temp
                    self._coordinator.record_diagnostic_event("TRV_KNOB_DELTA", {
                        "zone": self._zone_name,
                        "trv": entity_id,
                        "delta": round(delta, 1),
                        "old_temp": old_temp,
                        "new_temp": new_temp,
                    })
                    return None, delta

            return None, None

    @property
    def local_pwm_state(self) -> bool:
        """Return the current local PWM state."""
        return self._local_pwm_state
