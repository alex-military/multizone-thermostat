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
          background: radial-gradient(circle at 30% 50%, rgba(249, 115, 22, 0.28) 0%, rgba(239, 68, 68, 0.10) 50%, rgba(20, 27, 41, 0.92) 85%) !important;
          border-color: rgba(249, 115, 22, 0.35) !important;
        }
        .cooling-aura {
          background: radial-gradient(circle at 30% 50%, rgba(56, 189, 248, 0.28) 0%, rgba(14, 165, 233, 0.10) 50%, rgba(20, 27, 41, 0.92) 85%) !important;
          border-color: rgba(56, 189, 248, 0.35) !important;
        }
        .idle-aura {
          background: radial-gradient(circle at 30% 50%, rgba(245, 158, 11, 0.18) 0%, rgba(20, 27, 41, 0.92) 80%) !important;
          border-color: rgba(245, 158, 11, 0.25) !important;
        }
        .cool-idle-aura {
          background: radial-gradient(circle at 30% 50%, rgba(14, 165, 233, 0.15) 0%, rgba(20, 27, 41, 0.92) 80%) !important;
          border-color: rgba(56, 189, 248, 0.2) !important;
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

    const masterMode = typeof getMasterHVACMode === 'function' ? getMasterHVACMode(this._hass) : 'heat';
    const isCoolMode = (masterMode === 'cool');

    boilerEntity = this._config.entity || this._config.boiler_entity;
    if (!boilerEntity && typeof findBoilerEntity === 'function') {
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

    // Central Heat Pump (PDC) detection
    let hpEntity = this._config.heat_pump_entity || this._config.hp_entity || null;
    const masterStateObj = (masterEntity && this._hass.states[masterEntity]) ? this._hass.states[masterEntity] : null;
    if (!hpEntity && masterStateObj && masterStateObj.attributes) {
      hpEntity = masterStateObj.attributes.heat_pump_ch_switch || masterStateObj.attributes.heat_pump_switch || masterStateObj.attributes.heat_pump_entity;
    }
    if (!hpEntity) {
      hpEntity = Object.keys(this._hass.states).find(k =>
        (k.startsWith("switch.") || k.startsWith("climate.")) &&
        (k.includes("heat_pump") || k.includes("pompa_di_calore") || k.includes("_pdc"))
      ) || null;
    }

    let isHpSwitchActive = false;
    if (hpEntity && this._hass.states[hpEntity]) {
      const hpSt = this._hass.states[hpEntity];
      isHpSwitchActive = (hpSt.state === "on" || hpSt.state === "heat" || hpSt.attributes?.hvac_action === "heating" || hpSt.attributes?.hvac_action === "cooling");
    }

    // Also inspect all multizone climate zones for active heating or cooling (including splits/PDC)
    let activeHeatingZones = 0;
    let activeCoolingZones = 0;
    let activeSplits = 0;
    let activePdcZones = 0;

    for (const key of Object.keys(this._hass.states)) {
      if (key.startsWith("climate.")) {
        const st = this._hass.states[key];
        const attrs = st ? st.attributes || {} : {};
        if (attrs.hybrid_zone || key.includes("multizone_thermostat_")) {
          const isZoneHeating = (attrs.hvac_action === "heating" || (st.state === "heat" && attrs.split_active));
          if (isZoneHeating) {
            activeHeatingZones++;
            if (attrs.pdc_active || attrs.hp_active || attrs.heat_pump_active || (attrs.active_heating_source === "electric" && !attrs.split_active)) {
              activePdcZones++;
            }
          }
          if (attrs.hvac_action === "cooling" || attrs.split_cooling || (st.state === "cool" && attrs.split_active)) {
            activeCoolingZones++;
            if (attrs.pdc_active || attrs.hp_active || attrs.heat_pump_active) {
              activePdcZones++;
            }
          }
          if (attrs.split_active) {
            activeSplits++;
          }
        }
      }
    }

    const isCentralHpActive = isHpSwitchActive || activePdcZones > 0 || (activeHeatingZones > 0 && !boilerEntity && Boolean(hpEntity));
    const hasCentralHp = Boolean(hpEntity || activePdcZones > 0);
    const hasBoiler = Boolean(boilerEntity);

    const isHeatingSystemActive = isBoilerActive || isCentralHpActive || activeHeatingZones > 0;
    const isCoolingSystemActive = activeCoolingZones > 0;

    const card = this.shadowRoot.getElementById('status-card');
    const iconWrap = this.shadowRoot.getElementById('master-icon-wrap');
    const icon = this.shadowRoot.getElementById('master-icon');
    const nameEl = this.shadowRoot.getElementById('master-name');
    const pill = this.shadowRoot.getElementById('master-pill');
    const stateText = this.shadowRoot.getElementById('master-state-text');
    const telemetry = this.shadowRoot.getElementById('master-telemetry');

    if (nameEl) {
      nameEl.textContent = isCoolMode
        ? (getTranslation(this._hass, 'cooling_active') ? 'Raffrescamento' : 'Raffrescamento')
        : 'Riscaldamento';
    }

    if (telemetry) {
      if (isCoolMode) {
        telemetry.textContent = activeCoolingZones > 0
          ? `Zone attive: ${activeCoolingZones}`
          : `Split / PDC: Standby`;
      } else if (activeSplits > 0 && !isBoilerActive && !isCentralHpActive) {
        telemetry.textContent = `Split Elettrico: ON`;
      } else if (activeSplits > 0 && isBoilerActive && !isCentralHpActive) {
        telemetry.textContent = `Caldaia: ON + Split`;
      } else if (activeSplits > 0 && isCentralHpActive && !isBoilerActive) {
        telemetry.textContent = `PDC: ON + Split`;
      } else if (activeSplits > 0 && isCentralHpActive && isBoilerActive) {
        telemetry.textContent = `Caldaia + PDC: ON + Split`;
      } else if (isCentralHpActive && isBoilerActive) {
        telemetry.textContent = `Caldaia + PDC: ON`;
      } else if (isCentralHpActive) {
        telemetry.textContent = `PDC: ON`;
      } else if (isBoilerActive) {
        telemetry.textContent = `Caldaia: ${boilerText}`;
      } else if (hasCentralHp && hasBoiler) {
        telemetry.textContent = `Caldaia / PDC: OFF`;
      } else if (hasCentralHp && !hasBoiler) {
        telemetry.textContent = `PDC: OFF`;
      } else if (activeHeatingZones > 0 && !isBoilerActive) {
        // Heating is active across zones without boiler switch: PDC or integrated central heating
        telemetry.textContent = hasCentralHp ? `PDC: ON` : `Caldaia / PDC: ON`;
      } else {
        telemetry.textContent = `Caldaia: ${boilerText}`;
      }
    }

    const isClassic = (this.getEffectiveStyle() === 'classic');

    if (!isMasterOn) {
      if (card && !isClassic) card.className = "";
      if (icon) {
        icon.icon = "mdi:power";
        icon.style.color = "var(--secondary-text-color, #94a3b8)";
      }
      if (iconWrap) {
        iconWrap.style.background = isClassic ? "var(--secondary-background-color, rgba(255, 255, 255, 0.05))" : "rgba(255, 255, 255, 0.04)";
        iconWrap.style.borderColor = "var(--divider-color, rgba(255, 255, 255, 0.1))";
        iconWrap.style.boxShadow = "none";
      }
      if (pill) {
        pill.style.background = isClassic ? "rgba(255, 255, 255, 0.06)" : "rgba(148, 163, 184, 0.12)";
        pill.style.color = "var(--secondary-text-color, #94a3b8)";
        pill.style.borderColor = "var(--divider-color, rgba(148, 163, 184, 0.25))";
      }
      if (stateText) stateText.textContent = "SPENTO";
    } else if (isCoolMode) {
      if (isCoolingSystemActive) {
        if (card && !isClassic) card.className = "cooling-aura";
        if (icon) {
          icon.icon = "mdi:snowflake";
          icon.style.color = "#38bdf8";
        }
        if (iconWrap) {
          iconWrap.style.background = "rgba(56, 189, 248, 0.22)";
          iconWrap.style.borderColor = "#38bdf8";
          iconWrap.style.boxShadow = isClassic ? "none" : "0 0 18px rgba(56, 189, 248, 0.45)";
        }
        if (pill) {
          pill.style.background = "rgba(56, 189, 248, 0.18)";
          pill.style.color = "#38bdf8";
          pill.style.borderColor = "rgba(56, 189, 248, 0.45)";
        }
        if (stateText) stateText.textContent = "RAFFRESCAMENTO ATTIVO";
      } else {
        if (card && !isClassic) card.className = "cool-idle-aura";
        if (icon) {
          icon.icon = "mdi:snowflake";
          icon.style.color = "#38bdf8";
        }
        if (iconWrap) {
          iconWrap.style.background = "rgba(56, 189, 248, 0.12)";
          iconWrap.style.borderColor = "rgba(56, 189, 248, 0.35)";
          iconWrap.style.boxShadow = isClassic ? "none" : "0 0 12px rgba(56, 189, 248, 0.2)";
        }
        if (pill) {
          pill.style.background = "rgba(56, 189, 248, 0.12)";
          pill.style.color = "#7dd3fc";
          pill.style.borderColor = "rgba(56, 189, 248, 0.3)";
        }
        if (stateText) stateText.textContent = "STANDBY (FREDDO)";
      }
    } else {
      if (isHeatingSystemActive) {
        if (card && !isClassic) card.className = "heating-aura";
        if (icon) {
          icon.icon = "mdi:fire";
          icon.style.color = "#f97316";
        }
        if (iconWrap) {
          iconWrap.style.background = "rgba(249, 115, 22, 0.22)";
          iconWrap.style.borderColor = "#f97316";
          iconWrap.style.boxShadow = isClassic ? "none" : "0 0 18px rgba(249, 115, 22, 0.45)";
        }
        if (pill) {
          pill.style.background = "rgba(249, 115, 22, 0.18)";
          pill.style.color = "#f97316";
          pill.style.borderColor = "rgba(249, 115, 22, 0.45)";
        }
        if (stateText) stateText.textContent = "RISCALDAMENTO ATTIVO";
      } else {
        if (card && !isClassic) card.className = "idle-aura";
        if (icon) {
          icon.icon = "mdi:power";
          icon.style.color = "#f59e0b";
        }
        if (iconWrap) {
          iconWrap.style.background = "rgba(245, 158, 11, 0.15)";
          iconWrap.style.borderColor = "#f59e0b";
          iconWrap.style.boxShadow = isClassic ? "none" : "0 0 15px rgba(245, 158, 11, 0.25)";
        }
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
