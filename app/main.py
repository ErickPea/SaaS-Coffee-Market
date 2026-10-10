"""
Coffee Market Intelligence — punto de entrada de la aplicación FastAPI.

Ejecutar con: python run.py  (ver README para más detalle)
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api import alerts, currency, investments, markets, prices, sellers, simulations, views
from app.core.config import get_settings
from app.core.database import SessionLocal, init_db
from app.services.seller_service import seed_sellers_if_empty

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    db = SessionLocal()
    try:
        seed_sellers_if_empty(db)
    finally:
        db.close()
    yield


app = FastAPI(
    title=settings.app_name,
    description=(
        "API de análisis del mercado del café colombiano e internacional, y "
        "simulador de inversión cafetera. Ver /docs para la documentación "
        "interactiva generada automáticamente."
    ),
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="app/static"), name="static")

app.include_router(views.router)
app.include_router(prices.router)
app.include_router(markets.router)
app.include_router(currency.router)
app.include_router(investments.router)
app.include_router(sellers.router)
app.include_router(simulations.router)
app.include_router(alerts.router)


@app.get("/api/health", tags=["health"])
def health():
    return {"status": "ok", "app": settings.app_name, "environment": settings.environment}
