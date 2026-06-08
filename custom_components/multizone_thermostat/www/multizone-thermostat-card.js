// window.customCards definition to register the card in Lovelace UI
window.customCards = window.customCards || [];
window.customCards.push({
  type: "multizone-thermostat-card",
  name: "Multizone Thermostat Card",
  description: "A card to control a multizone thermostat zone and its bypass switch.",
  preview: true,
});

class MultizoneThermostatCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: 'open' });
    this._isDragging = false;
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
      title: "",
      layout: "button"
    };
  }

  updateCard() {
    if (!this._hass || !this._config) return;

    const climateEntity = this._config.entity;
    const switchEntity = this._config.switch;
    const layout = this._config.layout || 'button';

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
    const isZoneEnabled = switchState ? switchState.state === "on" : true;
    const title = this._config.title || climateState.attributes.friendly_name || "Termostato";

    // Setup initial DOM if not done
    if (!this._rendered) {
      this.renderStructure();
    }

    // Update layout class on card
    const cardEl = this.shadowRoot.querySelector('ha-card');
    cardEl.className = `layout-${layout}`;

    // Update title
    this.shadowRoot.querySelector('.title').textContent = title;

    // Update switch toggle
    const toggle = this.shadowRoot.querySelector('#zone-toggle');
    if (switchState) {
      toggle.style.display = 'block';
      this.shadowRoot.querySelector('#zone-toggle-label').style.display = 'block';
      toggle.checked = isZoneEnabled;
    } else {
      toggle.style.display = 'none';
      this.shadowRoot.querySelector('#zone-toggle-label').style.display = 'none';
    }

    // Apply active/disabled styling to thermostat control area
    const controlsArea = this.shadowRoot.querySelector('.thermostat-body');
    const disabledOverlay = this.shadowRoot.querySelector('.disabled-msg');
    if (isZoneEnabled) {
      controlsArea.classList.remove('disabled');
      disabledOverlay.style.display = 'none';
    } else {
      controlsArea.classList.add('disabled');
      disabledOverlay.style.display = 'block';
    }

    // --- Layout specific updates ---
    if (layout === 'button') {
      this.shadowRoot.querySelector('.temp-current-val').textContent = currentTemp !== undefined ? `${currentTemp}°C` : '--°C';
      this.shadowRoot.querySelector('.temp-target-val').textContent = targetTemp !== undefined ? `${targetTemp}°C` : '--°C';
    } else {
      // Dial layout
      this.shadowRoot.querySelector('.dial-temp-current-val').textContent = currentTemp !== undefined ? `${currentTemp}°C` : '--°C';
      
      let stateText = "Spento";
      if (hvacMode === 'heat') {
        stateText = hvacAction === 'heating' ? "Riscaldamento" : "In Attesa";
      }
      this.shadowRoot.querySelector('#dial-hvac-state').textContent = stateText;

      const minTemp = climateState.attributes.min_temp || 7;
      const maxTemp = climateState.attributes.max_temp || 35;
      
      const displayTargetTemp = this._isDragging && this._dragTemp !== undefined ? this._dragTemp : targetTemp;
      if (displayTargetTemp !== undefined) {
        this.updateDialUI(displayTargetTemp, minTemp, maxTemp);
      }
    }

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

  updateDialUI(temp, min, max) {
    const range = max - min;
    const pct = range > 0 ? (temp - min) / range : 0;
    
    // Update active track path dasharray
    const activeTrack = this.shadowRoot.querySelector('#dial-active-track');
    if (activeTrack) {
      const activeLength = pct * 353.43;
      activeTrack.setAttribute('stroke-dasharray', `${activeLength} 500`);
      
      const climateState = this._hass.states[this._config.entity];
      const hvacAction = climateState ? climateState.attributes.hvac_action : null;
      if (hvacAction === 'heating') {
        activeTrack.setAttribute('stroke', 'rgb(255, 111, 0)');
      } else {
        activeTrack.setAttribute('stroke', 'var(--primary-color, #03a9f4)');
      }
    }
    
    // Update knob position
    const knob = this.shadowRoot.querySelector('#dial-knob');
    if (knob) {
      const theta = 135 + pct * 270;
      const rad = (theta * Math.PI) / 180;
      const kx = 100 + 75 * Math.cos(rad);
      const ky = 100 + 75 * Math.sin(rad);
      knob.setAttribute('cx', kx);
      knob.setAttribute('cy', ky);
    }
    
    // Update text labels inside the dial
    const targetValEl = this.shadowRoot.querySelector('#dial-temp-target-val');
    if (targetValEl) {
      const formatted = temp.toFixed(1).replace('.', ',');
      targetValEl.textContent = `${formatted}°C`;
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
        width: 46px;
        height: 24px;
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
        border-radius: 24px;
      }
      .slider:before {
        position: absolute;
        content: "";
        height: 18px;
        width: 18px;
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
        transform: translateX(22px);
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
        top: 60px;
        left: 0;
        right: 0;
        bottom: 0;
        z-index: 2;
        text-align: center;
        padding-top: 60px;
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

      /* Layout Visibility togglers */
      .layout-button-view { display: none; }
      .layout-dial-view { display: none; }
      
      ha-card.layout-button .layout-button-view { display: block; }
      ha-card.layout-dial .layout-dial-view { display: block; }

      /* Button View styles */
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

      /* Dial View styles */
      .dial-container {
        display: flex;
        flex-direction: column;
        align-items: center;
        position: relative;
        margin: 10px 0;
      }
      .dial-svg {
        width: 200px;
        height: 200px;
        cursor: pointer;
      }
      .dial-center {
        position: absolute;
        top: 25px;
        left: 0;
        right: 0;
        bottom: 40px;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        pointer-events: none;
      }
      .dial-hvac-state {
        font-size: 14px;
        font-weight: 500;
        color: var(--secondary-text-color);
        margin-bottom: 2px;
      }
      .dial-temp-target {
        font-size: 42px;
        font-weight: 300;
        color: var(--primary-text-color);
        line-height: 1.0;
      }
      .dial-temp-current {
        font-size: 13px;
        color: var(--secondary-text-color);
        display: flex;
        align-items: center;
        margin-top: 6px;
      }
      .dial-temp-current ha-icon {
        --mdc-icon-size: 14px;
        margin-right: 4px;
      }
      .dial-buttons {
        display: flex;
        gap: 16px;
        margin-top: -15px;
        margin-bottom: 12px;
        z-index: 3;
      }

      /* Common layout styles */
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
        <!-- layout-button View -->
        <div class="layout-button-view">
          <div class="controls-container">
            <button class="btn-temp" id="temp-down-btn">-</button>
            <div class="temp-display">
              <div class="temp-target-val">--°C</div>
              <div class="temp-current">Rilevata: <span class="temp-current-val">--°C</span></div>
            </div>
            <button class="btn-temp" id="temp-up-btn">+</button>
          </div>
        </div>

        <!-- layout-dial View -->
        <div class="layout-dial-view">
          <div class="dial-container">
            <svg class="dial-svg" viewBox="0 0 200 200" id="dial-svg">
              <circle class="track" cx="100" cy="100" r="75" stroke="var(--secondary-background-color)" stroke-width="12" fill="none" stroke-linecap="round" stroke-dasharray="353.43 500" transform="rotate(135 100 100)" />
              <circle class="active-track" id="dial-active-track" cx="100" cy="100" r="75" stroke="var(--primary-color)" stroke-width="12" fill="none" stroke-linecap="round" stroke-dasharray="0 500" transform="rotate(135 100 100)" />
              <circle class="knob" id="dial-knob" cx="100" cy="100" r="10" fill="white" stroke="var(--divider-color)" stroke-width="2" />
            </svg>
            <div class="dial-center">
              <div class="dial-hvac-state" id="dial-hvac-state">Spento</div>
              <div class="dial-temp-target" id="dial-temp-target-val">--°C</div>
              <div class="dial-temp-current">
                <ha-icon icon="mdi:thermometer"></ha-icon>
                <span class="dial-temp-current-val">--°C</span>
              </div>
            </div>
            <div class="dial-buttons">
              <button class="btn-temp" id="temp-down-dial">-</button>
              <button class="btn-temp" id="temp-up-dial">+</button>
            </div>
          </div>
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
    `;

    // Hook events
    const toggle = card.querySelector('#zone-toggle');
    toggle.addEventListener('change', () => this.toggleZone(toggle.checked));

    // Button layout temperature adjustments
    card.querySelector('#temp-down-btn').addEventListener('click', () => this.changeTemp(-0.5));
    card.querySelector('#temp-up-btn').addEventListener('click', () => this.changeTemp(0.5));

    // Dial layout temperature adjustments
    card.querySelector('#temp-down-dial').addEventListener('click', () => this.changeTemp(-0.5));
    card.querySelector('#temp-up-dial').addEventListener('click', () => this.changeTemp(0.5));

    // HVAC modes
    card.querySelector('#btn-mode-off').addEventListener('click', () => this.changeHvacMode('off'));
    card.querySelector('#btn-mode-heat').addEventListener('click', () => this.changeHvacMode('heat'));

    // SVG Drag Event Listener
    const svg = card.querySelector('#dial-svg');
    
    const startDrag = (e) => {
      e.preventDefault();
      this._isDragging = true;
      updateDrag(e);
      
      window.addEventListener('mousemove', updateDrag);
      window.addEventListener('touchmove', updateDrag, { passive: false });
      window.addEventListener('mouseup', endDrag);
      window.addEventListener('touchend', endDrag);
    };

    const updateDrag = (e) => {
      if (!this._isDragging) return;
      if (e.cancelable) e.preventDefault();
      
      const rect = svg.getBoundingClientRect();
      const clientX = e.touches ? e.touches[0].clientX : e.clientX;
      const clientY = e.touches ? e.touches[0].clientY : e.clientY;
      
      const cx = rect.left + rect.width / 2;
      const cy = rect.top + rect.height / 2;
      
      const x = clientX - cx;
      const y = clientY - cy;
      
      let angle = (Math.atan2(y, x) * 180) / Math.PI;
      if (angle < 0) angle += 360;
      
      let shifted = angle - 135;
      if (shifted < 0) shifted += 360;
      
      let pct = 0;
      if (shifted <= 270) {
        pct = shifted / 270;
      } else if (shifted > 270) {
        pct = (shifted < 315) ? 1.0 : 0.0;
      }
      
      const climateEntity = this._config.entity;
      const state = this._hass.states[climateEntity];
      if (!state) return;
      
      const minTemp = state.attributes.min_temp || 7;
      const maxTemp = state.attributes.max_temp || 35;
      const step = state.attributes.target_temp_step || 0.5;
      
      const temp = minTemp + pct * (maxTemp - minTemp);
      const roundedTemp = Math.round(temp / step) * step;
      
      this.updateDialUI(roundedTemp, minTemp, maxTemp);
      this._dragTemp = roundedTemp;
      
      if (this._debounceTimer) clearTimeout(this._debounceTimer);
      this._debounceTimer = setTimeout(() => {
        this._hass.callService("climate", "set_temperature", {
          entity_id: climateEntity,
          temperature: roundedTemp
        });
      }, 150);
    };

    const endDrag = () => {
      this._isDragging = false;
      window.removeEventListener('mousemove', updateDrag);
      window.removeEventListener('touchmove', updateDrag);
      window.removeEventListener('mouseup', endDrag);
      window.removeEventListener('touchend', endDrag);
      
      if (this._dragTemp !== undefined) {
        const climateEntity = this._config.entity;
        this._hass.callService("climate", "set_temperature", {
          entity_id: climateEntity,
          temperature: this._dragTemp
        });
        this._dragTemp = undefined;
      }
    };

    svg.addEventListener('mousedown', startDrag);
    svg.addEventListener('touchstart', startDrag, { passive: false });

    this.shadowRoot.appendChild(style);
    this.shadowRoot.appendChild(card);
    this._rendered = true;
  }

  toggleZone(enable) {
    const switchEntity = this._config.switch;
    if (!switchEntity) return;

    this._hass.callService("switch", enable ? "turn_on" : "turn_off", {
      entity_id: switchEntity
    });
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
      this._layoutSelect.value = this._config.layout || 'button';
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
      input[type="text"], select {
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

    // Layout Row
    const layoutRow = document.createElement('div');
    layoutRow.className = 'form-row';
    const layoutLabel = document.createElement('label');
    layoutLabel.textContent = 'Stile Scheda (Layout)';
    const layoutSelect = document.createElement('select');
    layoutSelect.id = 'layout';
    
    const optButton = document.createElement('option');
    optButton.value = 'button';
    optButton.textContent = 'Pulsanti Semplici (Simple)';
    layoutSelect.appendChild(optButton);

    const optDial = document.createElement('option');
    optDial.value = 'dial';
    optDial.textContent = 'Termostato Classico (Dial)';
    layoutSelect.appendChild(optDial);

    layoutSelect.value = this._config.layout || 'button';
    layoutSelect.addEventListener('change', (e) => this._updateConfig('layout', e.target.value));
    this._layoutSelect = layoutSelect;
    layoutRow.appendChild(layoutLabel);
    layoutRow.appendChild(layoutSelect);
    container.appendChild(layoutRow);

    // Climate Entity Picker Row
    const climateRow = document.createElement('div');
    climateRow.className = 'form-row';
    const climateLabel = document.createElement('label');
    climateLabel.textContent = 'Termostato (Climate Entity)';
    const climatePicker = document.createElement('ha-entity-picker');
    climatePicker.setAttribute('domain-filter', 'climate');
    climatePicker.value = this._config.entity || '';
    climatePicker.hass = this._hass;
    climatePicker.addEventListener('value-changed', (e) => this._updateConfig('entity', e.detail.value));
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

customElements.define("multizone-thermostat-card", MultizoneThermostatCard);
customElements.define("multizone-thermostat-card-editor", MultizoneThermostatCardEditor);
