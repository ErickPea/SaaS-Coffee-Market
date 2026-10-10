"""Pruebas de CurrencyProvider con `requests` mockeado."""
from unittest.mock import Mock, patch

import pytest
import requests

from app.providers.currency import CurrencyProvider


def _mock_trm_rows(rows):
    resp = Mock()
    resp.raise_for_status = Mock()
    resp.json = Mock(return_value=rows)
    return resp


@pytest.fixture
def provider():
    return CurrencyProvider()


class TestProveedorFunciona:
    @patch("app.providers.currency.requests.get")
    def test_respuesta_valida_no_es_demo(self, mock_get, provider):
        mock_get.return_value = _mock_trm_rows([
            {"vigenciadesde": "2026-08-11T00:00:00.000", "valor": "3121.00"},
            {"vigenciadesde": "2026-08-10T00:00:00.000", "valor": "3115.50"},
        ])
        result = provider.get_price(period_days=7)
        assert result.is_demo is False
        assert result.current_price == pytest.approx(3121.00)
        assert result.previous_price == pytest.approx(3115.50)


class TestRespuestaInvalida:
    @patch("app.providers.currency.requests.get")
    def test_lista_vacia_cae_a_demo(self, mock_get, provider):
        mock_get.return_value = _mock_trm_rows([])
        result = provider.get_price(period_days=7)
        assert result.is_demo is True
        assert result.demo_reason is not None

    @patch("app.providers.currency.requests.get")
    def test_estructura_inesperada_cae_a_demo(self, mock_get, provider):
        resp = Mock()
        resp.raise_for_status = Mock()
        resp.json = Mock(return_value={"no_es_una_lista": True})
        mock_get.return_value = resp
        result = provider.get_price(period_days=7)
        assert result.is_demo is True

    @patch("app.providers.currency.requests.get")
    def test_filas_sin_campo_valor_se_descartan_y_cae_a_demo_si_no_queda_nada(self, mock_get, provider):
        mock_get.return_value = _mock_trm_rows([{"algo": "irrelevante"}])
        result = provider.get_price(period_days=7)
        assert result.is_demo is True


class TestTimeoutYErrores:
    @patch("app.providers.currency.requests.get")
    def test_timeout_cae_a_demo(self, mock_get, provider):
        mock_get.side_effect = requests.Timeout()
        result = provider.get_price(period_days=7)
        assert result.is_demo is True

    @patch("app.providers.currency.requests.get")
    def test_error_http_cae_a_demo(self, mock_get, provider):
        resp = Mock()
        resp.raise_for_status = Mock(side_effect=requests.HTTPError("404"))
        mock_get.return_value = resp
        result = provider.get_price(period_days=7)
        assert result.is_demo is True
