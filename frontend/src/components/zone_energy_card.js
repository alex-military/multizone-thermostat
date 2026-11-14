class MultizoneThermostatZoneEnergyCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: 'open' });
    this._rendered = false;
  }

  setConfig(config) {
    if (!config || !config.entity) {
      throw new Error("Devi specificare un'entità climate");
    }
    this._config = Object.assign({}, config);
  }

  getCardSize() {
    return 3;
  }

  static getStubConfig(hass, entities) {
    const climate = entities ? entities.find(e => e.startsWith("climate.")) : "";
    return {
      entity: climate || "",
      title: ""
    };
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
        display: flex;
        flex-direction: column;
        justify-content: space-between;
      }
      .top-row {
        display: flex;
        align-items: flex-start;
        justify-content: space-between;
        margin-bottom: 14px;
      }
      .zone-name {
        font-size: 20px;
        font-weight: 800;
        margin: 0;
        display: flex;
        align-items: center;
        gap: 10px;
      }
      .zone-mode-badge {
        font-size: 11px;
        font-weight: 800;
        padding: 4px 9px;
        border-radius: 6px;
        text-transform: uppercase;
        background: rgba(59, 130, 246, 0.2);
        color: #60a5fa;
        cursor: pointer;
        transition: opacity 0.2s ease, transform 0.1s ease;
      }
      .zone-mode-badge:hover {
        opacity: 0.85;
      }
      .zone-mode-badge:active {
        transform: scale(0.96);
      }
      .zone-sub {
        font-size: 14px;
        font-weight: 500;
        color: var(--secondary-text-color, #94a3b8);
        margin-top: 4px;
      }
      .energy-badge {
        padding: 6px 14px;
        border-radius: 10px;
        font-weight: 900;
        font-size: 18px;
        text-align: center;
        box-shadow: 0 2px 8px rgba(0,0,0,0.2);
        min-width: 48px;
        background: #10b981;
        color: white;
      }
      .ribbon-scale {
        display: flex;
        height: 6px;
        border-radius: 3px;
        overflow: hidden;
        margin-bottom: 16px;
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
      @media (max-width: 640px) {
        ha-card {
          padding: 16px 14px;
        }
        .top-row {
          flex-wrap: wrap;
          gap: 10px;
        }
        .zone-name {
          font-size: 17px;
          flex-wrap: wrap;
        }
        .stats-grid {
          grid-template-columns: 1fr;
          gap: 10px;
        }
      }
      .stat-box {
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(255, 255, 255, 0.05);
        border-radius: 14px;
        padding: 12px 14px;
      }
      .stat-label {
        font-size: 13px;
        font-weight: 600;
        color: var(--secondary-text-color, #94a3b8);
        display: block;
        margin-bottom: 5px;
      }
      .stat-val {
        font-size: 22px;
        font-weight: 800;
        line-height: 1.2;
      }
      .stat-unit {
        font-size: 13px;
        color: var(--secondary-text-color, #94a3b8);
        font-weight: 600;
        margin-left: 2px;
      }
      .stat-eval {
        font-size: 13px;
        margin-top: 5px;
        font-weight: 600;
        display: block;
      }
      .bottom-row {
        padding-top: 14px;
        border-top: 1px solid rgba(255, 255, 255, 0.06);
        display: flex;
        align-items: center;
        justify-content: space-between;
        font-size: 14px;
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
      .pid-panel {
        margin-top: 12px;
        background: var(--secondary-background-color, rgba(15, 23, 42, 0.35));
        border: 1px solid var(--divider-color, rgba(148, 163, 184, 0.16));
        border-radius: 12px;
        padding: 10px 12px;
      }
      .pid-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 8px;
        gap: 8px;
      }
      .pid-title-row {
        display: flex;
        align-items: center;
        gap: 6px;
        font-size: 0.78em;
        font-weight: 600;
        color: var(--secondary-text-color, #94a3b8);
      }
      .pid-state-pill {
        font-size: 0.78em;
        padding: 2px 7px;
        border-radius: 999px;
        background: rgba(148, 163, 184, 0.16);
        color: #cbd5e1;
      }
      .pid-reset-btn {
        display: inline-flex;
        align-items: center;
        gap: 4px;
        font-size: 0.75em;
        font-weight: 600;
        padding: 4px 8px;
        border-radius: 8px;
        border: 1px solid rgba(239, 68, 68, 0.35);
        background: rgba(239, 68, 68, 0.12);
        color: #fca5a5;
        cursor: pointer;
        transition: background 0.15s ease;
      }
      .pid-reset-btn:hover {
        background: rgba(239, 68, 68, 0.24);
      }
      .pid-grid {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 8px;
      }
      .pid-box {
        background: rgba(148, 163, 184, 0.14);
        border: 1px solid rgba(148, 163, 184, 0.28);
        border-radius: 10px;
        padding: 8px 6px;
        text-align: center;
        cursor: pointer;
        color: #94a3b8;
        transition: border-color 0.15s ease, transform 0.12s ease;
      }
      .pid-box:hover {
        border-color: rgba(148, 163, 184, 0.55);
        transform: translateY(-1px);
      }
      .pid-box.manual-override {
        background: rgba(245, 158, 11, 0.14);
        border-color: rgba(245, 158, 11, 0.55);
        color: #fde68a;
      }
      .pid-box-top {
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 4px;
        font-size: 0.72em;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.4px;
        margin-bottom: 3px;
      }
      .pid-box-val {
        font-size: 0.95em;
        font-weight: 700;
        font-variant-numeric: tabular-nums;
      }
      .pid-modal-backdrop {
        position: fixed;
        inset: 0;
        background: rgba(2, 6, 23, 0.72);
        backdrop-filter: blur(4px);
        display: none;
        align-items: center;
        justify-content: center;
        z-index: 9999;
        padding: 16px;
      }
      .pid-modal-backdrop.open {
        display: flex;
      }
      .pid-modal {
        width: 100%;
        max-width: 360px;
        background: var(--card-background-color, #1e293b);
        color: var(--primary-text-color, #f1f5f9);
        border: 1px solid rgba(148, 163, 184, 0.25);
        border-radius: 16px;
        padding: 18px;
        box-shadow: 0 20px 45px rgba(0, 0, 0, 0.45);
      }
      .pid-modal-title {
        display: flex;
        align-items: center;
        gap: 8px;
        font-size: 1.02em;
        font-weight: 700;
        margin-bottom: 10px;
        color: #fbbf24;
      }
      .pid-modal-warn {
        font-size: 0.84em;
        line-height: 1.45;
        color: var(--secondary-text-color, #cbd5e1);
        background: rgba(245, 158, 11, 0.1);
        border: 1px solid rgba(245, 158, 11, 0.28);
        border-radius: 10px;
        padding: 10px;
        margin-bottom: 12px;
      }
      .pid-modal-input-wrap {
        margin-bottom: 14px;
      }
      .pid-modal-input-wrap label {
        display: block;
        font-size: 0.8em;
        color: var(--secondary-text-color, #94a3b8);
        margin-bottom: 4px;
      }
      .pid-modal-input-wrap input {
        width: 100%;
        box-sizing: border-box;
        padding: 8px 10px;
        border-radius: 8px;
        border: 1px solid rgba(148, 163, 184, 0.35);
        background: rgba(15, 23, 42, 0.55);
        color: var(--primary-text-color, #f8fafc);
        font-size: 1em;
        font-weight: 600;
      }
      .pid-modal-actions {
        display: flex;
        justify-content: flex-end;
        flex-wrap: wrap;
        gap: 8px;
      }
      .pid-btn {
        border: none;
        border-radius: 8px;
        padding: 8px 12px;
        font-size: 0.82em;
        font-weight: 600;
        cursor: pointer;
      }
      .pid-btn-cancel {
        background: rgba(148, 163, 184, 0.18);
        color: #cbd5e1;
      }
      .pid-btn-restore {
        background: rgba(56, 189, 248, 0.18);
        color: #7dd3fc;
      }
      .pid-btn-save {
        background: #f59e0b;
        color: #0f172a;
      }
      .pid-btn-danger {
        background: #ef4444;
        color: #ffffff;
      }
    `;

    const t = (k) => getTranslation(this._hass, k);
    const card = document.createElement('ha-card');
    card.innerHTML = `
      <div class="top-row">
        <div>
          <div class="zone-name">
            <span id="zone-title">Stanza</span>
            <span class="zone-mode-badge" id="zone-mode-badge" title="Click to cycle zone mode">${t('primary_tag')}</span>
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
          <span class="stat-label" id="retention-label">${t('retention_label')}</span>
          <div>
            <span class="stat-val" id="retention-val">--</span>
            <span class="stat-unit" id="retention-unit">${t('hours')}</span>
          </div>
          <span class="stat-eval" id="retention-eval" style="color: #38bdf8;">--</span>
        </div>

        <div class="stat-box">
          <span class="stat-label" id="sizing-label">${t('sizing_label')}</span>
          <div>
            <span class="stat-val" id="sizing-val">--</span>
          </div>
          <span class="stat-eval" id="sizing-eval" style="color: #34d399;">--</span>
        </div>
      </div>

      <div class="pid-panel">
        <div class="pid-header">
          <div class="pid-title-row">
            <span id="pid-section-title">${t('pid_section_title')}</span>
            <span class="pid-state-pill" id="pid-state-pill">--</span>
          </div>
          <button type="button" class="pid-reset-btn" id="pid-reset-btn" title="${t('pid_reset_btn')}">
            <ha-icon icon="mdi:restart-alert" style="--mdc-icon-size: 14px;"></ha-icon>
            <span id="pid-reset-label">${t('pid_reset_btn')}</span>
          </button>
        </div>
        <div class="pid-grid">
          <div class="pid-box" id="pid-box-kp" data-param="Kp" title="${t('pid_click_to_edit')}">
            <div class="pid-box-top"><span id="pid-lock-kp">🔒</span><span>Kp</span></div>
            <div class="pid-box-val" id="pid-val-kp">--</div>
          </div>
          <div class="pid-box" id="pid-box-ki" data-param="Ki" title="${t('pid_click_to_edit')}">
            <div class="pid-box-top"><span id="pid-lock-ki">🔒</span><span>Ki</span></div>
            <div class="pid-box-val" id="pid-val-ki">--</div>
          </div>
          <div class="pid-box" id="pid-box-kd" data-param="Kd" title="${t('pid_click_to_edit')}">
            <div class="pid-box-top"><span id="pid-lock-kd">🔒</span><span>Kd</span></div>
            <div class="pid-box-val" id="pid-val-kd">--</div>
          </div>
        </div>
      </div>

      <div class="bottom-row">
        <span style="color: var(--secondary-text-color, #94a3b8);" id="valve-status-label">${t('valve_status')}</span>
        <div class="valve-status" id="valve-status" style="margin-right: auto; padding-left: 10px;">
          <span class="pulse-dot pulse-green" id="valve-dot"></span>
          <span id="valve-text">${t('valve_ok')}</span>
        </div>
        <div class="battery-status" id="battery-status" style="display:flex; align-items:center; gap: 4px; font-weight:600;">
          <ha-icon icon="mdi:battery" id="battery-icon" style="--mdc-icon-size: 18px;"></ha-icon>
          <span id="battery-text">--%</span>
        </div>
      </div>

      <div class="pid-modal-backdrop" id="pid-modal-backdrop">
        <div class="pid-modal">
          <div class="pid-modal-title" id="pid-modal-title"></div>
          <div class="pid-modal-warn" id="pid-modal-warn"></div>
          <div class="pid-modal-input-wrap" id="pid-modal-input-wrap">
            <label for="pid-modal-input" id="pid-modal-input-label"></label>
            <input type="number" id="pid-modal-input" />
          </div>
          <div class="pid-modal-actions">
            <button type="button" class="pid-btn pid-btn-cancel" id="pid-modal-cancel">${t('pid_modal_cancel')}</button>
            <button type="button" class="pid-btn pid-btn-restore" id="pid-modal-restore">${t('pid_modal_restore')}</button>
            <button type="button" class="pid-btn pid-btn-save" id="pid-modal-confirm">${t('pid_modal_save')}</button>
          </div>
        </div>
      </div>
    `;

    this.shadowRoot.appendChild(style);
    this.shadowRoot.appendChild(card);
    this._bindPidEvents();
    this._rendered = true;
  }

  _bindPidEvents() {
    this._activePidParam = null;
    this._modalMode = null;

    const closeModal = () => {
      const backdrop = this.shadowRoot.getElementById('pid-modal-backdrop');
      if (backdrop) backdrop.classList.remove('open');
      this._activePidParam = null;
      this._modalMode = null;
    };

    ['kp', 'ki', 'kd'].forEach((paramLower) => {
      const box = this.shadowRoot.getElementById(`pid-box-${paramLower}`);
      if (!box) return;
      box.addEventListener('click', () => {
        if (!this._hass || !this._config || !this._config.entity) return;
        const param = box.dataset.param;
        this._openPidEditModal(param);
      });
    });

    const resetBtn = this.shadowRoot.getElementById('pid-reset-btn');
    if (resetBtn) {
      resetBtn.addEventListener('click', () => {
        if (!this._hass || !this._config || !this._config.entity) return;
        this._openResetModal();
      });
    }

    const cancelBtn = this.shadowRoot.getElementById('pid-modal-cancel');
    if (cancelBtn) cancelBtn.addEventListener('click', closeModal);

    const backdrop = this.shadowRoot.getElementById('pid-modal-backdrop');
    if (backdrop) {
      backdrop.addEventListener('click', (e) => {
        if (e.target === backdrop) closeModal();
      });
    }

    const restoreBtn = this.shadowRoot.getElementById('pid-modal-restore');
    if (restoreBtn) {
      restoreBtn.addEventListener('click', async () => {
        if (!this._hass || !this._config || !this._activePidParam) return;
        await this._hass.callService('multizone_thermostat', 'set_pid_parameters', {
          climate_entity: this._config.entity,
          lock_parameter: this._activePidParam,
          unlock: false,
        });
        closeModal();
      });
    }

    const confirmBtn = this.shadowRoot.getElementById('pid-modal-confirm');
    if (confirmBtn) {
      confirmBtn.addEventListener('click', async () => {
        if (!this._hass || !this._config || !this._config.entity) return;
        if (this._modalMode === 'reset') {
          await this._hass.callService('multizone_thermostat', 'reset_autotune', {
            climate_entity: this._config.entity,
          });
          closeModal();
          return;
        }
        if (this._modalMode === 'edit' && this._activePidParam) {
          const inputEl = this.shadowRoot.getElementById('pid-modal-input');
          const parsed = inputEl ? parseFloat(inputEl.value) : NaN;
          if (!isNaN(parsed)) {
            await this._hass.callService('multizone_thermostat', 'set_pid_parameters', {
              climate_entity: this._config.entity,
              [this._activePidParam.toLowerCase()]: parsed,
              unlock: true,
            });
          }
          closeModal();
        }
      });
    }
  }

  _openPidEditModal(param) {
    const t = (k) => getTranslation(this._hass, k);
    this._modalMode = 'edit';
    this._activePidParam = param;

    const specs = {
      Kp: { min: 0.1, max: 500, step: 0.1 },
      Ki: { min: 0, max: 1, step: 0.0001 },
      Kd: { min: 0, max: 50000, step: 1 },
    }[param];

    const titleEl = this.shadowRoot.getElementById('pid-modal-title');
    const warnEl = this.shadowRoot.getElementById('pid-modal-warn');
    const inputWrap = this.shadowRoot.getElementById('pid-modal-input-wrap');
    const labelEl = this.shadowRoot.getElementById('pid-modal-input-label');
    const inputEl = this.shadowRoot.getElementById('pid-modal-input');
    const restoreBtn = this.shadowRoot.getElementById('pid-modal-restore');
    const confirmBtn = this.shadowRoot.getElementById('pid-modal-confirm');
    const valEl = this.shadowRoot.getElementById(`pid-val-${param.toLowerCase()}`);
    const backdrop = this.shadowRoot.getElementById('pid-modal-backdrop');

    if (titleEl) titleEl.innerText = `⚠️ ${t('pid_modal_title')} (${param})`;
    if (warnEl) warnEl.innerText = t('pid_modal_warn');
    if (inputWrap) inputWrap.style.display = 'block';
    if (labelEl) labelEl.innerText = `${t('pid_modal_value')} (${param})`;
    if (inputEl && specs) {
      inputEl.min = String(specs.min);
      inputEl.max = String(specs.max);
      inputEl.step = String(specs.step);
      const curNum = valEl ? parseFloat(valEl.innerText) : NaN;
      inputEl.value = isNaN(curNum) ? '0' : String(curNum);
    }
    if (restoreBtn) {
      const overrides = (this._latestPidInfo && this._latestPidInfo.overrides) || [];
      restoreBtn.style.display = overrides.includes(param) ? 'inline-block' : 'none';
      restoreBtn.innerText = t('pid_modal_restore');
    }
    if (confirmBtn) {
      confirmBtn.className = 'pid-btn pid-btn-save';
      confirmBtn.innerText = t('pid_modal_save');
    }
    if (backdrop) backdrop.classList.add('open');
  }

  _openResetModal() {
    const t = (k) => getTranslation(this._hass, k);
    this._modalMode = 'reset';
    this._activePidParam = null;

    const titleEl = this.shadowRoot.getElementById('pid-modal-title');
    const warnEl = this.shadowRoot.getElementById('pid-modal-warn');
    const inputWrap = this.shadowRoot.getElementById('pid-modal-input-wrap');
    const restoreBtn = this.shadowRoot.getElementById('pid-modal-restore');
    const confirmBtn = this.shadowRoot.getElementById('pid-modal-confirm');
    const backdrop = this.shadowRoot.getElementById('pid-modal-backdrop');

    if (titleEl) titleEl.innerText = `🔄 ${t('pid_reset_title')}`;
    if (warnEl) warnEl.innerText = t('pid_reset_confirm_msg');
    if (inputWrap) inputWrap.style.display = 'none';
    if (restoreBtn) restoreBtn.style.display = 'none';
    if (confirmBtn) {
      confirmBtn.className = 'pid-btn pid-btn-danger';
      confirmBtn.innerText = t('pid_reset_confirm_btn');
    }
    if (backdrop) backdrop.classList.add('open');
  }

  updateCard() {
    if (!this._hass || !this._hass.states) return;
    if (!this._hass || !this._rendered || !this._config || !this._config.entity) return;

    try {
      const t = (k) => getTranslation(this._hass, k);
      const climateId = this._config.entity;
      const climateState = this._hass.states[climateId];
      if (!climateState) return;

      let title = this._config.title || climateState.attributes.friendly_name || climateId;
      title = title.replace(/^Virtual Thermostats VT /i, '').replace(/^Heating Zones(?: Zone)? /i, '');
      let slug = climateId.replace("climate.multizone_thermostat_", "").replace("climate.", "");

      const energyEntity = this._hass && this._hass.states && Object.keys(this._hass.states).find(k =>
        k.startsWith('sensor.') && (k.includes('energy_class') || k.includes('classe_energetica')) && k.includes(slug)
      );
      const retentionEntity = this._hass && this._hass.states && Object.keys(this._hass.states).find(k =>
        k.startsWith('sensor.') && (k.includes('thermal_retention') || k.includes('tempo_ritenzione_termica')) && k.includes(slug)
      );
      const sizingEntity = this._hass && this._hass.states && Object.keys(this._hass.states).find(k =>
        k.startsWith('sensor.') && (k.includes('radiator_sizing') || k.includes('dimensionamento_radiatore')) && k.includes(slug)
      );
      const anomalyEntity = this._hass && this._hass.states && Object.keys(this._hass.states).find(k => k.startsWith('binary_sensor.') && k.includes('anomaly') && k.includes(slug));

      const titleEl = this.shadowRoot.getElementById('zone-title');
      const tempSubEl = this.shadowRoot.getElementById('temp-sub');
      const badgeEl = this.shadowRoot.getElementById('energy-badge');
      const modeBadge = this.shadowRoot.getElementById('zone-mode-badge');
      const retentionVal = this.shadowRoot.getElementById('retention-val');
      const retentionEval = this.shadowRoot.getElementById('retention-eval');
      const sizingVal = this.shadowRoot.getElementById('sizing-val');
      const sizingEval = this.shadowRoot.getElementById('sizing-eval');
      const valveDot = this.shadowRoot.getElementById('valve-dot');
      const valveText = this.shadowRoot.getElementById('valve-text');
      const batteryText = this.shadowRoot.getElementById('battery-text');
      const batteryIcon = this.shadowRoot.getElementById('battery-icon');

      // Robust determination of zone mode (primary, secondary, bypass)
      let zoneMode = "primary";
      const switchEntity = autoDiscoverSwitch(this._hass, climateId);
      if (switchEntity && this._hass.states[switchEntity]) {
        const sState = this._hass.states[switchEntity];
        if (switchEntity.startsWith("switch.")) {
          zoneMode = (sState.state === "off") ? "bypass" : "primary";
        } else {
          zoneMode = sState.state || "primary";
        }
      } else if (climateState.attributes && climateState.attributes.zone_mode) {
        zoneMode = climateState.attributes.zone_mode;
      } else {
        const selectObj = Object.values(this._hass.states).find(s => 
          s.entity_id.startsWith('select.') && (
            (s.attributes && s.attributes.climate_entity === climateId) ||
            (s.entity_id.includes(slug) && (s.entity_id.includes('mode') || s.entity_id.includes('zone')))
          )
        );
        if (selectObj && selectObj.state) {
          zoneMode = selectObj.state;
        }
      }

      if (titleEl) titleEl.innerText = title;

      if (tempSubEl) {
        const cur = climateState.attributes.current_temperature;
        const tgt = climateState.attributes.temperature;
        if (zoneMode === "bypass") {
          tempSubEl.innerText = `${cur !== undefined ? cur : '--'}°C / (${t('bypassed_tag')})`;
        } else {
          tempSubEl.innerText = `${cur !== undefined ? cur : '--'}°C / ${t('target')} ${tgt !== undefined ? tgt : '--'}°C`;
        }
      }

      this._currentZoneMode = zoneMode;
      this._currentSwitchEntity = switchEntity;

      if (modeBadge) {
        if (!this._modeListenerAttached && switchEntity) {
          this._modeListenerAttached = true;
          modeBadge.addEventListener('click', (e) => {
            e.stopPropagation();
            const activeSwitchEntity = this._currentSwitchEntity;
            const activeZoneMode = this._currentZoneMode || 'primary';
            if (!activeSwitchEntity) return;
            if (activeSwitchEntity.startsWith('select.')) {
              const modes = ['primary', 'secondary', 'bypass'];
              const curIdx = modes.indexOf(activeZoneMode);
              const nextMode = modes[(curIdx + 1) % modes.length];
              this._hass.callService('select', 'select_option', {
                entity_id: activeSwitchEntity,
                option: nextMode
              });
            } else if (activeSwitchEntity.startsWith('switch.')) {
              this._hass.callService('switch', 'toggle', {
                entity_id: activeSwitchEntity
              });
            }
          });
        }

        if (zoneMode === "bypass") {
          modeBadge.innerText = t('bypassed_tag');
          modeBadge.style.background = "rgba(100, 116, 139, 0.25)";
          modeBadge.style.color = "#94a3b8";
          modeBadge.style.border = "1px solid rgba(148, 163, 184, 0.3)";
        } else if (zoneMode === "secondary") {
          modeBadge.innerText = t('secondary_tag');
          modeBadge.style.background = "rgba(168, 85, 247, 0.2)";
          modeBadge.style.color = "#c084fc";
          modeBadge.style.border = "1px solid rgba(168, 85, 247, 0.3)";
        } else {
          modeBadge.innerText = t('primary_tag');
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
          if (isNaN(r)) retentionEval.innerText = t('learning');
          else if (r >= 6.0) retentionEval.innerText = t('opt_insulation');
          else if (r >= 3.5) retentionEval.innerText = t('med_insulation');
          else retentionEval.innerText = t('fast_dispersion');
        }
      }

      const sState = sizingEntity ? this._hass.states[sizingEntity] : null;
      if (sizingVal && sState) {
        sizingVal.innerText = sState.state;
        if (sizingEval) {
          if (sState.state === "Optimal" || sState.state === "Ottimale") {
            sizingEval.innerText = t('sizing_opt');
            sizingEval.style.color = "#34d399";
          } else if (sState.state === "Undersized" || sState.state === "Sottodimensionato") {
            sizingEval.innerText = t('sizing_under');
            sizingEval.style.color = "#f87171";
          } else if (sState.state === "Oversized" || sState.state === "Sovradimensionato") {
            sizingEval.innerText = t('sizing_over');
            sizingEval.style.color = "#fbbf24";
          } else {
            sizingEval.innerText = t('sizing_waiting');
            sizingEval.style.color = "#94a3b8";
          }
        }
      }

      const aState = anomalyEntity ? this._hass.states[anomalyEntity] : null;
      const passiveHeatSwitch = this._hass && this._hass.states && Object.keys(this._hass.states).find(k => 
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
            const sw = this._hass && this._hass.states && Object.keys(this._hass.states).find(k => 
              k.startsWith('switch.') && k.includes('passive_heat') && k.includes(slug)
            );
            if (sw) {
              this._hass.callService('switch', 'toggle', { entity_id: sw });
            }
          });
        }
        valveStatusEl.title = allowPassive 
          ? getTranslation(this._hass, 'passive_heat_active_tooltip') 
          : getTranslation(this._hass, 'passive_heat_inactive_tooltip');
      }

      if (valveDot && valveText) {
        const hasAnomaly = aState && aState.state === "on";
        if (hasAnomaly) {
          valveDot.className = "pulse-dot pulse-red";
          valveText.innerText = (aState.attributes && aState.attributes.details) || getTranslation(this._hass, 'anomaly_detected');
          valveText.style.color = "#f87171";
        } else if (zoneMode === "bypass") {
          valveDot.className = "pulse-dot pulse-green";
          valveText.innerText = allowPassive ? `${t('valve_closed_bypass')} (${t('passive_heat_active')})` : t('valve_closed_bypass');
          valveText.style.color = "#94a3b8";
        } else {
          valveDot.className = "pulse-dot pulse-green";
          valveText.innerText = allowPassive ? `${t('valve_ok')} (${t('passive_heat_active')})` : t('valve_ok');
          valveText.style.color = "#34d399";
        }
      }

      if (batteryText && batteryIcon) {
        let batVal = null;
        if (climateState.attributes && climateState.attributes.battery_level !== undefined && climateState.attributes.battery_level !== null) {
          batVal = climateState.attributes.battery_level;
        } else if (this._hass && this._hass.states) {
          const checkEntityBattery = (entId) => {
            if (!entId) return null;
            const clean = entId.replace('sensor.', '').replace('climate.', '').replace(/_temperature|_temp|_current_temperature$/, '');
            const candidateKeys = [
              `sensor.${clean}_battery`,
              `sensor.${clean}_battery_level`,
            ];
            for (const cand of candidateKeys) {
              if (this._hass.states[cand] && !['unavailable', 'unknown'].includes(this._hass.states[cand].state)) {
                const p = parseFloat(this._hass.states[cand].state);
                if (!isNaN(p)) return Math.round(p);
              }
            }
            const targetState = this._hass.states[entId];
            if (targetState && targetState.attributes) {
              for (const attr of ['battery', 'battery_level', 'battery_percent']) {
                if (targetState.attributes[attr] !== undefined) {
                  const p = parseFloat(targetState.attributes[attr]);
                  if (!isNaN(p)) return Math.round(p);
                }
              }
            }
            return null;
          };

          if (climateState.attributes && climateState.attributes.temperature_sensor) {
            batVal = checkEntityBattery(climateState.attributes.temperature_sensor);
          }
          if (batVal === null && climateState.attributes && Array.isArray(climateState.attributes.climates)) {
            for (const trv of climateState.attributes.climates) {
              const trvBat = checkEntityBattery(trv);
              if (trvBat !== null) {
                batVal = trvBat;
                break;
              }
            }
          }
          if (batVal === null) {
            const batEntity = Object.keys(this._hass.states).find(k => 
              k.startsWith('sensor.') && 
              (k.includes('battery') || k.includes('batteria')) && 
              k.includes(slug) &&
              !['unavailable', 'unknown'].includes(this._hass.states[k].state)
            );
            if (batEntity && this._hass.states[batEntity]) {
              const parsed = parseFloat(this._hass.states[batEntity].state);
              if (!isNaN(parsed)) {
                batVal = Math.round(parsed);
              }
            }
          }
        }

        if (batVal !== null && batVal !== undefined) {
          batteryText.innerText = batVal + "%";
          if (batVal > 80) {
            batteryIcon.icon = "mdi:battery";
            batteryIcon.style.color = "#10b981";
          } else if (batVal > 40) {
            batteryIcon.icon = "mdi:battery-50";
            batteryIcon.style.color = "#f39c12";
          } else if (batVal > 15) {
            batteryIcon.icon = "mdi:battery-20";
            batteryIcon.style.color = "#e67e22";
          } else {
            batteryIcon.icon = "mdi:battery-alert";
            batteryIcon.style.color = "#ef4444";
          }
        } else {
          batteryText.innerText = "--%";
          batteryIcon.icon = "mdi:battery-unknown";
          batteryIcon.style.color = "var(--secondary-text-color, #94a3b8)";
        }
      }

      // PID & Autotuner Display
      const attrs = climateState.attributes || {};
      const autotuneSensorKey = this._hass && this._hass.states && Object.keys(this._hass.states).find(k =>
        k.startsWith('sensor.') && k.includes('autotun') && k.includes(slug)
      );
      const autotuneStateObj = autotuneSensorKey ? this._hass.states[autotuneSensorKey] : null;
      const autoAttrs = (autotuneStateObj && autotuneStateObj.attributes) || {};

      const readNumFallback = (paramLower) => {
        const numKey = Object.keys(this._hass.states).find(k =>
          k.startsWith('number.') && k.includes(`pid_${paramLower}`) && k.includes(slug)
        );
        if (numKey && this._hass.states[numKey]) {
          const parsed = parseFloat(this._hass.states[numKey].state);
          if (!isNaN(parsed)) return parsed;
        }
        return null;
      };

      const kpVal = attrs.pid_kp !== undefined ? attrs.pid_kp : (autoAttrs.Kp !== undefined ? autoAttrs.Kp : readNumFallback('kp'));
      const kiVal = attrs.pid_ki !== undefined ? attrs.pid_ki : (autoAttrs.Ki !== undefined ? autoAttrs.Ki : readNumFallback('ki'));
      const kdVal = attrs.pid_kd !== undefined ? attrs.pid_kd : (autoAttrs.Kd !== undefined ? autoAttrs.Kd : readNumFallback('kd'));
      const overrides = Array.isArray(attrs.pid_manual_overrides)
        ? attrs.pid_manual_overrides
        : (Array.isArray(autoAttrs.manual_overrides) ? autoAttrs.manual_overrides : []);
      const autotuneState = attrs.autotune_state || (autotuneStateObj ? autotuneStateObj.state : null);

      this._latestPidInfo = { kp: kpVal, ki: kiVal, kd: kdVal, overrides };

      const pidTitleEl = this.shadowRoot.getElementById('pid-section-title');
      if (pidTitleEl) pidTitleEl.innerText = t('pid_section_title');
      const resetLabelEl = this.shadowRoot.getElementById('pid-reset-label');
      if (resetLabelEl) resetLabelEl.innerText = t('pid_reset_btn');

      const pillEl = this.shadowRoot.getElementById('pid-state-pill');
      if (pillEl) {
        if (overrides.length > 0) {
          pillEl.innerText = t('pid_manual_badge');
        } else if (autotuneState === 'completed' || autotuneState === 'Smart PID Active') {
          pillEl.innerText = t('pid_auto_badge');
        } else {
          const cyc = attrs.autotune_cycles !== undefined ? attrs.autotune_cycles : 0;
          const req = attrs.autotune_required_cycles !== undefined ? attrs.autotune_required_cycles : 3;
          pillEl.innerText = `${t('pid_learning_status')} (${cyc}/${req})`;
        }
      }

      const fmtMap = {
        Kp: kpVal !== null && kpVal !== undefined ? Number(kpVal).toFixed(1) : '--',
        Ki: kiVal !== null && kiVal !== undefined ? Number(kiVal).toFixed(4) : '--',
        Kd: kdVal !== null && kdVal !== undefined ? Number(kdVal).toFixed(1) : '--',
      };
      ['Kp', 'Ki', 'Kd'].forEach((param) => {
        const lower = param.toLowerCase();
        const box = this.shadowRoot.getElementById(`pid-box-${lower}`);
        const valEl = this.shadowRoot.getElementById(`pid-val-${lower}`);
        const lockEl = this.shadowRoot.getElementById(`pid-lock-${lower}`);
        const isOverride = overrides.includes(param);
        if (valEl) valEl.innerText = fmtMap[param];
        if (box) {
          box.classList.toggle('manual-override', isOverride);
          box.title = t('pid_click_to_edit');
        }
        if (lockEl) lockEl.innerText = isOverride ? '✏️' : '🔒';
      });
    } catch (err) {
      console.error("Error updating MultizoneThermostatZoneEnergyCard:", err);
    }
  }
}

if (!customElements.get("multizone-thermostat-zone-energy-card")) {
  customElements.define("multizone-thermostat-zone-energy-card", MultizoneThermostatZoneEnergyCard);
}

/* ==================== DASHBOARD STRATEGY ==================== */
/* ==================== MULTIZONE SCHEDULER & SMART RETURN MAIN CARD ==================== */

