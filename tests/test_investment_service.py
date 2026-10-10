"""
Pruebas del motor de cálculo puro (app/services/investment_service.py,
funciones calculate_totals / analyze_capital / build_scenario /
sensitivity_analysis / opportunity_scores). No requieren FastAPI,
SQLAlchemy ni Pydantic instalados: son las funciones más críticas de toda
la app y se prueban de forma completamente aislada.
"""
import pytest

from app.services.investment_service import (
    analyze_capital, build_scenario, calculate_totals, opportunity_scores,
    sensitivity_analysis,
)

HECTARES = 5
PROD_HA = 2000
PRICE = 11_200
COSTS = {
    "preparacion_terreno": 2_000_000, "plantulas": 3_000_000, "fertilizantes": 8_000_000,
    "mano_de_obra": 15_000_000, "control_plagas": 2_000_000, "herramientas": 1_500_000,
    "transporte": 1_000_000, "cosecha": 6_000_000, "procesamiento": 2_000_000,
    "secado": 1_000_000, "almacenamiento": 500_000, "administracion": 1_500_000, "otros": 500_000,
}


@pytest.fixture
def base_totals():
    return calculate_totals(HECTARES, PROD_HA, PRICE, COSTS)


def test_produccion_total(base_totals):
    assert base_totals.total_production_kg == HECTARES * PROD_HA


def test_inversion_total_es_suma_de_costos(base_totals):
    assert base_totals.total_investment == sum(COSTS.values())


def test_ingresos(base_totals):
    assert base_totals.total_income == base_totals.total_production_kg * PRICE


def test_utilidad(base_totals):
    assert base_totals.profit == pytest.approx(base_totals.total_income - base_totals.total_investment)


def test_roi(base_totals):
    esperado = base_totals.profit / base_totals.total_investment * 100
    assert base_totals.roi_pct == pytest.approx(esperado)


def test_margen(base_totals):
    esperado = base_totals.profit / base_totals.total_income * 100
    assert base_totals.margin_pct == pytest.approx(esperado)


def test_punto_de_equilibrio_reproduce_la_inversion(base_totals):
    """Vender exactamente `break_even_kg` al precio dado debe reproducir la
    inversión total (utilidad = 0), que es la definición de equilibrio."""
    assert base_totals.break_even_kg * PRICE == pytest.approx(base_totals.total_investment)


def test_grupos_de_costos_suman_el_total(base_totals):
    assert sum(base_totals.cost_by_group.values()) == pytest.approx(base_totals.total_investment)


def test_hectareas_cero_lanza_error():
    with pytest.raises(ValueError):
        calculate_totals(0, PROD_HA, PRICE, COSTS)


def test_costo_negativo_lanza_error():
    bad_costs = dict(COSTS)
    bad_costs["otros"] = -1
    with pytest.raises(ValueError):
        calculate_totals(HECTARES, PROD_HA, PRICE, bad_costs)


def test_inversion_cero_no_lanza_division_por_cero():
    totals = calculate_totals(HECTARES, PROD_HA, PRICE, {k: 0 for k in COSTS})
    assert totals.total_investment == 0
    assert totals.roi_pct == 0.0  # no se propaga ZeroDivisionError


class TestCapital:
    def test_capital_suficiente(self, base_totals):
        analysis = analyze_capital(100_000_000, base_totals, HECTARES)
        assert analysis.alcanza is True
        assert analysis.faltante is None
        assert analysis.sobrante == pytest.approx(100_000_000 - base_totals.total_investment)

    def test_capital_insuficiente(self, base_totals):
        analysis = analyze_capital(10_000_000, base_totals, HECTARES)
        assert analysis.alcanza is False
        assert analysis.sobrante is None
        assert analysis.faltante == pytest.approx(base_totals.total_investment - 10_000_000)

    def test_hectareas_cubribles_es_consistente(self, base_totals):
        analysis = analyze_capital(10_000_000, base_totals, HECTARES)
        costo_por_ha = base_totals.total_investment / HECTARES
        assert analysis.hectareas_cubribles == pytest.approx(10_000_000 / costo_por_ha)


class TestEscenarios:
    def test_pesimista_reduce_ingresos_y_utilidad(self, base_totals):
        pesimista = build_scenario(HECTARES, PROD_HA, PRICE, COSTS, price_delta_pct=-15, production_delta_pct=-10, cost_delta_pct=10)
        assert pesimista.total_income < base_totals.total_income
        assert pesimista.profit < base_totals.profit
        assert pesimista.total_investment > base_totals.total_investment

    def test_optimista_aumenta_ingresos_y_utilidad(self, base_totals):
        optimista = build_scenario(HECTARES, PROD_HA, PRICE, COSTS, price_delta_pct=15, production_delta_pct=10, cost_delta_pct=0)
        assert optimista.total_income > base_totals.total_income
        assert optimista.profit > base_totals.profit
        assert optimista.total_investment == pytest.approx(base_totals.total_investment)

    def test_escenario_sin_variacion_reproduce_el_base(self, base_totals):
        neutro = build_scenario(HECTARES, PROD_HA, PRICE, COSTS)
        assert neutro.profit == pytest.approx(base_totals.profit)


class TestSensibilidad:
    def test_utilidad_crece_monotonamente_con_el_precio(self):
        sens = sensitivity_analysis(HECTARES, PROD_HA, PRICE, COSTS)
        utilidades = [totals.profit for _, totals in sens]
        assert utilidades == sorted(utilidades)

    def test_delta_cero_coincide_con_el_caso_base(self, base_totals):
        sens = sensitivity_analysis(HECTARES, PROD_HA, PRICE, COSTS)
        delta0 = dict(sens)[0]
        assert delta0.profit == pytest.approx(base_totals.profit)


class TestOportunidad:
    def test_puntajes_entre_0_y_100(self, base_totals):
        sens = sensitivity_analysis(HECTARES, PROD_HA, PRICE, COSTS)
        scores = opportunity_scores(base_totals, sens, price_volatility_coefficient=0.2)
        for value in scores.values():
            assert 0 <= value <= 100

    def test_sin_volatilidad_historica_usa_valor_medio(self, base_totals):
        sens = sensitivity_analysis(HECTARES, PROD_HA, PRICE, COSTS)
        scores = opportunity_scores(base_totals, sens, price_volatility_coefficient=None)
        assert scores["volatility_score"] == 50.0
