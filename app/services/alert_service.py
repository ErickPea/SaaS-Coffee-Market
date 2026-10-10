"""
Lógica pura de evaluación de alertas de precio.

Deliberadamente sin Pydantic/SQLAlchemy ni imports de `app.models`:
`evaluate_condition` es la función más crítica del sistema de alertas
(decide si algo se dispara) y debe poder probarse de forma totalmente
aislada, igual que el motor de cálculo del simulador
(`investment_service.py`). Por eso los enums de dominio (AlertProduct,
AlertCondition, AlertStatus) se definen AQUÍ como Enums planos, y
`app/models/alert.py` los importa desde este módulo para usarlos en las
columnas SQLAlchemy — no al revés. La orquestación (leer/guardar en BD,
consultar `price_service`) vive en `app/services/alert_orchestrator.py`.
"""
import enum


class AlertProduct(str, enum.Enum):
    ARABICA = "arabica"
    ROBUSTA = "robusta"
    NACIONAL = "nacional"


class AlertCondition(str, enum.Enum):
    MAYOR_QUE = "mayor_que"
    MENOR_QUE = "menor_que"
    MAYOR_O_IGUAL = "mayor_o_igual"
    MENOR_O_IGUAL = "menor_o_igual"


class AlertStatus(str, enum.Enum):
    ACTIVA = "activa"
    DISPARADA = "disparada"
    DESACTIVADA = "desactivada"


# Unidad nativa en la que se compara el umbral de cada producto — la misma
# unidad que el usuario ve en el dashboard/mercados (así no hace
# conversiones mentales). El mapeo producto -> (mercado, tipo de café) del
# sistema de precios vive en `alert_orchestrator.py` (ese sí depende de
# `app.models.price`).
PRODUCT_UNIT_LABELS: dict[AlertProduct, str] = {
    AlertProduct.ARABICA: "USD/lb",
    AlertProduct.ROBUSTA: "USD/ton",
    AlertProduct.NACIONAL: "COP/carga",
}

CONDITION_LABELS: dict[AlertCondition, str] = {
    AlertCondition.MAYOR_QUE: "mayor que",
    AlertCondition.MENOR_QUE: "menor que",
    AlertCondition.MAYOR_O_IGUAL: "mayor o igual a",
    AlertCondition.MENOR_O_IGUAL: "menor o igual a",
}


def evaluate_condition(condition: AlertCondition, current_value: float, threshold: float) -> bool:
    """True si `current_value` cumple la condición contra `threshold`."""
    if condition == AlertCondition.MAYOR_QUE:
        return current_value > threshold
    if condition == AlertCondition.MENOR_QUE:
        return current_value < threshold
    if condition == AlertCondition.MAYOR_O_IGUAL:
        return current_value >= threshold
    if condition == AlertCondition.MENOR_O_IGUAL:
        return current_value <= threshold
    raise ValueError(f"Condición de alerta desconocida: {condition}")
