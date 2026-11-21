"""Simulatore termico d'impianto a tempo accelerato (v2, logica pura)."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Tuple


@dataclass
class SimulatedRoom:
    name: str
    target_temp: float = 20.0
    current_temp: float = 19.0
    valve_pct: float = 0.0               # 0..100%
    thermal_capacity: float = 1200.0     # Wh/K (aria + muri interni)
    heat_loss_coeff: float = 60.0        # W/K verso l'esterno
    emitter_power_nom: float = 1800.0    # W al DT nominale
    emitter_exponent: float = 1.3        # ~1.3 radiatori, ~1.1 pavimento radiante
    emitter_nominal_dt: float = 50.0     # K: (75+65)/2 - 20
    water_dt: float = 10.0               # K salto mandata-ritorno assunto (75/65)
    sensor_fault: bool = False
    last_reported_temp: float | None = 19.0
    energy_delivered_wh: float = 0.0
    discomfort_degree_hours: float = 0.0
    overshoot_degree_hours: float = 0.0

    def step(self, dt_hours: float, t_flow: float, t_out: float) -> None:
        p_loss_w = (self.current_temp - t_out) * self.heat_loss_coeff

        p_gain_w = 0.0
        if self.valve_pct > 0.0:
            t_mean_water = t_flow - self.water_dt / 2.0
            dt_emitter = max(0.0, t_mean_water - self.current_temp)
            ratio = (dt_emitter / self.emitter_nominal_dt) ** self.emitter_exponent
            p_gain_w = self.emitter_power_nom * (self.valve_pct / 100.0) * ratio

        self.current_temp += ((p_gain_w - p_loss_w) * dt_hours) / self.thermal_capacity
        self.energy_delivered_wh += p_gain_w * dt_hours
        self.overshoot_degree_hours += max(0.0, self.current_temp - self.target_temp) * dt_hours
        self.discomfort_degree_hours += (
            max(0.0, self.target_temp - self.current_temp)
            + max(0.0, self.current_temp - (self.target_temp + 0.5))
        ) * dt_hours

        self.last_reported_temp = None if self.sensor_fault else round(self.current_temp, 2)


@dataclass
class SimulatedBoiler:
    ch_enabled: bool = False
    dhw_active: bool = False
    target_flow_temp: float = 35.0
    current_flow_temp: float = 20.0
    inertia_tau_hours: float = 0.05
    idle_temp: float = 20.0

    def step(self, dt_hours: float) -> None:
        target = self.target_flow_temp if self.ch_enabled else self.idle_temp
        alpha = dt_hours / (self.inertia_tau_hours + dt_hours)
        self.current_flow_temp += alpha * (target - self.current_flow_temp)


@dataclass
class SimulatedHeatPump:
    enabled: bool = False
    running: bool = False
    available: bool = True
    target_flow_temp: float = 35.0
    current_flow_temp: float = 20.0
    inertia_tau_hours: float = 0.08
    idle_temp: float = 20.0
    min_cycle_on_hours: float = 5.0 / 60.0
    min_cycle_off_hours: float = 5.0 / 60.0
    hours_in_current_state: float = 1.0
    enforce_protection: bool = True
    elapsed_hours: float = 0.0
    command_log: List[Tuple[float, bool]] = field(default_factory=list)
    protection_rejections: int = 0
    _last_wanted: bool | None = None

    def step(self, dt_hours: float, wanted_on: bool) -> None:
        self.elapsed_hours += dt_hours
        self.hours_in_current_state += dt_hours
        if wanted_on != self._last_wanted:
            self.command_log.append((self.elapsed_hours, wanted_on))
            self._last_wanted = wanted_on

        if not self.available:
            self.running = False
        elif self.running and not wanted_on:
            if self.hours_in_current_state >= self.min_cycle_on_hours or not self.enforce_protection:
                self.running = False
                self.hours_in_current_state = 0.0
            else:
                self.protection_rejections += 1
        elif not self.running and wanted_on:
            if self.hours_in_current_state >= self.min_cycle_off_hours or not self.enforce_protection:
                self.running = True
                self.hours_in_current_state = 0.0
            else:
                self.protection_rejections += 1

        target = self.target_flow_temp if self.running else self.idle_temp
        alpha = dt_hours / (self.inertia_tau_hours + dt_hours)
        self.current_flow_temp += alpha * (target - self.current_flow_temp)


class PlantSimulator:
    MAX_SUBSTEP_S = 60.0

    def __init__(self, rooms: List[SimulatedRoom], t_out: float = 5.0):
        self.rooms: Dict[str, SimulatedRoom] = {r.name: r for r in rooms}
        self.boiler = SimulatedBoiler()
        self.heat_pump = SimulatedHeatPump()
        self.t_out = t_out
        self.simulated_time_hours: float = 0.0
        self.last_effective_flow: float = t_out

    def _substep(self, dt_seconds: float) -> None:
        dt_hours = dt_seconds / 3600.0
        self.simulated_time_hours += dt_hours

        flows = []
        if self.boiler.ch_enabled or self.boiler.current_flow_temp > (self.boiler.idle_temp + 0.1):
            flows.append(self.boiler.current_flow_temp)
        if self.heat_pump.running or self.heat_pump.current_flow_temp > (self.heat_pump.idle_temp + 0.1):
            flows.append(self.heat_pump.current_flow_temp)
        self.last_effective_flow = max(flows) if flows else self.t_out

        for room in self.rooms.values():
            room.step(dt_hours, self.last_effective_flow, self.t_out)

        self.boiler.step(dt_hours)
        self.heat_pump.step(dt_hours, wanted_on=self.heat_pump.enabled)

    def step(self, dt_seconds: float = 30.0) -> None:
        if dt_seconds <= 0:
            raise ValueError("dt_seconds deve essere > 0")
        remaining = dt_seconds
        while remaining > 1e-9:
            chunk = min(self.MAX_SUBSTEP_S, remaining)
            self._substep(chunk)
            remaining -= chunk
