"""
CurrencyProvider — Tasa Representativa del Mercado (TRM), COP por USD.

Fuente primaria intentada: portal de datos abiertos de Colombia
(datos.gov.co), API SODA de Socrata, dataset histórico de TRM del Banco de
la República. NOTA IMPORTANTE (ver README): el Banco de la República
migró durante 2026 a un nuevo "Portal de Estadísticas Económicas", por lo
que el dataset clásico de datos.gov.co podría estar desactualizado o
descontinuado para cuando despliegues esta app. Verifica
`TRM_OPEN_DATA_URL` en `.env` contra https://www.banrep.gov.co/es/estadisticas/trm
antes de asumir que el valor en vivo es correcto — por defecto, cualquier
fallo cae automáticamente a datos demo.
"""
import json
from datetime import datetime, timedelta,timezone
from pathlib import Path

import requests

from app.core.config import get_settings
from app.providers.base import BaseProvider, PricePoint, ProviderResult

DEMO_FILE = Path(__file__).resolve().parent.parent.parent / "data" / "demo_trm.json"


class CurrencyProvider(BaseProvider):
    name = "currency"

    def __init__(self) -> None:
        self.settings = get_settings()

    def get_price(self, period_days: int, **kwargs) -> ProviderResult:
        try:
            return self._fetch_open_data(period_days)
        except Exception as exc:  # noqa: BLE001
            return self._fallback_demo(period_days, reason=str(exc))

    def _fetch_open_data(self, period_days: int) -> ProviderResult:
        params = {"$order": "vigenciadesde DESC", "$limit": str(min(period_days + 5, 2000))}
        resp = requests.get(
            self.settings.trm_open_data_url, params=params,
            timeout=self.settings.currency_provider_timeout_seconds,
        )
        resp.raise_for_status()
        rows = resp.json()
        if not isinstance(rows, list) or not rows:
            raise ValueError("El dataset de TRM no devolvió filas (¿URL desactualizada?)")

        points: list[PricePoint] = []
        for row in rows:
            valor = row.get("valor")
            fecha = row.get("vigenciadesde") or row.get("vigencia_desde")
            if valor is None or fecha is None:
                continue
            try:
                points.append(PricePoint(timestamp=datetime.fromisoformat(fecha[:19]), price=float(valor)))
            except (ValueError, TypeError):
                continue
        if not points:
            raise ValueError("No se pudieron interpretar las filas devueltas por el dataset de TRM")

        points.sort(key=lambda p: p.timestamp)
        current = points[-1].price
        previous = points[-2].price if len(points) > 1 else None

        return ProviderResult(
            current_price=current,
            previous_price=previous,
            unit="COP",
            currency="COP",
            history=points,
            source="Datos Abiertos Colombia (datos.gov.co) - Banco de la República",
            source_url=self.settings.trm_open_data_url,
            last_updated=points[-1].timestamp,
            is_demo=False,
        )

    def _fallback_demo(self, period_days: int, reason: str) -> ProviderResult:
        with open(DEMO_FILE, encoding="utf-8") as f:
            payload = json.load(f)
        series = payload["series"]
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
        current = points[-1].price if points else 0.0
        previous = points[-2].price if len(points) > 1 else None

        return ProviderResult(
            current_price=current,
            previous_price=previous,
            unit="COP",
            currency="COP",
            history=points,
            source="Datos DEMO / histórico (fuente de TRM no disponible)",
            source_url=None,
            last_updated=points[-1].timestamp if points else datetime.now(timezone.utc),
            is_demo=True,
            demo_reason=(
                f"No se pudo consultar la fuente de TRM en vivo ({reason}). "
                "Mostrando serie de demostración calibrada con valores "
                "oficiales reportados públicamente en fechas puntuales."
            ),
        )
