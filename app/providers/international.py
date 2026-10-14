"""
InternationalMarketProvider — precios de futuros de café (Arábica/Robusta).

Fuente primaria: endpoint público de gráficos de Yahoo Finance
(query1.finance.yahoo.com/v8/finance/chart/{ticker}). No requiere API key.
Es un endpoint NO documentado oficialmente por Yahoo (lo usa la librería
`yfinance` y muchísimas herramientas del ecosistema financiero abierto),
por lo que puede cambiar sin aviso — de ahí que todo esté envuelto en
try/except con fallback automático a datos demo.

Ticker Arábica confirmado: "KC=F" (Coffee C, ICE Futures U.S.), cotizado en
CENTAVOS de dólar por libra (por eso se divide entre 100 al convertir a
USD/lb). Ticker Robusta: NO se encontró un ticker "continuo" gratuito
confirmado con certeza al construir esta app — queda configurable en
`.env` (INTERNATIONAL_ROBUSTA_TICKER); si Yahoo no lo reconoce, cae a demo
automáticamente. Ver README para más detalle y alternativas.
"""
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

from app.core.config import get_settings
from app.providers.base import BaseProvider, PricePoint, ProviderResult

YAHOO_CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
DEMO_FILE = Path(__file__).resolve().parent.parent.parent / "data" / "demo_international_prices.json"

_INTERVAL_BY_DAYS = [
    (2, "15m"),
    (10, "60m"),
    (400, "1d"),
    (99999, "1wk"),
]


def _interval_for(days: int) -> str:
    for max_days, interval in _INTERVAL_BY_DAYS:
        if days <= max_days:
            return interval
    return "1mo"


class InternationalMarketProvider(BaseProvider):
    name = "international"

    def __init__(self) -> None:
        self.settings = get_settings()
        # NUEVO: instanciamos el provider de Alpha Vantage
        from app.providers.alpha_vantage import AlphaVantageProvider
        self._alpha_vantage = AlphaVantageProvider()

    def get_price(self, period_days: int, coffee_type: str = "arabica", **kwargs) -> ProviderResult:
        ticker = (
            self.settings.international_arabica_ticker
            if coffee_type == "arabica"
            else self.settings.international_robusta_ticker
        )
        try:
            return self._fetch_yahoo(ticker, period_days, coffee_type)
        except Exception as exc:
            # NUEVO: antes de caer al demo, intentamos Alpha Vantage
            try:
                return self._alpha_vantage.get_price(period_days, coffee_type)
            except Exception:
                # Alpha Vantage también falló -> ahora sí, demo
                return self._fallback_demo(period_days, coffee_type, reason=str(exc))

    # -- Fuente en vivo -----------------------------------------------
    def _fetch_yahoo(self, ticker: str, period_days: int, coffee_type: str) -> ProviderResult:
        now = datetime.now(timezone.utc)
        period1 = int((now - timedelta(days=period_days + 2)).timestamp())
        period2 = int(now.timestamp())
        interval = _interval_for(period_days)

        url = YAHOO_CHART_URL.format(ticker=ticker)
        headers = {"User-Agent": "Mozilla/5.0 (compatible; CoffeeMarketIntelligence/1.0)"}
        params = {"period1": period1, "period2": period2, "interval": interval}

        resp = requests.get(
            url, params=params, headers=headers,
            timeout=self.settings.international_provider_timeout_seconds,
        )
        resp.raise_for_status()
        payload = resp.json()

        chart = payload.get("chart", {})
        if chart.get("error"):
            raise ValueError(f"Yahoo Finance devolvió un error: {chart['error']}")
        results = chart.get("result") or []
        if not results:
            raise ValueError("Yahoo Finance no devolvió resultados para este ticker")

        result = results[0]
        meta = result.get("meta", {})
        timestamps = result.get("timestamp") or []
        closes = (
            result.get("indicators", {}).get("quote", [{}])[0].get("close") or []
        )
        if not timestamps or not closes:
            raise ValueError("Respuesta de Yahoo Finance sin serie de precios")

        points: list[PricePoint] = []
        for ts, close in zip(timestamps, closes):
            if close is None:
                continue
            points.append(PricePoint(timestamp=datetime.fromtimestamp(ts, tz=timezone.utc), price=float(close)))
        if not points:
            raise ValueError("Todos los precios devueltos por Yahoo Finance eran nulos")

        current = points[-1].price
        previous = points[-2].price if len(points) > 1 else meta.get("previousClose")

        unit = "lb"
        currency = meta.get("currency", "USD")
        # Yahoo reporta café en "USX" (centavos de USD). Normalizamos a USD.
        divisor = 100.0 if currency == "USX" else 1.0
        current = current / divisor
        previous = (previous / divisor) if previous is not None else None
        for p in points:
            p.price = p.price / divisor

        return ProviderResult(
            current_price=current,
            previous_price=previous,
            unit=unit,
            currency="USD",
            history=points,
            source=f"Yahoo Finance (ticker {ticker}, ICE Futures - delayed quote)",
            source_url=f"https://finance.yahoo.com/quote/{ticker}/",
            last_updated=points[-1].timestamp,
            is_demo=False,
        )

    # -- Respaldo demo --------------------------------------------------
    def _fallback_demo(self, period_days: int, coffee_type: str, reason: str) -> ProviderResult:
        with open(DEMO_FILE, encoding="utf-8") as f:
            payload = json.load(f)

        series_info = payload["arabica"] if coffee_type == "arabica" else payload["robusta"]
        series = series_info["series"]
        dates_sorted = sorted(series.keys())
        cutoff = dates_sorted[-1]
        end_date = datetime.fromisoformat(cutoff)
        start_date = end_date - timedelta(days=period_days)

        points = [
            PricePoint(timestamp=datetime.fromisoformat(d), price=v)
            for d, v in series.items()
            if datetime.fromisoformat(d) >= start_date
        ]
        points.sort(key=lambda p: p.timestamp)

        unit = "lb" if coffee_type == "arabica" else "ton"
        current = points[-1].price if points else 0.0
        # El demo de arábica queda en centavos/lb en el JSON -> pasar a USD/lb
        if coffee_type == "arabica":
            current = current / 100.0
            previous = (points[-2].price / 100.0) if len(points) > 1 else None
            for p in points:
                p.price = p.price / 100.0
        else:
            previous = points[-2].price if len(points) > 1 else None

        return ProviderResult(
            current_price=current,
            previous_price=previous,
            unit=unit,
            currency="USD",
            history=points,
            source="Datos DEMO (Yahoo Finance no disponible)",
            source_url=None,
            last_updated=points[-1].timestamp if points else datetime.now(timezone.utc),
            is_demo=True,
            demo_reason=(
                f"No se pudo consultar Yahoo Finance ({reason}). Mostrando serie "
                "de demostración calibrada con cotizaciones públicas reales, "
                "no un precio en vivo."
            ),
        )
