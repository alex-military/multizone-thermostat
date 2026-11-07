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
    if (!config || !config.entity) {
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
    if (!this._hass || !this._hass.states) return;
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

    if (!this._rendered) {
      this.renderStructure();
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
    const step = this.getStep(climateState);
    const decimals = step.toString().includes('.') ? (step.toString().split('.')[1] || '').length : 0;
    let targetDisplay = '--';
    if (targetTemp !== undefined && targetTemp !== null) {
      const num = parseFloat(targetTemp);
      targetDisplay = !isNaN(num) ? (decimals > 0 && !Number.isInteger(num) ? num.toFixed(decimals) : num) : targetTemp;
    }
    this.shadowRoot.querySelector('.temp-target-val').textContent = `${targetDisplay}°C`;
    
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
    this.shadowRoot.innerHTML = '';
    const card = document.createElement('ha-card');
    const style = document.createElement('style');

    style.textContent = `
      ha-card {
        padding: 16px;
        position: relative;
        overflow: hidden;
        border-radius: var(--ha-card-border-radius, 20px);
        border: 1px solid var(--ha-card-border-color, rgba(255, 255, 255, 0.08));
        box-shadow: var(--ha-card-box-shadow, 0 4px 12px rgba(0, 0, 0, 0.15));
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

    card.querySelector('#temp-down').addEventListener('click', () => this.changeTemp(-1));
    card.querySelector('#temp-up').addEventListener('click', () => this.changeTemp(1));



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

  getStep(climateState) {
    if (this._config && (this._config.step !== undefined || this._config.target_temp_step !== undefined)) {
      const cfgStep = parseFloat(this._config.step ?? this._config.target_temp_step);
      if (!isNaN(cfgStep) && cfgStep > 0) return cfgStep;
    }
    const state = climateState || (this._hass && this._config && this._config.entity ? this._hass.states[this._config.entity] : null);
    if (state && state.attributes && state.attributes.target_temp_step !== undefined && state.attributes.target_temp_step !== null) {
      const attrStep = parseFloat(state.attributes.target_temp_step);
      if (!isNaN(attrStep) && attrStep > 0) return attrStep;
    }
    return 0.5;
  }

  changeTemp(stepOrDirection) {
    const climateEntity = this._config.entity;
    const state = this._hass.states[climateEntity];
    if (!state) return;

    const currentTarget = state.attributes.temperature;
    if (currentTarget === undefined || currentTarget === null) return;

    const step = this.getStep(state);

    let delta = 0;
    if (typeof stepOrDirection === 'number') {
      if (stepOrDirection > 0) {
        delta = step;
      } else if (stepOrDirection < 0) {
        delta = -step;
      }
    } else {
      delta = step;
    }

    const stepStr = step.toString();
    const decimals = stepStr.includes('.') ? (stepStr.split('.')[1] || '').length : 0;
    const rawTarget = Math.round((currentTarget + delta) / step) * step;
    const newTarget = parseFloat(rawTarget.toFixed(decimals));

    const minTemp = state.attributes.min_temp !== undefined ? parseFloat(state.attributes.min_temp) : undefined;
    const maxTemp = state.attributes.max_temp !== undefined ? parseFloat(state.attributes.max_temp) : undefined;
    let clampedTarget = newTarget;
    if (minTemp !== undefined && !isNaN(minTemp)) clampedTarget = Math.max(clampedTarget, minTemp);
    if (maxTemp !== undefined && !isNaN(maxTemp)) clampedTarget = Math.min(clampedTarget, maxTemp);

    this._hass.callService("climate", "set_temperature", {
      entity_id: climateEntity,
      temperature: clampedTarget
    });
  }

  disconnectedCallback() {
    // HTMLElement has no disconnectedCallback, so do NOT call super
    if (this._tempTimer) {
        clearTimeout(this._tempTimer);
        this._tempTimer = null;
    }
  }

  renderError(msg) {
    this.shadowRoot.innerHTML = `
      <ha-card style="padding: 16px; color: red;">
        <h3>${this._hass ? getTranslation(this._hass, 'card_error_title') : 'Multizone Thermostat Card Error'}</h3>
        <p>${msg}</p>
      </ha-card>
    `;
    this._rendered = false;
  }
}


/* ==================== DIAL (NATIVE WRAPPER) CARD CLASS ==================== */
/* ==================== DIAL CARD (BESPOKE VECTOR ARC & DRAG SLIDER) ==================== */
/* ==================== DIAL CARD (BESPOKE VECTOR ARC & DRAG SLIDER) ==================== */
