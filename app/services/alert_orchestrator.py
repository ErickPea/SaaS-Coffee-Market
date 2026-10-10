"""
Orquestación de alertas: CRUD sobre SQLAlchemy + evaluación contra
`price_service`. La lógica de "¿se cumple la condición?" vive en
`app/services/alert_service.py` (pura); aquí solo se conecta con la BD y
con los precios reales/demo.
"""
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.alert import Alert
from app.models.price import CoffeeType, MarketType
from app.schemas.alert import AlertCreate, AlertUpdate
from app.schemas.price import CurrentPriceOut
from app.services import price_service
from app.services.alert_service import AlertProduct, AlertStatus, evaluate_condition

# A qué (mercado, tipo de café) del sistema de precios corresponde cada
# producto de alerta. Vive aquí (no en alert_service.py) porque depende de
# app.models.price, que arrastra SQLAlchemy.
PRODUCT_PRICE_MAPPING: dict[AlertProduct, tuple[MarketType, CoffeeType]] = {
    AlertProduct.ARABICA: (MarketType.INTERNACIONAL, CoffeeType.ARABICA),
    AlertProduct.ROBUSTA: (MarketType.INTERNACIONAL, CoffeeType.ROBUSTA),
    AlertProduct.NACIONAL: (MarketType.NACIONAL, CoffeeType.PERGAMINO_SECO),
}
_REVERSE_PRODUCT_MAPPING = {v: k for k, v in PRODUCT_PRICE_MAPPING.items()}


def product_for(market: MarketType, coffee_type: CoffeeType) -> AlertProduct | None:
    """Producto de alerta correspondiente a un (mercado, tipo de café) del
    sistema de precios, o None si esa combinación no tiene alertas
    definidas (p.ej. café tostado o especial)."""
    return _REVERSE_PRODUCT_MAPPING.get((market, coffee_type))


def create_alert(db: Session, payload: AlertCreate) -> Alert:
    alert = Alert(
        name=payload.name, product=payload.product, condition=payload.condition,
        threshold=payload.threshold, status=AlertStatus.ACTIVA,
    )
    db.add(alert)
    db.commit()
    db.refresh(alert)
    return alert


def list_alerts(db: Session, status: AlertStatus | None = None, product: AlertProduct | None = None) -> list[Alert]:
    query = db.query(Alert)
    if status:
        query = query.filter(Alert.status == status)
    if product:
        query = query.filter(Alert.product == product)
    return query.order_by(Alert.created_at.desc()).all()


def get_alert(db: Session, alert_id: int) -> Alert | None:
    return db.query(Alert).filter(Alert.id == alert_id).first()


def update_alert(db: Session, alert_id: int, payload: AlertUpdate) -> Alert | None:
    alert = get_alert(db, alert_id)
    if alert is None:
        return None
    changes = payload.model_dump(exclude_unset=True)
    for field, value in changes.items():
        setattr(alert, field, value)
    # Editar la condición/umbral/producto de una alerta ya disparada la
    # reactiva: la condición cambió, así que debe volver a monitorearse.
    if changes and alert.status == AlertStatus.DISPARADA:
        alert.status = AlertStatus.ACTIVA
        alert.triggered_at = None
        alert.triggered_price = None
        alert.triggered_is_demo = None
    db.commit()
    db.refresh(alert)
    return alert


def delete_alert(db: Session, alert_id: int) -> bool:
    alert = get_alert(db, alert_id)
    if alert is None:
        return False
    db.delete(alert)
    db.commit()
    return True


def toggle_alert(db: Session, alert_id: int) -> Alert | None:
    """ACTIVA <-> DESACTIVADA. Una alerta DISPARADA se reactiva (vuelve a
    ACTIVA) en vez de desactivarse, para poder volver a monitorearla."""
    alert = get_alert(db, alert_id)
    if alert is None:
        return None
    alert.status = AlertStatus.DESACTIVADA if alert.status == AlertStatus.ACTIVA else AlertStatus.ACTIVA
    if alert.status == AlertStatus.ACTIVA:
        alert.triggered_at = None
        alert.triggered_price = None
        alert.triggered_is_demo = None
    db.commit()
    db.refresh(alert)
    return alert


def _apply_evaluation(alert: Alert, current_price: float, is_demo: bool, now: datetime) -> bool:
    """Actualiza los campos de seguimiento de una alerta contra un precio ya
    obtenido, y la dispara si corresponde. Devuelve True si se disparó."""
    alert.last_checked_at = now
    alert.last_checked_price = current_price
    alert.last_checked_is_demo = is_demo

    if evaluate_condition(alert.condition, current_price, alert.threshold):
        alert.status = AlertStatus.DISPARADA
        alert.triggered_at = now
        alert.triggered_price = current_price
        alert.triggered_is_demo = is_demo
        return True
    return False


def evaluate_alerts_for_price(db: Session, product: AlertProduct, price_result: CurrentPriceOut) -> list[Alert]:
    """Evalúa las alertas ACTIVAS de un producto contra un precio ya
    obtenido (evita volver a golpear el proveedor). Pensado para llamarse
    justo después de `price_service.get_current_price(...)` — así, 'cuando
    se consulte/refresque el precio, el sistema comprueba si alguna alerta
    se disparó' sin duplicar la consulta de precio."""
    alerts = list_alerts(db, status=AlertStatus.ACTIVA, product=product)
    if not alerts:
        return []

    now = datetime.now(timezone.utc)
    triggered = []
    for alert in alerts:
        if _apply_evaluation(alert, price_result.current_price, price_result.is_demo, now):
            triggered.append(alert)
    db.commit()
    for alert in triggered:
        db.refresh(alert)
    return triggered


def evaluate_all_active_alerts(db: Session) -> list[Alert]:
    """Evalúa TODAS las alertas activas, consultando el precio actual de
    cada producto distinto que tenga al menos una alerta activa. Pensado
    para `POST /api/alerts/evaluate` (evaluación explícita bajo demanda)."""
    active = list_alerts(db, status=AlertStatus.ACTIVA)
    if not active:
        return []

    products_needed = {a.product for a in active}
    triggered_all: list[Alert] = []
    for product in products_needed:
        market, coffee_type = PRODUCT_PRICE_MAPPING[product]
        price_result = price_service.get_current_price(db, market, coffee_type, period="1d")
        triggered_all.extend(evaluate_alerts_for_price(db, product, price_result))
    return triggered_all
