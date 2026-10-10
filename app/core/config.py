"""
Configuración central de la aplicación.

Todos los valores sensibles o dependientes del entorno (API keys, URL de
base de datos, diferenciales de precio, etc.) se leen desde variables de
entorno / archivo .env — nunca hardcodeados. Ver `.env.example` en la raíz
del proyecto para la lista completa de variables reconocidas y dónde
conseguir cada API key.
"""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # --- General ---
    app_name: str = "Coffee Market Intelligence"
    environment: str = "development"  # development | production
    debug: bool = True

    # --- Base de datos ---
    # SQLite por defecto para desarrollo. En producción, apuntar a Postgres:
    # postgresql+psycopg2://usuario:password@host:5432/coffee_market
    database_url: str = "sqlite:///./data/coffee_market.db"

    # --- Proveedor internacional (Yahoo Finance - no requiere API key) ---
    # Ticker de futuros de café arábica (ICE, vía Yahoo Finance). Ver
    # app/providers/international.py para más contexto.
    international_arabica_ticker: str = "KC=F"
    # El futuro de robusta no tiene un ticker "continuo" confiable y gratuito
    # confirmado al momento de construir esta app (ver README, sección de
    # fuentes de datos). Se deja configurable para poder actualizarlo sin
    # tocar código.
    international_robusta_ticker: str = "RM=F"
    international_provider_timeout_seconds: float = 6.0

    # --- Alpha Vantage (opcional, respaldo/histórico mensual de commodities) ---
    # Obtener clave gratuita en https://www.alphavantage.co/support/#api-key
    alpha_vantage_api_key: str | None = None

    # --- TRM / Banco de la República ---
    # Banco de la República migró su portal de series históricas durante 2026
    # (ver README). Se deja configurable un endpoint de datos abiertos y un
    # timeout corto para no bloquear el dashboard si el servicio cambia.
    trm_open_data_url: str = (
        "https://www.datos.gov.co/resource/32sa-8pi3.json"
    )
    currency_provider_timeout_seconds: float = 6.0

    # --- Precio nacional (Federación Nacional de Cafeteros) ---
    # La FNC publica el precio interno de referencia como boletín (PDF/HTML)
    # diario, no como API JSON estable (ver README). fnc_bulletin_url queda
    # configurable para quien quiera automatizar la lectura de ese boletín.
    fnc_bulletin_url: str = "https://federaciondecafeteros.org/estadisticas-cafeteras/"
    # Diferencial de referencia del café colombiano frente al contrato C de
    # Nueva York, en centavos de USD por libra. Se usa SOLO para estimar
    # (no para publicar como oficial) el precio interno cuando no hay un
    # valor oficial cargado manualmente. Debe calibrarse periódicamente
    # comparando contra el boletín oficial — ver README.
    colombia_price_differential_usd_cents_per_lb: float = 8.0

    # --- Caché de proveedores ---
    # Minutos que se considera "fresco" un precio antes de volver a
    # intentar consultarlo en la fuente externa.
    price_cache_minutes: int = 15

    # --- Seguridad / CORS ---
    allowed_origins: list[str] = ["http://localhost:8000", "http://127.0.0.1:8000"]


@lru_cache
def get_settings() -> Settings:
    """Settings como singleton cacheado (evita releer .env en cada request)."""
    return Settings()
