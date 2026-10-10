"""
Motor de cálculo puro del simulador de inversión (sección 11 del brief).

Deliberadamente NO importa Pydantic, SQLAlchemy ni FastAPI: son funciones de
Python puro sobre `float`/`dict`, fáciles de probar unitariamente (ver
`tests/test_investment_service.py`) y de razonar sin efectos secundarios.
La capa que sí conoce Pydantic/SQLAlchemy vive en
`app/services/investment_orchestrator.py` y simplemente adapta los schemas
de la API a estas funciones.

Fórmulas (idénticas a las de la sección 11 del brief):
    Producción total   = hectáreas × producción por hectárea
    Inversión total     = suma de todos los costos
    Ingresos             = producción total × precio de venta por kg
    Utilidad             = ingresos − inversión total
    ROI (%)               = (utilidad / inversión total) × 100
    Margen (%)            = (utilidad / ingresos) × 100
    Punto de equilibrio   = inversión total / precio de venta por kg
"""
from dataclasses import dataclass, field

# Agrupación conceptual de las 13 categorías de costo (sección 10) en los 4
# bloques que pide la sección 11. Es solo para presentación — el total
# siempre es la suma de las 13 categorías, sin importar la agrupación.
COST_GROUPS: dict[str, list[str]] = {
    "iniciales": ["preparacion_terreno", "plantulas", "herramientas"],
    "operativos": ["fertilizantes", "mano_de_obra", "control_plagas", "administracion"],
    "produccion": ["cosecha", "procesamiento", "secado"],
    "logisticos": ["transporte", "almacenamiento"],
}
ALL_COST_CATEGORIES = [c for group in COST_GROUPS.values() for c in group] + ["otros"]


@dataclass
class InvestmentTotals:
    total_production_kg: float
    price_per_kg: float
    cost_by_category: dict[str, float]
    cost_by_group: dict[str, float]
    total_investment: float
    total_income: float
    profit: float
    roi_pct: float
    margin_pct: float
    break_even_kg: float


@dataclass
class CapitalAnalysis:
    capital_disponible: float
    inversion_requerida: float
    alcanza: bool
    faltante: float | None
    sobrante: float | None
    hectareas_cubribles: float


def calculate_totals(
    hectares: float,
    production_per_hectare_kg: float,
    price_per_kg: float,
    costs: dict[str, float],
) -> InvestmentTotals:
    """Calcula producción, ingresos, utilidad, ROI, margen y punto de
    equilibrio para un único escenario. No lanza excepciones por división
    entre cero: si inversión o ingresos son 0, ROI/margen se reportan como
    0.0 en vez de propagar un error, ya que 0 costos o 0 ingresos son casos
    de borde legítimos que el usuario puede estar explorando a propósito."""
    if hectares <= 0:
        raise ValueError("Las hectáreas deben ser mayores que 0")
    if production_per_hectare_kg <= 0:
        raise ValueError("La producción por hectárea debe ser mayor que 0")
    if price_per_kg <= 0:
        raise ValueError("El precio por kg debe ser mayor que 0")
    if any(v < 0 for v in costs.values()):
        raise ValueError("Ningún costo puede ser negativo")

    total_production_kg = hectares * production_per_hectare_kg

    cost_by_category = {cat: float(costs.get(cat, 0.0)) for cat in ALL_COST_CATEGORIES}
    total_investment = sum(cost_by_category.values())

    cost_by_group = {
        group: sum(cost_by_category[c] for c in cats)
        for group, cats in COST_GROUPS.items()
    }
    cost_by_group["otros"] = cost_by_category["otros"]

    total_income = total_production_kg * price_per_kg
    profit = total_income - total_investment

    roi_pct = (profit / total_investment * 100) if total_investment > 0 else 0.0
    margin_pct = (profit / total_income * 100) if total_income > 0 else 0.0
    break_even_kg = (total_investment / price_per_kg) if price_per_kg > 0 else 0.0

    return InvestmentTotals(
        total_production_kg=total_production_kg,
        price_per_kg=price_per_kg,
        cost_by_category=cost_by_category,
        cost_by_group=cost_by_group,
        total_investment=total_investment,
        total_income=total_income,
        profit=profit,
        roi_pct=roi_pct,
        margin_pct=margin_pct,
        break_even_kg=break_even_kg,
    )


def analyze_capital(capital_disponible: float, base: InvestmentTotals, hectares: float) -> CapitalAnalysis:
    """Sección 14: ¿el capital disponible alcanza? ¿cuántas hectáreas cubre?"""
    if capital_disponible < 0:
        raise ValueError("El capital disponible no puede ser negativo")

    alcanza = capital_disponible >= base.total_investment
    cost_per_hectare = base.total_investment / hectares if hectares > 0 else 0.0
    hectareas_cubribles = (capital_disponible / cost_per_hectare) if cost_per_hectare > 0 else 0.0

    return CapitalAnalysis(
        capital_disponible=capital_disponible,
        inversion_requerida=base.total_investment,
        alcanza=alcanza,
        faltante=None if alcanza else (base.total_investment - capital_disponible),
        sobrante=(capital_disponible - base.total_investment) if alcanza else None,
        hectareas_cubribles=hectareas_cubribles,
    )


def build_scenario(
    hectares: float,
    production_per_hectare_kg: float,
    price_per_kg: float,
    costs: dict[str, float],
    price_delta_pct: float = 0.0,
    production_delta_pct: float = 0.0,
    cost_delta_pct: float = 0.0,
) -> InvestmentTotals:
    """Aplica variaciones porcentuales (escenarios pesimista/optimista, o un
    punto del análisis de sensibilidad) sobre los valores base y recalcula
    todo con `calculate_totals`, para no duplicar la lógica de cálculo."""
    adjusted_price = price_per_kg * (1 + price_delta_pct / 100)
    adjusted_production = production_per_hectare_kg * (1 + production_delta_pct / 100)
    adjusted_costs = {k: v * (1 + cost_delta_pct / 100) for k, v in costs.items()}
    return calculate_totals(hectares, adjusted_production, adjusted_price, adjusted_costs)


DEFAULT_SENSITIVITY_DELTAS = [-30, -20, -10, 0, 10, 20, 30]


def sensitivity_analysis(
    hectares: float,
    production_per_hectare_kg: float,
    price_per_kg: float,
    costs: dict[str, float],
    price_deltas_pct: list[float] = DEFAULT_SENSITIVITY_DELTAS,
) -> list[tuple[float, InvestmentTotals]]:
    """Sección 13: ¿qué pasa si el precio cambia?, con producción y costos
    fijos en su valor base (para aislar el efecto del precio)."""
    return [
        (delta, build_scenario(hectares, production_per_hectare_kg, price_per_kg, costs, price_delta_pct=delta))
        for delta in price_deltas_pct
    ]


def opportunity_scores(
    base: InvestmentTotals,
    sensitivity: list[tuple[float, InvestmentTotals]],
    price_volatility_coefficient: float | None,
) -> dict[str, float]:
    """
    Sección 15: puntajes 0-100 transparentes y explicables (NO una caja
    negra). Cada puntaje se documenta también en el texto de `explanation`
    que arma `investment_orchestrator.py`.

    - margin_score: el margen de utilidad tal cual, acotado a [0, 100].
    - volatility_score: coeficiente de variación (desviación estándar /
      promedio) del precio histórico usado, escalado a [0, 100]. Si no hay
      histórico suficiente, se asume volatilidad media (50) y se marca en
      la explicación.
    - price_sensitivity_score: qué tanto se mueve la utilidad ante una
      caída del 10% en el precio, relativo a la utilidad base (apalancamiento
      operativo). Se acota a [0, 100].
    - opportunity_score: promedio simple de margin_score, (100 - volatility_score)
      y un ROI normalizado — nunca una recomendación, solo una lectura
      compuesta y documentada de los otros tres puntajes.
    """
    margin_score = max(0.0, min(100.0, base.margin_pct))

    if price_volatility_coefficient is None:
        volatility_score = 50.0
    else:
        # Un coeficiente de variación de 0.30 (30%) o más se trata como
        # "muy volátil" (100); se escala linealmente hasta ahí.
        volatility_score = max(0.0, min(100.0, (price_volatility_coefficient / 0.30) * 100))

    minus_10 = next((totals for delta, totals in sensitivity if delta == -10), None)
    if minus_10 is not None and base.profit != 0:
        swing_pct = abs((minus_10.profit - base.profit) / abs(base.profit)) * 100
        price_sensitivity_score = max(0.0, min(100.0, swing_pct))
    else:
        price_sensitivity_score = 50.0

    roi_score = max(0.0, min(100.0, base.roi_pct))
    opportunity_score = (margin_score + (100 - volatility_score) + roi_score) / 3

    return {
        "opportunity_score": round(opportunity_score, 1),
        "volatility_score": round(volatility_score, 1),
        "price_sensitivity_score": round(price_sensitivity_score, 1),
        "margin_score": round(margin_score, 1),
    }
