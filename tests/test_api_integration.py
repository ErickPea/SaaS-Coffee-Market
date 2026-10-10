"""
Pruebas de integración de la API con `fastapi.testclient.TestClient`.

NOTA: estas pruebas requieren fastapi/sqlalchemy/pydantic realmente
instalados (no las cubre el shim de conftest.py, que solo alcanza para
unit-testear providers). No se pudieron ejecutar en el entorno de
desarrollo sin red usado para construir este proyecto — están escritas
para pasar en cuanto corras `pytest` con `requirements.txt` instalado.

No dependen de red real: los providers caen a datos demo automáticamente
si no hay conexión, así que estas pruebas validan la API (rutas,
validación, códigos HTTP, persistencia) sin importar si hay internet.
"""
import os

import pytest


@pytest.fixture(scope="module")
def client(tmp_path_factory):
    """Cliente de pruebas con una base de datos SQLite temporal y aislada
    (nunca toca data/coffee_market.db). Se fuerza DATABASE_URL ANTES de
    importar app.main, para que app/core/database.py cree el engine ya
    apuntando al archivo temporal."""
    db_dir = tmp_path_factory.mktemp("cm_test_db")
    os.environ["DATABASE_URL"] = f"sqlite:///{db_dir / 'test.db'}"

    from app.core.config import get_settings
    get_settings.cache_clear()

    from fastapi.testclient import TestClient
    from app.main import app

    with TestClient(app) as c:
        yield c


# ------------------------------------------------------------- Prices ----
class TestPrices:
    def test_precio_actual_nacional(self, client):
        resp = client.get("/api/prices/current?market=nacional&coffee_type=pergamino_seco&period=30d")
        assert resp.status_code == 200
        data = resp.json()
        assert data["market"] == "nacional"
        assert data["current_price"] > 0
        assert "is_demo" in data and isinstance(data["is_demo"], bool)

    def test_precio_actual_internacional(self, client):
        resp = client.get("/api/prices/current?market=internacional&coffee_type=arabica&period=30d")
        assert resp.status_code == 200
        assert resp.json()["current_price"] > 0

    def test_historico_devuelve_puntos(self, client):
        resp = client.get("/api/prices/history?market=nacional&period=30d")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["points"]) > 0
        assert all(p["price_cop_kg"] > 0 for p in data["points"])

    def test_periodo_invalido_da_400(self, client):
        resp = client.get("/api/prices/current?market=nacional&period=13meses")
        assert resp.status_code == 400

    def test_precio_manual_nacional(self, client):
        resp = client.post("/api/prices/national/manual?price_cop_per_carga=2300000")
        assert resp.status_code == 200
        data = resp.json()
        assert data["current_price"] == 2300000
        assert data["is_demo"] is False

    def test_atajo_nacional_e_internacional(self, client):
        assert client.get("/api/prices/national").status_code == 200
        assert client.get("/api/prices/international").status_code == 200


# ------------------------------------------------------------ Markets ----
class TestMarkets:
    def test_comparar_mercados(self, client):
        resp = client.get("/api/markets/compare?period=30d")
        assert resp.status_code == 200
        data = resp.json()
        assert "difference_cop_kg" in data
        assert data["national"]["current_price"] > 0
        assert data["international"]["current_price"] > 0

    def test_conversor_unidades_carga_a_kg(self, client):
        resp = client.get("/api/markets/units/convert?amount=1&from_unit=carga&to_unit=kg")
        assert resp.status_code == 200
        assert resp.json()["result"] == 125.0

    def test_listado_unidades(self, client):
        resp = client.get("/api/markets/units")
        assert resp.status_code == 200
        assert len(resp.json()["units"]) == 6


# ----------------------------------------------------------- Currency ----
class TestCurrency:
    def test_trm_actual(self, client):
        resp = client.get("/api/currency")
        assert resp.status_code == 200
        assert resp.json()["usd_cop"] > 0

    def test_conversion_usd_a_cop(self, client):
        resp = client.get("/api/currency/convert?amount=100&from_currency=USD&to_currency=COP")
        assert resp.status_code == 200
        data = resp.json()
        assert data["result"] == pytest.approx(100 * data["trm_used"])


# --------------------------------------------------------- Investments ---
INVESTMENT_PAYLOAD = {
    "coffee_type": "pergamino_seco",
    "hectares": 5,
    "production_per_hectare_kg": 2000,
    "use_current_price": False,
    "custom_price_per_kg": 11200,
    "currency": "COP",
    "capital_disponible": 40_000_000,
    "costs": {
        "preparacion_terreno": 2_000_000, "plantulas": 3_000_000, "fertilizantes": 8_000_000,
        "mano_de_obra": 15_000_000, "control_plagas": 2_000_000, "herramientas": 1_500_000,
        "transporte": 1_000_000, "cosecha": 6_000_000, "procesamiento": 2_000_000,
        "secado": 1_000_000, "almacenamiento": 500_000, "administracion": 1_500_000, "otros": 500_000,
    },
}


class TestInvestments:
    def test_calcular(self, client):
        resp = client.post("/api/investment/calculate", json=INVESTMENT_PAYLOAD)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_investment"] == 44_000_000
        assert data["total_income"] == 112_000_000
        assert data["capital_analysis"]["alcanza"] is False  # 40M < 44M

    def test_hectareas_negativas_da_422(self, client):
        bad = dict(INVESTMENT_PAYLOAD, hectares=-1)
        resp = client.post("/api/investment/calculate", json=bad)
        assert resp.status_code == 422

    def test_precio_personalizado_sin_valor_da_422(self, client):
        bad = dict(INVESTMENT_PAYLOAD, use_current_price=False, custom_price_per_kg=None)
        resp = client.post("/api/investment/calculate", json=bad)
        assert resp.status_code == 422

    def test_escenarios(self, client):
        resp = client.post("/api/investment/scenarios", json={"payload": INVESTMENT_PAYLOAD, "params": {}})
        assert resp.status_code == 200
        scenarios = resp.json()["scenarios"]
        assert len(scenarios) == 3
        assert {s["name"] for s in scenarios} == {"pesimista", "esperado", "optimista"}

    def test_sensibilidad(self, client):
        resp = client.post("/api/investment/sensitivity", json=INVESTMENT_PAYLOAD)
        assert resp.status_code == 200
        assert len(resp.json()["points"]) == 7

    def test_oportunidad(self, client):
        resp = client.post("/api/investment/opportunity", json=INVESTMENT_PAYLOAD)
        assert resp.status_code == 200
        data = resp.json()
        for key in ["opportunity_score", "volatility_score", "price_sensitivity_score", "margin_score"]:
            assert 0 <= data[key] <= 100
        assert "disclaimer" in data


# ------------------------------------------------------------- Sellers ---
class TestSellers:
    def test_listado(self, client):
        resp = client.get("/api/sellers")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 20  # 21 organizaciones curadas

    def test_filtro_por_departamento(self, client):
        resp = client.get("/api/sellers?department=Huila")
        assert resp.status_code == 200
        assert all(s["department"] == "Huila" for s in resp.json()["sellers"])

    def test_detalle_por_id(self, client):
        listado = client.get("/api/sellers").json()
        first_id = listado["sellers"][0]["id"]
        resp = client.get(f"/api/sellers/{first_id}")
        assert resp.status_code == 200

    def test_id_inexistente_da_404(self, client):
        resp = client.get("/api/sellers/999999")
        assert resp.status_code == 404


# --------------------------------------------------------- Simulations ---
class TestSimulations:
    def test_ciclo_completo_crear_listar_obtener_editar_eliminar(self, client):
        create_payload = {
            "name": "Test simulación integración",
            "coffee_type": "pergamino_seco",
            "hectares": 3,
            "production_per_hectare_kg": 1800,
            "price_used_per_kg": 10000,
            "price_currency": "COP",
            "price_source": "personalizado",
            "capital_disponible": 20_000_000,
            "costs": {k: 1_000_000 for k in INVESTMENT_PAYLOAD["costs"]},
            "scenario_params": {},
            "results": {"total_investment": 13_000_000, "profit": 5_000_000, "roi_pct": 38.5},
            "notes": "creada por pytest",
        }
        created = client.post("/api/simulations", json=create_payload)
        assert created.status_code == 200
        sim_id = created.json()["id"]

        listado = client.get("/api/simulations")
        assert listado.status_code == 200
        assert any(s["id"] == sim_id for s in listado.json())

        detalle = client.get(f"/api/simulations/{sim_id}")
        assert detalle.status_code == 200
        assert detalle.json()["costs_by_category"]["mano_de_obra"] == 1_000_000

        edit = client.patch(f"/api/simulations/{sim_id}", json={"name": "Renombrada", "hectares": 4})
        assert edit.status_code == 200
        assert edit.json()["name"] == "Renombrada"
        assert edit.json()["hectares"] == 4

        deleted = client.delete(f"/api/simulations/{sim_id}")
        assert deleted.status_code == 204
        assert client.get(f"/api/simulations/{sim_id}").status_code == 404

    def test_exportar_csv_xlsx_pdf(self, client):
        create_payload = {
            "name": "Para exportar", "coffee_type": "pergamino_seco", "hectares": 2,
            "production_per_hectare_kg": 1500, "price_used_per_kg": 9500, "price_currency": "COP",
            "price_source": "personalizado", "costs": {k: 500_000 for k in INVESTMENT_PAYLOAD["costs"]},
            "results": {"total_investment": 6_500_000, "profit": 1_000_000, "roi_pct": 15.4},
        }
        sim_id = client.post("/api/simulations", json=create_payload).json()["id"]
        for fmt, content_type in [("csv", "text/csv"), ("xlsx", "application/vnd.openxmlformats"), ("pdf", "application/pdf")]:
            resp = client.get(f"/api/simulations/{sim_id}/export/{fmt}")
            assert resp.status_code == 200
            assert content_type in resp.headers["content-type"]


# -------------------------------------------------------------- Alerts ---
class TestAlerts:
    def test_ciclo_completo(self, client):
        created = client.post("/api/alerts", json={
            "name": "Test alerta", "product": "arabica", "condition": "mayor_que", "threshold": 1.00,
        })
        assert created.status_code == 201
        data = created.json()
        alert_id = data["id"]
        assert data["status"] == "activa"
        assert data["threshold_unit"] == "USD/lb"

        listado = client.get("/api/alerts")
        assert any(a["id"] == alert_id for a in listado.json())

        edited = client.patch(f"/api/alerts/{alert_id}", json={"threshold": 1.50})
        assert edited.status_code == 200
        assert edited.json()["threshold"] == 1.50

        toggled = client.patch(f"/api/alerts/{alert_id}/toggle")
        assert toggled.json()["status"] == "desactivada"
        toggled_back = client.patch(f"/api/alerts/{alert_id}/toggle")
        assert toggled_back.json()["status"] == "activa"

        deleted = client.delete(f"/api/alerts/{alert_id}")
        assert deleted.status_code == 204
        assert client.get(f"/api/alerts/{alert_id}").status_code == 404

    def test_umbral_muy_bajo_se_dispara_al_evaluar(self, client):
        """Arábica > 0.01 USD/lb siempre es verdad con cualquier precio
        real o demo — sirve para probar que /evaluate realmente dispara."""
        created = client.post("/api/alerts", json={
            "name": "Siempre se dispara", "product": "arabica", "condition": "mayor_que", "threshold": 0.01,
        })
        alert_id = created.json()["id"]

        resp = client.post("/api/alerts/evaluate")
        assert resp.status_code == 200
        triggered_ids = [a["id"] for a in resp.json()]
        assert alert_id in triggered_ids

        refreshed = client.get(f"/api/alerts/{alert_id}").json()
        assert refreshed["status"] == "disparada"
        assert refreshed["triggered_price"] is not None
        assert isinstance(refreshed["triggered_is_demo"], bool)
        assert isinstance(refreshed["last_checked_is_demo"], bool)

    def test_alerta_se_evalua_automaticamente_al_consultar_precio(self, client):
        """Sección 4: al refrescar el precio, el sistema evalúa alertas de
        ese producto sin necesidad de llamar /evaluate explícitamente."""
        created = client.post("/api/alerts", json={
            "name": "Auto-evaluación nacional", "product": "nacional", "condition": "mayor_o_igual", "threshold": 1,
        })
        alert_id = created.json()["id"]

        client.get("/api/prices/current?market=nacional&coffee_type=pergamino_seco&period=1d")

        refreshed = client.get(f"/api/alerts/{alert_id}").json()
        assert refreshed["status"] == "disparada"

    def test_umbral_negativo_da_422(self, client):
        resp = client.post("/api/alerts", json={
            "name": "Inválida", "product": "arabica", "condition": "mayor_que", "threshold": -5,
        })
        assert resp.status_code == 422

    def test_id_inexistente_da_404_en_todas_las_operaciones(self, client):
        assert client.get("/api/alerts/999999").status_code == 404
        assert client.patch("/api/alerts/999999", json={"name": "x"}).status_code == 404
        assert client.delete("/api/alerts/999999").status_code == 404
        assert client.patch("/api/alerts/999999/toggle").status_code == 404


# ------------------------------------------------------------- General ---
def test_health(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_docs_disponible(client):
    resp = client.get("/docs")
    assert resp.status_code == 200


def test_dashboard_carga(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]
