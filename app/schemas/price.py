from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.price import CoffeeType, Currency, MarketType, PriceUnit


class PriceRecordOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    market: MarketType
    coffee_type: CoffeeType
    price: float
    currency: Currency
    unit: PriceUnit
    timestamp: datetime
    source: str
    source_url: str | None = None
    is_demo: bool


class PricePoint(BaseModel):
    """Un punto (fecha, precio) normalizado a COP/kg, para graficar series."""
    timestamp: datetime
    price_cop_kg: float


class CurrentPriceOut(BaseModel):
    """
    Precio actual de un mercado/tipo de café, con las estadísticas del
    período solicitado (sección 4-5 del brief: actual, anterior, variación
    absoluta/porcentual, máximo, mínimo, promedio, tendencia).
    """
    market: MarketType
    coffee_type: CoffeeType
    current_price: float
    previous_price: float | None
    unit: PriceUnit
    currency: Currency
    price_cop_per_kg: float
    change_abs: float | None
    change_pct: float | None
    period_max: float | None
    period_min: float | None
    period_avg: float | None
    trend: str  # "alcista" | "bajista" | "estable"
    last_updated: datetime
    source: str
    source_url: str | None = None
    is_demo: bool
    demo_reason: str | None = None


class PriceHistoryOut(BaseModel):
    market: MarketType
    coffee_type: CoffeeType
    period: str
    points: list[PricePoint]
    is_demo: bool
    source: str


class MarketComparisonOut(BaseModel):
    national: CurrentPriceOut
    international: CurrentPriceOut
    difference_cop_kg: float
    difference_pct: float
    national_history: list[PricePoint]
    international_history: list[PricePoint]
