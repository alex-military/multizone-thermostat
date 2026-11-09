class MultizoneThermostatPresetCard extends HTMLElement {
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
    this.renderStructure();
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
    this._config = Object.assign({}, config || {});
    this.renderStructure();
    this.updateCard();
  }

  getCardSize() {
    return 2;
  }

  static getConfigElement() {
    return document.createElement("multizone-thermostat-preset-card-editor");
  }

  static getStubConfig() {
    return {
      entity: "",
      title: ""
    };
  }

  get presetEntity() {
    if (this._config && this._config.entity) {
      return this._config.entity;
    }
    return findPresetEntity(this._hass);
  }

  renderStructure() {
    const radius = (this._config && this._config.border_radius) ? this._config.border_radius : '20px';
    const isClassic = (this.getEffectiveStyle() === 'classic');

    const styleContent = isClassic ? `
      :host {
        display: block;
        height: 100%;
        box-sizing: border-box;
      }
      ha-card {
        padding: 18px 16px;
        border-radius: ${radius} !important;
        overflow: hidden !important;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        gap: 12px;
        background: var(--ha-card-background, var(--card-background-color, #1c1c1e)) !important;
        border: var(--ha-card-border-width, 1px) solid var(--ha-card-border-color, var(--divider-color, rgba(255, 255, 255, 0.12))) !important;
        box-shadow: var(--ha-card-box-shadow, 0 2px 8px rgba(0, 0, 0, 0.2)) !important;
        backdrop-filter: none !important;
        -webkit-backdrop-filter: none !important;
        box-sizing: border-box;
        height: 100%;
        min-height: 96px;
      }
      .header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 8px;
        font-size: 11px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.8px;
        color: var(--secondary-text-color, #94a3b8);
      }
      .header-left {
        display: flex;
        align-items: center;
        gap: 6px;
      }
      .mode-switch-wrap {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        cursor: pointer;
        user-select: none;
      }
      .mode-switch-label {
        font-size: 11px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        transition: color 0.25s ease;
      }
      .mode-switch-wrap.heat .mode-switch-label { color: #fb923c; }
      .mode-switch-wrap.cool .mode-switch-label { color: #38bdf8; }
      .mode-switch-track {
        position: relative;
        width: 56px;
        height: 28px;
        border-radius: 9999px;
        background: rgba(15, 23, 42, 0.9);
        border: 1px solid rgba(255, 255, 255, 0.18);
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 0 6px;
        box-sizing: border-box;
        transition: all 0.25s ease;
      }
      .mode-switch-wrap.heat .mode-switch-track {
        border-color: rgba(249, 115, 22, 0.5);
        background: rgba(249, 115, 22, 0.15);
      }
      .mode-switch-wrap.cool .mode-switch-track {
        border-color: rgba(56, 189, 248, 0.5);
        background: rgba(56, 189, 248, 0.15);
      }
      .track-icon {
        --mdc-icon-size: 14px;
        z-index: 1;
        transition: opacity 0.25s ease, color 0.25s ease;
      }
      .track-icon.fire { color: #fb923c; opacity: 0.45; }
      .track-icon.snow { color: #38bdf8; opacity: 0.45; }
      .mode-switch-thumb {
        position: absolute;
        top: 2px;
        left: 2px;
        width: 22px;
        height: 22px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        transition: transform 0.28s cubic-bezier(0.34, 1.56, 0.64, 1), background 0.25s ease, box-shadow 0.25s ease;
        z-index: 2;
      }
      .mode-switch-thumb ha-icon {
        --mdc-icon-size: 14px;
        color: #ffffff;
      }
      .mode-switch-wrap.heat .mode-switch-thumb {
        transform: translateX(0px);
        background: linear-gradient(135deg, #f97316, #ea580c);
        box-shadow: 0 2px 8px rgba(249, 115, 22, 0.6);
      }
      .mode-switch-wrap.cool .mode-switch-thumb {
        transform: translateX(28px);
        background: linear-gradient(135deg, #38bdf8, #0284c7);
        box-shadow: 0 2px 8px rgba(56, 189, 248, 0.6);
      }
      .preset-grid {
        display: grid;
        grid-template-columns: repeat(5, 1fr);
        gap: 8px;
        width: 100%;
        box-sizing: border-box;
        align-items: stretch;
      }
      .preset-btn {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        padding: 10px 4px;
        border-radius: 12px;
        background: var(--card-background-color, #202b38);
        border: 1px solid var(--divider-color, rgba(255, 255, 255, 0.12));
        color: var(--secondary-text-color, #94a3b8);
        cursor: pointer;
        transition: all 0.2s ease;
        gap: 6px;
        min-height: 52px;
        box-sizing: border-box;
      }
      .preset-btn:hover {
        background: rgba(255, 255, 255, 0.08);
        color: var(--primary-text-color, white);
      }
      .preset-btn.active {
        background: var(--primary-color, #0284c7) !important;
        border-color: var(--primary-color, #0284c7) !important;
        color: #ffffff !important;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
      }
      .preset-btn ha-icon {
        --mdc-icon-size: 22px;
        color: inherit;
      }
      .preset-label {
        font-size: 11px;
        font-weight: 700;
        letter-spacing: 0.2px;
      }
      .priority-segmented {
        display: flex;
        align-items: center;
        gap: 3px;
        background: var(--card-background-color, #202b38);
        padding: 3px;
        border-radius: 9999px;
        border: 1px solid var(--divider-color, rgba(255, 255, 255, 0.15));
        flex: 1;
        justify-content: space-between;
      }
      .priority-btn {
        background: transparent;
        border: none;
        color: var(--secondary-text-color, #94a3b8);
        font-size: 11px;
        font-weight: 600;
        padding: 4px 8px;
        border-radius: 9999px;
        cursor: pointer;
        transition: all 0.2s ease;
        text-align: center;
        flex: 1;
        white-space: nowrap;
      }
      .priority-btn:hover {
        color: var(--primary-text-color, #ffffff);
        background: rgba(255, 255, 255, 0.08);
      }
      .priority-btn.active {
        color: #ffffff;
        background: #f97316;
        box-shadow: 0 2px 6px rgba(249, 115, 22, 0.4);
      }
      .priority-btn.active.electric {
        background: #38bdf8;
        box-shadow: 0 2px 6px rgba(56, 189, 248, 0.4);
      }
      .priority-btn.active.combined {
        background: #fcd34d;
        color: #0f172a;
        box-shadow: 0 2px 6px rgba(252, 211, 77, 0.4);
      }
      .priority-btn.active.hybrid {
        background: #10b981;
        box-shadow: 0 2px 6px rgba(16, 185, 129, 0.4);
      }
      .summer-indicator {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        background: rgba(56, 189, 248, 0.12);
        border: 1px solid rgba(56, 189, 248, 0.25);
        color: #38bdf8;
        padding: 4px 12px;
        border-radius: 9999px;
        font-size: 11px;
        font-weight: 700;
        letter-spacing: 0.3px;
        height: 28px;
        box-sizing: border-box;
      }
    ` : `
      :host {
        display: block;
        height: 100%;
        box-sizing: border-box;
      }
      ha-card {
        padding: 18px 16px;
        border-radius: ${radius} !important;
        overflow: hidden !important;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        gap: 12px;
        background: linear-gradient(135deg, rgba(20, 27, 41, 0.88) 0%, rgba(15, 23, 42, 0.94) 100%) !important;
        backdrop-filter: blur(20px) !important;
        -webkit-backdrop-filter: blur(20px) !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        box-shadow: 0 10px 30px -10px rgba(0, 0, 0, 0.5), inset 0 1px 0 rgba(255, 255, 255, 0.08) !important;
        box-sizing: border-box;
        height: 100%;
        min-height: 96px;
        transition: border-color 0.3s ease, box-shadow 0.3s ease;
      }
      ha-card.cooling-mode {
        border-color: rgba(56, 189, 248, 0.25) !important;
        box-shadow: 0 10px 30px -10px rgba(14, 165, 233, 0.2), inset 0 1px 0 rgba(56, 189, 248, 0.15) !important;
      }
      .header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 8px;
        font-size: 11px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 1px;
        color: #94a3b8;
      }
      .header-left {
        display: flex;
        align-items: center;
        gap: 6px;
      }
      .mode-switch-wrap {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        cursor: pointer;
        user-select: none;
        padding: 2px 4px;
        border-radius: 9999px;
        transition: transform 0.2s ease;
      }
      .mode-switch-wrap:hover {
        transform: scale(1.03);
      }
      .mode-switch-wrap:active {
        transform: scale(0.97);
      }
      .mode-switch-label {
        font-size: 11px;
        font-weight: 800;
        text-transform: uppercase;
        letter-spacing: 0.6px;
        transition: color 0.25s ease;
      }
      .mode-switch-wrap.heat .mode-switch-label {
        color: #fb923c;
        text-shadow: 0 0 10px rgba(249, 115, 22, 0.35);
      }
      .mode-switch-wrap.cool .mode-switch-label {
        color: #38bdf8;
        text-shadow: 0 0 10px rgba(56, 189, 248, 0.35);
      }
      .mode-switch-track {
        position: relative;
        width: 58px;
        height: 28px;
        border-radius: 9999px;
        background: rgba(15, 23, 42, 0.9);
        border: 1px solid rgba(255, 255, 255, 0.14);
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 0 7px;
        box-sizing: border-box;
        transition: all 0.3s ease;
        box-shadow: inset 0 2px 5px rgba(0, 0, 0, 0.5);
      }
      .mode-switch-wrap.heat .mode-switch-track {
        border-color: rgba(249, 115, 22, 0.45);
        background: linear-gradient(90deg, rgba(249, 115, 22, 0.2) 0%, rgba(15, 23, 42, 0.9) 100%);
        box-shadow: 0 0 12px rgba(249, 115, 22, 0.2), inset 0 1px 3px rgba(0, 0, 0, 0.5);
      }
      .mode-switch-wrap.cool .mode-switch-track {
        border-color: rgba(56, 189, 248, 0.45);
        background: linear-gradient(90deg, rgba(15, 23, 42, 0.9) 0%, rgba(56, 189, 248, 0.2) 100%);
        box-shadow: 0 0 12px rgba(56, 189, 248, 0.2), inset 0 1px 3px rgba(0, 0, 0, 0.5);
      }
      .track-icon {
        --mdc-icon-size: 14px;
        z-index: 1;
        transition: opacity 0.25s ease, transform 0.25s ease;
      }
      .track-icon.fire { color: #fb923c; opacity: 0.45; }
      .track-icon.snow { color: #38bdf8; opacity: 0.45; }
      .mode-switch-thumb {
        position: absolute;
        top: 2px;
        left: 2px;
        width: 22px;
        height: 22px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        transition: transform 0.3s cubic-bezier(0.34, 1.56, 0.64, 1), background 0.25s ease, box-shadow 0.25s ease;
        z-index: 2;
      }
      .mode-switch-thumb ha-icon {
        --mdc-icon-size: 14px;
        color: #ffffff;
      }
      .mode-switch-wrap.heat .mode-switch-thumb {
        transform: translateX(0px);
        background: linear-gradient(135deg, #fb923c 0%, #ea580c 100%);
        box-shadow: 0 0 10px rgba(249, 115, 22, 0.8), 0 2px 4px rgba(0, 0, 0, 0.4);
      }
      .mode-switch-wrap.cool .mode-switch-thumb {
        transform: translateX(30px);
        background: linear-gradient(135deg, #38bdf8 0%, #0284c7 100%);
        box-shadow: 0 0 10px rgba(56, 189, 248, 0.8), 0 2px 4px rgba(0, 0, 0, 0.4);
      }
      .preset-grid {
        display: grid;
        grid-template-columns: repeat(5, 1fr);
        gap: 8px;
        width: 100%;
        box-sizing: border-box;
        align-items: stretch;
      }
      .preset-btn {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        padding: 10px 4px;
        border-radius: 14px;
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(255, 255, 255, 0.08);
        color: #94a3b8;
        cursor: pointer;
        transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);
        gap: 6px;
        min-height: 52px;
        box-sizing: border-box;
      }
      .preset-btn:hover {
        background: rgba(255, 255, 255, 0.08);
        color: #ffffff;
        transform: translateY(-2px);
      }
      .preset-btn.active.manual {
        background: rgba(14, 165, 233, 0.2) !important;
        border-color: #38bdf8 !important;
        color: #38bdf8 !important;
        box-shadow: 0 0 15px rgba(56, 189, 248, 0.35) !important;
      }
      .preset-btn.active.eco {
        background: rgba(16, 185, 129, 0.2) !important;
        border-color: #10b981 !important;
        color: #34d399 !important;
        box-shadow: 0 0 15px rgba(16, 185, 129, 0.35) !important;
      }
      .preset-btn.active.comfort {
        background: rgba(245, 158, 11, 0.2) !important;
        border-color: #f59e0b !important;
        color: #fbbf24 !important;
        box-shadow: 0 0 15px rgba(245, 158, 11, 0.35) !important;
      }
      .cooling-mode .preset-btn.active.comfort {
        background: rgba(14, 165, 233, 0.2) !important;
        border-color: #38bdf8 !important;
        color: #38bdf8 !important;
        box-shadow: 0 0 15px rgba(56, 189, 248, 0.35) !important;
      }
      .preset-btn.active.sleep {
        background: rgba(99, 102, 241, 0.2) !important;
        border-color: #6366f1 !important;
        color: #818cf8 !important;
        box-shadow: 0 0 15px rgba(99, 102, 241, 0.35) !important;
      }
      .preset-btn.active.away {
        background: rgba(239, 68, 68, 0.2) !important;
        border-color: #ef4444 !important;
        color: #f87171 !important;
        box-shadow: 0 0 15px rgba(239, 68, 68, 0.35) !important;
      }
      .cooling-mode .preset-btn.active.away {
        background: rgba(100, 116, 139, 0.2) !important;
        border-color: #94a3b8 !important;
        color: #cbd5e1 !important;
        box-shadow: 0 0 15px rgba(100, 116, 139, 0.35) !important;
      }
      .preset-btn ha-icon {
        --mdc-icon-size: 22px;
        color: inherit;
      }
      .preset-label {
        font-size: 11px;
        font-weight: 700;
        letter-spacing: 0.3px;
      }
      .priority-wrap {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 6px;
        padding-top: 8px;
        border-top: 1px solid rgba(255, 255, 255, 0.08);
      }
      .priority-label {
        font-size: 10px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.8px;
        color: #94a3b8;
        white-space: nowrap;
      }
      
      .summer-indicator {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        background: rgba(56, 189, 248, 0.12);
        border: 1px solid rgba(56, 189, 248, 0.25);
        color: #38bdf8;
        padding: 4px 12px;
        border-radius: 9999px;
        font-size: 11px;
        font-weight: 700;
        letter-spacing: 0.3px;
        height: 28px;
        box-sizing: border-box;
      }

      .priority-segmented {
        display: flex;
        align-items: center;
        gap: 3px;
        background: rgba(15, 23, 42, 0.7);
        padding: 3px;
        border-radius: 9999px;
        border: 1px solid rgba(255, 255, 255, 0.08);
        flex: 1;
        justify-content: space-between;
      }
      .priority-btn {
        background: transparent;
        border: none;
        color: #94a3b8;
        font-size: 10px;
        font-weight: 700;
        padding: 4px 8px;
        border-radius: 9999px;
        cursor: pointer;
        transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1);
        text-align: center;
        flex: 1;
        white-space: nowrap;
      }
      .priority-btn:hover {
        color: #ffffff;
        background: rgba(255, 255, 255, 0.08);
      }
      .priority-btn.active {
        color: #ffffff;
        background: #f97316;
        box-shadow: 0 2px 8px rgba(249, 115, 22, 0.4);
      }
      .priority-btn.active.electric {
        background: #38bdf8;
        box-shadow: 0 2px 8px rgba(56, 189, 248, 0.4);
      }
      .priority-btn.active.combined {
        background: #fcd34d;
        color: #0f172a;
        box-shadow: 0 2px 8px rgba(252, 211, 77, 0.4);
      }
      .priority-btn.active.hybrid {
        background: #10b981;
        box-shadow: 0 2px 8px rgba(16, 185, 129, 0.4);
      }

    `;

    this.shadowRoot.innerHTML = `
      <style>${styleContent}</style>
      <ha-card id="preset-card-container">
        <div class="header">
          <div class="header-left">
            <div class="priority-segmented" id="priority-segmented">
              <button class="priority-btn" data-priority="auto" id="pbtn-auto" title="Automatica (Solare + Gas)">Auto</button>
              <button class="priority-btn" data-priority="hybrid" id="pbtn-hybrid" title="Ibrido (Split solo se surplus solare)">Ibrido</button>
              <button class="priority-btn" data-priority="combined" id="pbtn-combined" title="Combinato (Caldaia + Split insieme)">Combinato</button>
              <button class="priority-btn" data-priority="electric_only" id="pbtn-electric" title="Solo Elettrico (Blocca Caldaia)">Elettrico</button>
              <button class="priority-btn" data-priority="gas_only" id="pbtn-gas" title="Solo Gas (Split spenti in caldo)">Gas</button>
            </div>
            <div class="summer-indicator" id="summer-indicator" style="display: none;">
              <ha-icon icon="mdi:snowflake" style="--mdc-icon-size: 15px; color: #38bdf8;"></ha-icon>
              <span>Raffrescamento Elettrico</span>
            </div>
          </div>
          <div class="mode-switch-wrap heat" id="btn-mode-toggle" role="switch" aria-checked="false" title="Commuta Riscaldamento / Raffrescamento">
            <span class="mode-switch-label" id="mode-toggle-label">${getTranslation(this._hass, 'master_mode_heat') || 'Caldo'}</span>
            <div class="mode-switch-track">
              <ha-icon class="track-icon fire" icon="mdi:fire"></ha-icon>
              <ha-icon class="track-icon snow" icon="mdi:snowflake"></ha-icon>
              <div class="mode-switch-thumb">
                <ha-icon id="mode-toggle-icon" icon="mdi:fire"></ha-icon>
              </div>
            </div>
          </div>
        </div>
        <div class="preset-grid">
          <div class="preset-btn" data-preset="manual" id="btn-manual">
            <ha-icon icon="mdi:power"></ha-icon>
            <span class="preset-label">${getTranslation(this._hass, 'preset_manual') || 'Manuale'}</span>
          </div>
          <div class="preset-btn" data-preset="eco" id="btn-eco">
            <ha-icon icon="mdi:leaf"></ha-icon>
            <span class="preset-label">${getTranslation(this._hass, 'preset_eco') || 'Eco'}</span>
          </div>
          <div class="preset-btn" data-preset="comfort" id="btn-comfort">
            <ha-icon icon="mdi:sofa"></ha-icon>
            <span class="preset-label">${getTranslation(this._hass, 'preset_comfort') || 'Comfort'}</span>
          </div>
          <div class="preset-btn" data-preset="sleep" id="btn-sleep">
            <ha-icon icon="mdi:bed"></ha-icon>
            <span class="preset-label">${getTranslation(this._hass, 'preset_sleep') || 'Notte'}</span>
          </div>
          <div class="preset-btn" data-preset="away" id="btn-away">
            <ha-icon icon="mdi:car"></ha-icon>
            <span class="preset-label">${getTranslation(this._hass, 'preset_away') || 'Fuori Casa'}</span>
          </div>
        </div>
      </ha-card>
    `;

    const modeBtn = this.shadowRoot.querySelector('#btn-mode-toggle');
    if (modeBtn) {
      modeBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        this.toggleMasterMode();
      });
    }

    const buttons = this.shadowRoot.querySelectorAll('.preset-btn');
    buttons.forEach(btn => {
      btn.addEventListener('click', () => {
        const preset = btn.getAttribute('data-preset');
        this.selectPreset(preset);
      });
    });

    const pBtns = this.shadowRoot.querySelectorAll('.priority-btn');
    pBtns.forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        const prio = btn.getAttribute('data-priority');
        this.selectHeatPriority(prio);
      });
    });
  }

  toggleMasterMode() {
    if (!this._hass) return;
    const currentMode = getMasterHVACMode(this._hass);
    const newMode = (currentMode === 'cool') ? 'heat' : 'cool';

    const modeEntity = findMasterOperationModeEntity(this._hass);
    if (modeEntity) {
      this._hass.callService("select", "select_option", {
        entity_id: modeEntity,
        option: newMode
      });
    } else {
      this._hass.callService("multizone_thermostat", "set_master_operation_mode", {
        operation_mode: newMode
      });
    }
  }

  selectHeatPriority(priority) {
    if (!this._hass) return;
    const priorityEntity = typeof findHeatSourcePriorityEntity === 'function' ? findHeatSourcePriorityEntity(this._hass) : null;
    if (!priorityEntity) return;

    this._hass.callService("select", "select_option", {
      entity_id: priorityEntity,
      option: priority
    });
  }

  selectPreset(preset) {
    if (!this._hass) return;
    const entityId = this.presetEntity;
    if (!entityId) return;

    let targetOption = preset;
    if (targetOption === 'none') targetOption = 'manual';

    this._hass.callService("select", "select_option", {
      entity_id: entityId,
      option: targetOption
    });
  }

  updateCard() {
    if (!this._hass || !this._hass.states) return;

    // 1. Update Master Mode Toggle (Heat vs Cool)
    const masterMode = getMasterHVACMode(this._hass);
    const isCool = (masterMode === 'cool');

    const card = this.shadowRoot.querySelector('#preset-card-container');
    const modeBtn = this.shadowRoot.querySelector('#btn-mode-toggle');
    const modeIcon = this.shadowRoot.querySelector('#mode-toggle-icon');
    const modeLabel = this.shadowRoot.querySelector('#mode-toggle-label');

    if (card) {
      if (isCool) {
        card.classList.add('cooling-mode');
      } else {
        card.classList.remove('cooling-mode');
      }
    }

    if (modeBtn) {
      modeBtn.setAttribute('aria-checked', isCool ? 'true' : 'false');
      if (isCool) {
        modeBtn.classList.remove('heat');
        modeBtn.classList.add('cool');
        if (modeIcon) {
          modeIcon.icon = "mdi:snowflake";
          modeIcon.style.color = "#38bdf8";
        }
        if (modeLabel) modeLabel.textContent = getTranslation(this._hass, 'master_mode_cool') || 'Freddo';
      } else {
        modeBtn.classList.remove('cool');
        modeBtn.classList.add('heat');
        if (modeIcon) {
          modeIcon.icon = "mdi:fire";
          modeIcon.style.color = "#fb923c";
        }
        if (modeLabel) modeLabel.textContent = getTranslation(this._hass, 'master_mode_heat') || 'Caldo';
      }
    }

    // 2. Update Heat Source Priority Selector in Header
    const prioritySegmented = this.shadowRoot.querySelector('#priority-segmented');
    const summerIndicator = this.shadowRoot.querySelector('#summer-indicator');
    if (prioritySegmented && summerIndicator) {
      if (isCool) {
        prioritySegmented.style.display = 'none';
        summerIndicator.style.display = 'inline-flex';
      } else {
        prioritySegmented.style.display = 'flex';
        summerIndicator.style.display = 'none';

        const priorityEntity = typeof findHeatSourcePriorityEntity === 'function' ? findHeatSourcePriorityEntity(this._hass) : null;
        let currentPriority = 'auto';
        if (priorityEntity && this._hass.states[priorityEntity]) {
          currentPriority = this._hass.states[priorityEntity].state;
        }

        const pBtns = this.shadowRoot.querySelectorAll('.priority-btn');
        pBtns.forEach(btn => {
          const prio = btn.getAttribute('data-priority');
          btn.classList.remove('active', 'electric', 'combined', 'hybrid');
          if (prio === currentPriority) {
            btn.classList.add('active');
            if (prio === 'electric_only') btn.classList.add('electric');
            else if (prio === 'combined') btn.classList.add('combined');
            else if (prio === 'hybrid') btn.classList.add('hybrid');
          }
        });
      }
    }

    // 2. Update Active Preset
    const entityId = this.presetEntity;
    if (!entityId) return;

    const stateObj = this._hass.states[entityId];
    if (!stateObj) return;

    const currentPreset = stateObj.state;
    const buttons = this.shadowRoot.querySelectorAll('.preset-btn');
    buttons.forEach(btn => {
      const preset = btn.getAttribute('data-preset');
      const isActive = (preset === currentPreset) || (preset === 'manual' && (currentPreset === 'none' || currentPreset === 'manual'));
      if (isActive) {
        btn.classList.add('active');
        btn.classList.add(preset);
      } else {
        btn.classList.remove('active');
        btn.classList.remove(preset);
      }
    });
  }
}

class MultizoneThermostatPresetCardEditor extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: 'open' });
  }

  setConfig(config) {
    this._config = config;
    this.render();
  }

  set hass(hass) {
    this._hass = hass;
    if (!this._rendered) {
      this.render();
      this._rendered = true;
    }
  }

  configChanged(newConfig) {
    const event = new Event("config-changed", {
      bubbles: true,
      composed: true
    });
    event.detail = { config: newConfig };
    this.dispatchEvent(event);
  }

  render() {
    if (!this._config) return;
    
    // Only build DOM once, then just update values
    if (this.shadowRoot.querySelector('.editor-container')) {
        // Update existing input values
        const titleInput = this.shadowRoot.querySelector('#title-input');
        if (titleInput && titleInput.value !== (this._config.title || '')) {
            titleInput.value = this._config.title || '';
        }
        return;
    }

    if (!this._hass) return;
    const config = this._config || {};
    
    // Auto-discover preset entity if not configured
    let currentEntity = config.entity;
    if (!currentEntity) {
      currentEntity = findPresetEntity(this._hass) || '';
      if (currentEntity) {
        // Defer the config change slightly to let the editor finish rendering
        setTimeout(() => {
          this._config = { ...this._config, entity: currentEntity };
          this.configChanged(this._config);
        }, 100);
      }
    }

    if (this.shadowRoot.hasChildNodes()) {
      this.shadowRoot.innerHTML = '';
    }

    const container = document.createElement('div');
    container.className = 'card-config editor-container';

    // Title Row
    const titleRow = document.createElement('div');
    titleRow.className = 'form-row';
    const titleLabel = document.createElement('label');
    titleLabel.textContent = getTranslation(this._hass, 'edit_title');
    titleLabel.style.display = 'block';
    titleLabel.style.marginBottom = '8px';
    const titleInput = document.createElement('input');
    titleInput.id = 'title-input';
    titleInput.type = 'text';
    titleInput.value = config.title || '';
    titleInput.style.width = '100%';
    titleInput.style.padding = '8px';
    titleInput.style.boxSizing = 'border-box';
    titleInput.addEventListener('input', (e) => {
      if (!this._config) return;
      this._config = { ...this._config, title: e.target.value };
      this.configChanged(this._config);
    });
    titleRow.appendChild(titleLabel);
    titleRow.appendChild(titleInput);
    container.appendChild(titleRow);

    // Entity Row
    const entityRow = document.createElement('div');
    entityRow.className = 'form-row';
    entityRow.style.marginTop = '16px';
    const entityLabel = document.createElement('label');
    entityLabel.textContent = getTranslation(this._hass, 'edit_preset');
    const entityPicker = document.createElement('ha-entity-picker');
    entityPicker.includeDomains = ['select'];
    entityPicker.value = config.entity || '';
    entityPicker.hass = this._hass;
    entityPicker.addEventListener('value-changed', (e) => {
      if (!this._config) return;
      this._config = { ...this._config, entity: e.detail.value };
      this.configChanged(this._config);
    });
    
    entityRow.appendChild(entityLabel);
    entityRow.appendChild(entityPicker);
    container.appendChild(entityRow);

    this.shadowRoot.appendChild(container);
  }
}

// Define elements safely to avoid "already been used" errors on hot-reloads
if (!customElements.get("multizone-thermostat-button-card")) {
  customElements.define("multizone-thermostat-button-card", MultizoneThermostatButtonCard);
}
if (!customElements.get("multizone-thermostat-dial-card")) {
  customElements.define("multizone-thermostat-dial-card", MultizoneThermostatDialCard);
}
if (!customElements.get("multizone-thermostat-status-card")) {
  customElements.define("multizone-thermostat-status-card", MultizoneThermostatStatusCard);
}
if (!customElements.get("multizone-thermostat-card-editor")) {
  customElements.define("multizone-thermostat-card-editor", MultizoneThermostatCardEditor);
}
if (!customElements.get("multizone-thermostat-preset-card")) {
  customElements.define("multizone-thermostat-preset-card", MultizoneThermostatPresetCard);
}
if (!customElements.get("multizone-thermostat-preset-card-editor")) {
  customElements.define("multizone-thermostat-preset-card-editor", MultizoneThermostatPresetCardEditor);
}

/* ==================== SPACER CARD ==================== */
