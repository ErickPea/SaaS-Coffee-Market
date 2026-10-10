"""
Interfaz común para proveedores de datos externos.

Cada proveedor (internacional, nacional, moneda) implementa esta interfaz.
Esto permite que `price_service.py` no sepa ni le importe si el precio vino
de Yahoo Finance, de un valor cargado manualmente o de un archivo de
demostración: siempre recibe un `ProviderResult` con la misma forma y con
`is_demo` indicando honestamente si es un dato real o de respaldo.

Cambiar de proveedor en el futuro (p.ej. pasar de Yahoo Finance a un feed de
pago) implica escribir una clase nueva que cumpla esta interfaz, sin tocar
servicios, API ni frontend.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class PricePoint:
    timestamp: datetime
    price: float


@dataclass
class ProviderResult:
    """Resultado estandarizado que devuelve cualquier proveedor."""

    current_price: float
    previous_price: float | None
    unit: str  # ver app.core.units.WeightUnit o "lb" para futuros
    currency: str  # "COP" | "USD"
    history: list[PricePoint] = field(default_factory=list)
    source: str = ""
    source_url: str | None = None
    last_updated: datetime = field(default_factory=datetime.utcnow)
    is_demo: bool = False
    demo_reason: str | None = None


class BaseProvider(ABC):
    """Todo proveedor debe poder responder 'dame el precio actual + histórico
    para este período' de forma sincrónica y NUNCA lanzar una excepción hacia
    el llamador: si algo falla internamente, debe devolver un ProviderResult
    con is_demo=True y demo_reason explicando qué pasó, para que la capa de
    presentación pueda mostrarlo con transparencia en vez de romper la app."""

    name: str = "base"

    @abstractmethod
    def get_price(self, period_days: int, **kwargs) -> ProviderResult:
        raise NotImplementedError
