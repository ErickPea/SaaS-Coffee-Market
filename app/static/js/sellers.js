/* Directorio de compradores. */
const TYPE_LABELS = {
  cooperativa: 'Cooperativa', comercializadora: 'Comercializadora', exportador: 'Exportador',
  trilladora: 'Trilladora', cafeteria: 'Cafetería', tostador: 'Tostador',
  comprador_especial: 'Comprador de café especial', mercado_local: 'Mercado local', gremio: 'Gremio',
};

function sellerCard(s) {
  const website = s.website ? `<a href="${s.website}" target="_blank" rel="noopener">${s.website.replace(/^https?:\/\//, '')}</a>` : 'No verificado públicamente';
  const contact = s.public_contact || 'Consultar directamente con la organización';
  return `
    <div class="seller-card">
      <h3>${s.name}</h3>
      <div class="seller-meta">${s.city ? s.city + ', ' : ''}${s.department}</div>
      <p>${s.description}</p>
      <p class="source-note">Sitio web: ${website}<br>Contacto: ${contact}<br>Fuente: ${s.source_note}</p>
      <div class="seller-tags">
        <span class="tag">${TYPE_LABELS[s.seller_type] || s.seller_type}</span>
        ${(s.coffee_types_bought || []).map(ct => `<span class="tag">${CM.COFFEE_TYPE_LABELS[ct] || ct}</span>`).join('')}
      </div>
    </div>`;
}

async function loadSellers() {
  const dept = document.getElementById('filterDept').value;
  const type = document.getElementById('filterType').value;
  const coffee = document.getElementById('filterCoffee').value;

  const params = new URLSearchParams();
  if (dept) params.set('department', dept);
  if (type) params.set('seller_type', type);
  if (coffee) params.set('coffee_type', coffee);

  const data = await CM.get(`/api/sellers?${params.toString()}`);

  const deptSelect = document.getElementById('filterDept');
  if (deptSelect.options.length <= 1) {
    data.departments_available.forEach(d => { deptSelect.innerHTML += `<option value="${d}">${d}</option>`; });
  }
  const typeSelect = document.getElementById('filterType');
  if (typeSelect.options.length <= 1) {
    data.types_available.forEach(t => { typeSelect.innerHTML += `<option value="${t}">${TYPE_LABELS[t] || t}</option>`; });
  }

  document.getElementById('resultCount').textContent = `${data.total} organización(es) encontradas`;
  const list = document.getElementById('sellerList');
  list.innerHTML = data.sellers.length
    ? data.sellers.map(sellerCard).join('')
    : '<div class="empty-state">No hay compradores que coincidan con estos filtros.</div>';
}

document.addEventListener('DOMContentLoaded', () => {
  loadSellers().catch(console.error);
  ['filterDept', 'filterType', 'filterCoffee'].forEach(id =>
    document.getElementById(id).addEventListener('change', () => loadSellers().catch(console.error)));
});
