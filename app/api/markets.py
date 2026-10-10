from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.units import UNIT_LABELS, WeightUnit, convert
from app.models.price import CoffeeType
from app.schemas.price import MarketComparisonOut
from app.services import market_service

router = APIRouter(prefix="/api/markets", tags=["markets"])


@router.get("/compare", response_model=MarketComparisonOut)
def compare(
    national_coffee_type: CoffeeType = Query(CoffeeType.PERGAMINO_SECO),
    international_coffee_type: CoffeeType = Query(CoffeeType.ARABICA),
    period: str = Query("30d"),
    db: Session = Depends(get_db),
):
    """Sección 7: 'Comparar mercados' — precio nacional vs internacional."""
    return market_service.compare_markets(db, national_coffee_type, international_coffee_type, period)


@router.get("/units/convert")
def convert_units(
    amount: float = Query(..., gt=0),
    from_unit: WeightUnit = Query(...),
    to_unit: WeightUnit = Query(...),
):
    """Sección 18: conversor de unidades de peso."""
    return {
        "amount": amount,
        "from_unit": from_unit,
        "to_unit": to_unit,
        "result": round(convert(amount, from_unit, to_unit), 6),
    }


@router.get("/units")
def list_units():
    return {"units": [{"code": u.value, "label": label} for u, label in UNIT_LABELS.items()]}
