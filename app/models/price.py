"""
Modelo normalizado de precio.

Un PriceRecord representa UN precio, en UN momento, de UN tipo de café,
en UN mercado, con su unidad y moneda originales explícitas. Todo el resto
de la aplicación (servicios, API, frontend) consume estos registros ya
normalizados y nunca necesita saber de qué proveedor externo vinieron.

`is_demo=True` marca explícitamente los registros que son datos de
demostración/fallback (no un precio real obtenido de una fuente en vivo).
Esto permite que la capa de presentación muestre siempre con claridad si un
dato es real o de demostración, tal como exige el brief (sección 3 y 31).
"""
import enum
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Enum, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base

#-- Enumeraciones para los campos de PriceRecord
class MarketType(str, enum.Enum):
    NACIONAL = "nacional"
    INTERNACIONAL = "internacional"

#-- Nombres de los tipos de café que se pueden registrar en PriceRecord
class CoffeeType(str, enum.Enum):
    ARABICA = "arabica"
    ROBUSTA = "robusta"
    PERGAMINO_SECO = "pergamino_seco"
    VERDE = "verde"
    TOSTADO = "tostado"
    ESPECIAL = "especial"
    OTRO = "otro"

#-- Monedas soportadas para los precios en PriceRecord
class Currency(str, enum.Enum):
    COP = "COP"
    USD = "USD"
    EUR = "EUR"

#-- Unidades de medida soportadas para los precios en PriceRecord
class PriceUnit(str, enum.Enum):
    KG = "kg"
    LB = "lb"
    ARROBA = "arroba"
    CARGA = "carga"
    QUINTAL = "quintal"
    TON = "ton"

  #-- Esto es un modelo de SQLAlchemy que representa un registro de precio en la base de datos. 
  # Cada registro contiene información sobre el mercado, tipo de café, precio, moneda, unidad, 
  # timestamp, fuente y URL de la fuente. Además, se incluye un campo booleano para indicar si 
  # el registro es de demostración o no. El método __repr__ proporciona una representación legible 
  # del objeto para fines de depuración.
class PriceRecord(Base):
    __tablename__ = "price_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    market: Mapped[MarketType] = mapped_column(Enum(MarketType), index=True)
    coffee_type: Mapped[CoffeeType] = mapped_column(Enum(CoffeeType), index=True)
    price: Mapped[float] = mapped_column(Float)
    currency: Mapped[Currency] = mapped_column(Enum(Currency))
    unit: Mapped[PriceUnit] = mapped_column(Enum(PriceUnit))
    #-- es importante que el timestamp sea UTC para poder comparar precios de diferentes mercados
    timestamp: Mapped[datetime] = mapped_column(DateTime, index=True, default=lambda: datetime.now(timezone.utc) )
    source: Mapped[str] = mapped_column(String(200))
    
    source_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, index=True)

    def __repr__(self) -> str:  # pragma: no cover - solo para depuración
        return (
            f"<PriceRecord {self.market}/{self.coffee_type} "
            f"{self.price} {self.currency}/{self.unit} @ {self.timestamp} "
            f"demo={self.is_demo}>"
        )
