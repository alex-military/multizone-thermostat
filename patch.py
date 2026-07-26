import re

with open('custom_components/multizone_thermostat/config_flow.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Add selector import
if 'from homeassistant.helpers import selector' not in content:
    content = content.replace('from homeassistant.helpers import entity_registry as er', 'from homeassistant.helpers import entity_registry as er\nfrom homeassistant.helpers import selector')

# Replace vol.In with selector
content = content.replace(
    'vol.Required(CONF_BOILER_SWITCH): vol.In(switches)',
    'vol.Required(CONF_BOILER_SWITCH): selector.EntitySelector(selector.EntitySelectorConfig(domain=SWITCH_DOMAIN))'
)
content = content.replace(
    'vol.Required(CONF_BOILER_SWITCH, default=self._boiler_switch): vol.In(switches)',
    'vol.Required(CONF_BOILER_SWITCH, default=self._boiler_switch): selector.EntitySelector(selector.EntitySelectorConfig(domain=SWITCH_DOMAIN))'
)

content = content.replace(
    'vol.Required(CONF_VT_TEMP_SENSOR): vol.In(temp_sensors)',
    'vol.Required(CONF_VT_TEMP_SENSOR): selector.EntitySelector(selector.EntitySelectorConfig(domain=SENSOR_DOMAIN, device_class="temperature"))'
)
content = content.replace(
    'vol.Required(CONF_VT_HEATER_SWITCH): vol.In(switches)',
    'vol.Required(CONF_VT_HEATER_SWITCH): selector.EntitySelector(selector.EntitySelectorConfig(domain=SWITCH_DOMAIN))'
)

content = content.replace(
    'vol.Required(CONF_ZONE_CLIMATE): vol.In(available_climates)',
    'vol.Required(CONF_ZONE_CLIMATE): selector.EntitySelector(selector.EntitySelectorConfig(domain=CLIMATE_DOMAIN))'
)
content = content.replace(
    'vol.Required(CONF_ZONE_NAME, default=default_name): str',
    'vol.Required(CONF_ZONE_NAME): str'
)

# Regex for Window Sensor
content = re.sub(
    r'vol\.Optional\(CONF_ZONE_WINDOW_SENSOR, default="none"\): vol\.In\(window_sensors\)',
    r'vol.Optional(CONF_ZONE_WINDOW_SENSOR): selector.EntitySelector(selector.EntitySelectorConfig(domain=BINARY_SENSOR_DOMAIN))',
    content
)
content = re.sub(
    r'vol\.Optional\(CONF_ZONE_WINDOW_SENSOR, default="none"\): vol\.In\(sensors\)',
    r'vol.Optional(CONF_ZONE_WINDOW_SENSOR): selector.EntitySelector(selector.EntitySelectorConfig(domain=BINARY_SENSOR_DOMAIN))',
    content
)
content = re.sub(
    r'vol\.Optional\(CONF_ZONE_WINDOW_SENSOR, default=current_sensor\): vol\.In\(sensors\)',
    r'vol.Optional(CONF_ZONE_WINDOW_SENSOR, description={"suggested_value": current_sensor} if current_sensor != "none" else {}): selector.EntitySelector(selector.EntitySelectorConfig(domain=BINARY_SENSOR_DOMAIN))',
    content
)

content = re.sub(
    r'vol\.Optional\(CONF_PRESENCE_SENSOR, default="zone\.home"\): vol\.In\(presence_entities\)',
    r'vol.Optional(CONF_PRESENCE_SENSOR, default="zone.home"): selector.EntitySelector(selector.EntitySelectorConfig(domain=["person", "group", "zone", "input_boolean"]))',
    content
)
content = re.sub(
    r'vol\.Optional\(CONF_PRESENCE_SENSOR, default=self\._presence_sensor or "zone\.home"\): vol\.In\(presence_entities\)',
    r'vol.Optional(CONF_PRESENCE_SENSOR, default=self._presence_sensor or "zone.home"): selector.EntitySelector(selector.EntitySelectorConfig(domain=["person", "group", "zone", "input_boolean"]))',
    content
)

# Validation logic replacements
old_validation_1 = """            if not zone_name:
                errors[CONF_ZONE_NAME] = "zone_name_required\""""
new_validation_1 = """            if climate_entity in already_added:
                errors[CONF_ZONE_CLIMATE] = "climate_already_added"
            elif not zone_name:
                errors[CONF_ZONE_NAME] = "zone_name_required\""""
content = content.replace(old_validation_1, new_validation_1)

old_validation_2 = """            if not name:
                errors[CONF_ZONE_NAME] = "zone_name_required\""""
new_validation_2 = """            if climate_id in already_added:
                errors[CONF_ZONE_CLIMATE] = "climate_already_added"
            elif not name:
                errors[CONF_ZONE_NAME] = "zone_name_required\""""
content = content.replace(old_validation_2, new_validation_2)


with open('custom_components/multizone_thermostat/config_flow.py', 'w', encoding='utf-8') as f:
    f.write(content)
print('Config flow updated successfully.')
