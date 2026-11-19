"""Deterministic Chaos Engine & Plant Simulator wired to multizone_thermostat."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
import math
import pathlib
import random
import sys
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

_SIM_DIR = pathlib.Path(__file__).resolve().parent
_TESTS_DIR = _SIM_DIR.parent
_REPO_ROOT = _TESTS_DIR.parent
_DUMMY_HA = _TESTS_DIR / "dummy_ha"
for _p in (str(_SIM_DIR), str(_REPO_ROOT), str(_DUMMY_HA)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from custom_components.multizone_thermostat.boiler.opentherm_backend import OpenThermBoilerBackend
from custom_components.multizone_thermostat.const import (
    CONF_ZONE_CLIMATES,
    CONF_ZONE_NAME,
    CONF_ZONE_TEMP_SENSOR,
    HVAC_MODE_HEAT,
    KEY_ANTI_FROST_ENABLED,
    KEY_FROST_PROTECTION_TEMP,
    KEY_PHYSICAL_SYNC_PREFIX,
    ZONE_MODE_PRIMARY,
    from_celsius,
    make_zone_entity_id,
    to_celsius,
)
from custom_components.multizone_thermostat.demand_aggregator import DemandAggregator
from custom_components.multizone_thermostat.plant_diagnostics.engine import PlantDiagnosticsEngine
from custom_components.multizone_thermostat.safety.frost import FrostManager
from custom_components.multizone_thermostat.sync_manager import ZoneSyncManager
from custom_components.multizone_thermostat.zone_controller import ZoneController
from thermal_simulator import PlantSimulator, SimulatedRoom


@dataclass
class WeatherProfile:
    """Daily sinusoidal outdoor temperature profile with optional cold snap."""

    base_temp_c: float = 4.0
    daily_amp_c: float = 5.0
    cold_snap_day: int | None = 3
    cold_snap_drop_c: float = 10.0

    def outdoor_temp(self, t_sec: float) -> float:
        day = int(t_sec // 86400)
        hour = (t_sec % 86400) / 3600.0
        diurnal = -self.daily_amp_c * math.cos(2.0 * math.pi * (hour - 5.0) / 24.0)
        snap = -self.cold_snap_drop_c if (self.cold_snap_day is not None and day == self.cold_snap_day) else 0.0
        return self.base_temp_c + diurnal + snap


@dataclass
class ChaosConfig:
    """Configuration for a reproducible chaos simulation run."""

    seed: int = 42
    days: int = 3
    dt_sec: float = 60.0
    noise_std_c: float = 0.05
    dhw_prob_per_hour: float = 0.12
    dropout_prob_per_hour: float = 0.03
    setpoint_change_prob_per_hour: float = 0.05
    fahrenheit_mode: bool = False
    high_inertia_hysteresis: bool = False
    mid_cycle_restart_step: int | None = None
    inject_fault_mode: str | None = None
    weather: WeatherProfile = field(default_factory=WeatherProfile)


@dataclass
class ChaosReport:
    """Summary of a completed chaos simulation run."""

    seed: int
    steps: int
    simulated_hours: float
    dhw_events: int = 0
    sensor_dropouts: int = 0
    setpoint_changes: int = 0
    frost_activations: int = 0
    restart_events: int = 0
    outbound_temp_commands: int = 0
    violations: list[str] = field(default_factory=list)
    energy_delivered_wh: float = 0.0
    discomfort_degree_hours: float = 0.0


async def async_run_chaos_simulation(cfg: ChaosConfig | None = None) -> ChaosReport:
    """Run an accelerated multi-day chaos simulation against the real controller."""
    cfg = cfg or ChaosConfig()
    rng = random.Random(cfg.seed)

    zones_cfg = [
        {CONF_ZONE_NAME: "Salotto", CONF_ZONE_TEMP_SENSOR: "sensor.salotto_temp", CONF_ZONE_CLIMATES: ["climate.trv_salotto"]},
        {CONF_ZONE_NAME: "Cucina", CONF_ZONE_TEMP_SENSOR: "sensor.cucina_temp", CONF_ZONE_CLIMATES: []},
    ]
    cid_salotto = make_zone_entity_id("Salotto")
    cid_cucina = make_zone_entity_id("Cucina")
    zone_ids = [cid_salotto, cid_cucina]

    states_map: dict[str, SimpleNamespace] = {}
    hass = MagicMock()
    hass.config.units.temperature_unit = "°F" if cfg.fahrenheit_mode else "°C"
    hass.states.get = MagicMock(side_effect=lambda eid: states_map.get(eid))
    hass.services.async_call = AsyncMock()
    hass.async_create_task = MagicMock(side_effect=lambda coro: coro.close() if hasattr(coro, "close") else None)

    coord = MagicMock()
    coord.hass = hass
    coord.zones = zones_cfg
    coord.weather_sensor_id = "sensor.outdoor_temp"
    coord.is_dhw_active = False
    coord.get_master_state = MagicMock(return_value=True)
    coord.has_mixing_valve = False
    coord.is_modulating_plant = True
    coord.enable_heat_pump = False
    coord.enable_energy_management = False
    coord.energy_manager = None
    coord.split_manager = None
    coord._async_set_hvac_mode = AsyncMock()

    def _persistent(key: str, default=None):
        if key == KEY_ANTI_FROST_ENABLED:
            return True
        if key == KEY_FROST_PROTECTION_TEMP:
            return 8.0
        if key.startswith(KEY_PHYSICAL_SYNC_PREFIX):
            return True
        if key == "weather_curve":
            return 1.0
        return default if default is not None else 0.0

    coord.get_persistent_data = MagicMock(side_effect=_persistent)

    agg = DemandAggregator(strategy="max")
    for z in zones_cfg:
        cid = make_zone_entity_id(z[CONF_ZONE_NAME])
        agg.register_zone(z[CONF_ZONE_NAME], climate_id=cid, weight=1.0, mode=ZONE_MODE_PRIMARY)

    coord.demand_aggregator = agg
    coord.get_zone_demand = agg.get_zone_demand
    coord.set_zone_demand = agg.set_zone_demand
    coord.zone_manager = MagicMock()
    coord.zone_manager.get_zone_mode = agg.get_zone_mode
    coord.zone_manager.get_zone = MagicMock(
        side_effect=lambda cid: zones_cfg[0] if cid == cid_salotto else zones_cfg[1]
    )
    coord.get_zone_mode = agg.get_zone_mode
    coord.plant_diagnostics = PlantDiagnosticsEngine(coord)
    coord.frost_manager = FrostManager(hass, coord)
    coord.anti_frost = coord.frost_manager
    coord.storage = MagicMock()
    coord.storage.async_save_autotuner_states = AsyncMock()
    coord.storage.async_save_thermal_states = AsyncMock()

    zc = ZoneController(hass, coord)
    if cfg.high_inertia_hysteresis:
        zc.get_thermal_model(cid_salotto).thermal_inertia = 0.8
    else:
        tuner_c = zc.get_autotuner(cid_cucina)
        tuner_c.state = tuner_c.STATE_COMPLETED
        zc.get_pid(cid_cucina).set_pid_param(kp=25.0, ki=0.04, kd=0.0)
        zc.get_thermal_model(cid_cucina).thermal_inertia = 0.3

    ot = OpenThermBoilerBackend(hass, coord, "climate.ot_boiler", 35.0, 75.0)
    trv_sync = ZoneSyncManager(hass, coord, "Salotto", cid_salotto, ["climate.trv_salotto"], [], {})

    sim = PlantSimulator(
        rooms=[
            SimulatedRoom(name="Salotto", current_temp=18.8, target_temp=20.0, thermal_capacity=900.0, heat_loss_coeff=45.0),
            SimulatedRoom(name="Cucina", current_temp=19.0, target_temp=19.5, thermal_capacity=800.0, heat_loss_coeff=40.0),
        ],
        t_out=cfg.weather.outdoor_temp(0.0),
    )

    targets = {cid_salotto: 20.0, cid_cucina: 19.5}
    dhw_remaining_s = 0.0
    dropout_remaining_s = {cid_salotto: 0.0, cid_cucina: 0.0}
    total_steps = int((cfg.days * 86400.0) / cfg.dt_sec)
    report = ChaosReport(seed=cfg.seed, steps=total_steps, simulated_hours=(total_steps * cfg.dt_sec) / 3600.0)

    p_dhw = cfg.dhw_prob_per_hour * (cfg.dt_sec / 3600.0)
    p_drop = cfg.dropout_prob_per_hour * (cfg.dt_sec / 3600.0)
    p_sp = cfg.setpoint_change_prob_per_hour * (cfg.dt_sec / 3600.0)

    prev_salotto_demand = 0.0
    mono_t = 1000.0

    with patch("time.monotonic", side_effect=lambda: mono_t):
        for step in range(total_steps):
            t_sec = step * cfg.dt_sec
            mono_t = 1000.0 + t_sec
            t_out = cfg.weather.outdoor_temp(t_sec)
            sim.t_out = t_out

            if cfg.fahrenheit_mode:
                t_out_rep = round(from_celsius(t_out, hass), 2)
                states_map["sensor.outdoor_temp"] = SimpleNamespace(
                    state=f"{t_out_rep:.2f}", attributes={"unit_of_measurement": "°F"}
                )
            else:
                states_map["sensor.outdoor_temp"] = SimpleNamespace(
                    state=f"{t_out:.2f}", attributes={"unit_of_measurement": "°C"}
                )

            states_map["climate.ot_boiler"] = SimpleNamespace(
                state="heat" if sim.boiler.ch_enabled else "off",
                attributes={"temperature": round(from_celsius(sim.boiler.target_flow_temp, hass), 1)},
            )
            states_map["climate.trv_salotto"] = SimpleNamespace(
                state="heat",
                attributes={
                    "temperature": round(from_celsius(targets[cid_salotto], hass), 1),
                    "current_temperature": round(from_celsius(sim.rooms["Salotto"].current_temp, hass), 1),
                    "min_temp": round(from_celsius(5.0, hass), 1),
                    "max_temp": round(from_celsius(35.0, hass), 1),
                    "target_temp_step": 0.5,
                },
            )

            # Simulated Home Assistant mid-cycle restart
            if cfg.mid_cycle_restart_step is not None and step == cfg.mid_cycle_restart_step:
                at_dump = {
                    "heat": {cid: zc.get_autotuner(cid, "heat").dump_state() for cid in zone_ids},
                    "cool": {cid: zc.get_autotuner(cid, "cool").dump_state() for cid in zone_ids},
                }
                tm_dump = {cid: zc.get_thermal_model(cid).dump_state() for cid in zone_ids}
                zc = ZoneController(hass, coord)
                zc.load_state(at_dump, tm_dump)
                report.restart_events += 1

            # Random DHW burst
            if dhw_remaining_s <= 0.0 and rng.random() < p_dhw:
                dhw_remaining_s = rng.uniform(600.0, 1500.0)
                report.dhw_events += 1
            if dhw_remaining_s > 0.0:
                coord.is_dhw_active = True
                dhw_remaining_s -= cfg.dt_sec
            else:
                coord.is_dhw_active = False

            # Random setpoint nudges (skip Salotto in high-inertia hysteresis test to hold stable band)
            for cid in zone_ids:
                if cfg.high_inertia_hysteresis and cid == cid_salotto:
                    continue
                if rng.random() < p_sp:
                    targets[cid] = round(rng.uniform(18.5, 21.5) * 2.0) / 2.0
                    report.setpoint_changes += 1

            # Update sensors + run real ZoneController
            for cid, rname in ((cid_salotto, "Salotto"), (cid_cucina, "Cucina")):
                room = sim.rooms[rname]
                room.target_temp = targets[cid]

                if dropout_remaining_s[cid] <= 0.0 and rng.random() < p_drop:
                    dropout_remaining_s[cid] = rng.uniform(120.0, 300.0)
                    report.sensor_dropouts += 1

                sensor_id = "sensor.salotto_temp" if cid == cid_salotto else "sensor.cucina_temp"
                if dropout_remaining_s[cid] > 0.0:
                    dropout_remaining_s[cid] -= cfg.dt_sec
                    states_map[sensor_id] = SimpleNamespace(state="unavailable", attributes={})
                    sensed_c = room.current_temp
                else:
                    noisy = round(room.current_temp + rng.gauss(0.0, cfg.noise_std_c), 2)
                    if cfg.fahrenheit_mode:
                        f_val = from_celsius(noisy, hass)
                        states_map[sensor_id] = SimpleNamespace(
                            state=f"{f_val:.2f}", attributes={"unit_of_measurement": "°F"}
                        )
                        sensed_c = to_celsius(f_val, "°F", hass)
                    else:
                        states_map[sensor_id] = SimpleNamespace(
                            state=f"{noisy:.2f}", attributes={"unit_of_measurement": "°C"}
                        )
                        sensed_c = noisy

                if cfg.fahrenheit_mode:
                    z_attrs = {
                        "current_temperature": round(from_celsius(sensed_c, hass), 2),
                        "temperature": round(from_celsius(targets[cid], hass), 2),
                    }
                else:
                    z_attrs = {"current_temperature": sensed_c, "temperature": targets[cid]}

                z_state = SimpleNamespace(state=HVAC_MODE_HEAT, attributes=z_attrs)
                states_map[cid] = z_state
                dem = await zc.async_update_zone(cid, z_state)

                if cfg.inject_fault_mode == "bad_demand" and step == 10 and cid == cid_salotto:
                    dem = 150.0

                if not (0.0 <= dem <= 100.0):
                    report.violations.append(f"step={step} {cid}: demand out of bounds ({dem})")

                if cfg.high_inertia_hysteresis and cid == cid_salotto:
                    tuner_s = zc.get_autotuner(cid_salotto)
                    if (
                        tuner_s.state != tuner_s.STATE_COMPLETED
                        and not coord.is_dhw_active
                        and prev_salotto_demand == 100.0
                        and sensed_c < targets[cid_salotto] - 1e-6
                        and dem == 0.0
                    ):
                        report.violations.append(
                            f"step={step} Salotto: hysteresis collapsed OFF at {sensed_c:.2f}C < target {targets[cid_salotto]:.2f}C"
                        )
                    prev_salotto_demand = dem

                room.valve_pct = dem

            hass.services.async_call.reset_mock()
            frost_active = await coord.frost_manager.async_handle_frost_emergencies()
            if frost_active:
                report.frost_activations += 1

            agg_res = agg.calculate(is_dhw_active=coord.is_dhw_active, frost_emergency=frost_active)
            if not (0.0 <= agg_res.demand <= 100.0):
                report.violations.append(f"step={step}: plant demand out of bounds ({agg_res.demand})")

            if coord.is_dhw_active and not frost_active and agg_res.demand != 0.0:
                report.violations.append(f"step={step}: DHW active but plant demand={agg_res.demand}")

            # Exercise OpenTherm + TRV Sync every 5 steps (or on step 10 for mutation tests)
            if step % 5 == 0 or (cfg.inject_fault_mode == "raw_celsius_in_f" and step == 10):
                await ot.async_update(agg_res.demand, agg_res.peak_zone, frost_active)
                await trv_sync.async_sync_trvs(
                    HVAC_MODE_HEAT, targets[cid_salotto], sim.rooms["Salotto"].current_temp, False, True
                )
                if cfg.inject_fault_mode == "raw_celsius_in_f" and step == 10:
                    await hass.services.async_call("climate", "set_temperature", {"entity_id": "climate.test", "temperature": 11.0})

            # Outbound Fahrenheit Oracle: every set_temperature in °F mode must be >= 41.0 °F (5.0 °C)
            for call in hass.services.async_call.call_args_list:
                if len(call.args) >= 3 and call.args[1] == "set_temperature":
                    report.outbound_temp_commands += 1
                    sent_t = call.args[2].get("temperature")
                    if cfg.fahrenheit_mode and isinstance(sent_t, (int, float)) and sent_t < 41.0:
                        report.violations.append(
                            f"step={step}: raw Celsius value {sent_t} sent to set_temperature in Fahrenheit mode"
                        )

            # Drive simulated boiler
            sim.boiler.dhw_active = coord.is_dhw_active
            sim.boiler.ch_enabled = (not coord.is_dhw_active) and (agg_res.demand > 0.0 or frost_active)
            sim.boiler.target_flow_temp = 55.0 if sim.boiler.ch_enabled else 20.0
            sim.step(cfg.dt_sec)

            # Check room temperature physical sanity
            for rname, room in sim.rooms.items():
                if room.current_temp < 5.0 or room.current_temp > 35.0:
                    report.violations.append(f"step={step} {rname}: implausible room temp {room.current_temp:.2f}°C")

    report.energy_delivered_wh = sum(r.energy_delivered_wh for r in sim.rooms.values())
    report.discomfort_degree_hours = sum(r.discomfort_degree_hours for r in sim.rooms.values())
    return report


def run_chaos_simulation(cfg: ChaosConfig | None = None) -> ChaosReport:
    """Synchronous wrapper for running a chaos simulation."""
    return asyncio.run(async_run_chaos_simulation(cfg))
