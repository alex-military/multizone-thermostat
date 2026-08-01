import re

with open("custom_components/multizone_thermostat/coordinator.py", "r") as f:
    content = f.read()

# Remove the import of CONF_ZONE_TRV_SYNC
content = content.replace("    CONF_ZONE_TRV_SYNC,\n", "")

# Remove the block:
#        # 2. TRV preset sync (if enabled for this zone)
#        if zone and zone.get(CONF_ZONE_TRV_SYNC, False):
#            self.hass.async_create_task(
#                self._async_sync_trv_preset(entity_id, new_state.state)
#            )
trv_sync_pattern = r"\s*# 2\. TRV preset sync \(if enabled for this zone\)\s*if zone and zone\.get\(CONF_ZONE_TRV_SYNC, False\):\s*self\.hass\.async_create_task\(\s*self\._async_sync_trv_preset\(entity_id, new_state\.state\)\s*\)"
content = re.sub(trv_sync_pattern, "", content)

# Remove the method _async_sync_trv_preset entirely
method_pattern = r"\s*async def _async_sync_trv_preset\(self, climate_entity: str, hvac_mode: str\) -> None:(?:.*?\n)+?(?=\s*async def|\Z)"
content = re.sub(method_pattern, "\n", content)

with open("custom_components/multizone_thermostat/coordinator.py", "w") as f:
    f.write(content)
