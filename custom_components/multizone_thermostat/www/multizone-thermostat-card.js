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
    master_title: "Riscaldamento Centrale",
    thermostat: "Termostato",
    edit_title: "Titolo Personalizzato (Opzionale)",
    edit_climate: "Termostato (Climate Entity)",
    edit_switch: "Switch di Zona (Abilita/Escludi)"
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
    master_title: "Central Heating",
    thermostat: "Thermostat",
    edit_title: "Custom Title (Optional)",
    edit_climate: "Thermostat (Climate Entity)",
    edit_switch: "Zone Switch (Enable/Exclude)"
  }
};

function getTranslation(hass, key) {
  const lang = hass && hass.language ? hass.language.split('-')[0] : 'en';
  const translations = TRANSLATIONS[lang] || TRANSLATIONS['en'];
  return translations[key] || TRANSLATIONS['en'][key] || key;
}

// Helper function to auto-discover the bypass switch for a climate entity
function autoDiscoverSwitch(hass, climateEntity) {
  if (!hass || !climateEntity) return null;
  
  // Look for a switch entity that has this climate_entity attribute
  const switchEntity = Object.keys(hass.states).find(key => {
    if (!key.startsWith('switch.')) return false;
    const state = hass.states[key];
    return state.attributes && state.attributes.climate_entity === climateEntity;
  });
  
  return switchEntity || null;
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
    const switchEntity = this._config.switch;

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
      : (switchState ? switchState.state : "on");
    const isZoneEnabled = actualSwitchState === "on";

    const title = this._config.title || climateState.attributes.friendly_name || getTranslation(this._hass, 'thermostat');

    // Update title
    this.shadowRoot.querySelector('.title').textContent = title;

    // Update switch toggle checked state and label
    const toggle = this.shadowRoot.querySelector('#zone-toggle');
    const toggleLabel = this.shadowRoot.querySelector('#zone-toggle-label');
    if (toggleLabel) {
      toggleLabel.textContent = getTranslation(this._hass, 'enabled');
    }
    if (switchEntity) {
      toggle.style.display = 'block';
      if (toggleLabel) toggleLabel.style.display = 'block';
      toggle.checked = isZoneEnabled;
    } else {
      toggle.style.display = 'none';
      if (toggleLabel) toggleLabel.style.display = 'none';
    }

    // Apply active/disabled styling
    const controlsArea = this.shadowRoot.querySelector('.thermostat-body');
    const disabledOverlay = this.shadowRoot.querySelector('.disabled-msg');
    const disabledMsgBox = this.shadowRoot.querySelector('.disabled-msg-box');
    if (disabledMsgBox) {
      disabledMsgBox.innerHTML = `<ha-icon icon="mdi:alert-circle-outline" style="margin-right: 6px;"></ha-icon>${getTranslation(this._hass, 'bypass_msg')}`;
    }
    const wrapper = this.shadowRoot.querySelector('#wrapper');
    if (isZoneEnabled) {
      controlsArea.classList.remove('disabled');
      disabledOverlay.style.display = 'none';
      wrapper.classList.remove('disabled');
    } else {
      controlsArea.classList.add('disabled');
      disabledOverlay.style.display = 'block';
      wrapper.classList.add('disabled');
    }

    // Update temperatures
    const tempCurrentEl = this.shadowRoot.querySelector('.temp-current');
    if (tempCurrentEl) {
      const curStr = currentTemp !== undefined ? `${currentTemp}°C` : '--°C';
      tempCurrentEl.innerHTML = `${getTranslation(this._hass, 'temp_detected')}: <span class="temp-current-val">${curStr}</span>`;
    }
    this.shadowRoot.querySelector('.temp-target-val').textContent = targetTemp !== undefined ? `${targetTemp}°C` : '--°C';

    // Update status badge
    const badge = this.shadowRoot.querySelector('.status-badge');
    badge.className = 'status-badge';
    if (!isZoneEnabled) {
      badge.classList.add('disabled');
      badge.innerHTML = `<ha-icon icon="mdi:close-circle-outline" style="margin-right: 4px; --mdc-icon-size: 16px;"></ha-icon>${getTranslation(this._hass, 'excluded')}`;
    } else if (hvacMode === 'off') {
      badge.classList.add('off');
      badge.innerHTML = `<ha-icon icon="mdi:power" style="margin-right: 4px; --mdc-icon-size: 16px;"></ha-icon>${getTranslation(this._hass, 'off')}`;
    } else if (hvacAction === 'heating') {
      badge.classList.add('heating');
      badge.innerHTML = `<ha-icon icon="mdi:fire" style="margin-right: 4px; --mdc-icon-size: 16px;" class="glow-flame"></ha-icon>${getTranslation(this._hass, 'heating')}`;
    } else {
      badge.classList.add('idle');
      badge.innerHTML = `<ha-icon icon="mdi:thermometer" style="margin-right: 4px; --mdc-icon-size: 16px;"></ha-icon>${getTranslation(this._hass, 'idle')}`;
    }

    // Update HVAC mode buttons
    const btnHeat = this.shadowRoot.querySelector('#btn-mode-heat');
    const btnOff = this.shadowRoot.querySelector('#btn-mode-off');
    if (btnHeat) {
      btnHeat.className = 'btn-mode';
      btnHeat.innerHTML = `<ha-icon icon="mdi:fire" style="--mdc-icon-size: 18px;"></ha-icon>${getTranslation(this._hass, 'heat_mode')}`;
    }
    if (btnOff) {
      btnOff.className = 'btn-mode';
      btnOff.innerHTML = `<ha-icon icon="mdi:power" style="--mdc-icon-size: 18px;"></ha-icon>${getTranslation(this._hass, 'off')}`;
    }
    if (hvacMode === 'heat') {
      if (btnHeat) btnHeat.classList.add('active-heat');
    } else if (hvacMode === 'off') {
      if (btnOff) btnOff.classList.add('active-off');
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
      /* Simple CSS Toggle Switch */
      .switch {
        position: relative;
        display: inline-block;
        width: 38px;
        height: 20px;
      }
      .switch input {
        opacity: 0;
        width: 0;
        height: 0;
      }
      .slider {
        position: absolute;
        cursor: pointer;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background-color: var(--disabled-text-color, #ccc);
        transition: .4s;
        border-radius: 20px;
      }
      .slider:before {
        position: absolute;
        content: "";
        height: 14px;
        width: 14px;
        left: 3px;
        bottom: 3px;
        background-color: white;
        transition: .4s;
        border-radius: 50%;
      }
      input:checked + .slider {
        background-color: var(--primary-color, #03a9f4);
      }
      input:checked + .slider:before {
        transform: translateX(18px);
      }

      .thermostat-body {
        transition: opacity 0.3s ease;
      }
      .thermostat-body.disabled {
        opacity: 0.25;
        pointer-events: none;
      }

      .disabled-msg {
        display: none;
        position: absolute;
        top: 55px;
        left: 0;
        right: 0;
        bottom: 0;
        z-index: 8;
        text-align: center;
        padding-top: 50px;
      }
      .disabled-msg-box {
        display: inline-block;
        background: var(--card-background-color);
        border: 1px solid var(--divider-color);
        padding: 8px 16px;
        border-radius: 8px;
        box-shadow: 0 4px 8px rgba(0,0,0,0.1);
        color: var(--secondary-text-color);
        font-weight: 500;
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
      }
      .temp-target-val {
        font-size: 42px;
        font-weight: 300;
        color: var(--primary-text-color);
        line-height: 1.1;
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
        padding: 6px 12px;
        border-radius: 20px;
        font-size: 13px;
        font-weight: 500;
      }
      .status-badge.heating {
        background: rgba(255, 111, 0, 0.12);
        color: rgb(255, 111, 0);
      }
      .status-badge.idle {
        background: rgba(0, 150, 136, 0.12);
        color: rgb(0, 150, 136);
      }
      .status-badge.off {
        background: rgba(120, 120, 120, 0.12);
        color: rgb(120, 120, 120);
      }
      .status-badge.disabled {
        background: rgba(244, 67, 54, 0.12);
        color: rgb(244, 67, 54);
      }

      .glow-flame {
        animation: pulse-flame 1.5s infinite alternate;
      }
      @keyframes pulse-flame {
        0% { transform: scale(1); filter: drop-shadow(0 0 1px rgba(255,111,0,0.5)); }
        100% { transform: scale(1.1); filter: drop-shadow(0 0 5px rgba(255,111,0,0.8)); }
      }

      .hvac-modes {
        display: flex;
        justify-content: center;
        gap: 12px;
        border-top: 1px solid var(--divider-color);
        padding-top: 16px;
      }
      .btn-mode {
        flex: 1;
        max-width: 120px;
        padding: 10px;
        border-radius: 24px;
        border: 1px solid var(--divider-color);
        background-color: var(--card-background-color);
        color: var(--primary-text-color);
        font-size: 13px;
        font-weight: 500;
        cursor: pointer;
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 6px;
        transition: all 0.2s ease;
      }
      .btn-mode:hover {
        background-color: var(--secondary-background-color);
      }
      .btn-mode.active-heat {
        background-color: rgb(255, 111, 0);
        color: white;
        border-color: rgb(255, 111, 0);
        box-shadow: 0 4px 10px rgba(255, 111, 0, 0.25);
      }
      .btn-mode.active-off {
        background-color: var(--secondary-text-color);
        color: white;
        border-color: var(--secondary-text-color);
        box-shadow: 0 4px 10px rgba(0,0,0,0.15);
      }
    `;

    card.innerHTML = `
      <div class="wrapper" id="wrapper">
        <div class="header">
          <div class="title">Termostato</div>
          <div class="switch-container">
            <label id="zone-toggle-label">Abilitata</label>
            <label class="switch">
              <input type="checkbox" id="zone-toggle">
              <span class="slider"></span>
            </label>
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
              <div class="temp-target-val">--°C</div>
              <div class="temp-current">Rilevata: <span class="temp-current-val">--°C</span></div>
            </div>
            <button class="btn-temp" id="temp-up">+</button>
          </div>

          <div class="status-bar">
            <div class="status-badge"></div>
          </div>

          <div class="hvac-modes">
            <button class="btn-mode" id="btn-mode-off">
              <ha-icon icon="mdi:power" style="--mdc-icon-size: 18px;"></ha-icon>Spento
            </button>
            <button class="btn-mode" id="btn-mode-heat">
              <ha-icon icon="mdi:fire" style="--mdc-icon-size: 18px;"></ha-icon>Caldo
            </button>
          </div>
        </div>
      </div>
    `;

    // Hook events
    const toggle = card.querySelector('#zone-toggle');
    toggle.addEventListener('change', () => this.toggleZone(toggle.checked));

    card.querySelector('#temp-down').addEventListener('click', () => this.changeTemp(-0.5));
    card.querySelector('#temp-up').addEventListener('click', () => this.changeTemp(0.5));

    card.querySelector('#btn-mode-off').addEventListener('click', () => this.changeHvacMode('off'));
    card.querySelector('#btn-mode-heat').addEventListener('click', () => this.changeHvacMode('heat'));

    this.shadowRoot.appendChild(style);
    this.shadowRoot.appendChild(card);
    this._rendered = true;
  }

  toggleZone(enable) {
    const switchEntity = this._config.switch;
    if (!switchEntity) return;

    this._tempSwitchState = enable ? "on" : "off";
    this.updateCard(); // immediate local UI update
    
    this._hass.callService("switch", enable ? "turn_on" : "turn_off", {
      entity_id: switchEntity
    });

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

    const climateEntity = this._config.entity;
    const switchEntity = this._config.switch;
    
    const climateState = this._hass.states[climateEntity];
    const switchState = switchEntity ? this._hass.states[switchEntity] : null;

    if (!climateState) {
      this.renderError(getTranslation(this._hass, 'custom_error') + `: ${climateEntity} not found.`);
      return;
    }

    // Use temporary switch state if toggled locally to avoid flickering
    const actualSwitchState = this._tempSwitchState !== undefined 
      ? this._tempSwitchState 
      : (switchState ? switchState.state : "on");
    const isZoneEnabled = actualSwitchState === "on";

    // Update switch toggle state and label
    const toggle = this.shadowRoot.querySelector('#zone-toggle');
    if (toggle) {
      toggle.checked = isZoneEnabled;
    }
    const toggleLabel = this.shadowRoot.querySelector('#zone-toggle-label');
    if (toggleLabel) {
      toggleLabel.textContent = getTranslation(this._hass, 'enabled');
    }

    // Update disabled overlay text
    const disabledMsgBox = this.shadowRoot.querySelector('.disabled-msg-box');
    if (disabledMsgBox) {
      disabledMsgBox.innerHTML = `<ha-icon icon="mdi:alert-circle-outline" style="margin-right: 6px;"></ha-icon>${getTranslation(this._hass, 'bypass_msg')}`;
    }

    // Update title
    const title = this._config.title || climateState.attributes.friendly_name || getTranslation(this._hass, 'thermostat');
    const titleEl = this.shadowRoot.querySelector('#card-title');
    if (titleEl) {
      titleEl.textContent = title;
    }

    // Apply active/disabled styling and overlay
    const wrapper = this.shadowRoot.querySelector('#wrapper');
    if (wrapper) {
      if (isZoneEnabled) {
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
        margin-bottom: 8px;
        padding-bottom: 4px;
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
      .switch-container {
        display: flex;
        align-items: center;
        position: relative;
        z-index: 21;
      }
      .switch-container label {
        margin-right: 8px;
        font-size: 12px;
        color: var(--secondary-text-color);
        font-weight: 500;
      }
      /* Simple CSS Toggle Switch */
      .switch {
        position: relative;
        display: inline-block;
        width: 38px;
        height: 20px;
      }
      .switch input {
        opacity: 0;
        width: 0;
        height: 0;
      }
      .slider {
        position: absolute;
        cursor: pointer;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background-color: var(--disabled-text-color, #ccc);
        transition: .4s;
        border-radius: 20px;
      }
      .slider:before {
        position: absolute;
        content: "";
        height: 14px;
        width: 14px;
        left: 3px;
        bottom: 3px;
        background-color: white;
        transition: .4s;
        border-radius: 50%;
      }
      input:checked + .slider {
        background-color: var(--primary-color, #03a9f4);
      }
      input:checked + .slider:before {
        transform: translateX(18px);
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
        <div class="switch-container">
          <label id="zone-toggle-label">Abilitata</label>
          <label class="switch">
            <input type="checkbox" id="zone-toggle" checked>
            <span class="slider"></span>
          </label>
        </div>
      </div>

      <div class="disabled-overlay">
        <div class="disabled-msg-box">
          <ha-icon icon="mdi:alert-circle-outline" style="margin-right: 6px;"></ha-icon>Zona Esclusa / Bypassata
        </div>
      </div>

      <div id="card-body"></div>
    `;

    // Hook events
    const toggle = wrapper.querySelector('#zone-toggle');
    toggle.addEventListener('change', () => this.toggleZone(toggle.checked));

    card.appendChild(wrapper);
    this.shadowRoot.appendChild(style);
    this.shadowRoot.appendChild(card);
    this._rendered = true;
  }

  toggleZone(enable) {
    const switchEntity = this._config.switch;
    if (!switchEntity) return;

    this._tempSwitchState = enable ? "on" : "off";
    this.updateCard(); // immediate local UI update

    this._hass.callService("switch", enable ? "turn_on" : "turn_off", {
      entity_id: switchEntity
    });

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

    // Update the ha-card element's background color
    const card = this.shadowRoot.querySelector('ha-card');
    if (card) {
      card.style.backgroundColor = bgColor;
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

// Define elements
customElements.define("multizone-thermostat-button-card", MultizoneThermostatButtonCard);
customElements.define("multizone-thermostat-dial-card", MultizoneThermostatDialCard);
customElements.define("multizone-thermostat-status-card", MultizoneThermostatStatusCard);
customElements.define("multizone-thermostat-card-editor", MultizoneThermostatCardEditor);
