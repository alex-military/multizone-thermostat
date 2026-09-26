// window.customCards definition to register the cards in Lovelace UI card picker
window.customCards = window.customCards || [];
window.customCards.push({
  type: "multizone-thermostat-button-card",
  name: "Multizone Thermostat Card (Buttons)",
  description: "A card to control a heating zone using simple buttons and a bypass switch.",
  preview: true,
});
window.customCards.push({
  type: "multizone-thermostat-dial-card",
  name: "Multizone Thermostat Card (Dial)",
  description: "A card wrapping the native Home Assistant thermostat dial with an integrated zone bypass switch.",
  preview: true,
});
window.customCards.push({
  type: "multizone-thermostat-status-card",
  name: "Multizone Thermostat Master Card",
  description: "A zero-config button card that controls the Heating Master switch and displays system status (Gray = Off, Yellow = Standby, Orange = Heating).",
  preview: true,
});
window.customCards.push({
  type: "multizone-thermostat-preset-card",
  name: "Multizone Thermostat Preset Card",
  description: "A quick selection card for Global Presets (Comfort, Eco, Sleep, Away).",
  preview: true,
});
window.customCards.push({
  type: "multizone-thermostat-plant-card",
  name: "Multizone Thermostat Plant Health Card",
  description: "A modern card displaying boiler telemetry, short-cycling frequency and physical plant health.",
  preview: true,
});
window.customCards.push({
  type: "multizone-thermostat-zone-energy-card",
  name: "Multizone Thermostat Zone Energy Card",
  description: "A modern card displaying room energy efficiency class (A4-G), thermal retention time and radiator sizing.",
  preview: true,
});

const TRANSLATIONS = {
  it: {
    enabled: "Abilitata",
    heating: "Riscaldamento",
    heating_active: "Riscaldamento Attivo",
    idle: "Standby (In Attesa)",
    off: "Spento",
    excluded: "Zona Esclusa",
    bypass_msg: "Zona Esclusa / Bypassata",
    caldaia_circ: "Caldaia/Circolatore",
    system_active: "Sistema Attivo",
    system_off: "Sistema Spento",
    searching: "Ricerca...",
    master_not_found: "Master non trovato",
    temp_detected: "Rilevata",
    custom_error: "Errore scheda Multizone Thermostat",
    heat_mode: "Caldo",
    primary: "Prioritaria",
    secondary: "Secondaria",
    primary_tooltip: "Primaria (Accende Caldaia)",
    secondary_tooltip: "Secondaria (Passiva)",
    bypass_tooltip: "Bypass (Esclusa)",
    master_title: "Riscaldamento Centrale",
    thermostat: "Termostato",
    edit_title: "Titolo Personalizzato (Opzionale)",
    edit_climate: "Termostato (Climate Entity)",
    edit_switch: "Switch di Zona (Abilita/Escludi)",
    preset_manual: "Manuale",
    preset_eco: "Eco",
    preset_comfort: "Comfort",
    preset_sleep: "Notte",
    preset_away: "Fuori Casa",
    preset_card_title: "Preset Globale",
    edit_preset: "EntitÃ  Preset (Opzionale)"
  },
  en: {
    enabled: "Enabled",
    heating: "Heating",
    heating_active: "Active Heating",
    idle: "Standby (Idle)",
    off: "Off",
    excluded: "Zone Excluded",
    bypass_msg: "Zone Excluded / Bypassed",
    caldaia_circ: "Boiler/Circulator",
    system_active: "System Active",
    system_off: "System Off",
    searching: "Searching...",
    master_not_found: "Master not found",
    temp_detected: "Detected",
    custom_error: "Multizone Thermostat Card Error",
    heat_mode: "Heat",
    primary: "Primary",
    secondary: "Secondary",
    primary_tooltip: "Primary (Calls for Heat)",
    secondary_tooltip: "Secondary (Passive)",
    bypass_tooltip: "Bypass (Excluded)",
    master_title: "Central Heating",
    thermostat: "Thermostat",
    edit_title: "Custom Title (Optional)",
    edit_climate: "Thermostat (Climate Entity)",
    edit_switch: "Zone Switch (Enable/Exclude)",
    preset_manual: "Manual",
    preset_eco: "Eco",
    preset_comfort: "Comfort",
    preset_sleep: "Sleep",
    preset_away: "Away",
    preset_card_title: "Global Preset",
    edit_preset: "Preset Entity (Optional)"
  }
};

function getTranslation(hass, key) {
  const lang = hass && hass.language ? hass.language.split('-')[0] : 'en';
  const translations = TRANSLATIONS[lang] || TRANSLATIONS['en'];
  return translations[key] || TRANSLATIONS['en'][key] || key;
}

// Helper function to auto-discover the bypass switch for a climate entity
function autoDiscoverSwitch(hass, climateId) {
  if (!hass || !climateId) return "";
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
class MultizoneThermostatButtonCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: 'open' });
    this.renderStructure();
  }

  set hass(hass) {
    this._hass = hass;
    this.updateCard();
  }

  setConfig(config) {
    if (!config.entity) {
      throw new Error("Specificare un termostato (climate entity)");
    }
    this._config = config;
  }

  getCardSize() {
    return 3;
  }

  static getConfigElement() {
    return document.createElement("multizone-thermostat-card-editor");
  }

  static getStubConfig() {
    return {
      entity: "",
      switch: "",
      title: ""
    };
  }

  updateCard() {
    if (!this._hass || !this._config) return;

    const climateEntity = this._config.entity;
    let switchEntity = this._config.switch;

    // Auto-migrate legacy zone_enable switch configs
    if (switchEntity && switchEntity.endsWith('_zone_enable')) {
      switchEntity = null;
    }

    if (!switchEntity || !this._hass.states[switchEntity]) {
      const discovered = autoDiscoverSwitch(this._hass, climateEntity);
      if (discovered) switchEntity = discovered;
      // Only update config if we discovered something new so we don't keep searching
      if (discovered && this._config.switch !== discovered) {
        this._config = {...this._config, switch: discovered};
      }
    }

    const climateState = this._hass.states[climateEntity];
    const switchState = switchEntity ? this._hass.states[switchEntity] : null;

    if (!climateState) {
      this.renderError(getTranslation(this._hass, 'custom_error') + `: ${climateEntity} not found.`);
      return;
    }

    const currentTemp = climateState.attributes.current_temperature;
    const targetTemp = climateState.attributes.temperature;
    const hvacMode = climateState.state;
    const hvacAction = climateState.attributes.hvac_action;
    
    // Use temporary switch state if toggled locally to avoid flickering
    const actualSwitchState = this._tempSwitchState !== undefined 
      ? this._tempSwitchState 
      : (switchState ? switchState.state : "primary");

    const title = this._config.title || climateState.attributes.friendly_name || getTranslation(this._hass, 'thermostat');

    // Update title
    this.shadowRoot.querySelector('.title').textContent = title;

    // Update segmented buttons state
    const segContainer = this.shadowRoot.querySelector('#zone-modes-container');
    const segPrimary = this.shadowRoot.querySelector('#seg-primary');
    const segSecondary = this.shadowRoot.querySelector('#seg-secondary');
    const segBypass = this.shadowRoot.querySelector('#seg-bypass');
    
    if (switchEntity) {
      if (segContainer) segContainer.style.display = 'flex';
      if (segPrimary) segPrimary.classList.toggle('active', actualSwitchState === "primary" || actualSwitchState === "on");
      if (segSecondary) segSecondary.classList.toggle('active', actualSwitchState === "secondary");
      if (segBypass) segBypass.classList.toggle('active', actualSwitchState === "bypass" || actualSwitchState === "off");
    } else {
      if (segContainer) segContainer.style.display = 'none';
    }

    // Apply active/disabled styling
    const controlsArea = this.shadowRoot.querySelector('.thermostat-body');
    const wrapper = this.shadowRoot.querySelector('#wrapper');
    const disabledOverlay = this.shadowRoot.querySelector('.disabled-msg');
    const disabledMsgBox = this.shadowRoot.querySelector('.disabled-msg-box');
    if (disabledMsgBox) {
      disabledMsgBox.innerHTML = `<ha-icon icon="mdi:alert-circle-outline" style="margin-right: 6px;"></ha-icon>${getTranslation(this._hass, 'bypass_msg')}`;
    }
    if (actualSwitchState !== "bypass" && actualSwitchState !== "off") {
      controlsArea.classList.remove('disabled');
      wrapper.classList.remove('disabled');
      if (disabledOverlay) disabledOverlay.style.display = 'none';
      if (hvacAction === 'heating') {
        controlsArea.classList.add('heating');
      } else {
        controlsArea.classList.remove('heating');
      }
    } else {
      controlsArea.classList.add('disabled');
      wrapper.classList.add('disabled');
      if (disabledOverlay) disabledOverlay.style.display = 'block';
    }

    // Update temperatures
    const tempCurrentEl = this.shadowRoot.querySelector('.temp-current');
    if (tempCurrentEl) {
      const curStr = currentTemp !== undefined ? `${currentTemp}Â°C` : '--Â°C';
      tempCurrentEl.innerHTML = `<span class="temp-current-val">${curStr}</span>`;
    }
    this.shadowRoot.querySelector('.temp-target-val').textContent = targetTemp !== undefined ? `${targetTemp}Â°C` : '--Â°C';
    
    const tempTargetEl = this.shadowRoot.querySelector('.temp-target');
    if (tempTargetEl) {
      if (hvacAction === 'heating') {
        tempTargetEl.classList.add('heating');
      } else {
        tempTargetEl.classList.remove('heating');
      }
    }

    const badge = this.shadowRoot.querySelector('.status-badge');
    badge.className = 'status-badge';
    if (actualSwitchState === "bypass" || actualSwitchState === "off") {
      badge.innerHTML = "";
    } else if (actualSwitchState === "secondary") {
      badge.style.color = '#607d8b';
      badge.innerHTML = `<ha-icon icon="mdi:link-variant" style="margin-right: 4px; --mdc-icon-size: 16px;"></ha-icon>${getTranslation(this._hass, 'secondary')}`;
    } else {
      badge.style.color = 'var(--primary-color, #03a9f4)';
      badge.innerHTML = `<ha-icon icon="mdi:star-circle-outline" style="margin-right: 4px; --mdc-icon-size: 16px;"></ha-icon>${getTranslation(this._hass, 'primary')}`;
    }
  }


  renderStructure() {
    const card = document.createElement('ha-card');
    const style = document.createElement('style');

    style.textContent = `
      ha-card {
        padding: 16px;
        position: relative;
        overflow: hidden;
      }
      .wrapper {
        position: relative;
        display: block;
      }
      .header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 12px;
      }
      .title {
        font-size: 18px;
        font-weight: 500;
        color: var(--primary-text-color);
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        max-width: 70%;
      }
      .switch-container {
        display: flex;
        align-items: center;
        z-index: 10;
      }
      .switch-container label {
        margin-right: 8px;
        font-size: 12px;
        color: var(--secondary-text-color);
      }
      /* Segmented Control Styles */
      .segmented-control {
        display: flex;
        align-items: center;
        background-color: var(--secondary-background-color, #e0e0e0);
        border-radius: 8px;
        padding: 2px;
        position: relative;
      }
      .seg-btn {
        background: transparent;
        border: none;
        color: var(--secondary-text-color);
        padding: 6px 12px;
        cursor: pointer;
        border-radius: 6px;
        display: flex;
        align-items: center;
        justify-content: center;
        transition: background 0.3s, color 0.3s;
      }
      .seg-btn.active {
        background-color: var(--primary-color, #03a9f4);
        color: white;
        box-shadow: 0 1px 3px rgba(0,0,0,0.2);
      }
      .seg-btn ha-icon {
        --mdc-icon-size: 18px;
      }

      .thermostat-body {
        transition: opacity 0.3s ease;
        border-radius: var(--ha-card-border-radius, 12px);
        position: relative;
      }
      .thermostat-body.disabled {
        opacity: 0.25;
        pointer-events: none;
      }

      .disabled-msg {
        display: none;
        position: absolute;
        top: 40px; left: 0; right: 0; bottom: 0;
        background: rgba(0,0,0,0.15);
        z-index: 10;
        border-radius: 0 0 var(--ha-card-border-radius, 12px) var(--ha-card-border-radius, 12px);
        backdrop-filter: blur(2px);
      }
      .disabled-msg-box {
        position: absolute;
        top: 50%; left: 50%;
        transform: translate(-50%, -50%);
        background: var(--card-background-color);
        padding: 8px 16px;
        border-radius: 20px;
        font-weight: 500;
        color: var(--secondary-text-color);
        box-shadow: 0 4px 8px rgba(0,0,0,0.2);
        white-space: nowrap;
      }

      .controls-container {
        display: flex;
        justify-content: space-around;
        align-items: center;
        margin: 16px 0;
      }
      .btn-temp {
        width: 50px;
        height: 50px;
        border-radius: 50%;
        border: 1px solid var(--divider-color);
        background-color: var(--secondary-background-color);
        color: var(--primary-text-color);
        font-size: 24px;
        cursor: pointer;
        display: flex;
        align-items: center;
        justify-content: center;
        transition: background-color 0.2s, transform 0.1s;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
      }
      .btn-temp:hover {
        background-color: var(--divider-color);
      }
      .btn-temp:active {
        transform: scale(0.95);
      }

      .temp-display {
        display: flex;
        flex-direction: column;
        align-items: center;
        position: relative;
        z-index: 0;
      }
      .thermostat-body.heating .temp-display::before {
        content: '';
        position: absolute;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        width: 440px;
        height: 440px;
        border-radius: 50%;
        background: radial-gradient(closest-side, rgba(255, 111, 0, 0.35) 0%, rgba(255, 111, 0, 0.15) 30%, rgba(255, 111, 0, 0.02) 75%, transparent 100%);
        z-index: -1;
        pointer-events: none;
        animation: pulse-halo 2s infinite alternate;
      }
      @keyframes pulse-halo {
        0% { opacity: 0.8; transform: translate(-50%, -50%) scale(0.95); }
        100% { opacity: 1; transform: translate(-50%, -50%) scale(1.05); }
      }
      .temp-target-val {
        font-size: 42px;
        font-weight: 300;
        color: var(--primary-text-color);
        line-height: 1.1;
        transition: text-shadow 0.3s, color 0.3s;
      }
      .temp-target.heating .temp-target-val {
        color: rgb(255, 152, 0);
        text-shadow: 0 0 10px rgba(255, 152, 0, 0.5), 0 0 20px rgba(255, 152, 0, 0.3);
        animation: pulse-glow 1.5s infinite alternate;
      }
      @keyframes pulse-glow {
        0% { text-shadow: 0 0 10px rgba(255, 152, 0, 0.5), 0 0 20px rgba(255, 152, 0, 0.3); }
        100% { text-shadow: 0 0 15px rgba(255, 111, 0, 0.9), 0 0 30px rgba(255, 111, 0, 0.6); }
      }
      .temp-current {
        font-size: 14px;
        color: var(--secondary-text-color);
        margin-top: 4px;
      }

      .status-bar {
        display: flex;
        justify-content: center;
        margin-bottom: 16px;
      }
      .status-badge {
        display: inline-flex;
        align-items: center;
        font-size: 14px;
        font-weight: 400;
        color: var(--secondary-text-color);
      }
      .status-badge.heating { color: rgb(255, 111, 0); }
      .status-badge.idle { color: rgb(0, 150, 136); }
      .status-badge.disabled { color: rgb(244, 67, 54); }

      .glow-flame {
        animation: pulse-flame 1.5s infinite alternate;
      }
      @keyframes pulse-flame {
        0% { transform: scale(1); filter: drop-shadow(0 0 1px rgba(255,111,0,0.5)); }
        100% { transform: scale(1.1); filter: drop-shadow(0 0 5px rgba(255,111,0,0.8)); }
      }

    `;

    card.innerHTML = `
      <div class="wrapper" id="wrapper">
        <div class="header">
          <div class="title">Termostato</div>
          <div class="segmented-control" id="zone-modes-container">
            <button class="seg-btn primary" id="seg-primary"><ha-icon icon="mdi:star-circle-outline"></ha-icon></button>
            <button class="seg-btn secondary" id="seg-secondary"><ha-icon icon="mdi:link-variant"></ha-icon></button>
            <button class="seg-btn bypass" id="seg-bypass"><ha-icon icon="mdi:cancel"></ha-icon></button>
          </div>
        </div>

        <div class="disabled-msg">
          <div class="disabled-msg-box">
            <ha-icon icon="mdi:alert-circle-outline" style="margin-right: 6px;"></ha-icon>Zona Esclusa / Bypassata
          </div>
        </div>

        <div class="thermostat-body">
          <div class="controls-container">
            <button class="btn-temp" id="temp-down">-</button>
            <div class="temp-display">
              <div class="temp-target">
                <span class="temp-target-val">--Â°C</span>
              </div>
              <div class="temp-current"><span class="temp-current-val">--Â°C</span></div>
            </div>
            <button class="btn-temp" id="temp-up">+</button>
          </div>

          <div class="status-bar">
            <div class="status-badge"></div>
          </div>


        </div>
      </div>
    `;

    // Hook events
    card.querySelector('#seg-primary').addEventListener('click', () => this.setZoneMode("primary"));
    card.querySelector('#seg-secondary').addEventListener('click', () => this.setZoneMode("secondary"));
    card.querySelector('#seg-bypass').addEventListener('click', () => this.setZoneMode("bypass"));

    card.querySelector('#temp-down').addEventListener('click', () => this.changeTemp(-0.5));
    card.querySelector('#temp-up').addEventListener('click', () => this.changeTemp(0.5));



    this.shadowRoot.appendChild(style);
    this.shadowRoot.appendChild(card);
    this._rendered = true;
  }

  setZoneMode(mode) {
    const switchEntity = this._config.switch;
    if (!switchEntity) return;

    this._tempSwitchState = mode;
    this.updateCard(); // immediate local UI update
    
    // If it's a switch entity (legacy), map back to on/off
    if (switchEntity.startsWith("switch.")) {
      const enable = mode !== "bypass";
      this._hass.callService("switch", enable ? "turn_on" : "turn_off", {
        entity_id: switchEntity
      });
    } else {
      // It's a select entity
      this._hass.callService("select", "select_option", {
        entity_id: switchEntity,
        option: mode
      });
    }

    if (this._tempTimer) clearTimeout(this._tempTimer);
    this._tempTimer = setTimeout(() => {
      this._tempSwitchState = undefined;
      this.updateCard();
    }, 1000);
  }

  changeTemp(step) {
    const climateEntity = this._config.entity;
    const state = this._hass.states[climateEntity];
    if (!state) return;

    const currentTarget = state.attributes.temperature;
    if (currentTarget === undefined) return;

    const newTarget = Math.round((currentTarget + step) * 2) / 2;

    this._hass.callService("climate", "set_temperature", {
      entity_id: climateEntity,
      temperature: newTarget
    });
  }

  disconnectedCallback() {
    super.disconnectedCallback();
    if (this._tempTimer) {
        clearTimeout(this._tempTimer);
        this._tempTimer = null;
    }
  }

  renderError(msg) {
    this.shadowRoot.innerHTML = `
      <ha-card style="padding: 16px; color: red;">
        <h3>Errore scheda Multizone Thermostat</h3>
        <p>${msg}</p>
      </ha-card>
    `;
    this._rendered = false;
  }
}


/* ==================== DIAL (NATIVE WRAPPER) CARD CLASS ==================== */
class MultizoneThermostatDialCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: 'open' });
    this.renderStructure();
  }

  set hass(hass) {
    this._hass = hass;
    if (this._childCard) {
      this._childCard.hass = hass;
    }
    this.updateCard();
  }

  setConfig(config) {
    if (!config.entity) {
      throw new Error("Specificare un termostato (climate entity)");
    }
    this._config = config;
    this.loadHelpers();
  }

  async loadHelpers() {
    try {
      this._helpers = await window.loadCardHelpers();
      this.createChildCard();
    } catch (err) {
      console.error("Errore nel caricamento dei card helpers di Home Assistant:", err);
    }
  }

  getCardSize() {
    return 3;
  }

  static getConfigElement() {
    return document.createElement("multizone-thermostat-card-editor");
  }

  static getStubConfig() {
    return {
      entity: "",
      switch: "",
      title: ""
    };
  }

  createChildCard() {
    if (!this._helpers || !this._config) return;

    const cardConfig = {
      type: "thermostat",
      entity: this._config.entity,
      name: " ", // Empty space to hide native title and avoid duplicate titles
    };

    this._childCard = this._helpers.createCardElement(cardConfig);
    
    if (this._hass) {
      this._childCard.hass = this._hass;
    }

    const body = this.shadowRoot.querySelector('#card-body');
    if (body) {
      body.innerHTML = '';
      body.appendChild(this._childCard);
    }
  }

  updateCard() {
    if (!this._hass || !this._config) return;

    const card = this.shadowRoot.querySelector('ha-card');
    if (card) {
      if (this._config.height) card.style.height = this._config.height;
      if (this._config.width) card.style.width = this._config.width;
      if (this._config.border_radius) card.style.borderRadius = this._config.border_radius;
      if (this._config.min_height) card.style.minHeight = this._config.min_height;
      if (this._config.max_height) card.style.maxHeight = this._config.max_height;
      if (this._config.padding) card.style.padding = this._config.padding;
    }

    const climateEntity = this._config.entity;
    let switchEntity = this._config.switch;
    
    // Auto-migrate legacy zone_enable switch configs
    if (switchEntity && switchEntity.endsWith('_zone_enable')) {
      switchEntity = null;
    }

    if (!switchEntity || !this._hass.states[switchEntity]) {
      const discovered = autoDiscoverSwitch(this._hass, climateEntity);
      if (discovered) switchEntity = discovered;
      if (discovered && this._config.switch !== discovered) {
        this._config = {...this._config, switch: discovered};
      }
    }
    
    const climateState = this._hass.states[climateEntity];
    const switchState = switchEntity ? this._hass.states[switchEntity] : null;

    if (!climateState) {
      this.renderError(getTranslation(this._hass, 'custom_error') + `: ${climateEntity} not found.`);
      return;
    }

    let displayTitle = this._config.title || climateState.attributes.friendly_name || climateEntity;
    if (displayTitle) {
      displayTitle = displayTitle.replace(/^Virtual Thermostats VT /i, '').replace(/^Heating Zones(?: Zone)? /i, '');
    }

    const titleEl = this.shadowRoot.querySelector('.title');
    if (titleEl) {
      titleEl.textContent = displayTitle;
    }

    // Use temporary switch state if toggled locally to avoid flickering
    let actualSwitchState = "primary";
    if (this._tempSwitchState !== undefined) {
      actualSwitchState = this._tempSwitchState;
    } else if (switchState && switchState.state) {
      actualSwitchState = switchState.state;
    } else if (climateState && climateState.attributes && climateState.attributes.zone_mode) {
      actualSwitchState = climateState.attributes.zone_mode;
    }

    // Update segmented buttons state and tooltips
    const segPrimary = this.shadowRoot.querySelector('#seg-primary');
    const segSecondary = this.shadowRoot.querySelector('#seg-secondary');
    const segBypass = this.shadowRoot.querySelector('#seg-bypass');
    
    if (segPrimary) {
      segPrimary.classList.toggle('active', actualSwitchState === "primary" || actualSwitchState === "on");
      segPrimary.title = getTranslation(this._hass, 'primary_tooltip');
    }
    if (segSecondary) {
      segSecondary.classList.toggle('active', actualSwitchState === "secondary");
      segSecondary.title = getTranslation(this._hass, 'secondary_tooltip');
    }
    if (segBypass) {
      segBypass.classList.toggle('active', actualSwitchState === "bypass" || actualSwitchState === "off");
      segBypass.title = getTranslation(this._hass, 'bypass_tooltip');
    }
    
    // Update disabled overlay text
    const disabledMsgBox = this.shadowRoot.querySelector('.disabled-msg-box');
    if (disabledMsgBox) {
      disabledMsgBox.innerHTML = `<ha-icon icon="mdi:alert-circle-outline" style="margin-right: 6px;"></ha-icon>${getTranslation(this._hass, 'bypass_msg')}`;
    }

    // Update status text
    const badge = this.shadowRoot.querySelector('.status-badge');
    if (badge) {
      badge.className = 'status-badge';
      if (actualSwitchState === "bypass" || actualSwitchState === "off") {
        badge.innerHTML = "";
      } else if (actualSwitchState === "secondary") {
        badge.style.color = '#607d8b';
        badge.innerHTML = `<ha-icon icon="mdi:link-variant" style="margin-right: 4px; --mdc-icon-size: 16px;"></ha-icon>${getTranslation(this._hass, 'secondary')}`;
      } else {
        badge.style.color = 'var(--primary-color, #03a9f4)';
        badge.innerHTML = `<ha-icon icon="mdi:star-circle-outline" style="margin-right: 4px; --mdc-icon-size: 16px;"></ha-icon>${getTranslation(this._hass, 'primary')}`;
      }
    }

    // Apply active/disabled styling and overlay
    const wrapper = this.shadowRoot.querySelector('#wrapper');
    if (wrapper) {
      if (actualSwitchState !== "bypass" && actualSwitchState !== "off") {
        wrapper.classList.remove('disabled');
      } else {
        wrapper.classList.add('disabled');
      }
    }
  }

  renderStructure() {
    const style = document.createElement('style');

    style.textContent = `
      ha-card {
        padding: 16px;
        position: relative;
        overflow: hidden;
      }
      .wrapper {
        position: relative;
        display: block;
      }
      .header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 4px;
        padding-bottom: 4px;
        padding-left: 8px;
        position: relative;
        z-index: 20;
      }
      .title {
        font-size: 16px;
        font-weight: 500;
        color: var(--primary-text-color);
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        max-width: 60%;
      }
      .status-bar {
        position: absolute;
        top: 100px;
        left: 0;
        right: 0;
        display: flex;
        justify-content: center;
        z-index: 10;
        pointer-events: none;
      }
      .status-badge {
        display: inline-flex;
        align-items: center;
        font-size: 14px;
        font-weight: 400;
        color: var(--secondary-text-color);
      }
      .status-badge.heating { color: rgb(255, 111, 0); }
      .status-badge.idle { color: rgb(0, 150, 136); }
      .status-badge.disabled { color: rgb(244, 67, 54); }

      .glow-flame {
        animation: pulse-flame 1.5s infinite alternate;
      }
      @keyframes pulse-flame {
        0% { transform: scale(1); filter: drop-shadow(0 0 1px rgba(255,111,0,0.5)); }
        100% { transform: scale(1.1); filter: drop-shadow(0 0 5px rgba(255,111,0,0.8)); }
      }

      /* Segmented Control Styles */
      .segmented-control {
        display: flex;
        align-items: center;
        background-color: var(--secondary-background-color, #e0e0e0);
        border-radius: 8px;
        padding: 2px;
        position: relative;
        z-index: 21;
      }
      .seg-btn {
        background: transparent;
        border: none;
        color: var(--secondary-text-color);
        padding: 6px 12px;
        cursor: pointer;
        border-radius: 6px;
        display: flex;
        align-items: center;
        justify-content: center;
        transition: background 0.3s, color 0.3s;
      }
      .seg-btn.active {
        background-color: var(--primary-color, #03a9f4);
        color: white;
        box-shadow: 0 1px 3px rgba(0,0,0,0.2);
      }
      .seg-btn ha-icon {
        --mdc-icon-size: 18px;
      }

      .disabled-overlay {
        display: none;
        position: absolute;
        top: 40px; /* Positioned below our custom header, covering only the native card body */
        left: 0;
        right: 0;
        bottom: 0;
        z-index: 8;
        background: rgba(0, 0, 0, 0.15);
        backdrop-filter: blur(2px);
        align-items: center;
        justify-content: center;
        border-radius: 0 0 var(--ha-card-border-radius, 12px) var(--ha-card-border-radius, 12px);
        pointer-events: none;
      }
      .disabled-msg-box {
        display: inline-flex;
        align-items: center;
        background: var(--card-background-color);
        border: 1px solid var(--divider-color);
        padding: 10px 16px;
        border-radius: 8px;
        box-shadow: 0 4px 8px rgba(0,0,0,0.15);
        color: var(--secondary-text-color);
        font-weight: 500;
        pointer-events: auto;
      }

      /* Native Thermostat card styles styling (custom variables are passed down shadow bounds) */
      #card-body {
        --ha-card-background: none;
        --ha-card-box-shadow: none;
        --ha-card-border-width: 0px;
        --ha-card-border-color: transparent;
        margin-top: -16px; /* pull the native card slightly up to align it nicely */
      }

      /* When zone is disabled: fade out the native card */
      .wrapper.disabled #card-body {
        opacity: 0.25;
        pointer-events: none;
      }
      .wrapper.disabled .disabled-overlay {
        display: flex;
      }
    `;

    const card = document.createElement('ha-card');
    
    const wrapper = document.createElement('div');
    wrapper.className = 'wrapper';
    wrapper.id = 'wrapper';

    // The layout renders our custom header inside our own ha-card.
    // The native card below is stripped of its borders/title/shadows.
    wrapper.innerHTML = `
      <div class="header">
        <div class="title" id="card-title">Termostato</div>
        <div class="segmented-control" id="zone-modes-container">
          <button class="seg-btn primary" id="seg-primary"><ha-icon icon="mdi:star-circle-outline"></ha-icon></button>
          <button class="seg-btn secondary" id="seg-secondary"><ha-icon icon="mdi:link-variant"></ha-icon></button>
          <button class="seg-btn bypass" id="seg-bypass"><ha-icon icon="mdi:cancel"></ha-icon></button>
        </div>
      </div>
      
      <div class="status-bar">
        <div class="status-badge"></div>
      </div>

      <div class="disabled-overlay">
        <div class="disabled-msg-box">
          <ha-icon icon="mdi:alert-circle-outline" style="margin-right: 6px;"></ha-icon>Zona Esclusa / Bypassata
        </div>
      </div>

      <div id="card-body"></div>
    `;

    // Hook events
    wrapper.querySelector('#seg-primary').addEventListener('click', () => this.setZoneMode("primary"));
    wrapper.querySelector('#seg-secondary').addEventListener('click', () => this.setZoneMode("secondary"));
    wrapper.querySelector('#seg-bypass').addEventListener('click', () => this.setZoneMode("bypass"));

    card.appendChild(wrapper);
    this.shadowRoot.appendChild(style);
    this.shadowRoot.appendChild(card);
    this._rendered = true;
  }

  setZoneMode(mode) {
    let switchEntity = this._config.switch;
    if (!switchEntity || !this._hass.states[switchEntity]) {
      switchEntity = autoDiscoverSwitch(this._hass, this._config.entity);
      if (switchEntity) {
        this._config = {...this._config, switch: switchEntity};
      }
    }
    if (!switchEntity) return;

    this._tempSwitchState = mode;
    this.updateCard(); // immediate local UI update

    // If it's a switch entity (legacy), map back to on/off
    if (switchEntity.startsWith("switch.")) {
      const enable = mode !== "bypass";
      this._hass.callService("switch", enable ? "turn_on" : "turn_off", {
        entity_id: switchEntity
      });
    } else {
      // It's a select entity
      this._hass.callService("select", "select_option", {
        entity_id: switchEntity,
        option: mode
      });
    }

    if (this._tempTimer) clearTimeout(this._tempTimer);
    this._tempTimer = setTimeout(() => {
      this._tempSwitchState = undefined;
      this.updateCard();
    }, 1000);
  }

  disconnectedCallback() {
    super.disconnectedCallback();
    if (this._tempTimer) {
        clearTimeout(this._tempTimer);
        this._tempTimer = null;
    }
  }

  renderError(msg) {
    this.shadowRoot.innerHTML = `
      <ha-card style="padding: 16px; color: red;">
        <h3>Errore scheda Multizone Thermostat</h3>
        <p>${msg}</p>
      </ha-card>
    `;
    this._rendered = false;
  }
}


/* ==================== UNIFIED CARD CONFIGURATION EDITOR ==================== */
class MultizoneThermostatCardEditor extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: 'open' });
  }

  set hass(hass) {
    this._hass = hass;
    if (this._climatePicker) this._climatePicker.hass = hass;
    if (this._switchPicker) this._switchPicker.hass = hass;
    this.translateLabels();
  }

  setConfig(config) {
    this._config = config;
    this.render();
  }

  translateLabels() {
    if (!this._hass) return;
    const titleLabel = this.shadowRoot.querySelector('#title-label');
    if (titleLabel) titleLabel.textContent = getTranslation(this._hass, 'edit_title');
    const mainLabel = this.shadowRoot.querySelector('#main-label');
    if (mainLabel) mainLabel.textContent = getTranslation(this._hass, 'edit_climate');
    const switchLabel = this.shadowRoot.querySelector('#switch-label');
    if (switchLabel) switchLabel.textContent = getTranslation(this._hass, 'edit_switch');
  }

  render() {
    if (this._rendered) {
      this.shadowRoot.querySelector('#title').value = this._config.title || '';
      this._climatePicker.value = this._config.entity || '';
      this._switchPicker.value = this._config.switch || '';
      this.translateLabels();
      return;
    }

    const style = document.createElement('style');
    style.textContent = `
      .form-row {
        margin-bottom: 16px;
        display: flex;
        flex-direction: column;
      }
      label {
        font-weight: 500;
        margin-bottom: 8px;
        color: var(--primary-text-color);
      }
      input[type="text"] {
        padding: 10px;
        border-radius: 4px;
        border: 1px solid var(--divider-color);
        background: var(--card-background-color);
        color: var(--primary-text-color);
        font-size: 14px;
      }
    `;

    const container = document.createElement('div');
    container.className = 'editor-container';

    // Title Row
    const titleRow = document.createElement('div');
    titleRow.className = 'form-row';
    const titleLabel = document.createElement('label');
    titleLabel.id = 'title-label';
    titleLabel.textContent = 'Titolo Personalizzato (Opzionale)';
    const titleInput = document.createElement('input');
    titleInput.type = 'text';
    titleInput.id = 'title';
    titleInput.value = this._config.title || '';
    titleInput.addEventListener('change', (e) => this._updateConfig('title', e.target.value));
    titleRow.appendChild(titleLabel);
    titleRow.appendChild(titleInput);
    container.appendChild(titleRow);

    // Climate Entity Picker Row
    const climateRow = document.createElement('div');
    climateRow.className = 'form-row';
    const climateLabel = document.createElement('label');
    climateLabel.id = 'main-label';
    climateLabel.textContent = 'Termostato (Climate Entity)';
    const climatePicker = document.createElement('ha-entity-picker');
    climatePicker.includeDomains = ['climate'];
    climatePicker.value = this._config.entity || '';
    climatePicker.hass = this._hass;
    
    // Automatically pre-fill the corresponding switch when the climate entity changes
    climatePicker.addEventListener('value-changed', (e) => {
      const selectedClimate = e.detail.value;
      const discoveredSwitch = autoDiscoverSwitch(this._hass, selectedClimate);
      
      const newConfig = { 
        ...this._config, 
        entity: selectedClimate,
        switch: discoveredSwitch || ''
      };
      
      this._switchPicker.value = discoveredSwitch || '';
      
      this.dispatchEvent(new CustomEvent('config-changed', {
        detail: { config: newConfig },
        bubbles: true,
        composed: true
      }));
    });
    
    this._climatePicker = climatePicker;
    climateRow.appendChild(climateLabel);
    climateRow.appendChild(climatePicker);
    container.appendChild(climateRow);

    // Switch Entity Picker Row
    const switchRow = document.createElement('div');
    switchRow.className = 'form-row';
    const switchLabel = document.createElement('label');
    switchLabel.id = 'switch-label';
    switchLabel.textContent = 'Switch di Zona (Abilita/Escludi)';
    const switchPicker = document.createElement('ha-entity-picker');
    switchPicker.includeDomains = ['switch', 'select'];
    switchPicker.value = this._config.switch || '';
    switchPicker.hass = this._hass;
    switchPicker.addEventListener('value-changed', (e) => this._updateConfig('switch', e.detail.value));
    this._switchPicker = switchPicker;
    switchRow.appendChild(switchLabel);
    switchRow.appendChild(switchPicker);
    container.appendChild(switchRow);

    this.shadowRoot.appendChild(style);
    this.shadowRoot.appendChild(container);
    this._rendered = true;
    this.translateLabels();
  }

  _updateConfig(key, value) {
    if (!this._config) return;
    const newConfig = { ...this._config, [key]: value };
    const event = new CustomEvent('config-changed', {
      detail: { config: newConfig },
      bubbles: true,
      composed: true,
    });
    this.dispatchEvent(event);
  }
}

/* ==================== STATUS (BUTTON-STYLE MASTER SWITCH) CARD CLASS ==================== */
class MultizoneThermostatStatusCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: 'open' });
  }

  set hass(hass) {
    this._hass = hass;
    this.updateCard();
  }

  setConfig(config) {
    this._config = config || {};
    if (!this._rendered) {
      this.renderStructure();
    }
  }

  getCardSize() {
    return 1;
  }

  renderStructure() {
    const card = document.createElement('ha-card');
    const style = document.createElement('style');

    style.textContent = `
      ha-card {
        padding: 16px;
        border-radius: var(--ha-card-border-radius, 12px);
        color: white;
        transition: background-color 0.5s ease, transform 0.2s ease, box-shadow 0.2s ease;
        cursor: pointer;
        display: flex;
        align-items: center;
        min-height: 90px;
        position: relative;
        overflow: hidden;
        border: none;
      }
      ha-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 12px rgba(0, 0, 0, 0.25);
      }
      ha-card:active {
        transform: translateY(0);
      }
      .card-content {
        display: flex;
        align-items: center;
        width: 100%;
        gap: 16px;
        pointer-events: none;
      }
      .icon-container {
        display: flex;
        align-items: center;
        justify-content: center;
        width: 52px;
        height: 52px;
        border-radius: 50%;
        background: rgba(255, 255, 255, 0.15);
        flex-shrink: 0;
      }
      .icon-container ha-icon {
        --mdc-icon-size: 28px;
        color: white;
      }
      .info-container {
        display: flex;
        flex-direction: column;
        justify-content: center;
        flex-grow: 1;
        overflow: hidden;
      }
      .name {
        font-size: 18px;
        font-weight: 600;
        margin: 0;
        text-shadow: 0 1px 2px rgba(0,0,0,0.15);
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
      }
      .state {
        font-size: 13px;
        font-weight: 500;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin: 4px 0;
        opacity: 0.9;
        text-shadow: 0 1px 1px rgba(0,0,0,0.1);
      }
      .temp-row {
        font-size: 12px;
        opacity: 0.85;
      }
      .glow-flame {
        animation: pulse-flame 1.5s infinite alternate;
      }
      @keyframes pulse-flame {
        0% { transform: scale(1); filter: drop-shadow(0 0 1px rgba(255,255,255,0.4)); }
        100% { transform: scale(1.1); filter: drop-shadow(0 0 6px rgba(255,255,255,0.7)); }
      }
    `;

    card.innerHTML = `
      <div class="card-content">
        <div class="icon-container">
          <ha-icon icon="mdi:power"></ha-icon>
        </div>
        <div class="info-container">
          <div class="name">Riscaldamento Centrale</div>
          <div class="state">Ricerca...</div>
          <div class="temp-row">Caldaia: --</div>
        </div>
      </div>
    `;

    // Hook tap event to toggle the master entity
    card.addEventListener('click', () => this.handleTap());

    this.shadowRoot.appendChild(style);
    this.shadowRoot.appendChild(card);
    this._rendered = true;
  }

  handleTap() {
    const presetEntity = findPresetEntity(this._hass);
    if (!presetEntity) return;

    const presetState = this._hass.states[presetEntity];
    if (!presetState) return;

    // Toggle between manual (off) and the first available heating preset (like 'home')
    const options = presetState.attributes.options || [];
    let newPreset = "manual";
    if (presetState.state === "manual" && options.length > 1) {
        // Find the first option that isn't manual
        newPreset = options.find(o => o !== "manual") || "manual";
    }

    const domain = presetEntity.split('.')[0];
    this._hass.callService(domain, "select_option", {
      entity_id: presetEntity,
      option: newPreset
    });
  }

  updateCard() {
    if (!this._hass || !this._rendered) return;

    // We no longer rely on a master switch, we use the global preset to determine if system is ON
    const presetEntity = findPresetEntity(this._hass);
    let isMasterOn = false;
    let boilerEntity = null;

    if (presetEntity) {
      const presetState = this._hass.states[presetEntity];
      if (presetState) {
        isMasterOn = presetState.state !== "manual" && presetState.state !== "off";
      }
    }

    // Try to find the boiler switch directly or through climate attributes
    boilerEntity = this._config.entity || this._config.boiler_entity;
    if (!boilerEntity) {
      // First try to find a climate entity that has the boiler_entity_id attribute
      const zoneClimate = Object.values(this._hass.states).find(s => 
        s.entity_id.startsWith('climate.') && s.attributes && s.attributes.hybrid_zone === true && s.attributes.boiler_entity_id
      );
      
      if (zoneClimate) {
        boilerEntity = zoneClimate.attributes.boiler_entity_id;
      } else {
        // Fallback to name heuristic
        const boilerFound = Object.keys(this._hass.states).find(key => {
          return key.startsWith('switch.') && (key.includes('boiler') || key.includes('caldaia'));
        });
        if (boilerFound) {
           boilerEntity = boilerFound;
        }
      }
    }
    const boilerState = boilerEntity ? this._hass.states[boilerEntity] : null;
    let isBoilerOn = boilerState ? boilerState.state === "on" : false;

    // Fallback for OpenTherm or unreadable boiler state: check if any hybrid zone is actively heating
    if (!isBoilerOn) {
      const isAnyZoneHeating = Object.values(this._hass.states).some(s => 
        s.entity_id.startsWith('climate.') && 
        s.attributes && 
        s.attributes.hvac_action === 'heating'
      );
      if (isAnyZoneHeating) {
        isBoilerOn = true;
      }
    }

    let bgColor = "#37474f"; // grigio quando spento
    let stateText = getTranslation(this._hass, 'off');
    let iconName = this._config.icon || "mdi:power";
    let glowClass = false;

    if (!isMasterOn) {
      bgColor = "#37474f"; // grigio quando spento
      stateText = getTranslation(this._hass, 'off');
      iconName = this._config.icon || "mdi:power";
    } else {
      // Master acceso
      if (isBoilerOn) {
        bgColor = "#f57c00"; // arancione quando caldaia/circolatore acceso
        stateText = getTranslation(this._hass, 'heating_active');
        iconName = this._config.icon || "mdi:fire";
        glowClass = true;
      } else {
        bgColor = "#fbc02d"; // giallo quando caldaia/circolatore spento
        stateText = getTranslation(this._hass, 'idle');
        iconName = this._config.icon || "mdi:radiator-off";
      }
    }

    // Update the ha-card element's background color and custom styles
    const card = this.shadowRoot.querySelector('ha-card');
    if (card) {
      card.style.backgroundColor = bgColor;
      if (this._config.height) card.style.height = this._config.height;
      if (this._config.width) card.style.width = this._config.width;
      if (this._config.border_radius) card.style.borderRadius = this._config.border_radius;
    }

    // Update title / name
    const nameEl = this.shadowRoot.querySelector('.name');
    if (nameEl) {
      nameEl.textContent = this._config.title || getTranslation(this._hass, 'heating');
    }

    // Update state text
    const stateEl = this.shadowRoot.querySelector('.state');
    if (stateEl) {
      stateEl.textContent = stateText;
    }

    // Update icon
    const iconEl = this.shadowRoot.querySelector('ha-icon');
    if (iconEl) {
      iconEl.setAttribute('icon', iconName);
      if (glowClass) {
        iconEl.classList.add('glow-flame');
      } else {
        iconEl.classList.remove('glow-flame');
      }
    }

    // Update subtext info
    const infoEl = this.shadowRoot.querySelector('.temp-row');
    if (infoEl) {
      if (boilerEntity && boilerState) {
        infoEl.textContent = `${getTranslation(this._hass, 'caldaia_circ')}: ${isBoilerOn ? 'ON' : 'OFF'}`;
      } else {
        infoEl.textContent = isMasterOn ? getTranslation(this._hass, 'system_active') : getTranslation(this._hass, 'system_off');
      }
    }
  }

  renderError(msg) {
    this.shadowRoot.innerHTML = `
      <ha-card style="padding: 16px; color: red; background-color: rgba(255,0,0,0.15);">
        <h3>Errore scheda Multizone Thermostat</h3>
        <p>${msg}</p>
      </ha-card>
    `;
    this._rendered = false;
  }
}

/* ==================== PRESET CARD CLASS ==================== */
class MultizoneThermostatPresetCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: 'open' });
    this.renderStructure();
  }

  set hass(hass) {
    this._hass = hass;
    this.updateCard();
  }

  setConfig(config) {
    this._config = config;
  }

  getCardSize() {
    return 2;
  }

  static getConfigElement() {
    return document.createElement("multizone-thermostat-preset-card-editor");
  }

  static getStubConfig() {
    return {
      entity: "",
      title: ""
    };
  }

  get presetEntity() {
    if (this._config && this._config.entity) {
      return this._config.entity;
    }
    return findPresetEntity(this._hass);
  }

  renderStructure() {
    this.shadowRoot.innerHTML = `
      <style>
        ha-card {
          padding: 16px;
          border-radius: 12px;
          display: flex;
          flex-direction: column;
          gap: 12px;
          background: var(--ha-card-background, var(--card-background-color, white));
        }
        .header {
          font-weight: 500;
          font-size: 16px;
          color: var(--primary-text-color);
        }
        .buttons-row {
          display: flex;
          flex-direction: row;
          justify-content: space-between;
          gap: 8px;
        }
        .preset-btn {
          flex: 1;
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          background: var(--secondary-background-color);
          color: var(--secondary-text-color);
          border-radius: 12px;
          padding: 12px 4px;
          cursor: pointer;
          transition: all 0.3s ease;
          border: 2px solid transparent;
          gap: 6px;
        }
        .preset-btn:hover {
          background: rgba(var(--rgb-primary-color), 0.1);
        }
        .preset-btn.active {
          background: rgba(var(--rgb-primary-color), 0.15);
          color: var(--primary-color);
          border-color: var(--primary-color);
        }
        .preset-btn ha-icon {
          --mdc-icon-size: 28px;
        }
        .preset-label {
          font-size: 11px;
          font-weight: 500;
          text-align: center;
          word-break: break-word;
        }
      </style>
      <ha-card>
        <div class="header" id="card-title">Preset Globale</div>
        <div class="buttons-row">
          <div class="preset-btn" data-preset="manual" id="btn-manual">
            <ha-icon icon="mdi:power"></ha-icon>
            <div class="preset-label" id="lbl-manual">Manual</div>
          </div>
          <div class="preset-btn" data-preset="eco" id="btn-eco">
            <ha-icon icon="mdi:leaf"></ha-icon>
            <div class="preset-label" id="lbl-eco">Eco</div>
          </div>
          <div class="preset-btn" data-preset="comfort" id="btn-comfort">
            <ha-icon icon="mdi:sofa"></ha-icon>
            <div class="preset-label" id="lbl-comfort">Comfort</div>
          </div>
          <div class="preset-btn" data-preset="sleep" id="btn-sleep">
            <ha-icon icon="mdi:bed"></ha-icon>
            <div class="preset-label" id="lbl-sleep">Sleep</div>
          </div>
          <div class="preset-btn" data-preset="away" id="btn-away">
            <ha-icon icon="mdi:car"></ha-icon>
            <div class="preset-label" id="lbl-away">Away</div>
          </div>
        </div>
      </ha-card>
    `;

    // Add click listeners
    const buttons = this.shadowRoot.querySelectorAll('.preset-btn');
    buttons.forEach(btn => {
      btn.addEventListener('click', (e) => {
        const preset = e.currentTarget.getAttribute('data-preset');
        this.setPreset(preset);
      });
    });
  }

  setPreset(preset) {
    if (!this._hass || !this.presetEntity) return;
    this._hass.callService('select', 'select_option', {
      entity_id: this.presetEntity,
      option: preset
    });
  }

  updateCard() {
    if (!this._hass) return;

    // Apply custom styling from config
    const card = this.shadowRoot.querySelector('ha-card');
    if (card && this._config) {
      if (this._config.height) card.style.height = this._config.height;
      if (this._config.width) card.style.width = this._config.width;
      if (this._config.border_radius) card.style.borderRadius = this._config.border_radius;
    }

    // Title
    const titleEl = this.shadowRoot.getElementById('card-title');
    titleEl.textContent = (this._config && this._config.title) || getTranslation(this._hass, 'preset_card_title');

    // Labels
    this.shadowRoot.getElementById('lbl-manual').textContent = getTranslation(this._hass, 'preset_manual');
    this.shadowRoot.getElementById('lbl-eco').textContent = getTranslation(this._hass, 'preset_eco');
    this.shadowRoot.getElementById('lbl-comfort').textContent = getTranslation(this._hass, 'preset_comfort');
    this.shadowRoot.getElementById('lbl-sleep').textContent = getTranslation(this._hass, 'preset_sleep');
    this.shadowRoot.getElementById('lbl-away').textContent = getTranslation(this._hass, 'preset_away');

    const entityId = this.presetEntity;
    if (!entityId || !this._hass.states[entityId]) {
      return; // Not found yet
    }

    const state = this._hass.states[entityId].state;

    // Update active class
    const buttons = this.shadowRoot.querySelectorAll('.preset-btn');
    buttons.forEach(btn => {
      if (btn.getAttribute('data-preset') === state) {
        btn.classList.add('active');
      } else {
        btn.classList.remove('active');
      }
    });
  }
}

/* ==================== PRESET CARD EDITOR CLASS ==================== */
class MultizoneThermostatPresetCardEditor extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: 'open' });
  }

  setConfig(config) {
    this._config = config;
    this.render();
  }

  set hass(hass) {
    this._hass = hass;
    if (!this._rendered) {
      this.render();
      this._rendered = true;
    }
  }

  configChanged(newConfig) {
    const event = new Event("config-changed", {
      bubbles: true,
      composed: true
    });
    event.detail = { config: newConfig };
    this.dispatchEvent(event);
  }

  render() {
    if (!this._config) return;
    
    // Only build DOM once, then just update values
    if (this.shadowRoot.querySelector('.editor-container')) {
        // Update existing input values
        const titleInput = this.shadowRoot.querySelector('#title-input');
        if (titleInput && titleInput.value !== (this._config.title || '')) {
            titleInput.value = this._config.title || '';
        }
        return;
    }

    if (!this._hass) return;
    const config = this._config || {};
    
    // Auto-discover preset entity if not configured
    let currentEntity = config.entity;
    if (!currentEntity) {
      currentEntity = findPresetEntity(this._hass) || '';
      if (currentEntity) {
        // Defer the config change slightly to let the editor finish rendering
        setTimeout(() => {
          this._config = { ...this._config, entity: currentEntity };
          this.configChanged(this._config);
        }, 100);
      }
    }

    if (this.shadowRoot.hasChildNodes()) {
      this.shadowRoot.innerHTML = '';
    }

    const container = document.createElement('div');
    container.className = 'card-config editor-container';

    // Title Row
    const titleRow = document.createElement('div');
    titleRow.className = 'form-row';
    const titleLabel = document.createElement('label');
    titleLabel.textContent = getTranslation(this._hass, 'edit_title');
    titleLabel.style.display = 'block';
    titleLabel.style.marginBottom = '8px';
    const titleInput = document.createElement('input');
    titleInput.id = 'title-input';
    titleInput.type = 'text';
    titleInput.value = config.title || '';
    titleInput.style.width = '100%';
    titleInput.style.padding = '8px';
    titleInput.style.boxSizing = 'border-box';
    titleInput.addEventListener('input', (e) => {
      if (!this._config) return;
      this._config = { ...this._config, title: e.target.value };
      this.configChanged(this._config);
    });
    titleRow.appendChild(titleLabel);
    titleRow.appendChild(titleInput);
    container.appendChild(titleRow);

    // Entity Row
    const entityRow = document.createElement('div');
    entityRow.className = 'form-row';
    entityRow.style.marginTop = '16px';
    const entityLabel = document.createElement('label');
    entityLabel.textContent = getTranslation(this._hass, 'edit_preset');
    const entityPicker = document.createElement('ha-entity-picker');
    entityPicker.includeDomains = ['select'];
    entityPicker.value = config.entity || '';
    entityPicker.hass = this._hass;
    entityPicker.addEventListener('value-changed', (e) => {
      if (!this._config) return;
      this._config = { ...this._config, entity: e.detail.value };
      this.configChanged(this._config);
    });
    
    entityRow.appendChild(entityLabel);
    entityRow.appendChild(entityPicker);
    container.appendChild(entityRow);

    this.shadowRoot.appendChild(container);
  }
}

// Define elements safely to avoid "already been used" errors on hot-reloads
if (!customElements.get("multizone-thermostat-button-card")) {
  customElements.define("multizone-thermostat-button-card", MultizoneThermostatButtonCard);
}
if (!customElements.get("multizone-thermostat-dial-card")) {
  customElements.define("multizone-thermostat-dial-card", MultizoneThermostatDialCard);
}
if (!customElements.get("multizone-thermostat-status-card")) {
  customElements.define("multizone-thermostat-status-card", MultizoneThermostatStatusCard);
}
if (!customElements.get("multizone-thermostat-card-editor")) {
  customElements.define("multizone-thermostat-card-editor", MultizoneThermostatCardEditor);
}
if (!customElements.get("multizone-thermostat-preset-card")) {
  customElements.define("multizone-thermostat-preset-card", MultizoneThermostatPresetCard);
}
if (!customElements.get("multizone-thermostat-preset-card-editor")) {
  customElements.define("multizone-thermostat-preset-card-editor", MultizoneThermostatPresetCardEditor);
}

/* ==================== SPACER CARD ==================== */
class MultizoneThermostatSpacer extends HTMLElement {
  setConfig(config) {}
  set hass(hass) {}
}

if (!customElements.get("multizone-thermostat-spacer")) {
  customElements.define("multizone-thermostat-spacer", MultizoneThermostatSpacer);
}

/* ==================== PLANT DIAGNOSTIC CARD ==================== */
class MultizoneThermostatPlantCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: 'open' });
    this._rendered = false;
  }

  setConfig(config) {
    this._config = config || {};
  }

  set hass(hass) {
    this._hass = hass;
    if (!this._rendered) {
      this.render();
    }
    this.updateCard();
  }

  render() {
    const style = document.createElement('style');
    style.textContent = `
      ha-card {
        background: var(--ha-card-background, var(--card-background-color, rgba(30, 41, 59, 0.7)));
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
        border: 1px solid var(--divider-color, rgba(255, 255, 255, 0.08));
        border-radius: var(--card-border-radius, 20px);
        padding: 20px;
        box-shadow: var(--ha-card-box-shadow, 0 4px 20px rgba(0, 0, 0, 0.15));
        font-family: var(--paper-font-body1_-_font-family, inherit);
        color: var(--primary-text-color, #e2e8f0);
        box-sizing: border-box;
      }
      .header-row {
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 16px;
      }
      .title-group {
        display: flex;
        align-items: center;
        gap: 12px;
      }
      .icon-wrap {
        width: 46px;
        height: 46px;
        border-radius: 14px;
        display: flex;
        align-items: center;
        justify-content: center;
        background: rgba(14, 165, 233, 0.15);
        color: #38bdf8;
      }
      .icon-wrap ha-icon {
        --mdc-icon-size: 28px;
      }
      .title-text {
        font-size: 20px;
        font-weight: 800;
        margin: 0;
        line-height: 1.2;
      }
      .subtitle-text {
        font-size: 13px;
        color: var(--secondary-text-color, #94a3b8);
        margin-top: 3px;
      }
      .status-badge {
        padding: 6px 14px;
        border-radius: 9999px;
        font-size: 13px;
        font-weight: 800;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        display: flex;
        align-items: center;
        gap: 8px;
      }
      .status-optimal {
        background: rgba(16, 185, 129, 0.15);
        color: #34d399;
        border: 1px solid rgba(16, 185, 129, 0.3);
      }
      .status-warning {
        background: rgba(245, 158, 11, 0.15);
        color: #fbbf24;
        border: 1px solid rgba(245, 158, 11, 0.3);
      }
      .status-critical {
        background: rgba(239, 68, 68, 0.15);
        color: #f87171;
        border: 1px solid rgba(239, 68, 68, 0.3);
      }
      .status-dot {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background: currentColor;
      }
      .kpi-grid {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 14px;
        margin-bottom: 14px;
      }
      @media (max-width: 480px) {
        .kpi-grid { grid-template-columns: 1fr; }
      }
      .kpi-card {
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(255, 255, 255, 0.06);
        border-radius: 16px;
        padding: 16px;
      }
      .kpi-label {
        font-size: 13px;
        font-weight: 600;
        color: var(--secondary-text-color, #94a3b8);
        display: block;
        margin-bottom: 6px;
      }
      .kpi-value-row {
        display: flex;
        align-items: baseline;
        gap: 6px;
      }
      .kpi-val {
        font-size: 30px;
        font-weight: 900;
        line-height: 1;
      }
      .kpi-unit {
        font-size: 13px;
        font-weight: 600;
        color: var(--secondary-text-color, #94a3b8);
      }
      .kpi-sub {
        font-size: 12px;
        margin-top: 8px;
        font-weight: 600;
      }
      .alert-box {
        padding: 14px 16px;
        border-radius: 14px;
        font-size: 13px;
        line-height: 1.5;
        display: flex;
        flex-direction: column;
        gap: 6px;
        background: rgba(255, 255, 255, 0.02);
        border: 1px solid rgba(255, 255, 255, 0.06);
      }
      .alert-box.alert-ok {
        background: rgba(16, 185, 129, 0.08);
        border-color: rgba(16, 185, 129, 0.2);
        color: #a7f3d0;
      }
      .alert-box.alert-err {
        background: rgba(239, 68, 68, 0.12);
        border-color: rgba(239, 68, 68, 0.35);
        color: #fca5a5;
      }
      .alert-title {
        font-weight: 700;
        font-size: 14px;
        display: flex;
        align-items: center;
        gap: 8px;
      }
    `;

    const card = document.createElement('ha-card');
    card.innerHTML = `
      <div class="header-row">
        <div class="title-group">
          <div class="icon-wrap">
            <ha-icon icon="mdi:shield-check"></ha-icon>
          </div>
          <div>
            <div class="title-text">Salute Impianto & Caldaia</div>
            <div class="subtitle-text">Supervisione idraulica e usura relè</div>
          </div>
        </div>
        <div class="status-badge status-optimal" id="health-badge">
          <span class="status-dot"></span>
          <span id="health-text">OTTIMALE</span>
        </div>
      </div>

      <div class="kpi-grid">
        <div class="kpi-card">
          <span class="kpi-label">Frequenza Accensioni (Short-Cycle)</span>
          <div class="kpi-value-row">
            <span class="kpi-val" id="cycles-val">--</span>
            <span class="kpi-unit">cicli/h</span>
          </div>
          <div class="kpi-sub" id="cycles-sub" style="color: #34d399;">Usura Bassa</div>
        </div>

        <div class="kpi-card">
          <span class="kpi-label">Funzionamento Ultime 24h</span>
          <div class="kpi-value-row">
            <span class="kpi-val" id="runtime-val" style="color: #60a5fa;">--</span>
            <span class="kpi-unit">ore</span>
          </div>
          <div class="kpi-sub" style="color: #94a3b8;">Attività cumulativa relè/mandata</div>
        </div>
      </div>

      <div class="alert-box alert-ok" id="alert-box">
        <div class="alert-title" id="alert-title-wrap">
          <ha-icon icon="mdi:check-circle-outline" style="--mdc-icon-size: 18px; color: #34d399;"></ha-icon>
          <span>Tutti i circuiti operativi</span>
        </div>
        <div id="alert-desc">Nessun blocco valvola, trafilamento o short-cycling rilevato.</div>
      </div>
    `;

    this.shadowRoot.appendChild(style);
    this.shadowRoot.appendChild(card);
    this._rendered = true;
  }

  updateCard() {
    if (!this._hass || !this._rendered) return;

    let healthEntity = this._config.health_entity;
    let cyclesEntity = this._config.cycles_entity;
    let runtimeEntity = this._config.runtime_entity;
    let anomalyEntity = this._config.anomaly_entity;

    if (!healthEntity) {
      healthEntity = Object.keys(this._hass.states).find(k => k.startsWith('sensor.') && k.includes('stato_salute_impianto'));
    }
    if (!cyclesEntity) {
      cyclesEntity = Object.keys(this._hass.states).find(k => k.startsWith('sensor.') && k.includes('frequenza_accensioni_caldaia'));
    }
    if (!runtimeEntity) {
      runtimeEntity = Object.keys(this._hass.states).find(k => k.startsWith('sensor.') && k.includes('ore_funzionamento_caldaia_24h'));
    }
    if (!anomalyEntity) {
      anomalyEntity = Object.keys(this._hass.states).find(k => k.startsWith('binary_sensor.') && k.includes('plant_anomaly'));
    }

    const healthState = healthEntity ? this._hass.states[healthEntity] : null;
    const cyclesState = cyclesEntity ? this._hass.states[cyclesEntity] : null;
    const runtimeState = runtimeEntity ? this._hass.states[runtimeEntity] : null;
    const anomalyState = anomalyEntity ? this._hass.states[anomalyEntity] : null;

    const healthBadge = this.shadowRoot.getElementById('health-badge');
    const healthText = this.shadowRoot.getElementById('health-text');
    const cyclesVal = this.shadowRoot.getElementById('cycles-val');
    const cyclesSub = this.shadowRoot.getElementById('cycles-sub');
    const runtimeVal = this.shadowRoot.getElementById('runtime-val');
    const alertBox = this.shadowRoot.getElementById('alert-box');
    const alertDesc = this.shadowRoot.getElementById('alert-desc');

    const statusVal = healthState ? healthState.state : "Ottimale";
    if (healthBadge && healthText) {
      healthText.innerText = statusVal.toUpperCase();
      if (statusVal === "Critico") {
        healthBadge.className = "status-badge status-critical";
      } else if (statusVal === "Attenzione") {
        healthBadge.className = "status-badge status-warning";
      } else {
        healthBadge.className = "status-badge status-optimal";
      }
    }

    if (cyclesVal && cyclesState) {
      const c = parseFloat(cyclesState.state) || 0;
      cyclesVal.innerText = c.toFixed(1);
      if (cyclesSub) {
        if (c <= 3.5) {
          cyclesSub.innerText = "Usura Bassa (< 3.5 c/h)";
          cyclesSub.style.color = "#34d399";
        } else if (c <= 5.0) {
          cyclesSub.innerText = "Usura Moderata (3.5 - 5 c/h)";
          cyclesSub.style.color = "#fbbf24";
        } else {
          cyclesSub.innerText = "⚠️ Short-Cycling Elevato (> 5 c/h)";
          cyclesSub.style.color = "#f87171";
        }
      }
    }

    if (runtimeVal && runtimeState) {
      const r = parseFloat(runtimeState.state) || 0;
      runtimeVal.innerText = r.toFixed(1);
    }

    if (alertBox && alertDesc) {
      const hasAnomaly = anomalyState ? anomalyState.state === "on" : (statusVal !== "Ottimale");
      if (hasAnomaly && healthState && healthState.attributes && healthState.attributes.anomalies && healthState.attributes.anomalies.length > 0) {
        alertBox.className = "alert-box alert-err";
        const items = healthState.attributes.anomalies.map(a => `• <b>${a.zone}</b>: ${a.description}`).join('<br>');
        alertDesc.innerHTML = items;
      } else if (statusVal === "Attenzione") {
        alertBox.className = "alert-box alert-err";
        alertDesc.innerText = "Attenzione: frequenza di accensioni caldaia elevata o parametri da ottimizzare.";
      } else {
        alertBox.className = "alert-box alert-ok";
        alertDesc.innerText = "Nessun blocco valvola, trafilamento o short-cycling rilevato.";
      }
    }
  }
}

if (!customElements.get("multizone-thermostat-plant-card")) {
  customElements.define("multizone-thermostat-plant-card", MultizoneThermostatPlantCard);
}

/* ==================== ZONE ENERGY CARD ==================== */
class MultizoneThermostatZoneEnergyCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: 'open' });
    this._rendered = false;
  }

  setConfig(config) {
    if (!config.entity) {
      throw new Error("Devi specificare un'entità climate");
    }
    this._config = config;
  }

  set hass(hass) {
    this._hass = hass;
    if (!this._rendered) {
      this.render();
    }
    this.updateCard();
  }

  render() {
    const style = document.createElement('style');
    style.textContent = `
      ha-card {
        background: var(--ha-card-background, var(--card-background-color, rgba(30, 41, 59, 0.7)));
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
        border: 1px solid var(--divider-color, rgba(255, 255, 255, 0.08));
        border-radius: var(--card-border-radius, 20px);
        padding: 18px;
        box-shadow: var(--ha-card-box-shadow, 0 4px 20px rgba(0, 0, 0, 0.15));
        font-family: var(--paper-font-body1_-_font-family, inherit);
        color: var(--primary-text-color, #e2e8f0);
        box-sizing: border-box;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
      }
      .top-row {
        display: flex;
        align-items: flex-start;
        justify-content: space-between;
        margin-bottom: 12px;
      }
      .zone-name {
        font-size: 19px;
        font-weight: 800;
        margin: 0;
        display: flex;
        align-items: center;
        gap: 8px;
      }
      .zone-mode-badge {
        font-size: 10px;
        font-weight: 800;
        padding: 3px 8px;
        border-radius: 6px;
        text-transform: uppercase;
        background: rgba(59, 130, 246, 0.2);
        color: #60a5fa;
      }
      .zone-sub {
        font-size: 13px;
        font-weight: 500;
        color: var(--secondary-text-color, #94a3b8);
        margin-top: 3px;
      }
      .energy-badge {
        padding: 6px 12px;
        border-radius: 10px;
        font-weight: 900;
        font-size: 17px;
        text-align: center;
        box-shadow: 0 2px 8px rgba(0,0,0,0.2);
        min-width: 44px;
        background: #10b981;
        color: white;
      }
      .ribbon-scale {
        display: flex;
        height: 6px;
        border-radius: 3px;
        overflow: hidden;
        margin-bottom: 14px;
        opacity: 0.85;
        gap: 2px;
      }
      .ribbon-step {
        flex: 1;
        height: 100%;
        transition: transform 0.2s ease;
      }
      .ribbon-step.active {
        transform: scaleY(1.8);
        box-shadow: 0 0 6px white;
        z-index: 2;
      }
      .step-A4 { background-color: #00873d; }
      .step-A  { background-color: #139f37; }
      .step-B  { background-color: #55b726; }
      .step-C  { background-color: #96c818; }
      .step-D  { background-color: #e0d100; }
      .step-E  { background-color: #f39200; }
      .step-F  { background-color: #e64213; }
      .step-G  { background-color: #cb0019; }

      .stats-grid {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 12px;
        margin-bottom: 14px;
      }
      .stat-box {
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(255, 255, 255, 0.05);
        border-radius: 14px;
        padding: 12px 14px;
      }
      .stat-label {
        font-size: 12px;
        font-weight: 600;
        color: var(--secondary-text-color, #94a3b8);
        display: block;
        margin-bottom: 4px;
      }
      .stat-val {
        font-size: 20px;
        font-weight: 800;
        line-height: 1.2;
      }
      .stat-unit {
        font-size: 12px;
        color: var(--secondary-text-color, #94a3b8);
        font-weight: 600;
        margin-left: 2px;
      }
      .stat-eval {
        font-size: 12px;
        margin-top: 4px;
        font-weight: 600;
        display: block;
      }
      .bottom-row {
        padding-top: 12px;
        border-top: 1px solid rgba(255, 255, 255, 0.06);
        display: flex;
        align-items: center;
        justify-content: space-between;
        font-size: 13px;
      }
      .valve-status {
        display: flex;
        align-items: center;
        gap: 8px;
        font-weight: 600;
      }
      .pulse-dot {
        width: 8px;
        height: 8px;
        border-radius: 50%;
      }
      .pulse-green { background: #10b981; }
      .pulse-red { background: #ef4444; animation: blink 1s infinite; }
      @keyframes blink { 0%, 100% { opacity: 1; } 50% { opacity: 0.3; } }
    `;

    const card = document.createElement('ha-card');
    card.innerHTML = `
      <div class="top-row">
        <div>
          <div class="zone-name">
            <span id="zone-title">Stanza</span>
            <span class="zone-mode-badge" id="zone-mode-badge">PRIMARIA</span>
          </div>
          <div class="zone-sub" id="temp-sub">-- °C</div>
        </div>
        <div class="energy-badge" id="energy-badge">--</div>
      </div>

      <div class="ribbon-scale" id="ribbon-scale">
        <div class="ribbon-step step-A4" id="step-A4"></div>
        <div class="ribbon-step step-A" id="step-A"></div>
        <div class="ribbon-step step-B" id="step-B"></div>
        <div class="ribbon-step step-C" id="step-C"></div>
        <div class="ribbon-step step-D" id="step-D"></div>
        <div class="ribbon-step step-E" id="step-E"></div>
        <div class="ribbon-step step-F" id="step-F"></div>
        <div class="ribbon-step step-G" id="step-G"></div>
      </div>

      <div class="stats-grid">
        <div class="stat-box">
          <span class="stat-label">Ritenzione (-1°C)</span>
          <div>
            <span class="stat-val" id="retention-val">--</span>
            <span class="stat-unit">ore</span>
          </div>
          <span class="stat-eval" id="retention-eval" style="color: #38bdf8;">--</span>
        </div>

        <div class="stat-box">
          <span class="stat-label">Resa Termoarredo</span>
          <div>
            <span class="stat-val" id="sizing-val">--</span>
          </div>
          <span class="stat-eval" id="sizing-eval" style="color: #34d399;">--</span>
        </div>
      </div>

      <div class="bottom-row">
        <span style="color: var(--secondary-text-color, #94a3b8);">Stato Valvola:</span>
        <div class="valve-status" id="valve-status">
          <span class="pulse-dot pulse-green" id="valve-dot"></span>
          <span id="valve-text">Nessuna anomalia</span>
        </div>
      </div>
    `;

    this.shadowRoot.appendChild(style);
    this.shadowRoot.appendChild(card);
    this._rendered = true;
  }

  updateCard() {
    if (!this._hass || !this._rendered) return;

    const climateId = this._config.entity;
    const climateState = this._hass.states[climateId];
    if (!climateState) return;

    let title = this._config.title || climateState.attributes.friendly_name || climateId;
    title = title.replace(/^Virtual Thermostats VT /i, '').replace(/^Heating Zones(?: Zone)? /i, '');
    let slug = climateId.replace("climate.multizone_thermostat_", "").replace("climate.", "");

    const energyEntity = Object.keys(this._hass.states).find(k => k.startsWith('sensor.') && k.includes('classe_energetica') && k.includes(slug));
    const retentionEntity = Object.keys(this._hass.states).find(k => k.startsWith('sensor.') && k.includes('tempo_ritenzione_termica') && k.includes(slug));
    const sizingEntity = Object.keys(this._hass.states).find(k => k.startsWith('sensor.') && k.includes('dimensionamento_radiatore') && k.includes(slug));
    const anomalyEntity = Object.keys(this._hass.states).find(k => k.startsWith('binary_sensor.') && k.includes('anomaly') && k.includes(slug));

    const titleEl = this.shadowRoot.getElementById('zone-title');
    const tempSubEl = this.shadowRoot.getElementById('temp-sub');
    const badgeEl = this.shadowRoot.getElementById('energy-badge');
    const retentionVal = this.shadowRoot.getElementById('retention-val');
    const retentionEval = this.shadowRoot.getElementById('retention-eval');
    const sizingVal = this.shadowRoot.getElementById('sizing-val');
    const sizingEval = this.shadowRoot.getElementById('sizing-eval');
    const valveDot = this.shadowRoot.getElementById('valve-dot');
    const valveText = this.shadowRoot.getElementById('valve-text');
    // Determine zone mode (primary, secondary, bypass)
    let zoneMode = "primary";
    const selectObj = Object.values(this._hass.states).find(s => 
      s.entity_id.startsWith('select.') && (
        (s.attributes && s.attributes.climate_entity === climateId) ||
        (s.entity_id.includes(slug) && (s.entity_id.includes('mode') || s.entity_id.includes('zone')))
      )
    );
    if (selectObj && selectObj.state) {
      zoneMode = selectObj.state;
    } else if (climateState.attributes && climateState.attributes.zone_mode) {
      zoneMode = climateState.attributes.zone_mode;
    }

    if (titleEl) titleEl.innerText = title;

    if (tempSubEl) {
      const cur = climateState.attributes.current_temperature;
      const tgt = climateState.attributes.temperature;
      if (zoneMode === "bypass") {
        tempSubEl.innerText = `${cur !== undefined ? cur : '--'}°C / (Bypassata)`;
      } else {
        tempSubEl.innerText = `${cur !== undefined ? cur : '--'}°C / target ${tgt !== undefined ? tgt : '--'}°C`;
      }
    }

    if (modeBadge) {
      if (zoneMode === "bypass") {
        modeBadge.innerText = "BYPASSATA";
        modeBadge.style.background = "rgba(100, 116, 139, 0.25)";
        modeBadge.style.color = "#94a3b8";
        modeBadge.style.border = "1px solid rgba(148, 163, 184, 0.3)";
      } else if (zoneMode === "secondary") {
        modeBadge.innerText = "SECONDARIA";
        modeBadge.style.background = "rgba(168, 85, 247, 0.2)";
        modeBadge.style.color = "#c084fc";
        modeBadge.style.border = "1px solid rgba(168, 85, 247, 0.3)";
      } else {
        modeBadge.innerText = "PRIMARIA";
        modeBadge.style.background = "rgba(59, 130, 246, 0.2)";
        modeBadge.style.color = "#60a5fa";
        modeBadge.style.border = "1px solid rgba(59, 130, 246, 0.3)";
      }
    }

    const eState = energyEntity ? this._hass.states[energyEntity] : null;
    const energyClass = eState ? eState.state : "--";
    const colors = {
      'A4': '#00873d', 'A': '#139f37', 'B': '#55b726', 'C': '#96c818',
      'D': '#e0d100', 'E': '#f39200', 'F': '#e64213', 'G': '#cb0019'
    };

    if (badgeEl) {
      badgeEl.innerText = energyClass;
      if (colors[energyClass]) {
        badgeEl.style.backgroundColor = colors[energyClass];
        badgeEl.style.color = (['C', 'D'].includes(energyClass)) ? '#111' : '#fff';
      } else {
        badgeEl.style.backgroundColor = '#64748b';
        badgeEl.style.color = '#fff';
      }
    }

    ['A4', 'A', 'B', 'C', 'D', 'E', 'F', 'G'].forEach(cls => {
      const stepEl = this.shadowRoot.getElementById('step-' + cls);
      if (stepEl) {
        if (cls === energyClass) {
          stepEl.classList.add('active');
        } else {
          stepEl.classList.remove('active');
        }
      }
    });

    const rState = retentionEntity ? this._hass.states[retentionEntity] : null;
    if (retentionVal && rState) {
      const r = parseFloat(rState.state);
      retentionVal.innerText = isNaN(r) ? "--" : r.toFixed(1);
      if (retentionEval) {
        if (isNaN(r)) retentionEval.innerText = "In apprendimento...";
        else if (r >= 6.0) retentionEval.innerText = "Ottimo isolamento";
        else if (r >= 3.5) retentionEval.innerText = "Isolamento medio";
        else retentionEval.innerText = "Dispersione rapida";
      }
    }

    const sState = sizingEntity ? this._hass.states[sizingEntity] : null;
    if (sizingVal && sState) {
      sizingVal.innerText = sState.state;
      if (sizingEval) {
        if (sState.state === "Ottimale") {
          sizingEval.innerText = "Rapporto potenza/perdite OK";
          sizingEval.style.color = "#34d399";
        } else if (sState.state === "Sottodimensionato") {
          sizingEval.innerText = "Richiede tempo per salire";
          sizingEval.style.color = "#f87171";
        } else if (sState.state === "Sovradimensionato") {
          sizingEval.innerText = "Potenza elevata";
          sizingEval.style.color = "#fbbf24";
        } else {
          sizingEval.innerText = "In attesa dati termici";
          sizingEval.style.color = "#94a3b8";
        }
      }
    }

    const aState = anomalyEntity ? this._hass.states[anomalyEntity] : null;
    const passiveHeatSwitch = Object.keys(this._hass.states).find(k => 
      k.startsWith('switch.') && k.includes('passive_heat') && k.includes(slug)
    );
    const swState = passiveHeatSwitch ? this._hass.states[passiveHeatSwitch] : null;
    const allowPassive = (swState && swState.state === 'on') || (climateState.attributes && climateState.attributes.allow_passive_heat);

    const valveStatusEl = this.shadowRoot.getElementById('valve-status');
    if (valveStatusEl) {
      if (!this._valveListenerAttached) {
        this._valveListenerAttached = true;
        valveStatusEl.style.cursor = 'pointer';
        valveStatusEl.addEventListener('click', (e) => {
          e.stopPropagation();
          const sw = Object.keys(this._hass.states).find(k => 
            k.startsWith('switch.') && k.includes('passive_heat') && k.includes(slug)
          );
          if (sw) {
            this._hass.callService('switch', 'toggle', { entity_id: sw });
          }
        });
      }
      valveStatusEl.title = allowPassive 
        ? "Apporto Passivo ATTIVO (Clicca per disattivare)" 
        : "Clicca per attivare Apporto Passivo (Fancoil senza valvola / Soppalco)";
    }

    if (valveDot && valveText) {
      const hasAnomaly = aState && aState.state === "on";
      if (hasAnomaly) {
        valveDot.className = "pulse-dot pulse-red";
        valveText.innerText = (aState.attributes && aState.attributes.details) || "Anomalia Rilevata";
        valveText.style.color = "#f87171";
      } else if (zoneMode === "bypass") {
        valveDot.className = "pulse-dot pulse-green";
        valveText.innerText = allowPassive ? "Valvola Chiusa (Apporto passivo attivo)" : "Valvola Chiusa (Bypass)";
        valveText.style.color = "#94a3b8";
      } else {
        valveDot.className = "pulse-dot pulse-green";
        valveText.innerText = allowPassive ? "Nessuna anomalia (Apporto passivo attivo)" : "Nessuna anomalia";
        valveText.style.color = "#34d399";
      }
    }
  }
}

if (!customElements.get("multizone-thermostat-zone-energy-card")) {
  customElements.define("multizone-thermostat-zone-energy-card", MultizoneThermostatZoneEnergyCard);
}

/* ==================== DASHBOARD STRATEGY ==================== */
class MultizoneThermostatDashboardStrategy extends HTMLElement {
  static async generateDashboard(info) {
    const view = await this.generateView(info);
    const diagView = await this.generateDiagnosticView(info);
    return {
      title: "Multizone Thermostat",
      views: [
        {
          title: "Termostati",
          path: "home",
          icon: "mdi:radiator",
          panel: true,
          cards: view.cards,
        },
        {
          title: "Diagnostica & Efficienza",
          path: "diagnostica",
          icon: "mdi:chart-box-outline",
          panel: true,
          cards: diagView.cards,
        }
      ]
    };
  }

  static async generateDiagnosticView(info) {
    const hass = info.hass;
    const strategyConfig = info.config?.strategy || info.strategy || info.config || {};
    
    // Find all zones
    const zones = [];
    for (const entityId of Object.keys(hass.states)) {
      if (entityId.startsWith("select.") || entityId.startsWith("switch.")) {
        const stateObj = hass.states[entityId];
        const climateId = stateObj.attributes ? stateObj.attributes.climate_entity : null;
        if (climateId) {
          const climateState = hass.states[climateId];
          if (climateState && !zones.some(z => z.climate === climateId)) {
            let title = climateState.attributes.friendly_name || climateId;
            title = title.replace(/^Virtual Thermostats VT /i, '').replace(/^Heating Zones(?: Zone)? /i, '');
            zones.push({
              climate: climateId,
              title: title,
            });
          }
        }
      }
    }
    zones.sort((a, b) => a.title.localeCompare(b.title));

    let columns = parseInt(strategyConfig.columns, 10);
    if (isNaN(columns) || columns < 1) {
      columns = 3;
    }

    const stackCards = [
      {
        type: "custom:multizone-thermostat-plant-card",
        border_radius: "20px",
      }
    ];

    for (let i = 0; i < zones.length; i += columns) {
      const chunk = zones.slice(i, i + columns);
      const rowCards = chunk.map(zone => ({
        type: "custom:multizone-thermostat-zone-energy-card",
        entity: zone.climate,
        title: zone.title,
        border_radius: "20px",
      }));
      
      while (rowCards.length < columns && columns <= 3) {
        rowCards.push({
          type: "custom:multizone-thermostat-spacer"
        });
      }

      stackCards.push({
        type: "horizontal-stack",
        cards: rowCards
      });
    }

    return {
      cards: [
        {
          type: "vertical-stack",
          cards: stackCards
        }
      ]
    };
  }

  static async generateView(info) {
    const hass = info.hass;
    // In view strategies, config is usually in info.config.strategy or info.strategy
    const strategyConfig = info.config?.strategy || info.strategy || info.config || {};
    
    // Find master switch
    const masterEntity = findMasterEntity(hass);
    // Find preset entity
    const presetEntity = findPresetEntity(hass);
    
    // Find all zones (by checking for climate_entity attribute)
    const zones = [];
    for (const entityId of Object.keys(hass.states)) {
      if (entityId.startsWith("select.") || entityId.startsWith("switch.")) {
        const stateObj = hass.states[entityId];
        const climateId = stateObj.attributes ? stateObj.attributes.climate_entity : null;
        if (climateId) {
          const climateState = hass.states[climateId];
          if (climateState) {
            let title = climateState.attributes.friendly_name || climateId;
            title = title.replace(/^Virtual Thermostats VT /i, '').replace(/^Heating Zones(?: Zone)? /i, '');
            zones.push({
              climate: climateId,
              switch: entityId,
              title: title,
            });
          }
        }
      }
    }
    
    // Sort zones by title
    zones.sort((a, b) => a.title.localeCompare(b.title));
    
    // Build zone rows to get 'columns' config first
    let columns = parseInt(strategyConfig.columns, 10);
    if (isNaN(columns) || columns < 1) {
      columns = 3;
    }

    // Build top row
    const topRowCards = [];
    if (presetEntity) {
      topRowCards.push({
        type: "custom:multizone-thermostat-preset-card",
        entity: presetEntity,
        title: "",
        border_radius: "20px",
      });
    }
    
    topRowCards.push({
      type: "custom:multizone-thermostat-status-card",
      border_radius: "20px",
    });

    // Fill the rest of the top row with spacers so it's always exactly 3 blocks wide
    while (topRowCards.length < 3) {
      topRowCards.push({
        type: "custom:multizone-thermostat-spacer"
      });
    }

    const stackCards = [
      {
        type: "horizontal-stack",
        cards: topRowCards
      }
    ];

    for (let i = 0; i < zones.length; i += columns) {
      const chunk = zones.slice(i, i + columns);
      const rowCards = chunk.map(zone => ({
        type: "custom:multizone-thermostat-dial-card",
        entity: zone.climate,
        switch: zone.switch,
        title: zone.title,
        min_height: "300px",
        max_height: "400px",
        padding: "1px",
        border_radius: "20px",
      }));
      
      stackCards.push({
        type: "horizontal-stack",
        cards: rowCards
      });
    }

    return {
      cards: [
        {
          type: "vertical-stack",
          cards: stackCards
        }
      ]
    };
  }
}

// Register Strategy
window.customStrategies = window.customStrategies || [];
window.customStrategies.push({
  type: "multizone-thermostat-dashboard",
  name: "Multizone Thermostat Dashboard",
  description: "Auto-generated dashboard for your heating system."
});
window.customStrategies.push({
  type: "multizone-thermostat-diagnostics",
  name: "Multizone Thermostat Diagnostics",
  description: "Auto-generated diagnostic and energy efficiency view for your heating zones."
});

class MultizoneThermostatViewStrategy extends MultizoneThermostatDashboardStrategy {}
class MultizoneThermostatDiagnosticViewStrategy extends HTMLElement {
  static async generateView(info) {
    return MultizoneThermostatDashboardStrategy.generateDiagnosticView(info);
  }
}

if (!customElements.get("ll-strategy-dashboard-multizone-thermostat-dashboard")) {
  customElements.define("ll-strategy-dashboard-multizone-thermostat-dashboard", MultizoneThermostatDashboardStrategy);
}
if (!customElements.get("ll-strategy-view-multizone-thermostat-dashboard")) {
  customElements.define("ll-strategy-view-multizone-thermostat-dashboard", MultizoneThermostatViewStrategy);
}
if (!customElements.get("ll-strategy-view-multizone-thermostat-diagnostics")) {
  customElements.define("ll-strategy-view-multizone-thermostat-diagnostics", MultizoneThermostatDiagnosticViewStrategy);
}

