class MultizoneThermostatStyleSwitcher extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: 'open' });
    this._isOpen = false;
  }

  setConfig(config) {
    this._config = Object.assign({}, config || {});
    this.render();
  }

  getCardSize() {
    return 0;
  }

  connectedCallback() {
    const shouldHide = localStorage.getItem('mz_hide_header') === 'true';
    setHeaderVisibility(shouldHide);

    this._styleListener = (e) => {
      this.render();
    };
    window.addEventListener('mz-style-changed', this._styleListener);
    this.render();
  }

  disconnectedCallback() {
    if (this._styleListener) {
      window.removeEventListener('mz-style-changed', this._styleListener);
    }
  }

  getCurrentStyle() {
    return localStorage.getItem('mz_card_style') || 'luxury';
  }

  isHeaderHidden() {
    return localStorage.getItem('mz_hide_header') === 'true';
  }

  setStyle(style) {
    localStorage.setItem('mz_card_style', style);
    window.dispatchEvent(new CustomEvent('mz-style-changed', { detail: { style } }));
    this.render();
  }

  toggleHeader(hide) {
    localStorage.setItem('mz_hide_header', hide ? 'true' : 'false');
    setHeaderVisibility(hide);
    this.render();
  }

  openModal() {
    this._isOpen = true;
    this.render();
  }

  closeModal() {
    this._isOpen = false;
    this.render();
  }

  render() {
    const currentStyle = this.getCurrentStyle();
    const isClassic = currentStyle === 'classic';
    const hideHeader = this.isHeaderHidden();
    const bottom = this._config?.bottom || '2.5vh';
    const right = this._config?.right || '2.5vh';
    const icon = this._config?.icon || 'mdi:palette-outline';

    this.shadowRoot.innerHTML = `
      <style>
        :host {
          display: block;
        }
        .fab-btn {
          position: fixed !important;
          bottom: ${bottom} !important;
          right: ${right} !important;
          width: 52px !important;
          height: 52px !important;
          border-radius: 50% !important;
          z-index: 9999 !important;
          display: flex !important;
          justify-content: center !important;
          align-items: center !important;
          cursor: pointer !important;
          transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1) !important;
        }
        
        /* Responsive styling: Luxury vs Classic */
        .fab-luxury {
          background: rgba(20, 27, 41, 0.85) !important;
          backdrop-filter: blur(16px) !important;
          -webkit-backdrop-filter: blur(16px) !important;
          border: 1.5px solid rgba(56, 189, 248, 0.4) !important;
          box-shadow: 0 8px 30px rgba(0, 0, 0, 0.6), 0 0 15px rgba(56, 189, 248, 0.25) !important;
          color: #38bdf8 !important;
        }
        .fab-luxury:hover {
          transform: scale(1.1) !important;
          background: rgba(30, 41, 59, 0.95) !important;
          border-color: rgba(56, 189, 248, 0.7) !important;
          box-shadow: 0 12px 35px rgba(0, 0, 0, 0.8), 0 0 25px rgba(56, 189, 248, 0.5) !important;
        }
        
        .fab-classic {
          background: var(--card-background-color, #202b38) !important;
          border: 1.5px solid var(--divider-color, rgba(255, 255, 255, 0.2)) !important;
          box-shadow: 0 4px 16px rgba(0, 0, 0, 0.5) !important;
          color: var(--primary-text-color, #ffffff) !important;
        }
        .fab-classic:hover {
          transform: scale(1.1) !important;
          background: var(--primary-color, #0284c7) !important;
          color: #ffffff !important;
        }

        .fab-btn:active {
          transform: scale(0.95) !important;
        }
        .fab-btn ha-icon {
          --mdc-icon-size: 26px;
          color: inherit;
        }

        /* Modal Overlay */
        .modal-overlay {
          position: fixed;
          inset: 0;
          z-index: 10000;
          background: rgba(0, 0, 0, 0.75);
          backdrop-filter: blur(8px);
          -webkit-backdrop-filter: blur(8px);
          display: ${this._isOpen ? 'flex' : 'none'};
          align-items: center;
          justify-content: center;
          padding: 16px;
          box-sizing: border-box;
          animation: fadeIn 0.2s ease;
        }
        @keyframes fadeIn {
          from { opacity: 0; }
          to { opacity: 1; }
        }
        .modal-card {
          border-radius: 24px;
          width: 100%;
          max-width: 440px;
          overflow: hidden;
          animation: popIn 0.25s cubic-bezier(0.16, 1, 0.3, 1);
        }
        .modal-card.modal-luxury {
          background: linear-gradient(135deg, rgba(20, 27, 41, 0.96) 0%, rgba(15, 23, 42, 0.99) 100%);
          border: 1px solid rgba(255, 255, 255, 0.12);
          box-shadow: 0 25px 60px -15px rgba(0, 0, 0, 0.9), 0 0 30px rgba(56, 189, 248, 0.2);
        }
        .modal-card.modal-classic {
          background: var(--ha-card-background, var(--card-background-color, #1c1c1e)) !important;
          border: 1px solid var(--divider-color, rgba(255, 255, 255, 0.15)) !important;
          box-shadow: 0 20px 50px rgba(0, 0, 0, 0.6) !important;
        }
        .modal-classic .modal-header {
          border-bottom: 1px solid var(--divider-color, rgba(255, 255, 255, 0.12)) !important;
        }
        .modal-classic .modal-title {
          color: var(--primary-text-color, #ffffff) !important;
        }
        .modal-classic .section-label {
          color: var(--secondary-text-color, #94a3b8) !important;
        }
        .modal-classic .option-card {
          background: var(--card-background-color, #202b38) !important;
          border: 1px solid var(--divider-color, rgba(255, 255, 255, 0.12)) !important;
        }
        .modal-classic .option-card:hover {
          background: rgba(255, 255, 255, 0.05) !important;
        }
        .modal-classic .option-card.active {
          background: rgba(var(--rgb-primary-color, 2, 132, 199), 0.15) !important;
          border-color: var(--primary-color, #0284c7) !important;
          box-shadow: 0 0 16px rgba(var(--rgb-primary-color, 2, 132, 199), 0.25) !important;
        }
        .modal-classic .option-card.active .option-icon {
          background: rgba(var(--rgb-primary-color, 2, 132, 199), 0.25) !important;
          color: var(--primary-color, #0284c7) !important;
        }
        .modal-classic .option-card.active .radio-dot {
          border-color: var(--primary-color, #0284c7) !important;
          background: var(--primary-color, #0284c7) !important;
        }
        .modal-classic .toggle-box {
          background: var(--card-background-color, #202b38) !important;
          border: 1px solid var(--divider-color, rgba(255, 255, 255, 0.12)) !important;
        }
        .modal-classic .toggle-title {
          color: var(--primary-text-color, #ffffff) !important;
        }
        .modal-classic .toggle-desc {
          color: var(--secondary-text-color, #94a3b8) !important;
        }
        .modal-classic input:checked + .slider {
          background-color: var(--primary-color, #0284c7) !important;
        }
        @keyframes popIn {
          from { transform: scale(0.92); opacity: 0; }
          to { transform: scale(1); opacity: 1; }
        }
        .modal-header {
          display: flex;
          align-items: center;
          justify-content: space-between;
          padding: 18px 20px;
          border-bottom: 1px solid rgba(255, 255, 255, 0.08);
        }
        .modal-title {
          font-size: 16px;
          font-weight: 800;
          color: #ffffff;
          display: flex;
          align-items: center;
          gap: 8px;
        }
        .close-btn {
          background: rgba(255, 255, 255, 0.06);
          border: none;
          color: #94a3b8;
          width: 30px;
          height: 30px;
          border-radius: 50%;
          cursor: pointer;
          font-size: 16px;
          display: flex;
          align-items: center;
          justify-content: center;
          transition: all 0.2s ease;
        }
        .close-btn:hover {
          background: rgba(255, 255, 255, 0.15);
          color: #ffffff;
        }
        .modal-body {
          padding: 20px;
          display: flex;
          flex-direction: column;
          gap: 16px;
        }
        .section-label {
          font-size: 11px;
          font-weight: 700;
          text-transform: uppercase;
          letter-spacing: 1px;
          color: #94a3b8;
          margin-bottom: 2px;
        }
        .options-group {
          display: flex;
          flex-direction: column;
          gap: 10px;
        }
        .option-card {
          display: flex;
          align-items: center;
          padding: 14px 16px;
          border-radius: 16px;
          background: rgba(255, 255, 255, 0.03);
          border: 1.5px solid rgba(255, 255, 255, 0.08);
          cursor: pointer;
          gap: 14px;
          transition: all 0.2s ease;
        }
        .option-card:hover {
          background: rgba(255, 255, 255, 0.06);
          border-color: rgba(255, 255, 255, 0.18);
          transform: translateY(-1px);
        }
        .option-card.active {
          background: rgba(14, 165, 233, 0.15);
          border-color: #38bdf8;
          box-shadow: 0 0 20px rgba(14, 165, 233, 0.25);
        }
        .option-icon {
          width: 44px;
          height: 44px;
          border-radius: 12px;
          background: rgba(255, 255, 255, 0.06);
          display: flex;
          align-items: center;
          justify-content: center;
          font-size: 22px;
          flex-shrink: 0;
        }
        .option-card.active .option-icon {
          background: rgba(14, 165, 233, 0.25);
          color: #38bdf8;
        }
        .option-details {
          flex: 1;
        }
        .option-name {
          font-size: 14px;
          font-weight: 700;
          color: #ffffff;
          margin-bottom: 2px;
        }
        .option-desc {
          font-size: 11px;
          color: #94a3b8;
          line-height: 1.3;
        }
        .radio-dot {
          width: 20px;
          height: 20px;
          border-radius: 50%;
          border: 2px solid rgba(255, 255, 255, 0.2);
          display: flex;
          align-items: center;
          justify-content: center;
          flex-shrink: 0;
        }
        .option-card.active .radio-dot {
          border-color: #38bdf8;
          background: #38bdf8;
        }
        .radio-dot::after {
          content: '';
          width: 8px;
          height: 8px;
          border-radius: 50%;
          background: #ffffff;
          display: none;
        }
        .option-card.active .radio-dot::after {
          display: block;
        }

        /* Toggle Header Row */
        .toggle-box {
          display: flex;
          align-items: center;
          justify-content: space-between;
          padding: 14px 16px;
          border-radius: 16px;
          background: rgba(255, 255, 255, 0.03);
          border: 1px solid rgba(255, 255, 255, 0.08);
          gap: 12px;
        }
        .toggle-info {
          flex: 1;
        }
        .toggle-title {
          font-size: 14px;
          font-weight: 700;
          color: #ffffff;
          margin-bottom: 2px;
        }
        .toggle-desc {
          font-size: 11px;
          color: #94a3b8;
          line-height: 1.3;
        }
        .switch {
          position: relative;
          display: inline-block;
          width: 48px;
          height: 26px;
          flex-shrink: 0;
        }
        .switch input {
          opacity: 0;
          width: 0;
          height: 0;
        }
        .slider {
          position: absolute;
          cursor: pointer;
          top: 0; left: 0; right: 0; bottom: 0;
          background-color: rgba(255, 255, 255, 0.15);
          transition: .3s;
          border-radius: 26px;
        }
        .slider:before {
          position: absolute;
          content: "";
          height: 20px;
          width: 20px;
          left: 3px;
          bottom: 3px;
          background-color: white;
          transition: .3s;
          border-radius: 50%;
        }
        input:checked + .slider {
          background-color: #38bdf8;
        }
        input:checked + .slider:before {
          transform: translateX(22px);
        }
      </style>

      <div class="fab-btn ${isClassic ? 'fab-classic' : 'fab-luxury'}" id="fab-btn" title="Personalizza Grafica">
        <ha-icon icon="${icon}"></ha-icon>
      </div>

      <div class="modal-overlay" id="modal-overlay">
        <div class="modal-card ${isClassic ? 'modal-classic' : 'modal-luxury'}">
          <div class="modal-header">
            <div class="modal-title">
              <span>🎨</span> Personalizzazione Dashboard
            </div>
            <button class="close-btn" id="close-btn">✕</button>
          </div>
          <div class="modal-body">
            <div>
              <div class="section-label">Stile Schede Termostati</div>
              <div class="options-group">
                <div class="option-card ${currentStyle === 'luxury' ? 'active' : ''}" id="opt-luxury">
                  <div class="option-icon">💎</div>
                  <div class="option-details">
                    <div class="option-name">Luxury Vector Arc (Nuovo)</div>
                    <div class="option-desc">Design moderno con arco vettoriale a 270°, regolazione touch e tema glassmorphic.</div>
                  </div>
                  <div class="radio-dot"></div>
                </div>

                <div class="option-card ${currentStyle === 'classic' ? 'active' : ''}" id="opt-classic">
                  <div class="option-icon">🏛️</div>
                  <div class="option-details">
                    <div class="option-name">Standard Home Assistant (Classico)</div>
                    <div class="option-desc">Manopola circolare standard originale di Home Assistant.</div>
                  </div>
                  <div class="radio-dot"></div>
                </div>
              </div>
            </div>

            <div>
              <div class="section-label">Visualizzazione Interfaccia</div>
              <div class="toggle-box">
                <div class="toggle-info">
                  <div class="toggle-title">Nascondi Barra Superiore</div>
                  <div class="toggle-desc">Nasconde la barra in alto per una vista pulita. Disattiva per far riapparire la matita di modifica e i menu.</div>
                </div>
                <label class="switch">
                  <input type="checkbox" id="header-toggle" ${hideHeader ? 'checked' : ''}>
                  <span class="slider"></span>
                </label>
              </div>
            </div>
          </div>
        </div>
      </div>
    `;

    const fab = this.shadowRoot.querySelector('#fab-btn');
    if (fab) fab.addEventListener('click', () => this.openModal());

    const closeBtn = this.shadowRoot.querySelector('#close-btn');
    if (closeBtn) closeBtn.addEventListener('click', () => this.closeModal());

    const overlay = this.shadowRoot.querySelector('#modal-overlay');
    if (overlay) overlay.addEventListener('click', (e) => {
      if (e.target === overlay) this.closeModal();
    });

    const optLuxury = this.shadowRoot.querySelector('#opt-luxury');
    if (optLuxury) optLuxury.addEventListener('click', () => this.setStyle('luxury'));

    const optClassic = this.shadowRoot.querySelector('#opt-classic');
    if (optClassic) optClassic.addEventListener('click', () => this.setStyle('classic'));

    const headerToggle = this.shadowRoot.querySelector('#header-toggle');
    if (headerToggle) {
      headerToggle.addEventListener('change', (e) => {
        this.toggleHeader(e.target.checked);
      });
    }
  }
}

if (!customElements.get("multizone-thermostat-style-switcher")) {
  customElements.define("multizone-thermostat-style-switcher", MultizoneThermostatStyleSwitcher);
}

