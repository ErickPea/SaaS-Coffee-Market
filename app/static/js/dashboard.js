/* Dashboard principal. */
let priceChart = null;

async function loadStats() {
  const [national, international, trm] = await Promise.all([
    CM.get('/api/prices/national?period=30d'),
    CM.get('/api/prices/international?coffee_type=arabica&period=30d'),
    CM.get('/api/currency?period_days=30'),
  ]);

  const cards = document.querySelectorAll('#statGrid .stat-card');

  renderStatCard(cards[0], {
    label: 'Precio nacional (carga 125kg)',
    value: CM.cop(national.current_price),
    change: national.change_pct, trend: national.trend, isDemo: national.is_demo,
  });
  renderStatCard(cards[1], {
    label: 'Precio nacional (por kg)',
    value: CM.cop(national.price_cop_per_kg),
    change: national.change_pct, trend: national.trend, isDemo: national.is_demo,
  });
  renderStatCard(cards[2], {
    label: 'Arábica (Bolsa NY, USD/lb)',
    value: CM.usd(international.current_price),
    change: international.change_pct, trend: international.trend, isDemo: international.is_demo,
  });
  renderStatCard(cards[3], {
    label: 'TRM (USD → COP)',
    value: CM.cop(trm.usd_cop),
    change: trm.change_pct, trend: trm.change_pct > 0 ? 'alcista' : (trm.change_pct < 0 ? 'bajista' : 'estable'),
    isDemo: trm.is_demo,
  });

  const mostRecent = [national.last_updated, international.last_updated, trm.last_updated].sort().pop();
  document.getElementById('lastUpdatedBadge').innerHTML =
    `Última actualización: ${CM.dateLabel(mostRecent)} ${CM.demoBadge(national.is_demo || international.is_demo || trm.is_demo)}`;

  renderMarketSummary(national, international, trm);
  return { national, international, trm };
}

function renderStatCard(el, { label, value, change, trend, isDemo }) {
  const trendClass = trend === 'alcista' ? 'trend-alcista' : (trend === 'bajista' ? 'trend-bajista' : '');
  el.className = `stat-card ${trendClass}`;
  const changeClass = CM.changeClass(change);
  el.innerHTML = `
    <div class="stat-label">${label} ${isDemo ? '<span class="badge demo">Demo</span>' : ''}</div>
    <span class="stat-value">${value}</span>
    <div class="stat-change ${changeClass}">${CM.trendArrow(trend)} ${change !== null && change !== undefined ? CM.pct(change) : 'sin variación previa'}</div>
  `;
}

function renderMarketSummary(national, international, trm) {
  const dir = national.trend === 'alcista' ? 'subiendo' : (national.trend === 'bajista' ? 'bajando' : 'relativamente estable');
  const magnitude = national.change_pct !== null && national.change_pct !== undefined
    ? `(${CM.pct(national.change_pct)} frente al dato anterior)`
    : '';

  let text = `El precio nacional de referencia para café pergamino seco está ${dir} ${magnitude}. `;
  text += `Actualmente equivale a ${CM.cop(national.price_cop_per_kg)} por kilogramo. `;
  text += `En el mercado internacional, la arábica cotiza en ${CM.usd(international.current_price)} por libra en la Bolsa de Nueva York. `;
  text += `La TRM usada para las conversiones es de ${CM.cop(trm.usd_cop)} por dólar.`;

  if (national.is_demo || international.is_demo) {
    text += ' Algunos de estos valores provienen de datos de demostración porque la fuente en vivo no estuvo disponible — revisa las etiquetas "Demo" en cada tarjeta.';
  }
  document.getElementById('marketSummaryText').textContent = text;
}

async function loadChart(period) {
  const history = await CM.get(`/api/prices/history?market=nacional&period=${period}`);
  const labels = history.points.map(p => new Date(p.timestamp).toLocaleDateString('es-CO', { day: '2-digit', month: 'short' }));
  const data = history.points.map(p => p.price_cop_kg);

  document.getElementById('chartSourceNote').innerHTML =
    `Fuente: ${history.source} ${CM.demoBadge(history.is_demo)}`;

  if (priceChart) { priceChart.destroy(); }
  const ctx = document.getElementById('priceChart').getContext('2d');
  priceChart = new Chart(ctx, {
    type: 'line',
    data: {
      labels,
      datasets: [{
        label: 'Precio (COP/carga 125kg)',
        data: history.points.map(p => p.price_cop_kg * 125),
        borderColor: '#1F4D3A',
        backgroundColor: 'rgba(31,77,58,0.08)',
        fill: true,
        tension: 0.25,
        pointRadius: 0,
        borderWidth: 2,
      }],
    },
    options: {
      responsive: true,
      plugins: { legend: { display: false } },
      scales: {
        y: { ticks: { callback: (v) => CM.cop(v) } },
      },
    },
  });
}

document.addEventListener('DOMContentLoaded', async () => {
  try {
    await loadStats();
  } catch (e) {
    document.getElementById('marketSummaryText').textContent = 'No se pudieron cargar los precios. Intenta recargar la página.';
    console.error(e);
  }
  try {
    await loadChart('30d');
  } catch (e) { console.error(e); }

  document.getElementById('periodSelect').addEventListener('change', (e) => loadChart(e.target.value));
});
