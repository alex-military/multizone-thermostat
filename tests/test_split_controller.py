"""Unit tests for Multizone Thermostat Phase 11 Step 2: SplitZoneManager and Split Controller."""
import asyncio
import os
import sys
import unittest
from unittest.mock import MagicMock, AsyncMock

# Base paths
dummy_ha_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "dummy_ha"))
repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if dummy_ha_path not in sys.path:
    sys.path.insert(0, dummy_ha_path)
if repo_root not in sys.path:
    sys.path.insert(1, repo_root)

from custom_components.multizone_thermostat.const import (
    CONF_ZONE_NAME,
    CONF_ZONE_SPLIT_CLIMATE,
    CONF_ZONE_SPLIT_ROLE,
    SPLIT_ROLE_HEAT_COOL,
    SPLIT_ROLE_COOLING_ONLY,
    SPLIT_ROLE_HEATING_ONLY,
    CONF_ZONE_SPLIT_SOLAR_PRIORITY,
    CONF_ZONE_SPLIT_QUICK_BOOST,
    CONF_ZONE_SPLIT_BOOST_DELTA,
    CONF_ZONE_SPLIT_SENSOR_INJECTION,
    HVAC_MODE_HEAT,
    HVAC_MODE_COOL,
    HVAC_MODE_OFF,
    make_zone_entity_id,
    KEY_ALLOW_SPLIT_HEATING,
    KEY_ALLOW_SPLIT_COOLING,
    KEY_HEAT_SOURCE_PRIORITY,
    SOURCE_PRIORITY_ELECTRIC,
    SOURCE_PRIORITY_GAS_ONLY,
    SOURCE_PRIORITY_GAS,
)
from custom_components.multizone_thermostat.split.split_controller import SplitZoneManager


class TestSplitZoneManager(unittest.IsolatedAsyncioTestCase):
    """Test suite for SplitZoneManager."""

    async def asyncSetUp(self):
        self.hass = MagicMock()
        self.hass.services.async_call = AsyncMock()

        self.zones_config = [
            {
                CONF_ZONE_NAME: "Salotto",
                CONF_ZONE_SPLIT_CLIMATE: "climate.split_salotto",
                CONF_ZONE_SPLIT_ROLE: SPLIT_ROLE_HEAT_COOL,
                CONF_ZONE_SPLIT_SOLAR_PRIORITY: True,
                CONF_ZONE_SPLIT_QUICK_BOOST: True,
                CONF_ZONE_SPLIT_BOOST_DELTA: 1.5,
                CONF_ZONE_SPLIT_SENSOR_INJECTION: True,
            },
            {
                CONF_ZONE_NAME: "Camera",
                # Camera has no split
            },
            {
                CONF_ZONE_NAME: "Studio",
                CONF_ZONE_SPLIT_CLIMATE: "climate.split_studio",
                CONF_ZONE_SPLIT_ROLE: SPLIT_ROLE_COOLING_ONLY,
                CONF_ZONE_SPLIT_SOLAR_PRIORITY: False,
                CONF_ZONE_SPLIT_QUICK_BOOST: False,
            },
        ]

        self.coordinator = MagicMock()
        self.coordinator.zones = self.zones_config
        self.coordinator.get_master_state.return_value = True
        self.coordinator.zone_manager.get_zone_mode.return_value = "primary"
        self.coordinator.is_dhw_active = False
        self.coordinator.weather_sensor_id = None
        self.coordinator.get_persistent_data.side_effect = lambda key, default=None: default

        self.manager = SplitZoneManager(self.hass, self.coordinator)
        self.salotto_id = make_zone_entity_id("Salotto")
        self.camera_id = make_zone_entity_id("Camera")
        self.studio_id = make_zone_entity_id("Studio")

    def test_zone_discovery(self):
        """Verify discovery of zones with split climate entities."""
        self.assertTrue(self.manager.has_split(self.salotto_id))
        self.assertFalse(self.manager.has_split(self.camera_id))
        self.assertTrue(self.manager.has_split(self.studio_id))

        info = self.manager.get_split_info(self.salotto_id)
        self.assertEqual(info["split_entity_id"], "climate.split_salotto")
        self.assertTrue(info["split_quick_boost"])
        self.assertEqual(info["split_boost_delta"], 1.5)

    def test_cooling_only_role_does_not_heat(self):
        """Verify split with cooling_only role does not engage during winter heating."""
        mode, target, is_heating = self.manager.evaluate_split_state(
            climate_id=self.studio_id,
            current_temp=18.0,
            target_temp=21.0,
            zone_hvac_mode=HVAC_MODE_HEAT,
        )
        self.assertEqual(mode, HVAC_MODE_OFF)
        self.assertFalse(is_heating)

    def test_master_permission_toggle(self):
        """Verify master allow switch disables split heating immediately."""
        self.coordinator.get_persistent_data.side_effect = (
            lambda key, default=None: False if key == KEY_ALLOW_SPLIT_HEATING else default
        )
        mode, target, is_heating = self.manager.evaluate_split_state(
            climate_id=self.salotto_id,
            current_temp=17.0,
            target_temp=21.0,
            zone_hvac_mode=HVAC_MODE_HEAT,
        )
        self.assertEqual(mode, HVAC_MODE_OFF)
        self.assertFalse(is_heating)

    def test_quick_heat_boost_trigger_and_hysteresis(self):
        """Verify Quick Heat Boost engages at delta >= 1.5°C and disengages when close to comfort."""
        # Salotto: current 18.0°C, target 20.0°C (Delta = 2.0 >= 1.5) -> Boost triggers!
        mode, target, is_heating = self.manager.evaluate_split_state(
            climate_id=self.salotto_id,
            current_temp=18.0,
            target_temp=20.0,
            zone_hvac_mode=HVAC_MODE_HEAT,
            solar_surplus=False,
        )
        self.assertEqual(mode, HVAC_MODE_HEAT)
        self.assertTrue(is_heating)
        self.assertTrue(self.manager.is_quick_boost_active(self.salotto_id))

        # During Quick Boost, hydronic demand is NOT suppressed (dual heat boost active)
        self.assertFalse(self.manager.should_suppress_hydronic_demand(self.salotto_id))

        # Room warms up to 19.6°C (Delta = 0.4°C > 0.3°C hysteresis) -> Boost remains active
        mode, target, is_heating = self.manager.evaluate_split_state(
            climate_id=self.salotto_id,
            current_temp=19.6,
            target_temp=20.0,
            zone_hvac_mode=HVAC_MODE_HEAT,
        )
        self.assertTrue(self.manager.is_quick_boost_active(self.salotto_id))

        # Room reaches 19.8°C (Delta = 0.2°C <= 0.3°C) -> Boost ends!
        mode, target, is_heating = self.manager.evaluate_split_state(
            climate_id=self.salotto_id,
            current_temp=19.8,
            target_temp=20.0,
            zone_hvac_mode=HVAC_MODE_HEAT,
        )
        self.assertFalse(self.manager.is_quick_boost_active(self.salotto_id))

    def test_solar_priority_and_hydronic_demand_suppression(self):
        """Verify Solar Priority engages split during PV surplus and suppresses hydronic demand."""
        # Delta is small (0.5°C), so Quick Boost won't trigger (threshold is 1.5°C)
        # But solar_surplus = True!
        mode, target, is_heating = self.manager.evaluate_split_state(
            climate_id=self.salotto_id,
            current_temp=19.5,
            target_temp=20.0,
            zone_hvac_mode=HVAC_MODE_HEAT,
            solar_surplus=True,
        )
        self.assertEqual(mode, HVAC_MODE_HEAT)
        self.assertTrue(is_heating)
        self.assertFalse(self.manager.is_quick_boost_active(self.salotto_id))

        # In pure solar heating mode, hydronic demand MUST be suppressed to save gas!
        self.assertTrue(self.manager.should_suppress_hydronic_demand(self.salotto_id))

    def test_room_probe_sensor_injection(self):
        """Verify split target setpoint is compensated to overcome ceiling thermal stratification."""
        # Mock split climate entity reporting 23.0°C at ceiling level
        mock_split_state = MagicMock()
        mock_split_state.attributes = {"current_temperature": 23.0}
        self.hass.states.get.return_value = mock_split_state

        # Real room sensor is at 19.0°C, target is 20.0°C
        # Ceiling offset = 23.0 - 19.0 = +4.0°C
        # Compensated target = 20.0 + 4.0 = 24.0°C
        injected = self.manager.calculate_injected_target(
            climate_id=self.salotto_id,
            current_temp=19.0,
            target_temp=20.0,
        )
        self.assertEqual(injected, 24.0)

    async def test_async_sync_split_service_call(self):
        """Verify service calls are sent to HA climate entity with proper parameters."""
        await self.manager.async_sync_split(
            climate_id=self.salotto_id,
            desired_mode=HVAC_MODE_HEAT,
            desired_target=22.5,
        )

        self.assertEqual(self.hass.services.async_call.call_count, 2)
        mode_call = self.hass.services.async_call.call_args_list[0]
        temp_call = self.hass.services.async_call.call_args_list[1]

        self.assertEqual(mode_call[0][0], "climate")
        self.assertEqual(mode_call[0][1], "set_hvac_mode")
        self.assertEqual(mode_call[0][2]["entity_id"], "climate.split_salotto")
        self.assertEqual(mode_call[0][2]["hvac_mode"], HVAC_MODE_HEAT)

        self.assertEqual(temp_call[0][0], "climate")
        self.assertEqual(temp_call[0][1], "set_temperature")
        self.assertEqual(temp_call[0][2]["entity_id"], "climate.split_salotto")
        self.assertEqual(temp_call[0][2]["temperature"], 22.5)

    async def test_zone_controller_hydronic_decoupling_integration(self):
        """Verify ZoneController zeroes out hydronic demand when split covers the zone."""
        from custom_components.multizone_thermostat.zone_controller import ZoneController

        self.coordinator.demand_aggregator = MagicMock()
        self.coordinator.split_manager = self.manager
        self.coordinator.plant_diagnostics.has_critical_sensor_fault.return_value = False
        self.coordinator.zone_manager.get_zone_mode.return_value = "primary"

        zc = ZoneController(self.hass, self.coordinator)

        mock_state = MagicMock()
        mock_state.state = HVAC_MODE_HEAT
        mock_state.attributes = {
            "current_temperature": 19.5,
            "temperature": 20.0,
        }

        # Case 1: Pure solar surplus -> split covers load -> hydronic suppressed to 0.0%
        zc.pids[self.salotto_id].calc = MagicMock(return_value=60.0)
        self.manager._splits[self.salotto_id]["split_solar_priority"] = True
        self.coordinator.energy_manager.is_solar_surplus = True

        demand = await zc.async_update_zone(self.salotto_id, mock_state)
        self.assertEqual(demand, 0.0)
        self.coordinator.demand_aggregator.set_zone_demand.assert_called_with(self.salotto_id, 0.0)

        # Case 2: Camera has NO split -> normal demand calculated and sent
        zc._autotuners[self.camera_id].state = zc._autotuners[self.camera_id].STATE_COMPLETED
        zc._pids[self.camera_id].calc = MagicMock(return_value=75.0)

        demand_cam = await zc.async_update_zone(self.camera_id, mock_state)
        self.assertEqual(demand_cam, 75.0)
        self.coordinator.demand_aggregator.set_zone_demand.assert_called_with(self.camera_id, 75.0)

    def test_cooling_mode_evaluation(self):
        """Verify split turns on COOL when room is hot and turns OFF when cooled down."""
        # Salotto has role "both" (Heating & Cooling)
        # 1. Hot room: current 26.0°C, target 24.0°C (Delta = +2.0°C > 0.3°C) -> Split cools!
        mode, target, is_heating = self.manager.evaluate_split_state(
            climate_id=self.salotto_id,
            current_temp=26.0,
            target_temp=24.0,
            zone_hvac_mode=HVAC_MODE_COOL,
        )
        self.assertEqual(mode, HVAC_MODE_COOL)
        self.assertEqual(target, 24.0)
        self.assertFalse(is_heating)
        self.assertTrue(self.manager.is_split_active(self.salotto_id))

        # 2. Cooled room: current 23.8°C, target 24.0°C (Delta = -0.2°C <= 0.3°C) -> Split turns off
        mode, target, is_heating = self.manager.evaluate_split_state(
            climate_id=self.salotto_id,
            current_temp=23.8,
            target_temp=24.0,
            zone_hvac_mode=HVAC_MODE_COOL,
        )
        self.assertEqual(mode, HVAC_MODE_OFF)
        self.assertFalse(is_heating)
        self.assertFalse(self.manager.is_split_active(self.salotto_id))

    def test_cooling_master_switch_disabled(self):
        """Verify split cooling is blocked when master allow cooling switch is OFF."""
        self.coordinator.get_persistent_data.side_effect = (
            lambda key, default=None: False if key == KEY_ALLOW_SPLIT_COOLING else default
        )
        mode, target, is_heating = self.manager.evaluate_split_state(
            climate_id=self.salotto_id,
            current_temp=27.0,
            target_temp=24.0,
            zone_hvac_mode=HVAC_MODE_COOL,
        )
        self.assertEqual(mode, HVAC_MODE_OFF)
        self.assertFalse(is_heating)
        self.assertFalse(self.manager.is_split_active(self.salotto_id))


    def test_local_manual_split_activation_when_master_off(self):
        """Verify local manual split operation functions and suppresses hydronic heating when Master is OFF."""
        self.coordinator.get_master_state.return_value = False

        # When local manual is OFF, split is OFF if Master is OFF
        self.manager.set_local_manual_on(self.salotto_id, False)
        mode, target, is_heating = self.manager.evaluate_split_state(
            climate_id=self.salotto_id,
            current_temp=19.0,
            target_temp=21.0,
            zone_hvac_mode=HVAC_MODE_HEAT,
        )
        self.assertEqual(mode, HVAC_MODE_OFF)
        self.assertFalse(is_heating)

        # When local manual is toggled ON, split runs even if Master is OFF
        self.manager.set_local_manual_on(self.salotto_id, True)
        self.assertTrue(self.manager.is_local_manual_on(self.salotto_id))
        self.assertTrue(self.manager.should_suppress_hydronic_demand(self.salotto_id))

        mode, target, is_heating = self.manager.evaluate_split_state(
            climate_id=self.salotto_id,
            current_temp=19.0,
            target_temp=21.0,
            zone_hvac_mode=HVAC_MODE_HEAT,
        )
        self.assertEqual(mode, HVAC_MODE_HEAT)
        self.assertTrue(is_heating)
        self.assertTrue(self.manager.is_split_active(self.salotto_id))

    def test_local_manual_reset_on_master_turn_on(self):
        """Verify Master switch turning ON clears all local manual split overrides."""
        self.manager.set_local_manual_on(self.salotto_id, True)
        self.assertTrue(self.manager.is_local_manual_on(self.salotto_id))

        self.manager.reset_all_local_manual_overrides()
        self.assertFalse(self.manager.is_local_manual_on(self.salotto_id))


if __name__ == "__main__":
    unittest.main()
