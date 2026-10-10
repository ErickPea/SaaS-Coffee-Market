"""
Capa de orquestación del simulador de inversión: adapta los schemas
Pydantic de la API (y el acceso a BD/precios vía SQLAlchemy) a las
funciones puras de `app/services/investment_service.py`.

Se separó de `investment_service.py` a propósito: ese módulo debe poder
importarse y probarse sin Pydantic/SQLAlchemy/FastAPI instalados (ver su
docstring y `tests/test_investment_service.py`); este módulo sí depende de
ambos y es el que usa `app/api/investments.py`.
"""
from sqlalchemy.orm import Session

from app.models.price import CoffeeType, MarketType
from app.schemas.investment import (
    CapitalAnalysisOut, CostBreakdownOut, InvestmentInput, InvestmentResultOut,
    OpportunityAnalysisOut, ScenarioComparisonOut, ScenarioOut, ScenarioParamsIn,
    SensitivityPointOut, SensitivityResultOut,
)
from app.services import price_service
from app.services.investment_service import (
    InvestmentTotals, analyze_capital, build_scenario, calculate_totals,
    opportunity_scores, sensitivity_analysis,
)


def _resolve_price_per_kg(input: InvestmentInput, db: Session) -> tuple[float, str]:
    """Determina qué precio por kg usar: el actual (nacional, del tipo de
    café elegido) o el personalizado que haya escrito el usuario."""
    if not input.use_current_price:
        return input.custom_price_per_kg, "personalizado"

    proxy_note = ""
    if input.coffee_type != CoffeeType.PERGAMINO_SECO:
        # Sección 5: si no hay precio oficial en tiempo real para este tipo
        # específico, se usa la referencia de pergamino seco como proxy,
        # dejándolo explícito en vez de inventar un precio distinto.
        proxy_note = (
            " (proxy: referencia de pergamino seco — no hay precio oficial "
            "en tiempo real por tipo de café en Colombia)"
        )

    current = price_service.get_current_price(db, MarketType.NACIONAL, CoffeeType.PERGAMINO_SECO, period="1d")
    label = "actual" + proxy_note
    if current.is_demo:
        label += " [DEMO]"
    return current.price_cop_per_kg, label


def _totals_to_schema(totals: InvestmentTotals, price_source: str, hectares: float, currency) -> InvestmentResultOut:
    breakdown = CostBreakdownOut(
        by_category=totals.cost_by_category,
        iniciales=totals.cost_by_group["iniciales"],
        operativos=totals.cost_by_group["operativos"],
        produccion=totals.cost_by_group["produccion"],
        logisticos=totals.cost_by_group["logisticos"] + totals.cost_by_group.get("otros", 0.0),
        total=totals.total_investment,
    )
    return InvestmentResultOut(
        coffee_type=CoffeeType.PERGAMINO_SECO,  # se sobreescribe afuera si aplica
        hectares=hectares,
        production_per_hectare_kg=totals.total_production_kg / hectares if hectares else 0.0,
        total_production_kg=totals.total_production_kg,
        price_per_kg=totals.price_per_kg,
        price_currency=currency,
        price_source=price_source,
        cost_breakdown=breakdown,
        total_investment=totals.total_investment,
        total_income=totals.total_income,
        profit=totals.profit,
        roi_pct=round(totals.roi_pct, 2),
        margin_pct=round(totals.margin_pct, 2),
        break_even_kg=round(totals.break_even_kg, 2),
    )


class InvestmentCalculator:
    """Punto de entrada usado por `app/api/investments.py`."""

    def calculate(self, input: InvestmentInput, db: Session) -> InvestmentResultOut:
        price_per_kg_value, price_source = _resolve_price_per_kg(input, db)
        costs = input.costs.model_dump()

        totals = calculate_totals(input.hectares, input.production_per_hectare_kg, price_per_kg_value, costs)
        result = _totals_to_schema(totals, price_source, input.hectares, input.currency)
        result.coffee_type = input.coffee_type

        if input.capital_disponible is not None:
            capital = analyze_capital(input.capital_disponible, totals, input.hectares)
            result.capital_analysis = CapitalAnalysisOut(
                capital_disponible=capital.capital_disponible,
                inversion_requerida=capital.inversion_requerida,
                alcanza=capital.alcanza,
                faltante=capital.faltante,
                sobrante=capital.sobrante,
                hectareas_cubribles=round(capital.hectareas_cubribles, 2),
            )
        return result

    def scenarios(
        self, input: InvestmentInput, params: ScenarioParamsIn, db: Session,
    ) -> ScenarioComparisonOut:
        price_per_kg_value, price_source = _resolve_price_per_kg(input, db)
        costs = input.costs.model_dump()

        definitions = [
            ("pesimista", "Pesimista", params.pessimist_price_pct, params.pessimist_production_pct, params.pessimist_cost_pct),
            ("esperado", "Esperado", 0.0, 0.0, 0.0),
            ("optimista", "Optimista", params.optimist_price_pct, params.optimist_production_pct, params.optimist_cost_pct),
        ]
        scenario_outs = []
        for key, label, price_d, prod_d, cost_d in definitions:
            totals = build_scenario(
                input.hectares, input.production_per_hectare_kg, price_per_kg_value, costs,
                price_delta_pct=price_d, production_delta_pct=prod_d, cost_delta_pct=cost_d,
            )
            result = _totals_to_schema(totals, price_source, input.hectares, input.currency)
            result.coffee_type = input.coffee_type
            scenario_outs.append(ScenarioOut(name=key, label=label, result=result))

        return ScenarioComparisonOut(scenarios=scenario_outs, params_used=params)

    def sensitivity(self, input: InvestmentInput, db: Session) -> SensitivityResultOut:
        price_per_kg_value, _ = _resolve_price_per_kg(input, db)
        costs = input.costs.model_dump()

        raw = sensitivity_analysis(input.hectares, input.production_per_hectare_kg, price_per_kg_value, costs)
        points = [
            SensitivityPointOut(
                price_delta_pct=delta, price_per_kg=round(totals.price_per_kg, 2),
                total_income=round(totals.total_income, 2), profit=round(totals.profit, 2),
                roi_pct=round(totals.roi_pct, 2), break_even_kg=round(totals.break_even_kg, 2),
            )
            for delta, totals in raw
        ]
        return SensitivityResultOut(base_price_per_kg=round(price_per_kg_value, 2), points=points)

    def opportunity_analysis(self, input: InvestmentInput, db: Session) -> OpportunityAnalysisOut:
        price_per_kg_value, _ = _resolve_price_per_kg(input, db)
        costs = input.costs.model_dump()

        totals = calculate_totals(input.hectares, input.production_per_hectare_kg, price_per_kg_value, costs)
        raw_sensitivity = sensitivity_analysis(input.hectares, input.production_per_hectare_kg, price_per_kg_value, costs)
        volatility = price_service.price_volatility_coefficient(db, MarketType.NACIONAL, CoffeeType.PERGAMINO_SECO)

        scores = opportunity_scores(totals, raw_sensitivity, volatility)

        explanation = {
            "margin_score": (
                f"Igual al margen de utilidad calculado ({totals.margin_pct:.1f}%), acotado entre 0 y 100."
            ),
            "volatility_score": (
                "Basado en la variación histórica (1 año) del precio nacional de referencia: "
                f"coeficiente de variación = {volatility:.3f}." if volatility is not None
                else "No hay suficiente histórico de precio para calcularla; se asume volatilidad media (50)."
            ),
            "price_sensitivity_score": (
                "Qué tanto cambia la utilidad si el precio cae 10% frente al valor esperado "
                "(apalancamiento operativo: a mayor costo fijo frente al ingreso, mayor sensibilidad)."
            ),
            "opportunity_score": (
                "Promedio simple de: margen, (100 - volatilidad) y ROI, todos acotados a 0-100. "
                "Es una lectura compuesta de los otros tres puntajes, no una recomendación de inversión."
            ),
        }

        return OpportunityAnalysisOut(
            opportunity_score=scores["opportunity_score"],
            volatility_score=scores["volatility_score"],
            price_sensitivity_score=scores["price_sensitivity_score"],
            margin_score=scores["margin_score"],
            explanation=explanation,
        )
