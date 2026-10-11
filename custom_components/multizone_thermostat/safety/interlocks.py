"""Interlocks and safety permissions for boiler and zones."""
from __future__ import annotations

import logging

_LOGGER = logging.getLogger(__name__)


class SafetyInterlocks:
    """Evaluates safety interlocks, permissions, and protections."""

    @staticmethod
    def can_bypass_windows(is_frost_emergency: bool) -> bool:
        """Evaluate if window opening is allowed to bypass/shut down zone heating."""
        if is_frost_emergency:
            _LOGGER.warning("Window bypass blocked by active Anti-Frost emergency.")
            return False
        return True

    @staticmethod
    def can_boiler_fire(
        master_state: bool,
        demand: float,
        is_dhw_active: bool = False,
        frost_emergency: bool = False,
    ) -> tuple[bool, str]:
        """Check whether boiler ignition is permitted under current safety conditions."""
        if frost_emergency:
            return True, "FROST_EMERGENCY"

        if is_dhw_active:
            return False, "DHW_ACTIVE"

        if not master_state:
            return False, "MASTER_OFF"

        if demand <= 0.0:
            return False, "NO_DEMAND"

        return True, "DEMAND_ACTIVE"
