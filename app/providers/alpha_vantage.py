"""
AlphaVantageProvider — precio global del café (fallback de Yahoo Finance).

Fuente: endpoint `function=COFFEE` de Alpha Vantage. Requiere API key
(configurable en `.env` como ALPHA_VANTAGE_API_KEY; el tier gratuito
permite 25 requests/día).

IMPORTANTE — limitaciones conocidas:
  1. Es un precio GLOBAL de café, no específico de Arábica ni de Robusta.
     Se usa como fallback aproximado cuando Yahoo Finance falla; NO debe
     usarse como fuente primaria cuando se necesita la distinción
     Arábica/Robusta.
  2. Granularidad MENSUAL, no diaria ni horaria. Para períodos cortos
     (ej. 7 días) devolverá muy pocos puntos.
  3. El endpoint devuelve "." como valor para algunos meses (años 80s-91).
     Esos puntos se descartan.

Este provider NUNCA lanza excepciones hacia arriba: si la API key no está
configurada, si la red falla, o si el formato de respuesta cambia, cae al
demo automáticamente.
"""
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

from app.core.config import get_settings
from app.providers.base import BaseProvider, PricePoint, ProviderResult

ALPHA_VANTAGE_URL = "https://www.alphavantage.co/query"
DEMO_FILE = (
    Path(__file__).resolve().parent.parent.parent
    / "data"
    / "demo_international_prices.json"
)

# Este es el mismo demo que usa InternationalMarketProvider, para no duplicar datos.
#Los datos demo se calibraron con cotizaciones públicas reales de Yahoo Finance y Alpha Vantage.
#Los demos sirven para que la app funcione aunque no haya red o las fuentes externas fallen, pero NO son precios en vivo.
class AlphaVantageProvider(BaseProvider):
    name = "alpha_vantage"

    def __init__(self) -> None:
        self.settings = get_settings()

    def get_price(
        self,
        period_days: int,
        coffee_type: str = "arabica",
        **kwargs,
    ) -> ProviderResult:
        api_key = self.settings.alpha_vantage_api_key
        if not api_key:
            raise ValueError(
                "ALPHA_VANTAGE_API_KEY no configurada; Alpha Vantage no disponible."
            )

        try:
            return self._fetch_alpha_vantage(api_key, period_days)
        except Exception as exc:  # noqa: BLE001
            return self._fallback_demo(period_days, coffee_type, reason=str(exc))

    # -- Fuente en vivo -----------------------------------------------
    def _fetch_alpha_vantage(self, api_key: str, period_days: int) -> ProviderResult:
        #-- Llamada a la API de Alpha Vantage
        params = {
            "function": "COFFEE",
            "interval": "monthly",
            "apikey": api_key,
        }
        resp = requests.get(
            ALPHA_VANTAGE_URL,
            params=params,
            timeout=self.settings.international_provider_timeout_seconds,
        )
        #-- Manejo de errores y parseo de la respuesta
        resp.raise_for_status()
        payload = resp.json()

        # Alpha Vantage devuelve errores en claves conocidas con HTTP 200.
        if "Error Message" in payload:
            raise ValueError(f"Alpha Vantage error: {payload['Error Message']}")
        if "Note" in payload:
            raise ValueError(f"Alpha Vantage rate limit: {payload['Note']}")
        if "Information" in payload:
            raise ValueError(f"Alpha Vantage info: {payload['Information']}")

        rows = payload.get("data") or []
        if not rows:
            raise ValueError("Alpha Vantage no devolvió datos de café")

        # Filtrar puntos inválidos (value == ".") y parsear
        cutoff = datetime.now(timezone.utc) - timedelta(days=period_days)
        points: list[PricePoint] = []
        for row in rows:
            raw_value = row.get("value", ".")
            if raw_value in (".", "", None):
                continue
            try:
                value = float(raw_value)
            except (TypeError, ValueError):
                continue
            # Alpha Vantage reporta centavos/lb. Pasamos a USD/lb.
            price_usd_lb = value / 100.0
            # Las fechas vienen como "YYYY-MM-01" (primer día del mes).
            ts = datetime.fromisoformat(row["date"]).replace(tzinfo=timezone.utc)
            if ts < cutoff:
                continue
            points.append(PricePoint(timestamp=ts, price=price_usd_lb))

        if not points:
            raise ValueError(
                f"Alpha Vantage no tiene puntos válidos para los últimos {period_days} días"
            )

        points.sort(key=lambda p: p.timestamp)
        current = points[-1].price
        previous = points[-2].price if len(points) > 1 else None

        return ProviderResult(
            current_price=current,
            previous_price=previous,
            unit="lb",
            currency="USD",
            history=points,
            source="Alpha Vantage (Global Price of Coffee, mensual)",
            source_url="https://www.alphavantage.co/documentation/#coffee",
            last_updated=points[-1].timestamp,
            is_demo=False,
            demo_reason=None,
        )

    # -- Respaldo demo --------------------------------------------------
    def _fallback_demo(
        self, period_days: int, coffee_type: str, reason: str
    ) -> ProviderResult:
        # Reutiliza el mismo demo que international.py para no duplicar datos.
        with open(DEMO_FILE, encoding="utf-8") as f:
            payload = json.load(f)

        series_info = payload["arabica"] if coffee_type == "arabica" else payload["robusta"]
        series = series_info["series"]
        dates_sorted = sorted(series.keys())
        end_date = datetime.fromisoformat(dates_sorted[-1])
        start_date = end_date - timedelta(days=period_days)

        points = [
            PricePoint(timestamp=datetime.fromisoformat(d), price=v)
            for d, v in series.items()
            if datetime.fromisoformat(d) >= start_date
        ]
        points.sort(key=lambda p: p.timestamp)

        unit = "lb" if coffee_type == "arabica" else "ton"
        current = points[-1].price if points else 0.0
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
            source="Datos DEMO (Alpha Vantage y Yahoo Finance no disponibles)",
            source_url=None,
            last_updated=points[-1].timestamp if points else datetime.now(timezone.utc),
            is_demo=True,
            demo_reason=(
                f"No se pudo consultar Alpha Vantage ({reason}). "
                "Mostrando serie de demostración calibrada con cotizaciones "
                "públicas reales, no un precio en vivo."
            ),
        )