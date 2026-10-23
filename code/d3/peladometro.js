/* Offline, dependency-free panel. Load before atlas.js; mount after DATA is ready.
 * Pure QA API: peladometroData({data: DATA, threshold: 50, period: 'all'}).
 * Periods: 'all', 'active1966', 'before1983', 'from1983'; threshold is inclusive (>=).
 */
(function (root) {
  'use strict';

  const scores = [0, 25, 50, 75, 100];
  const descriptions = [
    'Sin pérdida visible', 'Entradas o menor densidad leves', 'Retroceso o menor densidad moderados',
    'Pérdida extensa o pelo muy ralo arriba', 'Parte superior sin cabello visible'
  ];
  const normalize = value => String(value || '').normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '').trim().replace(/\s+/g, ' ').toLowerCase();
  const qid = record => /^Q\d+$/i.test(String(record?.wikidata_id || '').trim())
    ? String(record.wikidata_id).trim().toUpperCase() : null;
  const validHair = hair => hair && typeof hair.score === 'number' && scores.includes(hair.score);

  function peladometroData({data = {}, threshold = 50, period = 'all'} = {}) {
    threshold = [25, 50, 75, 100].includes(Number(threshold)) ? Number(threshold) : 50;
    period = ['all', 'active1966', 'before1983', 'from1983'].includes(period) ? period : 'all';
    const people = Array.isArray(data?.profiles?.people) ? data.profiles.people : [];
    const ministers = Array.isArray(data?.ministers) ? data.ministers : [];
    const nameIds = new Map();
    for (const record of [...people, ...ministers]) {
      const name = normalize(record?.name), id = qid(record);
      if (!name || !id) continue;
      if (!nameIds.has(name)) nameIds.set(name, new Set());
      nameIds.get(name).add(id);
    }
    function identity(record) {
      if (!record) return null;
      const name = normalize(record.name), id = qid(record), matches = nameIds.get(name);
      if (id) return 'wikidata:' + id;
      if (!name) return null;
      // Resolve minister rows without IDs through an unambiguous profile name.
      return matches?.size === 1 ? 'wikidata:' + [...matches][0] : 'name:' + name;
    }
    const profileGroups = new Map();
    for (const person of people) {
      const id = identity(person);
      if (!id) continue;
      if (!profileGroups.has(id)) profileGroups.set(id, []);
      profileGroups.get(id).push(person);
    }
    const groups = new Map();
    for (const minister of ministers) {
      const id = identity(minister);
      if (!id) continue;
      if (!groups.has(id)) groups.set(id, {
        id, name: String(minister.name || profileGroups.get(id)?.[0]?.name || id),
        firstAppointment: null, hasRecentService: false
      });
      const person = groups.get(id);
      const start = typeof minister.start === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(minister.start)
        && Number.isFinite(Date.parse(minister.start)) ? minister.start : null;
      if (start && (!person.firstAppointment || start < person.firstAppointment)) person.firstAppointment = start;
      if (start && (start >= '1966-01-01' || (typeof minister.end === 'string' && minister.end > '1966-01-01'))) person.hasRecentService = true;
    }
    let unknownFirstAppointment = 0;
    const observations = [];
    for (const person of groups.values()) {
      if (!person.firstAppointment) unknownFirstAppointment++;
      if (period === 'active1966' && !person.hasRecentService) continue;
      if (['before1983', 'from1983'].includes(period) && (!person.firstAppointment ||
        (period === 'before1983' ? person.firstAppointment >= '1983-01-01' : person.firstAppointment < '1983-01-01'))) continue;
      const candidates = (profileGroups.get(person.id) || []).map(p => p.hair).filter(validHair);
      const conflict = new Set(candidates.map(hair => hair.score)).size > 1;
      // Conflicting duplicate ratings remain missing until editorial review.
      const hair = conflict ? null : candidates[0];
      observations.push({...person, score: hair?.score ?? null, conflict,
        hair: hair ? {score: hair.score, period: String(hair.period || ''),
          note: String(hair.note || ''), confidence: String(hair.confidence || ''),
          source_url: String(hair.source_url || ''), date_basis: String(hair.date_basis || ''),
          view_limitations: String(hair.view_limitations || '')} : null});
    }
    observations.sort((a, b) => a.name.localeCompare(b.name, 'es-AR') || a.id.localeCompare(b.id));
    const evaluated = observations.filter(person => person.score !== null);
    const numerator = evaluated.filter(person => person.score >= threshold).length;
    const denominator = evaluated.length;
    return {
      threshold, period, total: observations.length, numerator, denominator,
      proportion: denominator ? numerator / denominator : null,
      missing: observations.length - denominator,
      conflicts: observations.filter(person => person.conflict).length,
      unknownFirstAppointment,
      distribution: scores.map((score, i) => ({score, label: descriptions[i],
        count: evaluated.filter(person => person.score === score).length})),
      observations
    };
  }

  const styles = `
    #peladometro{min-width:0;color:var(--ink,#253c3b)}
    #peladometro .pm-panel{margin:12px 0 0;padding:24px;background:#fffcf5;border:1px solid var(--line,#d7d9ce);border-top:3px solid var(--gold,#a57526);border-radius:5px}
    #peladometro h2{font:normal 29px/1.2 Georgia,serif;margin:0 0 8px}
    #peladometro p{margin:8px 0}
    #peladometro .pm-kicker{font-size:11px;font-weight:700;letter-spacing:.12em;text-transform:uppercase;color:var(--muted,#596865);margin-bottom:8px}
    #peladometro .pm-copy{font-size:13px;color:var(--muted,#596865);max-width:85ch}
    #peladometro .pm-controls{display:flex;flex-wrap:wrap;gap:12px 20px;margin:20px 0 10px}
    #peladometro label{display:flex;flex-direction:column;gap:5px;font-size:13px;font-weight:650;min-width:0;max-width:100%}
    #peladometro select{font:inherit;color:inherit;background:#fffdf7;border:1px solid #a9b2a5;border-radius:4px;padding:9px 11px;min-height:44px;max-width:100%}
    #peladometro :is(select,summary,a):focus-visible{outline:3px solid #a57526;outline-offset:3px}
    #peladometro .pm-grid{display:grid;grid-template-columns:minmax(0,1.4fr) minmax(0,1fr);gap:24px;margin:20px 0}
    #peladometro .pm-gauge{display:block;width:100%;max-width:480px;height:auto;margin:12px auto 0;overflow:visible}
    #peladometro .pm-gauge text{font:16px system-ui,sans-serif;fill:var(--ink,#253c3b)}
    #peladometro .pm-gauge .pm-gauge-middle{font-weight:700}
    #peladometro .pm-counts{font-size:13px;line-height:1.9;color:var(--muted,#596865)}
    #peladometro .pm-counts span{display:inline-block;margin-right:14px}
    #peladometro .pm-counts strong{color:var(--ink,#253c3b)}
    #peladometro .pm-result{background:#e9ece2;padding:18px;border-radius:4px;align-self:start;min-width:0}
    #peladometro .pm-percent{font:normal clamp(32px,5vw,48px)/1.15 Georgia,serif;display:block;margin:12px 0}
    #peladometro details{border-top:1px solid var(--line,#d7d9ce);padding:14px 0 0}
    #peladometro summary{font-size:14px;cursor:pointer;min-height:44px;padding:9px 0}
    #peladometro .pm-evidence{list-style:none;padding:0;margin:0}
    #peladometro .pm-evidence li{padding:12px 0;border-top:1px solid var(--line,#d7d9ce);overflow-wrap:anywhere;font-size:13px}
    #peladometro a{color:#226778;text-underline-offset:3px}
    @media(max-width:650px){#peladometro .pm-panel{padding:16px}#peladometro .pm-grid{grid-template-columns:1fr;gap:16px}#peladometro .pm-controls label{width:100%}#peladometro select{width:100%}}
  `;

  function mountPeladometro() {
    const host = root.document?.getElementById('peladometro');
    if (!host) return null;
    // DATA is a top-level const in the standalone atlas, not a window property.
    const data = typeof DATA !== 'undefined' ? DATA : root.DATA;
    const document = host.ownerDocument;
    const previousThreshold = host.querySelector('[data-pm-threshold]')?.value || '50';
    const previousPeriod = host.querySelector('[data-pm-period]')?.value || 'all';
    host.replaceChildren();
    function element(tag, className, text) {
      const node = document.createElement(tag);
      if (className) node.className = className;
      if (text !== undefined) node.textContent = text;
      return node;
    }
    const style = element('style');
    style.textContent = styles;
    const panel = element('div', 'pm-panel');
    panel.setAttribute('role', 'region');
    panel.setAttribute('aria-labelledby', 'pm-title');
    
    const title = element('h2', '', 'Peladómetro');
    title.id = 'pm-title';
    panel.append(title, element('p', 'pm-copy',
      '¿Para qué lado se inclina el archivo? Explorá qué porcentaje de ministros evaluados alcanza el umbral elegido del índice visual.'));
    const controls = element('div', 'pm-controls');
    function selectControl(labelText, attribute, choices, selected) {
      const label = element('label', '', labelText);
      const select = element('select');
      select.setAttribute(attribute, '');
      select.setAttribute('aria-describedby', 'pm-scope');
      for (const [value, text] of choices) {
        const option = element('option', '', text);
        option.value = value;
        select.append(option);
      }
      select.value = selected;
      label.append(select);
      controls.append(label);
      return select;
    }
    const threshold = selectControl('Umbral del índice (inclusive)', 'data-pm-threshold',
      [25, 50, 75, 100].map(score => [String(score), `Al menos ${score}/100`]), previousThreshold);
    const period = selectControl('Grupo de ministros', 'data-pm-period', [
      ['all', 'Todo el período'], ['active1966', 'Con alguna gestión desde 1966'],
      ['before1983', 'Primera asunción antes de 1983'], ['from1983', 'Primera asunción desde 1983']
    ], previousPeriod);
    const scope = element('p', 'pm-copy',
      'Filtro propio, independiente de los filtros del atlas. «Desde 1966» incluye a quienes tuvieron algún servicio registrado desde el 01/01/1966. Los otros grupos usan la primera asunción (corte: 01/01/1983). Ninguno de estos filtros fecha la foto.');
    scope.id = 'pm-scope';
    panel.append(controls, scope);
    const grid = element('div', 'pm-grid');
    const chart = element('div');
    const heading = element('p');
    heading.append(element('strong', '', 'Porcentaje entre ministros evaluados · 0–100 %'));
    const gaugeHost = element('div');
    chart.append(heading, gaugeHost, element('p', 'pm-copy',
      'La aguja indica el porcentaje que alcanza el umbral, no el puntaje promedio de calvicie. Las zonas del arco solo orientan la lectura de la escala.'));
    const result = element('div', 'pm-result');
    const resultTitle = element('p', '', 'Proporción observada entre ministros evaluados');
    const live = element('div');
    live.setAttribute('role', 'status');
    live.setAttribute('aria-live', 'polite');
    live.setAttribute('aria-atomic', 'true');
    result.append(resultTitle, live);
    grid.append(chart, result);
    const caveat = element('p', 'pm-copy',
      'Muestra parcial, selección no representativa. Describe solo a los ministros evaluados; no permite estimar la probabilidad de llegar a ministro ni explicar sus designaciones.');
    const details = element('details');
    const summary = element('summary', '', 'Cómo se contó y qué se observó');
    const counts = element('p', 'pm-counts');
    counts.setAttribute('aria-label', 'Cantidad de personas por puntaje del índice visual');
    const evidence = element('ul', 'pm-evidence');
    details.append(summary, element('p', 'pm-copy',
      'Valoración subjetiva, no clínica: considera también menor densidad, afinamiento aparente y cuero cabelludo visible. No predice caída futura ni distingue calvicie de afeitado. Cada puntaje describe la imagen indicada, no todas las gestiones. La fecha de publicación puede diferir de la toma. Una foto sin fecha puede puntuarse si permite identificar a la persona y ver su pelo; la asociación con su gestión es solo contexto probable, no una fecha confirmada. Sin evaluar nunca equivale a cero. Identidades agrupadas por Wikidata y, si falta, por nombre; puntajes contradictorios quedan sin evaluar.'),
      element('p', 'pm-copy', scores.map((score, i) => `${score}: ${descriptions[i].toLowerCase()}`).join(' · ') + '.'), counts, evidence);
    panel.append(grid, caveat, details);
    host.append(style, panel);

    function drawGauge(stats, percent) {
      function svgElement(tag, attributes = {}, text) {
        const node = document.createElementNS('http://www.w3.org/2000/svg', tag);
        for (const [name, value] of Object.entries(attributes)) node.setAttribute(name, String(value));
        if (text !== undefined) node.textContent = text;
        return node;
      }
      const value = stats.proportion === null ? null : stats.proportion * 100;
      const svg = svgElement('svg', {class: 'pm-gauge', viewBox: '0 0 400 218',
        role: 'img', 'aria-labelledby': 'pm-gauge-title pm-gauge-description',
        'data-pm-gauge': '', 'data-value': value === null ? '' : value,
        'data-pm-state': value === null ? 'no-data' : 'available',
        'data-threshold': stats.threshold});
      svg.append(svgElement('title', {id: 'pm-gauge-title'},
        value === null ? 'Peladómetro: sin datos suficientes' : `Peladómetro: ${percent} entre ministros evaluados`),
      svgElement('desc', {id: 'pm-gauge-description'},
        `Escala semicircular: 0 % a la izquierda, 50 % arriba y 100 % a la derecha. ${stats.numerator} de ${stats.denominator} ministros evaluados alcanzan el índice ${stats.threshold}/100; ${stats.missing} sin evaluar.` +
        (value === null ? ' Sin aguja: no hay evaluaciones válidas.' : ' La aguja muestra una proporción observada, no el puntaje promedio.')));
      const drawing = svgElement('g', {'aria-hidden': 'true'});
      function point(percentValue, radius) {
        const angle = Math.PI * (1 - percentValue / 100);
        return [200 + radius * Math.cos(angle), 186 - radius * Math.sin(angle)];
      }
      const arc = (from, to, radius) => `M ${point(from, radius).join(' ')} A ${radius} ${radius} 0 0 1 ${point(to, radius).join(' ')}`;
      drawing.append(svgElement('path', {d: arc(0, 100, 142), fill: 'none',
        stroke: '#e8e3d7', 'stroke-width': 23}));
      const colors = ['#c4cdbf', '#bec7ae', '#cebf96', '#c7a87d', '#b98d75'];
      colors.forEach((color, index) => drawing.append(svgElement('path', {
        d: arc(index * 20 + 0.5, (index + 1) * 20 - 0.5, 142), fill: 'none',
        stroke: value === null ? '#d9d9ce' : color, 'stroke-width': 20
      })));
      for (let tick = 0; tick <= 100; tick += 5) {
        const major = tick % 25 === 0;
        const inner = point(tick, major ? 119 : 125), outer = point(tick, 130);
        drawing.append(svgElement('line', {x1: inner[0], y1: inner[1], x2: outer[0], y2: outer[1],
          stroke: major ? '#596865' : '#a5ada1', 'stroke-width': major ? 1.8 : 1}));
        if (major) {
          const position = point(tick, 174);
          drawing.append(svgElement('text', {x: position[0], y: position[1] + 5,
            'text-anchor': 'middle', class: tick === 50 ? 'pm-gauge-middle' : ''}, `${tick} %`));
        }
      }
      if (value !== null) {
        const needle = svgElement('g', {'data-pm-needle': '', 'data-value': value,
          transform: `rotate(${value * 1.8} 200 186)`});
        needle.append(svgElement('path', {d: 'M 82 186 L 200 181 L 211 186 L 200 191 Z',
          fill: '#253c3b', stroke: '#fffcf5', 'stroke-width': 1.2}));
        drawing.append(needle);
      } else {
        drawing.append(svgElement('text', {x: 200, y: 132, 'text-anchor': 'middle'}, 'Sin evaluaciones'));
      }
      drawing.append(svgElement('circle', {cx: 200, cy: 186, r: 9, fill: '#fffcf5',
        stroke: value === null ? '#a5ada1' : '#253c3b', 'stroke-width': 2}),
      svgElement('circle', {cx: 200, cy: 186, r: 3.5, fill: value === null ? '#a5ada1' : '#a57526'}));
      svg.append(drawing);
      gaugeHost.replaceChildren(svg);
    }

    function render() {
      const stats = peladometroData({data, threshold: threshold.value, period: period.value});
      counts.replaceChildren(element('strong', '', 'Personas por puntaje: '));
      for (const bin of stats.distribution) {
        counts.append(element('span', '', `${bin.score}/100: ${bin.count}`));
      }
      live.replaceChildren();
      const percent = stats.proportion === null ? 'Sin datos suficientes' :
        `${(stats.proportion * 100).toLocaleString('es-AR', {maximumFractionDigits: 1})} %`;
      drawGauge(stats, percent);
      live.append(element('strong', 'pm-percent', percent), element('p', '',
        `${stats.numerator} de ${stats.denominator} ministros evaluados con índice ≥ ${stats.threshold}/100.`));
      if (stats.proportion === null) {
        live.append(element('p', 'pm-copy', 'No hay observaciones válidas en este grupo para calcular una proporción.'));
      }
      live.append(element('p', 'pm-copy', `${stats.total} personas en el grupo · ${stats.missing} sin evaluar.`));
      if (stats.conflicts) live.append(element('p', 'pm-copy', `${stats.conflicts} sin evaluar por puntajes contradictorios entre fichas.`));
      if (stats.unknownFirstAppointment && stats.period !== 'all') live.append(element('p', 'pm-copy',
        `${stats.unknownFirstAppointment} personas excluidas del filtro temporal por falta de fecha de primera asunción.`));
      evidence.replaceChildren();
      const evaluated = stats.observations.filter(person => person.hair);
      if (!evaluated.length) evidence.append(element('li', '', 'No hay evaluaciones disponibles para este grupo.'));
      for (const person of evaluated) {
        const row = element('li');
        row.append(element('strong', '', `${person.name} · ${person.score}/100`),
          element('p', '', `Época o referencia de la imagen: ${person.hair.period || 'sin documentar'}.`),
          element('p', '', person.hair.note || 'Sin nota visual adicional.'),
          element('p', 'pm-copy', `Confianza de la valoración visual: ${person.hair.confidence || 'sin documentar'}.`));
        if (person.hair.date_basis) row.append(element('p', 'pm-copy', `Sobre la fecha: ${person.hair.date_basis}`));
        if (person.hair.view_limitations) row.append(element('p', 'pm-copy', `Límites de la imagen: ${person.hair.view_limitations}`));
        if (/^https?:\/\//i.test(person.hair.source_url)) {
          const link = element('a', '', 'Fuente de la imagen (requiere conexión)');
          link.href = person.hair.source_url;
          link.target = '_blank';
          link.rel = 'noopener noreferrer';
          row.append(link);
        }
        evidence.append(row);
      }
      return stats;
    }
    threshold.addEventListener('change', render);
    period.addEventListener('change', render);
    return render();
  }

  root.peladometroData = peladometroData;
  root.mountPeladometro = mountPeladometro;
})(window);
