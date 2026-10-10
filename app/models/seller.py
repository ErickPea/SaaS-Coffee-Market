"""
Directorio de compradores de café en Colombia (sección 16 del brief).

Los registros se cargan desde `data/sellers_colombia.json`, un archivo curado
manualmente a partir de fuentes públicas (federaciondecafeteros.org,
directorios de cooperativas por departamento, y reportajes especializados
del sector — ver README para el detalle de cada fuente). No se generan ni
completan compradores automáticamente: si un dato no se pudo verificar en
una fuente pública, el campo queda vacío en vez de inventarse.
"""
import enum

from sqlalchemy import Enum, Integer, String, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class SellerType(str, enum.Enum):
    COOPERATIVA = "cooperativa"
    COMERCIALIZADORA = "comercializadora"
    EXPORTADOR = "exportador"
    TRILLADORA = "trilladora"
    CAFETERIA = "cafeteria"
    TOSTADOR = "tostador"
    COMPRADOR_ESPECIAL = "comprador_especial"
    MERCADO_LOCAL = "mercado_local"
    GREMIO = "gremio"  # entidades institucionales (p.ej. la FNC misma)


class Seller(Base):
    __tablename__ = "sellers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(200), index=True)
    seller_type: Mapped[SellerType] = mapped_column(Enum(SellerType), index=True)
    department: Mapped[str] = mapped_column(String(100), index=True)
    city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    website: Mapped[str | None] = mapped_column(String(300), nullable=True)
    public_contact: Mapped[str | None] = mapped_column(String(300), nullable=True)
    description: Mapped[str] = mapped_column(String(1000))
    coffee_types_bought: Mapped[list] = mapped_column(JSON, default=list)
    source_note: Mapped[str] = mapped_column(String(300))

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Seller {self.name} ({self.seller_type}) {self.department}>"
