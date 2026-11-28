/* ==================== DEDICATED TELEMETRY & ADAPTIVE CHARTS CARD ==================== */

class MultizoneThermostatTelemetryCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: 'open' });
    this._target = 'plant';
    this._timeframe = '24h';
    this._historyCache = {};
    this._pendingKey = null;
    this._chartConfigs = {};
    this._copiedNotice = false;
    this._lastUpdateMs = 0;
  }

  setConfig(config) {
    this._config = Object.assign({}, config || {});
    if (this._config.initial_target) {
      this._target = this._config.initial_target;
    }
  }

  getCardSize() {
    return 8;
  }

  connectedCallback() {
    this._styleListener = () => this.render();
    window.addEventListener('mz-style-changed', this._styleListener);
    try {
      const requested = sessionStorage.getItem('mz_telemetry_target');
      if (requested) {
        this._target = requested;
      }
    } catch (e) {}
  }

  disconnectedCallback() {
    if (this._styleListener) {
      window.removeEventListener('mz-style-changed', this._styleListener);
    }
  }

  set hass(hass) {
    this._hass = hass;
    try {
      const requested = sessionStorage.getItem('mz_telemetry_target');
      if (requested && requested !== this._consumedTarget) {
        this._consumedTarget = requested;
        this._target = requested;
      }
    } catch (e) {}
    const now = Date.now();
    if (!this._renderedOnce || now - this._lastUpdateMs > 1500) {
      this._lastUpdateMs = now;
      this.render();
      this._ensureHistoryLoaded();
    }
  }

  _t(k) {
    return getTranslation(this._hass, k);
  }

  _discoverPlantAndZones() {
    const states = (this._hass && this._hass.states) ? this._hass.states : {};
    const keys = Object.keys(states);

    const findSensor = (keywords) => keys.find((k) =>
      k.startsWith('sensor.') && keywords.some((kw) => k.includes(kw))
    ) || null;
    const findBinary = (keywords) => keys.find((k) =>
      k.startsWith('binary_sensor.') && keywords.some((kw) => k.includes(kw))
    ) || null;

    const plant = {
      masterDemand: findSensor(['master_control_master_demand', 'master_demand']),
      plantHealth: findSensor(['plant_health', 'stato_salute_impianto']),
      cycles: findSensor(['boiler_cycles_per_hour', 'frequenza_accensioni_caldaia']),
      runtime: findSensor(['boiler_daily_runtime', 'ore_funzionamento_caldaia_24h']),
      anomaly: findBinary(['plant_anomaly']),
    };

    const zones = [];
    for (const entityId of keys) {
      if (entityId.startsWith('select.') || entityId.startsWith('switch.')) {
        const st = states[entityId];
        if (entityId.includes('pid_') || entityId.includes('split_') || (st && st.attributes && st.attributes.multizone_type === 'pid_manual_unlock')) continue;
        const climateId = st && st.attributes ? st.attributes.climate_entity : null;
        if (climateId && states[climateId] && !zones.some((z) => z.climate === climateId)) {
          let title = states[climateId].attributes.friendly_name || climateId;
          title = title.replace(/^Virtual Thermostats VT /i, '').replace(/^Heating Zones(?: Zone)? /i, '');
          zones.push({ climate: climateId, title });
        }
      }
    }
    for (const entityId of keys) {
      const isFallback = entityId.startsWith('climate.multizone_thermostat_') ||
        (entityId.startsWith('climate.') && states[entityId] && states[entityId].attributes && states[entityId].attributes.hybrid_zone === true);
      if (isFallback && !zones.some((z) => z.climate === entityId)) {
        let title = (states[entityId] && states[entityId].attributes && states[entityId].attributes.friendly_name) || entityId;
        title = title.replace(/^Virtual Thermostats VT /i, '').replace(/^Heating Zones(?: Zone)? /i, '');
        zones.push({ climate: entityId, title });
      }
    }
    zones.sort((a, b) => a.title.localeCompare(b.title));

    zones.forEach((z) => {
      const rawName = z.climate.split('.')[1] || '';
      const slug = rawName.replace(/^multizone_thermostat_/, '');
      const cleanSlug = slug.replace(/^zona_/, '');
      const matchFn = (id) => isZoneEntityMatch(id, cleanSlug);
      z.demand = keys.find((k) => k.startsWith('sensor.') && (k.includes('demand') || k.includes('fabbisogno')) && matchFn(k)) || null;
      z.autotune = keys.find((k) => k.startsWith('sensor.') && k.includes('autotun') && (matchFn(k) || k.includes(slug))) || null;
      z.heatingRate = keys.find((k) => k.startsWith('sensor.') && (k.includes('heating_rate') || k.includes('velocita_riscaldamento')) && matchFn(k)) || null;
      z.coolingRate = keys.find((k) => k.startsWith('sensor.') && (k.includes('cooling_rate') || k.includes('velocita_raffrescamento')) && matchFn(k)) || null;
      z.inertia = keys.find((k) => k.startsWith('sensor.') && (k.includes('thermal_inertia') || k.includes('inerzia_termica')) && matchFn(k)) || null;
      z.energyClass = keys.find((k) => k.startsWith('sensor.') && (k.includes('energy_class') || k.includes('classe_energetica')) && matchFn(k)) || null;
      z.retention = keys.find((k) => k.startsWith('sensor.') && (k.includes('retention') || k.includes('ritenzione')) && matchFn(k)) || null;
      z.sizing = keys.find((k) => k.startsWith('sensor.') && (k.includes('sizing') || k.includes('dimensionamento')) && matchFn(k)) || null;
    });

    if (this._target !== 'plant' && !zones.some((z) => z.climate === this._target)) {
      this._target = 'plant';
    }
    return { plant, zones };
  }

  _getEntityIdsForTarget(plant, zones) {
    if (this._target === 'plant') {
      const ids = [];
      if (plant.masterDemand) ids.push(plant.masterDemand);
      if (plant.cycles) ids.push(plant.cycles);
      if (plant.runtime) ids.push(plant.runtime);
      if (plant.plantHealth) ids.push(plant.plantHealth);
      zones.forEach((z) => { if (z.demand) ids.push(z.demand); });
      return ids;
    }
    const z = zones.find((item) => item.climate === this._target);
    if (!z) return [];
    return [z.climate, z.demand, z.heatingRate, z.coolingRate, z.inertia].filter(Boolean);
  }

  async _ensureHistoryLoaded() {
    if (!this._hass || typeof this._hass.callWS !== 'function') return;
    const { plant, zones } = this._discoverPlantAndZones();
    const hours = this._timeframe === '6h' ? 6 : (this._timeframe === '48h' ? 48 : (this._timeframe === '7d' ? 168 : 24));
    const cacheKey = `${this._target}|${hours}`;
    const cached = this._historyCache[cacheKey];
    const now = Date.now();
    if (cached && (now - cached.fetchedAt) < 60000) return;
    if (this._pendingKey === cacheKey) return;

    const entityIds = this._getEntityIdsForTarget(plant, zones);
    if (entityIds.length === 0) return;

    this._pendingKey = cacheKey;
    try {
      const fetchHours = this._target !== 'plant' ? Math.max(hours, 168) : hours;
      const startTime = new Date(now - fetchHours * 3600 * 1000).toISOString();
      const endTime = new Date(now).toISOString();
      const res = await this._hass.callWS({
        type: 'history/history_during_period',
        start_time: startTime,
        end_time: endTime,
        entity_ids: entityIds,
        minimal_response: false,
        significant_changes_only: false,
        no_attributes: false,
      });
      this._historyCache[cacheKey] = {
        fetchedAt: Date.now(),
        data: res || {},
      };
    } catch (err) {
      // Fallback safely when Recorder WS is unavailable
      this._historyCache[cacheKey] = { fetchedAt: Date.now(), data: {} };
    } finally {
      if (this._pendingKey === cacheKey) this._pendingKey = null;
      this.render();
    }
  }

  _normalizeEntry(raw) {
    if (!raw || typeof raw !== 'object') return null;
    const s = raw.s !== undefined ? raw.s : raw.state;
    const a = raw.a !== undefined ? raw.a : (raw.attributes || {});
    let tsMs = null;
    if (typeof raw.lu === 'number') tsMs = raw.lu * 1000;
    else if (typeof raw.lc === 'number') tsMs = raw.lc * 1000;
    else if (raw.last_updated) tsMs = Date.parse(raw.last_updated);
    else if (raw.last_changed) tsMs = Date.parse(raw.last_changed);
    if (!tsMs || isNaN(tsMs)) return null;
    return { tsMs, state: s, attrs: a || {} };
  }

  _sampleSeries(histEntries, liveStateObj, startMs, endMs, numPoints, extractorFn) {
    const events = [];
    if (Array.isArray(histEntries)) {
      histEntries.forEach((r) => {
        const norm = this._normalizeEntry(r);
        if (norm) events.push(norm);
      });
    }
    if (liveStateObj) {
      events.push({
        tsMs: endMs,
        state: liveStateObj.state,
        attrs: liveStateObj.attributes || {},
      });
    }
    events.sort((a, b) => a.tsMs - b.tsMs);

    const result = new Array(numPoints).fill(null);
    if (events.length === 0) return result;

    let evIdx = 0;
    let current = null;
    for (let i = 0; i < numPoints; i++) {
      const tickMs = startMs + (i / Math.max(1, numPoints - 1)) * (endMs - startMs);
      while (evIdx < events.length && events[evIdx].tsMs <= tickMs) {
        current = events[evIdx];
        evIdx++;
      }
      if (current) {
        const v = extractorFn(current);
        result[i] = (typeof v === 'number' && isFinite(v)) ? Math.round(v * 100) / 100 : null;
      }
    }
    return result;
  }

  _buildTimeAxis(startMs, endMs, numPoints, hours) {
    const axis = [];
    for (let i = 0; i < numPoints; i++) {
      const tickMs = startMs + (i / Math.max(1, numPoints - 1)) * (endMs - startMs);
      const d = new Date(tickMs);
      const hh = String(d.getHours()).padStart(2, '0');
      const mm = String(d.getMinutes()).padStart(2, '0');
      const label = hours >= 72 ? `${d.getDate()}/${d.getMonth() + 1} ${hh}:00` : `${hh}:${mm}`;
      axis.push({ tsMs: tickMs, label });
    }
    return axis;
  }

  _extractBands(histEntries, liveStateObj, startMs, endMs, numPoints, predFn, color, label) {
    const series = this._sampleSeries(histEntries, liveStateObj, startMs, endMs, numPoints, (ev) => predFn(ev) ? 1 : 0);
    const bands = [];
    series.forEach((v, idx) => {
      if (v === 1) {
        if (!bands.length || bands[bands.length - 1].end !== idx - 1) {
          bands.push({ start: idx, end: idx, color, label });
        } else {
          bands[bands.length - 1].end = idx;
        }
      }
    });
    return bands;
  }

  _numFromState(st, attrName = null) {
    if (!st) return null;
    const raw = attrName ? (st.attributes ? st.attributes[attrName] : null) : st.state;
    if (raw === null || raw === undefined || raw === 'unknown' || raw === 'unavailable') return null;
    const f = parseFloat(raw);
    return isNaN(f) || !isFinite(f) ? null : f;
  }

  _computeBounds(arrays, pad = 1, defaultMin = 0, defaultMax = 100) {
    const vals = [];
    arrays.forEach((arr) => {
      if (Array.isArray(arr)) {
        arr.forEach((v) => { if (typeof v === 'number' && isFinite(v)) vals.push(v); });
      }
    });
    if (vals.length === 0) return [defaultMin, defaultMax];
    let mn = Math.min(...vals);
    let mx = Math.max(...vals);
    if (mx - mn < 0.2) {
      mn -= 0.5;
      mx += 0.5;
    }
    return [Math.floor((mn - pad) * 2) / 2, Math.ceil((mx + pad) * 2) / 2];
  }

  _buildPlantDashboard(plant, zones, histData, hours) {
    const states = this._hass.states || {};
    const endMs = Date.now();
    const startMs = endMs - hours * 3600 * 1000;
    const N = 84;
    const axis = this._buildTimeAxis(startMs, endMs, N, hours);
    const unit = getTempUnit(this._hass);

    const mdState = plant.masterDemand ? states[plant.masterDemand] : null;
    const phState = plant.plantHealth ? states[plant.plantHealth] : null;
    const cycState = plant.cycles ? states[plant.cycles] : null;
    const runState = plant.runtime ? states[plant.runtime] : null;
    const mdAttrs = (mdState && mdState.attributes) || {};
    const phAttrs = (phState && phState.attributes) || {};
    const otLive = phAttrs.opentherm || {};

    let boilerType = mdAttrs.boiler_type;
    if (!boilerType) {
      boilerType = otLive.enabled ? 'opentherm' : 'relay';
    }

    const mdHist = plant.masterDemand ? (histData[plant.masterDemand] || []) : [];
    const phHist = plant.plantHealth ? (histData[plant.plantHealth] || []) : [];
    const cycHist = plant.cycles ? (histData[plant.cycles] || []) : [];
    const runHist = plant.runtime ? (histData[plant.runtime] || []) : [];

    const masterSeries = this._sampleSeries(mdHist, mdState, startMs, endMs, N, (ev) => parseFloat(ev.state));
    const boilerOnSeries = this._sampleSeries(mdHist, mdState, startMs, endMs, N, (ev) => {
      if (ev.attrs && typeof ev.attrs.boiler_active === 'boolean') return ev.attrs.boiler_active ? 100 : 0;
      const d = parseFloat(ev.state);
      return (!isNaN(d) && d > 0) ? 100 : 0;
    });

    // Panel 1 & Panel 3 adapt to boilerType
    let panel1, panel3;
    if (boilerType === 'opentherm') {
      const flowS = this._sampleSeries(mdHist, mdState, startMs, endMs, N, (ev) => {
        const raw = ev.attrs.flow_temp !== undefined ? ev.attrs.flow_temp : (ev.attrs.opentherm && ev.attrs.opentherm.flow_temperature);
        return raw !== undefined ? celsiusToDisplay(parseFloat(raw), this._hass) : null;
      });
      const retS = this._sampleSeries(mdHist, mdState, startMs, endMs, N, (ev) => {
        const raw = ev.attrs.return_temp !== undefined ? ev.attrs.return_temp : (ev.attrs.opentherm && ev.attrs.opentherm.return_temperature);
        return raw !== undefined ? celsiusToDisplay(parseFloat(raw), this._hass) : null;
      });
      const modS = this._sampleSeries(mdHist, mdState, startMs, endMs, N, (ev) => parseFloat(ev.attrs.modulation_level));
      const outS = this._sampleSeries(mdHist, mdState, startMs, endMs, N, (ev) => ev.attrs.outdoor_temp !== undefined ? celsiusToDisplay(parseFloat(ev.attrs.outdoor_temp), this._hass) : null);
      const dhwBands = this._extractBands(mdHist, mdState, startMs, endMs, N, (ev) => ev.attrs.dhw_active === true, 'rgba(56, 189, 248, 0.18)', this._t('tel_dhw_band'));
      const [yMin1, yMax1] = this._computeBounds([flowS, retS, outS], 3, 15, 75);
      const condThresh = celsiusToDisplay(55, this._hass);

      panel1 = {
        title: `${this._t('tel_ot_chart')} (${this._timeframe})`,
        badge: 'OPENTHERM BUS',
        badgeColor: '#38bdf8',
        axis, yLeftLabel: unit, yLeftMin: yMin1, yLeftMax: yMax1,
        yRightLabel: '%', yRightMin: 0, yRightMax: 105,
        bands: dhwBands,
        refLines: [{ y: condThresh, axis: 'left', color: '#34d399', dash: '4,4', label: `${Math.round(condThresh)}${unit}` }],
        series: [
          { name: this._t('ot_flow_temp'), data: flowS, axis: 'left', color: '#f97316', width: 2.3, unit },
          { name: this._t('ot_return_temp'), data: retS, axis: 'left', color: '#38bdf8', width: 2.0, unit },
          { name: this._t('tel_outdoor'), data: outS, axis: 'left', color: '#a78bfa', dash: '3,3', width: 1.5, unit },
          { name: this._t('ot_modulation'), data: modS, axis: 'right', color: '#fbbf24', fill: 'rgba(251,191,36,0.16)', width: 1.5, unit: '%' },
        ],
        emptyText: this._t('tel_waiting_history'),
      };

      const dtS = flowS.map((f, i) => (f !== null && retS[i] !== null) ? Math.round((f - retS[i]) * 10) / 10 : null);
      const [dtMin, dtMax] = this._computeBounds([dtS], 2, 0, 20);
      panel3 = {
        title: `${this._t('tel_ot_dt_chart')} (${this._timeframe})`,
        badge: 'ΔT = FLOW - RETURN',
        badgeColor: '#34d399',
        axis, yLeftLabel: unit, yLeftMin: Math.min(0, dtMin), yLeftMax: Math.max(15, dtMax),
        yRightLabel: '%', yRightMin: 0, yRightMax: 105,
        series: [
          { name: 'Boiler ΔT', data: dtS, axis: 'left', color: '#38bdf8', width: 2.2, unit },
          { name: 'Master Demand', data: masterSeries, axis: 'right', color: '#f97316', fill: 'rgba(249,115,22,0.15)', width: 1.6, unit: '%' },
        ],
        emptyText: this._t('tel_waiting_history'),
      };
    } else if (boilerType === 'heat_pump') {
      const outS = this._sampleSeries(mdHist, mdState, startMs, endMs, N, (ev) => ev.attrs.outdoor_temp !== undefined ? celsiusToDisplay(parseFloat(ev.attrs.outdoor_temp), this._hass) : null);
      const [yMinHp, yMaxHp] = this._computeBounds([outS], 3, -5, 30);
      const solarBands = this._extractBands(mdHist, mdState, startMs, endMs, N, (ev) => ev.attrs.solar_boost_active === true, 'rgba(16, 185, 129, 0.16)', this._t('tel_solar_boost'));

      panel1 = {
        title: `${this._t('tel_hp_chart')} (${this._timeframe})`,
        badge: mdAttrs.is_bivalent ? 'BIVALENT HP + GAS' : 'HEAT PUMP',
        badgeColor: '#22d3ee',
        axis, yLeftLabel: '%', yLeftMin: 0, yLeftMax: 105,
        yRightLabel: unit, yRightMin: yMinHp, yRightMax: yMaxHp,
        bands: solarBands,
        series: [
          { name: 'Master Demand', data: masterSeries, axis: 'left', color: '#22d3ee', fill: 'rgba(34,211,238,0.16)', width: 2.2, unit: '%' },
          { name: this._t('tel_generator_on'), data: boilerOnSeries, axis: 'left', color: '#f97316', step: true, width: 1.7, unit: '%' },
          { name: this._t('tel_outdoor'), data: outS, axis: 'right', color: '#fbbf24', dash: '4,3', width: 1.8, unit },
        ],
        emptyText: this._t('tel_waiting_history'),
      };

      const socS = this._sampleSeries(mdHist, mdState, startMs, endMs, N, (ev) => parseFloat(ev.attrs.battery_soc));
      const cycS = this._sampleSeries(cycHist, cycState, startMs, endMs, N, (ev) => parseFloat(ev.state));
      panel3 = {
        title: `${this._t('tel_hp_sec_chart')} (${this._timeframe})`,
        badge: 'ENERGY & CYCLES',
        badgeColor: '#34d399',
        axis, yLeftLabel: '%', yLeftMin: 0, yLeftMax: 105,
        yRightLabel: 'c/h', yRightMin: 0, yRightMax: 6,
        series: [
          { name: 'Battery SoC %', data: socS, axis: 'left', color: '#34d399', fill: 'rgba(16,185,129,0.16)', width: 2.0, unit: '%' },
          { name: this._t('cycles_label'), data: cycS, axis: 'right', color: '#a78bfa', width: 2.0, unit: ' c/h' },
        ],
        emptyText: this._t('tel_waiting_history'),
      };
    } else if (boilerType === 'centralized') {
      panel1 = {
        title: `${this._t('tel_central_chart')} (${this._timeframe})`,
        badge: 'CENTRALIZED PLANT',
        badgeColor: '#34d399',
        axis, yLeftLabel: '%', yLeftMin: 0, yLeftMax: 105,
        series: [
          { name: 'Master Demand', data: masterSeries, axis: 'left', color: '#f97316', fill: 'rgba(249,115,22,0.16)', width: 2.3, unit: '%' },
        ],
        emptyText: this._t('tel_waiting_history'),
      };
      const runS = this._sampleSeries(runHist, runState, startMs, endMs, N, (ev) => parseFloat(ev.state));
      panel3 = {
        title: `${this._t('runtime_24h')} (${this._timeframe})`,
        badge: 'CONDO RUNTIME',
        badgeColor: '#60a5fa',
        axis, yLeftLabel: 'h', yLeftMin: 0, yLeftMax: 24,
        series: [
          { name: this._t('runtime_24h'), data: runS, axis: 'left', color: '#60a5fa', fill: 'rgba(96,165,250,0.16)', width: 2.1, unit: ' h' },
        ],
        emptyText: this._t('tel_waiting_history'),
      };
    } else {
      // Relay PWM Boiler
      panel1 = {
        title: `${this._t('tel_relay_chart')} (${this._timeframe})`,
        badge: 'RELAY PWM (SINGLE PULSE • >=95% ON)',
        badgeColor: '#38bdf8',
        axis, yLeftLabel: '%', yLeftMin: 0, yLeftMax: 105,
        refLines: [{ y: 95, axis: 'left', color: '#34d399', dash: '4,4', label: '95% ON' }],
        series: [
          { name: this._t('tel_generator_on'), data: boilerOnSeries, axis: 'left', color: '#f97316', step: true, fill: 'rgba(249,115,22,0.20)', width: 1.8, unit: '%' },
          { name: 'Master Demand %', data: masterSeries, axis: 'left', color: '#38bdf8', width: 2.2, unit: '%' },
        ],
        emptyText: this._t('tel_waiting_history'),
      };

      const cycS = this._sampleSeries(cycHist, cycState, startMs, endMs, N, (ev) => parseFloat(ev.state));
      const runS = this._sampleSeries(runHist, runState, startMs, endMs, N, (ev) => parseFloat(ev.state));
      panel3 = {
        title: `${this._t('tel_cycles_chart')} (${this._timeframe})`,
        badge: 'SHORT-CYCLE GUARD (< 5 c/h)',
        badgeColor: '#a78bfa',
        axis, yLeftLabel: 'c/h', yLeftMin: 0, yLeftMax: 6,
        yRightLabel: 'h', yRightMin: 0, yRightMax: 24,
        refLines: [{ y: 5.0, axis: 'left', color: '#f87171', dash: '4,4', label: '5 c/h' }],
        series: [
          { name: this._t('cycles_unit'), data: cycS, axis: 'left', color: '#a78bfa', width: 2.2, unit: ' c/h' },
          { name: this._t('runtime_24h'), data: runS, axis: 'right', color: '#34d399', fill: 'rgba(16,185,129,0.14)', width: 1.8, unit: ' h' },
        ],
        emptyText: this._t('tel_waiting_history'),
      };
    }

    // Panel 2: Zone Contributions vs Master Demand
    const palette = ['#38bdf8', '#34d399', '#a78bfa', '#fbbf24', '#f472b6', '#2dd4bf'];
    const zSeries = [
      { name: 'Master Demand', data: masterSeries, axis: 'left', color: '#f97316', width: 2.5, unit: '%' },
    ];
    zones.slice(0, 6).forEach((z, idx) => {
      if (!z.demand) return;
      const zS = this._sampleSeries(histData[z.demand] || [], states[z.demand], startMs, endMs, N, (ev) => parseFloat(ev.state));
      zSeries.push({ name: z.title, data: zS, axis: 'left', color: palette[idx % palette.length], width: 1.7, unit: '%' });
    });
    const panel2 = {
      title: `${this._t('tel_zone_contrib_chart')} (${this._timeframe})`,
      badge: (mdAttrs.strategy || 'AGGREGATION').toUpperCase(),
      badgeColor: '#60a5fa',
      axis, yLeftLabel: '%', yLeftMin: 0, yLeftMax: 105,
      series: zSeries,
      emptyText: this._t('tel_waiting_history'),
    };

    const kpis = [
      { icon: '⚙️', label: this._t('tel_kpi_backend'), val: String(boilerType).toUpperCase(), color: '#38bdf8' },
      { icon: '📊', label: 'Master Demand', val: `${this._numFromState(mdState) !== null ? this._numFromState(mdState).toFixed(1) : '--'} %`, color: '#f97316' },
      { icon: '🔄', label: this._t('cycles_label'), val: `${this._numFromState(cycState) !== null ? this._numFromState(cycState).toFixed(1) : '--'} ${this._t('cycles_unit')}`, color: '#34d399' },
      { icon: '🕒', label: this._t('runtime_24h'), val: `${this._numFromState(runState) !== null ? this._numFromState(runState).toFixed(1) : '--'} ${this._t('hours')}`, color: '#60a5fa' },
      { icon: '🏔️', label: 'Peak Zone', val: mdAttrs.peak_zone || '--', color: '#e2e8f5' },
      { icon: 'ℹ️', label: 'Status', val: mdAttrs.boiler_status || (phState ? phState.state : '--'), color: '#cbd5e1' },
    ];
    if (boilerType === 'opentherm' && (mdAttrs.flow_temp !== undefined || otLive.flow_temperature !== undefined)) {
      const fVal = mdAttrs.flow_temp !== undefined ? mdAttrs.flow_temp : otLive.flow_temperature;
      const rVal = mdAttrs.return_temp !== undefined ? mdAttrs.return_temp : otLive.return_temperature;
      const mVal = mdAttrs.modulation_level !== undefined ? mdAttrs.modulation_level : otLive.modulation_level;
      kpis.push({ icon: '🌡️', label: `${this._t('ot_flow_temp')} / ${this._t('ot_return_temp')}`, val: `${fVal !== undefined ? fVal : '--'}${unit} / ${rVal !== undefined ? rVal : '--'}${unit}`, color: '#fbbf24' });
      kpis.push({ icon: '🔥', label: this._t('ot_modulation'), val: `${mVal !== undefined ? mVal : '--'}%`, color: '#f97316' });
    }

    return {
      mode: 'plant',
      boilerType,
      panels: [panel1, panel2, panel3],
      kpis,
      bars: null,
    };
  }

  _buildZoneDashboard(zone, histData, hours) {
    const states = this._hass.states || {};
    const endMs = Date.now();
    const startMs = endMs - hours * 3600 * 1000;
    const N = 84;
    const axis = this._buildTimeAxis(startMs, endMs, N, hours);
    const axis7d = this._buildTimeAxis(endMs - 168 * 3600 * 1000, endMs, 42, 168);
    const unit = getTempUnit(this._hass);

    const clState = states[zone.climate];
    const demState = zone.demand ? states[zone.demand] : null;
    const autoState = zone.autotune ? states[zone.autotune] : null;
    const clAttrs = (clState && clState.attributes) || {};
    const demAttrs = (demState && demState.attributes) || {};
    const autoAttrs = (autoState && autoState.attributes) || {};

    const ctrlMode = demAttrs.control_mode || 'smart_pid';
    const isHyst = ctrlMode === 'hysteresis';
    const isCool = demAttrs.active_track === 'cool' || (clState && clState.state === 'cool');
    const actType = demAttrs.actuator_type || 'trv';

    const clHist = histData[zone.climate] || [];
    const demHist = zone.demand ? (histData[zone.demand] || []) : [];

    const tempS = this._sampleSeries(clHist, clState, startMs, endMs, N, (ev) => ev.attrs.current_temperature !== undefined ? celsiusToDisplay(parseFloat(ev.attrs.current_temperature), this._hass) : null);
    const targetS = this._sampleSeries(clHist, clState, startMs, endMs, N, (ev) => ev.attrs.temperature !== undefined ? celsiusToDisplay(parseFloat(ev.attrs.temperature), this._hass) : null);
    const demS = this._sampleSeries(demHist, demState, startMs, endMs, N, (ev) => parseFloat(ev.state));
    const winBands = this._extractBands(demHist, demState, startMs, endMs, N, (ev) => ev.attrs && ev.attrs.window_open === true, 'rgba(148,163,184,0.22)', this._t('tel_window_open'));

    const [tMin, tMax] = this._computeBounds([tempS, targetS], 0.8, 16, 26);

    const c1Series = [
      { name: this._t('temp_detected'), data: tempS, axis: 'left', color: isCool ? '#22d3ee' : '#f87171', width: 2.4, unit },
      { name: this._t('target'), data: targetS, axis: 'left', color: '#34d399', dash: '5,4', unit },
      { name: 'Demand %', data: demS, axis: 'right', color: '#38bdf8', fill: 'rgba(56,189,248,0.16)', width: 1.8, unit: '%' },
    ];
    if (actType === 'pwm_relay' || actType === 'mixed') {
      const pwmS = this._sampleSeries(demHist, demState, startMs, endMs, N, (ev) => {
        if (ev.attrs && typeof ev.attrs.pwm_output_on === 'boolean') return ev.attrs.pwm_output_on ? 100 : 0;
        return null;
      });
      if (pwmS.some((v) => v !== null)) {
        c1Series.push({ name: 'PWM ON/OFF', data: pwmS, axis: 'right', color: '#fbbf24', step: true, width: 1.6, unit: '%' });
      }
    }

    const curTarget = this._numFromState(clState, 'temperature');
    const hBand = (isHyst && curTarget !== null)
      ? { minVal: celsiusToDisplay(curTarget - 0.3, this._hass), maxVal: celsiusToDisplay(curTarget + 0.3, this._hass), color: 'rgba(52, 211, 153, 0.14)' }
      : null;

    const panel1 = {
      title: `${this._t('tel_temp_demand_chart')} (${this._timeframe})`,
      badge: `${String(actType).toUpperCase()} • ${isCool ? 'COOL' : 'HEAT'}`,
      badgeColor: isCool ? '#22d3ee' : '#38bdf8',
      axis, yLeftLabel: unit, yLeftMin: tMin, yLeftMax: tMax,
      yRightLabel: '%', yRightMin: 0, yRightMax: 105,
      bands: winBands,
      hBand,
      series: c1Series,
      emptyText: this._t('tel_waiting_history'),
    };

    // Panel 2: Physical Model 7d
    const start7 = endMs - 168 * 3600 * 1000;
    const hrS = this._sampleSeries(zone.heatingRate ? (histData[zone.heatingRate] || []) : [], zone.heatingRate ? states[zone.heatingRate] : null, start7, endMs, 42, (ev) => parseFloat(ev.state));
    const crS = this._sampleSeries(zone.coolingRate ? (histData[zone.coolingRate] || []) : [], zone.coolingRate ? states[zone.coolingRate] : null, start7, endMs, 42, (ev) => parseFloat(ev.state));
    const inS = this._sampleSeries(zone.inertia ? (histData[zone.inertia] || []) : [], zone.inertia ? states[zone.inertia] : null, start7, endMs, 42, (ev) => parseFloat(ev.state));
    const [rMin, rMax] = this._computeBounds([hrS, crS], 0.3, 0, 2.5);
    const [iMin, iMax] = this._computeBounds([inS], 0.1, 0, 0.5);

    const panel2 = {
      title: this._t('tel_phys_chart'),
      badge: demAttrs.k_loss ? `k_loss: ${demAttrs.k_loss}/h` : 'THERMAL MODEL',
      badgeColor: '#a78bfa',
      axis: axis7d, yLeftLabel: `${unit}/h`, yLeftMin: Math.max(0, rMin), yLeftMax: Math.max(0.5, rMax),
      yRightLabel: unit, yRightMin: Math.max(0, iMin), yRightMax: Math.max(0.2, iMax),
      series: [
        { name: this._t('tel_heat_rate'), data: hrS, axis: 'left', color: '#f87171', width: 2.1, unit: `${unit}/h` },
        { name: this._t('tel_cool_rate'), data: crS, axis: 'left', color: '#38bdf8', width: 2.1, unit: `${unit}/h` },
        { name: this._t('tel_inertia'), data: inS, axis: 'right', color: '#fbbf24', width: 1.9, unit },
      ],
      emptyText: this._t('tel_waiting_history'),
    };

    // Panel 3: PID Breakdown OR Hysteresis Error
    let panel3;
    if (isHyst) {
      const errS = this._sampleSeries(clHist, clState, startMs, endMs, N, (ev) => {
        const pv = parseFloat(ev.attrs.current_temperature);
        const sp = parseFloat(ev.attrs.temperature);
        return (!isNaN(pv) && !isNaN(sp)) ? (sp - pv) : null;
      });
      panel3 = {
        title: `${this._t('tel_hyst_chart')} (${this._timeframe})`,
        badge: 'HYSTERESIS (±0.3°)',
        badgeColor: '#fbbf24',
        banner: this._t('tel_hyst_banner'),
        axis, yLeftLabel: `ΔT ${unit}`, yLeftMin: -1.0, yLeftMax: 1.0,
        yRightLabel: '%', yRightMin: 0, yRightMax: 105,
        hBand: { minVal: -0.3, maxVal: 0.3, color: 'rgba(251, 191, 36, 0.10)' },
        refLines: [{ y: 0, axis: 'left', color: '#64748b', dash: '3,3', label: '0' }],
        series: [
          { name: 'Error (ΔT)', data: errS, axis: 'left', color: '#f87171', width: 2.1, unit },
          { name: 'Demand %', data: demS, axis: 'right', color: '#38bdf8', step: true, fill: 'rgba(56,189,248,0.16)', width: 1.7, unit: '%' },
        ],
        emptyText: this._t('tel_waiting_history'),
      };
    } else {
      const pS = this._sampleSeries(demHist, demState, startMs, endMs, N, (ev) => parseFloat(ev.attrs.p_term));
      const iS = this._sampleSeries(demHist, demState, startMs, endMs, N, (ev) => parseFloat(ev.attrs.i_term));
      const dS = this._sampleSeries(demHist, demState, startMs, endMs, N, (ev) => parseFloat(ev.attrs.d_term));
      const ffS = this._sampleSeries(demHist, demState, startMs, endMs, N, (ev) => parseFloat(ev.attrs.weather_ff));
      const [pMin, pMax] = this._computeBounds([pS, iS, dS, demS], 5, -30, 105);

      const pidSeries = [
        { name: 'P (p_term)', data: pS, axis: 'left', color: '#38bdf8', width: 2.0, unit: '%' },
        { name: 'I (i_term)', data: iS, axis: 'left', color: '#f87171', width: 2.0, unit: '%' },
        { name: 'D (d_term)', data: dS, axis: 'left', color: '#fbbf24', width: 1.8, unit: '%' },
      ];
      if (ffS.some((v) => v !== null && Math.abs(v) > 0.01)) {
        pidSeries.push({ name: 'Weather FF', data: ffS, axis: 'left', color: '#a78bfa', dash: '3,3', width: 1.5, unit: '%' });
      }
      pidSeries.push({ name: 'Demand', data: demS, axis: 'left', color: '#34d399', width: 2.2, unit: '%' });

      panel3 = {
        title: `${this._t('tel_pid_chart')} (${this._timeframe})`,
        badge: isCool ? 'TRACK COOL (SIMC)' : 'SMART PID (SIMC)',
        badgeColor: isCool ? '#22d3ee' : '#34d399',
        axis, yLeftLabel: '%', yLeftMin: Math.min(-15, pMin), yLeftMax: Math.max(100, pMax),
        refLines: [{ y: 0, axis: 'left', color: '#64748b', dash: '3,3', label: '0%' }],
        series: pidSeries,
        emptyText: this._t('tel_waiting_history'),
      };
    }

    const kpV = demAttrs.kp !== undefined ? demAttrs.kp : (autoAttrs.Kp !== undefined ? autoAttrs.Kp : clAttrs.pid_kp);
    const kiV = demAttrs.ki !== undefined ? demAttrs.ki : (autoAttrs.Ki !== undefined ? autoAttrs.Ki : clAttrs.pid_ki);
    const kdV = demAttrs.kd !== undefined ? demAttrs.kd : (autoAttrs.Kd !== undefined ? autoAttrs.Kd : clAttrs.pid_kd);
    const errV = demAttrs.error;
    const guardrail = autoAttrs.weekly_guardrail_status || 'idle';
    const eCls = zone.energyClass && states[zone.energyClass] ? states[zone.energyClass].state : '--';
    const retH = zone.retention && states[zone.retention] ? states[zone.retention].state : '--';

    const kpis = [
      { icon: '🌡️', label: 'Error (ΔT)', val: typeof errV === 'number' ? `${errV >= 0 ? '+' : ''}${errV.toFixed(2)} ${unit}` : '--', color: '#38bdf8' },
      { icon: '⚙️', label: 'PID (Kp / Ki / Kd)', val: (kpV !== undefined) ? `${Number(kpV).toFixed(1)} / ${Number(kiV || 0).toFixed(4)} / ${Number(kdV || 0).toFixed(1)}` : '--', color: '#e2e8f5' },
      { icon: '🛡️', label: 'Weekly Guardrail', val: guardrail, color: guardrail === 'reverted' ? '#f87171' : '#34d399' },
      { icon: '📉', label: 'Cooling / k_loss', val: `${this._numFromState(zone.coolingRate ? states[zone.coolingRate] : null) ?? '--'} ${unit}/h (${demAttrs.k_loss || 0}/h)`, color: '#38bdf8' },
      { icon: '🏆', label: `${this._t('tel_energy_ret')}`, val: `${eCls} • ${retH} ${this._t('hours')}`, color: '#34d399' },
    ];

    let bars = null;
    if (isHyst) {
      const done = clAttrs.autotune_cycles !== undefined ? clAttrs.autotune_cycles : 0;
      const tot = clAttrs.autotune_required_cycles !== undefined ? clAttrs.autotune_required_cycles : 3;
      bars = { type: 'learning', title: this._t('pid_learning_status'), done, total: tot };
    } else {
      bars = {
        type: 'pid_balance',
        title: this._t('tel_pid_balance'),
        items: [
          { lbl: 'P', val: Number(demAttrs.p_term || 0), color: '#38bdf8' },
          { lbl: 'I', val: Number(demAttrs.i_term || 0), color: '#f87171' },
          { lbl: 'D', val: Number(demAttrs.d_term || 0), color: '#fbbf24' },
          { lbl: 'FF', val: Number(demAttrs.weather_ff || 0), color: '#a78bfa' },
        ],
      };
    }

    return {
      mode: 'zone',
      panels: [panel1, panel2, panel3],
      kpis,
      bars,
    };
  }

  _buildSupportSnapshot(plant, zones) {
    const states = (this._hass && this._hass.states) ? this._hass.states : {};
    const mdSt = plant.masterDemand ? states[plant.masterDemand] : null;
    const phSt = plant.plantHealth ? states[plant.plantHealth] : null;
    const cycSt = plant.cycles ? states[plant.cycles] : null;
    const runSt = plant.runtime ? states[plant.runtime] : null;
    const mdAttrs = (mdSt && mdSt.attributes) || {};
    const phAttrs = (phSt && phSt.attributes) || {};
    const lines = [
      '=== Multizone Thermostat Telemetry Snapshot ===',
      `Timestamp: ${new Date().toISOString()}`,
      `Timeframe: ${this._timeframe}`,
      '',
      '[Plant]',
      `boiler_type: ${mdAttrs.boiler_type || (phAttrs.opentherm && phAttrs.opentherm.enabled ? 'opentherm' : 'relay')}`,
      `master_on: ${mdAttrs.master_on ?? '--'} | mode: ${mdAttrs.master_hvac_mode || '--'}`,
      `master_demand: ${mdSt ? mdSt.state : '--'}% | peak_zone: ${mdAttrs.peak_zone || '--'}`,
      `boiler_status: ${mdAttrs.boiler_status || (phSt ? phSt.state : '--')}`,
      `cycles_per_hour: ${cycSt ? cycSt.state : '--'} | runtime_24h: ${runSt ? runSt.state : '--'}h`,
      `anomalies: ${Array.isArray(phAttrs.anomalies) && phAttrs.anomalies.length ? phAttrs.anomalies.map((a) => `${a.zone}:${a.type || a.description}`).join('; ') : 'none'}`,
    ];
    if (mdAttrs.flow_temp !== undefined || (phAttrs.opentherm && phAttrs.opentherm.enabled)) {
      const f = mdAttrs.flow_temp ?? phAttrs.opentherm?.flow_temperature;
      const r = mdAttrs.return_temp ?? phAttrs.opentherm?.return_temperature;
      const m = mdAttrs.modulation_level ?? phAttrs.opentherm?.modulation_level;
      lines.push(`opentherm: flow=${f} return=${r} mod=${m}% dhw=${mdAttrs.dhw_active ?? phAttrs.opentherm?.dhw_active}`);
    }

    const activeZones = this._target === 'plant' ? zones : zones.filter((z) => z.climate === this._target);
    activeZones.forEach((z) => {
      const cl = states[z.climate];
      const dm = z.demand ? states[z.demand] : null;
      const at = z.autotune ? states[z.autotune] : null;
      const ca = (cl && cl.attributes) || {};
      const da = (dm && dm.attributes) || {};
      const aa = (at && at.attributes) || {};
      const hr = z.heatingRate && states[z.heatingRate] ? states[z.heatingRate].state : '--';
      const cr = z.coolingRate && states[z.coolingRate] ? states[z.coolingRate].state : '--';
      const inr = z.inertia && states[z.inertia] ? states[z.inertia].state : '--';
      const ec = z.energyClass && states[z.energyClass] ? states[z.energyClass].state : '--';
      lines.push('');
      lines.push(`[Zone: ${z.title}]`);
      lines.push(`control_mode=${da.control_mode || '--'} track=${da.active_track || '--'} actuator=${da.actuator_type || '--'}`);
      lines.push(`temp=${ca.current_temperature ?? '--'} target=${ca.temperature ?? '--'} step=${ca.target_temp_step ?? '--'} demand=${dm ? dm.state : '--'}% window_open=${da.window_open ?? false}`);
      lines.push(`gains: Kp=${da.kp ?? aa.Kp ?? '--'} Ki=${da.ki ?? aa.Ki ?? '--'} Kd=${da.kd ?? aa.Kd ?? '--'} guardrail=${aa.weekly_guardrail_status || 'idle'}`);
      lines.push(`terms: P=${da.p_term ?? '--'}% I=${da.i_term ?? '--'}% D=${da.d_term ?? '--'}% FF=${da.weather_ff ?? '--'}% err=${da.error ?? '--'} smart_stop=${da.smart_stop_offset ?? '--'}`);
      lines.push(`thermal: heat=${hr} cool=${cr} inertia=${inr} k_loss=${da.k_loss ?? 0} class=${ec}`);
    });
    return lines.join('\n');
  }

  async _copySnapshot(plant, zones) {
    const text = this._buildSupportSnapshot(plant, zones);
    let copied = false;
    try {
      if (navigator.clipboard && typeof navigator.clipboard.writeText === 'function') {
        await navigator.clipboard.writeText(text);
        copied = true;
      }
    } catch (e) {}
    if (!copied) {
      try {
        const ta = document.createElement('textarea');
        ta.value = text;
        ta.style.position = 'fixed';
        ta.style.opacity = '0';
        document.body.appendChild(ta);
        ta.select();
        document.execCommand('copy');
        ta.remove();
        copied = true;
      } catch (e) {}
    }
    this._copiedNotice = true;
    this.render();
    setTimeout(() => {
      this._copiedNotice = false;
      this.render();
    }, 2400);
  }

  render() {
    if (!this._hass) return;
    this._renderedOnce = true;

    const { plant, zones } = this._discoverPlantAndZones();
    const hours = this._timeframe === '6h' ? 6 : (this._timeframe === '48h' ? 48 : (this._timeframe === '7d' ? 168 : 24));
    const cacheKey = `${this._target}|${hours}`;
    const histData = (this._historyCache[cacheKey] && this._historyCache[cacheKey].data) || {};

    let data;
    if (this._target === 'plant') {
      data = this._buildPlantDashboard(plant, zones, histData, hours);
    } else {
      const zObj = zones.find((z) => z.climate === this._target) || zones[0];
      if (zObj) {
        data = this._buildZoneDashboard(zObj, histData, hours);
      } else {
        data = this._buildPlantDashboard(plant, zones, histData, hours);
      }
    }

    this._chartConfigs = {
      c1: data.panels[0],
      c2: data.panels[1],
      c3: data.panels[2],
    };

    const isClassic = (typeof getActiveMzCardStyle === 'function' ? getActiveMzCardStyle() : 'luxury') === 'classic';
    const cardBg = isClassic
      ? 'background: var(--ha-card-background, #1c1d21); border: 1px solid var(--divider-color, rgba(255,255,255,0.12)); box-shadow: none;'
      : 'background: var(--ha-card-background, rgba(16, 23, 38, 0.85)); backdrop-filter: blur(14px); -webkit-backdrop-filter: blur(14px); border: 1px solid rgba(56, 189, 248, 0.22); box-shadow: 0 12px 32px -8px rgba(0, 0, 0, 0.55);';

    let barsHtml = '';
    if (data.bars) {
      if (data.bars.type === 'pid_balance') {
        barsHtml = `
          <div class="bars-box">
            <div class="bars-title">${escapeHtml(data.bars.title)}</div>
            ${data.bars.items.map((it) => {
              const pct = Math.min(100, Math.abs(it.val) * 1.4);
              return `
                <div class="bar-row">
                  <span class="bar-lbl">${escapeHtml(it.lbl)}</span>
                  <div class="bar-track"><div class="bar-fill" style="width:${pct.toFixed(0)}%;background:${it.color};"></div></div>
                  <span class="bar-val" style="color:${it.color};">${it.val >= 0 ? '+' : ''}${it.val.toFixed(1)}%</span>
                </div>
              `;
            }).join('')}
          </div>
        `;
      } else if (data.bars.type === 'learning') {
        const pct = Math.min(100, Math.round((data.bars.done / Math.max(1, data.bars.total)) * 100));
        barsHtml = `
          <div class="bars-box">
            <div class="bars-title">${escapeHtml(data.bars.title)} (${data.bars.done}/${data.bars.total})</div>
            <div class="bar-track" style="height:10px;margin:6px 0;"><div class="bar-fill" style="width:${pct}%;background:#fbbf24;"></div></div>
          </div>
        `;
      }
    }

    const kpiTitle = data.mode === 'plant' ? this._t('tel_kpi_plant_title') : this._t('tel_kpi_zone_title');
    const showBack = !(this._config && this._config.is_modal);

    this.shadowRoot.innerHTML = `
      <style>
        :host { display: block; width: 100%; }
        ha-card {
          display: block; ${cardBg}
          border-radius: var(--card-border-radius, 20px); padding: 18px 20px;
          color: var(--primary-text-color, #e2e8f0); font-family: inherit; box-sizing: border-box;
        }
        .tel-top-nav {
          display: flex; align-items: center; justify-content: space-between;
          flex-wrap: wrap; gap: 10px; margin-bottom: 14px;
        }
        .nav-action-btn {
          background: rgba(255, 255, 255, 0.06);
          border: 1px solid rgba(148, 163, 184, 0.28);
          color: var(--primary-text-color, #e2e8f0);
          padding: 6px 13px; border-radius: 999px;
          font-size: 12.5px; font-weight: 700; cursor: pointer;
          display: inline-flex; align-items: center; gap: 6px;
          transition: all 0.16s ease;
        }
        .nav-action-btn:hover { border-color: #38bdf8; background: rgba(56, 189, 248, 0.16); }
        .copy-btn.copied { border-color: #34d399; color: #34d399; background: rgba(16, 185, 129, 0.18); }
        .tel-header {
          display: flex; align-items: center; justify-content: space-between;
          flex-wrap: wrap; gap: 12px; margin-bottom: 12px;
        }
        .tel-title-wrap { display: flex; align-items: center; gap: 12px; }
        .tel-icon {
          width: 44px; height: 44px; border-radius: 13px;
          background: rgba(56, 189, 248, 0.16); color: #38bdf8;
          display: flex; align-items: center; justify-content: center;
        }
        .tel-title { font-size: 19px; font-weight: 800; }
        .tel-sub { font-size: 12px; color: var(--secondary-text-color, #94a3b8); margin-top: 2px; }
        .tf-bar { display: flex; gap: 5px; background: rgba(0,0,0,0.22); padding: 4px; border-radius: 999px; border: 1px solid rgba(255,255,255,0.06); }
        .tf-btn {
          background: transparent; border: none; color: #94a3b8;
          padding: 4px 10px; border-radius: 999px; font-size: 12px; font-weight: 700; cursor: pointer;
        }
        .tf-btn.active { background: #0284c7; color: #ffffff; }
        .pill-bar { display: flex; flex-wrap: wrap; gap: 7px; align-items: center; margin-bottom: 14px; }
        .pill-btn {
          background: rgba(255, 255, 255, 0.04);
          border: 1px solid rgba(148, 163, 184, 0.22);
          color: #cbd5e1; border-radius: 999px;
          padding: 6px 13px; font-size: 12.5px; font-weight: 700;
          cursor: pointer; transition: all 0.16s ease;
        }
        .pill-btn:hover { border-color: #38bdf8; color: #ffffff; }
        .pill-btn.active {
          background: rgba(14, 165, 233, 0.24);
          border-color: #38bdf8; color: #ffffff;
        }
        .grid-2x2 {
          display: grid; grid-template-columns: repeat(2, minmax(0, 1fr));
          gap: 14px; align-items: stretch;
        }
        @media (max-width: 980px) { .grid-2x2 { grid-template-columns: 1fr; } }
        .chart-card {
          background: rgba(255, 255, 255, 0.025);
          border: 1px solid rgba(255, 255, 255, 0.07);
          border-radius: 14px; padding: 12px 14px;
          display: flex; flex-direction: column; height: 100%; box-sizing: border-box;
        }
        .chart-head {
          display: flex; align-items: center; justify-content: space-between;
          flex-wrap: wrap; gap: 6px; margin-bottom: 6px;
        }
        .chart-title { font-size: 13.5px; font-weight: 800; }
        .chart-badge {
          font-size: 10px; font-weight: 800; padding: 2px 8px;
          border-radius: 6px; border: 1px solid; letter-spacing: 0.3px;
        }
        .chart-banner {
          font-size: 11.5px; font-weight: 600; color: #cbd5e1;
          background: rgba(148,163,184,0.12); border: 1px solid rgba(148,163,184,0.22);
          border-radius: 8px; padding: 5px 9px; margin-bottom: 6px;
        }
        .chart-empty { padding: 48px 16px; text-align: center; color: #94a3b8; font-size: 13px; }
        .chart-svg-wrap { position: relative; width: 100%; }
        .chart-svg { width: 100%; height: auto; display: block; cursor: crosshair; }
        .chart-tooltip {
          position: absolute; top: 8px; pointer-events: none;
          background: rgba(15, 23, 42, 0.94); border: 1px solid rgba(56, 189, 248, 0.45);
          border-radius: 10px; padding: 7px 10px; font-size: 11px; color: #f8fafc;
          box-shadow: 0 8px 24px rgba(0,0,0,0.45); z-index: 20; white-space: nowrap;
        }
        .chart-legend {
          display: flex; flex-wrap: wrap; gap: 10px; margin-top: 6px;
          padding-top: 6px; border-top: 1px solid rgba(255,255,255,0.05);
          font-size: 11px; color: #cbd5e1;
        }
        .chart-leg-item { display: inline-flex; align-items: center; gap: 5px; }
        .chart-leg-dot { width: 9px; height: 9px; border-radius: 50%; display: inline-block; }
        .kpi-panel {
          background: rgba(255, 255, 255, 0.025);
          border: 1px solid rgba(255, 255, 255, 0.07);
          border-radius: 14px; padding: 14px 16px;
          display: flex; flex-direction: column; justify-content: space-between;
        }
        .kpi-panel-title { font-size: 14px; font-weight: 800; margin-bottom: 10px; }
        .kpi-list { display: flex; flex-direction: column; gap: 7px; }
        .kpi-row {
          display: flex; justify-content: space-between; align-items: center;
          gap: 8px; font-size: 12.5px; padding-bottom: 6px;
          border-bottom: 1px solid rgba(255, 255, 255, 0.05);
        }
        .kpi-row:last-child { border-bottom: none; padding-bottom: 0; }
        .kpi-k { color: var(--secondary-text-color, #94a3b8); font-weight: 600; }
        .kpi-v { font-weight: 800; text-align: right; font-variant-numeric: tabular-nums; }
        .bars-box { margin-top: 12px; padding-top: 10px; border-top: 1px solid rgba(255, 255, 255, 0.08); }
        .bars-title { font-size: 12px; font-weight: 800; color: #cbd5e1; margin-bottom: 7px; }
        .bar-row { display: grid; grid-template-columns: 28px 1fr 56px; align-items: center; gap: 8px; margin-bottom: 5px; font-size: 11.5px; }
        .bar-lbl { font-weight: 800; color: #94a3b8; }
        .bar-track { height: 7px; border-radius: 999px; background: rgba(255,255,255,0.07); overflow: hidden; }
        .bar-fill { height: 100%; border-radius: 999px; }
        .bar-val { text-align: right; font-weight: 800; font-variant-numeric: tabular-nums; }
      </style>
      <ha-card>
        <div class="tel-top-nav">
          <div>
            ${showBack ? `<button type="button" class="nav-action-btn" id="tel-back-btn">← ${escapeHtml(this._t('tel_back_diag'))}</button>` : ''}
          </div>
          <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap;">
            <button type="button" class="nav-action-btn copy-btn ${this._copiedNotice ? 'copied' : ''}" id="copy_snapshot_btn">
              ${this._copiedNotice ? `✓ ${escapeHtml(this._t('tel_copied'))}` : `📋 ${escapeHtml(this._t('tel_copy_snapshot'))}`}
            </button>
          </div>
        </div>

        <div class="tel-header">
          <div class="tel-title-wrap">
            <div class="tel-icon"><ha-icon icon="mdi:chart-areaspline"></ha-icon></div>
            <div>
              <div class="tel-title">${escapeHtml(this._t('tel_title'))}</div>
              <div class="tel-sub">${escapeHtml(this._t('tel_sub'))}</div>
            </div>
          </div>
          <div class="tf-bar">
            ${['6h', '24h', '48h', '7d'].map((tf) => `
              <button type="button" class="tf-btn ${this._timeframe === tf ? 'active' : ''}" data-tf="${tf}">${escapeHtml(tf)}</button>
            `).join('')}
          </div>
        </div>

        <div class="pill-bar">
          <button type="button" class="pill-btn ${this._target === 'plant' ? 'active' : ''}" data-target="plant">🏭 ${escapeHtml(this._t('central_plant'))}</button>
          ${zones.map((z) => `
            <button type="button" class="pill-btn ${this._target === z.climate ? 'active' : ''}" data-target="${escapeHtml(z.climate)}">${escapeHtml(z.title)}</button>
          `).join('')}
        </div>

        <div class="grid-2x2">
          <div>${mzBuildSvgChart(data.panels[0], 'c1')}</div>
          <div>${mzBuildSvgChart(data.panels[1], 'c2')}</div>
          <div>${mzBuildSvgChart(data.panels[2], 'c3')}</div>
          <div class="kpi-panel">
            <div>
              <div class="kpi-panel-title">${escapeHtml(kpiTitle)}</div>
              <div class="kpi-list">
                ${data.kpis.map((k) => `
                  <div class="kpi-row">
                    <span class="kpi-k">${k.icon} ${escapeHtml(k.label)}</span>
                    <span class="kpi-v" style="color:${k.color};">${escapeHtml(k.val)}</span>
                  </div>
                `).join('')}
              </div>
            </div>
            ${barsHtml}
          </div>
        </div>
      </ha-card>
    `;

    const backBtn = this.shadowRoot.getElementById('tel-back-btn');
    if (backBtn) {
      backBtn.addEventListener('click', () => {
        navigateOrFallbackModal(this, 'diagnostica', () => openMzStandaloneModal('diagnostics', this._hass));
      });
    }
    const copyBtn = this.shadowRoot.getElementById('copy_snapshot_btn');
    if (copyBtn) {
      copyBtn.addEventListener('click', () => this._copySnapshot(plant, zones));
    }
    this.shadowRoot.querySelectorAll('[data-target]').forEach((btn) => {
      btn.addEventListener('click', () => {
        this._target = btn.dataset.target;
        this._consumedTarget = this._target;
        try { sessionStorage.setItem('mz_telemetry_target', this._target); } catch (e) {}
        this.render();
        this._ensureHistoryLoaded();
      });
    });
    this.shadowRoot.querySelectorAll('[data-tf]').forEach((btn) => {
      btn.addEventListener('click', () => {
        this._timeframe = btn.dataset.tf;
        this.render();
        this._ensureHistoryLoaded();
      });
    });
    mzBindChartTooltips(this.shadowRoot, this._chartConfigs);
  }
}

if (!customElements.get('multizone-thermostat-telemetry-card')) {
  customElements.define('multizone-thermostat-telemetry-card', MultizoneThermostatTelemetryCard);
}
