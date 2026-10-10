"""
Modelo de alertas de precio (sección 4 de esta ronda / sección 20 del brief
original).

El umbral (`threshold`) se guarda en la unidad NATIVA del producto elegido
(la misma que el usuario ve en el dashboard/mercados: USD/lb para Arábica,
USD/ton para Robusta, COP/carga para nacional) — así el usuario compara
directamente contra el número que está viendo, sin hacer conversiones
mentales. `PRODUCT_UNIT_LABELS` en `app/services/alert_service.py` mapea
cada producto a su unidad.
"""
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, Float, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.services.alert_service import AlertCondition, AlertProduct, AlertStatus

__all__ = ["Alert", "AlertProduct", "AlertCondition", "AlertStatus"]


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(200))
    product: Mapped[AlertProduct] = mapped_column(Enum(AlertProduct), index=True)
    condition: Mapped[AlertCondition] = mapped_column(Enum(AlertCondition))
    threshold: Mapped[float] = mapped_column(Float)
    status: Mapped[AlertStatus] = mapped_column(Enum(AlertStatus), default=AlertStatus.ACTIVA, index=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_checked_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    last_checked_is_demo: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    triggered_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    triggered_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    # True si la evaluación que disparó (o la última evaluación) se hizo
    # contra un precio demo, no un precio real — nunca se oculta este dato.
    triggered_is_demo: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Alert {self.id} {self.product}/{self.condition}/{self.threshold} [{self.status}]>"

    @property
    def threshold_unit(self) -> str:
        """Unidad nativa del umbral, derivada de `product` — no es una
        columna en BD, es una conveniencia para que `AlertOut` (Pydantic,
        from_attributes=True) la lea directamente del objeto ORM."""
        from app.services.alert_service import PRODUCT_UNIT_LABELS

        return PRODUCT_UNIT_LABELS[self.product]
