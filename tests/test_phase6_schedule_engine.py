"""Comprehensive tests for Phase 6: Core Scheduling, Smart Start, and Smart Return."""

import sys
from unittest.mock import AsyncMock, MagicMock, patch

# Ensure dummy_ha modules are used rather than any leftover HomeAssistantMockFinder from earlier test files
sys.meta_path[:] = [
    f for f in sys.meta_path if f.__class__.__name__ != "HomeAssistantMockFinder"
]
for _mod_name in (
    "homeassistant.components.switch",
    "homeassistant.components.select",
    "homeassistant.helpers.restore_state",
    "homeassistant.helpers.entity",
    "custom_components.multizone_thermostat.switch",
    "custom_components.multizone_thermostat.select",
):
    if _mod_name in sys.modules and (isinstance(sys.modules[_mod_name], MagicMock) or "dummy_ha" not in getattr(sys.modules[_mod_name], "__file__", "")):
        del sys.modules[_mod_name]

from datetime import datetime, timedelta, timezone

import homeassistant.util.dt as dt_util
import pytest

from homeassistant.components.climate.const import HVACMode
from homeassistant.const import ATTR_TEMPERATURE

from custom_components.multizone_thermostat.calendar_manager import CalendarManager
from custom_components.multizone_thermostat.calendar_parser import CalendarOverride, parse_calendar_event
from custom_components.multizone_thermostat.climate import MultizoneVirtualThermostat
from custom_components.multizone_thermostat.const import (
    CONF_ZONE_CLIMATES,
    CONF_ZONE_NAME,
    CONF_ZONE_SWITCHES,
    CONF_ZONE_TARGET_TEMP,
    DEFAULT_BASELINE_PRESET,
    DEFAULT_PRESET_TEMPS,
    DEFAULT_SCHEDULE_PROFILE,
    DOMAIN,
    KEY_ACTIVE_PROFILE,
    KEY_PROFILE_EXPIRES_AT,
    KEY_SCHEDULER_ENABLED,
    SCHEDULE_DAYS,
    ZONE_MODE_PRIMARY,
    make_zone_entity_id,
)
from custom_components.multizone_thermostat.schedule_manager import ScheduleProfileManager
from custom_components.multizone_thermostat.zone_manager import ZoneManager


@pytest.fixture
def mock_hass():
    """Create a mock Home Assistant instance."""
    import asyncio
    hass = MagicMock()
    hass.states = MagicMock()
    hass.states.get = MagicMock(return_value=None)
    hass.services = AsyncMock()
    hass.services.async_call = AsyncMock()

    def _create_task(coro):
        if hasattr(coro, "__await__"):
            return asyncio.create_task(coro)
        return coro

    hass.async_create_task = MagicMock(side_effect=_create_task)
    return hass


@pytest.fixture
def mock_coordinator(mock_hass):
    """Create a mock Coordinator with storage and zone manager."""
    coordinator = MagicMock()
    coordinator.hass = mock_hass
    coordinator.entry_id = "test_entry"
    coordinator.boiler_switch = "switch.boiler"
    coordinator.zones = [
        {
            CONF_ZONE_NAME: "Soggiorno",
            CONF_ZONE_TARGET_TEMP: 20.5,
            CONF_ZONE_CLIMATES: ["climate.trv_soggiorno"],
            CONF_ZONE_SWITCHES: ["switch.actuator_soggiorno"],
        },
        {
            CONF_ZONE_NAME: "Camera",
            CONF_ZONE_TARGET_TEMP: 19.0,
            CONF_ZONE_CLIMATES: ["climate.trv_camera"],
        },
        {
            CONF_ZONE_NAME: "Bagno",
            CONF_ZONE_TARGET_TEMP: 21.0,
            CONF_ZONE_CLIMATES: ["climate.trv_bagno"],
        },
    ]

    coordinator._settings = {}
    coordinator._settings_store = AsyncMock()
    coordinator._settings_store.async_save = AsyncMock()
    coordinator._async_save_presets_storage = AsyncMock()

    def get_persistent(key, default=None):
        return coordinator._settings.get(key, default)

    async def async_set_persistent(key, value):
        coordinator._settings[key] = value

    coordinator.get_persistent_data = MagicMock(side_effect=get_persistent)
    coordinator.async_set_persistent_data = AsyncMock(side_effect=async_set_persistent)

    coordinator.zone_manager = ZoneManager(mock_hass, coordinator)
    coordinator.zone_manager.load_state({}, {}, {})
    coordinator.get_global_preset = coordinator.zone_manager.get_global_preset
    coordinator.async_set_global_preset = coordinator.zone_manager.async_set_global_preset

    coordinator.calendar_manager = CalendarManager(coordinator)
    coordinator.schedule_manager = ScheduleProfileManager(coordinator)

    coordinator._climate_callbacks = {}
    coordinator._climate_entities = {}
    coordinator._diagnostics_history = []

    def record_diag(event_type, details=None):
        entry = {"type": event_type}
        if details:
            entry.update(details)
        coordinator._diagnostics_history.append(entry)

    coordinator.record_diagnostic_event = MagicMock(side_effect=record_diag)

    def get_demand(cid):
        return 0.0

    coordinator.get_zone_demand = MagicMock(side_effect=get_demand)
    coordinator.set_zone_demand = MagicMock()
    coordinator.get_zone_mode = MagicMock(return_value=ZONE_MODE_PRIMARY)
    coordinator.demand_aggregator = MagicMock()
    coordinator.demand_aggregator.get_zone_weight = MagicMock(return_value=1.0)

    mock_hass.data = {DOMAIN: {"test_entry": {"coordinator": coordinator}}}
    return coordinator


# ============================================================================
# 1. Parsing di preset per zona & Risoluzione dinamica in CalendarManager
# ============================================================================

def test_calendar_parser_per_zone_presets():
    """Verify calendar title parser extracts presets per zone accurately."""
    title = "Soggiorno: comfort, Camera: eco, Bagno: 22.0, Studio: set away"
    parsed = parse_calendar_event(title)

    assert parsed["global_preset"] is None
    assert parsed["global_temperature"] is None

    ovs = parsed["overrides"]
    assert "soggiorno" in ovs
    assert ovs["soggiorno"].preset == "comfort"
    assert ovs["soggiorno"].temperature is None
    assert ovs["soggiorno"].is_permanent is False

    assert "camera" in ovs
    assert ovs["camera"].preset == "eco"
    assert ovs["camera"].temperature is None

    assert "bagno" in ovs
    assert ovs["bagno"].temperature == 22.0
    assert ovs["bagno"].preset is None

    assert "studio" in ovs
    assert ovs["studio"].preset == "away"
    assert ovs["studio"].is_permanent is True


@pytest.mark.asyncio
async def test_calendar_manager_resolves_presets_without_disk_overwrite(mock_coordinator):
    """Verify CalendarManager resolves dynamic presets and doesn't pollute stored presets."""
    cal = mock_coordinator.calendar_manager
    cid_soggiorno = make_zone_entity_id("Soggiorno")
    cid_camera = make_zone_entity_id("Camera")
    cid_bagno = make_zone_entity_id("Bagno")

    # Set custom comfort temp in zone_manager
    mock_coordinator.zone_manager.update_preset_temperature("comfort", cid_soggiorno, 21.5)
    orig_presets_copy = dict(mock_coordinator.zone_manager._presets)

    now = datetime(2026, 10, 31, 10, 0, tzinfo=timezone.utc)
    current_events = [
        {
            "start": (now - timedelta(hours=1)).isoformat(),
            "end": (now + timedelta(hours=1)).isoformat(),
            "summary": "Soggiorno: comfort, Camera: eco, Bagno: 22.0",
        }
    ]

    await cal._async_process_calendar_events(current_events, None, now)

    # Dynamic resolution:
    # Soggiorno comfort -> 21.5 (from stored preset)
    # Camera eco -> 18.0 (from DEFAULT_PRESET_TEMPS)
    # Bagno -> 22.0 (explicit float)
    assert cal.current_event_overrides[cid_soggiorno] == 21.5
    assert cal.current_event_overrides[cid_camera] == 18.0
    assert cal.current_event_overrides[cid_bagno] == 22.0

    # Ensure presets in zone_manager were NOT overwritten for camera or bagno
    assert "eco" not in mock_coordinator.zone_manager._presets or cid_camera not in mock_coordinator.zone_manager._presets.get("eco", {})


# ============================================================================
# 2. Risoluzione blocchi orari per zona e Fallback deterministico a baseline
# ============================================================================

@pytest.mark.asyncio
async def test_schedule_resolution_and_baseline_gap_fallback(mock_coordinator):
    """Verify slot evaluation for blocks, midnight handling, and gap fallback to baseline."""
    sched = mock_coordinator.schedule_manager
    await sched.async_set_scheduler_enabled(True)

    cid_soggiorno = make_zone_entity_id("Soggiorno")

    # Configure Monday blocks:
    # Block 1: 06:30 - 08:30 (comfort)
    # Block 2: 18:00 - 24:00 (comfort)
    profile_data = {
        "name": "Standard",
        "baseline_preset": "eco",
        "days": {
            "mon": {
                cid_soggiorno: [
                    {"start": "06:30", "end": "08:30", "preset": "comfort"},
                    {"start": "18:00", "end": "24:00", "preset": "comfort"},
                ]
            }
        },
    }
    await sched.async_save_profile("standard", profile_data)

    # 1. At 07:15 on Monday (Inside block 1)
    mon_0715 = datetime(2026, 11, 2, 7, 15, tzinfo=timezone.utc) # 2026-11-02 is Monday
    slot = sched.evaluate_zone_slot(cid_soggiorno, mon_0715)
    assert slot["state_type"] == "block"
    assert slot["preset"] == "comfort"
    assert slot["target_temp"] == 20.5
    assert slot["slot_id"] == "mon_06:30_08:30_comfort"
    assert slot["until"] == mon_0715.replace(hour=8, minute=30, second=0, microsecond=0)

    # 2. At 12:00 on Monday (Gap between block 1 and block 2)
    mon_1200 = datetime(2026, 11, 2, 12, 0, tzinfo=timezone.utc)
    slot_gap = sched.evaluate_zone_slot(cid_soggiorno, mon_1200)
    assert slot_gap["state_type"] == "baseline"
    assert slot_gap["preset"] == "eco"
    assert slot_gap["target_temp"] == 18.0
    assert slot_gap["until"] == mon_1200.replace(hour=18, minute=0, second=0, microsecond=0)

    # 3. At 21:00 on Monday (Inside block 2 touching 24:00)
    mon_2100 = datetime(2026, 11, 2, 21, 0, tzinfo=timezone.utc)
    slot_night = sched.evaluate_zone_slot(cid_soggiorno, mon_2100)
    assert slot_night["state_type"] == "block"
    assert slot_night["preset"] == "comfort"
    assert slot_night["until"] == (mon_2100 + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)

    # Check upcoming blocks within 24h from 05:00 Monday
    mon_0500 = datetime(2026, 11, 2, 5, 0, tzinfo=timezone.utc)
    upcoming = sched.get_upcoming_blocks(cid_soggiorno, mon_0500, horizon_hours=24)
    assert len(upcoming) == 2
    assert upcoming[0]["preset"] == "comfort"
    assert upcoming[0]["start_dt"] == mon_0500.replace(hour=6, minute=30, second=0, microsecond=0)
    assert upcoming[1]["start_dt"] == mon_0500.replace(hour=18, minute=0, second=0, microsecond=0)


# ============================================================================
# 3. Modifica profilo inattivo in background senza perturbare le zone
# ============================================================================

@pytest.mark.asyncio
async def test_modify_inactive_profile_in_background(mock_coordinator):
    """Verify modifying an inactive profile (e.g. holiday) does not affect active profile."""
    sched = mock_coordinator.schedule_manager
    await sched.async_set_scheduler_enabled(True)

    cid_soggiorno = make_zone_entity_id("Soggiorno")

    # Active profile is 'standard'
    assert sched.active_profile == "standard"
    mon_1000 = datetime(2026, 11, 2, 10, 0, tzinfo=timezone.utc)
    await sched.async_evaluate_schedule(mon_1000)
    orig_target = sched.get_effective_target(cid_soggiorno)

    # Modify 'holiday' in background
    holiday_data = {
        "name": "Vacanze Invernali",
        "baseline_preset": "away",
        "days": {
            "mon": {
                "Soggiorno": [{"start": "09:00", "end": "22:00", "preset": "sleep"}]
            }
        },
    }
    await sched.async_save_profile("holiday", holiday_data, now=mon_1000)

    # Verify holiday was saved with normalized keys
    assert sched.profiles["holiday"]["name"] == "Vacanze Invernali"
    assert sched.profiles["holiday"]["baseline_preset"] == "away"
    assert cid_soggiorno in sched.profiles["holiday"]["days"]["mon"]

    # Verify active profile and target are unchanged
    assert sched.active_profile == "standard"
    assert sched.get_effective_target(cid_soggiorno) == orig_target


# ============================================================================
# 4. Attivazione temporanea con expires_at, persistenza e auto-ripristino
# ============================================================================

@pytest.mark.asyncio
async def test_temporary_profile_activation_expiry_and_restore(mock_coordinator):
    """Verify profile expires_at reverts to fallback, persists to storage, and survives reboot."""
    sched = mock_coordinator.schedule_manager
    await sched.async_set_scheduler_enabled(True)

    now = datetime(2026, 11, 2, 14, 0, tzinfo=timezone.utc)
    expiry = now + timedelta(hours=3)

    # Activate 'holiday' for 3 hours with fallback to 'standard'
    await sched.async_activate_profile("holiday", expires_at=expiry, fallback_profile="standard", now=now)
    assert sched.active_profile == "holiday"
    assert sched.profile_expires_at == expiry.isoformat()
    assert sched.fallback_profile == "standard"

    # Verify persisted in coordinator settings
    assert mock_coordinator._settings[KEY_ACTIVE_PROFILE] == "holiday"
    assert mock_coordinator._settings[KEY_PROFILE_EXPIRES_AT] == expiry.isoformat()

    # Simulate restart: load_from_storage in fresh manager
    new_manager = ScheduleProfileManager(mock_coordinator)
    new_manager.load_from_storage()
    assert new_manager.active_profile == "holiday"
    assert new_manager.profile_expires_at == expiry.isoformat()
    assert new_manager.fallback_profile == "standard"

    # 1 hour later: still holiday
    now_plus_1h = now + timedelta(hours=1)
    assert new_manager.check_profile_expiry(now_plus_1h) is False
    assert new_manager.active_profile == "holiday"

    # 3 hours + 1 minute later: expired!
    now_expired = now + timedelta(hours=3, minutes=1)
    assert new_manager.check_profile_expiry(now_expired) is True
    assert new_manager.active_profile == "standard"
    assert new_manager.profile_expires_at is None

    # Check diagnostic event was logged
    diag_events = [e for e in mock_coordinator._diagnostics_history if e.get("type") == "SCHEDULE_PROFILE_EXPIRED"]
    assert len(diag_events) == 1
    assert diag_events[0]["expired_profile"] == "holiday"
    assert diag_events[0]["fallback_profile"] == "standard"


# ============================================================================
# 5. Deroga manuale (record_manual_override) fino al prossimo cambio fascia
# ============================================================================

@pytest.mark.asyncio
async def test_manual_override_persists_until_slot_transition_without_preset_pollution(mock_coordinator, mock_hass):
    """Verify manual override lasts until slot change and does not corrupt _presets."""
    sched = mock_coordinator.schedule_manager
    await sched.async_set_scheduler_enabled(True)

    cid_soggiorno = make_zone_entity_id("Soggiorno")

    # Profile: Mon 06:30-08:30 comfort (20.5), baseline eco (18.0)
    profile_data = {
        "name": "Standard",
        "baseline_preset": "eco",
        "days": {
            "mon": {
                cid_soggiorno: [{"start": "06:30", "end": "08:30", "preset": "comfort"}]
            }
        },
    }
    await sched.async_save_profile("standard", profile_data)

    zone_data = mock_coordinator.zones[0]
    thermostat = MultizoneVirtualThermostat(hass=mock_hass, entry_id="test_entry", zone_data=zone_data)
    thermostat.async_write_ha_state = MagicMock()
    thermostat._hvac_mode = HVACMode.HEAT
    thermostat._target_temperature = 20.0
    mock_coordinator._climate_entities[cid_soggiorno] = thermostat

    # 1. At 07:00 (inside 06:30-08:30 block)
    t_0700 = datetime(2026, 11, 2, 7, 0, tzinfo=timezone.utc)
    await sched.async_evaluate_schedule(t_0700)
    assert thermostat.target_temperature == 20.5

    # 2. User increases temp to 22.5 at 07:15 via async_set_temperature
    t_0715 = datetime(2026, 11, 2, 7, 15, tzinfo=timezone.utc)
    with patch("homeassistant.util.dt.now", return_value=t_0715):
        await thermostat.async_set_temperature(temperature=22.5)

    assert thermostat.target_temperature == 22.5
    assert cid_soggiorno in sched.manual_overrides
    assert sched.manual_overrides[cid_soggiorno]["target_temp"] == 22.5
    assert sched.manual_overrides[cid_soggiorno]["slot_id"] == "mon_06:30_08:30_comfort"

    # Verify extra state attributes
    assert thermostat.extra_state_attributes["schedule_manual_override"] is True
    assert thermostat.extra_state_attributes["schedule_override_until"] is not None

    # Verify preset in zone_manager was NOT modified!
    comfort_stored = mock_coordinator.zone_manager._presets.get("comfort", {}).get(cid_soggiorno, {}).get("target_temp")
    assert comfort_stored != 22.5

    # 3. At 07:45 (still within block 06:30-08:30), override stays active
    t_0745 = datetime(2026, 11, 2, 7, 45, tzinfo=timezone.utc)
    await sched.async_evaluate_schedule(t_0745)
    assert thermostat.target_temperature == 22.5
    assert cid_soggiorno in sched.manual_overrides

    # 4. At 08:30:01 (transition to gap!), manual override automatically expires
    t_0830 = datetime(2026, 11, 2, 8, 30, 1, tzinfo=timezone.utc)
    await sched.async_evaluate_schedule(t_0830)
    assert cid_soggiorno not in sched.manual_overrides
    assert thermostat.target_temperature == 18.0 # reverts to baseline eco!
    assert thermostat.extra_state_attributes["schedule_manual_override"] is False


# ============================================================================
# 6. Spegnimento esplicito (HVACMode.OFF) preservato nei cambi di fascia
# ============================================================================

@pytest.mark.asyncio
async def test_explicit_off_preserved_across_slot_transitions(mock_coordinator, mock_hass):
    """Verify Explicit OFF rule prevents scheduler from turning on a turned-off zone."""
    sched = mock_coordinator.schedule_manager
    await sched.async_set_scheduler_enabled(True)

    cid_soggiorno = make_zone_entity_id("Soggiorno")

    # Profile has block 06:30-08:30 comfort
    profile_data = {
        "name": "Standard",
        "baseline_preset": "eco",
        "days": {
            "mon": {
                cid_soggiorno: [{"start": "06:30", "end": "08:30", "preset": "comfort"}]
            }
        },
    }
    await sched.async_save_profile("standard", profile_data)

    zone_data = mock_coordinator.zones[0]
    thermostat = MultizoneVirtualThermostat(hass=mock_hass, entry_id="test_entry", zone_data=zone_data)
    thermostat.async_write_ha_state = MagicMock()
    thermostat._hvac_mode = HVACMode.OFF # User turned zone OFF
    thermostat._target_temperature = 18.0
    mock_coordinator._climate_entities[cid_soggiorno] = thermostat

    # Even if an old manual override existed, it gets purged
    sched.manual_overrides[cid_soggiorno] = {"target_temp": 24.0, "slot_id": "mon_06:30_08:30_comfort", "until": "..."}

    # At 07:00 (during comfort block)
    t_0700 = datetime(2026, 11, 2, 7, 0, tzinfo=timezone.utc)
    await sched.async_evaluate_schedule(t_0700)

    # Explicit OFF:
    # 1. Manual overrides purged
    assert cid_soggiorno not in sched.manual_overrides
    # 2. Schedule overrides has no active entry forcing target
    assert sched.get_effective_target(cid_soggiorno) is None
    # 3. HVAC mode remains OFF
    assert thermostat.hvac_mode == HVACMode.OFF


# ============================================================================
# 7. Duplicazione profilo
# ============================================================================

@pytest.mark.asyncio
async def test_duplicate_profile(mock_coordinator):
    """Verify deep duplication of profiles."""
    sched = mock_coordinator.schedule_manager
    cid_soggiorno = make_zone_entity_id("Soggiorno")

    profile_data = {
        "name": "Smart Working",
        "baseline_preset": "sleep",
        "days": {
            "fri": {cid_soggiorno: [{"start": "08:00", "end": "18:00", "preset": "comfort"}]}
        },
    }
    await sched.async_save_profile("smart_working", profile_data)

    await sched.async_duplicate_profile("smart_working", "custom_friday", target_name="Venerdì Speciale")

    assert "custom_friday" in sched.profiles
    assert sched.profiles["custom_friday"]["name"] == "Venerdì Speciale"
    assert sched.profiles["custom_friday"]["baseline_preset"] == "sleep"
    assert sched.profiles["custom_friday"]["days"]["fri"][cid_soggiorno][0]["start"] == "08:00"

    # Mutating original doesn't affect copy
    sched.profiles["smart_working"]["days"]["fri"][cid_soggiorno][0]["start"] = "09:00"
    assert sched.profiles["custom_friday"]["days"]["fri"][cid_soggiorno][0]["start"] == "08:00"


# ============================================================================
# 8. Predictive Smart Start Staggered by Heating Rate
# ============================================================================

@pytest.mark.asyncio
async def test_predictive_smart_start_staggered_by_heating_rate(mock_coordinator, mock_hass):
    """Verify predictive smart start staggers ignition according to each zone's heating rate."""
    sched = mock_coordinator.schedule_manager
    await sched.async_set_scheduler_enabled(True)

    cid_soggiorno = make_zone_entity_id("Soggiorno")
    cid_bagno = make_zone_entity_id("Bagno")

    # Thermal models:
    # Soggiorno: heating_rate = 1.0 °C/h
    # Bagno: heating_rate = 2.5 °C/h
    tm_soggiorno = MagicMock()
    tm_soggiorno.heating_rate = 1.0
    tm_bagno = MagicMock()
    tm_bagno.heating_rate = 2.5
    mock_coordinator._thermal_models = {
        cid_soggiorno: tm_soggiorno,
        cid_bagno: tm_bagno,
    }

    # Current temperatures in HA states:
    # Soggiorno: 18.5 °C (target comfort 20.5 °C -> delta 2.0 -> needs 2.0h)
    # Bagno: 18.5 °C (target comfort 21.0 °C -> delta 2.5 -> needs 1.0h)
    state_soggiorno = MagicMock()
    state_soggiorno.attributes = {"current_temperature": 18.5}
    state_bagno = MagicMock()
    state_bagno.attributes = {"current_temperature": 18.5}

    def mock_states_get(eid):
        if eid == cid_soggiorno:
            return state_soggiorno
        if eid == cid_bagno:
            return state_bagno
        return None

    mock_hass.states.get = MagicMock(side_effect=mock_states_get)

    # Schedule: Monday 18:00 - 22:00 comfort, baseline eco (18.0)
    profile_data = {
        "name": "Standard",
        "baseline_preset": "eco",
        "days": {
            "mon": {
                cid_soggiorno: [{"start": "18:00", "end": "22:00", "preset": "comfort"}],
                cid_bagno: [{"start": "18:00", "end": "22:00", "preset": "comfort"}],
            }
        },
    }
    await sched.async_save_profile("standard", profile_data)

    # 1. At 15:30 on Monday: neither zone is in preheat yet
    # Soggiorno starts at 18:00 - 2.0h = 16:00
    # Bagno starts at 18:00 - 1.0h = 17:00
    mon_1530 = datetime(2026, 11, 2, 15, 30, tzinfo=timezone.utc)
    await sched.async_evaluate_schedule(mon_1530)
    assert sched.get_effective_target(cid_soggiorno) == 18.0
    assert sched.get_effective_target(cid_bagno) == 18.0
    assert cid_soggiorno not in sched.smart_start_info
    assert cid_bagno not in sched.smart_start_info

    # 2. At 16:15 on Monday:
    # Soggiorno (preheat from 16:00) is ACTIVE!
    # Bagno (preheat from 17:00) is NOT YET active!
    mon_1615 = datetime(2026, 11, 2, 16, 15, tzinfo=timezone.utc)
    await sched.async_evaluate_schedule(mon_1615)
    assert sched.get_effective_target(cid_soggiorno) == 20.5
    assert cid_soggiorno in sched.smart_start_info
    assert sched.smart_start_info[cid_soggiorno]["source"] == "schedule"
    assert sched.get_effective_target(cid_bagno) == 18.0
    assert cid_bagno not in sched.smart_start_info

    # 3. At 17:15 on Monday:
    # Both Soggiorno and Bagno are in active preheat!
    mon_1715 = datetime(2026, 11, 2, 17, 15, tzinfo=timezone.utc)
    await sched.async_evaluate_schedule(mon_1715)
    assert sched.get_effective_target(cid_soggiorno) == 20.5
    assert sched.get_effective_target(cid_bagno) == 21.0
    assert cid_soggiorno in sched.smart_start_info
    assert cid_bagno in sched.smart_start_info


# ============================================================================
# 9. Smart Start Recalculated on Profile Switch
# ============================================================================

@pytest.mark.asyncio
async def test_smart_start_recalculated_on_profile_switch(mock_coordinator, mock_hass):
    """Verify switching active profile while smart start is active recalculates immediately."""
    sched = mock_coordinator.schedule_manager
    await sched.async_set_scheduler_enabled(True)

    cid_soggiorno = make_zone_entity_id("Soggiorno")

    tm = MagicMock()
    tm.heating_rate = 1.0
    mock_coordinator._thermal_models = {cid_soggiorno: tm}

    state_soggiorno = MagicMock()
    state_soggiorno.attributes = {"current_temperature": 18.5}
    mock_hass.states.get = MagicMock(return_value=state_soggiorno)

    # Standard has Monday 18:00 comfort (20.5)
    standard_data = {
        "name": "Standard",
        "baseline_preset": "eco",
        "days": {
            "mon": {cid_soggiorno: [{"start": "18:00", "end": "22:00", "preset": "comfort"}]}
        },
    }
    await sched.async_save_profile("standard", standard_data)

    # Holiday has no blocks (baseline away = 16.0)
    holiday_data = {
        "name": "Festivo",
        "baseline_preset": "away",
        "days": {"mon": {}},
    }
    await sched.async_save_profile("holiday", holiday_data)

    mon_1630 = datetime(2026, 11, 2, 16, 30, tzinfo=timezone.utc)
    await sched.async_evaluate_schedule(mon_1630)

    # Smart start active on standard profile
    assert sched.get_effective_target(cid_soggiorno) == 20.5
    assert cid_soggiorno in sched.smart_start_info

    # User switches to 'holiday'
    await sched.async_activate_profile("holiday", now=mon_1630)

    # Immediately smart start is cleared and target reverts to away baseline (16.0)
    assert cid_soggiorno not in sched.smart_start_info
    assert sched.get_effective_target(cid_soggiorno) == 16.0


# ============================================================================
# 10. Motore Smart Return & Radar Termico
# ============================================================================

@pytest.mark.asyncio
async def test_smart_return_radar_and_execution(mock_coordinator, mock_hass):
    """Verify smart return radar plan calculation, staggered ignition and completion."""
    sched = mock_coordinator.schedule_manager
    # Note: scheduler_enabled can be False! Smart Return works independently!
    await sched.async_set_scheduler_enabled(False)

    cid_soggiorno = make_zone_entity_id("Soggiorno")
    cid_bagno = make_zone_entity_id("Bagno")

    tm_soggiorno = MagicMock()
    tm_soggiorno.heating_rate = 1.0
    tm_bagno = MagicMock()
    tm_bagno.heating_rate = 2.5
    mock_coordinator._thermal_models = {
        cid_soggiorno: tm_soggiorno,
        cid_bagno: tm_bagno,
    }

    # Soggiorno: 18.5 -> target 20.5 -> delta 2.0 -> needs 2.0h (120m)
    # Bagno: 18.5 -> target 21.0 -> delta 2.5 -> needs 1.0h (60m)
    state_soggiorno = MagicMock()
    state_soggiorno.attributes = {"current_temperature": 18.5}
    state_bagno = MagicMock()
    state_bagno.attributes = {"current_temperature": 18.5}

    def mock_states_get(eid):
        if eid == cid_soggiorno:
            return state_soggiorno
        if eid == cid_bagno:
            return state_bagno
        return None

    mock_hass.states.get = MagicMock(side_effect=mock_states_get)

    now_1500 = datetime(2026, 11, 2, 15, 0, tzinfo=timezone.utc)

    # Set smart return for 18:30
    plan = await sched.async_set_smart_return("18:30", preset="comfort", now=now_1500)

    # Verify thermal radar plan
    assert cid_soggiorno in plan
    assert plan[cid_soggiorno]["minutes_needed"] == 120
    # ignition = 18:30 - 2h = 16:30
    assert plan[cid_soggiorno]["ignition_time"] == datetime(2026, 11, 2, 16, 30, tzinfo=timezone.utc).isoformat()

    assert cid_bagno in plan
    assert plan[cid_bagno]["minutes_needed"] == 60
    # ignition = 18:30 - 1h = 17:30
    assert plan[cid_bagno]["ignition_time"] == datetime(2026, 11, 2, 17, 30, tzinfo=timezone.utc).isoformat()

    # 1. At 16:00: neither ignited
    now_1600 = datetime(2026, 11, 2, 16, 0, tzinfo=timezone.utc)
    await sched.async_evaluate_schedule(now_1600)
    assert sched.get_effective_target(cid_soggiorno) is None
    assert sched.get_effective_target(cid_bagno) is None

    # 2. At 16:45: Soggiorno ignited, Bagno not yet
    now_1645 = datetime(2026, 11, 2, 16, 45, tzinfo=timezone.utc)
    await sched.async_evaluate_schedule(now_1645)
    assert sched.get_effective_target(cid_soggiorno) == 20.5
    assert sched.smart_start_info[cid_soggiorno]["source"] == "smart_return"
    assert sched.get_effective_target(cid_bagno) is None

    # 3. At 17:45: Both ignited
    now_1745 = datetime(2026, 11, 2, 17, 45, tzinfo=timezone.utc)
    await sched.async_evaluate_schedule(now_1745)
    assert sched.get_effective_target(cid_soggiorno) == 20.5
    assert sched.get_effective_target(cid_bagno) == 21.0

    # 4. At 18:30: Arrival reached! Smart return completes and sets global preset
    now_1830 = datetime(2026, 11, 2, 18, 30, tzinfo=timezone.utc)
    await sched.async_evaluate_schedule(now_1830)
    assert sched.smart_return is None
    assert mock_coordinator.zone_manager.current_global_preset == "comfort"


@pytest.mark.asyncio
async def test_smart_return_wakes_up_off_zones_and_master(mock_coordinator, mock_hass):
    """Verify smart return wakes up master switch and turns off zones to HEAT at ignition."""
    sched = mock_coordinator.schedule_manager
    await sched.async_set_scheduler_enabled(False)

    # 1. Setup Master Switch in OFF state
    mock_coordinator.master_enabled = False
    mock_coordinator.get_master_state = MagicMock(return_value=False)

    def _set_mstate(st):
        mock_coordinator.master_enabled = st
        mock_coordinator.get_master_state.return_value = st

    mock_coordinator.set_master_state = MagicMock(side_effect=_set_mstate)
    mock_master_switch = MagicMock()
    mock_coordinator._master_switch = mock_master_switch

    # 2. Setup zone Soggiorno in HVACMode.OFF
    cid_soggiorno = make_zone_entity_id("Soggiorno")
    climate_soggiorno = MagicMock()
    climate_soggiorno.hvac_mode = HVACMode.OFF
    climate_soggiorno._hvac_mode = HVACMode.OFF

    async def _set_zone_hvac(mode):
        climate_soggiorno._hvac_mode = mode
        climate_soggiorno.hvac_mode = mode

    climate_soggiorno.async_set_hvac_mode = AsyncMock(side_effect=_set_zone_hvac)
    mock_coordinator._climate_entities[cid_soggiorno] = climate_soggiorno

    state_soggiorno = MagicMock()
    state_soggiorno.state = HVACMode.OFF
    state_soggiorno.attributes = {"current_temperature": 18.5}

    # Camera is also OFF but NOT in smart return zones (for negative check)
    cid_camera = make_zone_entity_id("Camera")
    climate_camera = MagicMock()
    climate_camera.hvac_mode = HVACMode.OFF
    climate_camera._hvac_mode = HVACMode.OFF
    climate_camera.async_set_hvac_mode = AsyncMock()
    mock_coordinator._climate_entities[cid_camera] = climate_camera

    state_camera = MagicMock()
    state_camera.state = HVACMode.OFF
    state_camera.attributes = {"current_temperature": 18.0}

    def mock_states_get(eid):
        if eid == cid_soggiorno:
            return state_soggiorno
        if eid == cid_camera:
            return state_camera
        return None

    mock_hass.states.get = MagicMock(side_effect=mock_states_get)

    # Thermal model: heating rate 1.0 -> target comfort (20.5) - 18.5 = 2.0 -> 2 hours
    tm_soggiorno = MagicMock()
    tm_soggiorno.heating_rate = 1.0
    mock_coordinator._thermal_models = {cid_soggiorno: tm_soggiorno}

    # 3. Schedule Smart Return for 18:30 at 15:00, targeting only Soggiorno
    now_1500 = datetime(2026, 11, 2, 15, 0, tzinfo=timezone.utc)
    plan = await sched.async_set_smart_return(
        "18:30", preset="comfort", zones=[cid_soggiorno], now=now_1500
    )

    # Verification: ignition is 16:30
    assert plan[cid_soggiorno]["ignition_time"] == datetime(2026, 11, 2, 16, 30, tzinfo=timezone.utc).isoformat()
    assert cid_camera not in plan

    # 4. At 16:00 (before ignition): Master remains False, Soggiorno remains OFF, no overrides
    now_1600 = datetime(2026, 11, 2, 16, 0, tzinfo=timezone.utc)
    await sched.async_evaluate_schedule(now_1600)
    assert mock_coordinator.master_enabled is False
    assert climate_soggiorno._hvac_mode == HVACMode.OFF
    assert climate_soggiorno.async_set_hvac_mode.call_count == 0
    assert sched.get_effective_target(cid_soggiorno) is None

    # 5. At 16:45 (after ignition 16:30):
    # Master is turned ON, Soggiorno is woken up to HVACMode.HEAT, receives comfort target (20.5)
    now_1645 = datetime(2026, 11, 2, 16, 45, tzinfo=timezone.utc)
    await sched.async_evaluate_schedule(now_1645)

    assert mock_coordinator.master_enabled is True
    assert mock_coordinator.set_master_state.called
    assert mock_master_switch.async_write_ha_state.called
    assert climate_soggiorno.async_set_hvac_mode.called
    assert climate_soggiorno._hvac_mode == HVACMode.HEAT
    assert sched.get_effective_target(cid_soggiorno) == 20.5
    assert sched.smart_start_info[cid_soggiorno]["source"] == "smart_return"

    # Camera was NOT in smart return, so it must still remain OFF and without overrides
    assert climate_camera._hvac_mode == HVACMode.OFF
    assert climate_camera.async_set_hvac_mode.call_count == 0
    assert sched.get_effective_target(cid_camera) is None

    # 6. At 18:30 (arrival): Smart return completed, master is confirmed ON
    now_1830 = datetime(2026, 11, 2, 18, 30, tzinfo=timezone.utc)
    await sched.async_evaluate_schedule(now_1830)
    assert sched.smart_return is None
    assert mock_coordinator.master_enabled is True


# ============================================================================
# 11. Servizi HA, Entità e State Summary
# ============================================================================

@pytest.mark.asyncio
async def test_ha_services_and_state_summary(mock_coordinator, mock_hass):
    """Verify HA services registration, execution, and state summary completeness."""
    sys.meta_path[:] = [
        f for f in sys.meta_path if f.__class__.__name__ != "HomeAssistantMockFinder"
    ]
    for _m in (
        "homeassistant.components.switch",
        "homeassistant.components.select",
        "custom_components.multizone_thermostat.switch",
        "custom_components.multizone_thermostat.select",
    ):
        sys.modules.pop(_m, None)

    from custom_components.multizone_thermostat import _async_register_services
    from custom_components.multizone_thermostat.switch import MultizoneSchedulerSwitch
    from custom_components.multizone_thermostat.select import MultizoneScheduleProfileSelect

    cid_soggiorno = make_zone_entity_id("Soggiorno")

    # Register services
    registered_services = {}

    def mock_register(domain, svc, handler):
        registered_services[f"{domain}.{svc}"] = handler

    mock_hass.services.async_register = MagicMock(side_effect=mock_register)
    mock_hass.data[DOMAIN]["_services_registered"] = False
    await _async_register_services(mock_hass)

    assert "multizone_thermostat.save_schedule_profile" in registered_services
    assert "multizone_thermostat.activate_schedule_profile" in registered_services
    assert "multizone_thermostat.duplicate_schedule_profile" in registered_services
    assert "multizone_thermostat.set_smart_return" in registered_services
    assert "multizone_thermostat.cancel_smart_return" in registered_services
    assert "multizone_thermostat.clear_zone_override" in registered_services
    assert "multizone_thermostat.set_preset_temperature" in registered_services

    # Call save_schedule_profile service
    save_svc = registered_services["multizone_thermostat.save_schedule_profile"]
    call_mock = MagicMock()
    call_mock.data = {
        "profile_id": "service_profile",
        "name": "Service Profile",
        "baseline_preset": "sleep",
        "days": {"mon": {cid_soggiorno: [{"start": "10:00", "end": "12:00", "preset": "comfort"}]}},
    }
    await save_svc(call_mock)
    assert "service_profile" in mock_coordinator.schedule_manager.profiles

    # Call activate_schedule_profile service
    act_svc = registered_services["multizone_thermostat.activate_schedule_profile"]
    call_mock.data = {"profile_id": "service_profile", "expires_at": None, "fallback_profile": "standard"}
    await act_svc(call_mock)
    assert mock_coordinator.schedule_manager.active_profile == "service_profile"

    # Test Scheduler Switch
    sched_switch = MultizoneSchedulerSwitch(mock_coordinator, "test_entry")
    sched_switch.async_write_ha_state = MagicMock()
    assert sched_switch.is_on is False
    await sched_switch.async_turn_on()
    assert mock_coordinator.schedule_manager.scheduler_enabled is True
    assert sched_switch.is_on is True
    assert "schedule_status" in sched_switch.extra_state_attributes

    # Test Schedule Profile Select
    prof_select = MultizoneScheduleProfileSelect(mock_coordinator, "test_entry")
    prof_select.async_write_ha_state = MagicMock()
    assert "service_profile" in prof_select.options
    assert prof_select.current_option == "service_profile"
    await prof_select.async_select_option("standard")
    assert mock_coordinator.schedule_manager.active_profile == "standard"

    # Test summary dictionary keys
    summary = mock_coordinator.schedule_manager.get_state_summary()
    assert "scheduler_enabled" in summary
    assert "active_profile" in summary
    assert "profile_expires_at" in summary
    assert "fallback_profile" in summary
    assert "profiles" in summary
    assert "manual_overrides" in summary
    assert "smart_start_info" in summary
    assert "smart_return" in summary
    assert "smart_return_plan" in summary
    assert "preset_matrix" in summary
    assert "comfort" in summary["preset_matrix"]

    # Test Climate extra_state_attributes
    zone_data = mock_coordinator.zones[0]
    thermostat = MultizoneVirtualThermostat(hass=mock_hass, entry_id="test_entry", zone_data=zone_data)
    thermostat.async_write_ha_state = MagicMock()
    attrs = thermostat.extra_state_attributes
    assert "schedule_manual_override" in attrs
    assert "schedule_override_until" in attrs
    assert "smart_start_active" in attrs
    assert "smart_start_detail" in attrs
    assert "heating_rate" in attrs

