from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.services.alert_service import AlertCondition, AlertProduct, AlertStatus


class AlertCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    product: AlertProduct
    condition: AlertCondition
    threshold: float = Field(..., gt=0)


class AlertUpdate(BaseModel):
    """Todos los campos opcionales: PATCH solo cambia lo que venga informado."""
    name: str | None = Field(None, min_length=1, max_length=200)
    product: AlertProduct | None = None
    condition: AlertCondition | None = None
    threshold: float | None = Field(None, gt=0)


class AlertOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    product: AlertProduct
    condition: AlertCondition
    threshold: float
    threshold_unit: str  # calculado (no persistido) a partir de `product`
    status: AlertStatus

    created_at: datetime
    last_checked_at: datetime | None
    last_checked_price: float | None
    last_checked_is_demo: bool | None

    triggered_at: datetime | None
    triggered_price: float | None
    triggered_is_demo: bool | None
