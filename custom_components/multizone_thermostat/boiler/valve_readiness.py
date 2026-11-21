"""Shared hydraulic valve-readiness evaluation for TRV-equipped zones."""
from __future__ import annotations

from collections.abc import Mapping
import math
from typing import Any

from ..const import (
    CONF_ZONE_CLIMATES,
    CONF_ZONE_NAME,
    ZONE_MODE_PRIMARY,
    ZONE_MODE_SECONDARY,
    make_zone_entity_id,
)

VALVE_POSITION_ATTRS = (
    "position",
    "valve_position",
    "pi_heating_demand",
    "heating_demand",
    "valve_state",
)
OPEN_STRINGS = ("open", "heating", "on", "true")
CLOSED_STRINGS = ("closed", "close", "idle", "off", "false")
OPEN_THRESHOLD_PCT = 10.0


def is_trv_reported_closed(trv_state: Any) -> bool | None:
    """Return True if a TRV affirmatively reports closed/idle, False if open, or None if unavailable/unknown telemetry."""
    if trv_state is None:
        return None
    raw_state = getattr(trv_state, "state", None)
    if not isinstance(raw_state, str) or raw_state in ("unavailable", "unknown"):
        return None

    attrs = getattr(trv_state, "attributes", None)
    if not isinstance(attrs, Mapping):
        attrs = {}

    for attr in VALVE_POSITION_ATTRS:
        if attr in attrs and attrs[attr] is not None:
            raw_val = attrs[attr]
            if isinstance(raw_val, bool):
                return not raw_val
            try:
                pos_val = float(raw_val)
            except (ValueError, TypeError):
                if isinstance(raw_val, str):
                    low = raw_val.strip().lower()
                    if low in OPEN_STRINGS:
                        return False
                    if low in CLOSED_STRINGS:
                        return True
                continue
            if math.isfinite(pos_val):
                return pos_val <= OPEN_THRESHOLD_PCT

    hvac_action = attrs.get("hvac_action")
    if isinstance(hvac_action, str):
        act_low = hvac_action.strip().lower()
        if act_low == "heating":
            return False
        if act_low in ("idle", "off", "cooling"):
            return True

    return None


def evaluate_trvs_ready(hass: Any, coordinator: Any) -> tuple[bool, bool]:
    """Check whether at least one demanding heating zone has an open water path.

    Returns ``(trvs_ready, has_any_trvs)`` failing open when coordinator metadata
    is absent (e.g. minimal unit-test mocks) or when TRVs expose no telemetry.
    """
    zones = getattr(coordinator, "zones", None)
    if not isinstance(zones, list) or not zones:
        return True, False

    dict_zones = [z for z in zones if isinstance(z, dict)]
    if not dict_zones:
        return True, False

    has_any_trvs = any(
        bool(z.get(CONF_ZONE_CLIMATES) or z.get("climates") or z.get("climate_entities") or [])
        for z in dict_zones
    )
    if not has_any_trvs:
        return True, False

    states_obj = getattr(hass, "states", None)
    demanding_zone_seen = False

    for zone in dict_zones:
        zname = zone.get(CONF_ZONE_NAME) or zone.get("zone_name")
        climate_id = zone.get("climate_id") or (make_zone_entity_id(zname) if isinstance(zname, str) and zname else None)
        if not climate_id:
            continue

        mode = coordinator.get_zone_mode(climate_id) if hasattr(coordinator, "get_zone_mode") else None
        if not isinstance(mode, str):
            continue

        z_demand = coordinator.get_zone_demand(climate_id) if hasattr(coordinator, "get_zone_demand") else None
        if not isinstance(z_demand, (int, float)) or isinstance(z_demand, bool) or z_demand <= 0:
            continue

        if mode not in (ZONE_MODE_PRIMARY, ZONE_MODE_SECONDARY):
            continue

        demanding_zone_seen = True
        trv_list = zone.get(CONF_ZONE_CLIMATES) or zone.get("climates") or zone.get("climate_entities") or []
        if not trv_list:
            return True, has_any_trvs

        for trv in trv_list:
            trv_state = states_obj.get(trv) if states_obj is not None else None
            if trv_state is None:
                continue
            raw_state = getattr(trv_state, "state", None)
            if not isinstance(raw_state, str) or raw_state in ("unavailable", "unknown"):
                continue
            closed = is_trv_reported_closed(trv_state)
            if closed is False or closed is None:
                return True, has_any_trvs

    if not demanding_zone_seen:
        return True, has_any_trvs

    return False, True
