import io

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.simulation import CostItem, Simulation
from app.schemas.simulation import SimulationCreate, SimulationDetailOut, SimulationSummaryOut, SimulationUpdate
from app.services import export_service

router = APIRouter(prefix="/api/simulations", tags=["simulations"])


@router.post("", response_model=SimulationDetailOut)
def create_simulation(payload: SimulationCreate, db: Session = Depends(get_db)):
    """Sección 21: guardar una simulación con nombre para consultarla después."""
    sim = Simulation(
        name=payload.name,
        coffee_type=payload.coffee_type,
        hectares=payload.hectares,
        production_per_hectare_kg=payload.production_per_hectare_kg,
        price_used_per_kg=payload.price_used_per_kg,
        price_currency=payload.price_currency,
        price_source=payload.price_source,
        capital_disponible=payload.capital_disponible,
        scenario_params=payload.scenario_params,
        results=payload.results,
        notes=payload.notes,
    )
    db.add(sim)
    db.flush()  # asigna sim.id sin cerrar la transacción

    for category, amount in payload.costs.model_dump().items():
        db.add(CostItem(simulation_id=sim.id, category=category, amount=amount))

    db.commit()
    db.refresh(sim)
    return sim


@router.get("", response_model=list[SimulationSummaryOut])
def list_simulations(db: Session = Depends(get_db)):
    sims = db.query(Simulation).order_by(Simulation.created_at.desc()).all()
    out = []
    for s in sims:
        results = s.results or {}
        out.append(SimulationSummaryOut(
            id=s.id, name=s.name, created_at=s.created_at, coffee_type=s.coffee_type,
            hectares=s.hectares,
            total_investment=results.get("total_investment"),
            profit=results.get("profit"),
            roi_pct=results.get("roi_pct"),
        ))
    return out


@router.get("/{simulation_id}", response_model=SimulationDetailOut)
def get_simulation(simulation_id: int, db: Session = Depends(get_db)):
    sim = db.query(Simulation).filter(Simulation.id == simulation_id).first()
    if sim is None:
        raise HTTPException(404, "Simulación no encontrada")
    return sim


@router.patch("/{simulation_id}", response_model=SimulationDetailOut)
def update_simulation(simulation_id: int, payload: SimulationUpdate, db: Session = Depends(get_db)):
    """Sección 5 (esta ronda): editar una simulación guardada. Solo cambia
    los campos que vengan informados; si se envía `costs`, reemplaza el
    desglose completo de costos."""
    sim = db.query(Simulation).filter(Simulation.id == simulation_id).first()
    if sim is None:
        raise HTTPException(404, "Simulación no encontrada")

    changes = payload.model_dump(exclude_unset=True, exclude={"costs"})
    for field, value in changes.items():
        setattr(sim, field, value)

    if payload.costs is not None:
        db.query(CostItem).filter(CostItem.simulation_id == sim.id).delete()
        for category, amount in payload.costs.model_dump().items():
            db.add(CostItem(simulation_id=sim.id, category=category, amount=amount))

    db.commit()
    db.refresh(sim)
    return sim


@router.delete("/{simulation_id}", status_code=204)
def delete_simulation(simulation_id: int, db: Session = Depends(get_db)):
    sim = db.query(Simulation).filter(Simulation.id == simulation_id).first()
    if sim is None:
        raise HTTPException(404, "Simulación no encontrada")
    db.delete(sim)  # cascade="all, delete-orphan" en la relación borra sus CostItem
    db.commit()


def _simulation_to_export_dict(sim: Simulation) -> dict:
    results = sim.results or {}
    costs = {c.category.value if hasattr(c.category, "value") else c.category: c.amount for c in sim.costs}
    return {
        "name": sim.name,
        "price_source": sim.price_source,
        "coffee_type": sim.coffee_type.value if hasattr(sim.coffee_type, "value") else sim.coffee_type,
        "hectares": sim.hectares,
        "production_per_hectare_kg": sim.production_per_hectare_kg,
        "price_per_kg": sim.price_used_per_kg,
        "costs": costs,
        "total_investment": results.get("total_investment", 0),
        "total_production_kg": results.get("total_production_kg", 0),
        "total_income": results.get("total_income", 0),
        "profit": results.get("profit", 0),
        "roi_pct": results.get("roi_pct", 0),
        "margin_pct": results.get("margin_pct", 0),
        "break_even_kg": results.get("break_even_kg", 0),
        "scenarios": results.get("scenarios"),
    }


@router.get("/{simulation_id}/export/{fmt}")
def export_simulation(simulation_id: int, fmt: str, db: Session = Depends(get_db)):
    """Sección 22: exportar una simulación guardada a csv | xlsx | pdf."""
    sim = db.query(Simulation).filter(Simulation.id == simulation_id).first()
    if sim is None:
        raise HTTPException(404, "Simulación no encontrada")

    data = _simulation_to_export_dict(sim)
    filename_base = f"simulacion_{sim.id}"

    if fmt == "csv":
        buf = export_service.export_csv(data)
        return StreamingResponse(
            io.BytesIO(buf.getvalue().encode("utf-8-sig")), media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="{filename_base}.csv"'},
        )
    if fmt == "xlsx":
        buf = export_service.export_excel(data)
        return StreamingResponse(
            buf, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f'attachment; filename="{filename_base}.xlsx"'},
        )
    if fmt == "pdf":
        buf = export_service.export_pdf(data)
        return StreamingResponse(
            buf, media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename_base}.pdf"'},
        )
    raise HTTPException(400, "Formato no soportado. Use csv, xlsx o pdf.")
