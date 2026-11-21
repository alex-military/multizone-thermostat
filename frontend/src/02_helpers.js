function getTempUnit(hass) { return (hass && hass.config && hass.config.unit_system && hass.config.unit_system.temperature) || '°C'; }
function isFahrenheit(hass) { return getTempUnit(hass) === '°F'; }
function celsiusToDisplay(val, hass) {
  if (typeof val !== 'number' || isNaN(val)) return val;
  return isFahrenheit(hass) ? (val * 9 / 5 + 32) : val;
}
function celsiusDeltaToDisplay(val, hass) {
  if (typeof val !== 'number' || isNaN(val)) return val;
  return isFahrenheit(hass) ? (val * 1.8) : val;
}
function escapeHtml(str) {
  if (str === null || str === undefined) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}
// Helper function to match entity_id to zone slug accurately without false positives
function isZoneEntityMatch(id, slug) {
  if (!id || !slug) return false;
  const objId = (id.includes('.') ? id.split('.')[1] : id).toLowerCase();
  const cleanSlug = String(slug).toLowerCase().replace(/^(multizone_thermostat_|zona_|zone_)/, '');

  let stripped = objId.replace(/^(multizone_thermostat_|zona_|zone_)/, '');
  if (stripped === cleanSlug) return true;

  const suffixes = [
    '_energy_class', '_classe_energetica',
    '_thermal_retention', '_tempo_ritenzione_termica', '_tempo_di_ritenzione_termica',
    '_radiator_sizing', '_dimensionamento_radiatore',
    '_anomaly', '_anomalia',
    '_passive_heat', '_apporto_passivo',
    '_battery', '_batteria',
    '_heating_rate', '_velocita_riscaldamento',
    '_cooling_rate', '_velocita_raffrescamento',
    '_thermal_loss', '_dispersione_termica',
    '_thermal_inertia', '_inerzia_termica',
    '_duty_cycle', '_ciclo_di_lavoro',
    '_demand', '_fabbisogno',
    '_autotune',
    '_window_open', '_finestra_aperta',
    '_split_boost', '_boost_split',
    '_physical_sync',
    '_zone_mode', '_modalita_zona', '_modalita', '_mode', '_preset',
    '_status', '_stato'
  ];

  for (const sfx of suffixes) {
    if (stripped.endsWith(sfx)) {
      if (stripped.slice(0, -sfx.length) === cleanSlug) return true;
    }
  }

  // Legacy patterns where entity ends with _<cleanSlug> or _zona_<cleanSlug>
  // e.g. ciclo_di_lavoro_zona_salotto or modalita_zona_salotto
  if (objId.endsWith('_' + cleanSlug) || objId.endsWith('_zona_' + cleanSlug) || objId.endsWith('_zone_' + cleanSlug)) {
    return true;
  }

  return false;
}

// Helper function to check whether an auxiliary switch/select should never be treated as zone mode
function _isAuxiliaryZoneEntity(entityId, stateObj) {
  if (!entityId) return false;
  if (entityId.includes("pid_") || entityId.includes("split_")) return true;
  const mType = stateObj && stateObj.attributes && stateObj.attributes.multizone_type;
  return mType === "pid_manual_unlock" || mType === "pid_parameter" || mType === "master";
}

// Helper function to auto-discover the bypass switch / zone_mode select for a climate entity
function autoDiscoverSwitch(hass, climateId) {
  if (!hass || !hass.states || !climateId) return "";
  // Prefer select.* zone_mode entities before legacy switch.* entities
  let legacySwitchFallback = "";
  for (const entityId of Object.keys(hass.states)) {
    const stateObj = hass.states[entityId];
    if (_isAuxiliaryZoneEntity(entityId, stateObj)) continue;
    if ((entityId.startsWith("select.") || entityId.startsWith("switch.")) &&
        stateObj && stateObj.attributes &&
        stateObj.attributes.climate_entity === climateId) {
      if (entityId.startsWith("select.")) return entityId;
      if (!legacySwitchFallback) legacySwitchFallback = entityId;
    }
  }
  if (legacySwitchFallback) return legacySwitchFallback;

  // Fallback: check if the entityId contains the climate device name AND is a zone_mode entity
  const rawName = climateId.split('.')[1] || "";
  const slug = rawName.replace(/^multizone_thermostat_/, "");
  const cleanSlug = slug.replace(/^zona_/, "");
  const isSlugMatch = (id) => isZoneEntityMatch(id, cleanSlug);

  let legacySlugSwitchFallback = "";
  for (const entityId of Object.keys(hass.states)) {
    const stateObj = hass.states[entityId];
    if (_isAuxiliaryZoneEntity(entityId, stateObj)) continue;
    if (!isSlugMatch(entityId)) continue;
    if (entityId.startsWith("select.") &&
        (entityId.includes("mode") || entityId.includes("zone") || entityId.includes("modalita"))) {
      return entityId;
    }
    if (entityId.startsWith("switch.") &&
        (entityId.includes("mode") || entityId.includes("modalita") || entityId.includes("bypass")) &&
        !legacySlugSwitchFallback) {
      legacySlugSwitchFallback = entityId;
    }
  }
  if (legacySlugSwitchFallback) return legacySlugSwitchFallback;

  return "";
}

// Helper function to auto-discover the master switch entity
function findMasterEntity(hass) {
  if (!hass || !hass.states) return null;
  
  // Search for switch with multizone_type: master attribute
  const found = Object.keys(hass.states).find(key => {
    const state = hass.states[key];
    return state && state.attributes && state.attributes.multizone_type === "master";
  });
  if (found) return found;

  // Fallback to name search
  return Object.keys(hass.states).find(key => {
    return key.startsWith('switch.') && (key.includes('heating_master') || key.includes('master_control'));
  }) || null;
}

// Helper function to auto-discover the boiler switch/sensor entity
function findBoilerEntity(hass) {
  if (!hass || !hass.states) return null;

  // 1. Check master switch attribute boiler_switch
  const masterId = findMasterEntity(hass);
  if (masterId && hass.states[masterId] && hass.states[masterId].attributes) {
    const bSwitch = hass.states[masterId].attributes.boiler_switch;
    if (bSwitch && hass.states[bSwitch]) return bSwitch;
  }

  // 2. Check climate entity attributes for boiler_entity_id
  for (const key of Object.keys(hass.states)) {
    if (key.startsWith('climate.')) {
      const attrs = hass.states[key].attributes || {};
      if (attrs.boiler_entity_id && hass.states[attrs.boiler_entity_id]) {
        return attrs.boiler_entity_id;
      }
    }
  }

  // 3. Fallback name search
  return Object.keys(hass.states).find(key => {
    return key.startsWith('switch.') && (key.includes('boiler') || key.includes('caldaia'));
  }) || null;
}

// Helper function to auto-discover the preset select entity
function findPresetEntity(hass) {
  if (!hass || !hass.states) return null;
  
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


// Helper function to auto-discover Heat Source Priority entity (select)
function findHeatSourcePriorityEntity(hass) {
  if (!hass || !hass.states) return null;
  const found = Object.keys(hass.states).find(key => {
    return key.startsWith('select.') && key.includes('heat_source_priority');
  });
  if (found) return found;

  return Object.keys(hass.states).find(key => {
    if (!key.startsWith('select.')) return false;
    const st = hass.states[key];
    if (st && st.attributes && Array.isArray(st.attributes.options)) {
      const opts = st.attributes.options;
      return opts.includes('auto') && opts.includes('hybrid') && opts.includes('combined');
    }
    return false;
  }) || null;
}

// Helper function to auto-discover Master Operation Mode entity (select)
function findMasterOperationModeEntity(hass) {
  if (!hass || !hass.states) return null;
  // 1. Exact match on select name
  const found = Object.keys(hass.states).find(key => {
    return key.startsWith('select.') && (key.includes('master_operation_mode') || key.includes('master_hvac_mode'));
  });
  if (found) return found;

  // 2. Select with options ['heat', 'cool']
  return Object.keys(hass.states).find(key => {
    if (!key.startsWith('select.')) return false;
    const st = hass.states[key];
    if (st && st.attributes && Array.isArray(st.attributes.options)) {
      const opts = st.attributes.options;
      return opts.includes('heat') && opts.includes('cool') && opts.length === 2;
    }
    return false;
  }) || null;
}

// Helper function to get current master HVAC mode ('heat' or 'cool')
function getMasterHVACMode(hass) {
  if (!hass || !hass.states) return 'heat';
  const opSelect = findMasterOperationModeEntity(hass);
  if (opSelect && hass.states[opSelect]) {
    const s = hass.states[opSelect].state;
    if (s === 'heat' || s === 'cool') return s;
  }
  const masterSwitch = findMasterEntity(hass);
  if (masterSwitch && hass.states[masterSwitch]) {
    const attrs = hass.states[masterSwitch].attributes || {};
    if (attrs.master_hvac_mode) return attrs.master_hvac_mode;
  }
  return 'heat';
}

/* ==================== BUTTON CARD CLASS ==================== */
