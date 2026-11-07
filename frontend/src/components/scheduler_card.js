class MultizoneThermostatSchedulerCard extends HTMLElement {
  getCardSize() { return 6; }

  constructor() {
    super();
    this.attachShadow({ mode: 'open' });
    this._hass = null;
    this._config = {};
    this._editorProfileId = 'standard';
    const dayMap = ['sun', 'mon', 'tue', 'wed', 'thu', 'fri', 'sat'];
    this._selectedDay = dayMap[new Date().getDay()] || 'mon';
    this._activeBrush = 'comfort'; // 'comfort', 'eco', 'sleep', 'away', 'erase'
    this._activeModal = null; // null | 'slot' | 'activate' | 'smart_return' | 'duplicate'
    this._modalData = {};
    this._copiedRoomSchedule = null;
    this._localScheduleCache = null;
    this._lastHaScheduleJson = "";
    this._rendered = false;
    this._refreshTimer = null;
  }

  setConfig(config) {
    this._config = config || {};
  }

  set hass(hass) {
    this._hass = hass;
    if (!this._rendered) {
      this.render();
      this._rendered = true;
      const raw = this._extractHaScheduleStatus();
      this._lastHaScheduleJson = raw ? JSON.stringify(raw) : "";
    } else {
      const raw = this._extractHaScheduleStatus();
      const currentJson = raw ? JSON.stringify(raw) : "";
      if (currentJson && currentJson !== this._lastHaScheduleJson) {
        this._lastHaScheduleJson = currentJson;
        this._localScheduleCache = null;
        this.renderHeader();
        this.renderLiveZones();
        this.renderEditor();
        this.renderPresetMatrixTable();
      } else {
        this.updateDynamicState();
      }
    }
  }

  connectedCallback() {
    this._refreshTimer = setInterval(() => {
      this.updateCurrentTimeIndicator();
    }, 60000);
  }

  disconnectedCallback() {
    if (this._refreshTimer) {
      clearInterval(this._refreshTimer);
      this._refreshTimer = null;
    }
  }

  _t(key) {
    return getTranslation(this._hass, key);
  }

  _extractHaScheduleStatus() {
    if (!this._hass || !this._hass.states) return null;
    for (const eid of Object.keys(this._hass.states)) {
      if (eid.startsWith('switch.') && (eid.includes('weekly_scheduler') || eid.includes('scheduler'))) {
        const s = this._hass.states[eid];
        if (s.attributes && s.attributes.schedule_status) {
          return s.attributes.schedule_status;
        }
      }
    }
    const masterEid = findMasterEntity(this._hass);
    if (masterEid && this._hass.states[masterEid]?.attributes?.schedule_status) {
      return this._hass.states[masterEid].attributes.schedule_status;
    }
    for (const eid of Object.keys(this._hass.states)) {
      if (this._hass.states[eid]?.attributes?.schedule_status) {
        return this._hass.states[eid].attributes.schedule_status;
      }
    }
    return null;
  }

  _getScheduleStatus() {
    if (this._localScheduleCache) {
      return this._localScheduleCache;
    }
    const haSched = this._extractHaScheduleStatus();
    if (haSched) return haSched;
    return this._getDefaultSchedule();
  }

  _getDefaultSchedule() {
    return {
      scheduler_enabled: true,
      active_profile: 'standard',
      profile_expires_at: null,
      fallback_profile: 'standard',
      profiles: {
        standard: {
          name: 'Standard',
          baseline_preset: 'eco',
          days: { mon: {}, tue: {}, wed: {}, thu: {}, fri: {}, sat: {}, sun: {} }
        },
        smart_working: {
          name: 'Smart Working',
          baseline_preset: 'eco',
          days: { mon: {}, tue: {}, wed: {}, thu: {}, fri: {}, sat: {}, sun: {} }
        },
        holiday: {
          name: 'Festivo',
          baseline_preset: 'eco',
          days: { mon: {}, tue: {}, wed: {}, thu: {}, fri: {}, sat: {}, sun: {} }
        }
      },
      manual_overrides: {},
      smart_start_info: {},
      smart_return: null,
      smart_return_plan: {},
      preset_matrix: {
        comfort: {},
        eco: {},
        sleep: {},
        away: {}
      }
    };
  }

  _getZones() {
    if (!this._hass || !this._hass.states) return [];
    const zones = [];
    const seenClimates = new Set();

    for (const eid of Object.keys(this._hass.states)) {
      const s = this._hass.states[eid];
      const climateId = s.attributes ? s.attributes.climate_entity : null;
      if (climateId && this._hass.states[climateId] && !seenClimates.has(climateId)) {
        seenClimates.add(climateId);
        const cState = this._hass.states[climateId];
        let name = cState.attributes.friendly_name || climateId;
        name = name.replace(/^Virtual Thermostats VT /i, '').replace(/^Heating Zones(?: Zone)? /i, '');
        zones.push({
          id: climateId,
          climate: climateId,
          switch: eid,
          name: name,
          current_temp: typeof cState.attributes.current_temperature === 'number' ? cState.attributes.current_temperature : 20.0,
          target_temp: typeof cState.attributes.temperature === 'number' ? cState.attributes.temperature : 20.0,
          hvac_mode: cState.state,
          heating_rate: typeof cState.attributes.heating_rate === 'number' ? cState.attributes.heating_rate : 1.0,
          manual_override: !!cState.attributes.schedule_manual_override,
          override_until: cState.attributes.schedule_override_until || null,
          smart_start: !!cState.attributes.smart_start_active,
          smart_start_detail: cState.attributes.smart_start_detail || ""
        });
      }
    }

    for (const eid of Object.keys(this._hass.states)) {
      if (eid.startsWith('climate.') && (eid.includes('multizone_thermostat_') || this._hass.states[eid]?.attributes?.hybrid_zone === true)) {
        if (!seenClimates.has(eid)) {
          seenClimates.add(eid);
          const cState = this._hass.states[eid];
          let name = cState.attributes.friendly_name || eid;
          name = name.replace(/^Virtual Thermostats VT /i, '').replace(/^Heating Zones(?: Zone)? /i, '');
          zones.push({
            id: eid,
            climate: eid,
            switch: null,
            name: name,
            current_temp: typeof cState.attributes.current_temperature === 'number' ? cState.attributes.current_temperature : 20.0,
            target_temp: typeof cState.attributes.temperature === 'number' ? cState.attributes.temperature : 20.0,
            hvac_mode: cState.state,
            heating_rate: typeof cState.attributes.heating_rate === 'number' ? cState.attributes.heating_rate : 1.0,
            manual_override: !!cState.attributes.schedule_manual_override,
            override_until: cState.attributes.schedule_override_until || null,
            smart_start: !!cState.attributes.smart_start_active,
            smart_start_detail: cState.attributes.smart_start_detail || ""
          });
        }
      }
    }

    zones.sort((a, b) => a.name.localeCompare(b.name));
    return zones;
  }

  _resolvePresetTemp(zoneId, preset) {
    const sched = this._getScheduleStatus();
    if (sched.preset_matrix && sched.preset_matrix[preset]) {
      if (typeof sched.preset_matrix[preset][zoneId] === 'number') {
        return sched.preset_matrix[preset][zoneId];
      }
    }
    const defaults = { comfort: 21.0, eco: 19.0, sleep: 17.0, away: 15.0 };
    return defaults[preset] || 20.0;
  }

  render() {
    this.shadowRoot.innerHTML = `
      <style>
        :host {
          display: block;
          --card-border-radius: var(--ha-card-border-radius, 20px);
          font-family: var(--paper-font-body1_-_font-family, sans-serif);
        }
        ha-card {
          padding: 20px;
          border-radius: var(--card-border-radius);
          background-color: var(--card-background-color, #1e293b);
          color: var(--primary-text-color, #f8fafc);
          box-sizing: border-box;
          position: relative;
        }
        .header-bar {
          display: flex;
          flex-wrap: wrap;
          align-items: center;
          justify-content: space-between;
          gap: 16px;
          margin-bottom: 20px;
          padding-bottom: 16px;
          border-bottom: 1px solid var(--divider-color, rgba(255, 255, 255, 0.1));
        }
        .header-title-box {
          display: flex;
          align-items: center;
          flex-wrap: wrap;
          gap: 12px;
        }
        .header-title-box ha-icon {
          --mdc-icon-size: 32px;
          color: #38bdf8;
        }
        .header-title {
          font-size: 1.35rem;
          font-weight: 700;
        }
        .header-badges {
          display: flex;
          flex-wrap: wrap;
          align-items: center;
          gap: 8px;
        }
        .badge {
          display: inline-flex;
          align-items: center;
          gap: 6px;
          padding: 6px 12px;
          border-radius: 9999px;
          font-size: 0.85rem;
          font-weight: 600;
          background: rgba(255, 255, 255, 0.08);
          border: 1px solid rgba(255, 255, 255, 0.12);
        }
        .badge-btn {
          cursor: pointer;
          transition: all 0.2s ease;
        }
        .badge-btn:hover {
          background: rgba(255, 255, 255, 0.18);
          transform: translateY(-1px);
        }
        .badge-green {
          background: rgba(16, 185, 129, 0.2);
          border-color: rgba(16, 185, 129, 0.4);
          color: #34d399;
        }
        .badge-orange {
          background: rgba(249, 115, 22, 0.2);
          border-color: rgba(249, 115, 22, 0.4);
          color: #fb923c;
        }
        .badge-amber {
          background: rgba(245, 158, 11, 0.2);
          border-color: rgba(245, 158, 11, 0.4);
          color: #fcd34d;
        }
        .badge-blue {
          background: rgba(56, 189, 248, 0.2);
          border-color: rgba(56, 189, 248, 0.4);
          color: #38bdf8;
        }
        .badge-gray {
          background: rgba(148, 163, 184, 0.15);
          border-color: rgba(148, 163, 184, 0.3);
          color: #94a3b8;
        }
        .header-actions {
          display: flex;
          flex-wrap: wrap;
          align-items: center;
          gap: 10px;
        }
        .btn {
          display: inline-flex;
          align-items: center;
          justify-content: center;
          gap: 6px;
          padding: 8px 14px;
          border-radius: 8px;
          font-size: 0.875rem;
          font-weight: 600;
          cursor: pointer;
          border: none;
          transition: all 0.2s ease;
          background: rgba(255, 255, 255, 0.1);
          color: white;
        }
        .btn:hover {
          background: rgba(255, 255, 255, 0.2);
          transform: translateY(-1px);
        }
        .btn-primary { background: #0284c7; color: white; }
        .btn-primary:hover { background: #0369a1; }
        .btn-amber { background: #d97706; color: white; }
        .btn-amber:hover { background: #b45309; }
        .btn-danger { background: #dc2626; color: white; }
        .btn-danger:hover { background: #b91c1c; }
        
        .live-zones-grid {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
          gap: 14px;
          margin-bottom: 24px;
        }
        .zone-card {
          background: rgba(255, 255, 255, 0.04);
          border: 1px solid rgba(255, 255, 255, 0.08);
          border-radius: 14px;
          padding: 14px;
          display: flex;
          flex-direction: column;
          gap: 10px;
          transition: border-color 0.2s;
        }
        .zone-card:hover { border-color: rgba(255, 255, 255, 0.18); }
        .zone-card-top {
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 8px;
          flex-wrap: wrap;
        }
        .zone-card-title {
          font-weight: 700;
          font-size: 1.02rem;
          line-height: 1.25;
          word-break: break-word;
        }
        .zone-card-mid {
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 10px;
          flex-wrap: wrap;
        }
        .temp-display {
          display: flex;
          align-items: baseline;
          gap: 6px;
        }
        .current-temp { font-size: 1.45rem; font-weight: 800; }
        .target-temp { font-size: 1.15rem; font-weight: 600; opacity: 0.85; }
        .temp-controls {
          display: flex;
          align-items: center;
          gap: 6px;
        }
        .btn-circle {
          width: 32px;
          height: 32px;
          border-radius: 50%;
          display: flex;
          align-items: center;
          justify-content: center;
          background: rgba(255, 255, 255, 0.1);
          color: white;
          border: none;
          font-size: 1.1rem;
          cursor: pointer;
          transition: all 0.2s;
        }
        .btn-circle:hover { background: rgba(255, 255, 255, 0.25); }
        .zone-card-bottom {
          display: flex;
          align-items: center;
          justify-content: space-between;
          font-size: 0.75rem;
          opacity: 0.75;
          border-top: 1px solid rgba(255, 255, 255, 0.08);
          padding-top: 8px;
          margin-top: 4px;
          gap: 8px;
          line-height: 1.4;
          overflow: hidden;
        }
        .zone-card-bottom span {
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
        }

        .editor-box {
          background: rgba(255, 255, 255, 0.02);
          border: 1px solid rgba(255, 255, 255, 0.08);
          border-radius: 16px;
          padding: 16px;
          margin-bottom: 24px;
        }
        .editor-header-bar {
          display: flex;
          flex-wrap: wrap;
          align-items: center;
          justify-content: space-between;
          gap: 12px;
          margin-bottom: 14px;
        }
        .profile-tabs {
          display: flex;
          flex-wrap: wrap;
          gap: 6px;
        }
        .profile-tab {
          padding: 8px 16px;
          border-radius: 10px;
          background: rgba(255, 255, 255, 0.06);
          color: var(--primary-text-color, #f8fafc);
          font-weight: 600;
          cursor: pointer;
          border: 1px solid transparent;
          transition: all 0.2s;
        }
        .profile-tab.active {
          background: #0284c7;
          color: white;
          border-color: #38bdf8;
        }
        .editor-controls {
          display: flex;
          flex-wrap: wrap;
          align-items: center;
          gap: 10px;
        }
        .baseline-select-box {
          display: flex;
          align-items: center;
          gap: 6px;
          font-size: 0.875rem;
        }
        select, input[type="text"], input[type="number"], input[type="time"], input[type="datetime-local"] {
          background: rgba(15, 23, 42, 0.8);
          border: 1px solid rgba(255, 255, 255, 0.15);
          color: white;
          padding: 6px 10px;
          border-radius: 6px;
          font-size: 0.875rem;
          outline: none;
        }
        select:focus, input:focus { border-color: #38bdf8; }
        .bg-notice-banner {
          background: rgba(245, 158, 11, 0.12);
          border: 1px solid rgba(245, 158, 11, 0.3);
          color: #fcd34d;
          padding: 8px 12px;
          border-radius: 8px;
          font-size: 0.85rem;
          margin-bottom: 14px;
          display: flex;
          align-items: center;
          gap: 8px;
        }

        .toolbar-bar {
          display: flex;
          flex-wrap: wrap;
          align-items: center;
          justify-content: space-between;
          gap: 12px;
          margin-bottom: 16px;
          background: rgba(255, 255, 255, 0.03);
          padding: 10px 14px;
          border-radius: 12px;
        }
        .day-pills { display: flex; gap: 4px; }
        .day-pill {
          padding: 6px 12px;
          border-radius: 8px;
          background: rgba(255, 255, 255, 0.06);
          cursor: pointer;
          font-size: 0.85rem;
          font-weight: 600;
          transition: all 0.2s;
        }
        .day-pill.active { background: #0284c7; color: white; }
        .day-pill.today::after { content: " •"; color: #38bdf8; font-weight: 900; }

        .matrix-container {
          overflow-x: auto;
          margin-bottom: 20px;
        }
        .time-ruler {
          display: flex;
          margin-left: 180px;
          border-bottom: 1px solid rgba(255, 255, 255, 0.1);
          padding-bottom: 4px;
          margin-bottom: 8px;
          position: relative;
        }
        .ruler-hour {
          flex: 1;
          text-align: left;
          font-size: 0.75rem;
          color: rgba(255, 255, 255, 0.6);
        }
        .matrix-row {
          display: flex;
          align-items: center;
          margin-bottom: 8px;
          gap: 10px;
        }
        .room-label-box {
          width: 170px;
          flex-shrink: 0;
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 4px;
        }
        .room-title {
          font-size: 0.875rem;
          font-weight: 600;
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
        }
        .room-copy-btn {
          background: none;
          border: none;
          color: rgba(255, 255, 255, 0.6);
          cursor: pointer;
          padding: 2px;
          font-size: 0.85rem;
        }
        .room-copy-btn:hover { color: white; }
        .timeline-track {
          flex: 1;
          height: 38px;
          background: rgba(255, 255, 255, 0.05);
          border-radius: 8px;
          position: relative;
          cursor: crosshair;
          overflow: hidden;
          border: 1px solid rgba(255, 255, 255, 0.08);
        }
        .grid-line {
          position: absolute;
          top: 0;
          bottom: 0;
          width: 1px;
          background: rgba(255, 255, 255, 0.04);
          pointer-events: none;
        }
        .current-time-line {
          position: absolute;
          top: 0;
          bottom: 0;
          width: 2px;
          background: #ef4444;
          z-index: 10;
          pointer-events: none;
          box-shadow: 0 0 6px #ef4444;
        }
        .time-block {
          position: absolute;
          top: 3px;
          bottom: 3px;
          border-radius: 6px;
          display: flex;
          align-items: center;
          padding: 0 6px;
          font-size: 0.75rem;
          font-weight: 700;
          color: white;
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
          cursor: pointer;
          box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
          transition: transform 0.1s, filter 0.1s;
          z-index: 2;
        }
        .time-block:hover {
          transform: scaleY(1.08);
          filter: brightness(1.15);
          z-index: 5;
        }
        .block-comfort { background: linear-gradient(135deg, #f97316, #ea580c); }
        .block-eco { background: linear-gradient(135deg, #22c55e, #16a34a); }
        .block-sleep { background: linear-gradient(135deg, #6366f1, #4f46e5); }
        .block-away { background: linear-gradient(135deg, #06b6d4, #0891b2); }

        .matrix-table-container {
          margin-top: 24px;
          background: rgba(255, 255, 255, 0.02);
          border: 1px solid rgba(255, 255, 255, 0.08);
          border-radius: 14px;
          padding: 16px;
          overflow-x: auto;
        }
        .matrix-table-title {
          font-size: 1.1rem;
          font-weight: 700;
          margin-bottom: 12px;
          display: flex;
          align-items: center;
          gap: 8px;
        }
        table {
          width: 100%;
          border-collapse: collapse;
          font-size: 0.875rem;
        }
        th, td {
          padding: 10px 12px;
          text-align: left;
          border-bottom: 1px solid rgba(255, 255, 255, 0.06);
        }
        th { font-weight: 600; color: rgba(255, 255, 255, 0.7); }
        /* Preset summary card */
        .preset-summary-card {
          background: rgba(255, 255, 255, 0.03);
          border: 1px solid rgba(255, 255, 255, 0.08);
          border-radius: 14px;
          padding: 14px;
          margin-top: 14px;
        }
        .preset-summary-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 12px;
        }
        .preset-summary-grid {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
          gap: 10px;
        }
        .preset-summary-zone-card {
          background: rgba(255, 255, 255, 0.03);
          border: 1px solid rgba(255, 255, 255, 0.06);
          border-radius: 10px;
          padding: 10px 12px;
        }
        .preset-zone-name {
          font-weight: 600;
          font-size: 0.85rem;
          margin-bottom: 6px;
          color: rgba(255, 255, 255, 0.9);
        }
        .preset-badges-row {
          display: flex;
          gap: 6px;
          flex-wrap: wrap;
        }
        .preset-badge {
          font-size: 0.75rem;
          font-weight: 600;
          padding: 3px 7px;
          border-radius: 6px;
        }
        .preset-badge.badge-comfort {
          background: rgba(239, 68, 68, 0.15);
          color: #f87171;
          border: 1px solid rgba(239, 68, 68, 0.3);
        }
        .preset-badge.badge-eco {
          background: rgba(34, 197, 94, 0.15);
          color: #4ade80;
          border: 1px solid rgba(34, 197, 94, 0.3);
        }
        .preset-badge.badge-sleep {
          background: rgba(59, 130, 246, 0.15);
          color: #60a5fa;
          border: 1px solid rgba(59, 130, 246, 0.3);
        }
        .preset-badge.badge-away {
          background: rgba(148, 163, 184, 0.15);
          color: #cbd5e1;
          border: 1px solid rgba(148, 163, 184, 0.3);
        }

        /* Responsive Mobile Layout Fixes for Scheduler Panel */
        @media (max-width: 768px) {
          ha-card {
            padding: 14px 10px;
          }
          .header-bar {
            flex-direction: column;
            align-items: flex-start;
            gap: 12px;
          }
          .header-title-box {
            width: 100%;
            justify-content: space-between;
          }
          .header-title {
            font-size: 1.15rem;
          }
          .header-badges {
            width: 100%;
          }
          .header-actions {
            width: 100%;
            display: grid;
            grid-template-columns: 1fr;
            gap: 8px;
          }
          .header-actions .btn {
            width: 100%;
            text-align: center;
            padding: 10px;
          }
          .live-zones-grid {
            grid-template-columns: 1fr;
            gap: 10px;
          }
          .editor-header-bar {
            flex-direction: column;
            align-items: stretch;
            gap: 10px;
          }
          .profile-tabs {
            display: flex;
            overflow-x: auto;
            -webkit-overflow-scrolling: touch;
            width: 100%;
            padding-bottom: 4px;
          }
          .editor-controls {
            justify-content: space-between;
            width: 100%;
          }
          .toolbar-bar {
            flex-direction: column;
            align-items: stretch;
            gap: 10px;
            padding: 10px 8px;
          }
          .day-pills {
            display: flex;
            overflow-x: auto;
            -webkit-overflow-scrolling: touch;
            scrollbar-width: none;
            padding-bottom: 4px;
            width: 100%;
          }
          .day-pills::-webkit-scrollbar { display: none; }
          .matrix-container {
            overflow-x: auto;
            -webkit-overflow-scrolling: touch;
            width: 100%;
          }
          .time-ruler, .matrix-row {
            min-width: 680px;
          }
          .room-label-box {
            position: sticky;
            left: 0;
            background: #1e293b;
            z-index: 10;
            padding-right: 6px;
          }
          .matrix-table-container table {
            min-width: 520px;
          }
          .preset-summary-grid {
            grid-template-columns: 1fr;
          }
        }

        /* Slot modal enhancements */
        .slot-modal-wide {
          max-width: 580px;
          width: 100%;
        }
        .form-section {
          background: rgba(255, 255, 255, 0.03);
          border: 1px solid rgba(255, 255, 255, 0.07);
          border-radius: 12px;
          padding: 12px 14px;
          margin-bottom: 14px;
        }
        .sub-label {
          font-size: 0.75rem;
          color: rgba(255, 255, 255, 0.6);
          display: block;
          margin-bottom: 4px;
        }
        .time-input {
          background: rgba(0, 0, 0, 0.25);
          border: 1px solid rgba(255, 255, 255, 0.15);
          border-radius: 8px;
          color: white;
          padding: 8px 10px;
          font-size: 1rem;
          width: 100%;
          box-sizing: border-box;
          font-family: inherit;
        }
        .duration-badge {
          font-size: 0.78rem;
          background: rgba(56, 189, 248, 0.15);
          color: #38bdf8;
          border: 1px solid rgba(56, 189, 248, 0.3);
          border-radius: 6px;
          padding: 3px 8px;
        }
        .quick-duration-bar {
          display: flex;
          gap: 6px;
          flex-wrap: wrap;
          margin-top: 10px;
          align-items: center;
        }
        .duration-pill {
          background: rgba(255, 255, 255, 0.06);
          border: 1px solid rgba(255, 255, 255, 0.12);
          color: white;
          border-radius: 14px;
          padding: 4px 10px;
          font-size: 0.75rem;
          cursor: pointer;
          transition: all 0.15s ease;
        }
        .duration-pill:hover {
          background: rgba(255, 255, 255, 0.12);
          border-color: rgba(255, 255, 255, 0.25);
        }
        .duration-pill.active {
          background: #0284c7;
          border-color: #38bdf8;
          color: white;
          font-weight: 600;
        }
        .general-preset-grid {
          display: grid;
          grid-template-columns: repeat(4, 1fr);
          gap: 8px;
        }
        .general-preset-card {
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          padding: 10px 6px;
          border-radius: 10px;
          border: 2px solid rgba(255, 255, 255, 0.1);
          background: rgba(255, 255, 255, 0.04);
          color: white;
          cursor: pointer;
          transition: all 0.15s ease;
        }
        .general-preset-card:hover {
          border-color: rgba(255, 255, 255, 0.25);
          background: rgba(255, 255, 255, 0.08);
        }
        .general-preset-card.active {
          border-color: #38bdf8;
          background: rgba(56, 189, 248, 0.2);
          box-shadow: 0 0 12px rgba(56, 189, 248, 0.3);
        }
        .preset-card-icon {
          font-size: 1.4rem;
          margin-bottom: 4px;
        }
        .preset-card-name {
          font-size: 0.8rem;
          font-weight: 600;
        }
        .zone-exceptions-container {
          display: flex;
          flex-direction: column;
          gap: 8px;
          max-height: 220px;
          overflow-y: auto;
          padding-right: 4px;
        }
        .zone-exception-row {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 8px 10px;
          background: rgba(255, 255, 255, 0.02);
          border: 1px solid rgba(255, 255, 255, 0.06);
          border-radius: 8px;
          gap: 12px;
        }
        .zone-exception-name {
          font-weight: 600;
          font-size: 0.82rem;
          color: rgba(255, 255, 255, 0.9);
          flex: 1;
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
        }
        .zone-override-select {
          background: #0f172a;
          border: 1px solid rgba(255, 255, 255, 0.18);
          color: white;
          border-radius: 6px;
          padding: 5px 8px;
          font-size: 0.8rem;
          max-width: 280px;
          font-family: inherit;
        }
        .btn-xs {
          padding: 2px 7px;
          font-size: 0.72rem;
        }

        .modal-overlay {
          position: fixed;
          inset: 0;
          background: rgba(0, 0, 0, 0.75);
          backdrop-filter: blur(4px);
          z-index: 9999;
          display: flex;
          align-items: center;
          justify-content: center;
          padding: 16px;
          box-sizing: border-box;
        }
        .modal-box {
          background: #1e293b;
          border: 1px solid rgba(255, 255, 255, 0.15);
          border-radius: 18px;
          padding: 24px;
          max-width: 520px;
          width: 100%;
          box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.5);
          color: white;
          max-height: 90vh;
          overflow-y: auto;
        }
        .modal-title {
          font-size: 1.25rem;
          font-weight: 700;
          margin-bottom: 16px;
          display: flex;
          align-items: center;
          justify-content: space-between;
        }
        .modal-close-btn {
          background: none;
          border: none;
          color: rgba(255, 255, 255, 0.6);
          font-size: 1.2rem;
          cursor: pointer;
        }
        .form-group {
          margin-bottom: 16px;
          display: flex;
          flex-direction: column;
          gap: 6px;
        }
        .form-label {
          font-size: 0.85rem;
          font-weight: 600;
          color: rgba(255, 255, 255, 0.8);
        }
        .checkbox-group { display: flex; flex-wrap: wrap; gap: 8px; }
        .checkbox-label {
          display: flex;
          align-items: center;
          gap: 4px;
          font-size: 0.85rem;
          background: rgba(255, 255, 255, 0.05);
          padding: 4px 8px;
          border-radius: 6px;
          cursor: pointer;
        }
        .modal-actions {
          display: flex;
          justify-content: flex-end;
          gap: 10px;
          margin-top: 20px;
        }
        .radar-list {
          margin-top: 14px;
          display: flex;
          flex-direction: column;
          gap: 8px;
          max-height: 250px;
          overflow-y: auto;
        }
        .radar-item {
          background: rgba(255, 255, 255, 0.04);
          padding: 10px 12px;
          border-radius: 10px;
          display: flex;
          align-items: center;
          justify-content: space-between;
          border-left: 4px solid #f97316;
        }
        .radar-item-left { display: flex; flex-direction: column; gap: 2px; }
        .radar-item-right { display: flex; flex-direction: column; align-items: flex-end; gap: 2px; }
      </style>
      <ha-card>
        <div id="header-container"></div>
        <div id="zones-container"></div>
        <div id="editor-container"></div>
        <div id="preset-matrix-container"></div>
        <div id="modal-container"></div>
      </ha-card>
    `;

    this.renderHeader();
    this.renderLiveZones();
    this.renderEditor();
    this.renderPresetMatrixTable();
  }

  updateDynamicState() {
    this.renderHeader();
    this.renderLiveZones();
    if (!this._activeModal) {
      this.updateCurrentTimeIndicator();
    }
  }

  renderHeader() {
    const container = this.shadowRoot.querySelector('#header-container');
    if (!container) return;

    const sched = this._getScheduleStatus();
    const enabled = !!sched.scheduler_enabled;
    const activeProf = sched.active_profile || 'standard';
    const profName = sched.profiles?.[activeProf]?.name || activeProf;

    let profPrefix = "🟢";
    if (activeProf === 'smart_working') profPrefix = "💼";
    else if (activeProf === 'holiday') profPrefix = "🎉";

    let expiryHtml = '';
    if (sched.profile_expires_at) {
      const expDate = new Date(sched.profile_expires_at);
      const expStr = isNaN(expDate.getTime()) ? String(sched.profile_expires_at) : expDate.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
      expiryHtml = `
        <span class="badge badge-amber badge-btn" id="btn-cancel-expiry" title="Annulla scadenza">
          ⏳ Fino a ${expStr} ✕
        </span>
      `;
    }

    let srHtml = '';
    const sr = sched.smart_return;
    if (sr && sr.active) {
      const arr = sr.arrival_time ? sr.arrival_time.substring(0, 5) : '';
      srHtml = `
        <span class="badge badge-orange badge-btn" id="btn-cancel-sr" title="Annulla Smart Return">
          🚗 Rientro ore ${arr} ✕
        </span>
      `;
    }

    container.innerHTML = `
      <div class="header-bar">
        <div class="header-title-box">
          <ha-icon icon="mdi:calendar-clock"></ha-icon>
          <div class="header-title">${this._t('sched_title')}</div>
          <div class="header-badges">
            <button class="badge ${enabled ? 'badge-green' : 'badge-gray'} badge-btn" id="btn-toggle-sched">
              ${enabled ? '🟢 ' + this._t('sched_active') : '⚪ ' + this._t('sched_paused')}
            </button>
            <span class="badge badge-blue">
              ${profPrefix} ${profName}
            </span>
            ${expiryHtml}
            ${srHtml}
          </div>
        </div>
        <div class="header-actions">
          <button class="btn btn-primary" id="btn-open-activate">
            📅 ${this._t('sched_activate_btn')}
          </button>
          <button class="btn btn-amber" id="btn-open-sr">
            🚗 ${this._t('sched_smart_return_btn')}
          </button>
          <button class="btn" id="btn-reset-overrides" title="${this._t('sched_reset_overrides')}">
            ↺ ${this._t('sched_reset_overrides')}
          </button>
        </div>
      </div>
    `;

    container.querySelector('#btn-toggle-sched')?.addEventListener('click', () => {
      this._toggleScheduler(!enabled);
    });
    container.querySelector('#btn-cancel-expiry')?.addEventListener('click', (e) => {
      e.stopPropagation();
      this._cancelProfileExpiry();
    });
    container.querySelector('#btn-cancel-sr')?.addEventListener('click', (e) => {
      e.stopPropagation();
      this._cancelSmartReturn();
    });
    container.querySelector('#btn-open-activate')?.addEventListener('click', () => {
      this.openActivateModal();
    });
    container.querySelector('#btn-open-sr')?.addEventListener('click', () => {
      this.openSmartReturnModal();
    });
    container.querySelector('#btn-reset-overrides')?.addEventListener('click', () => {
      this._clearAllOverrides();
    });
  }

  _toggleScheduler(enable) {
    if (!this._hass) return;
    for (const eid of Object.keys(this._hass.states)) {
      if (eid.startsWith('switch.') && (eid.includes('weekly_scheduler') || eid.includes('scheduler'))) {
        this._hass.callService('switch', enable ? 'turn_on' : 'turn_off', { entity_id: eid });
        return;
      }
    }
    for (const eid of Object.keys(this._hass.states)) {
      if (eid.startsWith('switch.') && this._hass.states[eid].attributes?.schedule_status && this._hass.states[eid].attributes?.multizone_type !== 'master') {
        this._hass.callService('switch', enable ? 'turn_on' : 'turn_off', { entity_id: eid });
        return;
      }
    }
  }

  _cancelProfileExpiry() {
    if (!this._hass) return;
    const sched = this._getScheduleStatus();
    this._hass.callService('multizone_thermostat', 'activate_schedule_profile', {
      profile_id: sched.fallback_profile || 'standard',
      expires_at: ''
    });
  }

  _cancelSmartReturn() {
    if (!this._hass) return;
    this._hass.callService('multizone_thermostat', 'cancel_smart_return', {});
  }

  _clearAllOverrides() {
    if (!this._hass) return;
    this._hass.callService('multizone_thermostat', 'clear_zone_override', {});
  }

  renderLiveZones() {
    const container = this.shadowRoot.querySelector('#zones-container');
    if (!container) return;

    const zones = this._getZones();
    if (zones.length === 0) {
      container.innerHTML = `<div style="opacity:0.6; margin-bottom: 20px;">Nessuna zona termostato configurata.</div>`;
      return;
    }

    container.innerHTML = `
      <div class="live-zones-grid">
        ${zones.map(z => {
          let badgeHtml = '';
          if (z.hvac_mode === 'off') {
            badgeHtml = `<span class="badge badge-gray" style="color: #f87171;">⛔ ${this._t('sched_explicit_off')}</span>`;
          } else if (z.manual_override) {
            let untilStr = '';
            if (z.override_until) {
              const d = new Date(z.override_until);
              untilStr = isNaN(d.getTime()) ? String(z.override_until) : d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
            }
            badgeHtml = `
              <span class="badge badge-amber badge-btn btn-clear-zone-override" data-zone="${z.climate}" title="${this._t('sched_restore')}">
                ✋ ${z.target_temp.toFixed(1)}°C ${untilStr ? this._t('sched_override_until') + ' ' + untilStr : ''} ✕
              </span>
            `;
          } else if (z.smart_start) {
            badgeHtml = `<span class="badge badge-orange">🔥 Smart Start ${z.smart_start_detail || ''}</span>`;
          } else {
            badgeHtml = `<span class="badge badge-green">🌿 ${z.target_temp.toFixed(1)}°C</span>`;
          }

          const isOff = z.hvac_mode === 'off';
          return `
            <div class="zone-card" data-zone="${z.climate}">
              <div class="zone-card-top">
                <span class="zone-card-title">${z.name}</span>
                ${badgeHtml}
              </div>
              <div class="zone-card-mid">
                <div class="temp-display">
                  <span class="current-temp">${z.current_temp.toFixed(1)}°C</span>
                  <span style="opacity:0.6;">➔</span>
                  <span class="target-temp">${z.target_temp.toFixed(1)}°C</span>
                </div>
                <div class="temp-controls">
                  <button class="btn-circle btn-temp-down" data-zone="${z.climate}" data-target="${z.target_temp}">-</button>
                  <button class="btn-circle btn-temp-up" data-zone="${z.climate}" data-target="${z.target_temp}">+</button>
                  <button class="btn ${isOff ? 'btn-primary' : 'btn-danger'}" data-zone="${z.climate}" data-action="toggle-power" style="padding: 4px 10px; font-size: 0.75rem;">
                    ${isOff ? this._t('sched_turn_on') : 'OFF'}
                  </button>
                </div>
              </div>
              <div class="zone-card-bottom">
                <span>⚡ Inerzia: ${z.heating_rate.toFixed(1)} °C/h</span>
                <span title="${z.climate}">${z.climate.replace('climate.', '')}</span>
              </div>
            </div>
          `;
        }).join('')}
      </div>
    `;

    container.querySelectorAll('.btn-clear-zone-override').forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        const cid = btn.getAttribute('data-zone');
        if (this._hass && cid) {
          this._hass.callService('multizone_thermostat', 'clear_zone_override', { entity_id: cid });
        }
      });
    });

    container.querySelectorAll('.btn-temp-down').forEach(btn => {
      btn.addEventListener('click', () => {
        const cid = btn.getAttribute('data-zone');
        const cur = parseFloat(btn.getAttribute('data-target')) || 20.0;
        this._setZoneTemp(cid, Math.max(5.0, cur - 0.5));
      });
    });

    container.querySelectorAll('.btn-temp-up').forEach(btn => {
      btn.addEventListener('click', () => {
        const cid = btn.getAttribute('data-zone');
        const cur = parseFloat(btn.getAttribute('data-target')) || 20.0;
        this._setZoneTemp(cid, Math.min(35.0, cur + 0.5));
      });
    });

    container.querySelectorAll('[data-action="toggle-power"]').forEach(btn => {
      btn.addEventListener('click', () => {
        const cid = btn.getAttribute('data-zone');
        const z = zones.find(item => item.climate === cid);
        if (z && this._hass) {
          const nextMode = z.hvac_mode === 'off' ? 'heat' : 'off';
          this._hass.callService('climate', 'set_hvac_mode', { entity_id: cid, hvac_mode: nextMode });
        }
      });
    });
  }

  _setZoneTemp(entityId, temp) {
    if (!this._hass) return;
    this._hass.callService('climate', 'set_temperature', {
      entity_id: entityId,
      temperature: temp
    });
  }

  renderEditor() {
    const container = this.shadowRoot.querySelector('#editor-container');
    if (!container) return;

    const sched = this._getScheduleStatus();
    const activeProf = sched.active_profile || 'standard';
    const isBgEdit = this._editorProfileId !== activeProf;

    const profilesList = Object.keys(sched.profiles || { standard: {} });
    if (!profilesList.includes('standard')) profilesList.unshift('standard');
    if (!profilesList.includes('smart_working')) profilesList.push('smart_working');
    if (!profilesList.includes('holiday')) profilesList.push('holiday');

    const currentProfileData = sched.profiles?.[this._editorProfileId] || { baseline_preset: 'eco', days: {} };
    const currentBaseline = currentProfileData.baseline_preset || 'eco';

    const dayLabels = {
      mon: this._t('day_mon').substring(0, 3),
      tue: this._t('day_tue').substring(0, 3),
      wed: this._t('day_wed').substring(0, 3),
      thu: this._t('day_thu').substring(0, 3),
      fri: this._t('day_fri').substring(0, 3),
      sat: this._t('day_sat').substring(0, 3),
      sun: this._t('day_sun').substring(0, 3),
    };
    const dayMap = ['sun', 'mon', 'tue', 'wed', 'thu', 'fri', 'sat'];
    const todayDay = dayMap[new Date().getDay()];

    container.innerHTML = `
      <div class="editor-box">
        <div class="editor-header-bar">
          <div class="profile-tabs">
            ${profilesList.map(pId => {
              const pObj = sched.profiles?.[pId];
              let pLabel = pObj?.name || pId.toUpperCase();
              let icon = "🟢";
              if (pId === 'smart_working') icon = "💼";
              else if (pId === 'holiday') icon = "🎉";
              const isActive = this._editorProfileId === pId;
              return `
                <button class="profile-tab ${isActive ? 'active' : ''}" data-profile="${pId}">
                  ${icon} ${pLabel}
                </button>
              `;
            }).join('')}
          </div>
          <div class="editor-controls">
            <div class="baseline-select-box">
              <span>${this._t('sched_baseline')}:</span>
              <select id="select-baseline">
                <option value="eco" ${currentBaseline === 'eco' ? 'selected' : ''}>🌿 Eco</option>
                <option value="sleep" ${currentBaseline === 'sleep' ? 'selected' : ''}>🌙 Notte</option>
                <option value="away" ${currentBaseline === 'away' ? 'selected' : ''}>🚶 Away</option>
                <option value="comfort" ${currentBaseline === 'comfort' ? 'selected' : ''}>🔥 Comfort</option>
              </select>
            </div>
            <button class="btn" id="btn-duplicate-profile">
              📋 ${this._t('sched_duplicate')}
            </button>
            <button class="btn btn-primary" id="btn-new-slot">
              ${this._t('sched_new_block')}
            </button>
          </div>
        </div>

        ${isBgEdit ? `
          <div class="bg-notice-banner">
            <span>✏️</span>
            <span>${this._t('sched_bg_edit_notice')}</span>
          </div>
        ` : ''}

        <div class="toolbar-bar">
          <div class="day-pills">
            ${['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun'].map(d => {
              const isSel = this._selectedDay === d;
              const isToday = todayDay === d;
              return `
                <button class="day-pill ${isSel ? 'active' : ''} ${isToday ? 'today' : ''}" data-day="${d}">
                  ${dayLabels[d]}
                </button>
              `;
            }).join('')}
          </div>
          <div style="display:flex; gap:8px;">
            <button class="btn" id="btn-copy-weekdays" style="padding:4px 8px; font-size:0.75rem;">
              ⚡ ${this._t('sched_copy_weekdays')}
            </button>
            <button class="btn" id="btn-copy-weekend" style="padding:4px 8px; font-size:0.75rem;">
              ⚡ ${this._t('sched_copy_weekend')}
            </button>
          </div>
        </div>

        <div class="matrix-container" id="matrix-scroll-area">
          <div class="time-ruler">
            ${Array.from({ length: 13 }).map((_, i) => {
              const h = String(i * 2).padStart(2, '0');
              return `<div class="ruler-hour">${h}:00</div>`;
            }).join('')}
          </div>
          <div id="matrix-rows-container"></div>
        </div>
      </div>
    `;

    container.querySelectorAll('.profile-tab').forEach(tab => {
      tab.addEventListener('click', () => {
        this._editorProfileId = tab.getAttribute('data-profile');
        this.renderEditor();
      });
    });

    container.querySelector('#select-baseline')?.addEventListener('change', (e) => {
      this._updateBaselinePreset(e.target.value);
    });

    container.querySelector('#btn-duplicate-profile')?.addEventListener('click', () => {
      this.openDuplicateModal();
    });

    container.querySelector('#btn-new-slot')?.addEventListener('click', () => {
      this.openSlotModal({
        isEdit: false,
        preset: 'comfort',
        start: '07:00',
        end: '09:00',
        selectedDays: [this._selectedDay]
      });
    });

    container.querySelectorAll('.day-pill').forEach(pill => {
      pill.addEventListener('click', () => {
        this._selectedDay = pill.getAttribute('data-day');
        this.renderEditor();
      });
    });

    container.querySelector('#btn-copy-weekdays')?.addEventListener('click', () => {
      this._copyDayToRange(['mon', 'tue', 'wed', 'thu', 'fri']);
    });

    container.querySelector('#btn-copy-weekend')?.addEventListener('click', () => {
      this._copyDayToRange(['sat', 'sun']);
    });

    this.renderMatrixRows();
  }

  _updateBaselinePreset(newPreset) {
    const sched = JSON.parse(JSON.stringify(this._getScheduleStatus()));
    if (!sched.profiles[this._editorProfileId]) {
      sched.profiles[this._editorProfileId] = { name: this._editorProfileId, baseline_preset: 'eco', days: {} };
    }
    sched.profiles[this._editorProfileId].baseline_preset = newPreset;
    this._localScheduleCache = sched;
    this._saveProfileToServer(this._editorProfileId, sched.profiles[this._editorProfileId]);
  }

  _copyDayToRange(targetDays) {
    const sched = JSON.parse(JSON.stringify(this._getScheduleStatus()));
    const prof = sched.profiles?.[this._editorProfileId];
    if (!prof) return;
    if (!prof.days) prof.days = {};

    const sourceDayBlocks = prof.days[this._selectedDay] || {};
    for (const d of targetDays) {
      if (d === this._selectedDay) continue;
      prof.days[d] = JSON.parse(JSON.stringify(sourceDayBlocks));
    }
    this._localScheduleCache = sched;
    this._saveProfileToServer(this._editorProfileId, prof);
    this.renderMatrixRows();
  }

  renderMatrixRows() {
    const rowsContainer = this.shadowRoot.querySelector('#matrix-rows-container');
    if (!rowsContainer) return;

    const zones = this._getZones();
    const sched = this._getScheduleStatus();
    const prof = sched.profiles?.[this._editorProfileId] || {};
    const daySchedule = prof.days?.[this._selectedDay] || {};

    const dayMap = ['sun', 'mon', 'tue', 'wed', 'thu', 'fri', 'sat'];
    const isToday = dayMap[new Date().getDay()] === this._selectedDay;
    const now = new Date();
    const nowMinutes = now.getHours() * 60 + now.getMinutes();
    const nowPercent = (nowMinutes / 1440) * 100;

    rowsContainer.innerHTML = zones.map(z => {
      const blocks = daySchedule[z.climate] || daySchedule[z.id] || [];
      return `
        <div class="matrix-row" data-zone="${z.climate}">
          <div class="room-label-box">
            <span class="room-title" title="${z.name}">${z.name}</span>
            <button class="room-copy-btn btn-copy-room" data-zone="${z.climate}" title="Copia/Incolla programmazione stanza">
              📋
            </button>
          </div>
          <div class="timeline-track" data-zone="${z.climate}">
            ${Array.from({ length: 12 }).map((_, i) => `
              <div class="grid-line" style="left: ${(i + 1) * (100 / 12)}%;"></div>
            `).join('')}
            ${isToday ? `
              <div class="current-time-line" style="left: ${nowPercent}%;"></div>
            ` : ''}
            ${blocks.map((b, idx) => {
              const startMin = this._toMinutes(b.start);
              const endMin = this._toMinutes(b.end);
              const left = (startMin / 1440) * 100;
              const width = Math.max(1.5, ((endMin - startMin) / 1440) * 100);
              const presetClass = 'block-' + (b.preset || 'comfort');
              return `
                <div class="time-block ${presetClass}" style="left: ${left}%; width: ${width}%;"
                     data-zone="${z.climate}" data-index="${idx}" title="${(b.preset || 'comfort').toUpperCase()}: ${b.start} - ${b.end}">
                  ${(b.preset || 'comfort').substring(0, 3).toUpperCase()} ${b.start}-${b.end}
                </div>
              `;
            }).join('')}
          </div>
        </div>
      `;
    }).join('');

    rowsContainer.querySelectorAll('.btn-copy-room').forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        const cid = btn.getAttribute('data-zone');
        this._handleRoomCopyPaste(cid);
      });
    });

    rowsContainer.querySelectorAll('.timeline-track').forEach(track => {
      track.addEventListener('click', (e) => {
        if (e.target.closest('.time-block')) return;
        const cid = track.getAttribute('data-zone');
        const rect = track.getBoundingClientRect();
        const clickX = e.clientX - rect.left;
        const ratio = Math.max(0, Math.min(1, clickX / rect.width));
        const clickMin = Math.floor(ratio * 1440);
        const startMin = Math.floor(clickMin / 30) * 30;
        const endMin = Math.min(1440, startMin + 120);

        this.openSlotModal({
          isEdit: false,
          zoneId: cid,
          day: this._selectedDay,
          start: this._toTimeStr(startMin),
          end: this._toTimeStr(endMin),
          selectedDays: [this._selectedDay]
        });
      });
    });

    rowsContainer.querySelectorAll('.time-block').forEach(block => {
      block.addEventListener('click', (e) => {
        e.stopPropagation();
        const cid = block.getAttribute('data-zone');
        const idx = parseInt(block.getAttribute('data-index'), 10);
        const blocks = (sched.profiles?.[this._editorProfileId]?.days?.[this._selectedDay]?.[cid]) || [];
        const slot = blocks[idx];
        if (slot) {
          this.openSlotModal({
            isEdit: true,
            zoneId: cid,
            day: this._selectedDay,
            blockIndex: idx,
            preset: slot.preset || 'comfort',
            start: slot.start,
            end: slot.end,
            selectedDays: [this._selectedDay]
          });
        }
      });
    });
  }

  _handleRoomCopyPaste(zoneId) {
    const sched = this._getScheduleStatus();
    const prof = sched.profiles?.[this._editorProfileId];
    if (!prof) return;

    if (!this._copiedRoomSchedule) {
      const blocks = prof.days?.[this._selectedDay]?.[zoneId] || [];
      this._copiedRoomSchedule = {
        sourceZone: zoneId,
        blocks: JSON.parse(JSON.stringify(blocks))
      };
      alert("Programmazione stanza copiata! Clicca di nuovo 📋 su un'altra stanza per incollare.");
    } else {
      if (!prof.days) prof.days = {};
      if (!prof.days[this._selectedDay]) prof.days[this._selectedDay] = {};
      prof.days[this._selectedDay][zoneId] = JSON.parse(JSON.stringify(this._copiedRoomSchedule.blocks));

      const updatedSched = JSON.parse(JSON.stringify(sched));
      updatedSched.profiles[this._editorProfileId] = prof;
      this._localScheduleCache = updatedSched;
      this._saveProfileToServer(this._editorProfileId, prof);
      this.renderMatrixRows();
      this._copiedRoomSchedule = null;
    }
  }

  _toMinutes(timeStr) {
    if (!timeStr) return 0;
    const parts = timeStr.split(':').map(Number);
    return (parts[0] || 0) * 60 + (parts[1] || 0);
  }

  _toTimeStr(min) {
    const h = String(Math.floor(min / 60)).padStart(2, '0');
    const m = String(min % 60).padStart(2, '0');
    return h + ":" + m;
  }

  _applySlotToZone(prof, day, zoneId, startStr, endStr, preset) {
    if (!prof.days) prof.days = {};
    if (!prof.days[day]) prof.days[day] = {};
    if (!prof.days[day][zoneId]) prof.days[day][zoneId] = [];

    const startMin = this._toMinutes(startStr);
    let endMin = this._toMinutes(endStr);
    if (endStr === "23:59" || endStr === "24:00") endMin = 1440;
    if (startMin >= endMin) return;

    const existing = prof.days[day][zoneId];
    const newBlocks = [];

    for (const b of existing) {
      const bStart = this._toMinutes(b.start);
      let bEnd = this._toMinutes(b.end);
      if (b.end === "23:59" || b.end === "24:00") bEnd = 1440;
      const bPreset = b.preset || 'comfort';

      // No overlap
      if (bEnd <= startMin || bStart >= endMin) {
        newBlocks.push({ startMin: bStart, endMin: bEnd, preset: bPreset });
        continue;
      }
      // Overlap left remainder
      if (bStart < startMin) {
        newBlocks.push({ startMin: bStart, endMin: startMin, preset: bPreset });
      }
      // Overlap right remainder
      if (bEnd > endMin) {
        newBlocks.push({ startMin: endMin, endMin: bEnd, preset: bPreset });
      }
    }

    if (preset && preset !== 'none') {
      newBlocks.push({ startMin, endMin, preset });
    }

    newBlocks.sort((a, b) => a.startMin - b.startMin);

    const merged = [];
    for (const blk of newBlocks) {
      if (blk.startMin >= blk.endMin) continue;
      if (merged.length > 0) {
        const last = merged[merged.length - 1];
        if (last.endMin === blk.startMin && last.preset === blk.preset) {
          last.endMin = blk.endMin;
          continue;
        }
      }
      merged.push({ ...blk });
    }

    prof.days[day][zoneId] = merged.map(b => ({
      start: this._toTimeStr(b.startMin),
      end: b.endMin >= 1440 ? "24:00" : this._toTimeStr(b.endMin),
      preset: b.preset
    }));
  }

  _addSlot(zoneId, day, start, end, preset) {
    const sched = JSON.parse(JSON.stringify(this._getScheduleStatus()));
    if (!sched.profiles[this._editorProfileId]) {
      sched.profiles[this._editorProfileId] = {
        name: this._editorProfileId.toUpperCase(),
        baseline_preset: 'eco',
        days: {}
      };
    }
    const prof = sched.profiles[this._editorProfileId];
    this._applySlotToZone(prof, day, zoneId, start, end, preset);

    this._localScheduleCache = sched;
    this._saveProfileToServer(this._editorProfileId, prof);
    this.renderMatrixRows();
  }

  _deleteSlot(zoneId, day, blockIndex) {
    const sched = JSON.parse(JSON.stringify(this._getScheduleStatus()));
    const prof = sched.profiles?.[this._editorProfileId];
    if (prof && prof.days?.[day]?.[zoneId]) {
      prof.days[day][zoneId].splice(blockIndex, 1);
      this._localScheduleCache = sched;
      this._saveProfileToServer(this._editorProfileId, prof);
      this.renderMatrixRows();
    }
  }

  _saveProfileToServer(profileId, profObj) {
    if (!this._hass) return;
    this._hass.callService('multizone_thermostat', 'save_schedule_profile', {
      profile_id: profileId,
      name: profObj.name || profileId,
      baseline_preset: profObj.baseline_preset || 'eco',
      days: profObj.days || {}
    });
  }

  updateCurrentTimeIndicator() {
    const dayMap = ['sun', 'mon', 'tue', 'wed', 'thu', 'fri', 'sat'];
    if (dayMap[new Date().getDay()] !== this._selectedDay) return;

    const now = new Date();
    const nowMinutes = now.getHours() * 60 + now.getMinutes();
    const nowPercent = (nowMinutes / 1440) * 100;
    this.shadowRoot.querySelectorAll('.current-time-line').forEach(el => {
      el.style.left = nowPercent + '%';
    });
  }

  renderPresetMatrixTable() {
    const container = this.shadowRoot.querySelector('#preset-matrix-container');
    if (!container) return;

    const zones = this._getZones();
    if (zones.length === 0) {
      container.innerHTML = '';
      return;
    }

    container.innerHTML = `
      <div class="preset-summary-card">
        <div class="preset-summary-header">
          <div style="display:flex; align-items:center; gap:8px;">
            <span style="font-size:1.15rem;">🌡️</span>
            <div>
              <div style="font-weight:600; font-size:0.925rem;">Temperature Preset Standard</div>
              <div style="font-size:0.75rem; opacity:0.65;">Valori di riferimento in sola lettura sincronizzati dai Preset Standard dell'impianto</div>
            </div>
          </div>
        </div>
        <div class="preset-summary-grid">
          ${zones.map(z => {
            const cVal = this._resolvePresetTemp(z.climate, 'comfort');
            const eVal = this._resolvePresetTemp(z.climate, 'eco');
            const sVal = this._resolvePresetTemp(z.climate, 'sleep');
            const aVal = this._resolvePresetTemp(z.climate, 'away');
            return `
              <div class="preset-summary-zone-card">
                <div class="preset-zone-name">${z.name}</div>
                <div class="preset-badges-row">
                  <span class="preset-badge badge-comfort" title="Comfort">🔥 ${cVal.toFixed(1)}°C</span>
                  <span class="preset-badge badge-eco" title="Eco">🌿 ${eVal.toFixed(1)}°C</span>
                  <span class="preset-badge badge-sleep" title="Notte">🌙 ${sVal.toFixed(1)}°C</span>
                  <span class="preset-badge badge-away" title="Away">🚶 ${aVal.toFixed(1)}°C</span>
                </div>
              </div>
            `;
          }).join('')}
        </div>
      </div>
    `;
  }
  /* ==================== MODALS ==================== */

  closeModal() {
    this._activeModal = null;
    this._modalData = {};
    const modalBox = this.shadowRoot.querySelector('#modal-container');
    if (modalBox) modalBox.innerHTML = '';
  }

  openSlotModal(data) {
    this._activeModal = 'slot';
    this._modalData = data || {};
    const modalContainer = this.shadowRoot.querySelector('#modal-container');
    if (!modalContainer) return;

    const zones = this._getZones();
    const sched = this._getScheduleStatus();
    const prof = sched.profiles?.[this._editorProfileId] || {};
    const currentBaseline = prof.baseline_preset || 'eco';
    const daySchedule = prof.days?.[data.day || this._selectedDay] || {};

    const days = [
      { id: 'mon', label: 'Lun' },
      { id: 'tue', label: 'Mar' },
      { id: 'wed', label: 'Mer' },
      { id: 'thu', label: 'Gio' },
      { id: 'fri', label: 'Ven' },
      { id: 'sat', label: 'Sab' },
      { id: 'sun', label: 'Dom' }
    ];

    const isEdit = !!data.isEdit;
    let curStart = data.start || '07:00';
    let curEnd = data.end || '09:00';
    if (curEnd === '24:00') curEnd = '23:59';
    const selDays = data.selectedDays || [this._selectedDay];

    // Determine initial General Preset and per-zone initial choices
    let initialGeneralPreset = data.preset || 'comfort';
    const initialZoneChoices = {}; // climateId -> 'inherit' | 'comfort' | 'eco' | 'sleep' | 'away' | 'none'

    if (isEdit) {
      const slotStart = data.start;
      const slotEnd = data.end;
      const presetCounts = { comfort: 0, eco: 0, sleep: 0, away: 0 };
      const zoneMatchPreset = {};

      for (const z of zones) {
        const zBlocks = daySchedule[z.climate] || daySchedule[z.id] || [];
        const match = zBlocks.find(b => b.start === slotStart && b.end === slotEnd)
                   || zBlocks.find(b => {
                       const bS = this._toMinutes(b.start);
                       let bE = this._toMinutes(b.end);
                       if (b.end === '23:59' || b.end === '24:00') bE = 1440;
                       const sS = this._toMinutes(slotStart);
                       let sE = this._toMinutes(slotEnd);
                       if (slotEnd === '23:59' || slotEnd === '24:00') sE = 1440;
                       return Math.max(bS, sS) < Math.min(bE, sE);
                     });
        if (match) {
          const p = match.preset || 'comfort';
          zoneMatchPreset[z.climate] = p;
          presetCounts[p] = (presetCounts[p] || 0) + 1;
        } else {
          zoneMatchPreset[z.climate] = 'none';
        }
      }

      let maxC = 0;
      for (const [p, c] of Object.entries(presetCounts)) {
        if (c > maxC) {
          maxC = c;
          initialGeneralPreset = p;
        }
      }

      for (const z of zones) {
        const matchedP = zoneMatchPreset[z.climate];
        if (matchedP === initialGeneralPreset) {
          initialZoneChoices[z.climate] = 'inherit';
        } else if (matchedP && matchedP !== 'none') {
          initialZoneChoices[z.climate] = matchedP;
        } else {
          initialZoneChoices[z.climate] = 'none';
        }
      }
    } else {
      initialGeneralPreset = data.preset || 'comfort';
      for (const z of zones) {
        initialZoneChoices[z.climate] = 'inherit';
      }
    }

    let currentGeneralPreset = initialGeneralPreset;

    const parseTimeInput = (val) => {
      if (!val) return 0;
      if (val === '23:59' || val === '24:00') return 1440;
      const p = val.split(':').map(Number);
      return (p[0] || 0) * 60 + (p[1] || 0);
    };

    const formatTimeInput = (min) => {
      if (min >= 1440) return '23:59';
      const h = String(Math.floor(min / 60)).padStart(2, '0');
      const m = String(min % 60).padStart(2, '0');
      return `${h}:${m}`;
    };

    const formatDurationText = (min) => {
      if (min <= 0) return '0m';
      const h = Math.floor(min / 60);
      const m = min % 60;
      if (h === 0) return `${m}m`;
      if (m === 0) return `${h}h`;
      return `${h}h ${String(m).padStart(2, '0')}m`;
    };

    let startMin = parseTimeInput(curStart);
    let endMin = parseTimeInput(curEnd);
    if (endMin <= startMin) endMin = Math.min(1440, startMin + 120);
    let durationMin = endMin - startMin;

    modalContainer.innerHTML = `
      <div class="modal-overlay" id="slot-modal-backdrop">
        <div class="modal-box slot-modal-wide">
          <div class="modal-title">
            <div style="display:flex; align-items:center; gap:8px;">
              <span>${isEdit ? '✏️ Modifica Fascia Oraria' : '➕ Nuova Fascia Oraria'}</span>
            </div>
            <button class="modal-close-btn" id="modal-close-x">✕</button>
          </div>

          <!-- 1. Orario di Partenza + Durata e Fine sincronizzati -->
          <div class="form-section">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
              <label class="form-label">⏰ Orario e Durata:</label>
              <div id="slot-duration-badge" class="duration-badge">⏱️ Durata: <strong>${formatDurationText(durationMin)}</strong></div>
            </div>
            <div style="display:flex; gap:12px; align-items:flex-end;">
              <div class="form-group" style="flex:1; margin-bottom:0;">
                <span class="sub-label">Orario Inizio</span>
                <input type="time" id="slot-start-time" class="time-input" step="900" value="${curStart}">
              </div>
              <div class="form-group" style="flex:1; margin-bottom:0;">
                <span class="sub-label">Orario Fine</span>
                <input type="time" id="slot-end-time" class="time-input" step="900" value="${curEnd}">
              </div>
            </div>
            <div class="quick-duration-bar">
              <span class="sub-label" style="align-self:center; margin-bottom:0; margin-right:4px;">Durata rapida:</span>
              <button type="button" class="duration-pill ${durationMin === 30 ? 'active' : ''}" data-minutes="30">30m</button>
              <button type="button" class="duration-pill ${durationMin === 60 ? 'active' : ''}" data-minutes="60">1h</button>
              <button type="button" class="duration-pill ${durationMin === 90 ? 'active' : ''}" data-minutes="90">1.5h</button>
              <button type="button" class="duration-pill ${durationMin === 120 ? 'active' : ''}" data-minutes="120">2h</button>
              <button type="button" class="duration-pill ${durationMin === 180 ? 'active' : ''}" data-minutes="180">3h</button>
              <button type="button" class="duration-pill ${durationMin === 240 ? 'active' : ''}" data-minutes="240">4h</button>
              <button type="button" class="duration-pill ${durationMin === 360 ? 'active' : ''}" data-minutes="360">6h</button>
            </div>
          </div>

          <!-- 2. Giorni della Settimana -->
          <div class="form-section">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
              <label class="form-label">📅 Giorni di Applicazione:</label>
              <div style="display:flex; gap:6px;">
                <button type="button" class="btn btn-xs" id="btn-quick-weekdays">Lun-Ven</button>
                <button type="button" class="btn btn-xs" id="btn-quick-weekend">Sab-Dom</button>
                <button type="button" class="btn btn-xs" id="btn-quick-all">Tutti</button>
              </div>
            </div>
            <div class="checkbox-group" id="slot-days-group">
              ${days.map(d => `
                <label class="checkbox-label ${selDays.includes(d.id) ? 'checked' : ''}">
                  <input type="checkbox" value="${d.id}" ${selDays.includes(d.id) ? 'checked' : ''}>
                  ${d.label}
                </label>
              `).join('')}
            </div>
          </div>

          <!-- 3. Preset Generale della Fascia -->
          <div class="form-section">
            <label class="form-label">🎯 Preset Generale della Fascia:</label>
            <div class="sub-label" style="margin-bottom:8px;">Preset principale applicato a tutte le stanze per questa fascia:</div>
            <div class="general-preset-grid">
              <button type="button" class="general-preset-card preset-card-comfort ${initialGeneralPreset === 'comfort' ? 'active' : ''}" data-preset="comfort">
                <div class="preset-card-icon">🔥</div>
                <div class="preset-card-name">Comfort</div>
              </button>
              <button type="button" class="general-preset-card preset-card-eco ${initialGeneralPreset === 'eco' ? 'active' : ''}" data-preset="eco">
                <div class="preset-card-icon">🌿</div>
                <div class="preset-card-name">Eco</div>
              </button>
              <button type="button" class="general-preset-card preset-card-sleep ${initialGeneralPreset === 'sleep' ? 'active' : ''}" data-preset="sleep">
                <div class="preset-card-icon">🌙</div>
                <div class="preset-card-name">Notte</div>
              </button>
              <button type="button" class="general-preset-card preset-card-away ${initialGeneralPreset === 'away' ? 'active' : ''}" data-preset="away">
                <div class="preset-card-icon">🚶</div>
                <div class="preset-card-name">Away</div>
              </button>
            </div>
          </div>

          <!-- 4. Eccezioni per Singole Zone -->
          <div class="form-section">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
              <label class="form-label">🏠 Eccezioni per Singole Zone (Opzionale):</label>
            </div>
            <div class="sub-label" style="margin-bottom:8px;">Personalizza o escludi specifiche stanze mantenendo il resto dell'impianto sul Preset Generale:</div>
            <div class="zone-exceptions-container">
              ${zones.map(z => {
                const cTemp = this._resolvePresetTemp(z.climate, 'comfort');
                const eTemp = this._resolvePresetTemp(z.climate, 'eco');
                const sTemp = this._resolvePresetTemp(z.climate, 'sleep');
                const aTemp = this._resolvePresetTemp(z.climate, 'away');
                const baseTemp = this._resolvePresetTemp(z.climate, currentBaseline);
                const initialVal = initialZoneChoices[z.climate] || 'inherit';

                return `
                  <div class="zone-exception-row" data-zone="${z.climate}">
                    <div class="zone-exception-name" title="${z.name}">🏠 ${z.name}</div>
                    <div class="zone-exception-control">
                      <select class="zone-override-select" data-zone="${z.climate}">
                        <option value="inherit" ${initialVal === 'inherit' ? 'selected' : ''}>🔗 Segui Preset Generale</option>
                        <option value="comfort" ${initialVal === 'comfort' ? 'selected' : ''}>🔥 Comfort (${cTemp.toFixed(1)}°C)</option>
                        <option value="eco" ${initialVal === 'eco' ? 'selected' : ''}>🌿 Eco (${eTemp.toFixed(1)}°C)</option>
                        <option value="sleep" ${initialVal === 'sleep' ? 'selected' : ''}>🌙 Notte (${sTemp.toFixed(1)}°C)</option>
                        <option value="away" ${initialVal === 'away' ? 'selected' : ''}>🚶 Away (${aTemp.toFixed(1)}°C)</option>
                        <option value="none" ${initialVal === 'none' ? 'selected' : ''}>⏸️ Nessuna modifica / Baseline (${baseTemp.toFixed(1)}°C)</option>
                      </select>
                    </div>
                  </div>
                `;
              }).join('')}
            </div>
          </div>

          <!-- Azioni Modale -->
          <div class="modal-actions">
            ${isEdit ? `
              <button type="button" class="btn btn-danger" id="btn-delete-slot">
                🗑️ Elimina Fascia
              </button>
            ` : ''}
            <button type="button" class="btn" id="btn-cancel-modal">
              Annulla
            </button>
            <button type="button" class="btn btn-primary" id="btn-save-slot">
              💾 Salva Fascia
            </button>
          </div>
        </div>
      </div>
    `;

    // Dynamic inherit labels updater
    const updateZoneSelectLabels = (genPreset) => {
      const pInfo = {
        comfort: { label: 'Comfort', icon: '🔥' },
        eco: { label: 'Eco', icon: '🌿' },
        sleep: { label: 'Notte', icon: '🌙' },
        away: { label: 'Away', icon: '🚶' }
      }[genPreset] || { label: 'Comfort', icon: '🔥' };

      modalContainer.querySelectorAll('.zone-override-select').forEach(sel => {
        const zid = sel.getAttribute('data-zone');
        const temp = this._resolvePresetTemp(zid, genPreset);
        const inheritOpt = sel.querySelector('option[value="inherit"]');
        if (inheritOpt) {
          inheritOpt.textContent = `🔗 Segui Preset Generale (${pInfo.icon} ${pInfo.label} · ${temp.toFixed(1)}°C)`;
        }
      });
    };

    updateZoneSelectLabels(currentGeneralPreset);

    // Event listeners
    modalContainer.querySelector('#modal-close-x')?.addEventListener('click', () => this.closeModal());
    modalContainer.querySelector('#btn-cancel-modal')?.addEventListener('click', () => this.closeModal());

    const startInput = modalContainer.querySelector('#slot-start-time');
    const endInput = modalContainer.querySelector('#slot-end-time');
    const badge = modalContainer.querySelector('#slot-duration-badge');

    const updatePillActives = (curDur) => {
      modalContainer.querySelectorAll('.duration-pill').forEach(pill => {
        const m = parseInt(pill.getAttribute('data-minutes'), 10);
        if (m === curDur) pill.classList.add('active');
        else pill.classList.remove('active');
      });
    };

    startInput?.addEventListener('change', () => {
      startMin = parseTimeInput(startInput.value);
      endMin = Math.min(1440, startMin + durationMin);
      endInput.value = formatTimeInput(endMin);
      badge.innerHTML = `⏱️ Durata: <strong>${formatDurationText(durationMin)}</strong>`;
      updatePillActives(durationMin);
    });

    endInput?.addEventListener('change', () => {
      endMin = parseTimeInput(endInput.value);
      if (endMin <= startMin) {
        startMin = Math.max(0, endMin - 15);
        startInput.value = formatTimeInput(startMin);
      }
      durationMin = endMin - startMin;
      badge.innerHTML = `⏱️ Durata: <strong>${formatDurationText(durationMin)}</strong>`;
      updatePillActives(durationMin);
    });

    modalContainer.querySelectorAll('.duration-pill').forEach(pill => {
      pill.addEventListener('click', () => {
        durationMin = parseInt(pill.getAttribute('data-minutes'), 10);
        endMin = Math.min(1440, startMin + durationMin);
        endInput.value = formatTimeInput(endMin);
        badge.innerHTML = `⏱️ Durata: <strong>${formatDurationText(durationMin)}</strong>`;
        updatePillActives(durationMin);
      });
    });

    modalContainer.querySelectorAll('.general-preset-card').forEach(card => {
      card.addEventListener('click', () => {
        currentGeneralPreset = card.getAttribute('data-preset');
        modalContainer.querySelectorAll('.general-preset-card').forEach(c => c.classList.remove('active'));
        card.classList.add('active');
        updateZoneSelectLabels(currentGeneralPreset);
      });
    });

    modalContainer.querySelector('#btn-quick-weekdays')?.addEventListener('click', () => {
      modalContainer.querySelectorAll('#slot-days-group input').forEach(cb => {
        cb.checked = ['mon', 'tue', 'wed', 'thu', 'fri'].includes(cb.value);
      });
    });

    modalContainer.querySelector('#btn-quick-weekend')?.addEventListener('click', () => {
      modalContainer.querySelectorAll('#slot-days-group input').forEach(cb => {
        cb.checked = ['sat', 'sun'].includes(cb.value);
      });
    });

    modalContainer.querySelector('#btn-quick-all')?.addEventListener('click', () => {
      modalContainer.querySelectorAll('#slot-days-group input').forEach(cb => {
        cb.checked = true;
      });
    });

    modalContainer.querySelector('#btn-delete-slot')?.addEventListener('click', () => {
      const schedObj = JSON.parse(JSON.stringify(this._getScheduleStatus()));
      const profObj = schedObj.profiles?.[this._editorProfileId];
      if (profObj) {
        const checkedDays = Array.from(modalContainer.querySelectorAll('#slot-days-group input:checked')).map(cb => cb.value);
        const daysToProcess = checkedDays.length > 0 ? checkedDays : [data.day || this._selectedDay];
        for (const d of daysToProcess) {
          for (const z of zones) {
            this._applySlotToZone(profObj, d, z.climate, curStart, (curEnd === '23:59' ? '24:00' : curEnd), 'none');
          }
        }
        this._localScheduleCache = schedObj;
        this._saveProfileToServer(this._editorProfileId, profObj);
        this.renderMatrixRows();
      }
      this.closeModal();
    });

    modalContainer.querySelector('#btn-save-slot')?.addEventListener('click', () => {
      const sVal = modalContainer.querySelector('#slot-start-time').value;
      const eVal = modalContainer.querySelector('#slot-end-time').value;
      const sMin = parseTimeInput(sVal);
      const eMin = parseTimeInput(eVal);

      if (sMin >= eMin) {
        alert("L'orario di inizio deve precedere quello di fine!");
        return;
      }

      const checkedDays = Array.from(modalContainer.querySelectorAll('#slot-days-group input:checked')).map(cb => cb.value);
      if (checkedDays.length === 0) {
        alert("Seleziona almeno un giorno della settimana!");
        return;
      }

      const schedObj = JSON.parse(JSON.stringify(this._getScheduleStatus()));
      if (!schedObj.profiles[this._editorProfileId]) {
        schedObj.profiles[this._editorProfileId] = {
          name: this._editorProfileId.toUpperCase(),
          baseline_preset: 'eco',
          days: {}
        };
      }
      const profObj = schedObj.profiles[this._editorProfileId];

      const effectiveEndStr = eMin >= 1440 ? '24:00' : eVal;

      for (const d of checkedDays) {
        for (const z of zones) {
          const sel = modalContainer.querySelector(`.zone-override-select[data-zone="${z.climate}"]`);
          const choice = sel ? sel.value : 'inherit';
          const zonePreset = choice === 'inherit' ? currentGeneralPreset : choice;
          this._applySlotToZone(profObj, d, z.climate, sVal, effectiveEndStr, zonePreset);
        }
      }

      this._localScheduleCache = schedObj;
      this._saveProfileToServer(this._editorProfileId, profObj);
      this.renderMatrixRows();
      this.closeModal();
    });
  }  openActivateModal() {
    this._activeModal = 'activate';
    const modalContainer = this.shadowRoot.querySelector('#modal-container');
    if (!modalContainer) return;

    const sched = this._getScheduleStatus();
    const profilesList = Object.keys(sched.profiles || { standard: {} });
    const currentActive = sched.active_profile || 'standard';

    modalContainer.innerHTML = `
      <div class="modal-overlay">
        <div class="modal-box">
          <div class="modal-title">
            <span>📅 ${this._t('sched_activate_btn')}</span>
            <button class="modal-close-btn" id="modal-close-x">✕</button>
          </div>

          <div class="form-group">
            <label class="form-label">Seleziona Profilo da Attivare:</label>
            <select id="activate-profile-select">
              ${profilesList.map(pId => {
                const p = sched.profiles?.[pId];
                return `<option value="${pId}" ${currentActive === pId ? 'selected' : ''}>${p?.name || pId.toUpperCase()}</option>`;
              }).join('')}
            </select>
          </div>

          <div class="form-group">
            <label class="form-label">Durata Attivazione / Scadenza:</label>
            <div style="display:flex; flex-direction:column; gap:8px;">
              <label class="checkbox-label">
                <input type="radio" name="expiry-type" value="permanent" checked>
                Permanente (Nessuna scadenza)
              </label>
              <label class="checkbox-label">
                <input type="radio" name="expiry-type" value="temporary">
                Temporanea con scadenza
              </label>
            </div>
          </div>

          <div id="temporary-expiry-box" style="display:none; flex-direction:column; gap:10px; margin-top:8px;">
            <div style="display:flex; flex-wrap:wrap; gap:6px;">
              <button class="btn" id="btn-exp-24h" style="padding:4px 8px; font-size:0.8rem;">+24 ore</button>
              <button class="btn" id="btn-exp-today" style="padding:4px 8px; font-size:0.8rem;">Fine Oggi 23:59</button>
              <button class="btn" id="btn-exp-sunday" style="padding:4px 8px; font-size:0.8rem;">Fine Domenica 23:59</button>
              <button class="btn" id="btn-exp-3d" style="padding:4px 8px; font-size:0.8rem;">+3 giorni</button>
            </div>
            <input type="datetime-local" id="activate-expires-at">
            <div class="form-group" style="margin-top:6px;">
              <label class="form-label">Profilo di Ripristino (Fallback):</label>
              <select id="activate-fallback-select">
                ${profilesList.map(pId => {
                  return `<option value="${pId}" ${pId === 'standard' ? 'selected' : ''}>${pId.toUpperCase()}</option>`;
                }).join('')}
              </select>
            </div>
          </div>

          <div class="modal-actions">
            <button class="btn" id="btn-cancel-modal">Annulla</button>
            <button class="btn btn-primary" id="btn-confirm-activate">Attiva Profilo</button>
          </div>
        </div>
      </div>
    `;

    modalContainer.querySelector('#modal-close-x')?.addEventListener('click', () => this.closeModal());
    modalContainer.querySelector('#btn-cancel-modal')?.addEventListener('click', () => this.closeModal());

    const expBox = modalContainer.querySelector('#temporary-expiry-box');
    modalContainer.querySelectorAll('input[name="expiry-type"]').forEach(r => {
      r.addEventListener('change', () => {
        expBox.style.display = r.value === 'temporary' ? 'flex' : 'none';
      });
    });

    const dtInput = modalContainer.querySelector('#activate-expires-at');
    const setDt = (d) => {
      const pad = (n) => String(n).padStart(2, '0');
      const s = d.getFullYear() + '-' + pad(d.getMonth() + 1) + '-' + pad(d.getDate()) + 'T' + pad(d.getHours()) + ':' + pad(d.getMinutes());
      dtInput.value = s;
    };

    modalContainer.querySelector('#btn-exp-24h')?.addEventListener('click', () => {
      setDt(new Date(Date.now() + 24 * 3600 * 1000));
    });
    modalContainer.querySelector('#btn-exp-today')?.addEventListener('click', () => {
      const d = new Date();
      d.setHours(23, 59, 0, 0);
      setDt(d);
    });
    modalContainer.querySelector('#btn-exp-sunday')?.addEventListener('click', () => {
      const d = new Date();
      const day = d.getDay();
      const diff = (7 - day) % 7;
      d.setDate(d.getDate() + (diff === 0 ? 7 : diff));
      d.setHours(23, 59, 0, 0);
      setDt(d);
    });
    modalContainer.querySelector('#btn-exp-3d')?.addEventListener('click', () => {
      setDt(new Date(Date.now() + 72 * 3600 * 1000));
    });

    modalContainer.querySelector('#btn-confirm-activate')?.addEventListener('click', () => {
      const profId = modalContainer.querySelector('#activate-profile-select').value;
      const isTemp = modalContainer.querySelector('input[name="expiry-type"]:checked').value === 'temporary';
      let expIso = '';
      let fbProf = 'standard';
      if (isTemp) {
        expIso = dtInput.value ? new Date(dtInput.value).toISOString() : '';
        fbProf = modalContainer.querySelector('#activate-fallback-select').value || 'standard';
      }

      if (this._hass) {
        this._hass.callService('multizone_thermostat', 'activate_schedule_profile', {
          profile_id: profId,
          expires_at: expIso,
          fallback_profile: fbProf
        });
      }
      this.closeModal();
    });
  }

  openSmartReturnModal() {
    this._activeModal = 'smart_return';
    const modalContainer = this.shadowRoot.querySelector('#modal-container');
    if (!modalContainer) return;

    const zones = this._getZones();
    const now = new Date();
    const defArr = new Date(now.getTime() + 2 * 3600 * 1000);
    const defArrStr = String(defArr.getHours()).padStart(2, '0') + ':' + String(defArr.getMinutes()).padStart(2, '0');

    modalContainer.innerHTML = `
      <div class="modal-overlay">
        <div class="modal-box" style="max-width: 580px;">
          <div class="modal-title">
            <span>🚗 ${this._t('sched_smart_return_btn')}</span>
            <button class="modal-close-btn" id="modal-close-x">✕</button>
          </div>

          <div style="display:flex; gap:12px;">
            <div class="form-group" style="flex:1;">
              <label class="form-label">Orario di Rientro Previsto:</label>
              <input type="time" id="sr-arrival-time" value="${defArrStr}">
            </div>
            <div class="form-group" style="flex:1;">
              <label class="form-label">Preset Obiettivo:</label>
              <select id="sr-preset-select">
                <option value="comfort" selected>🔥 Comfort</option>
                <option value="eco">🌿 Eco</option>
              </select>
            </div>
          </div>

          <div style="display:flex; gap:6px; margin-bottom:12px;">
            <button class="btn" id="btn-sr-add-1h" style="padding:4px 8px; font-size:0.8rem;">+1 ora</button>
            <button class="btn" id="btn-sr-add-2h" style="padding:4px 8px; font-size:0.8rem;">+2 ore</button>
            <button class="btn" id="btn-sr-add-3h" style="padding:4px 8px; font-size:0.8rem;">+3 ore</button>
          </div>

          <div class="form-group">
            <label class="form-label">Radar Termico & Accensione Scaglionata (Anteprima Live):</label>
            <div class="radar-list" id="sr-radar-preview"></div>
          </div>

          <div class="modal-actions">
            <button class="btn" id="btn-cancel-modal">Annulla</button>
            <button class="btn btn-amber" id="btn-confirm-sr">🔥 Pianifica Rientro</button>
          </div>
        </div>
      </div>
    `;

    modalContainer.querySelector('#modal-close-x')?.addEventListener('click', () => this.closeModal());
    modalContainer.querySelector('#btn-cancel-modal')?.addEventListener('click', () => this.closeModal());

    const timeInput = modalContainer.querySelector('#sr-arrival-time');
    const presetSelect = modalContainer.querySelector('#sr-preset-select');
    const previewList = modalContainer.querySelector('#sr-radar-preview');

    const updateRadar = () => {
      const arrVal = timeInput.value;
      const chosenPreset = presetSelect.value;
      if (!arrVal) return;

      const [ah, am] = arrVal.split(':').map(Number);
      const arrDate = new Date();
      arrDate.setHours(ah, am, 0, 0);
      if (arrDate.getTime() < Date.now()) {
        arrDate.setDate(arrDate.getDate() + 1);
      }

      const plan = zones.map(z => {
        const targetTemp = this._resolvePresetTemp(z.climate, chosenPreset);
        const curTemp = z.current_temp;
        const delta = Math.max(0, targetTemp - curTemp);
        const rate = z.heating_rate > 0.05 ? z.heating_rate : 1.0;
        const reqMin = Math.ceil((delta / rate) * 60);
        const ignDate = new Date(arrDate.getTime() - reqMin * 60000);
        const ignStr = String(ignDate.getHours()).padStart(2, '0') + ':' + String(ignDate.getMinutes()).padStart(2, '0');
        return {
          zone: z,
          targetTemp,
          curTemp,
          delta,
          rate,
          reqMin,
          ignDate,
          ignStr
        };
      });

      plan.sort((a, b) => b.reqMin - a.reqMin);

      previewList.innerHTML = plan.map(item => {
        const isReady = item.reqMin <= 0;
        return `
          <div class="radar-item">
            <div class="radar-item-left">
              <strong>${item.zone.name}</strong>
              <span style="font-size:0.8rem; opacity:0.8;">
                Attuale: ${item.curTemp.toFixed(1)}°C ➔ Target: ${item.targetTemp.toFixed(1)}°C (Δ ${item.delta.toFixed(1)}°C, ${item.rate.toFixed(1)}°C/h)
              </span>
            </div>
            <div class="radar-item-right">
              ${isReady ? `
                <span class="badge badge-green" style="font-size:0.75rem;">✅ In temperatura</span>
              ` : `
                <span class="badge badge-orange" style="font-size:0.75rem;">⏱️ ${item.reqMin} min</span>
                <span style="font-size:0.75rem; font-weight:700; color:#fcd34d;">Accensione: ${item.ignStr}</span>
              `}
            </div>
          </div>
        `;
      }).join('');
    };

    timeInput.addEventListener('input', updateRadar);
    presetSelect.addEventListener('change', updateRadar);

    modalContainer.querySelector('#btn-sr-add-1h')?.addEventListener('click', () => {
      const d = new Date(Date.now() + 1 * 3600 * 1000);
      timeInput.value = String(d.getHours()).padStart(2, '0') + ':' + String(d.getMinutes()).padStart(2, '0');
      updateRadar();
    });
    modalContainer.querySelector('#btn-sr-add-2h')?.addEventListener('click', () => {
      const d = new Date(Date.now() + 2 * 3600 * 1000);
      timeInput.value = String(d.getHours()).padStart(2, '0') + ':' + String(d.getMinutes()).padStart(2, '0');
      updateRadar();
    });
    modalContainer.querySelector('#btn-sr-add-3h')?.addEventListener('click', () => {
      const d = new Date(Date.now() + 3 * 3600 * 1000);
      timeInput.value = String(d.getHours()).padStart(2, '0') + ':' + String(d.getMinutes()).padStart(2, '0');
      updateRadar();
    });

    updateRadar();

    modalContainer.querySelector('#btn-confirm-sr')?.addEventListener('click', () => {
      const arrival = timeInput.value;
      const preset = presetSelect.value;
      if (this._hass && arrival) {
        this._hass.callService('multizone_thermostat', 'set_smart_return', {
          arrival_time: arrival,
          preset: preset
        });
      }
      this.closeModal();
    });
  }

  openDuplicateModal() {
    this._activeModal = 'duplicate';
    const modalContainer = this.shadowRoot.querySelector('#modal-container');
    if (!modalContainer) return;

    modalContainer.innerHTML = `
      <div class="modal-overlay">
        <div class="modal-box">
          <div class="modal-title">
            <span>📋 ${this._t('sched_duplicate')}</span>
            <button class="modal-close-btn" id="modal-close-x">✕</button>
          </div>

          <div class="form-group">
            <label class="form-label">Profilo Sorgente:</label>
            <input type="text" value="${this._editorProfileId}" disabled style="opacity:0.7;">
          </div>

          <div class="form-group">
            <label class="form-label">Nuovo ID Profilo (es. standard_spring):</label>
            <input type="text" id="dup-target-id" placeholder="es. standard_spring">
          </div>

          <div class="form-group">
            <label class="form-label">Nome Visualizzato (es. Standard Primavera):</label>
            <input type="text" id="dup-target-name" placeholder="es. Standard Primavera">
          </div>

          <div class="modal-actions">
            <button class="btn" id="btn-cancel-modal">Annulla</button>
            <button class="btn btn-primary" id="btn-confirm-dup">Duplica</button>
          </div>
        </div>
      </div>
    `;

    modalContainer.querySelector('#modal-close-x')?.addEventListener('click', () => this.closeModal());
    modalContainer.querySelector('#btn-cancel-modal')?.addEventListener('click', () => this.closeModal());

    modalContainer.querySelector('#btn-confirm-dup')?.addEventListener('click', () => {
      const targetId = modalContainer.querySelector('#dup-target-id').value.trim();
      const targetName = modalContainer.querySelector('#dup-target-name').value.trim() || targetId;

      if (!targetId) {
        alert("Inserisci un ID per il nuovo profilo!");
        return;
      }

      if (this._hass) {
        this._hass.callService('multizone_thermostat', 'duplicate_schedule_profile', {
          source_profile_id: this._editorProfileId,
          target_profile_id: targetId,
          target_name: targetName
        });
      }

      this._editorProfileId = targetId;
      this.closeModal();
      this.renderEditor();
    });
  }
}

if (!customElements.get("multizone-thermostat-scheduler-card")) {
  customElements.define("multizone-thermostat-scheduler-card", MultizoneThermostatSchedulerCard);
}

/* ==================== FLOATING STYLE SWITCHER WITH POPUP MODAL ==================== */
function setHeaderVisibility(hide, retryCount = 0) {
  try {
    // 1. Document head global fallback
    let docStyle = document.getElementById('mz-header-hide-style-global');
    if (hide) {
      if (!docStyle) {
        docStyle = document.createElement('style');
        docStyle.id = 'mz-header-hide-style-global';
        docStyle.textContent = `
          app-header, .header, ha-top-app-bar, ha-top-app-bar-fixed, ha-tabs {
            display: none !important;
          }
          #view, #columns, hui-root {
            padding-top: 0 !important;
            margin-top: 0 !important;
          }
        `;
        document.head.appendChild(docStyle);
      }
    } else {
      if (docStyle) docStyle.remove();
    }

    // 2. Piercing Lovelace hui-root Shadow DOM
    const ha = document.querySelector('home-assistant');
    const main = ha?.shadowRoot?.querySelector('home-assistant-main');
    const lovelace = main?.shadowRoot?.querySelector('ha-panel-lovelace');
    const huiRoot = lovelace?.shadowRoot?.querySelector('hui-root');
    
    if (!huiRoot || !huiRoot.shadowRoot) {
      if (retryCount < 10) {
        setTimeout(() => setHeaderVisibility(hide, retryCount + 1), 300);
      }
      return;
    }

    let style = huiRoot.shadowRoot.querySelector('#mz-header-hide-style');
    if (hide) {
      if (!style) {
        style = document.createElement('style');
        style.id = 'mz-header-hide-style';
        style.textContent = `
          .header, app-header, ha-top-app-bar, ha-top-app-bar-fixed, ha-tabs {
            display: none !important;
          }
          #view, #columns {
            padding-top: 0 !important;
            margin-top: 0 !important;
          }
        `;
        huiRoot.shadowRoot.appendChild(style);
      }
    } else {
      if (style) {
        style.remove();
      }
    }
  } catch (e) {
    console.warn("Could not toggle header visibility:", e);
  }
}

