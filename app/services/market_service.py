"""Comparación nacional vs internacional (sección 7 del brief)."""
from sqlalchemy.orm import Session

from app.models.price import CoffeeType, MarketType
from app.schemas.price import MarketComparisonOut
from app.services import price_service


def compare_markets(
    db: Session,
    national_coffee_type: CoffeeType = CoffeeType.PERGAMINO_SECO,
    international_coffee_type: CoffeeType = CoffeeType.ARABICA,
    period: str = "30d",
) -> MarketComparisonOut:
    national = price_service.get_current_price(db, MarketType.NACIONAL, national_coffee_type, period)
    international = price_service.get_current_price(
        db, MarketType.INTERNACIONAL, international_coffee_type, period
    )

    national_history = price_service.get_history(db, MarketType.NACIONAL, national_coffee_type, period)
    international_history = price_service.get_history(
        db, MarketType.INTERNACIONAL, international_coffee_type, period
    )

    difference_cop_kg = national.price_cop_per_kg - international.price_cop_per_kg
    difference_pct = (
        (difference_cop_kg / international.price_cop_per_kg) * 100
        if international.price_cop_per_kg
        else 0.0
    )

    return MarketComparisonOut(
        national=national,
        international=international,
        difference_cop_kg=round(difference_cop_kg, 2),
        difference_pct=round(difference_pct, 2),
        national_history=national_history.points,
        international_history=international_history.points,
    )
