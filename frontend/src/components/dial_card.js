class MultizoneThermostatDialCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: 'open' });
    this._rendered = false;
    this._isDragging = false;
    this._dragTargetTemp = undefined;
    this._minTemp = 10;
    this._maxTemp = 30;
    this._targetTemp = 20;
    this._currentTemp = 20;
    this._isHeating = false;
    this._isCooling = false;
    this._isStandby = false;
    this._isOff = false;
    this._switchEntity = null;
    this._switchTimeout = null;
  }

  formatTemperature(val) {
    if (typeof val !== 'number' || isNaN(val)) return '--';
    return val.toFixed(1).replace('.', ',');
  }

  updateTargetTempDisplay(val) {
    const formatted = this.formatTemperature(val);
    const parts = formatted.split(',');
    const intPart = parts[0] || '--';
    const decPart = parts.length > 1 ? ',' + parts[1] : '';
    const intEl = this.shadowRoot.querySelector('#target-temp-int');
    const decEl = this.shadowRoot.querySelector('#target-temp-dec');
    if (intEl) intEl.textContent = intPart;
    if (decEl) decEl.textContent = decPart;
    const legacyEl = this.shadowRoot.querySelector('#target-temp');
    if (legacyEl) legacyEl.textContent = formatted;
  }

  set hass(hass) {
    this._hass = hass;
    if (!this._rendered) {
      this.renderStructure();
    }
    this.updateCard();
  }

  connectedCallback() {
    this._styleListener = (e) => {
      const newStyle = e.detail?.style || 'luxury';
      this._effectiveStyle = newStyle;
      if (this._config) this._config.card_style = newStyle;
      this.renderStructure();
      this.updateCard();
    };
    window.addEventListener('mz-style-changed', this._styleListener);
  }

  disconnectedCallback() {
    this._isDragging = false;
    if (this._onWindowPointerUp) {
      window.removeEventListener('pointerup', this._onWindowPointerUp);
      window.removeEventListener('pointercancel', this._onWindowPointerUp);
      this._onWindowPointerUp = null;
    }
    if (this._styleListener) {
      window.removeEventListener('mz-style-changed', this._styleListener);
    }
    if (this._switchTimeout) {
      clearTimeout(this._switchTimeout);
      this._switchTimeout = null;
    }
  }

  getEffectiveStyle() {
    if (this._effectiveStyle) return this._effectiveStyle;
    const saved = localStorage.getItem('mz_card_style');
    if (saved) return saved;
    if (this._config && (this._config.card_style || this._config.style)) {
      return this._config.card_style || this._config.style;
    }
    return 'luxury';
  }

  setConfig(config) {
    if (!config || !config.entity) {
      throw new Error("Specificare un termostato (climate entity)");
    }
    const prevStyle = this.getEffectiveStyle();
    this._config = Object.assign({}, config);
    const newStyle = this.getEffectiveStyle();

    if (!this._rendered || prevStyle !== newStyle) {
      this.renderStructure();
    }
    this.updateCard();
  }

  getStep() {
    if (this._config && (this._config.step !== undefined || this._config.target_temp_step !== undefined)) {
      const cfgStep = parseFloat(this._config.step ?? this._config.target_temp_step);
      if (!isNaN(cfgStep) && cfgStep > 0) return cfgStep;
    }
    const climateState = this._hass && this._config && this._config.entity ? this._hass.states[this._config.entity] : null;
    if (climateState && climateState.attributes && climateState.attributes.target_temp_step !== undefined && climateState.attributes.target_temp_step !== null) {
      const attrStep = parseFloat(climateState.attributes.target_temp_step);
      if (!isNaN(attrStep) && attrStep > 0) return attrStep;
    }
    return 0.5;
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
      card_style: "luxury"
    };
  }

  renderStructure() {
    const radius = (this._config && this._config.border_radius) ? this._config.border_radius : '20px';
    const isClassic = (this.getEffectiveStyle() === "classic");
    this.renderUnifiedStructure(radius, isClassic);
    this._rendered = true;
  }

  renderClassicStructure(radius) {
    this.renderUnifiedStructure(radius, true);
  }

  renderLuxuryStructure(radius) {
    this.renderUnifiedStructure(radius, false);
  }

  renderUnifiedStructure(radius, isClassic) {
    const cardBgStyle = isClassic ? `
        ha-card {
          padding: 16px 16px 14px 16px;
          position: relative;
          overflow: hidden !important;
          border-radius: ${radius} !important;
          background: var(--ha-card-background, var(--card-background-color, #1c1c1e)) !important;
          border: var(--ha-card-border-width, 1px) solid var(--ha-card-border-color, var(--divider-color, rgba(255, 255, 255, 0.12))) !important;
          box-shadow: var(--ha-card-box-shadow, 0 2px 8px rgba(0, 0, 0, 0.2)) !important;
          backdrop-filter: none !important;
          -webkit-backdrop-filter: none !important;
          transition: all 0.3s ease;
          display: flex;
          flex-direction: column;
          justify-content: space-between;
          box-sizing: border-box;
          user-select: none;
          touch-action: pan-y;
        }
        .dial-track {
          stroke: rgba(255, 255, 255, 0.12);
          stroke-width: 24;
          stroke-linecap: round;
          fill: none;
        }
        .step-btn {
          pointer-events: auto;
          width: 48px;
          height: 48px;
          border-radius: 50%;
          background: transparent;
          border: 1px solid var(--divider-color, rgba(255, 255, 255, 0.22));
          color: var(--primary-text-color, #ffffff);
          display: flex;
          align-items: center;
          justify-content: center;
          cursor: pointer;
          transition: all 0.2s ease;
        }
        .step-btn:hover {
          background: rgba(255, 255, 255, 0.08);
          border-color: rgba(255, 255, 255, 0.35);
        }
        .segmented-control {
          display: flex;
          align-items: center;
          background: var(--card-background-color, #202b38);
          border: 1px solid var(--divider-color, rgba(255, 255, 255, 0.15));
          border-radius: 9999px;
          padding: 2px;
          gap: 2px;
          z-index: 21;
        }
        .split-pill-btn {
          display: inline-flex;
          align-items: center;
          gap: 6px;
          background: var(--card-background-color, #202b38);
          border: 1px solid var(--divider-color, rgba(255, 255, 255, 0.15));
          color: var(--secondary-text-color, #94a3b8);
          padding: 4px 12px;
          border-radius: 9999px;
          font-size: 11px;
          font-weight: 600;
          cursor: pointer;
          transition: all 0.2s ease;
          white-space: nowrap;
        }
    ` : `
        ha-card {
          padding: 16px 16px 14px 16px;
          position: relative;
          overflow: hidden !important;
          border-radius: ${radius} !important;
          background: linear-gradient(135deg, rgba(20, 27, 41, 0.88) 0%, rgba(15, 23, 42, 0.94) 100%) !important;
          backdrop-filter: blur(20px) !important;
          -webkit-backdrop-filter: blur(20px) !important;
          border: 1px solid rgba(255, 255, 255, 0.08) !important;
          box-shadow: 0 10px 30px -10px rgba(0, 0, 0, 0.5), inset 0 1px 0 rgba(255, 255, 255, 0.08) !important;
          transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
          display: flex;
          flex-direction: column;
          justify-content: space-between;
          box-sizing: border-box;
          user-select: none;
          touch-action: pan-y;
        }
        ha-card:hover {
          border-color: rgba(255, 255, 255, 0.16) !important;
          transform: translateY(-2px);
          box-shadow: 0 16px 40px -10px rgba(0, 0, 0, 0.7), inset 0 1px 0 rgba(255, 255, 255, 0.12) !important;
        }
        .heating-aura {
          background: radial-gradient(circle at 50% 120%, rgba(249, 115, 22, 0.22) 0%, rgba(239, 68, 68, 0.06) 45%, rgba(20, 27, 41, 0.92) 75%) !important;
        }
        .cooling-aura {
          background: radial-gradient(circle at 50% 120%, rgba(56, 189, 248, 0.22) 0%, rgba(14, 165, 233, 0.06) 45%, rgba(20, 27, 41, 0.92) 75%) !important;
        }
        .idle-aura {
          background: radial-gradient(circle at 50% 120%, rgba(255, 255, 255, 0.06) 0%, rgba(20, 27, 41, 0.92) 75%) !important;
        }
        .dial-track {
          stroke: rgba(255, 255, 255, 0.08);
          stroke-width: 24;
          stroke-linecap: round;
          fill: none;
        }
        .step-btn {
          pointer-events: auto;
          width: 48px;
          height: 48px;
          border-radius: 50%;
          background: rgba(255, 255, 255, 0.06);
          border: 1px solid rgba(255, 255, 255, 0.16);
          color: #ffffff;
          display: flex;
          align-items: center;
          justify-content: center;
          cursor: pointer;
          transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1);
          box-shadow: 0 4px 12px rgba(0, 0, 0, 0.25);
        }
        .step-btn:hover {
          background: rgba(255, 255, 255, 0.14);
          border-color: rgba(255, 255, 255, 0.28);
          transform: scale(1.04);
        }
        .segmented-control {
          display: flex;
          align-items: center;
          background: rgba(15, 23, 42, 0.85);
          border: 1px solid rgba(255, 255, 255, 0.1);
          border-radius: 9999px;
          padding: 2px;
          gap: 2px;
          z-index: 21;
        }
        .split-pill-btn {
          display: inline-flex;
          align-items: center;
          gap: 6px;
          background: rgba(15, 23, 42, 0.85);
          border: 1px solid rgba(255, 255, 255, 0.12);
          color: #cbd5e1;
          padding: 4px 12px;
          border-radius: 9999px;
          font-size: 11px;
          font-weight: 700;
          cursor: pointer;
          transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);
          white-space: nowrap;
          backdrop-filter: blur(8px);
          -webkit-backdrop-filter: blur(8px);
        }
    `;

    this.shadowRoot.innerHTML = `
      <style>
        :host {
          display: block;
          box-sizing: border-box;
        }
        ${cardBgStyle}
        .header {
          display: flex;
          justify-content: space-between;
          align-items: flex-start;
          min-height: 44px;
          margin-bottom: 4px;
          position: relative;
          z-index: 20;
        }
        .title-box {
          display: flex;
          flex-direction: column;
          align-items: flex-start;
          gap: 4px;
        }
        .title {
          font-size: 16px;
          font-weight: 700;
          color: var(--primary-text-color, #ffffff);
          line-height: 1.2;
        }
        .pills-row {
          display: flex;
          align-items: center;
          gap: 6px;
          flex-wrap: wrap;
        }
        .header-center {
          position: absolute;
          left: 50%;
          top: 4px;
          transform: translateX(-50%);
          display: flex;
          align-items: center;
          justify-content: center;
          pointer-events: auto;
          z-index: 22;
        }
        .split-pill-btn:hover {
          color: #ffffff;
          border-color: rgba(255, 255, 255, 0.25);
          background: rgba(255, 255, 255, 0.12);
        }
        .split-pill-btn.active.heat {
          background: linear-gradient(135deg, #f97316, #ea580c);
          border-color: #fb923c;
          color: #ffffff;
          box-shadow: 0 2px 10px rgba(249, 115, 22, 0.5);
        }
        .split-pill-btn.active.cool {
          background: linear-gradient(135deg, #38bdf8, #0284c7);
          border-color: #7dd3fc;
          color: #ffffff;
          box-shadow: 0 2px 10px rgba(56, 189, 248, 0.5);
        }
        .split-pill-btn ha-icon {
          --mdc-icon-size: 14px;
        }
        .luxury-pill {
          display: inline-flex;
          align-items: center;
          gap: 5px;
          padding: 2px 8px;
          border-radius: 9999px;
          font-size: 10px;
          font-weight: 700;
          text-transform: uppercase;
          letter-spacing: 0.4px;
        }
        .pulse-dot {
          width: 5px;
          height: 5px;
          border-radius: 50%;
          background: currentColor;
          box-shadow: 0 0 6px currentColor;
        }
        .pill-cyan {
          background: rgba(56, 189, 248, 0.15);
          color: #38bdf8;
          border: 1px solid rgba(56, 189, 248, 0.3);
        }
        .pill-amber {
          background: rgba(251, 191, 36, 0.15);
          color: #fbbf24;
          border: 1px solid rgba(251, 191, 36, 0.3);
        }
        .pill-gray {
          background: rgba(148, 163, 184, 0.15);
          color: #94a3b8;
          border: 1px solid rgba(148, 163, 184, 0.3);
        }
        .pill-gas {
          background: rgba(249, 115, 22, 0.15);
          color: #fb923c;
          border: 1px solid rgba(249, 115, 22, 0.35);
        }
        .pill-electric {
          background: rgba(56, 189, 248, 0.15);
          color: #38bdf8;
          border: 1px solid rgba(56, 189, 248, 0.35);
        }
        .pill-dual {
          background: linear-gradient(135deg, rgba(249, 115, 22, 0.2), rgba(56, 189, 248, 0.2));
          color: #fcd34d;
          border: 1px solid rgba(251, 191, 36, 0.4);
        }
        .header-controls {
          display: flex;
          align-items: center;
          gap: 6px;
          z-index: 21;
        }
        .seg-btn {
          background: transparent;
          border: none;
          color: #94a3b8;
          padding: 4px 8px;
          cursor: pointer;
          border-radius: 9999px;
          display: flex;
          align-items: center;
          justify-content: center;
          font-size: 12px;
          transition: all 0.2s ease;
        }
        .seg-btn:hover { color: white; background: rgba(255, 255, 255, 0.08); }
        .seg-btn.active { background-color: #0284c7; color: white; box-shadow: 0 2px 6px rgba(0, 0, 0, 0.3); }
        .seg-btn ha-icon { --mdc-icon-size: 16px; }
        
        /* 1-to-1 HA Native Circular Slider & Info Geometry (320x320, r=145, stroke=24) */
        .gauge-container {
          position: relative;
          width: 100%;
          max-width: 280px;
          aspect-ratio: 1 / 1;
          margin: 2px auto 0 auto;
          display: flex;
          align-items: center;
          justify-content: center;
          user-select: none;
          touch-action: pan-y;
        }
        .dial-svg {
          width: 100%;
          height: 100%;
          display: block;
          touch-action: pan-y;
          overflow: visible;
          cursor: pointer;
        }
        .dial-meter {
          stroke-width: 24;
          stroke-linecap: round;
          fill: none;
          transition: stroke-dashoffset 0.12s ease, stroke 0.3s ease;
        }
        .dial-knob {
          fill: #ffffff;
          cursor: grab;
          filter: drop-shadow(0 1px 4px rgba(0, 0, 0, 0.5));
          transition: transform 0.1s ease;
        }
        /* Centered Info Block (Matches HA .info) */
        .gauge-center {
          position: absolute;
          top: 0;
          left: 0;
          right: 0;
          bottom: 0;
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          pointer-events: none;
          gap: 6px;
        }
        .dial-sub-text {
          font-size: 15px;
          font-weight: 500;
          line-height: 1.4;
          letter-spacing: 0.1px;
          text-transform: none;
          margin: 0;
          text-align: center;
        }
        .heating-text { color: #fb923c; }
        .cooling-text { color: #38bdf8; }
        .standby-text { color: var(--primary-text-color, #ffffff); }
        .off-text { color: var(--secondary-text-color, #94a3b8); }

        /* HA Native ha-big-number Layout (57px with stacked unit & decimal) */
        .target-temp-val {
          font-size: 57px;
          font-weight: 400;
          line-height: 1.12;
          letter-spacing: -0.25px;
          color: var(--primary-text-color, #ffffff);
          display: flex;
          margin: 0;
          direction: ltr;
        }
        .displayed-value {
          display: inline-flex;
          flex-direction: row;
          align-items: flex-end;
        }
        .addon {
          display: flex;
          flex-direction: column-reverse;
          padding: 4px 0;
          margin-left: 2px;
        }
        .decimal {
          font-size: 0.42em;
          line-height: 1.33;
          min-height: 1.33em;
        }
        .unit {
          font-size: 0.33em;
          line-height: 1.15;
        }
        .current-temp-badge {
          font-size: 15px;
          font-weight: 400;
          line-height: 1.4;
          color: var(--primary-text-color, #e2e8f0);
          background: transparent;
          border: none;
          padding: 0;
          margin: 0;
          display: flex;
          align-items: center;
          gap: 3px;
        }

        /* Bottom Arc Opening Step Buttons (Matches HA .buttons) */
        .step-buttons {
          position: absolute;
          bottom: 8px;
          left: 0;
          right: 0;
          margin: 0 auto;
          gap: 24px;
          display: flex;
          flex-direction: row;
          align-items: center;
          justify-content: center;
          pointer-events: none;
        }
        .step-btn ha-icon {
          --mdc-icon-size: 24px;
        }
        .step-btn:active {
          transform: scale(0.94);
          background: rgba(255, 255, 255, 0.2);
        }

        .disabled-overlay {
          position: absolute;
          inset: 0;
          z-index: 30;
          background: rgba(11, 15, 23, 0.85);
          backdrop-filter: blur(8px);
          -webkit-backdrop-filter: blur(8px);
          display: none;
          align-items: center;
          justify-content: center;
          flex-direction: column;
          gap: 8px;
          color: #f87171;
          font-weight: 700;
          font-size: 13px;
        }
      </style>

      <ha-card id="zone-card">
        <div class="disabled-overlay" id="disabled-overlay">
          <ha-icon icon="mdi:close-circle-outline" style="--mdc-icon-size: 32px;"></ha-icon>
          <span>Zona Esclusa / Bypass</span>
          <button id="re-enable-btn" style="background: rgba(255,255,255,0.1); border: 1px solid rgba(255,255,255,0.2); color: white; padding: 4px 12px; border-radius: 8px; font-size: 11px; font-weight: 600; cursor: pointer; margin-top: 4px;">Riattiva</button>
        </div>

        <div class="header">
          <div class="title-box">
            <div class="title" id="zone-title">Termostato</div>
            <div class="pills-row">
              <div class="luxury-pill pill-cyan" id="mode-pill">
                <span class="pulse-dot"></span>
                <span id="mode-text">Prioritaria</span>
              </div>
              <div class="luxury-pill pill-gas" id="heat-source-pill" style="display: none;">
                <ha-icon id="heat-source-icon" icon="mdi:fire" style="--mdc-icon-size: 13px;"></ha-icon>
                <span id="heat-source-text">Gas</span>
              </div>
            </div>
          </div>

          <div class="header-center">
            <button class="split-pill-btn" id="btn-split-toggle" style="display: none;" title="Split Locale">
              <ha-icon id="split-toggle-icon" icon="mdi:fire"></ha-icon>
              <span id="split-toggle-text">Split</span>
            </button>
          </div>

          <div class="header-controls">
            <div class="segmented-control">
              <button class="seg-btn active" id="seg-primary" title="Prioritaria"><ha-icon icon="mdi:target"></ha-icon></button>
              <button class="seg-btn" id="seg-secondary" title="Secondaria"><ha-icon icon="mdi:link-variant"></ha-icon></button>
              <button class="seg-btn" id="seg-bypass" title="Bypass"><ha-icon icon="mdi:close-circle-outline"></ha-icon></button>
            </div>
          </div>
        </div>

        <!-- 1-to-1 HA Native Circular Slider Geometry (320x320, cx=160, cy=160, r=145, stroke=24) -->
        <div class="gauge-container" id="gauge-container">
          <svg class="dial-svg" id="dial-svg" viewBox="0 0 320 320">
            <defs>
              <filter id="heating-glow" x="-20%" y="-20%" width="140%" height="140%">
                <feDropShadow dx="0" dy="0" stdDeviation="4" flood-color="#f97316" flood-opacity="0.7"/>
              </filter>
              <filter id="cooling-glow" x="-20%" y="-20%" width="140%" height="140%">
                <feDropShadow dx="0" dy="0" stdDeviation="4" flood-color="#38bdf8" flood-opacity="0.7"/>
              </filter>
              <filter id="standby-glow" x="-20%" y="-20%" width="140%" height="140%">
                <feDropShadow dx="0" dy="0" stdDeviation="3" flood-color="#e2e8f0" flood-opacity="0.35"/>
              </filter>
            </defs>
            <!-- 270deg background track: cx=160, cy=160, r=145, stroke-width=24 -->
            <path class="dial-track" id="dial-track" d="M 57.47 262.53 A 145 145 0 1 1 262.53 262.53"></path>
            <!-- Active arc -->
            <path class="dial-meter" id="dial-meter" d="M 57.47 262.53 A 145 145 0 0 1 160 15"></path>
            <!-- Current temperature marker dot on track -->
            <circle id="curr-temp-dot" cx="160" cy="15" r="4" fill="#cbd5e1" opacity="0.85"></circle>
            <!-- Visible Knob inside 24px track -->
            <circle class="dial-knob" id="dial-knob" cx="160" cy="15" r="9" stroke="#ffffff" stroke-width="3"></circle>
            <!-- Transparent Enlarged Hit Area for Touch & Click -->
            <circle id="dial-knob-hit" cx="160" cy="15" r="28" fill="transparent" style="cursor: grab; touch-action: none;"></circle>
          </svg>

          <div class="gauge-center">
            <div class="dial-sub-text standby-text" id="dial-sub-text">Spento</div>
            <div class="target-temp-val">
              <span class="displayed-value">
                <span id="target-temp-int">20</span>
                <span class="addon">
                  <span class="decimal" id="target-temp-dec">,0</span>
                  <span class="unit">°C</span>
                </span>
              </span>
            </div>
            <div class="current-temp-badge">
              <ha-icon icon="mdi:thermometer" style="--mdc-icon-size: 16px; color: ${isClassic ? 'currentColor' : '#38bdf8'};"></ha-icon>
              <span id="current-temp">20,0 °C</span>
            </div>
          </div>

          <div class="step-buttons">
            <button class="step-btn" id="btn-temp-down" title="Diminuisci target (-0.5°C)">
              <ha-icon icon="mdi:minus"></ha-icon>
            </button>
            <button class="step-btn" id="btn-temp-up" title="Aumenta target (+0.5°C)">
              <ha-icon icon="mdi:plus"></ha-icon>
            </button>
          </div>
        </div>
      </ha-card>
    `;

    this.setupLuxuryEventListeners();
  }

  setupClassicEventListeners() {
    const segPrimary = this.shadowRoot.querySelector('#seg-primary');
    const segSecondary = this.shadowRoot.querySelector('#seg-secondary');
    const segBypass = this.shadowRoot.querySelector('#seg-bypass');
    const reEnableBtn = this.shadowRoot.querySelector('#re-enable-btn');

    if (segPrimary) segPrimary.addEventListener('click', (e) => { e.stopPropagation(); this.setZoneMode('primary'); });
    if (segSecondary) segSecondary.addEventListener('click', (e) => { e.stopPropagation(); this.setZoneMode('secondary'); });
    if (segBypass) segBypass.addEventListener('click', (e) => { e.stopPropagation(); this.setZoneMode('bypass'); });
    if (reEnableBtn) reEnableBtn.addEventListener('click', (e) => { e.stopPropagation(); this.setZoneMode('primary'); });

    const btnSplitToggle = this.shadowRoot.querySelector('#btn-split-toggle');
    if (btnSplitToggle) {
      btnSplitToggle.addEventListener('click', (e) => {
        e.stopPropagation();
        this.toggleLocalSplit();
      });
    }
    const btnSplitClassic = this.shadowRoot.querySelector('#btn-split-toggle-classic');
    if (btnSplitClassic) {
      btnSplitClassic.addEventListener('click', (e) => {
        e.stopPropagation();
        this.toggleLocalSplit();
      });
    }
  }

  setupLuxuryEventListeners() {
    this.setupClassicEventListeners();

    // Step buttons [-] and [+]
    const btnDown = this.shadowRoot.querySelector('#btn-temp-down');
    const btnUp = this.shadowRoot.querySelector('#btn-temp-up');
    if (btnDown) btnDown.addEventListener('click', (e) => { e.stopPropagation(); this.stepTemperature(-this.getStep()); });
    if (btnUp) btnUp.addEventListener('click', (e) => { e.stopPropagation(); this.stepTemperature(this.getStep()); });

    // Click/tap directly on SVG track
    const svgDial = this.shadowRoot.querySelector('#dial-svg');
    if (svgDial) {
      svgDial.addEventListener('click', (e) => {
        if (e.target && (e.target.id === 'btn-temp-down' || e.target.id === 'btn-temp-up')) return;
        this.setTempFromPointer(e);
      });
    }

    const knobHit = this.shadowRoot.querySelector('#dial-knob-hit');
    if (knobHit) {
      let startX = 0, startY = 0;
      let isPointerDown = false;

      const onWindowPointerUp = (e) => {
        if (this._onWindowPointerUp) {
          window.removeEventListener('pointerup', this._onWindowPointerUp);
          window.removeEventListener('pointercancel', this._onWindowPointerUp);
          this._onWindowPointerUp = null;
        }
        onPointerEnd(e);
      };

      const onPointerEnd = (e) => {
        if (this._onWindowPointerUp) {
          window.removeEventListener('pointerup', this._onWindowPointerUp);
          window.removeEventListener('pointercancel', this._onWindowPointerUp);
          this._onWindowPointerUp = null;
        }
        if (!isPointerDown && !this._isDragging) return;
        isPointerDown = false;
        if (this._isDragging) {
          this._isDragging = false;
          try { knobHit.releasePointerCapture(e.pointerId); } catch(err) {}
          if (this._dragTargetTemp !== undefined && this._hass && this._config.entity) {
            this._hass.callService("climate", "set_temperature", {
              entity_id: this._config.entity,
              temperature: this._dragTargetTemp
            });
          }
        }
      };

      knobHit.addEventListener('pointerdown', (e) => {
        isPointerDown = true;
        startX = e.clientX;
        startY = e.clientY;
        this._isDragging = false;
      });

      knobHit.addEventListener('pointermove', (e) => {
        if (!isPointerDown) return;
        const dx = e.clientX - startX;
        const dy = e.clientY - startY;
        const dist = Math.sqrt(dx * dx + dy * dy);

        if (!this._isDragging) {
          // If vertical gesture exceeds threshold, abort drag so mobile page scrolls freely
          if (Math.abs(dy) > 8 && Math.abs(dy) > Math.abs(dx)) {
            isPointerDown = false;
            return;
          }
          if (dist > 5) {
            this._isDragging = true;
            try { knobHit.setPointerCapture(e.pointerId); } catch(err) {}
            this._onWindowPointerUp = onWindowPointerUp;
            window.addEventListener('pointerup', onWindowPointerUp);
            window.addEventListener('pointercancel', onWindowPointerUp);
          }
        }

        if (this._isDragging) {
          e.preventDefault();
          this.handlePointerDrag(e);
        }
      });

      knobHit.addEventListener('pointerup', onPointerEnd);
      knobHit.addEventListener('pointercancel', onPointerEnd);
      knobHit.addEventListener('lostpointercapture', onPointerEnd);
    }
  }

  stepTemperature(delta) {
    if (!this._hass || !this._config) return;
    const climateEntity = this._config.entity;
    const climateState = this._hass.states[climateEntity];
    if (!climateState) return;

    const step = this.getStep();
    const decimals = (step.toString().split('.')[1] || '').length;
    const effectiveDelta = (delta === 1 || delta === -1) ? delta * step : (delta || step);
    const minTemp = this._minTemp || 10;
    const maxTemp = this._maxTemp || 30;
    const currentTarget = typeof climateState.attributes.temperature === 'number'
      ? climateState.attributes.temperature
      : (this._targetTemp || 20.0);
    const stepped = parseFloat((Math.round((currentTarget + effectiveDelta) / step) * step).toFixed(decimals));
    const newTarget = Math.min(maxTemp, Math.max(minTemp, stepped));

    this._targetTemp = newTarget;
    this.updateTargetTempDisplay(newTarget);
    this.renderDialArc(newTarget);

    this._hass.callService("climate", "set_temperature", {
      entity_id: climateEntity,
      temperature: newTarget
    });
  }

  setTempFromPointer(e) {
    if (!this._hass || !this._config) return;
    const climateEntity = this._config.entity;
    const svg = this.shadowRoot.querySelector('#dial-svg');
    if (!svg) return;
    const rect = svg.getBoundingClientRect();
    const scaleX = 320 / rect.width;
    const scaleY = 320 / rect.height;
    const px = (e.clientX - rect.left) * scaleX;
    const py = (e.clientY - rect.top) * scaleY;
    const dx = px - 160.0;
    const dy = py - 160.0;

    let angle = Math.atan2(dx, -dy) * (180 / Math.PI);
    if (angle > 135) {
      if (angle > 157.5) angle = -135;
      else angle = 135;
    } else if (angle < -135) {
      if (angle < -157.5) angle = 135;
      else angle = -135;
    }

    const minTemp = this._minTemp || 10;
    const maxTemp = this._maxTemp || 30;
    const step = this.getStep();
    const decimals = (step.toString().split('.')[1] || '').length;
    const pct = Math.max(0, Math.min(1, (angle + 135) / 270));
    let temp = minTemp + pct * (maxTemp - minTemp);
    const stepped = parseFloat((Math.round(temp / step) * step).toFixed(decimals));
    temp = Math.max(minTemp, Math.min(maxTemp, stepped));

    this._targetTemp = temp;
    this.renderDialArc(temp);
    this.updateTargetTempDisplay(temp);

    this._hass.callService("climate", "set_temperature", {
      entity_id: climateEntity,
      temperature: temp
    });
  }

  handlePointerDrag(e) {
    const svg = this.shadowRoot.querySelector('#dial-svg');
    if (!svg) return;
    const rect = svg.getBoundingClientRect();
    const scaleX = 320 / rect.width;
    const scaleY = 320 / rect.height;
    const px = (e.clientX - rect.left) * scaleX;
    const py = (e.clientY - rect.top) * scaleY;

    const dx = px - 160.0;
    const dy = py - 160.0;

    // Clockwise angle where 0 = 12 o'clock (dy < 0)
    let angle = Math.atan2(dx, -dy) * (180 / Math.PI);

    // Bottom gap is from +135 to +180 and -180 to -135
    if (angle > 135) {
      if (angle > 157.5) angle = -135;
      else angle = 135;
    } else if (angle < -135) {
      if (angle < -157.5) angle = 135;
      else angle = -135;
    }

    const minTemp = this._minTemp || 10;
    const maxTemp = this._maxTemp || 30;
    const step = this.getStep();
    const decimals = (step.toString().split('.')[1] || '').length;
    const pct = Math.max(0, Math.min(1, (angle + 135) / 270));
    let temp = minTemp + pct * (maxTemp - minTemp);
    const stepped = parseFloat((Math.round(temp / step) * step).toFixed(decimals));
    temp = Math.max(minTemp, Math.min(maxTemp, stepped));

    this._dragTargetTemp = temp;
    this.renderDialArc(temp);

    this.updateTargetTempDisplay(temp);
  }

  renderDialArc(targetTemp) {
    const minTemp = this._minTemp || 10;
    const maxTemp = this._maxTemp || 30;
    const range = Math.max(maxTemp - minTemp, 1);
    const pct = Math.max(0, Math.min(1, (targetTemp - minTemp) / range));
    const delta = pct * 270.0;
    const alpha = -135.0 + delta;
    const rad = alpha * (Math.PI / 180);

    const cx = 160.0;
    const cy = 160.0;
    const r = 145.0;

    const xt = cx + r * Math.sin(rad);
    const yt = cy - r * Math.cos(rad);

    const meter = this.shadowRoot.querySelector('#dial-meter');
    const knob = this.shadowRoot.querySelector('#dial-knob');
    const knobHit = this.shadowRoot.querySelector('#dial-knob-hit');

    let activeColor = '#e2e8f0'; // Default Standby warm white
    let filterId = 'url(#standby-glow)';

    if (this._isOff) {
      activeColor = '#475569';
      filterId = 'none';
    } else if (this._isCooling) {
      activeColor = '#38bdf8'; // Cooling ice blue
      filterId = 'url(#cooling-glow)';
    } else if (this._isHeating) {
      activeColor = '#f97316'; // Heating flame orange
      filterId = 'url(#heating-glow)';
    }

    if (meter) {
      if (this._isOff) {
        meter.setAttribute('d', '');
      } else if (this._isCooling) {
        // In cooling: sweep counter-clockwise from right (+135deg) to target
        const sweepAngle = (1.0 - pct) * 270.0;
        if (sweepAngle <= 0.5) {
          meter.setAttribute('d', '');
        } else {
          const largeArc = sweepAngle > 180 ? 1 : 0;
          meter.setAttribute('d', `M 262.53 262.53 A 145 145 0 ${largeArc} 0 ${xt.toFixed(2)} ${yt.toFixed(2)}`);
        }
      } else {
        // In heating/standby: sweep clockwise from left (-135deg) to target
        if (delta <= 0.5) {
          meter.setAttribute('d', '');
        } else {
          const largeArc = delta > 180 ? 1 : 0;
          meter.setAttribute('d', `M 57.47 262.53 A 145 145 0 ${largeArc} 1 ${xt.toFixed(2)} ${yt.toFixed(2)}`);
        }
      }
      meter.setAttribute('stroke', activeColor);
      meter.style.filter = (this.getEffectiveStyle() === 'classic') ? 'none' : filterId;
    }

    if (knob) {
      knob.setAttribute('cx', xt.toFixed(2));
      knob.setAttribute('cy', yt.toFixed(2));
      knob.setAttribute('stroke', activeColor);
      if (this._isOff) {
        knob.setAttribute('fill', '#1e293b');
      } else {
        knob.setAttribute('fill', '#ffffff');
      }
    }

    if (knobHit) {
      knobHit.setAttribute('cx', xt.toFixed(2));
      knobHit.setAttribute('cy', yt.toFixed(2));
    }
  }

  renderCurrentTempMarker(currentTemp) {
    const minTemp = this._minTemp || 10;
    const maxTemp = this._maxTemp || 30;
    const range = Math.max(maxTemp - minTemp, 1);
    const pct = Math.max(0, Math.min(1, (currentTemp - minTemp) / range));
    const delta = pct * 270.0;
    const alpha = -135.0 + delta;
    const rad = alpha * (Math.PI / 180);

    const cx = 160.0;
    const cy = 160.0;
    const r = 145.0;

    const xc = cx + r * Math.sin(rad);
    const yc = cy - r * Math.cos(rad);

    const dot = this.shadowRoot.querySelector('#curr-temp-dot');
    if (dot) {
      dot.setAttribute('cx', xc.toFixed(2));
      dot.setAttribute('cy', yc.toFixed(2));
    }
  }

  toggleLocalSplit() {
    if (!this._hass || !this._config) return;
    const climateEntity = this._config.entity;
    const climateState = this._hass.states[climateEntity];
    if (!climateState) return;
    const splitEntity = climateState.attributes.split_climate_entity;
    if (!splitEntity) return;

    const masterEntity = typeof findMasterEntity === 'function' ? findMasterEntity(this._hass) : null;
    const isMasterOn = Boolean(masterEntity && this._hass.states[masterEntity] && this._hass.states[masterEntity].state === 'on');
    if (isMasterOn) {
      // Guard: when master is active, individual manual split override is disabled
      return;
    }

    const masterMode = typeof getMasterHVACMode === 'function' ? getMasterHVACMode(this._hass) : 'heat';
    const splitState = this._hass.states[splitEntity];
    const isSplitOn = (splitState && splitState.state !== 'off') || Boolean(climateState.attributes.split_active) || Boolean(climateState.attributes.split_manual_on);
    const targetHvac = isSplitOn ? 'off' : (masterMode === 'cool' ? 'cool' : 'heat');

    // Turn both the virtual thermostat zone and the split entity to target HVAC mode
    this._hass.callService("climate", "set_hvac_mode", {
      entity_id: climateEntity,
      hvac_mode: targetHvac
    });
    this._hass.callService("climate", "set_hvac_mode", {
      entity_id: splitEntity,
      hvac_mode: targetHvac
    });
  }

  setHvacMode(mode) {
    if (!this._hass) return;
    const climateEntity = this._config.entity;
    if (!climateEntity) return;
    this._hass.callService("climate", "set_hvac_mode", {
      entity_id: climateEntity,
      hvac_mode: mode
    });
  }

  renderMinimizedView(title, currentTemp) {
    const curStr = (typeof currentTemp === 'number') ? `${this.formatTemperature(currentTemp)} °C` : '--°C';
    this.shadowRoot.innerHTML = `
      <style>
        ha-card {
          padding: 12px 16px;
          border-radius: var(--ha-card-border-radius, 14px);
          background: rgba(30, 41, 59, 0.6);
          border: 1px dashed rgba(255, 255, 255, 0.12);
          display: flex;
          align-items: center;
          justify-content: space-between;
          color: #94a3b8;
          font-size: 12px;
          box-sizing: border-box;
        }
        .min-left { display: flex; align-items: center; gap: 8px; }
        .min-tag {
          font-size: 10px;
          text-transform: uppercase;
          background: rgba(148, 163, 184, 0.15);
          color: #94a3b8;
          padding: 2px 6px;
          border-radius: 4px;
          font-weight: 700;
        }
        .min-temp { font-size: 14px; font-weight: 700; color: #cbd5e1; }
      </style>
      <ha-card>
        <div class="min-left">
          <ha-icon icon="mdi:snowflake-off" style="--mdc-icon-size: 18px; color: #64748b;"></ha-icon>
          <span style="font-weight: 600;">${title}</span>
          <span class="min-tag">${getTranslation(this._hass, 'winter_only') || 'Solo Inverno'}</span>
        </div>
        <div class="min-temp">${curStr}</div>
      </ha-card>
    `;
    this._rendered = false;
  }

  setZoneMode(mode) {
    if (!this._hass) return;
    const climateEntity = this._config.entity;
    let switchEntity = this._config.switch;
    if (!switchEntity || !this._hass.states[switchEntity]) {
      const discovered = autoDiscoverSwitch(this._hass, climateEntity);
      if (discovered) switchEntity = discovered;
    }
    if (!switchEntity || !this._hass.states[switchEntity]) return;

    this._tempSwitchState = mode;
    this.updateCard();

    if (this._switchTimeout) clearTimeout(this._switchTimeout);
    this._switchTimeout = setTimeout(() => {
      this._tempSwitchState = undefined;
      this.updateCard();
    }, 1000);

    if (switchEntity.startsWith('select.')) {
      this._hass.callService("select", "select_option", {
        entity_id: switchEntity,
        option: mode
      });
    } else if (switchEntity.startsWith('switch.')) {
      if (mode === "bypass" || mode === "off") {
        this._hass.callService("switch", "turn_off", { entity_id: switchEntity });
      } else {
        this._hass.callService("switch", "turn_on", { entity_id: switchEntity });
      }
    }
  }

  updateCard() {
    if (!this._hass || !this._hass.states) return;
    if (!this._config) return;

    const climateEntity = this._config.entity;
    let switchEntity = this._config.switch;

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
      return;
    }

    let displayTitle = this._config.title || climateState.attributes.friendly_name || climateEntity;
    if (displayTitle) {
      displayTitle = displayTitle.replace(/^Virtual Thermostats VT /i, '').replace(/^Heating Zones(?: Zone)? /i, '');
    }

    const canCool = (climateState.attributes.can_cool !== false);
    const masterMode = typeof getMasterHVACMode === 'function' ? getMasterHVACMode(this._hass) : 'heat';
    const isSummer = (masterMode === 'cool');
    const curTempVal = typeof climateState.attributes.current_temperature === 'number' ? climateState.attributes.current_temperature : climateState.attributes.temperature;

    // Conditional visibility in summer mode if room cannot cool
    if (isSummer && !canCool) {
      if (this._config.hide_if_cannot_cool) {
        this.style.display = 'none';
        return;
      }
      if (this._config.minimize_if_cannot_cool) {
        this.style.display = '';
        this.renderMinimizedView(displayTitle, curTempVal);
        return;
      }
    }
    this.style.display = '';

    if (!this._rendered) {
      this.renderStructure();
    }

    const titleEl = this.shadowRoot.querySelector('#zone-title');
    if (titleEl) {
      titleEl.textContent = displayTitle;
    }

    let actualSwitchState = "primary";
    if (this._tempSwitchState !== undefined) {
      actualSwitchState = this._tempSwitchState;
    } else if (switchState && switchState.state) {
      actualSwitchState = switchState.state;
    } else if (climateState.attributes && climateState.attributes.zone_mode) {
      actualSwitchState = climateState.attributes.zone_mode;
    }

    // Local Split Toggle Button (In Header next to Title)
    const btnSplitToggle = this.shadowRoot.querySelector('#btn-split-toggle');
    const splitToggleIcon = this.shadowRoot.querySelector('#split-toggle-icon');
    const splitEntity = climateState.attributes.split_climate_entity;

    const masterEntity = typeof findMasterEntity === 'function' ? findMasterEntity(this._hass) : null;
    const isMasterOn = Boolean(masterEntity && this._hass.states[masterEntity] && this._hass.states[masterEntity].state === 'on');

    if (btnSplitToggle) {
      if (!splitEntity) {
        btnSplitToggle.style.display = 'none';
      } else {
        btnSplitToggle.style.display = 'inline-flex';
        const splitState = this._hass.states[splitEntity];
        const isSplitOn = (splitState && splitState.state !== 'off') || Boolean(climateState.attributes.split_active) || Boolean(climateState.attributes.split_manual_on);
        const iconName = isSummer ? 'mdi:snowflake' : 'mdi:fire';
        if (splitToggleIcon) splitToggleIcon.setAttribute('icon', iconName);

        if (isMasterOn) {
          btnSplitToggle.disabled = true;
          btnSplitToggle.style.pointerEvents = 'none';
          btnSplitToggle.style.opacity = '0.45';
          btnSplitToggle.style.cursor = 'not-allowed';
          btnSplitToggle.setAttribute('title', 'Gestito da Impianto Master (Controllo manuale disabilitato)');
          btnSplitToggle.className = isSplitOn ? (isSummer ? 'split-pill-btn active cool disabled' : 'split-pill-btn active heat disabled') : 'split-pill-btn disabled';
        } else {
          btnSplitToggle.disabled = false;
          btnSplitToggle.style.pointerEvents = 'auto';
          btnSplitToggle.style.opacity = '1';
          btnSplitToggle.style.cursor = 'pointer';
          if (isSplitOn) {
            btnSplitToggle.className = isSummer ? 'split-pill-btn active cool' : 'split-pill-btn active heat';
            btnSplitToggle.setAttribute('title', isSummer ? 'Split Acceso (Clicca per spegnere)' : 'Split Acceso (Clicca per spegnere)');
          } else {
            btnSplitToggle.className = 'split-pill-btn';
            btnSplitToggle.setAttribute('title', isSummer ? 'Accendi Split Climatizzazione' : 'Accendi Split Riscaldamento');
          }
        }
      }
    }

    // Classic Header Split Toggle
    const btnSplitClassic = this.shadowRoot.querySelector('#btn-split-toggle-classic');
    const splitIconClassic = this.shadowRoot.querySelector('#split-toggle-icon-classic');
    if (btnSplitClassic) {
      if (!splitEntity) {
        btnSplitClassic.style.display = 'none';
      } else {
        btnSplitClassic.style.display = 'inline-flex';
        const splitState = this._hass.states[splitEntity];
        const isSplitOn = (splitState && splitState.state !== 'off') || Boolean(climateState.attributes.split_active) || Boolean(climateState.attributes.split_manual_on);
        const iconName = isSummer ? 'mdi:snowflake' : 'mdi:fire';
        if (splitIconClassic) splitIconClassic.setAttribute('icon', iconName);

        if (isMasterOn) {
          btnSplitClassic.disabled = true;
          btnSplitClassic.style.pointerEvents = 'none';
          btnSplitClassic.style.opacity = '0.45';
          btnSplitClassic.style.cursor = 'not-allowed';
          btnSplitClassic.setAttribute('title', 'Gestito da Impianto Master (Controllo manuale disabilitato)');
          btnSplitClassic.className = isSplitOn ? (isSummer ? 'split-pill-btn active cool disabled' : 'split-pill-btn active heat disabled') : 'split-pill-btn disabled';
        } else {
          btnSplitClassic.disabled = false;
          btnSplitClassic.style.pointerEvents = 'auto';
          btnSplitClassic.style.opacity = '1';
          btnSplitClassic.style.cursor = 'pointer';
          if (isSplitOn) {
            btnSplitClassic.className = isSummer ? 'split-pill-btn active cool' : 'split-pill-btn active heat';
            btnSplitClassic.setAttribute('title', isSummer ? 'Split Acceso (Clicca per spegnere)' : 'Split Acceso (Clicca per spegnere)');
          } else {
            btnSplitClassic.className = 'split-pill-btn';
            btnSplitClassic.setAttribute('title', isSummer ? 'Accendi Split Climatizzazione' : 'Accendi Split Riscaldamento');
          }
        }
      }
    }

    // Segmented buttons
    const segPrimary = this.shadowRoot.querySelector('#seg-primary');
    const segSecondary = this.shadowRoot.querySelector('#seg-secondary');
    const segBypass = this.shadowRoot.querySelector('#seg-bypass');
    if (segPrimary) segPrimary.className = (actualSwitchState === "primary" || actualSwitchState === "on") ? "seg-btn active" : "seg-btn";
    if (segSecondary) segSecondary.className = (actualSwitchState === "secondary") ? "seg-btn active" : "seg-btn";
    if (segBypass) segBypass.className = (actualSwitchState === "bypass" || actualSwitchState === "off") ? "seg-btn active" : "seg-btn";

    // Mode Pill
    const modePill = this.shadowRoot.querySelector('#mode-pill');
    const modeText = this.shadowRoot.querySelector('#mode-text');
    if (modePill && modeText) {
      if (actualSwitchState === "secondary") {
        modePill.className = "luxury-pill pill-gray";
        modeText.textContent = getTranslation(this._hass, 'secondary');
      } else if (actualSwitchState === "bypass" || actualSwitchState === "off") {
        modePill.className = "luxury-pill pill-gray";
        modeText.textContent = "Bypass";
      } else {
        modePill.className = "luxury-pill pill-cyan";
        modeText.textContent = getTranslation(this._hass, 'primary');
      }
    }

    // Disabled overlay
    const overlay = this.shadowRoot.querySelector('#disabled-overlay');
    if (overlay) {
      overlay.style.display = (actualSwitchState === "bypass" || actualSwitchState === "off") ? "flex" : "none";
    }

    // Evaluate active heating source for both Classic and Luxury styles
    let heatSource = climateState.attributes.active_heating_source;
    const isHeatingActive = (climateState.attributes.hvac_action === "heating" || Boolean(climateState.attributes.split_active));
    if (!heatSource && isHeatingActive) {
      const splitActive = Boolean(climateState.attributes.split_active);
      const hydronicSuppressed = Boolean(climateState.attributes.split_hydronic_suppressed);
      if (splitActive && !hydronicSuppressed) {
        heatSource = "dual";
      } else if (splitActive) {
        heatSource = "electric";
      } else if (climateState.attributes.hvac_action === "heating") {
        heatSource = "gas";
      } else {
        heatSource = "none";
      }
    }

    const sourcePill = this.shadowRoot.querySelector('#heat-source-pill');
    const sourceIcon = this.shadowRoot.querySelector('#heat-source-icon');
    const sourceText = this.shadowRoot.querySelector('#heat-source-text');

    if (sourcePill && sourceIcon && sourceText) {
      const isCardDisabled = (actualSwitchState === "bypass" || actualSwitchState === "off" || climateState.state === "off");
      if (!isCardDisabled && isHeatingActive && heatSource && heatSource !== "none") {
        sourcePill.style.display = "inline-flex";
        sourcePill.classList.remove('pill-gas', 'pill-electric', 'pill-dual');
        if (heatSource === "electric") {
          sourcePill.classList.add('pill-electric');
          sourceIcon.icon = "mdi:lightning-bolt";
          sourceIcon.style.color = "#38bdf8";
          sourceText.textContent = getTranslation(this._hass, 'heat_source_electric');
        } else if (heatSource === "dual") {
          sourcePill.classList.add('pill-dual');
          sourceIcon.icon = "mdi:lightning-bolt-circle";
          sourceIcon.style.color = "#fcd34d";
          sourceText.textContent = getTranslation(this._hass, 'heat_source_dual');
        } else {
          sourcePill.classList.add('pill-gas');
          sourceIcon.icon = "mdi:fire";
          sourceIcon.style.color = "#fb923c";
          sourceText.textContent = getTranslation(this._hass, 'heat_source_gas');
        }
      } else {
        sourcePill.style.display = "none";
      }
    }

    const isClassic = (this.getEffectiveStyle() === 'classic');

    // Luxury Mode: State Evaluations
    const hvacAction = climateState.attributes.hvac_action;
    const hvacMode = climateState.state;

    this._isOff = (actualSwitchState === "bypass" || actualSwitchState === "off" || hvacMode === "off");
    this._isCooling = !this._isOff && (hvacAction === "cooling" || hvacMode === "cool");
    this._isHeating = !this._isOff && !this._isCooling && (hvacAction === "heating");
    this._isStandby = !this._isOff && !this._isHeating && !this._isCooling;

    this._minTemp = climateState.attributes.min_temp !== undefined ? climateState.attributes.min_temp : 10;
    this._maxTemp = climateState.attributes.max_temp !== undefined ? climateState.attributes.max_temp : 30;

    const targetTemp = typeof climateState.attributes.temperature === 'number' ? climateState.attributes.temperature : 20.0;
    const currentTemp = typeof climateState.attributes.current_temperature === 'number' ? climateState.attributes.current_temperature : targetTemp;

    this._targetTemp = targetTemp;
    this._currentTemp = currentTemp;

    // Only update dial visually from HA state if user is NOT currently dragging
    if (!this._isDragging) {
      this.updateTargetTempDisplay(targetTemp);
      this.renderDialArc(targetTemp);
    }

    const currentEl = this.shadowRoot.querySelector('#current-temp');
    if (currentEl) currentEl.textContent = this.formatTemperature(currentTemp) + " °C";

    this.renderCurrentTempMarker(currentTemp);

    const card = this.shadowRoot.querySelector('#zone-card');
    if (card) {
      card.classList.remove('heating-aura', 'cooling-aura', 'idle-aura');
      if (this._isHeating) {
        card.classList.add('heating-aura');
      } else if (this._isCooling) {
        card.classList.add('cooling-aura');
      } else if (this._isStandby) {
        card.classList.add('idle-aura');
      }
    }

    const subText = this.shadowRoot.querySelector('#dial-sub-text');
    if (subText) {
      if (this._isOff) {
        subText.className = "dial-sub-text off-text";
        subText.textContent = getTranslation(this._hass, 'off') || "Spento";
      } else if (this._isCooling) {
        subText.className = "dial-sub-text cooling-text";
        subText.textContent = "In Raffrescamento";
      } else if (this._isHeating) {
        subText.className = "dial-sub-text heating-text";
        if (heatSource === "electric") {
          subText.textContent = "Riscaldamento (" + (getTranslation(this._hass, 'heat_source_electric') || "Split") + ")";
        } else if (heatSource === "dual") {
          subText.textContent = "Riscaldamento (" + (getTranslation(this._hass, 'heat_source_dual') || "Gas + Split") + ")";
        } else {
          subText.textContent = "Riscaldamento (" + (getTranslation(this._hass, 'heat_source_gas') || "Gas") + ")";
        }
      } else {
        subText.className = "dial-sub-text standby-text";
        subText.textContent = getTranslation(this._hass, 'idle') || "In attesa";
      }
    }

    // Humidity
    const humEl = this.shadowRoot.querySelector('#humidity-val');
    const humBox = this.shadowRoot.querySelector('#humidity-metric');
    if (typeof climateState.attributes.current_humidity === 'number') {
      if (humEl) humEl.textContent = climateState.attributes.current_humidity + "%";
      if (humBox) humBox.style.display = "inline-flex";
    }

    // Valve Telemetry
    const valveEl = this.shadowRoot.querySelector('#valve-val');
    if (valveEl) {
      if (typeof climateState.attributes.valve_position === 'number') {
        valveEl.textContent = "Valvola " + Math.round(climateState.attributes.valve_position) + "%";
        valveEl.style.color = "#38bdf8";
      } else if (this._isHeating) {
        if (heatSource === "electric") {
          valveEl.textContent = "Attivo (Split/PDC)";
          valveEl.style.color = "#38bdf8";
        } else if (heatSource === "dual") {
          valveEl.textContent = "Attivo (Gas + Split)";
          valveEl.style.color = "#fcd34d";
        } else {
          valveEl.textContent = "Attivo (Gas)";
          valveEl.style.color = "#f97316";
        }
      } else if (this._isCooling) {
        valveEl.textContent = "Raffrescamento";
        valveEl.style.color = "#38bdf8";
      } else {
        valveEl.textContent = "Standby";
        valveEl.style.color = "#94a3b8";
      }
    }
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
    if (!this._config) return;
    
    // Only build DOM once — prevent focus loss on every keystroke
    if (this.shadowRoot && this.shadowRoot.querySelector('.card-editor-container')) {
        // Just update values if already built
        const titleInput = this.shadowRoot.querySelector('#card-title-input');
        if (titleInput && document.activeElement !== titleInput && this.shadowRoot.activeElement !== titleInput) {
            titleInput.value = this._config.title || '';
        }
        if (this._climatePicker) this._climatePicker.value = this._config.entity || '';
        if (this._switchPicker) this._switchPicker.value = this._config.switch || '';
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
    container.className = 'card-editor-container';

    // Title Row
    const titleRow = document.createElement('div');
    titleRow.className = 'form-row';
    const titleLabel = document.createElement('label');
    titleLabel.id = 'title-label';
    titleLabel.textContent = 'Titolo Personalizzato (Opzionale)';
    const titleInput = document.createElement('input');
    titleInput.type = 'text';
    titleInput.id = 'card-title-input';
    titleInput.value = this._config.title || '';
    titleInput.addEventListener('input', (e) => this._updateConfig('title', e.target.value));
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

    // Card Style Picker Row
    const styleRow = document.createElement('div');
    styleRow.className = 'form-row';
    const styleLabel = document.createElement('label');
    styleLabel.id = 'style-label';
    styleLabel.textContent = 'Stile Grafico Card';
    const styleSelect = document.createElement('select');
    styleSelect.id = 'card-style-select';
    styleSelect.style.padding = '10px';
    styleSelect.style.borderRadius = '4px';
    styleSelect.style.border = '1px solid var(--divider-color)';
    styleSelect.style.background = 'var(--card-background-color)';
    styleSelect.style.color = 'var(--primary-text-color)';
    styleSelect.style.fontSize = '14px';
    styleSelect.innerHTML = `
      <option value="luxury">Luxury Vector Arc (Nuovo)</option>
      <option value="classic">Standard Home Assistant (Classico)</option>
    `;
    styleSelect.value = this._config.card_style || this._config.style || 'luxury';
    styleSelect.addEventListener('change', (e) => {
      this._updateConfig('card_style', e.target.value);
    });
    styleRow.appendChild(styleLabel);
    styleRow.appendChild(styleSelect);
    container.appendChild(styleRow);

    // Summer Non-Cooling Visibility Options
    const summerRow = document.createElement('div');
    summerRow.className = 'form-row';
    summerRow.innerHTML = `
      <label style="display: flex; align-items: center; gap: 8px; cursor: pointer; margin-bottom: 8px;">
        <input type="checkbox" id="chk-hide-non-cooling" ${this._config.hide_if_cannot_cool ? 'checked' : ''}>
        <span>${getTranslation(this._hass, 'hide_non_cooling') || 'Nascondi card in modalità Raffrescamento se non climatizzata'}</span>
      </label>
      <label style="display: flex; align-items: center; gap: 8px; cursor: pointer;">
        <input type="checkbox" id="chk-min-non-cooling" ${this._config.minimize_if_cannot_cool ? 'checked' : ''}>
        <span>${getTranslation(this._hass, 'minimize_non_cooling') || 'Minimizza card in modalità Raffrescamento se non climatizzata'}</span>
      </label>
    `;
    summerRow.querySelector('#chk-hide-non-cooling').addEventListener('change', (e) => {
      this._updateConfig('hide_if_cannot_cool', e.target.checked);
    });
    summerRow.querySelector('#chk-min-non-cooling').addEventListener('change', (e) => {
      this._updateConfig('minimize_if_cannot_cool', e.target.checked);
    });
    container.appendChild(summerRow);

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

function getActiveMzCardStyle() {
  return localStorage.getItem('mz_card_style') || 'luxury';
}

/* ==================== STATUS (BUTTON-STYLE MASTER SWITCH) CARD CLASS ==================== */
/* ==================== MULTIZONE STATUS CARD ==================== */
