"""
Pruebas de NationalCoffeeProvider. Incluye una prueba con un PDF real
generado con reportlab (no un mock) para validar de verdad la extracción
con pdfplumber, ya que ambas librerías sí están disponibles.
"""
import io
from unittest.mock import Mock, patch

import pytest
import requests

from app.providers.national import NationalCoffeeProvider, PLAUSIBLE_RANGE_COP


@pytest.fixture
def provider():
    return NationalCoffeeProvider()


class TestExtraccionValidada:
    """_extract_validated_price es una función pura: sin red, sin mocks."""

    def test_encuentra_precio_cerca_de_la_palabra_clave(self):
        text = "Boletín diario\nPrecio interno de referencia: $2.265.000 por carga de 125 Kg\nOtros datos..."
        price = NationalCoffeeProvider._extract_validated_price(text)
        assert price == 2_265_000

    def test_rechaza_numero_fuera_de_rango_plausible(self):
        # $86.500 (un valor de compensación Sisbén, no un precio de carga) no debe aceptarse como precio.
        text = "Compensación Sisbén A/B/C: $86.500\nprecio interno de referencia sin más datos numéricos válidos"
        price = NationalCoffeeProvider._extract_validated_price(text)
        assert price is None or PLAUSIBLE_RANGE_COP[0] <= price <= PLAUSIBLE_RANGE_COP[1]

    def test_sin_cifras_devuelve_none(self):
        text = "El boletín cambió de formato y ya no incluye el precio en este texto."
        assert NationalCoffeeProvider._extract_validated_price(text) is None

    def test_rango_plausible_excluye_valores_absurdos(self):
        text = "precio interno de referencia $50 y también $999.000.000"
        price = NationalCoffeeProvider._extract_validated_price(text)
        assert price is None  # ninguno de los dos cae dentro de PLAUSIBLE_RANGE_COP


class TestExtraccionDePDFReal:
    """Genera un PDF real con reportlab y lo lee con pdfplumber (sin mocks)."""

    def _build_real_pdf(self, text_lines: list[str]) -> bytes:
        from reportlab.pdfgen import canvas

        buf = io.BytesIO()
        c = canvas.Canvas(buf)
        y = 800
        for line in text_lines:
            c.drawString(50, y, line)
            y -= 20
        c.save()
        return buf.getvalue()

    def test_extrae_texto_de_un_pdf_real(self):
        pdf_bytes = self._build_real_pdf([
            "Federacion Nacional de Cafeteros",
            "Precio interno de referencia: $2.180.500 por carga de 125 Kg",
        ])
        text = NationalCoffeeProvider._extract_pdf_text(pdf_bytes)
        assert "2.180.500" in text or "2180500" in text.replace(".", "")
        price = NationalCoffeeProvider._extract_validated_price(text)
        assert price == 2_180_500


class TestValorManual:
    def test_valor_manual_nunca_es_demo(self, provider):
        result = provider.get_price(period_days=7, manual_price=2_300_000)
        assert result.is_demo is False
        assert result.current_price == 2_300_000
        assert "manual" in result.source.lower()


class TestFallbackYRed:
    @patch("app.providers.national.requests.get")
    def test_timeout_cae_a_demo(self, mock_get, provider):
        mock_get.side_effect = requests.Timeout()
        result = provider.get_price(period_days=7)
        assert result.is_demo is True
        assert result.demo_reason is not None

    @patch("app.providers.national.requests.get")
    def test_pdf_sin_precio_reconocible_cae_a_demo_no_inventa_numero(self, mock_get, provider):
        """Si el PDF cambia de formato y no se encuentra un precio
        verificable, NUNCA debe inventarse un número — debe caer a demo."""
        resp = Mock()
        resp.raise_for_status = Mock()
        resp.headers = {"content-type": "application/pdf"}
        # PDF real pero sin ningún precio reconocible cerca de las palabras clave.
        from reportlab.pdfgen import canvas
        buf = io.BytesIO()
        c = canvas.Canvas(buf)
        c.drawString(50, 800, "Boletin sin informacion de precio esta semana.")
        c.save()
        resp.content = buf.getvalue()
        mock_get.return_value = resp

        result = provider.get_price(period_days=7)
        assert result.is_demo is True

    def test_demo_tiene_historial_y_fuente_identificable(self, provider):
        with patch("app.providers.national.requests.get", side_effect=requests.ConnectionError()):
            result = provider.get_price(period_days=30)
        assert result.is_demo is True
        assert len(result.history) > 0
        assert result.unit == "carga"
        assert result.currency == "COP"
