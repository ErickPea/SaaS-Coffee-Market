from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.price import CoffeeType, MarketType
from app.schemas.price import CurrentPriceOut, PriceHistoryOut
from app.services import alert_orchestrator, price_service

router = APIRouter(prefix="/api/prices", tags=["prices"])

VALID_PERIODS = list(price_service.PERIOD_DAYS.keys())


def _validate_period(period: str) -> str:
    if period not in VALID_PERIODS:
        raise HTTPException(400, f"Período inválido. Use uno de: {', '.join(VALID_PERIODS)}")
    return period


def _get_current_and_check_alerts(db: Session, market: MarketType, coffee_type: CoffeeType, period: str, manual_price: float | None = None) -> CurrentPriceOut:
    """Obtiene el precio actual y, de paso, evalúa las alertas activas de
    ese producto contra el precio recién obtenido (sección 4: 'cuando se
    consulte/refresque el precio, el sistema debe poder comprobar si
    alguna alerta se ha activado'). Reutiliza el precio ya obtenido en vez
    de volver a consultarlo."""
    result = price_service.get_current_price(db, market, coffee_type, period, manual_price=manual_price)
    product = alert_orchestrator.product_for(market, coffee_type)
    if product is not None:
        alert_orchestrator.evaluate_alerts_for_price(db, product, result)
    return result


@router.get("/current", response_model=CurrentPriceOut)
def get_current(
    market: MarketType = Query(..., description="nacional | internacional"),
    coffee_type: CoffeeType = Query(CoffeeType.PERGAMINO_SECO),
    period: str = Query("30d"),
    db: Session = Depends(get_db),
):
    _validate_period(period)
    return _get_current_and_check_alerts(db, market, coffee_type, period)


@router.get("/history", response_model=PriceHistoryOut)
def get_history(
    market: MarketType = Query(...),
    coffee_type: CoffeeType = Query(CoffeeType.PERGAMINO_SECO),
    period: str = Query("30d"),
    db: Session = Depends(get_db),
):
    _validate_period(period)
    return price_service.get_history(db, market, coffee_type, period)


@router.get("/national", response_model=CurrentPriceOut)
def get_national(
    coffee_type: CoffeeType = Query(CoffeeType.PERGAMINO_SECO),
    period: str = Query("30d"),
    db: Session = Depends(get_db),
):
    _validate_period(period)
    return _get_current_and_check_alerts(db, MarketType.NACIONAL, coffee_type, period)


@router.get("/international", response_model=CurrentPriceOut)
def get_international(
    coffee_type: CoffeeType = Query(CoffeeType.ARABICA),
    period: str = Query("30d"),
    db: Session = Depends(get_db),
):
    _validate_period(period)
    return _get_current_and_check_alerts(db, MarketType.INTERNACIONAL, coffee_type, period)


@router.post("/national/manual", response_model=CurrentPriceOut)
def set_national_manual_price(
    price_cop_per_carga: float = Query(..., gt=0, description="Precio interno de referencia, COP por carga de 125kg, leído directamente del boletín oficial de la FNC"),
    db: Session = Depends(get_db),
):
    """
    Permite registrar el precio oficial del día leído manualmente del
    boletín de la FNC (sección 5 del brief: 'datos ingresados manualmente
    como alternativa' cuando no hay una fuente en tiempo real confiable).
    """
    return _get_current_and_check_alerts(
        db, MarketType.NACIONAL, CoffeeType.PERGAMINO_SECO, period="30d", manual_price=price_cop_per_carga,
    )
