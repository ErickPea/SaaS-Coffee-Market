"""
Pruebas de InternationalMarketProvider con `requests` mockeado (nunca toca
la red real). Cubre exactamente los escenarios pedidos: proveedor funciona,
respuesta inválida, vacía, timeout, error HTTP, ticker no encontrado — y en
todos los casos de falla comprueba que se use el fallback demo, nunca que
se propague la excepción ni que se presente un dato falso como real.
"""
from unittest.mock import Mock, patch

import pytest
import requests

from app.providers.international import InternationalMarketProvider


def _mock_yahoo_response(timestamps, closes, currency="USX", previous_close=None):
    payload = {
        "chart": {
            "error": None,
            "result": [{
                "meta": {"currency": currency, "previousClose": previous_close},
                "timestamp": timestamps,
                "indicators": {"quote": [{"close": closes}]},
            }],
        }
    }
    resp = Mock()
    resp.raise_for_status = Mock()
    resp.json = Mock(return_value=payload)
    return resp


@pytest.fixture
def provider():
    return InternationalMarketProvider()


class TestProveedorFunciona:
    @patch("app.providers.international.requests.get")
    def test_respuesta_exitosa_no_es_demo(self, mock_get, provider):
        mock_get.return_value = _mock_yahoo_response(
            timestamps=[1735689600, 1735776000], closes=[320.5, 328.0], previous_close=318.0,
        )
        result = provider.get_price(period_days=7, coffee_type="arabica")
        assert result.is_demo is False
        assert result.source.startswith("Yahoo Finance")

    @patch("app.providers.international.requests.get")
    def test_convierte_centavos_usx_a_dolares(self, mock_get, provider):
        """328.0 USX (centavos) debe convertirse a 3.28 USD/lb."""
        mock_get.return_value = _mock_yahoo_response(timestamps=[1735776000], closes=[328.0])
        result = provider.get_price(period_days=1, coffee_type="arabica")
        assert result.current_price == pytest.approx(3.28)
        assert result.currency == "USD"
        assert result.unit == "lb"


class TestRespuestaInvalida:
    @patch("app.providers.international.requests.get")
    def test_ticker_no_encontrado_cae_a_demo(self, mock_get, provider):
        resp = Mock()
        resp.raise_for_status = Mock()
        resp.json = Mock(return_value={"chart": {"error": {"code": "Not Found", "description": "No data found"}, "result": None}})
        mock_get.return_value = resp

        result = provider.get_price(period_days=7, coffee_type="robusta")
        assert result.is_demo is True
        assert result.demo_reason is not None
        assert "Yahoo Finance" in result.demo_reason or "error" in result.demo_reason.lower()

    @patch("app.providers.international.requests.get")
    def test_resultado_vacio_cae_a_demo(self, mock_get, provider):
        resp = Mock()
        resp.raise_for_status = Mock()
        resp.json = Mock(return_value={"chart": {"error": None, "result": []}})
        mock_get.return_value = resp

        result = provider.get_price(period_days=7, coffee_type="arabica")
        assert result.is_demo is True

    @patch("app.providers.international.requests.get")
    def test_json_sin_las_llaves_esperadas_cae_a_demo(self, mock_get, provider):
        resp = Mock()
        resp.raise_for_status = Mock()
        resp.json = Mock(return_value={"algo_inesperado": True})
        mock_get.return_value = resp

        result = provider.get_price(period_days=7, coffee_type="arabica")
        assert result.is_demo is True


class TestRespuestaVacia:
    @patch("app.providers.international.requests.get")
    def test_closes_todos_nulos_cae_a_demo(self, mock_get, provider):
        mock_get.return_value = _mock_yahoo_response(timestamps=[1735689600, 1735776000], closes=[None, None])
        result = provider.get_price(period_days=7, coffee_type="arabica")
        assert result.is_demo is True

    @patch("app.providers.international.requests.get")
    def test_sin_timestamps_cae_a_demo(self, mock_get, provider):
        mock_get.return_value = _mock_yahoo_response(timestamps=[], closes=[])
        result = provider.get_price(period_days=7, coffee_type="arabica")
        assert result.is_demo is True


class TestTimeoutYErroresHTTP:
    @patch("app.providers.international.requests.get")
    def test_timeout_cae_a_demo(self, mock_get, provider):
        mock_get.side_effect = requests.Timeout("Connection timed out")
        result = provider.get_price(period_days=7, coffee_type="arabica")
        assert result.is_demo is True
        assert "timed out" in result.demo_reason.lower() or "timeout" in result.demo_reason.lower()

    @patch("app.providers.international.requests.get")
    def test_error_http_cae_a_demo(self, mock_get, provider):
        resp = Mock()
        resp.raise_for_status = Mock(side_effect=requests.HTTPError("500 Server Error"))
        mock_get.return_value = resp
        result = provider.get_price(period_days=7, coffee_type="arabica")
        assert result.is_demo is True

    @patch("app.providers.international.requests.get")
    def test_error_de_conexion_cae_a_demo(self, mock_get, provider):
        mock_get.side_effect = requests.ConnectionError("No se pudo resolver el host")
        result = provider.get_price(period_days=7, coffee_type="arabica")
        assert result.is_demo is True


class TestFallbackDemoEsHonesto:
    """El fallback nunca debe reportarse como si fuera un dato real."""

    @patch("app.providers.international.requests.get")
    def test_demo_trae_historial_no_vacio(self, mock_get, provider):
        mock_get.side_effect = requests.ConnectionError("sin red")
        result = provider.get_price(period_days=30, coffee_type="arabica")
        assert result.is_demo is True
        assert len(result.history) > 0
        assert result.source.lower().startswith("datos demo") or "demo" in result.source.lower()

    @patch("app.providers.international.requests.get")
    def test_demo_de_robusta_usa_unidad_ton(self, mock_get, provider):
        mock_get.side_effect = requests.ConnectionError("sin red")
        result = provider.get_price(period_days=30, coffee_type="robusta")
        assert result.is_demo is True
        assert result.unit == "ton"
