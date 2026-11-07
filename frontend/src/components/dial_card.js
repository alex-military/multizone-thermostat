class MultizoneThermostatDialCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: 'open' });
    this._rendered = false;
    this._childCard = null;
    this._helpers = null;
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
  }

  set hass(hass) {
    this._hass = hass;
    if (this._childCard) {
      this._childCard.hass = hass;
    }
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
      if (newStyle === 'classic' && !this._helpers) {
        this.loadHelpers();
      }
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

    if (newStyle === "classic" && !this._helpers) {
      this.loadHelpers();
    }

    if (!this._rendered || prevStyle !== newStyle) {
      this.renderStructure();
    }
    this.updateCard();
  }

  async loadHelpers() {
    try {
      this._helpers = await window.loadCardHelpers();
      if (this.getEffectiveStyle() === "classic") {
        this.createChildCard();
      }
    } catch (err) {
      console.error("Errore nel caricamento dei card helpers di Home Assistant:", err);
    }
  }

  createChildCard() {
    if (!this._helpers || !this._config) return;
    const cardConfig = {
      type: "thermostat",
      entity: this._config.entity,
      name: " ",
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

    if (isClassic) {
      this.renderClassicStructure(radius);
    } else {
      this.renderLuxuryStructure(radius);
    }
    this._rendered = true;
  }

  renderClassicStructure(radius) {
    this.shadowRoot.innerHTML = `
      <style>
        :host {
          display: block;
          box-sizing: border-box;
        }
        ha-card {
          padding: 16px 14px;
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
          box-sizing: border-box;
        }
        .header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 8px;
          position: relative;
          z-index: 20;
        }
        .title {
          font-size: 16px;
          font-weight: 700;
          color: var(--primary-text-color, #ffffff);
        }
        .segmented-control {
          display: flex;
          align-items: center;
          background: var(--card-background-color, #202b38);
          border: 1px solid var(--divider-color, rgba(255, 255, 255, 0.15));
          border-radius: 10px;
          padding: 2px;
          gap: 2px;
        }
        .seg-btn {
          background: transparent;
          border: none;
          color: #94a3b8;
          padding: 5px 9px;
          cursor: pointer;
          border-radius: 8px;
          display: flex;
          align-items: center;
          justify-content: center;
          font-size: 12px;
          transition: all 0.2s ease;
        }
        .seg-btn:hover { color: white; background: rgba(255, 255, 255, 0.08); }
        .seg-btn.active { background-color: #0284c7; color: white; box-shadow: 0 2px 6px rgba(0, 0, 0, 0.3); }
        .seg-btn ha-icon { --mdc-icon-size: 16px; }
        #card-body { position: relative; width: 100%; }
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
          <div class="title" id="zone-title">Termostato</div>
          <div class="segmented-control">
            <button class="seg-btn active" id="seg-primary" title="Prioritaria"><ha-icon icon="mdi:target"></ha-icon></button>
            <button class="seg-btn" id="seg-secondary" title="Secondaria"><ha-icon icon="mdi:link-variant"></ha-icon></button>
            <button class="seg-btn" id="seg-bypass" title="Bypass"><ha-icon icon="mdi:close-circle-outline"></ha-icon></button>
          </div>
        </div>
        <div id="card-body"></div>
      </ha-card>
    `;

    this.setupClassicEventListeners();
    const body = this.shadowRoot.querySelector('#card-body');
    if (body) {
      body.innerHTML = '';
      if (this._childCard) {
        if (this._hass) this._childCard.hass = this._hass;
        body.appendChild(this._childCard);
      } else if (this._helpers) {
        this.createChildCard();
      } else {
        this.loadHelpers();
      }
    }
  }

  renderLuxuryStructure(radius) {
    this.shadowRoot.innerHTML = `
      <style>
        :host {
          display: block;
          box-sizing: border-box;
        }
        ha-card {
          padding: 18px 16px 14px 16px;
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
        .header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 2px;
          position: relative;
          z-index: 20;
        }
        .title-box {
          display: flex;
          flex-direction: column;
          gap: 3px;
          max-width: 65%;
        }
        .title {
          font-size: 16px;
          font-weight: 800;
          color: #ffffff;
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
          letter-spacing: -0.2px;
          line-height: 1.2;
        }
        .luxury-pill {
          display: inline-flex;
          align-items: center;
          gap: 5px;
          padding: 2px 8px;
          border-radius: 9999px;
          font-size: 10px;
          font-weight: 700;
          letter-spacing: 0.3px;
          text-transform: uppercase;
          align-self: flex-start;
        }
        .pill-cyan {
          background: rgba(14, 165, 233, 0.15);
          color: #38bdf8;
          border: 1px solid rgba(14, 165, 233, 0.35);
        }
        .pill-gray {
          background: rgba(148, 163, 184, 0.12);
          color: #94a3b8;
          border: 1px solid rgba(148, 163, 184, 0.25);
        }
        .pulse-dot {
          width: 5px;
          height: 5px;
          border-radius: 50%;
          background: currentColor;
          box-shadow: 0 0 6px currentColor;
        }
        .segmented-control {
          display: flex;
          align-items: center;
          background: rgba(15, 23, 42, 0.85);
          border: 1px solid rgba(255, 255, 255, 0.1);
          border-radius: 12px;
          padding: 2px;
          gap: 2px;
          z-index: 21;
        }
        .seg-btn {
          background: transparent;
          border: none;
          color: #94a3b8;
          padding: 5px 9px;
          cursor: pointer;
          border-radius: 8px;
          display: flex;
          align-items: center;
          justify-content: center;
          font-size: 12px;
          transition: all 0.2s ease;
        }
        .seg-btn:hover { color: white; background: rgba(255, 255, 255, 0.08); }
        .seg-btn.active { background-color: #0284c7; color: white; box-shadow: 0 2px 6px rgba(0, 0, 0, 0.3); }
        .seg-btn ha-icon { --mdc-icon-size: 16px; }
        
        /* Enlarged Radial Arc Gauge */
        .gauge-container {
          position: relative;
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          margin: 4px auto;
          width: 100%;
          max-width: 300px;
          user-select: none;
          touch-action: pan-y;
        }
        .dial-svg {
          width: 280px;
          height: 260px;
          max-width: 100%;
          touch-action: pan-y;
          overflow: visible;
        }
        .dial-track {
          stroke: rgba(255, 255, 255, 0.07);
          stroke-width: 13;
          stroke-linecap: round;
          fill: none;
        }
        .dial-meter {
          stroke-width: 13;
          stroke-linecap: round;
          fill: none;
          transition: stroke-dashoffset 0.1s ease, stroke 0.3s ease;
        }
        .dial-knob {
          fill: #ffffff;
          cursor: grab;
          filter: drop-shadow(0 2px 8px rgba(0, 0, 0, 0.6));
          transition: transform 0.1s ease;
        }
        .gauge-center {
          position: absolute;
          top: 15px;
          left: 0;
          right: 0;
          bottom: 25px;
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          pointer-events: none;
        }
        .target-label {
          font-size: 11px;
          font-weight: 700;
          text-transform: uppercase;
          letter-spacing: 1.5px;
          color: #94a3b8;
          margin-bottom: 2px;
        }
        .target-temp-val {
          font-size: 44px;
          font-weight: 900;
          color: #ffffff;
          display: flex;
          align-items: baseline;
          line-height: 1;
          margin: 2px 0;
          letter-spacing: -1.5px;
        }
        .unit {
          font-size: 20px;
          font-weight: 700;
          color: #94a3b8;
          margin-left: 2px;
        }
        .current-temp-badge {
          font-size: 13px;
          font-weight: 700;
          color: #cbd5e1;
          background: rgba(15, 23, 42, 0.85);
          border: 1px solid rgba(255, 255, 255, 0.12);
          padding: 3px 12px;
          border-radius: 9999px;
          margin-top: 6px;
          display: flex;
          align-items: center;
          gap: 5px;
        }
        .dial-sub-text {
          font-size: 11px;
          font-weight: 700;
          letter-spacing: 0.4px;
          text-transform: uppercase;
          margin-top: 8px;
        }
        .heating-text { color: #fb923c; }
        .cooling-text { color: #38bdf8; }
        .standby-text { color: #cbd5e1; }
        .off-text { color: #64748b; }

        /* Card Footer Metrics */
        .bottom-bar {
          display: flex;
          align-items: center;
          justify-content: space-between;
          padding-top: 8px;
          border-top: 1px solid rgba(255, 255, 255, 0.06);
          position: relative;
          z-index: 20;
          font-size: 11px;
          font-weight: 600;
          color: #94a3b8;
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
            <div class="luxury-pill pill-cyan" id="mode-pill">
              <span class="pulse-dot"></span>
              <span id="mode-text">Prioritaria</span>
            </div>
          </div>

          <div class="segmented-control">
            <button class="seg-btn active" id="seg-primary" title="Prioritaria"><ha-icon icon="mdi:target"></ha-icon></button>
            <button class="seg-btn" id="seg-secondary" title="Secondaria"><ha-icon icon="mdi:link-variant"></ha-icon></button>
            <button class="seg-btn" id="seg-bypass" title="Bypass"><ha-icon icon="mdi:close-circle-outline"></ha-icon></button>
          </div>
        </div>

        <!-- Center Radial Arc Gauge with Drag & Mobile Scroll Guard -->
        <div class="gauge-container" id="gauge-container">
          <svg class="dial-svg" id="dial-svg" viewBox="0 0 300 270">
            <defs>
              <filter id="heating-glow" x="-20%" y="-20%" width="140%" height="140%">
                <feDropShadow dx="0" dy="0" stdDeviation="5" flood-color="#f97316" flood-opacity="0.8"/>
              </filter>
              <filter id="cooling-glow" x="-20%" y="-20%" width="140%" height="140%">
                <feDropShadow dx="0" dy="0" stdDeviation="5" flood-color="#38bdf8" flood-opacity="0.8"/>
              </filter>
              <filter id="standby-glow" x="-20%" y="-20%" width="140%" height="140%">
                <feDropShadow dx="0" dy="0" stdDeviation="3" flood-color="#e2e8f0" flood-opacity="0.4"/>
              </filter>
            </defs>
            <!-- 270deg background track: cx=150, cy=145, r=115 -->
            <path class="dial-track" id="dial-track" d="M 68.68 226.32 A 115 115 0 1 1 231.32 226.32"></path>
            <!-- Active arc (heat = clockwise from left, cool = counter-clockwise from right) -->
            <path class="dial-meter" id="dial-meter" d="M 68.68 226.32 A 115 115 0 0 1 150 30"></path>
            <!-- Current temperature marker dot on track -->
            <circle id="curr-temp-dot" cx="150" cy="30" r="4" fill="#cbd5e1" opacity="0.9"></circle>
            <!-- Visible Knob -->
            <circle class="dial-knob" id="dial-knob" cx="150" cy="30" r="12" stroke="#e2e8f0" stroke-width="4"></circle>
            <!-- Transparent Enlarged Hit Area for Touch (Mobile Scroll Guard) -->
            <circle id="dial-knob-hit" cx="150" cy="30" r="28" fill="transparent" style="cursor: grab; touch-action: none;"></circle>
          </svg>

          <div class="gauge-center">
            <span class="target-label">Target</span>
            <div class="target-temp-val">
              <span id="target-temp">20.0</span><span class="unit">°C</span>
            </div>
            <div class="current-temp-badge">
              <ha-icon icon="mdi:thermometer" style="--mdc-icon-size: 16px; color: #38bdf8;"></ha-icon>
              <span id="current-temp">20.0°C</span>
            </div>
            <div class="dial-sub-text standby-text" id="dial-sub-text">● Standby</div>
          </div>
        </div>

        <!-- Bottom Bar Telemetry -->
        <div class="bottom-bar">
          <div id="humidity-metric" style="display: none; align-items: center; gap: 4px;">
            <ha-icon icon="mdi:water-percent" style="--mdc-icon-size: 16px; color: #38bdf8;"></ha-icon>
            <span id="humidity-val">--%</span>
          </div>
          <div style="margin-left: auto; display: flex; align-items: center; gap: 6px;">
            <span id="valve-val">Standby</span>
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
  }

  setupLuxuryEventListeners() {
    this.setupClassicEventListeners();

    const knobHit = this.shadowRoot.querySelector('#dial-knob-hit');
    if (knobHit) {
      let startX = 0, startY = 0;
      let isPointerDown = false;

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
          }
        }

        if (this._isDragging) {
          e.preventDefault();
          this.handlePointerDrag(e);
        }
      });

      const onPointerEnd = (e) => {
        if (!isPointerDown) return;
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

      knobHit.addEventListener('pointerup', onPointerEnd);
      knobHit.addEventListener('pointercancel', onPointerEnd);
    }
  }

  handlePointerDrag(e) {
    const svg = this.shadowRoot.querySelector('#dial-svg');
    if (!svg) return;
    const rect = svg.getBoundingClientRect();
    const scaleX = 300 / rect.width;
    const scaleY = 270 / rect.height;
    const px = (e.clientX - rect.left) * scaleX;
    const py = (e.clientY - rect.top) * scaleY;

    const dx = px - 150.0;
    const dy = py - 145.0;

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
    const pct = Math.max(0, Math.min(1, (angle + 135) / 270));
    let temp = minTemp + pct * (maxTemp - minTemp);
    temp = Math.round(temp * 2) / 2; // Step 0.5
    temp = Math.max(minTemp, Math.min(maxTemp, temp));

    this._dragTargetTemp = temp;
    this.renderDialArc(temp);

    const targetEl = this.shadowRoot.querySelector('#target-temp');
    if (targetEl) targetEl.textContent = temp.toFixed(1);
  }

  renderDialArc(targetTemp) {
    const minTemp = this._minTemp || 10;
    const maxTemp = this._maxTemp || 30;
    const range = Math.max(maxTemp - minTemp, 1);
    const pct = Math.max(0, Math.min(1, (targetTemp - minTemp) / range));
    const delta = pct * 270.0;
    const alpha = -135.0 + delta;
    const rad = alpha * (Math.PI / 180);

    const cx = 150.0;
    const cy = 145.0;
    const r = 115.0;

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
          meter.setAttribute('d', `M 231.32 226.32 A 115 115 0 ${largeArc} 0 ${xt.toFixed(2)} ${yt.toFixed(2)}`);
        }
      } else {
        // In heating/standby: sweep clockwise from left (-135deg) to target
        if (delta <= 0.5) {
          meter.setAttribute('d', '');
        } else {
          const largeArc = delta > 180 ? 1 : 0;
          meter.setAttribute('d', `M 68.68 226.32 A 115 115 0 ${largeArc} 1 ${xt.toFixed(2)} ${yt.toFixed(2)}`);
        }
      }
      meter.setAttribute('stroke', activeColor);
      meter.style.filter = filterId;
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

    const cx = 150.0;
    const cy = 145.0;
    const r = 115.0;

    const xc = cx + r * Math.sin(rad);
    const yc = cy - r * Math.cos(rad);

    const dot = this.shadowRoot.querySelector('#curr-temp-dot');
    if (dot) {
      dot.setAttribute('cx', xc.toFixed(2));
      dot.setAttribute('cy', yc.toFixed(2));
    }
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

    if (!this._rendered) {
      this.renderStructure();
    }

    let displayTitle = this._config.title || climateState.attributes.friendly_name || climateEntity;
    if (displayTitle) {
      displayTitle = displayTitle.replace(/^Virtual Thermostats VT /i, '').replace(/^Heating Zones(?: Zone)? /i, '');
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

    // Classic style handles inner HA child card
    const isClassic = (this.getEffectiveStyle() === "classic");
    if (isClassic) {
      if (this._childCard) {
        this._childCard.hass = this._hass;
      }
      return;
    }

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
      const targetEl = this.shadowRoot.querySelector('#target-temp');
      if (targetEl) targetEl.textContent = targetTemp.toFixed(1);
      this.renderDialArc(targetTemp);
    }

    const currentEl = this.shadowRoot.querySelector('#current-temp');
    if (currentEl) currentEl.textContent = currentTemp.toFixed(1) + "°C";

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
        subText.textContent = "● " + getTranslation(this._hass, 'off');
      } else if (this._isCooling) {
        subText.className = "dial-sub-text cooling-text";
        subText.textContent = "❄️ In Raffrescamento";
      } else if (this._isHeating) {
        subText.className = "dial-sub-text heating-text";
        subText.textContent = "🔥 " + getTranslation(this._hass, 'heating_active');
      } else {
        subText.className = "dial-sub-text standby-text";
        subText.textContent = "● " + getTranslation(this._hass, 'idle');
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
        valveEl.textContent = "Attivo";
        valveEl.style.color = "#f97316";
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
