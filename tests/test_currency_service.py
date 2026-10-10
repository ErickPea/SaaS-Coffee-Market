"""Pruebas de app/services/currency_service.build_trm_lookup (TRM por fecha)."""
from datetime import datetime, timedelta

import pytest

from app.providers.base import PricePoint, ProviderResult
from app.services.currency_service import build_trm_lookup

BASE = datetime(2026, 8, 1)


def _make_result(history, current=None, previous=None):
    return ProviderResult(
        current_price=current if current is not None else (history[-1].price if history else 0.0),
        previous_price=previous, unit="COP", currency="COP", history=history, source="test",
    )


class TestConHistorial:
    @pytest.fixture
    def result(self):
        history = [PricePoint(timestamp=BASE + timedelta(days=i * 2), price=3000 + i * 10) for i in range(10)]
        return _make_result(history)

    def test_fecha_exacta_devuelve_esa_tasa(self, result):
        lookup = build_trm_lookup(result)
        assert lookup(BASE) == 3000
        assert lookup(BASE + timedelta(days=18)) == 3090

    def test_fecha_intermedia_usa_la_mas_cercana(self, result):
        lookup = build_trm_lookup(result)
        assert lookup(BASE + timedelta(days=3)) == 3010  # más cerca del día 2 que del día 4

    def test_fecha_antes_del_inicio_usa_el_primer_dato(self, result):
        lookup = build_trm_lookup(result)
        assert lookup(BASE - timedelta(days=100)) == 3000

    def test_fecha_despues_del_final_usa_el_ultimo_dato(self, result):
        lookup = build_trm_lookup(result)
        assert lookup(BASE + timedelta(days=100)) == 3090


class TestSinHistorial:
    def test_usa_precio_actual_como_unica_alternativa(self):
        result = _make_result([], current=3500)
        lookup = build_trm_lookup(result)
        assert lookup(BASE) == 3500
        assert lookup(BASE + timedelta(days=999)) == 3500  # constante para cualquier fecha
