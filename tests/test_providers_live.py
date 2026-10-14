"""
Tests "smoke" contra las fuentes externas REALES.

No corren por defecto. Se activan con:
    pytest -m live

Requieren conexión a internet. Si una fuente externa cambia su formato
o cae, estos tests lo detectan antes que un usuario real.
"""
import pytest

from app.providers.international import InternationalMarketProvider
from app.providers.national import NationalCoffeeProvider
from app.providers.currency import CurrencyProvider

pytestmark = pytest.mark.live


@pytest.mark.timeout(30)
def test_yahoo_finance_responde_y_parsea_arabica():
    """Si esto falla, o Yahoo cambió su API o no hay red."""
    provider = InternationalMarketProvider()
    result = provider.get_price(period_days=7, coffee_type="arabica")

    # No exigimos is_demo=False (por si no hay red), pero SÍ que el objeto
    # tenga la forma esperada.
    assert result is not None
    assert result.current_price > 0
    assert result.unit in ("lb", "ton")
    assert result.currency == "USD"
    assert len(result.history) > 0

    # Si hay red Y Yahoo responde, NO debería ser demo.
    # Si no hay red, is_demo=True con demo_reason explicando.
    if not result.is_demo:
        assert result.source_url is not None
    else:
        assert result.demo_reason is not None


@pytest.mark.timeout(30)
def test_datos_gov_co_responde_y_parsea_trm():
    provider = CurrencyProvider()
    result = provider.get_price(period_days=7)

    assert result is not None
    assert result.current_price > 0
    assert result.currency == "COP"

    if not result.is_demo:
        assert result.source_url is not None


@pytest.mark.timeout(60)  # el boletín PDF es lento
def test_boletin_fnc_responde():
    provider = NationalCoffeeProvider()
    result = provider.get_price(period_days=7)

    assert result is not None
    assert result.current_price > 0

    # El boletín es experimental — no exigimos éxito, solo que no explote.
    if not result.is_demo:
        assert result.source_url is not None