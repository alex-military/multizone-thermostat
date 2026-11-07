class MultizoneThermostatPlantCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: 'open' });
    this._rendered = false;
  }

  setConfig(config) {
    this._config = Object.assign({}, config || {});
  }

  getCardSize() {
    return 3;
  }

  static getStubConfig() {
    return {};
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
      }
      .header-row {
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 16px;
      }
      .title-group {
        display: flex;
        align-items: center;
        gap: 12px;
      }
      .icon-wrap {
        width: 46px;
        height: 46px;
        border-radius: 14px;
        display: flex;
        align-items: center;
        justify-content: center;
        background: rgba(14, 165, 233, 0.15);
        color: #38bdf8;
      }
      .icon-wrap ha-icon {
        --mdc-icon-size: 28px;
      }
      .title-text {
        font-size: 20px;
        font-weight: 800;
        margin: 0;
        line-height: 1.2;
      }
      .subtitle-text {
        font-size: 13px;
        color: var(--secondary-text-color, #94a3b8);
        margin-top: 3px;
      }
      .status-badge {
        padding: 6px 14px;
        border-radius: 9999px;
        font-size: 13px;
        font-weight: 800;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        display: flex;
        align-items: center;
        gap: 8px;
      }
      .status-optimal {
        background: rgba(16, 185, 129, 0.15);
        color: #34d399;
        border: 1px solid rgba(16, 185, 129, 0.3);
      }
      .status-warning {
        background: rgba(245, 158, 11, 0.15);
        color: #fbbf24;
        border: 1px solid rgba(245, 158, 11, 0.3);
      }
      .status-critical {
        background: rgba(239, 68, 68, 0.15);
        color: #f87171;
        border: 1px solid rgba(239, 68, 68, 0.3);
      }
      .status-dot {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background: currentColor;
      }
      .kpi-grid {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 14px;
        margin-bottom: 14px;
      }
      @media (max-width: 640px) {
        ha-card {
          padding: 16px 14px;
        }
        .header-row {
          flex-direction: column;
          align-items: flex-start;
          gap: 12px;
        }
        .title-text {
          font-size: 18px;
        }
        .kpi-grid {
          grid-template-columns: 1fr;
          gap: 10px;
        }
        .ot-grid {
          padding: 10px 12px !important;
        }
        .ot-grid > div:last-child {
          grid-template-columns: repeat(2, 1fr) !important;
          gap: 8px !important;
        }
      }
      .kpi-card {
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(255, 255, 255, 0.06);
        border-radius: 16px;
        padding: 16px;
      }
      .kpi-label {
        font-size: 13px;
        font-weight: 600;
        color: var(--secondary-text-color, #94a3b8);
        display: block;
        margin-bottom: 6px;
      }
      .kpi-value-row {
        display: flex;
        align-items: baseline;
        gap: 6px;
      }
      .kpi-val {
        font-size: 30px;
        font-weight: 900;
        line-height: 1;
      }
      .kpi-unit {
        font-size: 13px;
        font-weight: 600;
        color: var(--secondary-text-color, #94a3b8);
      }
      .kpi-sub {
        font-size: 12px;
        margin-top: 8px;
        font-weight: 600;
      }
      .alert-box {
        padding: 14px 16px;
        border-radius: 14px;
        font-size: 13px;
        line-height: 1.5;
        display: flex;
        flex-direction: column;
        gap: 6px;
        background: rgba(255, 255, 255, 0.02);
        border: 1px solid rgba(255, 255, 255, 0.06);
      }
      .alert-box.alert-ok {
        background: rgba(16, 185, 129, 0.08);
        border-color: rgba(16, 185, 129, 0.2);
        color: #a7f3d0;
      }
      .alert-box.alert-err {
        background: rgba(239, 68, 68, 0.12);
        border-color: rgba(239, 68, 68, 0.35);
        color: #fca5a5;
      }
      .alert-title {
        font-weight: 700;
        font-size: 14px;
        display: flex;
        align-items: center;
        gap: 8px;
      }
    `;

    const t = (k) => getTranslation(this._hass, k);
    const card = document.createElement('ha-card');
    card.innerHTML = `
      <div class="header-row">
        <div class="title-group">
          <div class="icon-wrap">
            <ha-icon icon="mdi:shield-check"></ha-icon>
          </div>
          <div>
            <div class="title-text" id="plant-title">${t('plant_health_title')}</div>
            <div class="subtitle-text" id="plant-sub">${t('plant_health_sub')}</div>
          </div>
        </div>
        <div class="status-badge status-optimal" id="health-badge">
          <span class="status-dot"></span>
          <span id="health-text">${t('optimal')}</span>
        </div>
      </div>

      <div class="kpi-grid">
        <div class="kpi-card">
          <span class="kpi-label" id="cycles-label">${t('cycles_label')}</span>
          <div class="kpi-value-row">
            <span class="kpi-val" id="cycles-val">--</span>
            <span class="kpi-unit" id="cycles-unit">${t('cycles_unit')}</span>
          </div>
          <div class="kpi-sub" id="cycles-sub" style="color: #34d399;">${t('wear_low')}</div>
        </div>

        <div class="kpi-card">
          <span class="kpi-label" id="runtime-label">${t('runtime_24h')}</span>
          <div class="kpi-value-row">
            <span class="kpi-val" id="runtime-val" style="color: #60a5fa;">--</span>
            <span class="kpi-unit" id="runtime-unit">${t('hours')}</span>
          </div>
          <div class="kpi-sub" id="runtime-sub" style="color: #94a3b8;">${t('runtime_sub')}</div>
        </div>
      </div>

      <div class="ot-grid" id="ot-grid" style="display:none; margin-bottom: 14px; background: rgba(14, 165, 233, 0.05); border: 1px solid rgba(14, 165, 233, 0.2); border-radius: 14px; padding: 12px 16px;">
        <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px;">
          <div style="font-weight: 700; font-size: 13px; color: #38bdf8; display: flex; align-items: center; gap: 6px;">
            <ha-icon icon="mdi:pipe-valve" style="--mdc-icon-size: 16px;"></ha-icon>
            <span id="ot-telemetry-title">${t('ot_telemetry')}</span>
          </div>
          <div id="ot-dhw-badge" style="display:none; font-size: 11px; font-weight: 700; background: rgba(59, 130, 246, 0.2); color: #60a5fa; border-radius: 6px; padding: 2px 8px; border: 1px solid rgba(59, 130, 246, 0.3);">
            ${t('ot_dhw_active')}
          </div>
        </div>
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(75px, 1fr)); gap: 10px;">
          <div>
            <div style="font-size: 11px; color: var(--secondary-text-color, #94a3b8);">${t('ot_pressure')}</div>
            <div style="font-size: 16px; font-weight: 800;" id="ot-pressure-val">-- bar</div>
          </div>
          <div>
            <div style="font-size: 11px; color: var(--secondary-text-color, #94a3b8);">${t('ot_flow_temp')}</div>
            <div style="font-size: 16px; font-weight: 800;" id="ot-flow-val">--°C</div>
          </div>
          <div>
            <div style="font-size: 11px; color: var(--secondary-text-color, #94a3b8);">${t('ot_return_temp')}</div>
            <div style="font-size: 16px; font-weight: 800;" id="ot-return-val">--°C</div>
            <div style="font-size: 10px; font-weight: 600;" id="ot-condense-eval"></div>
          </div>
          <div>
            <div style="font-size: 11px; color: var(--secondary-text-color, #94a3b8);">${t('ot_modulation')}</div>
            <div style="font-size: 16px; font-weight: 800;" id="ot-mod-val">--%</div>
          </div>
          <div>
            <div style="font-size: 11px; color: var(--secondary-text-color, #94a3b8);">${t('ot_flame_status')}</div>
            <div style="font-size: 14px; font-weight: 700;" id="ot-flame-val">${t('ot_flame_off')}</div>
          </div>
        </div>
      </div>

      <div class="alert-box alert-ok" id="alert-box">
        <div class="alert-title" id="alert-title-wrap">
          <ha-icon icon="mdi:check-circle-outline" style="--mdc-icon-size: 18px; color: #34d399;"></ha-icon>
          <span id="alert-title-text">${t('all_circuits_ok')}</span>
        </div>
        <div id="alert-desc">${t('no_anomalies')}</div>
      </div>
    `;

    this.shadowRoot.appendChild(style);
    this.shadowRoot.appendChild(card);
    this._rendered = true;
  }

  updateCard() {
    if (!this._hass || !this._hass.states) return;
    if (!this._hass || !this._rendered) return;

    try {
      const t = (k) => getTranslation(this._hass, k);
      let healthEntity = this._config.health_entity;
      let cyclesEntity = this._config.cycles_entity;
      let runtimeEntity = this._config.runtime_entity;
      let anomalyEntity = this._config.anomaly_entity;

      if (!healthEntity) {
        healthEntity = this._hass && this._hass.states && Object.keys(this._hass.states).find(k =>
          k.startsWith('sensor.') && (k.includes('plant_health') || k.includes('stato_salute_impianto'))
        );
      }
      if (!cyclesEntity) {
        cyclesEntity = this._hass && this._hass.states && Object.keys(this._hass.states).find(k =>
          k.startsWith('sensor.') && (k.includes('boiler_cycles_per_hour') || k.includes('frequenza_accensioni_caldaia'))
        );
      }
      if (!runtimeEntity) {
        runtimeEntity = this._hass && this._hass.states && Object.keys(this._hass.states).find(k =>
          k.startsWith('sensor.') && (k.includes('boiler_daily_runtime') || k.includes('ore_funzionamento_caldaia_24h'))
        );
      }
      if (!anomalyEntity) {
        anomalyEntity = this._hass && this._hass.states && Object.keys(this._hass.states).find(k => k.startsWith('binary_sensor.') && k.includes('plant_anomaly'));
      }

      const healthState = healthEntity ? this._hass.states[healthEntity] : null;
      const cyclesState = cyclesEntity ? this._hass.states[cyclesEntity] : null;
      const runtimeState = runtimeEntity ? this._hass.states[runtimeEntity] : null;
      const anomalyState = anomalyEntity ? this._hass.states[anomalyEntity] : null;

      const healthBadge = this.shadowRoot.getElementById('health-badge');
      const healthText = this.shadowRoot.getElementById('health-text');
      const cyclesVal = this.shadowRoot.getElementById('cycles-val');
      const cyclesSub = this.shadowRoot.getElementById('cycles-sub');
      const runtimeVal = this.shadowRoot.getElementById('runtime-val');
      const alertBox = this.shadowRoot.getElementById('alert-box');
      const alertDesc = this.shadowRoot.getElementById('alert-desc');

      const statusVal = healthState ? healthState.state : "Optimal";
      const isCritical = statusVal === "Critical" || statusVal === "Critico";
      const isWarning = statusVal === "Warning" || statusVal === "Attenzione";
      const isOptimal = statusVal === "Optimal" || statusVal === "Ottimale";
      if (healthBadge && healthText) {
        if (isCritical) {
          healthText.innerText = t('critical');
          healthBadge.className = "status-badge status-critical";
        } else if (isWarning) {
          healthText.innerText = t('warning');
          healthBadge.className = "status-badge status-warning";
        } else {
          healthText.innerText = t('optimal');
          healthBadge.className = "status-badge status-optimal";
        }
      }

      if (cyclesVal && cyclesState) {
        const c = parseFloat(cyclesState.state) || 0;
        cyclesVal.innerText = c.toFixed(1);
        if (cyclesSub) {
          if (c <= 3.5) {
            cyclesSub.innerText = t('wear_low');
            cyclesSub.style.color = "#34d399";
          } else if (c <= 5.0) {
            cyclesSub.innerText = t('wear_moderate');
            cyclesSub.style.color = "#fbbf24";
          } else {
            cyclesSub.innerText = t('wear_high');
            cyclesSub.style.color = "#f87171";
          }
        }
      }

      if (runtimeVal && runtimeState) {
        const r = parseFloat(runtimeState.state) || 0;
        runtimeVal.innerText = r.toFixed(1);
      }

      if (alertBox && alertDesc) {
        const hasAnomaly = anomalyState ? anomalyState.state === "on" : !isOptimal;
        if (hasAnomaly && healthState && healthState.attributes && healthState.attributes.anomalies && healthState.attributes.anomalies.length > 0) {
          alertBox.className = "alert-box alert-err";
          const items = healthState.attributes.anomalies.map(a => `• <b>${a.zone}</b>: ${a.description}`).join('<br>');
          alertDesc.innerHTML = items;
        } else if (isWarning) {
          alertBox.className = "alert-box alert-err";
          alertDesc.innerText = t('attention_cycles');
        } else {
          alertBox.className = "alert-box alert-ok";
          alertDesc.innerText = t('no_anomalies');
        }
      }

      // OpenTherm Telemetry Update
      const otGrid = this.shadowRoot.getElementById('ot-grid');
      const otPressure = this.shadowRoot.getElementById('ot-pressure-val');
      const otFlow = this.shadowRoot.getElementById('ot-flow-val');
      const otReturn = this.shadowRoot.getElementById('ot-return-val');
      const otCondense = this.shadowRoot.getElementById('ot-condense-eval');
      const otMod = this.shadowRoot.getElementById('ot-mod-val');
      const otFlame = this.shadowRoot.getElementById('ot-flame-val');
      const otDhw = this.shadowRoot.getElementById('ot-dhw-badge');

      if (otGrid && healthState && healthState.attributes && healthState.attributes.opentherm && healthState.attributes.opentherm.enabled) {
        const ot = healthState.attributes.opentherm;
        otGrid.style.display = 'block';

        if (otPressure) {
          if (ot.water_pressure !== null && ot.water_pressure !== undefined) {
            otPressure.innerText = `${ot.water_pressure} bar`;
            otPressure.style.color = (ot.water_pressure < 0.8) ? '#f87171' : (ot.water_pressure > 2.5 ? '#fbbf24' : '#34d399');
          } else {
            otPressure.innerText = '-- bar';
            otPressure.style.color = 'inherit';
          }
        }

        if (otFlow) {
          const flowVal = ot.flow_temperature !== undefined && ot.flow_temperature !== null ? ot.flow_temperature :
                          (ot.flow_temp !== undefined && ot.flow_temp !== null ? ot.flow_temp : ot.water_flow_temperature);
          if (flowVal !== null && flowVal !== undefined && flowVal !== "") {
            const num = parseFloat(flowVal);
            const displayVal = !isNaN(num) ? (Number.isInteger(num) ? num : num.toFixed(1)) : flowVal;
            otFlow.innerText = `${displayVal}°C`;
          } else {
            otFlow.innerText = '--°C';
          }
        }

        if (otReturn) {
          if (ot.return_temperature !== null && ot.return_temperature !== undefined) {
            otReturn.innerText = `${ot.return_temperature}°C`;
            if (otCondense) {
              if (ot.condensing_optimal) {
                otCondense.innerText = t('ot_condensing_ok');
                otCondense.style.color = '#34d399';
              } else {
                otCondense.innerText = t('ot_return_hot');
                otCondense.style.color = '#fbbf24';
              }
            }
          } else {
            otReturn.innerText = '--°C';
            if (otCondense) otCondense.innerText = '';
          }
        }

        if (otMod) {
          if (ot.modulation_level !== null && ot.modulation_level !== undefined) {
            otMod.innerText = `${ot.modulation_level}%`;
          } else {
            otMod.innerText = '--%';
          }
        }

        if (otFlame) {
          if (ot.flame_active) {
            otFlame.innerHTML = `<span style="color: #f59e0b;">${t('ot_flame_on')}</span>`;
          } else {
            otFlame.innerHTML = `<span style="color: #94a3b8;">${t('ot_flame_off')}</span>`;
          }
        }

        if (otDhw) {
          otDhw.style.display = ot.dhw_active ? 'inline-block' : 'none';
          otDhw.innerText = t('ot_dhw_active');
        }
      } else if (otGrid) {
        otGrid.style.display = 'none';
      }
    } catch (err) {
      console.error("Error updating MultizoneThermostatPlantCard:", err);
    }
  }
}

if (!customElements.get("multizone-thermostat-plant-card")) {
  customElements.define("multizone-thermostat-plant-card", MultizoneThermostatPlantCard);
}

/* ==================== ZONE ENERGY CARD ==================== */
