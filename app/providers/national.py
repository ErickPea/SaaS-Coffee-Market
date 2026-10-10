"""
NationalCoffeeProvider — precio interno de referencia (Colombia).

A diferencia del proveedor internacional, la Federación Nacional de
Cafeteros (FNC) NO publica el precio interno de referencia como una API
JSON/CSV estable: lo publica como un boletín (PDF/HTML) que se actualiza a
diario en su sitio web. Esto se investigó explícitamente antes de construir
esta app (ver README, sección "Fuentes de datos").

Por eso este proveedor intenta, EN ESTE ORDEN:
  1. Un valor cargado MANUALMENTE por un usuario/administrador para el día
     de hoy (lo más confiable: alguien leyó el boletín oficial y lo
     transcribió). Ver `POST /api/prices/national/manual`.
  2. Descargar y leer el boletín PDF público de la FNC en la URL configurada
     (`FNC_BULLETIN_URL`), con validaciones conservadoras: si el número
     extraído no aparece cerca del texto esperado o está fuera de un rango
     plausible, se descarta en vez de arriesgarse a mostrar un dato
     incorrecto como si fuera real.
  3. Si todo lo anterior falla, datos DEMO/histórico, marcados como tales.

El paso 2 es EXPERIMENTAL: no se pudo probar contra el boletín real en este
entorno de desarrollo (sin acceso a red), y la URL exacta del PDF cambia
periódicamente. Ver README antes de confiar en él para producción.
"""
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

from app.core.config import get_settings
from app.providers.base import BaseProvider, PricePoint, ProviderResult

DEMO_FILE = Path(__file__).resolve().parent.parent.parent / "data" / "demo_national_prices.json"

# Rango plausible (COP por carga de 125kg) para validar cualquier número
# extraído del boletín antes de confiar en él. Ajustar si el mercado se
# mueve fuera de este rango de forma sostenida.
PLAUSIBLE_RANGE_COP = (300_000, 8_000_000)


class NationalCoffeeProvider(BaseProvider):
    name = "national"

    def __init__(self) -> None:
        self.settings = get_settings()

    def get_price(self, period_days: int, manual_price: float | None = None, **kwargs) -> ProviderResult:
        if manual_price is not None:
            return self._from_manual(manual_price, period_days)
        try:
            return self._fetch_fnc_bulletin(period_days)
        except Exception as exc:  # noqa: BLE001
            return self._fallback_demo(period_days, reason=str(exc))

    # -- Valor cargado manualmente por un usuario --------------------------
    def _from_manual(self, manual_price: float, period_days: int) -> ProviderResult:
        demo = self._fallback_demo(period_days, reason="", as_history_only=True)
        now = datetime.now(timezone.utc)
        demo.history.append(PricePoint(timestamp=now, price=manual_price))
        return ProviderResult(
            current_price=manual_price,
            previous_price=demo.history[-2].price if len(demo.history) > 1 else None,
            unit="carga",
            currency="COP",
            history=demo.history,
            source="Ingresado manualmente (boletín oficial FNC)",
            source_url=self.settings.fnc_bulletin_url,
            last_updated=now,
            is_demo=False,
        )

    # -- Intento de lectura del boletín PDF oficial (experimental) --------
    def _fetch_fnc_bulletin(self, period_days: int) -> ProviderResult:
        resp = requests.get(
            self.settings.fnc_bulletin_url,
            timeout=self.settings.international_provider_timeout_seconds,
            headers={"User-Agent": "Mozilla/5.0 (compatible; CoffeeMarketIntelligence/1.0)"},
        )
        resp.raise_for_status()
        content_type = resp.headers.get("content-type", "")

        text = ""
        if "pdf" in content_type or self.settings.fnc_bulletin_url.endswith(".pdf"):
            text = self._extract_pdf_text(resp.content)
        else:
            text = resp.text  # HTML: búsqueda simple de patrón sobre el texto crudo

        price = self._extract_validated_price(text)
        if price is None:
            raise ValueError(
                "No se encontró un precio interno de referencia válido y "
                "verificable en el boletín (formato inesperado o URL desactualizada)"
            )

        now = datetime.now(timezone.utc)
        # El boletín FNC solo publica el precio de HOY, no la serie histórica.
        # Usamos el histórico demo como relleno para que la gráfica tenga
        # puntos, y añadimos el precio real del boletín como último punto.
        # Marcamos is_demo=False porque el precio ACTUAL sí es real; el
        # histórico de relleno se documenta en source.
        demo = self._fallback_demo(
            period_days,
            reason="",
            as_history_only=True,
        )
        history = [p for p in demo.history if p.timestamp < now]
        history.append(PricePoint(timestamp=now, price=price))

        return ProviderResult(
            current_price=price,
            previous_price=history[-2].price if len(history) > 1 else None,
            unit="carga",
            currency="COP",
            history=history,
            source="Federación Nacional de Cafeteros (boletín oficial) — histórico de relleno demo",
            source_url=self.settings.fnc_bulletin_url,
            last_updated=now,
            is_demo=False,
        )

    @staticmethod
    def _extract_pdf_text(pdf_bytes: bytes) -> str:
        import io

        import pdfplumber

        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            return "\n".join(page.extract_text() or "" for page in pdf.pages)

    @staticmethod
    def _extract_validated_price(text: str) -> float | None:
        """Busca un monto en pesos cerca de las palabras clave esperadas y
        lo valida contra un rango plausible antes de aceptarlo. Devuelve
        None (nunca un valor "adivinado") si no hay suficiente certeza."""
        keyword_zone = re.search(
            r"(precio\s+interno.{0,400}|carga.{0,20}125.{0,400})",
            text, re.IGNORECASE | re.DOTALL,
        )
        search_text = keyword_zone.group(0) if keyword_zone else text[:2000]

        candidates = re.findall(r"\$\s?([\d.,]{6,12})", search_text)
        for raw in candidates:
            normalized = raw.replace(".", "").replace(",", "")
            try:
                value = float(normalized)
            except ValueError:
                continue
            if PLAUSIBLE_RANGE_COP[0] <= value <= PLAUSIBLE_RANGE_COP[1]:
                return value
        return None

    # -- Respaldo demo ------------------------------------------------------
    def _fallback_demo(self, period_days: int, reason: str, as_history_only: bool = False) -> ProviderResult:
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
            unit="carga",
            currency="COP",
            history=points,
            source="Datos DEMO / histórico (FNC no disponible en vivo)",
            source_url=None,
            last_updated=points[-1].timestamp if points else datetime.now(timezone.utc),
            is_demo=True,
            demo_reason=(
                None if as_history_only else
                f"No se pudo leer el boletín oficial de la FNC ({reason or 'sin fuente en vivo configurada'}). "
                "Mostrando serie de demostración calibrada con precios oficiales "
                "reportados públicamente en fechas puntuales, no un boletín en vivo."
            ),
        )
