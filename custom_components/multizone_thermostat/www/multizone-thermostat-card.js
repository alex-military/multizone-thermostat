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
    edit_preset: "Entità Preset (Opzionale)"
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
  const climateName = climateId.split('.')[1];
  if (climateName) {
    for (const entityId of Object.keys(hass.states)) {
      if (entityId.startsWith("select.") && entityId.includes("zone_mode") && entityId.includes(climateName)) {
        return entityId;
      }
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
      if (opts.includes('manual') && opts.includes('eco') && opts.includes('comfort')) {
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
      const curStr = currentTemp !== undefined ? `${currentTemp}°C` : '--°C';
      tempCurrentEl.innerHTML = `<span class="temp-current-val">${curStr}</span>`;
    }
    this.shadowRoot.querySelector('.temp-target-val').textContent = targetTemp !== undefined ? `${targetTemp}°C` : '--°C';
    
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
                <span class="temp-target-val">--°C</span>
              </div>
              <div class="temp-current"><span class="temp-current-val">--°C</span></div>
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

  changeHvacMode(mode) {
    const climateEntity = this._config.entity;
    this._hass.callService("climate", "set_hvac_mode", {
      entity_id: climateEntity,
      hvac_mode: mode
    });
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
      displayTitle = displayTitle.replace(/^Virtual Thermostats VT /i, '');
    }

    const titleEl = this.shadowRoot.querySelector('.title');
    if (titleEl) {
      titleEl.textContent = displayTitle;
    }

    // Use temporary switch state if toggled locally to avoid flickering
    const actualSwitchState = this._tempSwitchState !== undefined 
      ? this._tempSwitchState 
      : (switchState ? switchState.state : "primary");

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
      const hvacMode = climateState.state;
      const hvacAction = climateState.attributes.hvac_action;
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
    switchPicker.includeDomains = ['switch'];
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
    const masterEntity = findMasterEntity(this._hass);
    if (!masterEntity) return;

    const domain = masterEntity.split('.')[0];
    this._hass.callService(domain, "toggle", {
      entity_id: masterEntity
    });
  }

  updateCard() {
    if (!this._hass || !this._rendered) return;

    const masterEntity = findMasterEntity(this._hass);
    if (!masterEntity) {
      const stateEl = this.shadowRoot.querySelector('.state');
      if (stateEl) stateEl.textContent = getTranslation(this._hass, 'master_not_found');
      const nameEl = this.shadowRoot.querySelector('.name');
      if (nameEl) nameEl.textContent = getTranslation(this._hass, 'master_title');
      const card = this.shadowRoot.querySelector('ha-card');
      if (card) card.style.backgroundColor = "#7f8c8d";
      return;
    }

    const masterState = this._hass.states[masterEntity];
    if (!masterState) return;

    const boilerEntity = masterState.attributes ? masterState.attributes.boiler_switch : null;
    const boilerState = boilerEntity ? this._hass.states[boilerEntity] : null;

    const isMasterOn = masterState.state === "on";
    const isBoilerOn = boilerState ? boilerState.state === "on" : false;

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
    container.className = 'card-config';

    // Title Row
    const titleRow = document.createElement('div');
    titleRow.className = 'form-row';
    const titleLabel = document.createElement('label');
    titleLabel.textContent = getTranslation(this._hass, 'edit_title');
    titleLabel.style.display = 'block';
    titleLabel.style.marginBottom = '8px';
    const titleInput = document.createElement('input');
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

/* ==================== DASHBOARD STRATEGY ==================== */
class MultizoneThermostatDashboardStrategy extends HTMLElement {
  static async generateDashboard(info) {
    const view = await this.generateView(info);
    return {
      title: "Multizone Thermostat",
      views: [
        {
          title: "Home",
          path: "home",
          panel: true,
          cards: view.cards,
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
      if (entityId.startsWith("select.")) {
        const stateObj = hass.states[entityId];
        const climateId = stateObj.attributes ? stateObj.attributes.climate_entity : null;
        if (climateId) {
          const climateState = hass.states[climateId];
          if (climateState) {
            let title = climateState.attributes.friendly_name || climateId;
            title = title.replace(/^Virtual Thermostats VT /i, '');
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

class MultizoneThermostatViewStrategy extends MultizoneThermostatDashboardStrategy {}

if (!customElements.get("ll-strategy-dashboard-multizone-thermostat-dashboard")) {
  customElements.define("ll-strategy-dashboard-multizone-thermostat-dashboard", MultizoneThermostatDashboardStrategy);
}
if (!customElements.get("ll-strategy-view-multizone-thermostat-dashboard")) {
  customElements.define("ll-strategy-view-multizone-thermostat-dashboard", MultizoneThermostatViewStrategy);
}
