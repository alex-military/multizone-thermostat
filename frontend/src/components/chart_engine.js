/* ==================== NATIVE SVG CHART ENGINE (ZERO DEPENDENCIES) ==================== */

function mzBuildSvgChart(cfg, containerId) {
  const W = 680;
  const H = 224;
  const ML = 46;
  const MR = cfg.yRightLabel ? 46 : 18;
  const MT = 18;
  const MB = 30;
  const PW = W - ML - MR;
  const PH = H - MT - MB;
  const axis = Array.isArray(cfg.axis) ? cfg.axis : [];
  const len = axis.length;

  if (len < 2 || !Array.isArray(cfg.series) || cfg.series.length === 0) {
    return `
      <div class="chart-card">
        <div class="chart-head">
          <div class="chart-title">${escapeHtml(cfg.title || '')}</div>
          ${cfg.badge ? `<span class="chart-badge" style="color:${cfg.badgeColor || '#38bdf8'}; border-color:${cfg.badgeColor || '#38bdf8'}44; background:${cfg.badgeColor || '#38bdf8'}18;">${escapeHtml(cfg.badge)}</span>` : ''}
        </div>
        <div class="chart-empty">${escapeHtml(cfg.emptyText || 'Waiting for Recorder data...')}</div>
      </div>
    `;
  }

  let yLeftMin = typeof cfg.yLeftMin === 'number' ? cfg.yLeftMin : 0;
  let yLeftMax = typeof cfg.yLeftMax === 'number' ? cfg.yLeftMax : 100;
  if (Math.abs(yLeftMax - yLeftMin) < 0.01) {
    yLeftMin -= 1;
    yLeftMax += 1;
  }

  let yRightMin = typeof cfg.yRightMin === 'number' ? cfg.yRightMin : 0;
  let yRightMax = typeof cfg.yRightMax === 'number' ? cfg.yRightMax : 100;
  if (Math.abs(yRightMax - yRightMin) < 0.01) {
    yRightMin -= 1;
    yRightMax += 1;
  }

  const xPos = (i) => ML + (i / Math.max(1, len - 1)) * PW;
  const yLeft = (v) => MT + PH - ((v - yLeftMin) / Math.max(0.001, yLeftMax - yLeftMin)) * PH;
  const yRight = (v) => MT + PH - ((v - yRightMin) / Math.max(0.001, yRightMax - yRightMin)) * PH;

  let gridSvg = '';
  for (let g = 0; g <= 4; g++) {
    const frac = g / 4;
    const y = MT + PH - frac * PH;
    const valL = yLeftMin + frac * (yLeftMax - yLeftMin);
    const lblL = Math.abs(valL) >= 10 || Number.isInteger(valL) ? Math.round(valL * 10) / 10 : valL.toFixed(1);
    gridSvg += `<line x1="${ML}" y1="${y.toFixed(1)}" x2="${W - MR}" y2="${y.toFixed(1)}" stroke="rgba(148,163,184,0.13)" stroke-dasharray="3,3" />`;
    gridSvg += `<text x="${ML - 6}" y="${(y + 3.5).toFixed(1)}" text-anchor="end" fill="#94a3b8" font-size="10" font-weight="600">${lblL}</text>`;
    if (cfg.yRightLabel) {
      const valR = yRightMin + frac * (yRightMax - yRightMin);
      const lblR = Math.abs(valR) >= 10 || Number.isInteger(valR) ? Math.round(valR * 10) / 10 : valR.toFixed(1);
      gridSvg += `<text x="${W - MR + 6}" y="${(y + 3.5).toFixed(1)}" text-anchor="start" fill="#94a3b8" font-size="10" font-weight="600">${lblR}</text>`;
    }
  }
  if (cfg.yLeftLabel) {
    gridSvg += `<text x="8" y="${MT + 8}" fill="#64748b" font-size="9.5" font-weight="700">${escapeHtml(cfg.yLeftLabel)}</text>`;
  }
  if (cfg.yRightLabel) {
    gridSvg += `<text x="${W - 8}" y="${MT + 8}" text-anchor="end" fill="#64748b" font-size="9.5" font-weight="700">${escapeHtml(cfg.yRightLabel)}</text>`;
  }

  let xAxisSvg = '';
  for (let t = 0; t <= 4; t++) {
    const idx = Math.round((t / 4) * (len - 1));
    xAxisSvg += `<text x="${xPos(idx).toFixed(1)}" y="${H - 8}" text-anchor="middle" fill="#94a3b8" font-size="10" font-weight="600">${escapeHtml(axis[idx].label || '')}</text>`;
  }

  let bandsSvg = '';
  if (Array.isArray(cfg.bands)) {
    cfg.bands.forEach((b) => {
      const x1 = xPos(b.start);
      const x2 = xPos(b.end);
      const bw = Math.max(4, x2 - x1);
      bandsSvg += `<rect x="${x1.toFixed(1)}" y="${MT}" width="${bw.toFixed(1)}" height="${PH}" fill="${b.color}" rx="2" />`;
      if (b.label && bw > 34) {
        bandsSvg += `<text x="${(x1 + bw / 2).toFixed(1)}" y="${MT + 12}" text-anchor="middle" fill="#e2e8f0" font-size="9" font-weight="700" opacity="0.85">${escapeHtml(b.label)}</text>`;
      }
    });
  }

  let hBandSvg = '';
  if (cfg.hBand && typeof cfg.hBand.minVal === 'number' && typeof cfg.hBand.maxVal === 'number') {
    const yTop = Math.max(MT, Math.min(MT + PH, yLeft(cfg.hBand.maxVal)));
    const yBot = Math.max(MT, Math.min(MT + PH, yLeft(cfg.hBand.minVal)));
    hBandSvg += `<rect x="${ML}" y="${yTop.toFixed(1)}" width="${PW}" height="${Math.max(2, yBot - yTop).toFixed(1)}" fill="${cfg.hBand.color}" />`;
  }

  let refSvg = '';
  if (Array.isArray(cfg.refLines)) {
    cfg.refLines.forEach((r) => {
      const y = r.axis === 'right' ? yRight(r.y) : yLeft(r.y);
      if (y >= MT && y <= MT + PH) {
        refSvg += `<line x1="${ML}" y1="${y.toFixed(1)}" x2="${W - MR}" y2="${y.toFixed(1)}" stroke="${r.color}" stroke-width="1.2" stroke-dasharray="${r.dash || '4,4'}" opacity="0.85" />`;
        if (r.label) {
          refSvg += `<text x="${W - MR - 4}" y="${(y - 4).toFixed(1)}" text-anchor="end" fill="${r.color}" font-size="9.5" font-weight="700">${escapeHtml(r.label)}</text>`;
        }
      }
    });
  }

  let pathsSvg = '';
  const legendItems = [];
  cfg.series.forEach((s) => {
    const yFn = s.axis === 'right' ? yRight : yLeft;
    let d = '';
    let lastValidIdx = -1;
    let firstValidIdx = -1;
    let lastVal = null;

    s.data.forEach((val, idx) => {
      if (val === null || val === undefined || isNaN(val)) return;
      const x = xPos(idx);
      const y = Math.max(MT, Math.min(MT + PH, yFn(val)));
      if (firstValidIdx === -1) {
        d = `M ${x.toFixed(1)} ${y.toFixed(1)}`;
        firstValidIdx = idx;
      } else if (s.step && lastVal !== null) {
        const prevY = Math.max(MT, Math.min(MT + PH, yFn(lastVal)));
        d += ` L ${x.toFixed(1)} ${prevY.toFixed(1)} L ${x.toFixed(1)} ${y.toFixed(1)}`;
      } else {
        d += ` L ${x.toFixed(1)} ${y.toFixed(1)}`;
      }
      lastValidIdx = idx;
      lastVal = val;
    });

    if (d && s.fill && firstValidIdx !== -1 && lastValidIdx !== -1) {
      const baseVal = (s.axis === 'right' ? yRightMin : yLeftMin);
      const baseY = Math.max(MT, Math.min(MT + PH, yFn(Math.max(baseVal, 0))));
      pathsSvg += `<path d="${d} L ${xPos(lastValidIdx).toFixed(1)} ${baseY.toFixed(1)} L ${xPos(firstValidIdx).toFixed(1)} ${baseY.toFixed(1)} Z" fill="${s.fill}" stroke="none" />`;
    }
    if (d) {
      pathsSvg += `<path d="${d}" fill="none" stroke="${s.color}" stroke-width="${s.width || 2}" stroke-linejoin="round" stroke-linecap="round" ${s.dash ? `stroke-dasharray="${s.dash}"` : ''} />`;
    }
    const dispVal = lastVal !== null ? `${lastVal}${s.unit || ''}` : '--';
    legendItems.push(`
      <span class="chart-leg-item">
        <span class="chart-leg-dot" style="background:${s.color};"></span>
        <span>${escapeHtml(s.name)}: <b>${escapeHtml(dispVal)}</b></span>
      </span>
    `);
  });

  return `
    <div class="chart-card">
      <div class="chart-head">
        <div class="chart-title">${escapeHtml(cfg.title || '')}</div>
        ${cfg.badge ? `<span class="chart-badge" style="color:${cfg.badgeColor || '#38bdf8'}; border-color:${cfg.badgeColor || '#38bdf8'}44; background:${cfg.badgeColor || '#38bdf8'}18;">${escapeHtml(cfg.badge)}</span>` : ''}
      </div>
      ${cfg.banner ? `<div class="chart-banner">ℹ️ ${escapeHtml(cfg.banner)}</div>` : ''}
      <div class="chart-svg-wrap" data-chart-id="${escapeHtml(containerId)}">
        <svg viewBox="0 0 ${W} ${H}" class="chart-svg">
          ${bandsSvg}${hBandSvg}${gridSvg}${refSvg}${pathsSvg}${xAxisSvg}
          <line class="hover-line" x1="0" y1="${MT}" x2="0" y2="${MT + PH}" stroke="#cbd5e1" stroke-width="1" stroke-dasharray="3,3" style="display:none;" />
        </svg>
        <div class="chart-tooltip" style="display:none;"></div>
      </div>
      <div class="chart-legend">${legendItems.join('')}</div>
    </div>
  `;
}

function mzBindChartTooltips(shadowRoot, chartConfigs) {
  if (!shadowRoot || !chartConfigs) return;
  shadowRoot.querySelectorAll('.chart-svg-wrap').forEach((wrap) => {
    const cid = wrap.dataset.chartId;
    const cfg = chartConfigs[cid];
    if (!cfg || !Array.isArray(cfg.axis) || cfg.axis.length < 2) return;
    const svg = wrap.querySelector('.chart-svg');
    const hoverLine = wrap.querySelector('.hover-line');
    const tip = wrap.querySelector('.chart-tooltip');
    if (!svg || !hoverLine || !tip) return;

    const W = 680;
    const ML = 46;
    const MR = cfg.yRightLabel ? 46 : 18;
    const PW = W - ML - MR;

    const handleMove = (clientX) => {
      const rect = svg.getBoundingClientRect();
      if (!rect || rect.width <= 0) return;
      const svgX = ((clientX - rect.left) / rect.width) * W;
      const frac = Math.max(0, Math.min(1, (svgX - ML) / PW));
      const idx = Math.round(frac * (cfg.axis.length - 1));
      const xSnap = ML + (idx / Math.max(1, cfg.axis.length - 1)) * PW;

      hoverLine.setAttribute('x1', xSnap.toFixed(1));
      hoverLine.setAttribute('x2', xSnap.toFixed(1));
      hoverLine.style.display = '';

      const rows = cfg.series.map((s) => {
        const v = s.data[idx];
        const disp = (v !== null && v !== undefined && !isNaN(v)) ? `${v}${s.unit || ''}` : '--';
        return `
          <div style="display:flex;justify-content:space-between;gap:12px;">
            <span style="color:${s.color};font-weight:700;">● ${escapeHtml(s.name)}</span>
            <b>${escapeHtml(disp)}</b>
          </div>
        `;
      }).join('');
      tip.innerHTML = `<div style="font-weight:800;color:#94a3b8;margin-bottom:4px;">🕒 ${escapeHtml(cfg.axis[idx].label || '')}</div>${rows}`;
      tip.style.display = 'block';
      if (frac > 0.58) {
        tip.style.left = 'auto';
        tip.style.right = `${Math.max(12, ((W - xSnap) / W) * rect.width + 12)}px`;
      } else {
        tip.style.right = 'auto';
        tip.style.left = `${Math.max(12, (xSnap / W) * rect.width + 12)}px`;
      }
    };

    svg.addEventListener('mousemove', (e) => handleMove(e.clientX));
    svg.addEventListener('touchmove', (e) => {
      if (e.touches && e.touches[0]) handleMove(e.touches[0].clientX);
    }, { passive: true });
    svg.addEventListener('mouseleave', () => {
      hoverLine.style.display = 'none';
      tip.style.display = 'none';
    });
  });
}
