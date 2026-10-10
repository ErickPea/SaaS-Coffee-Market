from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.investment import (
    InvestmentInput, InvestmentResultOut, OpportunityAnalysisOut,
    ScenarioComparisonOut, ScenarioParamsIn, SensitivityResultOut,
)
from app.services.investment_orchestrator import InvestmentCalculator

router = APIRouter(prefix="/api/investment", tags=["investment"])
calculator = InvestmentCalculator()


@router.post("/calculate", response_model=InvestmentResultOut)
def calculate(payload: InvestmentInput, db: Session = Depends(get_db)):
    """Sección 11: inversión, producción, ingresos, utilidad, ROI, margen y punto de equilibrio."""
    return calculator.calculate(payload, db)


@router.post("/scenarios", response_model=ScenarioComparisonOut)
def scenarios(
    payload: InvestmentInput,
    params: ScenarioParamsIn = ScenarioParamsIn(),
    db: Session = Depends(get_db),
):
    """Sección 12: comparación pesimista / esperado / optimista."""
    return calculator.scenarios(payload, params, db)


@router.post("/sensitivity", response_model=SensitivityResultOut)
def sensitivity(payload: InvestmentInput, db: Session = Depends(get_db)):
    """Sección 13: ¿qué pasa si cambia el precio del café? (-30% .. +30%)."""
    return calculator.sensitivity(payload, db)


@router.post("/opportunity", response_model=OpportunityAnalysisOut)
def opportunity(payload: InvestmentInput, db: Session = Depends(get_db)):
    """Sección 15: análisis de oportunidad (nivel de oportunidad, volatilidad,
    sensibilidad al precio, margen) — siempre con la explicación de cómo se
    calculó cada puntaje y el descargo de responsabilidad financiera."""
    return calculator.opportunity_analysis(payload, db)
