"""Pruebas de app/services/alert_service.py (lógica pura, sin framework)."""
import pytest

from app.services.alert_service import AlertCondition, evaluate_condition


def test_mayor_que():
    assert evaluate_condition(AlertCondition.MAYOR_QUE, 5, 3) is True
    assert evaluate_condition(AlertCondition.MAYOR_QUE, 3, 5) is False
    assert evaluate_condition(AlertCondition.MAYOR_QUE, 5, 5) is False


def test_menor_que():
    assert evaluate_condition(AlertCondition.MENOR_QUE, 3, 5) is True
    assert evaluate_condition(AlertCondition.MENOR_QUE, 5, 3) is False
    assert evaluate_condition(AlertCondition.MENOR_QUE, 5, 5) is False


def test_mayor_o_igual():
    assert evaluate_condition(AlertCondition.MAYOR_O_IGUAL, 5, 5) is True
    assert evaluate_condition(AlertCondition.MAYOR_O_IGUAL, 6, 5) is True
    assert evaluate_condition(AlertCondition.MAYOR_O_IGUAL, 4, 5) is False


def test_menor_o_igual():
    assert evaluate_condition(AlertCondition.MENOR_O_IGUAL, 5, 5) is True
    assert evaluate_condition(AlertCondition.MENOR_O_IGUAL, 4, 5) is True
    assert evaluate_condition(AlertCondition.MENOR_O_IGUAL, 6, 5) is False


def test_condicion_desconocida_lanza_error():
    with pytest.raises(ValueError):
        evaluate_condition("no_existe", 5, 5)  # type: ignore[arg-type]


def test_umbral_real_arabica():
    """Caso realista: alerta 'Arábica mayor que $3.00/lb' contra el cierre
    real del 11 ago 2026 (3.36 USD/lb, ver README)."""
    assert evaluate_condition(AlertCondition.MAYOR_QUE, 3.36, 3.00) is True
    assert evaluate_condition(AlertCondition.MAYOR_QUE, 3.36, 3.36) is False
    assert evaluate_condition(AlertCondition.MAYOR_QUE, 3.36, 3.40) is False
