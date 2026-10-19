"""Parser for Calendar events in Multizone Thermostat."""
import logging
from typing import Any, Dict

from .const import GLOBAL_PRESETS, ZONE_MODE_BYPASS, ZONE_MODE_PRIMARY, ZONE_MODES

_LOGGER = logging.getLogger(__name__)

class CalendarOverride:
    def __init__(self, is_permanent: bool = False, temperature: float | None = None, mode: str | None = None):
        self.is_permanent = is_permanent
        self.temperature = temperature
        self.mode = mode

    def __repr__(self):
        return f"Override(perm={self.is_permanent}, temp={self.temperature}, mode={self.mode})"


def parse_calendar_event(title: str) -> dict[str, Any]:
    """
    Parses a calendar event title.
    Returns a dict with:
    - 'global_preset': str | None (e.g. 'eco', 'comfort', 'away', 'sleep', 'manual')
    - 'global_temperature': float | None (if the whole title is just a number)
    - 'overrides': dict[zone_name_lower, CalendarOverride]
    """
    result = {
        "global_preset": None,
        "global_temperature": None,
        "overrides": {}
    }

    if not title:
        return result

    parts = [p.strip() for p in title.split(",")]
    if not parts:
        return result

    # Check the first part
    first_part = parts[0]
    if ":" not in first_part:
        # It's a global command
        first_part_lower = first_part.lower()
        try:
            # Maybe it's a global temperature? e.g. "21.5"
            val = float(first_part_lower)
            result["global_temperature"] = val
        except ValueError:
            # Only accept valid global presets so ordinary calendar events are ignored
            if first_part_lower in GLOBAL_PRESETS:
                result["global_preset"] = first_part_lower
        
        override_parts = parts[1:]
    else:
        override_parts = parts

    valid_modes = set(ZONE_MODES)

    for part in override_parts:
        if ":" not in part:
            continue
            
        zone_str, cmd_str = part.split(":", 1)
        zone_name = zone_str.strip().lower()
        
        commands = cmd_str.strip().lower().split()
        
        override = CalendarOverride()
        
        for cmd in commands:
            if cmd == "set":
                override.is_permanent = True
            elif cmd in valid_modes:
                override.mode = cmd
            elif cmd == "off":
                override.mode = ZONE_MODE_BYPASS
            elif cmd == "standalone":
                override.mode = ZONE_MODE_PRIMARY
            else:
                try:
                    override.temperature = float(cmd)
                except ValueError:
                    _LOGGER.warning("Unknown calendar command for zone %s: %s", zone_name, cmd)
                    
        result["overrides"][zone_name] = override

    return result
