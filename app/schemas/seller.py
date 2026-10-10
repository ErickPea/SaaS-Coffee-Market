from pydantic import BaseModel, ConfigDict

from app.models.seller import SellerType


class SellerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    seller_type: SellerType
    department: str
    city: str | None
    website: str | None
    public_contact: str | None
    description: str
    coffee_types_bought: list[str]
    source_note: str


class SellerListOut(BaseModel):
    total: int
    departments_available: list[str]
    types_available: list[str]
    sellers: list[SellerOut]
