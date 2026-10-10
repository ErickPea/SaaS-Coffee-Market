from fastapi import APIRouter, Query

from app.services import currency_service

router = APIRouter(prefix="/api/currency", tags=["currency"])


@router.get("")
def get_currency(period_days: int = Query(30, ge=1, le=1825)):
    """Sección 19: TRM actual, última actualización y variación."""
    trm = currency_service.get_trm(period_days)
    return {
        "usd_cop": trm.rate,
        "previous_usd_cop": trm.previous_rate,
        "change_abs": trm.change_abs,
        "change_pct": round(trm.change_pct, 3) if trm.change_pct is not None else None,
        "last_updated": trm.last_updated,
        "source": trm.source,
        "source_url": trm.source_url,
        "is_demo": trm.is_demo,
        "demo_reason": trm.demo_reason,
    }


@router.get("/convert")
def convert_currency(amount: float = Query(..., gt=0), from_currency: str = Query(...), to_currency: str = Query(...)):
    trm = currency_service.get_trm().rate
    from_c, to_c = from_currency.upper(), to_currency.upper()

    if from_c == to_c:
        result = amount
    elif from_c == "USD" and to_c == "COP":
        result = currency_service.usd_to_cop(amount, trm)
    elif from_c == "COP" and to_c == "USD":
        result = currency_service.cop_to_usd(amount, trm)
    else:
        return {"error": f"Conversión {from_c}->{to_c} no soportada en esta versión (solo USD<->COP)."}

    return {"amount": amount, "from_currency": from_c, "to_currency": to_c, "result": round(result, 4), "trm_used": trm}
