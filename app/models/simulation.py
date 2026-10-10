"""Modelos para guardar simulaciones de inversión (sección 21 del brief)."""
import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, Float, ForeignKey, Integer, String, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.price import CoffeeType, Currency


class CostCategory(str, enum.Enum):
    PREPARACION_TERRENO = "preparacion_terreno"
    PLANTULAS = "plantulas"
    FERTILIZANTES = "fertilizantes"
    MANO_DE_OBRA = "mano_de_obra"
    CONTROL_PLAGAS = "control_plagas"
    HERRAMIENTAS = "herramientas"
    TRANSPORTE = "transporte"
    COSECHA = "cosecha"
    PROCESAMIENTO = "procesamiento"
    SECADO = "secado"
    ALMACENAMIENTO = "almacenamiento"
    ADMINISTRACION = "administracion"
    OTROS = "otros"


class Simulation(Base):
    """
    Una simulación guardada de inversión cafetera. Los resultados calculados
    (utilidad, ROI, escenarios, sensibilidad, etc.) se guardan en `results`
    como JSON en el momento de guardar, para que el histórico muestre
    exactamente lo que el usuario vio (aunque luego cambien precios o
    fórmulas). Los insumos crudos también quedan guardados por separado
    para poder "recalcular" si se desea.
    """

    __tablename__ = "simulations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)

    coffee_type: Mapped[CoffeeType] = mapped_column(Enum(CoffeeType))
    hectares: Mapped[float] = mapped_column(Float)
    production_per_hectare_kg: Mapped[float] = mapped_column(Float)

    price_used_per_kg: Mapped[float] = mapped_column(Float)
    price_currency: Mapped[Currency] = mapped_column(Enum(Currency), default=Currency.COP)
    price_source: Mapped[str] = mapped_column(String(50))  # "actual" | "personalizado"

    capital_disponible: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Parámetros de escenario usados (porcentajes), guardados para trazabilidad.
    scenario_params: Mapped[dict] = mapped_column(JSON, default=dict)

    # Resultado completo calculado (totales, escenarios, sensibilidad,
    # oportunidad) tal como se le mostró al usuario al guardar.
    results: Mapped[dict] = mapped_column(JSON, default=dict)

    notes: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    costs: Mapped[list["CostItem"]] = relationship(
        back_populates="simulation", cascade="all, delete-orphan"
    )

    @property
    def costs_by_category(self) -> dict:
        """Desglose de costos como dict plano {categoría: monto} — para
        que `SimulationDetailOut` lo exponga sin que el frontend tenga que
        conocer la relación CostItem. No colisiona con `costs` (la
        relación ORM) porque tiene otro nombre."""
        return {
            (item.category.value if hasattr(item.category, "value") else item.category): item.amount
            for item in self.costs
        }

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Simulation {self.id} '{self.name}' {self.hectares}ha>"


class CostItem(Base):
    __tablename__ = "cost_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    simulation_id: Mapped[int] = mapped_column(ForeignKey("simulations.id"))
    category: Mapped[CostCategory] = mapped_column(Enum(CostCategory))
    amount: Mapped[float] = mapped_column(Float)

    simulation: Mapped["Simulation"] = relationship(back_populates="costs")
