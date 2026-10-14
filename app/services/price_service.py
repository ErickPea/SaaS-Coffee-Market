"""
Servicio central de precios (secciones 4, 5 y 26 del brief).

Implementa el pipeline pedido en la sección 26:
    Obtención -> Validación -> Normalización -> Conversión -> Almacenamiento -> API -> Dashboard

1. Obtención: se delega en el Provider correspondiente (Internacional/Nacional).
2. Validación: precios <= 0 o histórico vacío se descartan (ver providers).
3. Normalización: todo precio se expresa también en COP/kg, sin importar la
   moneda/unidad original, para poder comparar mercados entre sí.
4. Conversión: usa `currency_service` (TRM) y `core.units` (peso).
5. Almacenamiento: el precio "actual" resuelto se guarda como PriceRecord.
6-7. API/Dashboard: lo consume `app/api/prices.py`.
"""
"""..."""
from datetime import datetime, timedelta, timezone
from statistics import mean, pstdev

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.units import WeightUnit, price_per_kg
from app.models.price import CoffeeType, Currency, MarketType, PriceRecord, PriceUnit
from app.providers.base import ProviderResult
from app.providers.international import InternationalMarketProvider
from app.providers.national import NationalCoffeeProvider
from app.schemas.price import CurrentPriceOut, PriceHistoryOut
from app.schemas.price import PricePoint as PricePointOut
from app.services import currency_service

PERIOD_DAYS: dict[str, int] = {
    "1d": 1, "7d": 7, "30d": 30, "3m": 90, "6m": 180, "1y": 365, "5y": 1825,
}

TREND_THRESHOLD_PCT = 1.0  # por debajo de esto (en valor absoluto), se considera "estable"

_international_provider = InternationalMarketProvider()
_national_provider = NationalCoffeeProvider()


def _trend_label(change_pct: float | None) -> str:
    if change_pct is None:
        return "estable"
    if change_pct > TREND_THRESHOLD_PCT:
        return "alcista"
    if change_pct < -TREND_THRESHOLD_PCT:
        return "bajista"
    return "estable"


def _unit_for(market: MarketType, coffee_type: CoffeeType) -> PriceUnit:
    if market == MarketType.INTERNACIONAL:
        # El Robusta (ICE Futures Europe) cotiza en USD por TONELADA, no por
        # libra como el Arábica (KC=F) — ver app/providers/international.py.
        # Confundir estas unidades produciría un COP/kg equivocado.
        return PriceUnit.TON if coffee_type == CoffeeType.ROBUSTA else PriceUnit.LB
    return PriceUnit.CARGA


def _normalize_to_cop_kg(price: float, currency: str, unit: PriceUnit, trm: float) -> float:
    price_kg_native = price_per_kg(price, WeightUnit(unit.value))
    return price_kg_native * trm if currency == "USD" else price_kg_native


def _store_price_record(
    db: Session, market: MarketType, coffee_type: CoffeeType, result: ProviderResult, unit: PriceUnit,
) -> None:
    """Guarda el precio actual resuelto como un nuevo registro histórico
    (paso 'Almacenamiento' del pipeline). No se deduplica agresivamente:
    cada refresco exitoso deja un rastro auditable de cuándo se consultó
    qué precio, con su fuente."""
    record = PriceRecord(
        market=market,
        coffee_type=coffee_type,
        price=result.current_price,
        currency=Currency(result.currency),
        unit=unit,
        timestamp=result.last_updated,
        source=result.source,
        source_url=result.source_url,
        is_demo=result.is_demo,
    )
    db.add(record)
    db.commit()

#sirve para reconstruir un CurrentPriceOut desde un registro cacheado, incluyendo max/min/promedio del período y cambios porcentuales.
def _find_cached_price_record(
    db: Session, market: MarketType, coffee_type: CoffeeType,
) -> PriceRecord | None:
    """Devuelve el PriceRecord más reciente de este (market, coffee_type)
    si está dentro de la ventana de caché (`price_cache_minutes`).

    Si no hay ninguno, o el más reciente es más antiguo que el caché,
    devuelve None para forzar una consulta fresca al provider.
    """
    cache_minutes = get_settings().price_cache_minutes
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=cache_minutes)

    stmt = (
        select(PriceRecord)
        .where(PriceRecord.market == market)
        .where(PriceRecord.coffee_type == coffee_type)
        .where(PriceRecord.timestamp >= cutoff)
        .order_by(PriceRecord.timestamp.desc())
        .limit(1)
    )
    return db.execute(stmt).scalar_one_or_none()

#Es para reconstruir un CurrentPriceOut desde un registro cacheado, incluyendo max/min/promedio del período y cambios porcentuales.
def _build_current_price_out_from_record(
    db: Session,
    record: PriceRecord,
    market: MarketType,
    coffee_type: CoffeeType,
    period: str,
) -> CurrentPriceOut:
    """Reconstruye un `CurrentPriceOut` desde un PriceRecord cacheado.

    Para calcular max/min/promedio del período, consultamos los registros
    históricos del mismo (market, coffee_type) dentro del período. Esto
    mantiene la semántica del endpoint aunque el precio "actual" venga
    del caché.
    """
    days = PERIOD_DAYS.get(period, 30)
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    unit = _unit_for(market, coffee_type)

    stmt = (
        select(PriceRecord.price)
        .where(PriceRecord.market == market)
        .where(PriceRecord.coffee_type == coffee_type)
        .where(PriceRecord.timestamp >= cutoff)
    )
    historical_prices = list(db.execute(stmt).scalars())
    if not historical_prices:
        historical_prices = [record.price]

    trm = currency_service.get_trm().rate
    price_cop_kg = _normalize_to_cop_kg(record.price, record.currency.value, unit, trm)

    # previous_price: el registro inmediatamente anterior al cacheado.
    prev_stmt = (
        select(PriceRecord.price)
        .where(PriceRecord.market == market)
        .where(PriceRecord.coffee_type == coffee_type)
        .where(PriceRecord.timestamp < record.timestamp)
        .order_by(PriceRecord.timestamp.desc())
        .limit(1)
    )
    previous_price = db.execute(prev_stmt).scalar_one_or_none()

    change_abs = None
    change_pct = None
    if previous_price:
        change_abs = record.price - previous_price
        change_pct = (change_abs / previous_price) * 100 if previous_price else None
     #Esto es para reconstruir un CurrentPriceOut desde un registro cacheado, incluyendo max/min/promedio del período y cambios porcentuales.
    return CurrentPriceOut(
        market=market,
        coffee_type=coffee_type,
        current_price=record.price,
        previous_price=previous_price,
        unit=unit,
        currency=record.currency,
        price_cop_per_kg=round(price_cop_kg, 2),
        change_abs=change_abs,
        change_pct=round(change_pct, 3) if change_pct is not None else None,
        period_max=max(historical_prices),
        period_min=min(historical_prices),
        period_avg=round(mean(historical_prices), 4),
        trend=_trend_label(change_pct),
        last_updated=record.timestamp,
        source=record.source,
        source_url=record.source_url,
        is_demo=record.is_demo,
        demo_reason=None,  # ya no aplica: es un registro histórico
    )

def get_current_price(
    db: Session,
    market: MarketType,
    coffee_type: CoffeeType,
    period: str = "30d",
    manual_price: float | None = None,
) -> CurrentPriceOut:
    days = PERIOD_DAYS.get(period, 30)
    unit = _unit_for(market, coffee_type)
        # --- Caché: si hay un registro reciente, devolverlo sin tocar al provider.
    # Solo aplicamos caché cuando NO se está pasando un precio manual explícito
    # (el precio manual es una acción del usuario que debe reflejarse ya).
    if manual_price is None:
        cached = _find_cached_price_record(db, market, coffee_type)
        if cached is not None:
            return _build_current_price_out_from_record(
                db, cached, market, coffee_type, period
            )
    if market == MarketType.INTERNACIONAL:
        provider_coffee = "robusta" if coffee_type == CoffeeType.ROBUSTA else "arabica"
        result = _international_provider.get_price(period_days=days, coffee_type=provider_coffee)
    else:
        result = _national_provider.get_price(period_days=days, manual_price=manual_price)

    trm = currency_service.get_trm().rate
    price_cop_kg = _normalize_to_cop_kg(result.current_price, result.currency, unit, trm)

    prices_in_period = [p.price for p in result.history] or [result.current_price]
    change_abs = None
    change_pct = None
    if result.previous_price:
        change_abs = result.current_price - result.previous_price
        change_pct = (change_abs / result.previous_price) * 100

    _store_price_record(db, market, coffee_type, result, unit)

    return CurrentPriceOut(
        market=market,
        coffee_type=coffee_type,
        current_price=result.current_price,
        previous_price=result.previous_price,
        unit=unit,
        currency=Currency(result.currency),
        price_cop_per_kg=round(price_cop_kg, 2),
        change_abs=change_abs,
        change_pct=round(change_pct, 3) if change_pct is not None else None,
        period_max=max(prices_in_period),
        period_min=min(prices_in_period),
        period_avg=round(mean(prices_in_period), 4),
        trend=_trend_label(change_pct),
        last_updated=result.last_updated,
        source=result.source,
        source_url=result.source_url,
        is_demo=result.is_demo,
        demo_reason=result.demo_reason,
    )


def get_history(
    db: Session, market: MarketType, coffee_type: CoffeeType, period: str = "30d",
) -> PriceHistoryOut:
    days = PERIOD_DAYS.get(period, 30)
    unit = _unit_for(market, coffee_type)

    if market == MarketType.INTERNACIONAL:
        provider_coffee = "robusta" if coffee_type == CoffeeType.ROBUSTA else "arabica"
        result = _international_provider.get_price(period_days=days, coffee_type=provider_coffee)
    else:
        result = _national_provider.get_price(period_days=days)

    # Cada punto se normaliza a COP/kg. El nacional ya está en COP (no
    # necesita TRM); el internacional está en USD y se convierte con la
    # TRM de CADA FECHA (no una tasa única para toda la serie) — ver
    # `currency_service.build_trm_lookup` para la estrategia quando no hay
    # una TRM exacta para una fecha puntual.
    if result.currency == "USD":
        trm_result = currency_service.get_trm_history(period_days=days)
        trm_lookup = currency_service.build_trm_lookup(trm_result)
        points = [
            PricePointOut(
                timestamp=p.timestamp,
                price_cop_kg=round(_normalize_to_cop_kg(p.price, result.currency, unit, trm_lookup(p.timestamp)), 4),
            )
            for p in result.history
        ]
    else:
        points = [
            PricePointOut(
                timestamp=p.timestamp,
                price_cop_kg=round(_normalize_to_cop_kg(p.price, result.currency, unit, 1.0), 4),
            )
            for p in result.history
        ]

    return PriceHistoryOut(
        market=market, coffee_type=coffee_type, period=period,
        points=points, is_demo=result.is_demo, source=result.source,
    )


def price_volatility_coefficient(
    db: Session, market: MarketType, coffee_type: CoffeeType, period: str = "1y",
) -> float | None:
    """Coeficiente de variación (desviación estándar / promedio) del precio
    histórico — insumo para el puntaje de volatilidad de la sección 15."""
    days = PERIOD_DAYS.get(period, 365)
    if market == MarketType.INTERNACIONAL:
        provider_coffee = "robusta" if coffee_type == CoffeeType.ROBUSTA else "arabica"
        result = _international_provider.get_price(period_days=days, coffee_type=provider_coffee)
    else:
        result = _national_provider.get_price(period_days=days)

    prices = [p.price for p in result.history]
    if len(prices) < 5:
        return None
    avg = mean(prices)
    if avg == 0:
        return None
    return pstdev(prices) / avg
