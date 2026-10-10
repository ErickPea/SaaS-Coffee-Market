/* Página de mercados. */
let marketChart = null;
let compareChart = null;
let currentMarket = 'nacional';
let currentCoffee = 'pergamino_seco';
let isCompareMode = false;

function fmtByCurrency(value, currency) {
  return currency === 'USD' ? CM.usd(value) : CM.cop(value);
}

async function loadSingleMarket() {
  document.getElementById('singleMarketView').style.display = '';
  document.getElementById('compareView').style.display = 'none';

  const period = document.getElementById('marketPeriod').value;
  const current = await CM.get(`/api/prices/current?market=${currentMarket}&coffee_type=${currentCoffee}&period=${period}`);

  const grid = document.getElementById('marketStatGrid');
  const trendClass = current.trend === 'alcista' ? 'trend-alcista' : (current.trend === 'bajista' ? 'trend-bajista' : '');
  grid.innerHTML = `
    <div class="stat-card ${trendClass}">
      <div class="stat-label">Precio actual (${current.unit}) ${current.is_demo ? '<span class="badge demo">Demo</span>' : ''}</div>
      <span class="stat-value">${fmtByCurrency(current.current_price, current.currency)}</span>
      <div class="stat-change ${CM.changeClass(current.change_pct)}">${CM.trendArrow(current.trend)} ${current.change_pct != null ? CM.pct(current.change_pct) : 'sin dato previo'}</div>
    </div>
    <div class="stat-card">
      <div class="stat-label">Equivalente COP/kg</div>
      <span class="stat-value">${CM.cop(current.price_cop_per_kg)}</span>
    </div>
    <div class="stat-card">
      <div class="stat-label">Máximo del período</div>
      <span class="stat-value">${fmtByCurrency(current.period_max, current.currency)}</span>
    </div>
    <div class="stat-card">
      <div class="stat-label">Mínimo del período</div>
      <span class="stat-value">${fmtByCurrency(current.period_min, current.currency)}</span>
    </div>
    <div class="stat-card">
      <div class="stat-label">Promedio del período</div>
      <span class="stat-value">${fmtByCurrency(current.period_avg, current.currency)}</span>
    </div>
    <div class="stat-card">
      <div class="stat-label">Tendencia</div>
      <span class="stat-value" style="font-family: var(--font-body); font-size: 1.1rem;">${CM.trendArrow(current.trend)} ${current.trend[0].toUpperCase() + current.trend.slice(1)}</span>
    </div>
  `;

  document.getElementById('chartTitle').textContent =
    `Precio histórico — ${CM.COFFEE_TYPE_LABELS[currentCoffee] || currentCoffee} (${currentMarket})`;

  const history = await CM.get(`/api/prices/history?market=${currentMarket}&coffee_type=${currentCoffee}&period=${period}`);
  document.getElementById('marketSourceNote').innerHTML =
    `Fuente: ${history.source} ${CM.demoBadge(history.is_demo)} — Última actualización: ${CM.dateLabel(current.last_updated)}`;

  const labels = history.points.map(p => new Date(p.timestamp).toLocaleDateString('es-CO', { day: '2-digit', month: 'short' }));

  if (marketChart) marketChart.destroy();
  const ctx = document.getElementById('marketChart').getContext('2d');
  marketChart = new Chart(ctx, {
    type: 'line',
    data: {
      labels,
      datasets: [{
        label: `Precio (COP/kg)`,
        data: history.points.map(p => p.price_cop_kg),
        borderColor: '#1F4D3A', backgroundColor: 'rgba(31,77,58,0.08)',
        fill: true, tension: 0.25, pointRadius: 0, borderWidth: 2,
      }],
    },
    options: { responsive: true, plugins: { legend: { display: false } } },
  });
}

async function loadCompare() {
  document.getElementById('singleMarketView').style.display = 'none';
  document.getElementById('compareView').style.display = '';

  const period = document.getElementById('marketPeriod').value;
  const cmp = await CM.get(`/api/markets/compare?period=${period}`);

  document.getElementById('cmpNational').textContent = CM.cop(cmp.national.price_cop_per_kg);
  document.getElementById('cmpIntl').textContent = CM.cop(cmp.international.price_cop_per_kg);
  document.getElementById('cmpDiffAbs').textContent = CM.cop(cmp.difference_cop_kg);
  document.getElementById('cmpDiffPct').textContent = CM.pct(cmp.difference_pct);

  const labels = cmp.national_history.map(p => new Date(p.timestamp).toLocaleDateString('es-CO', { day: '2-digit', month: 'short' }));
  if (compareChart) compareChart.destroy();
  const ctx = document.getElementById('compareChart').getContext('2d');
  compareChart = new Chart(ctx, {
    type: 'line',
    data: {
      labels,
      datasets: [
        { label: 'Nacional (COP/kg)', data: cmp.national_history.map(p => p.price_cop_kg), borderColor: '#1F4D3A', pointRadius: 0, borderWidth: 2 },
        { label: 'Internacional (COP/kg equiv.)', data: cmp.international_history.map(p => p.price_cop_kg), borderColor: '#7A4A2E', pointRadius: 0, borderWidth: 2 },
      ],
    },
    options: { responsive: true },
  });
}

function refresh() {
  if (isCompareMode) { loadCompare().catch(console.error); }
  else { loadSingleMarket().catch(console.error); }
}

document.querySelectorAll('#marketTabs .tab-btn').forEach((btn) => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('#marketTabs .tab-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    if (btn.dataset.compare) {
      isCompareMode = true;
    } else {
      isCompareMode = false;
      currentMarket = btn.dataset.market;
      currentCoffee = btn.dataset.coffee;
    }
    refresh();
  });
});

document.getElementById('marketPeriod').addEventListener('change', refresh);

async function setupConverters() {
  const units = await CM.get('/api/markets/units');
  const fromSel = document.getElementById('convFrom');
  const toSel = document.getElementById('convTo');
  units.units.forEach(u => {
    fromSel.innerHTML += `<option value="${u.code}">${u.label}</option>`;
    toSel.innerHTML += `<option value="${u.code}">${u.label}</option>`;
  });
  fromSel.value = 'carga';
  toSel.value = 'kg';

  async function runConvert() {
    const amount = parseFloat(document.getElementById('convAmount').value) || 0;
    if (amount <= 0) { document.getElementById('convResult').textContent = '—'; return; }
    const res = await CM.get(`/api/markets/units/convert?amount=${amount}&from_unit=${fromSel.value}&to_unit=${toSel.value}`);
    document.getElementById('convResult').textContent = `${CM.num(res.result, 4)} ${toSel.value}`;
  }
  [document.getElementById('convAmount'), fromSel, toSel].forEach(el => el.addEventListener('input', runConvert));
  runConvert();

  async function runCurrencyConvert() {
    const amount = parseFloat(document.getElementById('curAmount').value) || 0;
    const from = document.getElementById('curFrom').value;
    const to = document.getElementById('curTo').value;
    if (amount <= 0) { document.getElementById('curResult').textContent = '—'; return; }
    const res = await CM.get(`/api/currency/convert?amount=${amount}&from_currency=${from}&to_currency=${to}`);
    document.getElementById('curResult').textContent = fmtByCurrency(res.result, to);
  }
  ['curAmount', 'curFrom', 'curTo'].forEach(id => document.getElementById(id).addEventListener('input', runCurrencyConvert));
  runCurrencyConvert();
}

document.addEventListener('DOMContentLoaded', () => {
  refresh();
  setupConverters().catch(console.error);
});
