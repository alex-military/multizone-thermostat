"""Tests for Telemetry subview, native SVG chart bundle, translations, and sensor telemetry attributes."""
from __future__ import annotations

import re
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

from custom_components.multizone_thermostat.const import (
    CONF_ZONES,
    CONF_ZONE_CLIMATES,
    CONF_ZONE_NAME,
    CONF_ZONE_SPLIT_CLIMATE,
    CONF_ZONE_SWITCHES,
    CONF_ZONE_TEMP_SENSOR,
    CONF_ZONE_VALVES,
    DOMAIN,
    make_zone_entity_id,
)
from custom_components.multizone_thermostat.coordinator import MultizoneCoordinator
from custom_components.multizone_thermostat.sensor import (
    DemandSensor,
    MultizoneMasterDemandSensor,
)


def _make_coord_with_zones(zones_cfg: list[dict], extra_attrs: dict | None = None):
    hass = MagicMock()
    hass.states = MagicMock()
    hass.states.get.return_value = None
    entry = MagicMock()
    entry.entry_id = "telemetry_test_entry"
    entry.version = 1
    entry.domain = DOMAIN
    entry.title = "Telemetry Test"
    entry.data = {CONF_ZONES: zones_cfg}
    entry.options = {}
    coord = MultizoneCoordinator(hass, entry)
    coord.storage = MagicMock()
    coord.storage.async_save_autotuner_states = AsyncMock()
    if extra_attrs:
        for k, v in extra_attrs.items():
            setattr(coord, k, v)
    return hass, coord


def test_demand_sensor_exposes_actuator_type_kloss_and_hysteresis_bounds() -> None:
    zones_cfg = [
        {CONF_ZONE_NAME: "Living", CONF_ZONE_TEMP_SENSOR: "sensor.living_t", CONF_ZONE_VALVES: ["valve.living"]},
        {CONF_ZONE_NAME: "Kitchen", CONF_ZONE_TEMP_SENSOR: "sensor.kitchen_t", CONF_ZONE_SWITCHES: ["switch.kitchen"]},
        {CONF_ZONE_NAME: "Bedroom", CONF_ZONE_TEMP_SENSOR: "sensor.bedroom_t", CONF_ZONE_SPLIT_CLIMATE: "climate.split_bed"},
        {CONF_ZONE_NAME: "Office", CONF_ZONE_TEMP_SENSOR: "sensor.office_t", CONF_ZONE_CLIMATES: ["climate.trv_office"]},
    ]
    hass, coord = _make_coord_with_zones(zones_cfg)
    zc = coord.zone_controller

    # Configure mock climate entity PWM state for Kitchen
    kitchen_cid = make_zone_entity_id("Kitchen")
    coord._climate_entities = {kitchen_cid: SimpleNamespace(_local_pwm_state=True)}

    # Inject k_loss and hysteresis mode on Living
    living_cid = make_zone_entity_id("Living")
    zc.get_thermal_model(living_cid).k_loss = 0.0215
    zc._last_zone_telemetry[living_cid] = {"control_mode": "hysteresis", "active_track": "heat"}

    living_ds = DemandSensor(hass, "telemetry_test_entry", "Living", living_cid, coord)
    living_attrs = living_ds.extra_state_attributes
    assert living_attrs["actuator_type"] == "valve"
    assert living_attrs["k_loss"] == 0.0215
    assert living_attrs["hysteresis_cold_tol"] == 0.3
    assert living_attrs["hysteresis_hot_tol"] == 0.3

    kitchen_ds = DemandSensor(hass, "telemetry_test_entry", "Kitchen", kitchen_cid, coord)
    kitchen_attrs = kitchen_ds.extra_state_attributes
    assert kitchen_attrs["actuator_type"] == "pwm_relay"
    assert kitchen_attrs["pwm_output_on"] is True

    bed_cid = make_zone_entity_id("Bedroom")
    bed_attrs = zc.get_zone_demand_attributes(bed_cid)
    assert bed_attrs["actuator_type"] == "split"

    off_cid = make_zone_entity_id("Office")
    off_attrs = zc.get_zone_demand_attributes(off_cid)
    assert off_attrs["actuator_type"] == "trv"


def test_master_demand_sensor_exposes_boiler_type_and_live_metrics() -> None:
    hass, coord = _make_coord_with_zones(
        [{CONF_ZONE_NAME: "Living", CONF_ZONE_TEMP_SENSOR: "sensor.living_t"}]
    )
    coord.get_master_state = lambda: True

    # 1. Relay backend
    coord.boiler_mode = "relay"
    coord.boiler_backend = SimpleNamespace(is_modulating=False, _last_known_boiler_on=True, status_reason="ON - Demand 60%")
    coord.enable_heat_pump = False
    coord.heat_pump_backend = None
    coord.plant_orchestrator = SimpleNamespace(
        last_aggregate=SimpleNamespace(
            demand=60.0, peak_zone="Living", strategy="max", dhw_active=False,
            frost_emergency=False, primary_demands={"Living": 60.0}, secondary_demands={},
        )
    )
    ms = MultizoneMasterDemandSensor(hass, "telemetry_test_entry", coord)
    attrs_relay = ms.extra_state_attributes
    assert attrs_relay["boiler_type"] == "relay"
    assert attrs_relay["boiler_active"] is True

    # 2. OpenTherm backend + live OT diagnostics
    coord.boiler_mode = "opentherm"
    coord.boiler_backend = SimpleNamespace(is_modulating=True, status_reason="MODULATING")
    coord.plant_diagnostics = SimpleNamespace(
        get_opentherm_diagnostics=lambda: {
            "enabled": True,
            "flame_active": True,
            "flow_temperature": 48.0,
            "return_temperature": 39.5,
            "modulation_level": 44,
            "water_pressure": 1.4,
            "condensing_optimal": True,
        }
    )
    attrs_ot = ms.extra_state_attributes
    assert attrs_ot["boiler_type"] == "opentherm"
    assert attrs_ot["flow_temp"] == 48.0
    assert attrs_ot["return_temp"] == 39.5
    assert attrs_ot["modulation_level"] == 44
    assert attrs_ot["flame_active"] is True

    # 3. Heat Pump (Bivalent) + Energy Manager
    coord.enable_heat_pump = True
    coord.enable_gas_heater = True
    coord.heat_pump_backend = SimpleNamespace(_last_state_on=True, status_reason="PDC ON")
    coord.energy_manager = SimpleNamespace(is_solar_boost_active=lambda: True, _last_battery_soc=86.0)
    attrs_hp = ms.extra_state_attributes
    assert attrs_hp["boiler_type"] == "heat_pump"
    assert attrs_hp["is_bivalent"] is True
    assert attrs_hp["solar_boost_active"] is True
    assert attrs_hp["battery_soc"] == 86.0

    # 4. Centralized backend
    coord.enable_heat_pump = False
    coord.heat_pump_backend = None
    coord.boiler_mode = "central"
    coord.boiler_backend = SimpleNamespace(is_modulating=False, status_reason="CENTRAL")
    coord.plant_diagnostics = None
    attrs_cent = ms.extra_state_attributes
    assert attrs_cent["boiler_type"] == "centralized"


def test_telemetry_bundle_symbols_and_translation_parity() -> None:
    root = Path(__file__).resolve().parent.parent
    bundle = (root / "custom_components" / "multizone_thermostat" / "www" / "multizone-thermostat-card.js").read_text(encoding="utf-8")

    for sym in (
        "mzBuildSvgChart",
        "mzBindChartTooltips",
        "multizone-thermostat-telemetry-card",
        "ll-strategy-view-multizone-thermostat-telemetry",
        "copy_snapshot_btn",
        "tel_open_charts_btn",
        "history/history_during_period",
    ):
        assert sym in bundle, f"Missing expected telemetry symbol {sym!r} in built card bundle"

    # Check 100% key parity across all 6 languages in frontend/src/01_translations.js
    trans_src = (root / "frontend" / "src" / "01_translations.js").read_text(encoding="utf-8")
    blocks = re.findall(r"^  ([a-z]{2}): \{(.*?)\n  \},?(?:\n|$)", trans_src, flags=re.S | re.M)
    assert len(blocks) == 6, f"Expected 6 language blocks, found {len(blocks)}"
    keys_by_lang = {}
    for lang, body in blocks:
        keys = set(re.findall(r"^\s*([a-zA-Z0-9_]+):", body, flags=re.M))
        keys_by_lang[lang] = keys

    base_keys = keys_by_lang["en"]
    assert "tel_copy_snapshot" in base_keys
    assert "tel_title" in base_keys
    for lang, kset in keys_by_lang.items():
        missing = base_keys - kset
        extra = kset - base_keys
        assert not missing and not extra, f"Translation key mismatch in {lang!r}: missing={missing}, extra={extra}"
