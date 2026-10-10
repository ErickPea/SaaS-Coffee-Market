from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.alert import AlertCreate, AlertOut, AlertUpdate
from app.services import alert_orchestrator
from app.services.alert_service import AlertProduct, AlertStatus

router = APIRouter(prefix="/api/alerts", tags=["alerts"])


@router.post("", response_model=AlertOut, status_code=201)
def create_alert(payload: AlertCreate, db: Session = Depends(get_db)):
    return alert_orchestrator.create_alert(db, payload)


@router.get("", response_model=list[AlertOut])
def list_alerts(
    status: AlertStatus | None = Query(None),
    product: AlertProduct | None = Query(None),
    db: Session = Depends(get_db),
):
    return alert_orchestrator.list_alerts(db, status=status, product=product)


@router.get("/{alert_id}", response_model=AlertOut)
def get_alert(alert_id: int, db: Session = Depends(get_db)):
    alert = alert_orchestrator.get_alert(db, alert_id)
    if alert is None:
        raise HTTPException(404, "Alerta no encontrada")
    return alert


@router.patch("/{alert_id}", response_model=AlertOut)
def update_alert(alert_id: int, payload: AlertUpdate, db: Session = Depends(get_db)):
    alert = alert_orchestrator.update_alert(db, alert_id, payload)
    if alert is None:
        raise HTTPException(404, "Alerta no encontrada")
    return alert


@router.delete("/{alert_id}", status_code=204)
def delete_alert(alert_id: int, db: Session = Depends(get_db)):
    deleted = alert_orchestrator.delete_alert(db, alert_id)
    if not deleted:
        raise HTTPException(404, "Alerta no encontrada")


@router.patch("/{alert_id}/toggle", response_model=AlertOut)
def toggle_alert(alert_id: int, db: Session = Depends(get_db)):
    """Activa <-> desactiva. Una alerta disparada se reactiva (vuelve a
    quedar en 'activa') para poder monitorearla de nuevo."""
    alert = alert_orchestrator.toggle_alert(db, alert_id)
    if alert is None:
        raise HTTPException(404, "Alerta no encontrada")
    return alert


@router.post("/evaluate", response_model=list[AlertOut])
def evaluate_alerts(db: Session = Depends(get_db)):
    """Evalúa manualmente todas las alertas activas contra el precio actual
    de cada producto y devuelve las que se dispararon. También ocurre
    automáticamente cada vez que se consulta /api/prices/current (ver
    app/api/prices.py)."""
    return alert_orchestrator.evaluate_all_active_alerts(db)
