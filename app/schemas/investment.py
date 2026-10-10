from pydantic import BaseModel, Field, model_validator

from app.models.price import CoffeeType, Currency


class CostInput(BaseModel):
    """Costos de producción (sección 10 del brief). Todos en la misma moneda
    que `currency` en InvestmentInput. Los no informados se asumen en 0."""

    preparacion_terreno: float = Field(0, ge=0)
    plantulas: float = Field(0, ge=0)
    fertilizantes: float = Field(0, ge=0)
    mano_de_obra: float = Field(0, ge=0)
    control_plagas: float = Field(0, ge=0)
    herramientas: float = Field(0, ge=0)
    transporte: float = Field(0, ge=0)
    cosecha: float = Field(0, ge=0)
    procesamiento: float = Field(0, ge=0)
    secado: float = Field(0, ge=0)
    almacenamiento: float = Field(0, ge=0)
    administracion: float = Field(0, ge=0)
    otros: float = Field(0, ge=0)

    def total(self) -> float:
        return sum(self.model_dump().values())


class InvestmentInput(BaseModel):
    coffee_type: CoffeeType = CoffeeType.PERGAMINO_SECO
    hectares: float = Field(..., gt=0)
    production_per_hectare_kg: float = Field(..., gt=0)

    use_current_price: bool = True
    custom_price_per_kg: float | None = Field(None, gt=0)
    currency: Currency = Currency.COP

    capital_disponible: float | None = Field(None, ge=0)

    costs: CostInput = Field(default_factory=CostInput)

    @model_validator(mode="after")
    def _validar_precio_personalizado(self) -> "InvestmentInput":
        if not self.use_current_price and not self.custom_price_per_kg:
            raise ValueError(
                "Si use_current_price es falso, custom_price_per_kg es obligatorio"
            )
        return self


class CostBreakdownOut(BaseModel):
    by_category: dict[str, float]
    # Agrupación conceptual de las 13 categorías en los 4 grandes bloques
    # que pide la sección 11 del brief (costos iniciales / operativos /
    # producción / logísticos). Es solo para presentación: el total no
    # cambia sin importar cómo se agrupe.
    iniciales: float
    operativos: float
    produccion: float
    logisticos: float
    total: float


class CapitalAnalysisOut(BaseModel):
    capital_disponible: float
    inversion_requerida: float
    alcanza: bool
    faltante: float | None = None
    sobrante: float | None = None
    hectareas_cubribles: float


class InvestmentResultOut(BaseModel):
    coffee_type: CoffeeType
    hectares: float
    production_per_hectare_kg: float
    total_production_kg: float

    price_per_kg: float
    price_currency: Currency
    price_source: str  # "actual" | "personalizado"

    cost_breakdown: CostBreakdownOut
    total_investment: float
    total_income: float
    profit: float
    roi_pct: float
    margin_pct: float
    break_even_kg: float

    capital_analysis: CapitalAnalysisOut | None = None


class ScenarioParamsIn(BaseModel):
    """Porcentajes configurables de los escenarios (sección 12 del brief)."""
    pessimist_price_pct: float = -15.0
    pessimist_production_pct: float = -10.0
    pessimist_cost_pct: float = 10.0
    optimist_price_pct: float = 15.0
    optimist_production_pct: float = 10.0
    optimist_cost_pct: float = 0.0


class ScenarioOut(BaseModel):
    name: str  # "pesimista" | "esperado" | "optimista"
    label: str
    result: InvestmentResultOut


class ScenarioComparisonOut(BaseModel):
    scenarios: list[ScenarioOut]
    params_used: ScenarioParamsIn


class SensitivityPointOut(BaseModel):
    price_delta_pct: float
    price_per_kg: float
    total_income: float
    profit: float
    roi_pct: float
    break_even_kg: float


class SensitivityResultOut(BaseModel):
    base_price_per_kg: float
    points: list[SensitivityPointOut]


class OpportunityAnalysisOut(BaseModel):
    opportunity_score: float = Field(..., ge=0, le=100)
    volatility_score: float = Field(..., ge=0, le=100)
    price_sensitivity_score: float = Field(..., ge=0, le=100)
    margin_score: float = Field(..., ge=0, le=100)
    explanation: dict[str, str]
    disclaimer: str = (
        "Esta herramienta es informativa y no constituye asesoría financiera. "
        "Los resultados son estimaciones basadas en los datos suministrados y "
        "en precios de referencia; no garantizan rentabilidad."
    )
