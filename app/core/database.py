"""
Configuración de base de datos con SQLAlchemy 2.x.

Usa SQLite por defecto (cero configuración para desarrollo) y queda lista
para apuntar a PostgreSQL en producción con solo cambiar DATABASE_URL en
`.env` — el resto del código (modelos, servicios) no cambia.
"""
from collections.abc import Generator
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import get_settings

settings = get_settings()

# Aseguramos que exista la carpeta data/ para SQLite antes de conectar.
if settings.database_url.startswith("sqlite"):
    Path("data").mkdir(parents=True, exist_ok=True)

connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}

engine = create_engine(settings.database_url, connect_args=connect_args, echo=False)

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
    # Importar los modelos aquí (no arriba) evita ciclos de importación:
    # los modelos importan Base desde este módulo.
    from app.models import alert, price, seller, simulation  # noqa: F401

    Base.metadata.create_all(bind=engine)
