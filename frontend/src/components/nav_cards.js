class MultizoneThermostatNavCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: 'open' });
    this._schedCard = null;
    this._healthCard = null;
    this._rendered = false;
  }

  setConfig(config) {
    this._config = Object.assign({}, config || {});
    if (!this._rendered) {
      this.render();
    }
  }

  getCardSize() {
    return 3;
  }

  set hass(hass) {
    this._hass = hass;
    if (this._schedCard) {
      this._schedCard.hass = hass;
    }
    if (this._healthCard) {
      this._healthCard.hass = hass;
    }
  }

  render() {
    const radius = (this._config && this._config.border_radius) ? this._config.border_radius : '20px';
    this.shadowRoot.innerHTML = `
      <style>
        :host {
          display: block;
          height: 100%;
          box-sizing: border-box;
        }
        .nav-container {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 12px;
          height: 100%;
          box-sizing: border-box;
        }
        .nav-container > * {
          min-width: 0;
          height: 100%;
        }
      </style>
      <div class="nav-container" id="nav-container"></div>
    `;

    const container = this.shadowRoot.getElementById('nav-container');

    this._schedCard = document.createElement('multizone-thermostat-schedule-summary-card');
    if (typeof this._schedCard.setConfig === 'function') {
      this._schedCard.setConfig({
        border_radius: radius,
        navigation_path: (this._config && (this._config.scheduler_path || this._config.navigation_path)) || 'programmazione'
      });
    }
    if (this._hass) {
      this._schedCard.hass = this._hass;
    }
    this._schedCard.style.cursor = 'pointer';
    this._schedCard.addEventListener('click', (e) => {
      e.stopPropagation();
      navigateOrFallbackModal(this._schedCard, 'programmazione', () => openMzStandaloneModal('scheduler', this._hass));
    });

    this._healthCard = document.createElement('multizone-thermostat-health-summary-card');
    if (typeof this._healthCard.setConfig === 'function') {
      this._healthCard.setConfig({
        border_radius: radius,
        navigation_path: (this._config && (this._config.diagnostics_path || this._config.navigation_path)) || 'diagnostica'
      });
    }
    if (this._hass) {
      this._healthCard.hass = this._hass;
    }
    this._healthCard.style.cursor = 'pointer';
    this._healthCard.addEventListener('click', (e) => {
      e.stopPropagation();
      navigateOrFallbackModal(this._healthCard, 'diagnostica', () => openMzStandaloneModal('diagnostics', this._hass));
    });

    container.appendChild(this._schedCard);
    container.appendChild(this._healthCard);
    this._rendered = true;
  }
}

if (!customElements.get("multizone-thermostat-nav-card")) {
  customElements.define("multizone-thermostat-nav-card", MultizoneThermostatNavCard);
}


/* ==================== RESPONSIVE GRID CARD ==================== */
class MultizoneThermostatResponsiveGrid extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: 'open' });
    this._cardElements = [];
    this._rendered = false;
  }

  setConfig(config) {
    this._config = Object.assign({}, config || {});
    this.render();
  }

  getCardSize() {
    return 6;
  }

  set hass(hass) {
    this._hass = hass;
    const switcher = this.shadowRoot.querySelector('multizone-thermostat-style-switcher');
    if (switcher) {
      try { switcher.hass = hass; } catch (e) {}
    }
    if (this._cardElements && this._cardElements.length > 0) {
      for (const el of this._cardElements) {
        try {
          el.hass = hass;
        } catch (e) {}
      }
    }
  }

  async render() {
    const columns = parseInt(this._config.columns, 10) || 3;
    const cards = this._config.cards || [];

    this.shadowRoot.innerHTML = `
      <style>
        :host {
          display: block;
          width: 100%;
          box-sizing: border-box;
          position: relative;
        }
        .responsive-grid {
          display: grid;
          grid-template-columns: repeat(${columns}, minmax(0, 1fr));
          gap: 12px;
          width: 100%;
          box-sizing: border-box;
          margin-bottom: 12px;
        }
        @media (max-width: 1024px) and (min-width: 769px) {
          .responsive-grid {
            grid-template-columns: repeat(${Math.min(columns, 2)}, minmax(0, 1fr));
          }
        }
        @media (max-width: 768px) {
          .responsive-grid {
            grid-template-columns: 1fr !important;
            gap: 12px;
          }
        }
      </style>
      <div class="responsive-grid" id="grid"></div>
      <multizone-thermostat-style-switcher></multizone-thermostat-style-switcher>
    `;

    const grid = this.shadowRoot.getElementById('grid');
    this._cardElements = [];

    let helpers = window.cardHelpers;
    if (!helpers && window.loadCardHelpers) {
      try {
        helpers = await window.loadCardHelpers();
        window.cardHelpers = helpers;
      } catch (e) {
        console.warn("Could not load Lovelace card helpers:", e);
      }
    }

    for (const cardConfig of cards) {
      if (!cardConfig) continue;
      let cardEl = null;
      if (helpers && typeof helpers.createCardElement === 'function') {
        try {
          cardEl = helpers.createCardElement(cardConfig);
        } catch (e) {
          console.warn("Error creating card element with helpers:", e);
        }
      }
      if (!cardEl) {
        const type = cardConfig.type || '';
        const tag = type.startsWith('custom:') ? type.replace('custom:', '') : `hui-${type}-card`;
        cardEl = document.createElement(tag);
        if (typeof cardEl.setConfig === 'function') {
          try {
            cardEl.setConfig(cardConfig);
          } catch (e) {}
        }
      }
      if (this._hass) {
        try {
          cardEl.hass = this._hass;
        } catch (e) {}
      }
      this._cardElements.push(cardEl);
      grid.appendChild(cardEl);
    }

    this._rendered = true;
  }
}

if (!customElements.get("multizone-thermostat-responsive-grid")) {
  customElements.define("multizone-thermostat-responsive-grid", MultizoneThermostatResponsiveGrid);
}

/* ==================== PLANT DIAGNOSTIC CARD ==================== */
