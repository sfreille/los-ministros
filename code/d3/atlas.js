'use strict';
const $ = id => document.getElementById(id);
const fmt = (n, places=1) => n == null || !Number.isFinite(n) ? '—' : n.toLocaleString('es-AR', {maximumFractionDigits:places});
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const norm = s => s.normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase();
const dateLabel = s => s.split('-').reverse().join('/');
const dayDiff = (a,b) => (Date.parse(b)-Date.parse(a))/86400000;
const months = days => days*12/365.25;
const nameLabel = name => ({'Military Junta':'Junta Militar','Junta of Commanders of the Armed Forces':'Junta de Comandantes de las Fuerzas Armadas'}[name] || name);
const ministers = new Map(DATA.ministers.map(m => [m.id,m]));
const categories = DATA.classification.categories;
const categoryMap = new Map(categories.map(c=>[c.id,c]));
const periods = new Map(DATA.classification.periods.map(r=>[r.id,r]));
const color = key => categoryMap.get(key)?.color || '#89908d';
const pColor = p => p.regime_categories.length===1 ? color(p.regime_categories[0]) : '#89908d';
const label = key => categoryMap.get(key)?.label || key;
let selected = null, visible = [], regimeRows = [];
const tip=d3.select('body').append('div').attr('class','tooltip').attr('role','tooltip').style('display','none');
function showTip(event,text){
 const box=event.currentTarget.getBoundingClientRect();
 tip.text(text).style('display','block').style('left',Math.max(8,Math.min(innerWidth-310,event.clientX||box.left))+'px')
   .style('top',Math.max(8,Math.min(innerHeight-130,(event.clientY||box.top)+16))+'px');
}
function hideTip(){tip.style('display','none');}
function flagsText(f){
 const exact={'acting':'Interinato','same-day: duration unavailable':'Registro del mismo día: duración no disponible',
 'end date repaired from source period':'Fecha final recuperada del período original',
 'observed to cutoff; not a completed tenure':'Gestión abierta: duración observada hasta el corte',
 'appointment president unresolved':'Designación sin presidente asignable dentro de la cobertura'};
 if(exact[f])return exact[f];
 if(f.startsWith('overlap: '))return 'Superposición con el registro presidencial '+f.slice(9);
 if(f.startsWith('minister overlap: '))return 'Superposición con la gestión ministerial '+f.slice(18);
 return f.replace(' days without a recorded minister',' días sin ministro registrado');
}
function linksFor(p){return DATA.links.filter(l=>l.president_id===p.id&&(!$('completed').checked||!l.ongoing));}
function measure(p){
 const links=linksFor(p),appointments=links.filter(l=>l.initiated).length;
 return {...p,links,people_serving:new Set(links.map(l=>ministers.get(l.minister_id).name)).size,
  appointments,appointments_per_year:p.days?appointments*365.25/p.days:null,
  mean_service_days:links.length?d3.mean(links,l=>l.days):null};
}
function pick(id){
 const focusKey=document.activeElement?.getAttribute('data-focus');
 selected=selected===id?null:id;render();
 if(focusKey)document.querySelector(`[data-focus="${CSS.escape(focusKey)}"]`)?.focus({preventScroll:true});
}
function render(){
 hideTip();$('regime-detail').hidden=true;
 const from=$('from').value,to=$('to').value,query=norm($('search').value.trim()),valid=from&&to&&from<to;
 visible=valid?DATA.presidents.filter(p=>(p.start<to&&p.end>from||p.days===0&&p.start>=from&&p.start<to)
  &&(!$('regime').value||p.regime_categories.includes($('regime').value))
  &&($('acting').checked||p.authority_role!=='interino')
  &&(!query||norm(nameLabel(p.name)).includes(query)||linksFor(p).some(l=>norm(ministers.get(l.minister_id).name).includes(query)))).map(measure):[];
 if(!visible.some(p=>p.id===selected))selected=null;
 const sort=$('sort').value,metric=$('metric').value;
 visible.sort((a,b)=>sort==='date'?a.start.localeCompare(b.start):(sort==='count'?(b[metric]??-1)-(a[metric]??-1):(b.mean_service_days??-1)-(a.mean_service_days??-1))||a.start.localeCompare(b.start));
 $('status').textContent=valid?`${visible.length} registros presidenciales coinciden con los filtros. La búsqueda conserva todos los ministros de las presidencias encontradas.`:'Elegí un rango válido: «Desde» debe ser anterior a «Hasta».';
 const spellIds=new Set(visible.flatMap(p=>p.links.map(l=>l.minister_id)));
 const unique=new Set([...spellIds].map(id=>ministers.get(id).name));
 $('stats').innerHTML=[[visible.length,'registros presidenciales'],[unique.size,'ministros distintos en esos registros'],[spellIds.size,'gestiones ministeriales que los atraviesan'],[visible.filter(p=>p.flags.length).length,'registros con observaciones']].map(([n,t])=>`<div class="stat"><strong>${fmt(n,0)}</strong><span>${t}</span></div>`).join('');
 $('metric-title').textContent=$('metric').selectedOptions[0].textContent;
 const max=d3.max(visible,p=>p[metric])||1;
 $('comparison').innerHTML=visible.length?visible.map(p=>`<tr class="${p.id===selected?'selected':''}"><td><button data-pick="${p.id}" data-focus="table-${p.id}" aria-pressed="${p.id===selected}">${esc(nameLabel(p.name))}</button><div class="sub">${dateLabel(p.start)} — ${dateLabel(p.end)}${p.ongoing?' · en curso al corte':''}</div>${p.flags.length?'<span class="tag">Con observaciones</span>':''}</td><td>${fmt(p[metric])}<div class="bar" style="width:${100*(p[metric]||0)/max}%;background:${pColor(p)}"></div></td><td>${fmt(p.mean_service_days==null?null:months(p.mean_service_days))}</td><td>${fmt(p.days/365.25,2)}</td></tr>`).join(''):'<tr><td colspan="4" class="empty">No hay registros coincidentes. Ampliá las fechas o borrá la búsqueda.</td></tr>';
 document.querySelectorAll('[data-pick]').forEach(b=>b.onclick=()=>pick(b.dataset.pick));
 regimeRows=valid?DATA.regime_service.filter(r=>spellIds.has(r.minister_id)&&(!$('regime').value||r.category===$('regime').value))
  .map(r=>({...r,start:r.start>from?r.start:from,end:r.end<to?r.end:to}))
  .filter(r=>r.start<r.end).map(r=>({...r,days:dayDiff(r.start,r.end)})):[];
 drawTimeline(from,to);drawRankings();drawDetails();bindPersonLinks();drawRegimes();drawContext(from,to);
}
function drawTimeline(from,to){
 const host=d3.select('#timeline');host.selectAll('*').remove();
 if(!visible.length){host.append('p').attr('class','empty').text('No hay registros para mostrar.');return;}
 const width=Math.max(600,$('timeline').clientWidth-26),height=210;
 const svg=host.append('svg').attr('viewBox',`0 0 ${width} ${height}`).style('min-width','600px').attr('role','group').attr('aria-label','Línea de tiempo presidencial. La tabla permite seleccionar los mismos registros.');
 const x=d3.scaleUtc().domain([new Date(from),new Date(to)]).range([24,width-24]).clamp(true);
 svg.append('g').attr('class','axis').attr('transform','translate(0,170)').call(d3.axisBottom(x).ticks(Math.max(3,Math.floor(width/110))).tickFormat(d3.utcFormat(dayDiff(from,to)<730?'%m/%Y':'%Y')));
 const chronological=[...visible].sort((a,b)=>a.start.localeCompare(b.start)),lanes=[];
 chronological.forEach(p=>{let lane=lanes.findIndex(end=>end<=p.start);if(lane<0)lane=lanes.length;lanes[lane]=p.end;p.lane=lane;});
 svg.append('text').attr('x',24).attr('y',17).text('PRESIDENCIAS · COLOR SEGÚN EL RÉGIMEN EN CADA FECHA');
 const segments=chronological.flatMap(p=>p.regime_periods.map(id=>{const r=periods.get(id);return {p,r,start:p.start>r.start?p.start:r.start,end:p.end<r.end?p.end:r.end};}).filter(s=>s.start<to&&s.end>=from));
 svg.selectAll('rect.segment').data(segments).join('rect').attr('x',s=>x(new Date(s.start))).attr('y',s=>28+s.p.lane*23)
  .attr('width',s=>Math.max(2,x(new Date(s.end))-x(new Date(s.start)))).attr('height',19).attr('fill',s=>color(s.r.category))
  .attr('opacity',s=>selected&&selected!==s.p.id?.25:1);
 const hit=svg.selectAll('rect.term').data(chronological).join('rect').attr('class','term').attr('x',p=>x(new Date(p.start))).attr('y',p=>28+p.lane*23)
  .attr('width',p=>Math.max(3,x(new Date(p.end))-x(new Date(p.start)))).attr('height',19).attr('fill','transparent')
  .attr('stroke',p=>p.id===selected?'#172e2e':p.ongoing?'#253c3b':'none').attr('stroke-width',2).attr('stroke-dasharray',p=>p.ongoing?'4 2':null)
  .attr('tabindex',0).attr('role','button').attr('data-focus',p=>`timeline-${p.id}`).attr('aria-label',p=>`${nameLabel(p.name)}, ${dateLabel(p.start)} a ${dateLabel(p.end)}`).attr('aria-pressed',p=>p.id===selected)
  .style('cursor','pointer').on('click',(e,p)=>pick(p.id)).on('keydown',(e,p)=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();pick(p.id);}})
  .on('pointerenter',(e,p)=>showTip(e,`${nameLabel(p.name)} · ${p.regime}`)).on('pointerleave',hideTip);
 hit.append('title').text(p=>`${nameLabel(p.name)}\n${dateLabel(p.start)} — ${dateLabel(p.end)}\n${p.regime}`);
 const target=visible.find(p=>p.id===selected),ids=new Set((target?[target]:visible).flatMap(p=>p.links.map(l=>l.minister_id)));
 svg.append('text').attr('x',24).attr('y',119).text(target?'SERVICIOS MINISTERIALES · PRESIDENCIA ELEGIDA':'INICIOS DE GESTIONES MINISTERIALES');
 if(target){
  svg.selectAll('rect.minister').data(target.links.filter(l=>l.start<to&&l.end>from)).join('rect').attr('x',l=>x(new Date(l.start))).attr('y',(l,i)=>129+i%3*8).attr('height',5)
   .attr('width',l=>Math.max(1,x(new Date(l.end))-x(new Date(l.start)))).attr('fill','#395f49').append('title').text(l=>`${ministers.get(l.minister_id).name}: ${dateLabel(l.start)} — ${dateLabel(l.end)}`);
 }else{
  svg.selectAll('line.minister').data([...ids].map(id=>ministers.get(id)).filter(m=>m.start>=from&&m.start<to)).join('line').attr('x1',m=>x(new Date(m.start))).attr('x2',m=>x(new Date(m.start))).attr('y1',128).attr('y2',155).attr('stroke','#395f49').attr('opacity',.7).append('title').text(m=>`${m.name}: ${dateLabel(m.start)}`);
 }
}
function sourceLinks(ids){return ids.map(id=>{const s=DATA.classification.sources[id];return `<a href="${esc(s.url)}" target="_blank" rel="noopener">${esc(s.title)}</a>`;}).join(' · ');}
function drawDetails(){
 const p=visible.find(p=>p.id===selected);
 if(!p){$('details').innerHTML='<div class="eyebrow">Explorador de registros</div><h2>Seguí una presidencia</h2><p>Elegí un registro para ver sus ministros, las designaciones heredadas, los períodos originales y las observaciones sobre los datos.</p><p class="sub">Probá el período 2001–2003 y el indicador «Designaciones por año» para ver cuánto cambia una comparación cuando la presidencia dura pocos días.</p>';return;}
 const classNotes=p.regime_periods.map(id=>{const r=periods.get(id);return `<p><b>${esc(label(r.category))}</b><br><span class="sub">${esc(r.rationale)}</span></p>`;}).join('');
 $('details').innerHTML=`<div class="eyebrow">Registro ${p.id} · ${esc(p.authority_role)}</div><h2>${esc(nameLabel(p.name))}</h2><p>${dateLabel(p.start)} — ${dateLabel(p.end)}${p.ongoing?' · observado hasta el corte':''}</p><p>${fmt(p.days/365.25,2)} años observados · ${p.people_serving} personas · ${p.links.length} gestiones</p><button id="clear-selection">Quitar selección</button> <button id="zoom-selection" ${p.days?'':'disabled'}>Acercar al período</button><h3>Ministros en funciones</h3>${p.links.length?p.links.map(l=>{const m=ministers.get(l.minister_id);return `<div style="border-top:1px solid #c5cebf;padding:12px 0"><button data-person="${esc(m.name)}">${esc(m.name)} · ver ficha</button> <span class="tag">${l.initiated?'Designado en el período':'Heredado'}</span><div class="sub">${esc(m.office)} · ${dateLabel(l.start)} — ${dateLabel(l.end)}</div><p>${fmt(months(l.days))} meses en esta presidencia; ${fmt(months(m.days))} meses en la gestión ${m.ongoing?'observada hasta el corte':'completa'}.</p><div class="sub">Presidente según la fuente: ${esc(m.source_president)}<br>Período original: ${esc(m.source_period)}</div>${m.flags.length?`<ul>${m.flags.map(f=>`<li>${esc(flagsText(f))}</li>`).join('')}</ul>`:''}</div>`;}).join(''):'<p>No hay servicio ministerial registrado con estos filtros.</p>'}<h3>Contexto institucional</h3>${classNotes}<h3>Observaciones</h3><ul>${p.flags.map(f=>`<li>${esc(flagsText(f))}</li>`).join('')||'<li>Sin observaciones automáticas.</li>'}</ul><p class="sub">Fila ${p.source_row} de la base presidencial original. Los días sin cobertura se calculan con todas las gestiones disponibles, antes del filtro de gestiones finalizadas. Los interinatos pueden coexistir con un titular formal.</p>`;
 $('clear-selection').onclick=()=>{selected=null;render();};
 $('zoom-selection').onclick=()=>{$('from').value=p.start;$('to').value=p.end;render();};
}
function drawRegimes(){
 const max=d3.max(regimeRows,r=>months(r.days))||1;
 const selectedIds=new Set(visible.find(p=>p.id===selected)?.links.map(l=>l.minister_id)||[]);
 $('regimes').innerHTML=categories.map((c,i)=>{const rows=regimeRows.filter(r=>r.category===c.id),vals=rows.map(r=>months(r.days));return `<div class="regime-card" style="--c:${c.color}"><h3>${esc(c.label)}</h3><p><strong>${fmt(d3.median(vals))}</strong> meses · mediana</p><div class="sub">Promedio ${fmt(d3.mean(vals))} · n = ${rows.length} fragmentos</div><div class="sub">${new Set(rows.map(r=>r.minister_id)).size} gestiones · ${rows.filter(r=>r.ongoing).length} fragmentos de gestiones abiertas</div><svg id="regime-${i}" role="group" aria-label="${esc(c.label)}: distribución de permanencias"></svg><button data-category="${c.id}">Ver períodos y fuentes</button></div>`;}).join('');
 categories.forEach((c,i)=>{
  const rows=regimeRows.filter(r=>r.category===c.id).sort((a,b)=>a.days-b.days||a.minister_id.localeCompare(b.minister_id));
  const svg=d3.select(`#regime-${i}`),x=d3.scaleLinear().domain([0,max]).nice().range([14,280]);
  const placed=[];let maxY=0;
  for(const r of rows){const px=x(months(r.days));let offset=0;for(let j=0;j<1000;j++){const candidate=j===0?0:Math.ceil(j/2)*7.5*(j%2?1:-1);if(placed.every(p=>Math.hypot(p.x-px,p.y-candidate)>=7.5)){offset=candidate;break;}}placed.push({r,x:px,y:offset});maxY=Math.max(maxY,Math.abs(offset));}
  const center=maxY+14,axisY=2*maxY+65,height=axisY+36;svg.attr('viewBox',`0 0 300 ${height}`);
  if(rows.length){const values=rows.map(r=>months(r.days)),q1=d3.quantile(values,.25),q3=d3.quantile(values,.75),median=d3.median(values);
   svg.append('line').attr('x1',x(d3.min(values))).attr('x2',x(d3.max(values))).attr('y1',axisY-18).attr('y2',axisY-18).attr('stroke',c.color).attr('stroke-width',1.5);
   svg.append('rect').attr('x',x(q1)).attr('width',Math.max(1,x(q3)-x(q1))).attr('y',axisY-24).attr('height',12).attr('fill',c.color).attr('fill-opacity',.25);
   svg.append('line').attr('x1',x(median)).attr('x2',x(median)).attr('y1',axisY-27).attr('y2',axisY-9).attr('stroke',c.color).attr('stroke-width',2.5);
  }
  svg.append('g').attr('class','axis').attr('transform',`translate(0,${axisY})`).call(d3.axisBottom(x).ticks(4).tickFormat(d=>fmt(d,0)));
  const description=r=>`${ministers.get(r.minister_id).name}: ${fmt(months(r.days))} meses, ${dateLabel(r.start)} a ${dateLabel(r.end)}${r.ongoing?'; gestión abierta al corte':''}`;
  svg.selectAll('circle').data(placed).join('circle').attr('cx',p=>p.x).attr('cy',p=>center+p.y).attr('r',3.3).attr('fill',p=>p.r.ongoing?'#fffcf5':c.color).attr('stroke',c.color).attr('stroke-width',1.4)
   .attr('opacity',p=>selected&&!selectedIds.has(p.r.minister_id)?.2:1).attr('tabindex',0).attr('role','button').attr('aria-label',p=>description(p.r))
   .on('pointerenter',(e,p)=>showTip(e,description(p.r))).on('pointerleave',hideTip).on('focus',(e,p)=>showTip(e,description(p.r))).on('blur',hideTip)
   .on('click',(e,p)=>showRegimeRecord(p.r)).on('keydown',(e,p)=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();showRegimeRecord(p.r);}}).append('title').text(p=>description(p.r));
  if(!rows.length)svg.append('text').attr('x',15).attr('y',22).attr('fill','#596865').text('Sin observaciones en este rango');
 });
 document.querySelectorAll('[data-category]').forEach(b=>b.onclick=()=>{setChapter('methods',false);$('classification').open=true;document.getElementById('class-'+b.dataset.category)?.scrollIntoView({behavior:'auto',block:'start'});});
}
function showRegimeRecord(r){
 const m=ministers.get(r.minister_id),period=periods.get(r.period_id);
 $('regime-detail').hidden=false;$('regime-detail').innerHTML=`<b>${esc(m.name)} · ${esc(label(r.category))}</b><p>${dateLabel(r.start)} — ${dateLabel(r.end)}: ${fmt(months(r.days))} meses dentro del episodio y el filtro. Gestión original: ${esc(m.source_period)}.</p><p>${esc(period.rationale)}</p><p>${sourceLinks(period.sources)}</p>`;
}
function drawContext(from,to){
 const hints=[
  ['1912-02-10','La Ley Sáenz Peña reformó el voto, pero mantuvo exclusiones. En el atlas, el cambio de mandato electoral se ubica en 1916.','reform'],
  ['1951-11-11','Las mujeres votaron por primera vez en una elección presidencial en 1951. El mandato resultante comenzó en junio de 1952.','suffrage'],
  ['1962-03-29','Guido asumió por la vía sucesoria después de un golpe y quedó bajo tutela militar: el atlas lo agrupa en de facto y conserva su particularidad de autoridad civil bajo tutela militar.','guido'],
  ['1983-12-10','La asunción de Alfonsín marca el inicio del período democrático que el atlas sigue hasta el corte de los datos.','restoration']
 ];
 const candidates=hints.filter(h=>h[0]>=from&&h[0]<to),chosen=candidates.length?candidates[Math.min(candidates.length-1,selected?1:0)]:null;
 $('context-note').innerHTML=chosen?`<b>${dateLabel(chosen[0])}</b> · ${esc(chosen[1])} ${sourceLinks([chosen[2]])}`:'Podés consultar los criterios y las fuentes de cada categoría al final del atlas.';
}
function downloadCSV(filename,columns,rows){
 const quote=v=>'"'+String(v??'').replace(/"/g,'""')+'"';
 const csv=[columns.map(quote).join(';'),...rows.map(r=>r.map(quote).join(';'))].join('\r\n');
 const url=URL.createObjectURL(new Blob(['\ufeff'+csv],{type:'text/csv;charset=utf-8'})),a=document.createElement('a');a.href=url;a.download=filename;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
}
const exportNumber=n=>n==null?'':String(n).replace('.',',');
const filterLabel=()=> $('completed').checked?'solo gestiones finalizadas':'todas las gestiones observadas';
$('download').onclick=()=>downloadCSV('argentina-comparacion-presidencial.csv',
 ['registro','presidente','inicio','fin','categorias_historicas','dias_presidencia','ministros_distintos','designaciones','designaciones_por_anio','permanencia_promedio_dias','presidencia_abierta','observaciones','filtro_gestiones'],
 visible.map(p=>[p.id,nameLabel(p.name),dateLabel(p.start),dateLabel(p.end),p.regime,p.days,p.people_serving,p.appointments,exportNumber(p.appointments_per_year),exportNumber(p.mean_service_days),p.ongoing?'sí':'no',p.flags.map(flagsText).join(' | '),filterLabel()]));
$('download-spells').onclick=()=>downloadCSV('argentina-servicios-ministeriales.csv',
 ['registro_presidencial','presidente','gestion','ministro','cartera','inicio_servicio','fin_servicio','dias_servicio','designado_en_presidencia','gestion_abierta','periodo_original','filtro_gestiones'],
 visible.flatMap(p=>p.links.map(l=>{const m=ministers.get(l.minister_id);return [p.id,nameLabel(p.name),m.id,m.name,m.office,dateLabel(l.start),dateLabel(l.end),l.days,l.initiated?'sí':'no',m.ongoing?'sí':'no',m.source_period,filterLabel()];})));
$('download-regimes').onclick=()=>downloadCSV('argentina-servicios-por-regimen.csv',
 ['gestion','ministro','episodio','categoria','inicio_fragmento','fin_fragmento','dias_fragmento','gestion_abierta','fuentes','filtro_gestiones'],
 regimeRows.map(r=>[r.minister_id,ministers.get(r.minister_id).name,r.period_id,label(r.category),dateLabel(r.start),dateLabel(r.end),r.days,r.ongoing?'sí':'no',periods.get(r.period_id).sources.map(id=>DATA.classification.sources[id].url).join(' | '),filterLabel()]));
['search','from','to','regime','acting','metric','sort','completed'].forEach(id=>$(id).addEventListener(id==='search'?'input':'change',render));
$('reset').onclick=()=>{$('search').value='';$('from').value='1880-10-12';$('to').value=DATA.cutoff;$('regime').value='';$('acting').checked=false;$('completed').checked=false;$('metric').value='people_serving';$('sort').value='date';selected=null;render();};
document.querySelectorAll('[data-range]').forEach(b=>b.onclick=()=>{[$('from').value,$('to').value]=b.dataset.range.split(',');selected=null;render();});
$('regime').innerHTML='<option value="">Todas las categorías</option>'+categories.map(c=>`<option value="${c.id}">${esc(c.label)}</option>`).join('');
$('legend').innerHTML=categories.map(c=>`<span style="--c:${c.color}">${esc(c.label)}</span>`).join('');
$('criteria').textContent=DATA.classification.criteria;
const firstCategory=new Set();
$('classification-periods').innerHTML=DATA.classification.periods.map(r=>{const anchor=firstCategory.has(r.category)?'':`id="class-${r.category}"`;firstCategory.add(r.category);return `<div class="source-period" ${anchor}><div><b>${dateLabel(r.start)}<br>al ${dateLabel(r.end)}</b><div class="sub">Fin sin incluir</div></div><div><h3 style="color:${color(r.category)};margin:0">${esc(label(r.category))}</h3><p>${esc(r.rationale)}</p><p class="sub">Situación institucional: ${esc(r.status)}.<br>Electorado: ${esc(r.electorate)}.<br>Competencia: ${esc(r.competition)}.</p><p>${sourceLinks(r.sources)}</p></div></div>`;}).join('');
$('audit-summary').textContent=`La auditoría registra ${DATA.audit.length} hallazgos: reparaciones, duplicados, vínculos, superposiciones y vacíos. El primer ministro de la base precede a la cobertura presidencial: se conserva en los datos, pero no entra en las comparaciones. Las fechas originales aún requieren contrastación histórica en los casos señalados.`;
let resizeTimer;window.addEventListener('resize',()=>{clearTimeout(resizeTimer);resizeTimer=setTimeout(render,120);});
const chapters=['history','rankings','compare','regime-panel','people','hair-panel','methods'];
let activeChapter=chapters.includes(location.hash.slice(1))?location.hash.slice(1):'history',allChapters=false;
const profiles=new Map(DATA.profiles.people.map(p=>[p.name,p]));
let activePerson='Domingo Cavallo';
function setChapter(id,scroll=true){
 activeChapter=id;
 $('global-exploration').hidden=!allChapters&&['people','hair-panel','methods'].includes(id);
 document.querySelectorAll('[data-panel]').forEach(p=>p.hidden=!allChapters&&p.id!==id);
 document.querySelectorAll('[data-chapter]').forEach(b=>b.setAttribute('aria-pressed',b.dataset.chapter===id));
 $('show-all').setAttribute('aria-pressed',allChapters);
 $('show-all').textContent=allChapters?'Volver a bloques':'Ver todo seguido';
 const i=chapters.indexOf(id);$('previous-chapter').disabled=i===0;$('next-chapter').disabled=i===chapters.length-1;
 $('chapter-progress').textContent=allChapters?'Recorrido completo':`${i+1} de ${chapters.length} · ${document.querySelector(`[data-chapter="${id}"]`).textContent}`;
 history.replaceState(null,'','#'+id);
 render();
 if(scroll){$(id).scrollIntoView({block:'start'});$(id).setAttribute('tabindex','-1');$(id).focus({preventScroll:true});}
}
document.querySelectorAll('[data-chapter]').forEach(b=>b.onclick=()=>setChapter(b.dataset.chapter));
$('show-all').onclick=()=>{allChapters=!allChapters;setChapter(activeChapter);};
$('previous-chapter').onclick=()=>setChapter(chapters[chapters.indexOf(activeChapter)-1]);
$('next-chapter').onclick=()=>setChapter(chapters[chapters.indexOf(activeChapter)+1]);
function unionDays(spells){
 let cursor='',total=0;
 for(const m of [...spells].sort((a,b)=>a.start.localeCompare(b.start))){if(m.end>cursor){total+=dayDiff(m.start>cursor?m.start:cursor,m.end);cursor=m.end;}}
 return total;
}
function rankingRecords(){
 const ids=new Set(visible.flatMap(p=>p.links.map(l=>l.minister_id)));
 const rows=DATA.ministers.filter(m=>ids.has(m.id)&&m.days>0&&($('rank-open').checked||!m.ongoing));
 if($('rank-unit').value==='spell')return rows.map(m=>({...m,spells:[m]}));
 return [...d3.group(rows,m=>m.name)].map(([name,spells])=>({name,spells,days:unionDays(spells),start:d3.min(spells,m=>m.start),end:d3.max(spells,m=>m.end),ongoing:spells.some(m=>m.ongoing)}));
}
function drawRankings(){
 const rows=rankingRecords(),max=d3.max(rows,m=>m.days)||1;
 $('rank-scope').textContent=`${rows.length} ${$('rank-unit').value==='spell'?'gestiones elegibles':'personas elegibles'}. ${$('rank-unit').value==='person'?'Se suman los días de sus gestiones elegibles sin duplicar días superpuestos; no incluye automáticamente otros cargos fuera de la selección.':''}`;
 $('rankings-content').innerHTML=[['Los 5 que más duraron',-1],['Los 5 que menos duraron',1]].map(([title,direction])=>`<div><h3>${title}</h3>${[...rows].sort((a,b)=>direction*(a.days-b.days)||a.start.localeCompare(b.start)||a.name.localeCompare(b.name,'es')).slice(0,5).map((m,i)=>`<div class="rank-row"><span class="rank-number">${i+1}</span><button data-person="${esc(m.name)}">${esc(m.name)}</button><div><b>${fmt(m.days,0)} ${m.days===1?'día':'días'}</b> · ${m.days<31?'menos de un mes':fmt(months(m.days))+' meses'}${m.ongoing?' · duración mínima observada':''}</div><div class="bar" style="width:${100*m.days/max}%"></div><div class="sub">${m.spells.length>1?`${m.spells.length} gestiones · `:''}${dateLabel(m.start)} — ${dateLabel(m.end)}${m.ongoing?' · abierta al corte':''}</div></div>`).join('')||'<p class="rank-empty">Sin gestiones elegibles con estos filtros.</p>'}</div>`).join('');
 bindPersonLinks();
}
function bindPersonLinks(){document.querySelectorAll('[data-person]').forEach(b=>b.onclick=()=>openPerson(b.dataset.person));}
function openPerson(name){activePerson=name;$('person-search').value='';$('person-sex').value='';drawPeople();setChapter('people');}
function linkTo(url,title){return `<a href="${esc(url)}" target="_blank" rel="noopener">${esc(title)}</a>`;}
function birthLabel(p){
 if(p.birth_date)return dateLabel(p.birth_date);
 if(p.birth_lower)return p.birth_precision==='month'?p.birth_lower.slice(5,7)+'/'+p.birth_lower.slice(0,4):p.birth_lower.slice(0,4);
 return 'Pendiente';
}
function ageLabel(m){
 if(m.age_at_start!=null)return m.age_at_start+' años';
 if(m.age_at_start_min!=null)return (m.age_at_start_min===m.age_at_start_max?m.age_at_start_min:m.age_at_start_min+'–'+m.age_at_start_max)+' años · fecha parcial';
 return 'Edad pendiente';
}
function birthStatusLabel(p){
 if(p.birth_status?.startsWith('Wikidata'))return 'Nacimiento tomado de Wikidata en primera pasada; pendiente de contraste independiente.';
 if(p.birth_review_note?.startsWith('requires review'))return 'Nacimiento con discrepancias o dudas de identificación: pendiente de contraste.';
 if(p.birth_date)return 'Nacimiento con fuente biográfica enlazada.';
 return 'Fecha de nacimiento pendiente de investigación.';
}
let activePeopleGroup='A-E';
const peopleGroups=[['A-E','A','E'],['F-M','F','M'],['N-Z','N','Z']];
function drawPeople(){
 const q=norm($('person-search').value),sex=$('person-sex').value;
 const matches=DATA.profiles.people.filter(p=>(!sex||(sex==='unknown'?!p.sex:p.sex===sex))&&norm([p.name,p.policy?.title,p.policy?.text,p.quote?.text].join(' ')).includes(q)).sort((a,b)=>a.name.localeCompare(b.name,'es'));
 const firstLetter=p=>p.name.normalize('NFD').replace(/[\u0300-\u036f]/g,'').toUpperCase()[0];
 const inGroup=(p,g)=>{const letter=firstLetter(p);return letter>=g[1]&&letter<=g[2];};
 if(!q&&!matches.some(p=>inGroup(p,peopleGroups.find(g=>g[0]===activePeopleGroup))))activePeopleGroup=peopleGroups.find(g=>matches.some(p=>inGroup(p,g)))?.[0]||'A-E';
 const rows=q?matches:matches.filter(p=>inGroup(p,peopleGroups.find(g=>g[0]===activePeopleGroup)));
 $('people-groups').innerHTML=peopleGroups.map(g=>`<button type="button" data-people-group="${g[0]}" aria-pressed="${g[0]===activePeopleGroup}" class="${g[0]===activePeopleGroup?'active':''}">${g[0]} <span>${matches.filter(p=>inGroup(p,g)).length}</span></button>`).join('');
 document.querySelectorAll('[data-people-group]').forEach(b=>b.onclick=()=>{activePeopleGroup=b.dataset.peopleGroup;drawPeople();});
 if(!rows.some(p=>p.name===activePerson))activePerson=rows[0]?.name;
 $('people-list').innerHTML=rows.map(p=>`<button data-directory-person="${esc(p.name)}" aria-pressed="${p.name===activePerson}" class="${p.name===activePerson?'active':''}">${esc(p.name)}<span class="sub" style="display:block;color:inherit">${p.birth_date?'Edad disponible':p.birth_lower?'Edad con rango':'Nacimiento pendiente'}${p.policy?' · medida':''}${p.quote?' · frase':''}</span></button>`).join('')||'<p>No hay fichas que coincidan.</p>';
 document.querySelectorAll('[data-directory-person]').forEach(b=>b.onclick=()=>{activePerson=b.dataset.directoryPerson;drawPeople();document.querySelector(`[data-directory-person="${CSS.escape(activePerson)}"]`)?.focus({preventScroll:true});});
 const p=profiles.get(activePerson);
 if(!p){$('person-card').innerHTML='<p>Probá otro nombre, medida o frase.</p>';return;}
 const spells=DATA.ministers.filter(m=>m.name===p.name),policy=p.policy,quote=p.quote,hair=p.hair;
 $('person-card').innerHTML=`<div class="eyebrow">Ficha individual · investigación en curso</div><h2>${esc(p.name)}</h2><div class="person-facts"><div><span class="sub">Sexo/género según fuente</span><strong>${esc(p.sex||'Sin dato')}</strong></div><div><span class="sub">Nacimiento</span><strong>${birthLabel(p)}</strong></div></div><p class="source">${p.bio_sources.map(s=>linkTo(s.url,s.title)).join(' · ')}${p.sex_source_url?' · '+linkTo(p.sex_source_url,'Sexo/género en Wikidata'):''}</p><p class="sub">${birthStatusLabel(p)}</p><h3>Edad en cada asunción</h3>${spells.map(m=>`<p><b>${ageLabel(m)}</b> · ${dateLabel(m.start)}<br><span class="sub">${esc(m.office)} · ${fmt(m.days,0)} días${m.ongoing?' observados al corte':''} · hasta ${dateLabel(m.end)}</span></p>`).join('')}<h3>Una medida para recordar</h3>${policy?`<p><b>${esc(policy.title)} · ${policy.year}</b></p><p>${esc(policy.text)}</p><p class="source">Selección editorial de un hito documentado. ${linkTo(policy.source_url,policy.source_title)}</p>`:'<p class="sub">Pendiente de investigación. No se asignó una medida por asociación con el presidente.</p>'}<h3>La frase que quedó</h3>${quote?`<blockquote>«${esc(quote.text)}»</blockquote><p class="sub">${quote.year} · ${esc(quote.kind)}. ${esc(quote.context)}</p><p class="source">${linkTo(quote.source_url,quote.source_title)}</p>`:'<p class="sub">Todavía no hay una frase documentada en esta ficha. El nombre de un plan no cuenta como cita personal.</p>'}<details><summary>Índice pelado · ${hair?hair.score+'/100':'sin evaluar'}</summary>${hair?`<p><strong>${hair.score}/100</strong> · ${esc(hair.period)}</p><p>${esc(hair.note)}</p>${hair.date_basis?`<p class="sub">Sobre la fecha: ${esc(hair.date_basis)}</p>`:''}${hair.view_limitations?`<p class="sub">Límites de la imagen: ${esc(hair.view_limitations)}</p>`:''}<p class="sub">Confianza ${esc(hair.confidence)} · valoración subjetiva de la imagen indicada.</p><meter min="0" max="100" value="${hair.score}" aria-label="Índice pelado, ${hair.score} de 100">${hair.score}/100</meter><p>${linkTo(hair.source_url,'Consultar la fuente de la foto')}</p>`:'<p>Sin evaluar: falta una imagen que permita identificar a la persona y apreciar el pelo. No equivale a 0/100.</p>'}<p class="sub">${esc(DATA.profiles.hair_methodology)}</p></details><details><summary>Seguir investigando esta persona</summary><p>Estas búsquedas abren la web; no son fuentes ya verificadas.</p>${[['Biografía',p.name+' ministro economía nacimiento biografía'],['Medida o plan',p.name+' ministro economía plan medida'],['Frase y contexto',p.name+' ministro frase discurso'],['Retrato de época',p.name+' ministro retrato fotografía']].map(([title,q])=>`<p>${linkTo('https://www.google.com/search?q='+encodeURIComponent(q),title)}</p>`).join('')}</details>`;
}
['rank-unit','rank-open'].forEach(id=>$(id).onchange=drawRankings);
$('person-search').oninput=drawPeople;$('person-sex').onchange=drawPeople;
$('profile-coverage').textContent=`${DATA.profiles.people.length} fichas por nombre de la base · ${DATA.profiles.people.filter(p=>p.birth_date).length} nacimientos completos · ${DATA.profiles.people.filter(p=>p.birth_lower&&!p.birth_date).length} con mes/año o año · ${DATA.profiles.people.filter(p=>p.sex).length} con sexo/género en fuente · ${DATA.profiles.people.filter(p=>p.policy).length} con medida · ${DATA.profiles.people.filter(p=>p.quote).length} con frase · ${DATA.profiles.people.filter(p=>p.hair).length} con índice pelado. Los datos incorporados desde Wikidata están identificados como primera pasada.`;
const enrichment=DATA.profiles.first_pass?.coverage;
$('enrichment-summary').innerHTML=enrichment?`<p>De ${enrichment.baseline.birth_date} a ${enrichment.exact_birth} nacimientos completos, más ${enrichment.partial_birth} fechas parciales. El sexo/género con fuente pasó de ${enrichment.baseline.sex} a ${enrichment.sex_or_gender} fichas.</p><p>${enrichment.cdi_matched_names} nombres tienen correspondencias en CDI. Los ${enrichment.names} nombres apuntan a ${enrichment.wikidata_entities} entidades: las variantes José / José María Dagnino Pastore comparten identificador. Se conservan los nombres originales del inventario.</p><p>Se localizaron ${enrichment.portrait_candidates} referencias de imágenes para ${enrichment.portrait_candidate_names} nombres. Son candidatas: localizar una imagen no implica haberla inspeccionado ni poder puntuarla.</p><p>Las fechas de nacimiento con conflictos o incompatibilidades se retienen para revisión, sin generar edades. La precisión por año o mes se conserva mediante rangos; no se inventan cumpleaños. No se modificaron las fechas de los cargos.</p><p>Wikidata es una fuente de datos estructurados, con referencias de calidad variable. Esta primera pasada no equivale a contraste independiente de todas las biografías. P21 se conserva como «sexo o género» según la fuente.</p><p>${linkTo('https://cdi.mecon.gob.ar/ministros-de-economia','CDI: listado, decretos y bibliografía')} · ${linkTo('https://www.wikidata.org','Wikidata')}</p>`:'<p>Sin pasada de enriquecimiento registrada.</p>';
$('bio-method').textContent=DATA.profiles.methodology;$('hair-method').textContent=DATA.profiles.hair_methodology;
$('crosswalk').innerHTML='<h3>Correspondencia con las categorías anteriores</h3><table><thead><tr><th>Categoría anterior</th><th>Nueva categoría</th></tr></thead><tbody>'+DATA.classification.crosswalk.map(c=>`<tr><td>${esc(c.previous_label)}</td><td>${esc(label(c.category))}</td></tr>`).join('')+'</tbody></table>';
$('download-profiles').onclick=()=>downloadCSV('argentina-fichas-ministeriales.csv',['ministro','gestion','inicio','sexo_genero_segun_fuente','nacimiento','edad_al_asumir','fuentes_biografia','medida','anio_medida','fuente_medida','frase','anio_frase','tipo_atribucion','fuente_frase','calvicie_visual','periodo_imagen','fuente_imagen','confianza_visual','nota_visual','nacimiento_desde','nacimiento_hasta','precision_nacimiento','edad_minima','edad_maxima','estado_nacimiento','fuente_sexo_genero','wikidata_id','fuente_CDI','fecha_foto_declarada','precision_fecha_foto','base_fecha_foto','limites_imagen'],DATA.ministers.map(m=>{const p=profiles.get(m.name);return [m.name,m.id,m.start,p.sex,p.birth_date,m.age_at_start,p.bio_sources.map(s=>s.url).join(' | '),p.policy?.title,p.policy?.year,p.policy?.source_url,p.quote?.text,p.quote?.year,p.quote?.kind,p.quote?.source_url,p.hair?.score,p.hair?.period,p.hair?.source_url,p.hair?.confidence,p.hair?.note,p.birth_lower,p.birth_upper,({day:'día',month:'mes',year:'año'}[p.birth_precision]||''),m.age_at_start_min,m.age_at_start_max,birthStatusLabel(p),p.sex_source_url,p.wikidata_id,p.cdi_source_url,p.hair?.capture_date,p.hair?.capture_date_precision,p.hair?.date_basis,p.hair?.view_limitations];}));
drawPeople();setChapter(activeChapter,false);
window.mountPeladometro?.();
