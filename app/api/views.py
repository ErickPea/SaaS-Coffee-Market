from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates

router = APIRouter(tags=["views"])

templates = Jinja2Templates(directory="app/templates")

NAV_ITEMS = [
    {"path": "/", "label": "Dashboard"},
    {"path": "/mercados", "label": "Mercados"},
    {"path": "/simulador", "label": "Simulador de inversión"},
    {"path": "/vendedores", "label": "Dónde vender"},
    {"path": "/historial", "label": "Historial"},
    {"path": "/alertas", "label": "Alertas"},
]


def _ctx(request: Request, active: str, **extra):
    return {
        "request": request,
        "nav_items": NAV_ITEMS,
        "active": active,
        **extra,
    }


@router.get("/")
def dashboard(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context=_ctx(request, "/"),
    )


@router.get("/mercados")
def markets(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="markets.html",
        context=_ctx(request, "/mercados"),
    )


@router.get("/simulador")
def investment(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="investment.html",
        context=_ctx(request, "/simulador"),
    )


@router.get("/vendedores")
def sellers(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="sellers.html",
        context=_ctx(request, "/vendedores"),
    )


@router.get("/historial")
def simulations(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="simulations.html",
        context=_ctx(request, "/historial"),
    )


@router.get("/alertas")
def alerts(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="alerts.html",
        context=_ctx(request, "/alertas"),
    )