/* Alertas de precio. */
const PRODUCT_UNITS = { arabica: 'USD/lb', robusta: 'USD/ton', nacional: 'COP/carga' };
const PRODUCT_LABELS = { arabica: 'Arábica', robusta: 'Robusta', nacional: 'Café nacional' };
const CONDITION_LABELS = {
  mayor_que: 'mayor que', menor_que: 'menor que',
  mayor_o_igual: 'mayor o igual que', menor_o_igual: 'menor o igual que',
};
const STATUS_LABELS = { activa: 'Activa', disparada: 'Disparada', desactivada: 'Desactivada' };

function fmtThreshold(value, product) {
  return product === 'nacional' ? CM.cop(value) : `$${CM.num(value, 2)}`;
}

function alertCard(a) {
  const statusClass = a.status === 'disparada' ? 'trend-bajista' : (a.status === 'activa' ? 'trend-alcista' : '');
  const badgeStyle = a.status === 'disparada' ? 'demo' : (a.status === 'desactivada' ? '' : 'live');
  let triggeredInfo = '';
  if (a.status === 'disparada' && a.triggered_at) {
    triggeredInfo = `
      <p class="source-note">
        Se disparó el ${CM.dateLabel(a.triggered_at)} con un precio de ${fmtThreshold(a.triggered_price, a.product)}
        ${CM.demoBadge(a.triggered_is_demo)}
      </p>`;
  }
  let lastChecked = a.last_checked_at
    ? `<p class="source-note">Última evaluación: ${CM.dateLabel(a.last_checked_at)} — precio visto: ${fmtThreshold(a.last_checked_price, a.product)} ${CM.demoBadge(a.last_checked_is_demo)}</p>`
    : '<p class="source-note">Todavía no se ha evaluado.</p>';

  return `
    <div class="stat-card ${statusClass}" style="margin-bottom:12px;">
      <div class="topbar" style="margin-bottom:6px;">
        <div>
          <h3 style="margin-bottom:2px;">${a.name}</h3>
          <div class="seller-meta">${PRODUCT_LABELS[a.product]} ${CONDITION_LABELS[a.condition]} ${fmtThreshold(a.threshold, a.product)} <span class="badge ${badgeStyle}">${STATUS_LABELS[a.status]}</span></div>
        </div>
        <div style="display:flex; gap:6px; flex-wrap:wrap;">
          <button class="btn secondary" onclick="toggleAlert(${a.id})">${a.status === 'desactivada' ? 'Activar' : (a.status === 'disparada' ? 'Reactivar' : 'Desactivar')}</button>
          <button class="btn secondary" onclick="startEdit(${a.id})">Editar</button>
          <button class="btn secondary" onclick="removeAlert(${a.id})">Eliminar</button>
        </div>
      </div>
      ${lastChecked}
      ${triggeredInfo}
    </div>`;
}

let allAlerts = [];

async function loadAlerts() {
  allAlerts = await CM.get('/api/alerts');
  const container = document.getElementById('alertsList');
  container.innerHTML = allAlerts.length
    ? allAlerts.map(alertCard).join('')
    : '<div class="empty-state">No tienes alertas creadas todavía.</div>';
}

function updateUnitHint() {
  document.getElementById('unitHint').textContent = PRODUCT_UNITS[document.getElementById('alertProduct').value];
}

function startEdit(id) {
  const alert_ = allAlerts.find(a => a.id === id);
  if (!alert_) return;
  document.getElementById('editingId').value = id;
  document.getElementById('alertName').value = alert_.name;
  document.getElementById('alertProduct').value = alert_.product;
  document.getElementById('alertCondition').value = alert_.condition;
  document.getElementById('alertThreshold').value = alert_.threshold;
  updateUnitHint();
  document.getElementById('formTitle').textContent = `Editando: ${alert_.name}`;
  document.getElementById('alertSubmitBtn').textContent = 'Guardar cambios';
  document.getElementById('cancelEditBtn').style.display = '';
  document.getElementById('alertForm').scrollIntoView({ behavior: 'smooth' });
}

function cancelEdit() {
  document.getElementById('editingId').value = '';
  document.getElementById('alertForm').reset();
  updateUnitHint();
  document.getElementById('formTitle').textContent = 'Nueva alerta';
  document.getElementById('alertSubmitBtn').textContent = 'Crear alerta';
  document.getElementById('cancelEditBtn').style.display = 'none';
}

async function submitAlertForm(e) {
  e.preventDefault();
  const editingId = document.getElementById('editingId').value;
  const payload = {
    name: document.getElementById('alertName').value.trim(),
    product: document.getElementById('alertProduct').value,
    condition: document.getElementById('alertCondition').value,
    threshold: parseFloat(document.getElementById('alertThreshold').value),
  };
  if (!payload.name) { alert('Ponle un nombre a la alerta'); return; }
  if (!(payload.threshold > 0)) { alert('El umbral debe ser mayor que 0'); return; }

  try {
    if (editingId) {
      const res = await fetch(`/api/alerts/${editingId}`, {
        method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload),
      });
      if (!res.ok) throw new Error('No se pudo actualizar');
    } else {
      await CM.post('/api/alerts', payload);
    }
    cancelEdit();
    await loadAlerts();
  } catch (err) {
    console.error(err);
    alert('No se pudo guardar la alerta.');
  }
}

async function toggleAlert(id) {
  try {
    await fetch(`/api/alerts/${id}/toggle`, { method: 'PATCH' });
    await loadAlerts();
  } catch (err) { console.error(err); }
}

async function removeAlert(id) {
  if (!confirm('¿Eliminar esta alerta? Esta acción no se puede deshacer.')) return;
  try {
    await fetch(`/api/alerts/${id}`, { method: 'DELETE' });
    await loadAlerts();
  } catch (err) { console.error(err); }
}

async function evaluateNow() {
  const btn = document.getElementById('evaluateNowBtn');
  btn.disabled = true; btn.textContent = 'Evaluando…';
  try {
    const triggered = await CM.post('/api/alerts/evaluate', {});
    await loadAlerts();
    if (triggered.length) {
      alert(`Se dispararon ${triggered.length} alerta(s): ${triggered.map(a => a.name).join(', ')}`);
    } else {
      alert('Ninguna alerta se disparó con los precios actuales.');
    }
  } catch (err) {
    console.error(err);
    alert('No se pudo evaluar las alertas.');
  } finally {
    btn.disabled = false; btn.textContent = 'Evaluar ahora';
  }
}

document.addEventListener('DOMContentLoaded', () => {
  loadAlerts().catch(console.error);
  document.getElementById('alertProduct').addEventListener('change', updateUnitHint);
  document.getElementById('alertForm').addEventListener('submit', submitAlertForm);
  document.getElementById('cancelEditBtn').addEventListener('click', cancelEdit);
  document.getElementById('evaluateNowBtn').addEventListener('click', evaluateNow);
});
