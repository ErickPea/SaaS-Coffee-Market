"""Directorio de compradores de café en Colombia (sección 16 del brief)."""
import json
from pathlib import Path

from sqlalchemy.orm import Session

from app.models.seller import Seller
from app.schemas.seller import SellerListOut, SellerOut

SELLERS_JSON = Path(__file__).resolve().parent.parent.parent / "data" / "sellers_colombia.json"


def seed_sellers_if_empty(db: Session) -> None:
    """Carga el directorio curado a la BD la primera vez que se arranca la
    app (idempotente: si ya hay vendedores, no hace nada)."""
    if db.query(Seller).first() is not None:
        return

    with open(SELLERS_JSON, encoding="utf-8") as f:
        payload = json.load(f)

    for item in payload["sellers"]:
        db.add(Seller(
            name=item["name"],
            seller_type=item["seller_type"],
            department=item["department"],
            city=item.get("city"),
            website=item.get("website"),
            public_contact=item.get("public_contact"),
            description=item["description"],
            coffee_types_bought=item.get("coffee_types_bought", []),
            source_note=item["source_note"],
        ))
    db.commit()


def list_sellers(
    db: Session,
    department: str | None = None,
    city: str | None = None,
    seller_type: str | None = None,
    coffee_type: str | None = None,
) -> SellerListOut:
    query = db.query(Seller)
    if department:
        query = query.filter(Seller.department == department)
    if city:
        query = query.filter(Seller.city == city)
    if seller_type:
        query = query.filter(Seller.seller_type == seller_type)

    all_sellers = query.order_by(Seller.department, Seller.name).all()
    if coffee_type:
        all_sellers = [s for s in all_sellers if coffee_type in (s.coffee_types_bought or [])]

    # Las facetas de filtro se calculan sobre el universo completo (sin
    # filtrar), para que el usuario siga viendo todas las opciones posibles.
    everyone = db.query(Seller).all()
    departments_available = sorted({s.department for s in everyone})
    types_available = sorted({s.seller_type for s in everyone})

    return SellerListOut(
        total=len(all_sellers),
        departments_available=departments_available,
        types_available=types_available,
        sellers=[SellerOut.model_validate(s) for s in all_sellers],
    )


def get_seller(db: Session, seller_id: int) -> Seller | None:
    return db.query(Seller).filter(Seller.id == seller_id).first()
