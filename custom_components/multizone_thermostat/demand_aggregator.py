"""Demand Aggregator for Multizone Thermostat.

Manages per-zone heating demands, priority routing (Primary vs Secondary vs Bypass),
weighting, and overall plant demand calculation strategies (MAX, WEIGHTED_AVERAGE, SUM_CAPPED).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Callable

from .const import (
    CONF_ZONE_NAME,
    ZONE_MODE_BYPASS,
    ZONE_MODE_PRIMARY,
    ZONE_MODE_SECONDARY,
    make_zone_entity_id,
)

_LOGGER = logging.getLogger(__name__)

# Demand calculation strategies
DEMAND_STRATEGY_MAX = "max"
DEMAND_STRATEGY_WEIGHTED_AVERAGE = "weighted_average"
DEMAND_STRATEGY_SUM_CAPPED = "sum_capped"

VALID_DEMAND_STRATEGIES = (
    DEMAND_STRATEGY_MAX,
    DEMAND_STRATEGY_WEIGHTED_AVERAGE,
    DEMAND_STRATEGY_SUM_CAPPED,
)

DEFAULT_ZONE_WEIGHT = 1.0


@dataclass
class AggregatedDemand:
    """Result of demand calculation."""

    demand: float
    peak_zone: str | None
    strategy: str
    primary_demands: dict[str, float] = field(default_factory=dict)
    secondary_demands: dict[str, float] = field(default_factory=dict)
    active_primary_count: int = 0
    active_secondary_count: int = 0
    frost_emergency: bool = False
    dhw_active: bool = False

    def __iter__(self):
        """Allow tuple unpacking: (demand, peak_zone) = aggregated_demand."""
        yield self.demand
        yield self.peak_zone


class DemandAggregator:
    """Aggregates zone heating demands according to zone priority and aggregation strategy."""

    def __init__(
        self,
        zones: list[dict[str, Any]] | None = None,
        strategy: str = DEMAND_STRATEGY_MAX,
        mode_getter: Callable[[str], str] | None = None,
    ) -> None:
        """Initialize the demand aggregator.

        :param zones: Optional initial list of zone configuration dictionaries.
        :param strategy: Calculation strategy (max, weighted_average, sum_capped).
        :param mode_getter: Optional external callable to resolve zone mode (e.g. calendar overrides).
        """
        if strategy not in VALID_DEMAND_STRATEGIES:
            raise ValueError(
                f"Invalid strategy '{strategy}'. Must be one of {VALID_DEMAND_STRATEGIES}"
            )

        self._strategy: str = strategy
        self._mode_getter: Callable[[str], str] | None = mode_getter

        # Internal state
        self._zone_demands: dict[str, float] = {}
        self._zone_modes: dict[str, str] = {}
        self._zone_weights: dict[str, float] = {}
        self._zone_names: dict[str, str] = {}

        # Callbacks
        self._on_demand_changed_listeners: list[Callable[[str, float], None]] = []
        self._climate_callbacks: dict[str, list[Callable[[], None]]] = {}

        if zones:
            for zone_cfg in zones:
                name = zone_cfg.get(CONF_ZONE_NAME, "")
                if name:
                    weight = float(zone_cfg.get("weight", DEFAULT_ZONE_WEIGHT))
                    climate_id = zone_cfg.get("climate_id", None)
                    self.register_zone(name=name, climate_id=climate_id, weight=weight)

    @property
    def strategy(self) -> str:
        """Return the current demand aggregation strategy."""
        return self._strategy

    @strategy.setter
    def strategy(self, new_strategy: str) -> None:
        """Set demand aggregation strategy."""
        if new_strategy not in VALID_DEMAND_STRATEGIES:
            raise ValueError(
                f"Invalid strategy '{new_strategy}'. Must be one of {VALID_DEMAND_STRATEGIES}"
            )
        self._strategy = new_strategy
        _LOGGER.debug("Demand aggregation strategy updated to '%s'", new_strategy)

    def register_zone(
        self,
        name: str,
        climate_id: str | None = None,
        weight: float = DEFAULT_ZONE_WEIGHT,
        mode: str = ZONE_MODE_PRIMARY,
    ) -> str:
        """Register a new zone in the aggregator.

        :param name: Human-friendly name of the zone.
        :param climate_id: Entity ID of the climate device (auto-generated if None).
        :param weight: Weight for weighted average calculations (e.g., surface area or kW).
        :param mode: Priority mode (primary, secondary, bypass).
        :return: The climate_id key used for tracking.
        """
        if not climate_id:
            climate_id = make_zone_entity_id(name)

        self._zone_names[climate_id] = name
        self._zone_modes[climate_id] = mode
        self._zone_weights[climate_id] = max(0.0, float(weight))
        self._zone_demands.setdefault(climate_id, 0.0)

        _LOGGER.debug(
            "Registered zone '%s' (id=%s, mode=%s, weight=%.2f)",
            name,
            climate_id,
            mode,
            weight,
        )
        return climate_id

    def register_climate_callback(
        self, climate_id: str, callback: Callable[[], None]
    ) -> None:
        """Register a callback for climate state changes when demand changes."""
        self._climate_callbacks.setdefault(climate_id, []).append(callback)

    def unregister_climate_callback(self, climate_id: str) -> None:
        """Unregister all climate callbacks for a zone."""
        self._climate_callbacks.pop(climate_id, None)

    def register_on_demand_changed(
        self, callback: Callable[[str, float], None]
    ) -> None:
        """Register a general listener called when any zone's demand changes."""
        self._on_demand_changed_listeners.append(callback)

    # -------------------------------------------------------------
    # Demand Management
    # -------------------------------------------------------------
    def get_zone_demand(self, climate_id: str) -> float:
        """Get the current demand (0-100%) for a zone."""
        return self._zone_demands.get(climate_id, 0.0)

    def set_zone_demand(self, climate_id: str, demand: float) -> None:
        """Set the demand for a zone with clamping and trigger callbacks if changed."""
        clamped_demand = min(100.0, max(0.0, float(demand)))
        old_demand = self._zone_demands.get(climate_id)
        self._zone_demands[climate_id] = clamped_demand

        if old_demand != clamped_demand:
            _LOGGER.debug(
                "Zone '%s' demand changed: %.1f%% -> %.1f%%",
                climate_id,
                old_demand if old_demand is not None else 0.0,
                clamped_demand,
            )
            # Notify general listeners
            for listener in self._on_demand_changed_listeners:
                try:
                    listener(climate_id, clamped_demand)
                except Exception:
                    _LOGGER.exception("Error executing on_demand_changed listener")

            # Notify climate callbacks
            if climate_id in self._climate_callbacks:
                for cb in self._climate_callbacks[climate_id]:
                    try:
                        cb()
                    except Exception:
                        _LOGGER.exception(
                            "Error executing climate callback for %s", climate_id
                        )

    def get_all_demands(self) -> dict[str, float]:
        """Return a copy of all current zone demands."""
        return dict(self._zone_demands)

    def reset_zone_demand(self, climate_id: str) -> None:
        """Reset demand of a single zone to 0.0%."""
        self.set_zone_demand(climate_id, 0.0)

    def reset_all_demands(self) -> None:
        """Reset demands of all zones to 0.0%."""
        for cid in list(self._zone_demands.keys()):
            self.set_zone_demand(cid, 0.0)

    # -------------------------------------------------------------
    # Mode & Priority Routing
    # -------------------------------------------------------------
    def get_zone_mode(self, climate_id: str) -> str:
        """Get the effective zone mode, prioritizing external mode_getter if configured."""
        if self._mode_getter is not None:
            external_mode = self._mode_getter(climate_id)
            if external_mode is not None:
                return external_mode
        return self._zone_modes.get(climate_id, ZONE_MODE_PRIMARY)

    def set_zone_mode(self, climate_id: str, mode: str) -> None:
        """Set the priority mode of a zone."""
        self._zone_modes[climate_id] = mode
        _LOGGER.debug("Zone '%s' mode set to '%s'", climate_id, mode)

    def load_saved_modes(self, saved_modes: dict[str, str]) -> None:
        """Load and update zone modes from persistent storage."""
        for cid, mode in saved_modes.items():
            self._zone_modes[cid] = mode

    def is_primary(self, climate_id: str) -> bool:
        """Return True if the zone is in PRIMARY mode."""
        return self.get_zone_mode(climate_id) == ZONE_MODE_PRIMARY

    def is_secondary(self, climate_id: str) -> bool:
        """Return True if the zone is in SECONDARY mode."""
        return self.get_zone_mode(climate_id) == ZONE_MODE_SECONDARY

    def is_bypassed(self, climate_id: str) -> bool:
        """Return True if the zone is in BYPASS mode."""
        return self.get_zone_mode(climate_id) == ZONE_MODE_BYPASS

    # -------------------------------------------------------------
    # Weight Management
    # -------------------------------------------------------------
    def get_zone_weight(self, climate_id: str) -> float:
        """Get the weight configured for a zone."""
        return self._zone_weights.get(climate_id, DEFAULT_ZONE_WEIGHT)

    def set_zone_weight(self, climate_id: str, weight: float) -> None:
        """Set weight for a zone (e.g. area in m² or radiator power)."""
        self._zone_weights[climate_id] = max(0.0, float(weight))

    def set_zone_weights(self, weights: dict[str, float]) -> None:
        """Update multiple zone weights."""
        for cid, w in weights.items():
            self.set_zone_weight(cid, w)

    # -------------------------------------------------------------
    # Calculation & Aggregation
    # -------------------------------------------------------------
    def calculate(
        self,
        zones: list[dict[str, Any]] | None = None,
        frost_emergency: bool = False,
        is_dhw_active: bool = False,
    ) -> AggregatedDemand:
        """Calculate aggregated plant demand and determine peak zone.

        Routing rules:
        - DHW active: heating demand is immediately suppressed to 0.0%.
        - Frost emergency: heating demand is immediately forced to 100.0% with peak_zone="Frost Emergency".
        - Primary zones: drive boiler demand according to active strategy.
        - Secondary zones: tracked separately; do NOT trigger boiler heating on their own.
        - Bypass zones: completely ignored.

        :param zones: Optional list of zone configurations. If None, uses all registered zones.
        :param frost_emergency: Whether an active anti-frost emergency is ongoing.
        :param is_dhw_active: Whether Domestic Hot Water is currently being produced.
        :return: AggregatedDemand object (also unpackable as (demand, peak_zone)).
        """
        # Resolve target zones to evaluate
        zone_entries: list[tuple[str, str]] = []  # (climate_id, display_name)
        if zones is not None:
            for z in zones:
                name = z.get(CONF_ZONE_NAME, "")
                cid = z.get("climate_id") or make_zone_entity_id(name)
                zone_entries.append((cid, name))
        else:
            for cid, name in self._zone_names.items():
                zone_entries.append((cid, name))

        primary_demands: dict[str, float] = {}
        secondary_demands: dict[str, float] = {}

        for cid, name in zone_entries:
            mode = self.get_zone_mode(cid)
            demand = self.get_zone_demand(cid)

            coord = getattr(self, "coordinator", None)
            if coord and hasattr(coord, "plant_diagnostics") and coord.plant_diagnostics.has_critical_sensor_fault(cid):
                demand = 0.0

            if mode == ZONE_MODE_BYPASS:
                continue
            elif mode == ZONE_MODE_SECONDARY:
                secondary_demands[name] = demand
            else:
                # ZONE_MODE_PRIMARY (or default)
                primary_demands[name] = demand

        active_primary = sum(1 for d in primary_demands.values() if d > 0.0)
        active_secondary = sum(1 for d in secondary_demands.values() if d > 0.0)

        # 1. Domestic Hot Water Priority Interlock
        if is_dhw_active:
            _LOGGER.debug("DHW is active: plant heating demand suppressed to 0.0%%")
            return AggregatedDemand(
                demand=0.0,
                peak_zone=None,
                strategy=self._strategy,
                primary_demands=primary_demands,
                secondary_demands=secondary_demands,
                active_primary_count=active_primary,
                active_secondary_count=active_secondary,
                frost_emergency=False,
                dhw_active=True,
            )

        # 2. Frost Emergency Priority Override
        if frost_emergency:
            _LOGGER.debug("Frost emergency active: plant heating demand forced to 100.0%%")
            return AggregatedDemand(
                demand=100.0,
                peak_zone="Frost Emergency",
                strategy=self._strategy,
                primary_demands=primary_demands,
                secondary_demands=secondary_demands,
                active_primary_count=active_primary,
                active_secondary_count=active_secondary,
                frost_emergency=True,
                dhw_active=False,
            )

        # 3. Normal Aggregation (evaluated over Primary zones)
        if not primary_demands:
            return AggregatedDemand(
                demand=0.0,
                peak_zone=None,
                strategy=self._strategy,
                primary_demands=primary_demands,
                secondary_demands=secondary_demands,
                active_primary_count=0,
                active_secondary_count=active_secondary,
                frost_emergency=False,
                dhw_active=False,
            )

        # Calculate peak zone and demand by strategy
        if self._strategy == DEMAND_STRATEGY_MAX:
            peak_demand = 0.0
            peak_zone = None
            for name, demand in primary_demands.items():
                if demand > peak_demand:
                    peak_demand = demand
                    peak_zone = name
            final_demand = peak_demand

        elif self._strategy == DEMAND_STRATEGY_WEIGHTED_AVERAGE:
            # Weighted average over active primary zones (demand > 0)
            active_items = []
            for cid, name in zone_entries:
                demand = primary_demands.get(name, 0.0)
                if demand > 0.0:
                    active_items.append((cid, name, demand))

            if not active_items:
                final_demand = 0.0
                peak_zone = None
            else:
                weighted_sum = sum(
                    demand * self.get_zone_weight(cid)
                    for cid, _, demand in active_items
                )
                weight_sum = sum(
                    self.get_zone_weight(cid)
                    for cid, _, _ in active_items
                )
                if weight_sum > 0:
                    final_demand = min(100.0, max(0.0, round(weighted_sum / weight_sum, 2)))
                else:
                    final_demand = max(d for _, _, d in active_items)

                # Peak zone is the one with highest demand among primary
                peak_item = max(active_items, key=lambda item: item[2])
                peak_zone = peak_item[1]

        elif self._strategy == DEMAND_STRATEGY_SUM_CAPPED:
            total_sum = sum(primary_demands.values())
            final_demand = min(100.0, max(0.0, round(total_sum, 2)))
            if final_demand > 0.0:
                # Peak zone is the one with highest individual demand
                peak_zone = max(primary_demands.items(), key=lambda item: item[1])[0]
            else:
                peak_zone = None

        else:
            final_demand = 0.0
            peak_zone = None

        return AggregatedDemand(
            demand=final_demand,
            peak_zone=peak_zone,
            strategy=self._strategy,
            primary_demands=primary_demands,
            secondary_demands=secondary_demands,
            active_primary_count=active_primary,
            active_secondary_count=active_secondary,
            frost_emergency=False,
            dhw_active=False,
        )

    def has_active_primary_demand(self) -> bool:
        """Return True if any primary zone has demand > 0%."""
        for cid, demand in self._zone_demands.items():
            if self.is_primary(cid) and demand > 0.0:
                return True
        return False

    def has_active_secondary_demand(self) -> bool:
        """Return True if any secondary zone has demand > 0%."""
        for cid, demand in self._zone_demands.items():
            if self.is_secondary(cid) and demand > 0.0:
                return True
        return False

    def is_secondary_only_active(self) -> bool:
        """Return True if only secondary zones have demand (no primary demand).

        This is useful to detect parasitic heat requests while the main generator is idle.
        """
        return self.has_active_secondary_demand() and not self.has_active_primary_demand()
