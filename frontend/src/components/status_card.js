class MultizoneThermostatStatusCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: 'open' });
  }

  connectedCallback() {
    this._styleListener = () => {
      this.renderStructure();
      this.updateCard();
    };
    window.addEventListener('mz-style-changed', this._styleListener);
  }

  disconnectedCallback() {
    if (this._styleListener) {
      window.removeEventListener('mz-style-changed', this._styleListener);
    }
  }

  getEffectiveStyle() {
    return getActiveMzCardStyle();
  }

  set hass(hass) {
    this._hass = hass;
    this.updateCard();
  }

  setConfig(config) {
    this._config = Object.assign({}, config);
    if (!this._rendered) {
      this.renderStructure();
    }
    this.updateCard();
  }

  getCardSize() {
    return 1;
  }

  renderStructure() {
    const card = document.createElement('ha-card');
    const style = document.createElement('style');

    const radius = (this._config && this._config.border_radius) ? this._config.border_radius : '20px';
    const isClassic = (this.getEffectiveStyle() === 'classic');

    if (isClassic) {
      style.textContent = `
        :host {
          display: block;
          height: 100%;
          box-sizing: border-box;
        }
        ha-card {
          padding: 18px 20px;
          border-radius: ${radius} !important;
          overflow: hidden !important;
          color: var(--primary-text-color, white);
          background: var(--ha-card-background, var(--card-background-color, #1c1c1e)) !important;
          border: var(--ha-card-border-width, 1px) solid var(--ha-card-border-color, var(--divider-color, rgba(255, 255, 255, 0.12))) !important;
          box-shadow: var(--ha-card-box-shadow, 0 2px 8px rgba(0, 0, 0, 0.2)) !important;
          backdrop-filter: none !important;
          -webkit-backdrop-filter: none !important;
          transition: all 0.3s ease;
          cursor: pointer;
          display: flex;
          align-items: center;
          height: 100%;
          min-height: 96px;
          position: relative;
          box-sizing: border-box;
        }
        ha-card:hover {
          transform: translateY(-2px);
          box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3) !important;
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
        .icon-wrap {
          display: flex;
          align-items: center;
          justify-content: center;
          width: 54px;
          height: 54px;
          border-radius: 12px;
          background: var(--secondary-background-color, rgba(255, 255, 255, 0.05));
          border: 1px solid var(--divider-color, rgba(255, 255, 255, 0.12));
          flex-shrink: 0;
          transition: transform 0.2s ease;
        }
        ha-card:hover .icon-wrap {
          transform: scale(1.05);
        }
        .icon-wrap ha-icon {
          --mdc-icon-size: 28px;
          color: var(--primary-color, #0284c7);
        }
        .info-container {
          display: flex;
          flex-direction: column;
          justify-content: center;
          flex-grow: 1;
          overflow: hidden;
          gap: 3px;
        }
        .sub-title {
          font-size: 11px;
          font-weight: 700;
          text-transform: uppercase;
          letter-spacing: 0.8px;
          color: var(--secondary-text-color, #94a3b8);
        }
        .name {
          font-size: 16px;
          font-weight: 700;
          margin: 0;
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
          color: var(--primary-text-color, #ffffff);
        }
        .status-pill {
          display: inline-flex;
          align-items: center;
          gap: 6px;
          padding: 2px 8px;
          border-radius: 6px;
          font-size: 11px;
          font-weight: 600;
          letter-spacing: 0.3px;
          align-self: flex-start;
          margin-top: 2px;
          background: rgba(255, 255, 255, 0.06);
          color: var(--primary-text-color, #ffffff);
          border: 1px solid var(--divider-color, rgba(255, 255, 255, 0.1));
        }
        .status-dot {
          width: 6px;
          height: 6px;
          border-radius: 50%;
          background: currentColor;
        }
        .telemetry {
          font-size: 11px;
          color: var(--secondary-text-color, #94a3b8);
          font-weight: 500;
          margin-top: 2px;
        }
      `;
    } else {
      style.textContent = `
        :host {
          display: block;
          height: 100%;
          box-sizing: border-box;
        }
        ha-card {
          padding: 18px 20px;
          border-radius: ${radius} !important;
          overflow: hidden !important;
          color: white;
          background: linear-gradient(135deg, rgba(20, 27, 41, 0.88) 0%, rgba(15, 23, 42, 0.94) 100%) !important;
          backdrop-filter: blur(20px) !important;
          -webkit-backdrop-filter: blur(20px) !important;
          border: 1px solid rgba(255, 255, 255, 0.08) !important;
          box-shadow: 0 10px 30px -10px rgba(0, 0, 0, 0.5), inset 0 1px 0 rgba(255, 255, 255, 0.08) !important;
          transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
          cursor: pointer;
          display: flex;
          align-items: center;
          height: 100%;
          min-height: 96px;
          position: relative;
          box-sizing: border-box;
        }
        ha-card:hover {
          transform: translateY(-2px);
          border-color: rgba(255, 255, 255, 0.16) !important;
          box-shadow: 0 16px 40px -10px rgba(0, 0, 0, 0.7), inset 0 1px 0 rgba(255, 255, 255, 0.12) !important;
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
        .icon-wrap {
          display: flex;
          align-items: center;
          justify-content: center;
          width: 58px;
          height: 58px;
          border-radius: 18px;
          background: rgba(255, 255, 255, 0.06);
          border: 1px solid rgba(255, 255, 255, 0.1);
          flex-shrink: 0;
          transition: transform 0.2s ease, background 0.3s ease, box-shadow 0.3s ease;
        }
        ha-card:hover .icon-wrap {
          transform: scale(1.08);
        }
        .icon-wrap ha-icon {
          --mdc-icon-size: 30px;
          color: inherit;
        }
        .info-container {
          display: flex;
          flex-direction: column;
          justify-content: center;
          flex-grow: 1;
          overflow: hidden;
          gap: 3px;
        }
        .sub-title {
          font-size: 11px;
          font-weight: 700;
          text-transform: uppercase;
          letter-spacing: 0.8px;
          color: #94a3b8;
        }
        .name {
          font-size: 17px;
          font-weight: 800;
          margin: 0;
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
          color: #ffffff;
          letter-spacing: -0.3px;
        }
        .status-pill {
          display: inline-flex;
          align-items: center;
          gap: 6px;
          padding: 3px 10px;
          border-radius: 9999px;
          font-size: 11px;
          font-weight: 700;
          letter-spacing: 0.3px;
          text-transform: uppercase;
          align-self: flex-start;
          margin-top: 2px;
          box-shadow: 0 2px 6px rgba(0, 0, 0, 0.2);
        }
        .status-dot {
          width: 6px;
          height: 6px;
          border-radius: 50%;
          background: currentColor;
          box-shadow: 0 0 6px currentColor;
        }
        .telemetry {
          font-size: 11px;
          color: #94a3b8;
          font-weight: 600;
          margin-top: 2px;
        }
        .heating-aura {
          background: radial-gradient(circle at 30% 50%, rgba(249, 115, 22, 0.25) 0%, rgba(239, 68, 68, 0.08) 50%, rgba(20, 27, 41, 0.92) 80%) !important;
        }
        .idle-aura {
          background: radial-gradient(circle at 30% 50%, rgba(245, 158, 11, 0.18) 0%, rgba(20, 27, 41, 0.92) 80%) !important;
        }
      `;
    }

    card.id = 'status-card';
    card.innerHTML = `
      <div class="card-content">
        <div class="icon-wrap" id="master-icon-wrap">
          <ha-icon id="master-icon" icon="mdi:power"></ha-icon>
        </div>
        <div class="info-container">
          <div class="sub-title">Impianto Centrale</div>
          <div class="name" id="master-name">Riscaldamento</div>
          <div style="display: flex; align-items: center; gap: 8px; flex-wrap: wrap;">
            <div class="status-pill" id="master-pill">
              <span class="status-dot"></span>
              <span id="master-state-text">Caricamento...</span>
            </div>
            <div class="telemetry" id="master-telemetry">Caldaia: OFF</div>
          </div>
        </div>
      </div>
    `;

    card.addEventListener('click', () => {
      this.toggleMaster();
    });

    this.shadowRoot.innerHTML = '';
    this.shadowRoot.appendChild(style);
    this.shadowRoot.appendChild(card);
    this._rendered = true;
  }

  toggleMaster() {
    if (!this._hass) return;
    const masterEntity = findMasterEntity(this._hass);
    if (!masterEntity) return;

    this._hass.callService("switch", "toggle", {
      entity_id: masterEntity
    });
  }

  updateCard() {
    if (!this._hass || !this._hass.states) return;
    if (!this._rendered) return;

    const masterEntity = findMasterEntity(this._hass);
    let isMasterOn = false;
    let boilerEntity = null;

    if (masterEntity) {
      const masterState = this._hass.states[masterEntity];
      if (masterState) {
        isMasterOn = masterState.state === "on";
      }
    }

    boilerEntity = this._config.entity || this._config.boiler_entity;
    if (!boilerEntity) {
      boilerEntity = findBoilerEntity(this._hass);
    }

    let isBoilerActive = false;
    let boilerText = "OFF";

    if (boilerEntity) {
      const bState = this._hass.states[boilerEntity];
      if (bState) {
        if (boilerEntity.startsWith("switch.")) {
          isBoilerActive = bState.state === "on";
          boilerText = isBoilerActive ? "ON" : "OFF";
        } else if (boilerEntity.startsWith("sensor.")) {
          const val = parseFloat(bState.state);
          isBoilerActive = !isNaN(val) && val > 0;
          boilerText = `${bState.state} ${bState.attributes.unit_of_measurement || ''}`.trim();
        }
      }
    }

    const card = this.shadowRoot.getElementById('status-card');
    const iconWrap = this.shadowRoot.getElementById('master-icon-wrap');
    const icon = this.shadowRoot.getElementById('master-icon');
    const pill = this.shadowRoot.getElementById('master-pill');
    const stateText = this.shadowRoot.getElementById('master-state-text');
    const telemetry = this.shadowRoot.getElementById('master-telemetry');

    if (telemetry) {
      let zonesHeating = 0;
      for (const k of Object.keys(this._hass.states)) {
        if (k.startsWith('climate.')) {
          const a = this._hass.states[k].attributes || {};
          if ((a.hybrid_zone || k.includes('multizone_thermostat_')) && a.hvac_action === 'heating') zonesHeating++;
        }
      }
      telemetry.textContent = (isMasterOn && !isBoilerActive && zonesHeating > 0 && boilerEntity)
        ? `Caldaia: ${boilerText} (richiesta calore)`
        : `Caldaia: ${boilerText}`;
    }

    const isClassic = (this.getEffectiveStyle() === 'classic');

    if (!isMasterOn) {
      if (card && !isClassic) card.className = "";
      if (iconWrap) {
        iconWrap.style.background = isClassic ? "var(--secondary-background-color, rgba(255, 255, 255, 0.05))" : "rgba(255, 255, 255, 0.04)";
        iconWrap.style.borderColor = "var(--divider-color, rgba(255, 255, 255, 0.1))";
        iconWrap.style.boxShadow = "none";
      }
      if (icon) icon.style.color = "var(--secondary-text-color, #94a3b8)";
      if (pill) {
        pill.style.background = isClassic ? "rgba(255, 255, 255, 0.06)" : "rgba(148, 163, 184, 0.12)";
        pill.style.color = "var(--secondary-text-color, #94a3b8)";
        pill.style.borderColor = "var(--divider-color, rgba(148, 163, 184, 0.25))";
      }
      if (stateText) stateText.textContent = "SPENTO";
    } else {
      if (isBoilerActive) {
        if (card && !isClassic) card.className = "heating-aura";
        if (iconWrap) {
          iconWrap.style.background = "rgba(249, 115, 22, 0.2)";
          iconWrap.style.borderColor = "#f97316";
          iconWrap.style.boxShadow = isClassic ? "none" : "0 0 15px rgba(249, 115, 22, 0.4)";
        }
        if (icon) icon.style.color = "#f97316";
        if (pill) {
          pill.style.background = "rgba(249, 115, 22, 0.15)";
          pill.style.color = "#f97316";
          pill.style.borderColor = "rgba(249, 115, 22, 0.4)";
        }
        if (stateText) stateText.textContent = "RISCALDAMENTO ATTIVO";
      } else {
        if (card && !isClassic) card.className = "idle-aura";
        if (iconWrap) {
          iconWrap.style.background = "rgba(245, 158, 11, 0.15)";
          iconWrap.style.borderColor = "#f59e0b";
          iconWrap.style.boxShadow = isClassic ? "none" : "0 0 15px rgba(245, 158, 11, 0.25)";
        }
        if (icon) icon.style.color = "#f59e0b";
        if (pill) {
          pill.style.background = "rgba(245, 158, 11, 0.15)";
          pill.style.color = "#f59e0b";
          pill.style.borderColor = "rgba(245, 158, 11, 0.35)";
        }
        if (stateText) stateText.textContent = "STANDBY (ACCESO)";
      }
    }
  }
}

/* ==================== MULTIZONE PRESET CARD ==================== */
