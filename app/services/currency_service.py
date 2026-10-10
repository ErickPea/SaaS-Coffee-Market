"""Servicio de moneda (TRM) — sección 19 del brief."""
from dataclasses import dataclass
from datetime import datetime

from app.providers.currency import CurrencyProvider
from app.providers.base import ProviderResult

_provider = CurrencyProvider()


@dataclass
class TRMInfo:
    rate: float  # COP por 1 USD
    previous_rate: float | None
    change_abs: float | None
    change_pct: float | None
    last_updated: datetime
    source: str
    source_url: str | None
    is_demo: bool
    demo_reason: str | None


def get_trm(period_days: int = 30) -> TRMInfo:
    result: ProviderResult = _provider.get_price(period_days=period_days)
    change_abs = None
    change_pct = None
    if result.previous_price:
        change_abs = result.current_price - result.previous_price
        change_pct = (change_abs / result.previous_price) * 100

    return TRMInfo(
        rate=result.current_price,
        previous_rate=result.previous_price,
        change_abs=change_abs,
        change_pct=change_pct,
        last_updated=result.last_updated,
        source=result.source,
        source_url=result.source_url,
        is_demo=result.is_demo,
        demo_reason=result.demo_reason,
    )


def get_trm_history(period_days: int = 30):
    """Serie histórica de TRM (misma fuente/fallback que `get_trm`), para
    poder convertir series de precio USD->COP usando la TRM de cada fecha
    en vez de un único valor vigente. Devuelve el ProviderResult completo
    (incluye is_demo) para que el llamador decida cómo reportar la fuente."""
    return _provider.get_price(period_days=period_days)


def build_trm_lookup(trm_result: ProviderResult):
    """
    Devuelve una función `lookup(fecha) -> tasa` que encuentra la TRM más
    cercana a `fecha` dentro del histórico ya obtenido (búsqueda binaria).

    Estrategia documentada cuando no hay una TRM exacta para una fecha
    puntual (pregunta explícita: sección 6 de la ronda de correcciones):
    se usa la TRM del día más cercano disponible (antes o después,
    cualquiera que esté a menos tiempo de distancia) en vez de inventar un
    valor interpolado o dejar el punto sin convertir. Si no hay NINGÚN
    dato histórico de TRM (proveedor y demo fallaron ambos, caso muy
    extremo), se usa `trm_result.current_price` como única alternativa
    razonable, documentado aquí explícitamente — nunca un número inventado.

    Nota de implementación: normalizamos todas las fechas a naive-UTC
    antes de compararlas. Los proveedores pueden devolver timestamps
    naive (demo, fechas ISO sin zona) o aware (Yahoo Finance usa UTC
    explícito); mezclarlos rompe `bisect` y la resta de `datetime`s.
    """
    import bisect
    from datetime import timezone

    def _to_naive_utc(dt: datetime) -> datetime:
        """Convierte a naive-UTC. Si ya es naive, se asume UTC y se deja igual."""
        if dt.tzinfo is not None:
            return dt.astimezone(timezone.utc).replace(tzinfo=None)
        return dt

    points = sorted(trm_result.history, key=lambda p: _to_naive_utc(p.timestamp))
    if not points:
        constant_rate = trm_result.current_price

        def lookup_constant(_target):
            return constant_rate

        return lookup_constant

    dates = [_to_naive_utc(p.timestamp) for p in points]
    rates = [p.price for p in points]

    def lookup(target):
        target_naive = _to_naive_utc(target)
        idx = bisect.bisect_left(dates, target_naive)
        candidates = [i for i in (idx - 1, idx) if 0 <= i < len(dates)]
        best_idx = min(
            candidates,
            key=lambda i: abs((dates[i] - target_naive).total_seconds()),
        )
        return rates[best_idx]

    return lookup


def usd_to_cop(amount_usd: float, trm: float | None = None) -> float:
    rate = trm if trm is not None else get_trm().rate
    return amount_usd * rate


def cop_to_usd(amount_cop: float, trm: float | None = None) -> float:
    rate = trm if trm is not None else get_trm().rate
    if rate <= 0:
        raise ValueError("La TRM debe ser mayor que 0")
    return amount_cop / rate
