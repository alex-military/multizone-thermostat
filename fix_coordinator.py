with open("custom_components/multizone_thermostat/coordinator.py", "r") as f:
    content = f.read()

content = content.replace("zone[CONF_ZONE_CLIMATE]", "make_zone_entity_id(zone[CONF_ZONE_NAME])")
content = content.replace("z[CONF_ZONE_CLIMATE]", "make_zone_entity_id(z[CONF_ZONE_NAME])")
content = content.replace("    CONF_ZONE_CLIMATE,\n", "    CONF_ZONE_NAME,\n    make_zone_entity_id,\n")

with open("custom_components/multizone_thermostat/coordinator.py", "w") as f:
    f.write(content)
