"""Pruebas del módulo de conversión de unidades (app/core/units.py)."""
import pytest

from app.core.units import WeightUnit, convert, from_kg, price_per_kg, to_kg


def test_carga_es_125_kg():
    assert to_kg(1, WeightUnit.CARGA) == 125.0


def test_arroba_es_12_5_kg():
    assert to_kg(1, WeightUnit.ARROBA) == 12.5


def test_carga_es_10_arrobas():
    assert convert(1, WeightUnit.CARGA, WeightUnit.ARROBA) == pytest.approx(10.0)


def test_kg_a_libras():
    assert convert(1, WeightUnit.KG, WeightUnit.LB) == pytest.approx(2.20462, rel=1e-4)


def test_ida_y_vuelta_no_pierde_precision():
    original = 37.5
    result = from_kg(to_kg(original, WeightUnit.ARROBA), WeightUnit.ARROBA)
    assert result == pytest.approx(original)


def test_precio_por_carga_a_precio_por_kg():
    precio_carga = 1_400_000  # COP
    assert price_per_kg(precio_carga, WeightUnit.CARGA) == pytest.approx(1_400_000 / 125)


def test_unidad_no_soportada_lanza_error():
    with pytest.raises(ValueError):
        to_kg(1, "unidad_invalida")  # type: ignore[arg-type]
