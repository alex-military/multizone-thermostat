// Helper function to auto-discover the bypass switch for a climate entity
function autoDiscoverSwitch(hass, climateId) {
  if (!hass || !hass.states || !climateId) return "";
  for (const entityId of Object.keys(hass.states)) {
    // Check both legacy switches and new select entities for the climate_entity attribute
    if ((entityId.startsWith("select.") || entityId.startsWith("switch.")) && 
        hass.states[entityId].attributes && 
        hass.states[entityId].attributes.climate_entity === climateId) {
      return entityId;
    }
  }
  
  // Fallback: check if the entityId contains the climate device name AND is a zone_mode entity
  const rawName = climateId.split('.')[1] || "";
  const slug = rawName.replace(/^multizone_thermostat_/, "");
  for (const entityId of Object.keys(hass.states)) {
    if (entityId.startsWith("select.") && 
        (entityId.includes(slug) || (rawName && entityId.includes(rawName))) &&
        (entityId.includes("mode") || entityId.includes("zone"))) {
      return entityId;
    }
  }
  
  return "";
}

// Helper function to auto-discover the master switch entity
function findMasterEntity(hass) {
  if (!hass) return null;
  
  // Search for switch with multizone_type: master attribute
  const found = Object.keys(hass.states).find(key => {
    const state = hass.states[key];
    return state.attributes && state.attributes.multizone_type === "master";
  });
  if (found) return found;

  // Fallback to name search
  return Object.keys(hass.states).find(key => {
    return key.startsWith('switch.') && key.includes('heating_master');
  }) || null;
}

// Helper function to auto-discover the boiler switch/sensor entity
function findBoilerEntity(hass) {
  if (!hass || !hass.states) return null;

  // 1. boiler_switch attribute exposed by the master switch
  const masterId = findMasterEntity(hass);
  if (masterId && hass.states[masterId] && hass.states[masterId].attributes) {
    const bSwitch = hass.states[masterId].attributes.boiler_switch;
    if (bSwitch && hass.states[bSwitch]) return bSwitch;
  }

  // 2. boiler_entity_id attribute exposed by the zone climate entities
  for (const key of Object.keys(hass.states)) {
    if (key.startsWith('climate.')) {
      const attrs = hass.states[key].attributes || {};
      if (attrs.boiler_entity_id && hass.states[attrs.boiler_entity_id]) {
        return attrs.boiler_entity_id;
      }
    }
  }

  // 3. Fallback: name search
  return Object.keys(hass.states).find(key =>
    key.startsWith('switch.') && (key.includes('boiler') || key.includes('caldaia'))
  ) || null;
}

// Helper function to auto-discover the preset select entity
function findPresetEntity(hass) {
  if (!hass) return null;
  
  // Robust method: find the select entity that has our specific global presets
  const found = Object.keys(hass.states).find(key => {
    if (!key.startsWith('select.')) return false;
    const state = hass.states[key];
    if (state && state.attributes && state.attributes.options) {
      const opts = state.attributes.options;
        if (opts.includes('manual') && opts.includes('comfort') && opts.includes('sleep')) {
          return true;
        }
    }
    return false;
  });
  if (found) return found;

  // Fallback
  return Object.keys(hass.states).find(key => {
    return key.startsWith('select.') && key.includes('global_preset');
  }) || null;
}


/* ==================== BUTTON CARD CLASS ==================== */
