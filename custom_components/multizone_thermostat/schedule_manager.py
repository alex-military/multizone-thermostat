"""Schedule Profile Manager for Multizone Thermostat (Phase 6).

This module acts as a backward-compatible facade for the modular schedule package.
"""
from __future__ import annotations

from typing import Any

from .schedule import ScheduleProfileManager, default_profiles_dict


def _default_profiles_dict() -> dict[str, dict[str, Any]]:
    """Return default dictionary of base profiles."""
    return default_profiles_dict()


__all__ = ["ScheduleProfileManager", "_default_profiles_dict"]
