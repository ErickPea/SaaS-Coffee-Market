/* Utilidades compartidas por todas las páginas. */

const CM = {
  async get(path) {
    const res = await fetch(path);
    if (!res.ok) {
      const body = await res.text();
      throw new Error(`Error ${res.status} en ${path}: ${body}`);
    }
    return res.json();
  },

  async post(path, body) {
    const res = await fetch(path, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    if (!res.ok) {
      const errBody = await res.text();
      throw new Error(`Error ${res.status} en ${path}: ${errBody}`);
    }
    return res.json();
  },

  cop(value) {
    if (value === null || value === undefined || Number.isNaN(value)) return '—';
    return new Intl.NumberFormat('es-CO', { style: 'currency', currency: 'COP', maximumFractionDigits: 0 }).format(value);
  },

  usd(value) {
    if (value === null || value === undefined || Number.isNaN(value)) return '—';
    return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 2 }).format(value);
  },

  num(value, decimals = 0) {
    if (value === null || value === undefined || Number.isNaN(value)) return '—';
    return new Intl.NumberFormat('es-CO', { minimumFractionDigits: decimals, maximumFractionDigits: decimals }).format(value);
  },

  pct(value, decimals = 2) {
    if (value === null || value === undefined || Number.isNaN(value)) return '—';
    const sign = value > 0 ? '+' : '';
    return `${sign}${this.num(value, decimals)}%`;
  },

  dateLabel(iso) {
    try {
      const d = new Date(iso);
      return d.toLocaleString('es-CO', { day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' });
    } catch (e) { return iso; }
  },

  trendArrow(trend) {
    if (trend === 'alcista') return '▲';
    if (trend === 'bajista') return '▼';
    return '→';
  },

  changeClass(value) {
    if (value === null || value === undefined) return 'flat';
    if (value > 0) return 'up';
    if (value < 0) return 'down';
    return 'flat';
  },

  demoBadge(isDemo) {
    return isDemo
      ? '<span class="badge demo">Demo / histórico</span>'
      : '<span class="badge live">En vivo</span>';
  },

  COFFEE_TYPE_LABELS: {
    pergamino_seco: 'Café pergamino seco',
    verde: 'Café verde',
    tostado: 'Café tostado',
    especial: 'Café especial',
    arabica: 'Arábica',
    robusta: 'Robusta',
    otro: 'Otro',
  },

  COST_LABELS: {
    preparacion_terreno: 'Preparación del terreno',
    plantulas: 'Plántulas',
    fertilizantes: 'Fertilizantes',
    mano_de_obra: 'Mano de obra',
    control_plagas: 'Control de plagas',
    herramientas: 'Herramientas',
    transporte: 'Transporte',
    cosecha: 'Cosecha',
    procesamiento: 'Procesamiento',
    secado: 'Secado',
    almacenamiento: 'Almacenamiento',
    administracion: 'Administración',
    otros: 'Otros',
  },
};
