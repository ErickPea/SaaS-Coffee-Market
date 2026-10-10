from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.price import CoffeeType, Currency
from app.schemas.investment import CostInput, InvestmentResultOut, ScenarioOut


class SimulationCreate(BaseModel):
    name: str
    coffee_type: CoffeeType
    hectares: float
    production_per_hectare_kg: float
    price_used_per_kg: float
    price_currency: Currency = Currency.COP
    price_source: str
    capital_disponible: float | None = None
    costs: CostInput
    scenario_params: dict = {}
    results: dict
    notes: str | None = None


class SimulationUpdate(BaseModel):
    """Todos los campos opcionales: PATCH solo cambia lo que venga
    informado. Si se envía `costs`, reemplaza el desglose completo (no se
    fusiona categoría por categoría) — igual que como lo arma el frontend
    al reenviar el formulario de edición completo."""
    name: str | None = Field(None, min_length=1)
    coffee_type: CoffeeType | None = None
    hectares: float | None = Field(None, gt=0)
    production_per_hectare_kg: float | None = Field(None, gt=0)
    price_used_per_kg: float | None = Field(None, gt=0)
    price_currency: Currency | None = None
    price_source: str | None = None
    capital_disponible: float | None = Field(None, ge=0)
    costs: CostInput | None = None
    scenario_params: dict | None = None
    results: dict | None = None
    notes: str | None = None


class SimulationSummaryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    created_at: datetime
    coffee_type: CoffeeType
    hectares: float
    total_investment: float | None = None
    profit: float | None = None
    roi_pct: float | None = None


class SimulationDetailOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    created_at: datetime
    coffee_type: CoffeeType
    hectares: float
    production_per_hectare_kg: float
    price_used_per_kg: float
    price_currency: Currency
    price_source: str
    capital_disponible: float | None
    scenario_params: dict
    results: dict
    notes: str | None
    costs_by_category: dict[str, float]
