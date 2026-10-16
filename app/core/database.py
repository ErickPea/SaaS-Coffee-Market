"""
Configuración de base de datos con SQLAlchemy 2.x.

Usa SQLite por defecto (cero configuración para desarrollo) y queda lista
para apuntar a PostgreSQL en producción con solo cambiar DATABASE_URL en
`.env` — el resto del código (modelos, servicios) no cambia.

Configuración específica de SQLite:
  - WAL mode: permite lecturas concurrentes mientras hay una escritura
    en curso. Sin esto, SQLite bloquea toda la BD en cada INSERT/UPDATE.
  - busy_timeout: si la BD está bloqueada, espera hasta 5 s antes de
    rendirse (evita "database is locked" en cargas concurrentes).
  - synchronous=NORMAL: trade-off razonable entre velocidad y durabilidad.
"""
from collections.abc import Generator
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import get_settings

settings = get_settings()

# Aseguramos que exista la carpeta data/ para SQLite antes de conectar.
if settings.database_url.startswith("sqlite"):
    Path("data").mkdir(parents=True, exist_ok=True)

connect_args = (
    {"check_same_thread": False}
    if settings.database_url.startswith("sqlite")
    else {}
)

engine = create_engine(
    settings.database_url,
    connect_args=connect_args,
    echo=False,
    # Con 199 usuarios concurrentes y WAL mode, necesitamos un pool grande.
    # SQLite sí soporta N lectores simultáneos; los escritores se serializan
    # con busy_timeout. No hay límite duro de conexiones de lectura con WAL.
    pool_size=500,
    max_overflow=600,     # total: 150 conexiones máximo
    pool_pre_ping=True,
    pool_recycle=3600,    # recicla conexiones cada hora (por si el SO las cierra)
    pool_timeout=10,      # si el pool está lleno, espera 10 s (antes 30 s)
                          # — mejor fallar rápido que colgar la request 30 s
)


# --- Configuración específica de SQLite: WAL + busy_timeout ----------------
if settings.database_url.startswith("sqlite"):

    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_connection, _connection_record):
        """Se ejecuta en CADA nueva conexión a SQLite."""
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.execute("PRAGMA busy_timeout=5000")
        cursor.close()


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """Clase base declarativa para todos los modelos ORM."""
    pass


def get_db() -> Generator[Session, None, None]:
    """Dependencia de FastAPI: entrega una sesión de BD y la cierra al final."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Crea todas las tablas registradas en Base.metadata (si no existen)."""
    from app.models import alert, price, seller, simulation  # noqa: F401

    Base.metadata.create_all(bind=engine)