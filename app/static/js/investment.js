/* Simulador de inversión. */
let costChart = null, scenarioChart = null, sensitivityChart = null;
let lastResult = null, lastScenarios = null, lastSensitivity = null, lastOpportunity = null;

function buildCostFields() {
  const container = document.getElementById('costFields');
  Object.entries(CM.COST_LABELS).forEach(([key, label]) => {
    const div = document.createElement('div');
    div.className = 'field';
    div.innerHTML = `<label for="cost_${key}">${label}</label><input type="number" id="cost_${key}" min="0" step="any" value="0">`;
    container.appendChild(div);
  });
}

function readCosts() {
  const costs = {};
  Object.keys(CM.COST_LABELS).forEach((key) => {
    costs[key] = parseFloat(document.getElementById(`cost_${key}`).value) || 0;
  });
  return costs;
}

function buildPayload() {
  const useCurrentPrice = document.querySelector('input[name="priceMode"]:checked').value === 'actual';
  const payload = {
    coffee_type: document.getElementById('coffeeType').value,
    hectares: parseFloat(document.getElementById('hectares').value),
    production_per_hectare_kg: parseFloat(document.getElementById('prodHa').value),
    use_current_price: useCurrentPrice,
    currency: 'COP',
    costs: readCosts(),
  };
  if (!useCurrentPrice) {
    payload.custom_price_per_kg = parseFloat(document.getElementById('customPrice').value);
  }
  const capital = document.getElementById('capital').value;
  if (capital) payload.capital_disponible = parseFloat(capital);
  return payload;
}

function scenarioParamsPayload() {
  return {
    pessimist_price_pct: parseFloat(document.getElementById('pesPrecio').value),
    pessimist_production_pct: parseFloat(document.getElementById('pesProd').value),
    pessimist_cost_pct: parseFloat(document.getElementById('pesCosto').value),
    optimist_price_pct: parseFloat(document.getElementById('optPrecio').value),
    optimist_production_pct: parseFloat(document.getElementById('optProd').value),
    optimist_cost_pct: parseFloat(document.getElementById('optCosto').value),
  };
}

function renderResultStats(result) {
  const grid = document.getElementById('resultStatGrid');
  const items = [
    ['Inversión total', CM.cop(result.total_investment)],
    ['Producción total', `${CM.num(result.total_production_kg)} kg`],
    ['Ingresos', CM.cop(result.total_income)],
    ['Utilidad', CM.cop(result.profit)],
    ['ROI', CM.pct(result.roi_pct)],
    ['Margen', CM.pct(result.margin_pct)],
    ['Punto de equilibrio', `${CM.num(result.break_even_kg, 1)} kg`],
    ['Precio usado (COP/kg)', `${CM.cop(result.price_per_kg)} · ${result.price_source}`],
  ];
  grid.innerHTML = items.map(([label, value]) => `
    <div class="stat-card">
      <div class="stat-label">${label}</div>
      <span class="stat-value" style="font-size:1.15rem;">${value}</span>
    </div>
  `).join('');
}

function renderCostChart(result) {
  const breakdown = result.cost_breakdown.by_category;
  const labels = Object.keys(breakdown).map(k => CM.COST_LABELS[k] || k);
  const values = Object.values(breakdown);

  if (costChart) costChart.destroy();
  const ctx = document.getElementById('costChart').getContext('2d');
  costChart = new Chart(ctx, {
    type: 'bar',
    data: { labels, datasets: [{ label: 'Costo (COP)', data: values, backgroundColor: '#1F4D3A' }] },
    options: {
      indexAxis: 'y',
      plugins: { legend: { display: false } },
      scales: { x: { ticks: { callback: (v) => CM.cop(v) } } },
    },
  });
}

function renderCapital(result) {
  const card = document.getElementById('capitalCard');
  if (!result.capital_analysis) { card.style.display = 'none'; return; }
  card.style.display = '';
  const c = result.capital_analysis;
  const content = document.getElementById('capitalContent');
  if (c.alcanza) {
    content.innerHTML = `
      <p><strong style="color: var(--color-up);">Sí, tu capital alcanza.</strong></p>
      <table>
        <tr><td>Capital disponible</td><td class="num mono">${CM.cop(c.capital_disponible)}</td></tr>
        <tr><td>Inversión requerida</td><td class="num mono">${CM.cop(c.inversion_requerida)}</td></tr>
        <tr><td>Sobrante estimado</td><td class="num mono">${CM.cop(c.sobrante)}</td></tr>
        <tr><td>Hectáreas que podrías cubrir con ese capital</td><td class="num mono">${CM.num(c.hectareas_cubribles, 2)}</td></tr>
      </table>`;
  } else {
    content.innerHTML = `
      <p><strong style="color: var(--color-down);">No, tu capital no alcanza.</strong></p>
      <table>
        <tr><td>Capital disponible</td><td class="num mono">${CM.cop(c.capital_disponible)}</td></tr>
        <tr><td>Inversión requerida</td><td class="num mono">${CM.cop(c.inversion_requerida)}</td></tr>
        <tr><td>Te faltan aproximadamente</td><td class="num mono">${CM.cop(c.faltante)}</td></tr>
        <tr><td>Hectáreas que sí podrías cubrir con ese capital</td><td class="num mono">${CM.num(c.hectareas_cubribles, 2)}</td></tr>
      </table>`;
  }
  content.innerHTML += `<p class="source-note">Estimación basada en el costo promedio por hectárea de esta simulación. No constituye asesoría financiera.</p>`;
}

function renderScenarios(comparison) {
  const tbody = document.querySelector('#scenarioTable tbody');
  tbody.innerHTML = comparison.scenarios.map(s => `
    <tr>
      <td>${s.label}</td>
      <td class="num mono">${CM.cop(s.result.total_investment)}</td>
      <td class="num mono">${CM.cop(s.result.total_income)}</td>
      <td class="num mono">${CM.cop(s.result.profit)}</td>
      <td class="num mono">${CM.pct(s.result.roi_pct)}</td>
    </tr>
  `).join('');

  if (scenarioChart) scenarioChart.destroy();
  const ctx = document.getElementById('scenarioChart').getContext('2d');
  scenarioChart = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: comparison.scenarios.map(s => s.label),
      datasets: [
        { label: 'Inversión', data: comparison.scenarios.map(s => s.result.total_investment), backgroundColor: '#5C6B60' },
        { label: 'Ingresos', data: comparison.scenarios.map(s => s.result.total_income), backgroundColor: '#1F4D3A' },
        { label: 'Utilidad', data: comparison.scenarios.map(s => s.result.profit), backgroundColor: '#7A4A2E' },
      ],
    },
    options: { responsive: true, scales: { y: { ticks: { callback: (v) => CM.cop(v) } } } },
  });
}

function renderSensitivity(sensitivity) {
  if (sensitivityChart) sensitivityChart.destroy();
  const ctx = document.getElementById('sensitivityChart').getContext('2d');
  sensitivityChart = new Chart(ctx, {
    type: 'line',
    data: {
      labels: sensitivity.points.map(p => `${p.price_delta_pct > 0 ? '+' : ''}${p.price_delta_pct}%`),
      datasets: [
        { label: 'Utilidad (COP)', data: sensitivity.points.map(p => p.profit), borderColor: '#1F4D3A', backgroundColor: 'rgba(31,77,58,0.08)', fill: true, tension: 0.2 },
      ],
    },
    options: {
      plugins: {
        tooltip: {
          callbacks: {
            afterLabel: (item) => {
              const p = sensitivity.points[item.dataIndex];
              return [`ROI: ${CM.pct(p.roi_pct)}`, `Punto de equilibrio: ${CM.num(p.break_even_kg, 1)} kg`];
            },
          },
        },
      },
      scales: { y: { ticks: { callback: (v) => CM.cop(v) } } },
    },
  });
}

function renderOpportunity(op) {
  const bars = [
    ['Nivel de oportunidad estimado', op.opportunity_score],
    ['Volatilidad', op.volatility_score],
    ['Sensibilidad al precio', op.price_sensitivity_score],
    ['Margen estimado', op.margin_score],
  ];
  document.getElementById('opportunityBars').innerHTML = bars.map(([label, value]) => `
    <div class="opportunity-bar-row">
      <div class="opportunity-bar-label">${label}</div>
      <div class="opportunity-bar-track"><div class="opportunity-bar-fill" style="width:${Math.max(0, Math.min(100, value))}%"></div></div>
      <div class="opportunity-bar-value">${CM.num(value, 0)}%</div>
    </div>
  `).join('');

  document.getElementById('opportunityExplanation').innerHTML =
    Object.entries(op.explanation).map(([k, v]) => `<div style="margin-bottom:4px;"><strong>${k}:</strong> ${v}</div>`).join('');
  document.getElementById('opportunityDisclaimer').textContent = op.disclaimer;
}

async function runCalculation(e) {
  if (e) e.preventDefault();
  const payload = buildPayload();
  if (!payload.hectares || payload.hectares <= 0) { alert('Las hectáreas deben ser mayores que 0'); return; }
  if (!payload.production_per_hectare_kg || payload.production_per_hectare_kg <= 0) { alert('La producción por hectárea debe ser mayor que 0'); return; }
  if (!payload.use_current_price && !(payload.custom_price_per_kg > 0)) { alert('Ingresa un precio personalizado válido'); return; }

  const submitBtn = document.querySelector('#invForm button[type="submit"]');
  submitBtn.disabled = true; submitBtn.textContent = 'Calculando…';

  try {
    const [result, scenarios, sensitivity, opportunity] = await Promise.all([
      CM.post('/api/investment/calculate', payload),
      CM.post('/api/investment/scenarios', { payload, params: scenarioParamsPayload() }),
      CM.post('/api/investment/sensitivity', payload),
      CM.post('/api/investment/opportunity', payload),
    ]);

    lastResult = result; lastScenarios = scenarios; lastSensitivity = sensitivity; lastOpportunity = opportunity;

    document.getElementById('resultsSection').style.display = '';
    renderResultStats(result);
    renderCostChart(result);
    renderCapital(result);
    renderScenarios(scenarios);
    renderSensitivity(sensitivity);
    renderOpportunity(opportunity);
    document.getElementById('resultsSection').scrollIntoView({ behavior: 'smooth' });
  } catch (err) {
    console.error(err);
    alert('No se pudo calcular la simulación. Revisa los datos ingresados e intenta de nuevo.');
  } finally {
    submitBtn.disabled = false; submitBtn.textContent = 'Calcular';
  }
}

async function recalcScenarios() {
  const payload = buildPayload();
  const scenarios = await CM.post('/api/investment/scenarios', { payload, params: scenarioParamsPayload() });
  lastScenarios = scenarios;
  renderScenarios(scenarios);
}

async function saveSimulation() {
  if (!lastResult) return;
  const name = document.getElementById('simName').value.trim();
  if (!name) { alert('Ponle un nombre a la simulación'); return; }

  const payload = buildPayload();
  const body = {
    name,
    coffee_type: payload.coffee_type,
    hectares: payload.hectares,
    production_per_hectare_kg: payload.production_per_hectare_kg,
    price_used_per_kg: lastResult.price_per_kg,
    price_currency: 'COP',
    price_source: lastResult.price_source,
    capital_disponible: payload.capital_disponible || null,
    costs: payload.costs,
    scenario_params: scenarioParamsPayload(),
    results: {
      total_investment: lastResult.total_investment,
      total_production_kg: lastResult.total_production_kg,
      total_income: lastResult.total_income,
      profit: lastResult.profit,
      roi_pct: lastResult.roi_pct,
      margin_pct: lastResult.margin_pct,
      break_even_kg: lastResult.break_even_kg,
      scenarios: lastScenarios ? lastScenarios.scenarios.map(s => ({
        label: s.label, total_investment: s.result.total_investment,
        total_income: s.result.total_income, profit: s.result.profit, roi_pct: s.result.roi_pct,
      })) : null,
    },
  };

  const saved = await CM.post('/api/simulations', body);
  document.getElementById('saveConfirmation').innerHTML = `
    <p style="color: var(--color-up);">Simulación guardada como "${saved.name}".</p>
    <div style="display:flex; gap:8px; flex-wrap:wrap;">
      <a class="btn secondary" href="/api/simulations/${saved.id}/export/csv">Exportar CSV</a>
      <a class="btn secondary" href="/api/simulations/${saved.id}/export/xlsx">Exportar Excel</a>
      <a class="btn secondary" href="/api/simulations/${saved.id}/export/pdf">Exportar PDF</a>
      <a class="btn secondary" href="/historial">Ver historial</a>
    </div>`;
}

document.addEventListener('DOMContentLoaded', async () => {
  buildCostFields();
  document.getElementById('invForm').addEventListener('submit', runCalculation);
  document.getElementById('recalcScenariosBtn').addEventListener('click', () => recalcScenarios().catch(console.error));
  document.getElementById('saveSimBtn').addEventListener('click', () => saveSimulation().catch((e) => { console.error(e); alert('No se pudo guardar la simulación.'); }));
  document.getElementById('resetBtn').addEventListener('click', () => {
    Object.keys(CM.COST_LABELS).forEach((key) => { document.getElementById(`cost_${key}`).value = 0; });
  });

  document.querySelectorAll('input[name="priceMode"]').forEach((radio) => {
    radio.addEventListener('change', () => {
      document.getElementById('customPrice').disabled = document.querySelector('input[name="priceMode"]:checked').value !== 'personalizado';
    });
  });

  try {
    const current = await CM.get('/api/prices/national?coffee_type=pergamino_seco&period=1d');
    document.getElementById('currentPriceNote').innerHTML =
      `Precio actual de referencia: ${CM.cop(current.price_cop_per_kg)}/kg ${CM.demoBadge(current.is_demo)} — actualizado ${CM.dateLabel(current.last_updated)}`;
  } catch (e) { console.error(e); }
});
