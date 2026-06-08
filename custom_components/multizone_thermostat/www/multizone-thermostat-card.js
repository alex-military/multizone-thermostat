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
      this.renderError(`Entità termostato ${climateEntity} non trovata.`);
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

    const title = this._config.title || climateState.attributes.friendly_name || "Termostato";

    // Update title
    this.shadowRoot.querySelector('.title').textContent = title;

    // Update switch toggle checked state
    const toggle = this.shadowRoot.querySelector('#zone-toggle');
    if (switchEntity) {
      toggle.style.display = 'block';
      this.shadowRoot.querySelector('#zone-toggle-label').style.display = 'block';
      toggle.checked = isZoneEnabled;
    } else {
      toggle.style.display = 'none';
      this.shadowRoot.querySelector('#zone-toggle-label').style.display = 'none';
    }

    // Apply active/disabled styling
    const controlsArea = this.shadowRoot.querySelector('.thermostat-body');
    const disabledOverlay = this.shadowRoot.querySelector('.disabled-msg');
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
    this.shadowRoot.querySelector('.temp-current-val').textContent = currentTemp !== undefined ? `${currentTemp}°C` : '--°C';
    this.shadowRoot.querySelector('.temp-target-val').textContent = targetTemp !== undefined ? `${targetTemp}°C` : '--°C';

    // Update status badge
    const badge = this.shadowRoot.querySelector('.status-badge');
    badge.className = 'status-badge';
    if (!isZoneEnabled) {
      badge.classList.add('disabled');
      badge.innerHTML = `<ha-icon icon="mdi:close-circle-outline" style="margin-right: 4px; --mdc-icon-size: 16px;"></ha-icon>Zona Esclusa`;
    } else if (hvacMode === 'off') {
      badge.classList.add('off');
      badge.innerHTML = `<ha-icon icon="mdi:power" style="margin-right: 4px; --mdc-icon-size: 16px;"></ha-icon>Spento`;
    } else if (hvacAction === 'heating') {
      badge.classList.add('heating');
      badge.innerHTML = `<ha-icon icon="mdi:fire" style="margin-right: 4px; --mdc-icon-size: 16px;" class="glow-flame"></ha-icon>Riscaldamento`;
    } else {
      badge.classList.add('idle');
      badge.innerHTML = `<ha-icon icon="mdi:thermometer" style="margin-right: 4px; --mdc-icon-size: 16px;"></ha-icon>Attivo (In Attesa)`;
    }

    // Update HVAC mode buttons
    const btnHeat = this.shadowRoot.querySelector('#btn-mode-heat');
    const btnOff = this.shadowRoot.querySelector('#btn-mode-off');
    btnHeat.className = 'btn-mode';
    btnOff.className = 'btn-mode';
    if (hvacMode === 'heat') {
      btnHeat.classList.add('active-heat');
    } else if (hvacMode === 'off') {
      btnOff.classList.add('active-off');
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
  }

  set hass(hass) {
    this._hass = hass;
    if (this._childCard) {
      this._childCard.hass = hass;
    }
    this.updateCard();
  }

  async setConfig(config) {
    if (!config.entity) {
      throw new Error("Specificare un termostato (climate entity)");
    }
    this._config = config;

    this._helpers = await window.loadCardHelpers();
    this.createChildCard();
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
      this.renderError(`Entità termostato ${climateEntity} non trovata.`);
      return;
    }

    // Use temporary switch state if toggled locally to avoid flickering
    const actualSwitchState = this._tempSwitchState !== undefined 
      ? this._tempSwitchState 
      : (switchState ? switchState.state : "on");
    const isZoneEnabled = actualSwitchState === "on";

    // Update switch toggle state
    const toggle = this.shadowRoot.querySelector('#zone-toggle');
    if (toggle) {
      toggle.checked = isZoneEnabled;
    }

    // Update title
    const title = this._config.title || climateState.attributes.friendly_name || "Termostato";
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
        z-index: 10;
        pointer-events: auto;
      }
      .switch-container label {
        margin-right: 8px;
        font-size: 12px;
        color: var(--secondary-text-color);
        font-weight: 500;
        pointer-events: none;
      }
      /* Simple CSS Toggle Switch */
      .switch {
        position: relative;
        display: inline-block;
        width: 38px;
        height: 20px;
        pointer-events: auto;
      }
      .switch input {
        opacity: 0;
        width: 0;
        height: 0;
        pointer-events: auto;
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
        pointer-events: none;
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
        pointer-events: none;
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
  }

  setConfig(config) {
    this._config = config;
    this.render();
  }

  render() {
    if (this._rendered) {
      this.shadowRoot.querySelector('#title').value = this._config.title || '';
      this._climatePicker.value = this._config.entity || '';
      this._switchPicker.value = this._config.switch || '';
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
    climateLabel.textContent = 'Termostato (Climate Entity)';
    const climatePicker = document.createElement('ha-entity-picker');
    climatePicker.setAttribute('domain-filter', 'climate');
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
    switchLabel.textContent = 'Switch di Zona (Abilita/Escludi)';
    const switchPicker = document.createElement('ha-entity-picker');
    switchPicker.setAttribute('domain-filter', 'switch');
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

// Define elements
customElements.define("multizone-thermostat-button-card", MultizoneThermostatButtonCard);
customElements.define("multizone-thermostat-dial-card", MultizoneThermostatDialCard);
customElements.define("multizone-thermostat-card-editor", MultizoneThermostatCardEditor);
