/* Historial de simulaciones guardadas: listar, editar (recalcular), eliminar. */
let editingSimId = null;

function simRow(s) {
  return `
    <div class="card" style="margin-bottom:12px;">
      <div class="topbar" style="margin-bottom:6px;">
        <div>
          <h3 style="margin-bottom:2px;">${s.name}</h3>
          <div class="source-note">${CM.dateLabel(s.created_at)} · ${CM.COFFEE_TYPE_LABELS[s.coffee_type] || s.coffee_type} · ${CM.num(s.hectares, 2)} ha</div>
        </div>
        <div style="display:flex; gap:8px; flex-wrap:wrap;">
          <button class="btn secondary" onclick="startEditSimulation(${s.id})">Editar</button>
          <button class="btn secondary" onclick="deleteSimulation(${s.id})">Eliminar</button>
          <a class="btn secondary" href="/api/simulations/${s.id}/export/csv">CSV</a>
          <a class="btn secondary" href="/api/simulations/${s.id}/export/xlsx">Excel</a>
          <a class="btn secondary" href="/api/simulations/${s.id}/export/pdf">PDF</a>
        </div>
      </div>
      <div class="stat-grid" style="margin-bottom:0;">
        <div class="stat-card"><div class="stat-label">Inversión</div><span class="stat-value" style="font-size:1.1rem;">${s.total_investment != null ? CM.cop(s.total_investment) : '—'}</span></div>
        <div class="stat-card"><div class="stat-label">Utilidad</div><span class="stat-value" style="font-size:1.1rem;">${s.profit != null ? CM.cop(s.profit) : '—'}</span></div>
        <div class="stat-card"><div class="stat-label">ROI</div><span class="stat-value" style="font-size:1.1rem;">${s.roi_pct != null ? CM.pct(s.roi_pct) : '—'}</span></div>
      </div>
    </div>`;
}

async function loadSimulations() {
  const sims = await CM.get('/api/simulations');
  const container = document.getElementById('simList');
  container.innerHTML = sims.length
    ? sims.map(simRow).join('')
    : '<div class="empty-state">Todavía no has guardado ninguna simulación.<br><br><a class="btn" href="/simulador">Crear la primera</a></div>';
}

function buildEditCostFields(costs) {
  const container = document.getElementById('editCostFields');
  container.innerHTML = '';
  Object.entries(CM.COST_LABELS).forEach(([key, label]) => {
    const div = document.createElement('div');
    div.className = 'field';
    const value = costs[key] || 0;
    div.innerHTML = `<label for="editcost_${key}">${label}</label><input type="number" id="editcost_${key}" min="0" step="any" value="${value}">`;
    container.appendChild(div);
  });
}

function readEditCosts() {
  const costs = {};
  Object.keys(CM.COST_LABELS).forEach((key) => {
    costs[key] = parseFloat(document.getElementById(`editcost_${key}`).value) || 0;
  });
  return costs;
}

async function startEditSimulation(id) {
  const sim = await CM.get(`/api/simulations/${id}`);
  editingSimId = id;

  document.getElementById('editTitle').textContent = `Editando: ${sim.name}`;
  document.getElementById('editName').value = sim.name;
  document.getElementById('editHectares').value = sim.hectares;
  document.getElementById('editProdHa').value = sim.production_per_hectare_kg;
  document.getElementById('editCapital').value = sim.capital_disponible ?? '';
  document.getElementById('editNotes').value = sim.notes ?? '';
  document.getElementById('editUseCurrentPrice').checked = false;
  document.getElementById('editPriceNote').textContent =
    `Precio guardado originalmente: ${CM.cop(sim.price_used_per_kg)}/kg (${sim.price_source}). Si no marcas la casilla, se reutiliza este valor al recalcular.`;
  buildEditCostFields(sim.costs_by_category || {});

  document.getElementById('editPanel').style.display = '';
  document.getElementById('editPanel').scrollIntoView({ behavior: 'smooth' });
}

function cancelEditSimulation() {
  editingSimId = null;
  document.getElementById('editPanel').style.display = 'none';
}

async function submitEditSimulation(e) {
  e.preventDefault();
  if (!editingSimId) return;

  const original = await CM.get(`/api/simulations/${editingSimId}`);
  const useCurrentPrice = document.getElementById('editUseCurrentPrice').checked;
  const costs = readEditCosts();

  const investmentPayload = {
    coffee_type: original.coffee_type,
    hectares: parseFloat(document.getElementById('editHectares').value),
    production_per_hectare_kg: parseFloat(document.getElementById('editProdHa').value),
    use_current_price: useCurrentPrice,
    currency: 'COP',
    costs,
  };
  if (!useCurrentPrice) investmentPayload.custom_price_per_kg = original.price_used_per_kg;
  const capitalVal = document.getElementById('editCapital').value;
  if (capitalVal) investmentPayload.capital_disponible = parseFloat(capitalVal);

  const submitBtn = document.querySelector('#editForm button[type="submit"]');
  submitBtn.disabled = true; submitBtn.textContent = 'Recalculando…';

  try {
    const [result, scenarios] = await Promise.all([
      CM.post('/api/investment/calculate', investmentPayload),
      CM.post('/api/investment/scenarios', { payload: investmentPayload, params: original.scenario_params || {} }),
    ]);

    const patchBody = {
      name: document.getElementById('editName').value.trim(),
      hectares: investmentPayload.hectares,
      production_per_hectare_kg: investmentPayload.production_per_hectare_kg,
      price_used_per_kg: result.price_per_kg,
      price_source: result.price_source,
      capital_disponible: investmentPayload.capital_disponible ?? null,
      costs,
      notes: document.getElementById('editNotes').value.trim() || null,
      results: {
        total_investment: result.total_investment,
        total_production_kg: result.total_production_kg,
        total_income: result.total_income,
        profit: result.profit,
        roi_pct: result.roi_pct,
        margin_pct: result.margin_pct,
        break_even_kg: result.break_even_kg,
        scenarios: scenarios.scenarios.map(s => ({
          label: s.label, total_investment: s.result.total_investment,
          total_income: s.result.total_income, profit: s.result.profit, roi_pct: s.result.roi_pct,
        })),
      },
    };

    const res = await fetch(`/api/simulations/${editingSimId}`, {
      method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(patchBody),
    });
    if (!res.ok) throw new Error(await res.text());

    cancelEditSimulation();
    await loadSimulations();
  } catch (err) {
    console.error(err);
    alert('No se pudo recalcular/guardar la simulación.');
  } finally {
    submitBtn.disabled = false; submitBtn.textContent = 'Recalcular y guardar';
  }
}

async function deleteSimulation(id) {
  if (!confirm('¿Eliminar esta simulación? Esta acción no se puede deshacer.')) return;
  try {
    const res = await fetch(`/api/simulations/${id}`, { method: 'DELETE' });
    if (!res.ok && res.status !== 204) throw new Error('No se pudo eliminar');
    if (editingSimId === id) cancelEditSimulation();
    await loadSimulations();
  } catch (err) {
    console.error(err);
    alert('No se pudo eliminar la simulación.');
  }
}

document.addEventListener('DOMContentLoaded', () => {
  loadSimulations().catch(console.error);
  document.getElementById('editForm').addEventListener('submit', submitEditSimulation);
  document.getElementById('cancelEditSimBtn').addEventListener('click', cancelEditSimulation);
});
