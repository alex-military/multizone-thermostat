class MultizoneThermostatSpacer extends HTMLElement {
  setConfig(config) {}
  set hass(hass) {}
}

if (!customElements.get("multizone-thermostat-spacer")) {
  customElements.define("multizone-thermostat-spacer", MultizoneThermostatSpacer);
}

/* ==================== HEALTH SUMMARY CARD ==================== */
/* ==================== SCHEDULE SUMMARY NAVIGATION BUTTON CARD ==================== */

function closeMzStandaloneModal() {
  const existing = document.getElementById('mz-standalone-nav-overlay');
  if (existing) {
    existing.remove();
  }
}

function getGlobalHass() {
  if (window.hass) return window.hass;
  try {
    const ha = document.querySelector('home-assistant');
    if (ha && ha.hass) return ha.hass;
  } catch (e) {}
  try {
    const grid = document.querySelector('multizone-thermostat-responsive-grid') || document.querySelector('multizone-thermostat-nav-card');
    if (grid && grid._hass) return grid._hass;
  } catch (e) {}
  return null;
}

function openMzStandaloneModal(type, hass) {
  closeMzStandaloneModal();
  const effectiveHass = hass || getGlobalHass();

  const overlay = document.createElement('div');
  overlay.id = 'mz-standalone-nav-overlay';
  overlay.style.cssText = [
    'position: fixed',
    'inset: 0',
    'z-index: 999999',
    'background: rgba(10, 15, 29, 0.90)',
    'backdrop-filter: blur(12px)',
    '-webkit-backdrop-filter: blur(12px)',
    'overflow-y: auto',
    'padding: 24px 16px',
    'box-sizing: border-box',
    'display: flex',
    'flex-direction: column',
    'align-items: center'
  ].join(';');

  const wrapper = document.createElement('div');
  wrapper.style.cssText = 'width: 100%; max-width: 1200px; margin: 0 auto; box-sizing: border-box;';

  const topBar = document.createElement('div');
  topBar.style.cssText = 'display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; padding: 0 4px;';

  const titleEl = document.createElement('div');
  titleEl.style.cssText = 'font-size: 1.2rem; font-weight: 700; color: #ffffff; display: flex; align-items: center; gap: 10px;';
  titleEl.innerHTML = type === 'scheduler'
    ? '<ha-icon icon="mdi:calendar-clock" style="color:#38bdf8;"></ha-icon> <span>Programmazione Fasce Orarie</span>'
    : '<ha-icon icon="mdi:chart-box-outline" style="color:#10b981;"></ha-icon> <span>Diagnostica & Impianto</span>';

  const closeBtn = document.createElement('button');
  closeBtn.innerHTML = '✕ Chiudi';
  closeBtn.style.cssText = [
    'background: rgba(255, 255, 255, 0.14)',
    'color: #ffffff',
    'border: 1px solid rgba(255, 255, 255, 0.25)',
    'border-radius: 10px',
    'padding: 8px 18px',
    'font-size: 0.95rem',
    'font-weight: 600',
    'cursor: pointer',
    'transition: background 0.2s ease'
  ].join(';');
  closeBtn.onmouseover = () => { closeBtn.style.background = 'rgba(255, 255, 255, 0.25)'; };
  closeBtn.onmouseout = () => { closeBtn.style.background = 'rgba(255, 255, 255, 0.14)'; };

  const dismissModal = () => {
    closeMzStandaloneModal();
    window.removeEventListener('keydown', keyHandler);
  };

  const keyHandler = (e) => {
    if (e.key === 'Escape') dismissModal();
  };
  window.addEventListener('keydown', keyHandler);
  closeBtn.addEventListener('click', dismissModal);

  topBar.appendChild(titleEl);
  topBar.appendChild(closeBtn);
  wrapper.appendChild(topBar);

  let innerCard;
  if (type === 'scheduler') {
    innerCard = document.createElement('multizone-thermostat-scheduler-card');
  } else {
    innerCard = document.createElement('multizone-thermostat-plant-card');
  }
  if (typeof innerCard.setConfig === 'function') {
    innerCard.setConfig({ border_radius: '16px' });
  }
  if (effectiveHass) {
    innerCard.hass = effectiveHass;
  }
  wrapper.appendChild(innerCard);
  overlay.appendChild(wrapper);

  overlay.addEventListener('click', (e) => {
    if (e.target === overlay) dismissModal();
  });

  document.body.appendChild(overlay);
}

function findLovelaceConfig(el) {
  let node = el;
  while (node) {
    if (node.lovelace && node.lovelace.config && Array.isArray(node.lovelace.config.views)) {
      return node.lovelace.config;
    }
    if (node.config && Array.isArray(node.config.views)) {
      return node.config;
    }
    node = node.parentNode || node.host || null;
  }
  try {
    const ha = document.querySelector('home-assistant');
    const main = ha && ha.shadowRoot && ha.shadowRoot.querySelector('home-assistant-main');
    const resolver = main && main.shadowRoot && main.shadowRoot.querySelector('partial-panel-resolver, ha-panel-lovelace');
    const panel = resolver && (resolver.tagName === 'HA-PANEL-LOVELACE' ? resolver : (resolver.shadowRoot && resolver.shadowRoot.querySelector('ha-panel-lovelace')));
    if (panel && panel.lovelace && panel.lovelace.config && Array.isArray(panel.lovelace.config.views)) {
      return panel.lovelace.config;
    }
  } catch (e) {}
  return null;
}

function haNavigate(node, path) {
  if (!path) return;
  // 1. Dispatch hass-action (official Lovelace action handler)
  try {
    const actionEv = new CustomEvent('hass-action', {
      detail: {
        config: {
          tap_action: {
            action: 'navigate',
            navigation_path: path
          }
        },
        action: 'tap'
      },
      bubbles: true,
      composed: true
    });
    (node || document.body).dispatchEvent(actionEv);
  } catch (e) {}

  // 2. Dispatch hass-navigate (Lovelace router event)
  try {
    const navEv = new CustomEvent('hass-navigate', {
      detail: { path: path },
      bubbles: true,
      composed: true
    });
    (node || document.body).dispatchEvent(navEv);
  } catch (e) {}

  // 3. Low-level history API and location-changed event (standard HA navigate.ts)
  try {
    if (window.location.pathname !== path) {
      window.history.pushState(null, '', path);
      const locEv = new CustomEvent('location-changed', {
        detail: { replace: false },
        bubbles: true,
        composed: true
      });
      (node || window).dispatchEvent(locEv);
      window.dispatchEvent(new CustomEvent('location-changed'));
    }
  } catch (e) {}
}

function navigateOrFallbackModal(hostEl, targetPath, onFallback) {
  let normalizedPath = targetPath || 'programmazione';
  if (normalizedPath === 'schedulatore') normalizedPath = 'programmazione';

  // 1. Resolve dashboard base and target fullPath
  const parts = window.location.pathname.split('/').filter(Boolean);
  const dashboardBase = parts.length > 0 ? `/${parts[0]}` : '/lovelace';
  let fullPath = normalizedPath.startsWith('/') 
    ? normalizedPath 
    : `${dashboardBase}/${normalizedPath}`;

  const llConfig = findLovelaceConfig(hostEl);
  let hasMatchingView = false;

  if (llConfig && Array.isArray(llConfig.views)) {
    const matchedView = llConfig.views.find((v, idx) => {
      const p = (v.path !== undefined && v.path !== null && v.path !== '') ? String(v.path) : String(idx);
      if (p.toLowerCase() === normalizedPath.toLowerCase() || (normalizedPath === 'programmazione' && p.toLowerCase() === 'schedulatore')) {
        fullPath = `${dashboardBase}/${p}`;
        return true;
      }
      const stratType = (v.strategy && v.strategy.type) ? String(v.strategy.type) : '';
      if ((normalizedPath === 'programmazione' || normalizedPath === 'schedulatore') && stratType.includes('multizone-thermostat-scheduler')) {
        fullPath = `${dashboardBase}/${p}`;
        return true;
      }
      if (normalizedPath === 'diagnostica' && stratType.includes('multizone-thermostat-diagnostics')) {
        fullPath = `${dashboardBase}/${p}`;
        return true;
      }
      return false;
    });

    if (matchedView) {
      hasMatchingView = true;
    } else {
      // Lovelace config exists but does not contain target view: open fallback modal immediately
      if (typeof onFallback === 'function') {
        onFallback();
        return;
      }
    }
  }

  // 2. Perform navigation
  const initialPath = window.location.pathname;
  haNavigate(hostEl, fullPath);

  // 3. Fallback verification: if path hasn't changed after 150ms and fallback is provided
  setTimeout(() => {
    if (window.location.pathname === initialPath && window.location.pathname !== fullPath) {
      if (typeof onFallback === 'function') {
        onFallback();
      }
    }
  }, 150);
}

function navigateToLovelaceView(viewSlug) {
  const type = (viewSlug === 'programmazione' || viewSlug === 'schedulatore') ? 'scheduler' : 'diagnostics';
  navigateOrFallbackModal(document.body, viewSlug, () => openMzStandaloneModal(type, null));
}

/* ==================== SUMMARY NAVIGATION CARDS ==================== */
class MultizoneThermostatScheduleSummaryCard extends HTMLElement {
  getCardSize() { return 3; }
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
    this._config = config || {};
    if (!this._rendered) this.renderStructure();
    this.updateCard();
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
        padding: 14px 10px;
        border-radius: ${radius} !important;
        overflow: hidden !important;
        background: var(--ha-card-background, var(--card-background-color, #1c1c1e)) !important;
        border: var(--ha-card-border-width, 1px) solid var(--ha-card-border-color, var(--divider-color, rgba(255, 255, 255, 0.12))) !important;
        box-shadow: var(--ha-card-box-shadow, 0 2px 8px rgba(0, 0, 0, 0.2)) !important;
        backdrop-filter: none !important;
        -webkit-backdrop-filter: none !important;
        color: var(--primary-text-color, white);
        display: flex;
        align-items: center;
        justify-content: center;
        height: 100%;
        min-height: 96px;
        cursor: pointer;
        transition: all 0.2s ease;
        box-sizing: border-box;
      }
      ha-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3) !important;
      }
      .badge-content {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        text-align: center;
        gap: 4px;
        width: 100%;
      }
      .icon-box {
        width: 36px;
        height: 36px;
        border-radius: 10px;
        background: var(--secondary-background-color, rgba(255, 255, 255, 0.06));
        border: 1px solid var(--divider-color, rgba(255, 255, 255, 0.12));
        display: flex;
        align-items: center;
        justify-content: center;
        color: var(--primary-color, #0284c7);
      }
      .icon-box ha-icon { --mdc-icon-size: 20px; }
      .badge-title {
        font-size: 11px;
        font-weight: 700;
        letter-spacing: 0.2px;
        color: var(--primary-text-color, #ffffff);
      }
      .badge-pill {
        display: inline-flex;
        align-items: center;
        gap: 4px;
        padding: 2px 6px;
        border-radius: 6px;
        font-size: 9px;
        font-weight: 600;
        background: rgba(255, 255, 255, 0.06);
        color: var(--secondary-text-color, #94a3b8);
        border: 1px solid var(--divider-color, rgba(255, 255, 255, 0.1));
      }
      .badge-dot {
        width: 4px;
        height: 4px;
        border-radius: 50%;
        background: currentColor;
      }
    ` : `
      :host {
        display: block;
        height: 100%;
        box-sizing: border-box;
      }
      ha-card {
        padding: 14px 10px;
        border-radius: ${radius} !important;
        overflow: hidden !important;
        background: linear-gradient(135deg, rgba(20, 27, 41, 0.88) 0%, rgba(15, 23, 42, 0.94) 100%) !important;
        backdrop-filter: blur(20px) !important;
        -webkit-backdrop-filter: blur(20px) !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        box-shadow: 0 10px 30px -10px rgba(0, 0, 0, 0.5), inset 0 1px 0 rgba(255, 255, 255, 0.08) !important;
        color: white;
        display: flex;
        align-items: center;
        justify-content: center;
        height: 100%;
        min-height: 96px;
        cursor: pointer;
        transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);
        box-sizing: border-box;
      }
      ha-card:hover {
        transform: translateY(-2px);
        border-color: rgba(255, 255, 255, 0.16) !important;
        box-shadow: 0 16px 40px -10px rgba(0, 0, 0, 0.7), inset 0 1px 0 rgba(255, 255, 255, 0.12) !important;
      }
      .badge-content {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        text-align: center;
        gap: 5px;
        width: 100%;
      }
      .icon-box {
        width: 38px;
        height: 38px;
        border-radius: 12px;
        background: rgba(255, 255, 255, 0.06);
        border: 1px solid rgba(255, 255, 255, 0.1);
        display: flex;
        align-items: center;
        justify-content: center;
        color: #94a3b8;
        transition: transform 0.2s ease;
      }
      ha-card:hover .icon-box {
        transform: scale(1.08);
      }
      .icon-box ha-icon { --mdc-icon-size: 20px; }
      .badge-title {
        font-size: 11px;
        font-weight: 700;
        letter-spacing: 0.2px;
        color: #ffffff;
      }
      .badge-pill {
        display: inline-flex;
        align-items: center;
        gap: 4px;
        padding: 2px 7px;
        border-radius: 9999px;
        font-size: 9px;
        font-weight: 700;
        letter-spacing: 0.2px;
        text-transform: uppercase;
        background: rgba(148, 163, 184, 0.12);
        color: #94a3b8;
        border: 1px solid rgba(148, 163, 184, 0.25);
      }
      .badge-dot {
        width: 4px;
        height: 4px;
        border-radius: 50%;
        background: currentColor;
        box-shadow: 0 0 4px currentColor;
      }
    `;

    this.shadowRoot.innerHTML = `
      <style>${styleContent}</style>
      <ha-card id="card">
        <div class="badge-content">
          <div class="icon-box" id="icon-box">
            <ha-icon icon="mdi:calendar-clock"></ha-icon>
          </div>
          <div class="badge-title">Programmazione</div>
          <div class="badge-pill" id="pill">
            <span class="badge-dot" id="dot"></span>
            <span id="label">In Pausa</span>
          </div>
        </div>
      </ha-card>
    `;

    const card = this.shadowRoot.getElementById('card');
    const handleSchedClick = (e) => {
      if (e) e.stopPropagation();
      const targetPath = (this._config && this._config.navigation_path) ? this._config.navigation_path : 'programmazione';
      navigateOrFallbackModal(this, targetPath, () => openMzStandaloneModal('scheduler', this._hass));
    };

    if (card) {
      card.addEventListener('click', handleSchedClick);
    }
    this.style.cursor = 'pointer';
    this.onclick = handleSchedClick;

    this._rendered = true;
  }

  updateCard() {
    if (!this._hass || !this._rendered) return;
    const pill = this.shadowRoot.getElementById('pill');
    const label = this.shadowRoot.getElementById('label');
    const dot = this.shadowRoot.getElementById('dot');

    const profileState = this._hass.states['select.multizone_thermostat_active_profile'];
    const activeProfile = profileState ? profileState.state : 'standard';

    if (activeProfile && activeProfile !== 'none') {
      const name = activeProfile.charAt(0).toUpperCase() + activeProfile.slice(1);
      label.textContent = name;
      pill.style.background = 'rgba(56, 189, 248, 0.15)';
      pill.style.color = '#38bdf8';
      pill.style.borderColor = 'rgba(56, 189, 248, 0.35)';
      if (dot) dot.style.background = '#38bdf8';
    } else {
      label.textContent = 'In Pausa';
      pill.style.background = 'rgba(148, 163, 184, 0.12)';
      pill.style.color = '#94a3b8';
      pill.style.borderColor = 'rgba(148, 163, 184, 0.25)';
      if (dot) dot.style.background = '#94a3b8';
    }
  }
}

if (!customElements.get("multizone-thermostat-schedule-summary-card")) {
  customElements.define("multizone-thermostat-schedule-summary-card", MultizoneThermostatScheduleSummaryCard);
}

class MultizoneThermostatHealthSummaryCard extends HTMLElement {
  getCardSize() { return 3; }
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
    this._config = config || {};
    if (!this._rendered) this.renderStructure();
    this.updateCard();
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
        padding: 14px 10px;
        border-radius: ${radius} !important;
        overflow: hidden !important;
        background: var(--ha-card-background, var(--card-background-color, #1c1c1e)) !important;
        border: var(--ha-card-border-width, 1px) solid var(--ha-card-border-color, var(--divider-color, rgba(255, 255, 255, 0.12))) !important;
        box-shadow: var(--ha-card-box-shadow, 0 2px 8px rgba(0, 0, 0, 0.2)) !important;
        backdrop-filter: none !important;
        -webkit-backdrop-filter: none !important;
        color: var(--primary-text-color, white);
        display: flex;
        align-items: center;
        justify-content: center;
        height: 100%;
        min-height: 96px;
        cursor: pointer;
        transition: all 0.2s ease;
        box-sizing: border-box;
      }
      ha-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3) !important;
      }
      .badge-content {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        text-align: center;
        gap: 4px;
        width: 100%;
      }
      .icon-box {
        width: 36px;
        height: 36px;
        border-radius: 10px;
        background: var(--secondary-background-color, rgba(255, 255, 255, 0.06));
        border: 1px solid var(--divider-color, rgba(255, 255, 255, 0.12));
        display: flex;
        align-items: center;
        justify-content: center;
        color: #10b981;
      }
      .icon-box ha-icon { --mdc-icon-size: 20px; }
      .badge-title {
        font-size: 11px;
        font-weight: 700;
        letter-spacing: 0.2px;
        color: var(--primary-text-color, #ffffff);
      }
      .badge-pill {
        display: inline-flex;
        align-items: center;
        gap: 4px;
        padding: 2px 6px;
        border-radius: 6px;
        font-size: 9px;
        font-weight: 600;
        background: rgba(16, 185, 129, 0.12);
        color: #10b981;
        border: 1px solid rgba(16, 185, 129, 0.25);
      }
      .badge-dot {
        width: 4px;
        height: 4px;
        border-radius: 50%;
        background: currentColor;
      }
    ` : `
      :host {
        display: block;
        height: 100%;
        box-sizing: border-box;
      }
      ha-card {
        padding: 14px 10px;
        border-radius: ${radius} !important;
        overflow: hidden !important;
        background: linear-gradient(135deg, rgba(20, 27, 41, 0.88) 0%, rgba(15, 23, 42, 0.94) 100%) !important;
        backdrop-filter: blur(20px) !important;
        -webkit-backdrop-filter: blur(20px) !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        box-shadow: 0 10px 30px -10px rgba(0, 0, 0, 0.5), inset 0 1px 0 rgba(255, 255, 255, 0.08) !important;
        color: white;
        display: flex;
        align-items: center;
        justify-content: center;
        height: 100%;
        min-height: 96px;
        cursor: pointer;
        transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);
        box-sizing: border-box;
      }
      ha-card:hover {
        transform: translateY(-2px);
        border-color: rgba(255, 255, 255, 0.16) !important;
        box-shadow: 0 16px 40px -10px rgba(0, 0, 0, 0.7), inset 0 1px 0 rgba(255, 255, 255, 0.12) !important;
      }
      .badge-content {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        text-align: center;
        gap: 5px;
        width: 100%;
      }
      .icon-box {
        width: 38px;
        height: 38px;
        border-radius: 12px;
        background: rgba(16, 185, 129, 0.12);
        border: 1px solid rgba(16, 185, 129, 0.25);
        display: flex;
        align-items: center;
        justify-content: center;
        color: #10b981;
        transition: transform 0.2s ease;
      }
      ha-card:hover .icon-box {
        transform: scale(1.08);
      }
      .icon-box ha-icon { --mdc-icon-size: 20px; }
      .badge-title {
        font-size: 11px;
        font-weight: 700;
        letter-spacing: 0.2px;
        color: #ffffff;
      }
      .badge-pill {
        display: inline-flex;
        align-items: center;
        gap: 4px;
        padding: 2px 7px;
        border-radius: 9999px;
        font-size: 9px;
        font-weight: 700;
        letter-spacing: 0.2px;
        text-transform: uppercase;
        background: rgba(16, 185, 129, 0.15);
        color: #10b981;
        border: 1px solid rgba(16, 185, 129, 0.35);
      }
      .badge-dot {
        width: 4px;
        height: 4px;
        border-radius: 50%;
        background: currentColor;
        box-shadow: 0 0 4px currentColor;
      }
    `;

    this.shadowRoot.innerHTML = `
      <style>${styleContent}</style>
      <ha-card id="card">
        <div class="badge-content">
          <div class="icon-box" id="icon-box">
            <ha-icon icon="mdi:shield-check"></ha-icon>
          </div>
          <div class="badge-title">Diagnostica</div>
          <div class="badge-pill" id="pill">
            <span class="badge-dot" id="dot"></span>
            <span id="label">Sistema OK</span>
          </div>
        </div>
      </ha-card>
    `;

    const card = this.shadowRoot.getElementById('card');
    const handleHealthClick = (e) => {
      if (e) e.stopPropagation();
      const targetPath = (this._config && this._config.navigation_path) ? this._config.navigation_path : 'diagnostica';
      navigateOrFallbackModal(this, targetPath, () => openMzStandaloneModal('diagnostics', this._hass));
    };

    if (card) {
      card.addEventListener('click', handleHealthClick);
    }
    this.style.cursor = 'pointer';
    this.onclick = handleHealthClick;

    this._rendered = true;
  }

  updateCard() {
    if (!this._hass || !this._rendered) return;
    const pill = this.shadowRoot.getElementById('pill');
    const label = this.shadowRoot.getElementById('label');
    const dot = this.shadowRoot.getElementById('dot');
    const iconBox = this.shadowRoot.getElementById('icon-box');

    const errSensors = ['binary_sensor.multizone_thermostat_anomaly_detected'];
    let hasAnomaly = false;
    for (const sid of errSensors) {
      if (this._hass.states[sid]?.state === 'on') {
        hasAnomaly = true;
        break;
      }
    }

    if (hasAnomaly) {
      label.textContent = 'Allarme';
      pill.style.background = 'rgba(239, 68, 68, 0.18)';
      pill.style.color = '#ef4444';
      pill.style.borderColor = 'rgba(239, 68, 68, 0.4)';
      if (dot) dot.style.background = '#ef4444';
      if (iconBox) iconBox.style.color = '#ef4444';
    } else {
      label.textContent = 'Sistema Ok';
      pill.style.background = 'rgba(16, 185, 129, 0.15)';
      pill.style.color = '#10b981';
      pill.style.borderColor = 'rgba(16, 185, 129, 0.35)';
      if (dot) dot.style.background = '#10b981';
      if (iconBox) iconBox.style.color = '#10b981';
    }
  }
}

if (!customElements.get("multizone-thermostat-health-summary-card")) {
  customElements.define("multizone-thermostat-health-summary-card", MultizoneThermostatHealthSummaryCard);
}

