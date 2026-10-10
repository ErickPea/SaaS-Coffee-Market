from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.seller import SellerListOut, SellerOut
from app.services import seller_service

router = APIRouter(prefix="/api/sellers", tags=["sellers"])


@router.get("", response_model=SellerListOut)
def list_sellers(
    department: str | None = Query(None),
    city: str | None = Query(None),
    seller_type: str | None = Query(None),
    coffee_type: str | None = Query(None),
    db: Session = Depends(get_db),
):
    """Sección 16: directorio de compradores, con filtros por departamento,
    ciudad, tipo de comprador y tipo de café."""
    return seller_service.list_sellers(db, department, city, seller_type, coffee_type)


@router.get("/{seller_id}", response_model=SellerOut)
def get_seller(seller_id: int, db: Session = Depends(get_db)):
    seller = seller_service.get_seller(db, seller_id)
    if seller is None:
        raise HTTPException(404, "Comprador no encontrado")
    return seller
