# Coffee Market Intelligence

Plataforma de análisis del mercado del café (nacional colombiano e internacional) y simulador de inversión cafetera. Construida con FastAPI + SQLAlchemy + Jinja2/Chart.js, siguiendo una arquitectura de proveedores de datos que permite reemplazar cualquier fuente externa sin tocar el resto de la app.

> **Antes de usarla para decisiones reales, lee la sección [Estado real de los datos](#estado-real-de-los-datos-lee-esto) — es la parte más importante de este documento.**

---

## 1. Instalación y ejecución

```bash
cd coffee-market
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

pip install -r requirements.txt

cp .env.example .env            # ajusta valores si quieres usar APIs con clave

python run.py                   # arranca en http://localhost:8000
```

Al arrancar por primera vez, la app crea `data/coffee_market.db` (SQLite) y carga el directorio de compradores automáticamente. La documentación interactiva de la API queda disponible en `http://localhost:8000/docs`.

### Ejecutar las pruebas

```bash
pytest
```

Sin instalar nada, también puedes correr `python3 run_tests_no_pytest.py` desde la raíz del proyecto — es el mismo mini-runner que se usó para validar esta entrega (ver sección 2), útil solo como referencia rápida; una vez tengas `requirements.txt` instalado, usa `pytest` normal.

---

## 2. ⚠️ Nota de transparencia sobre cómo se construyó esto (actualizado — segunda ronda)

Esta aplicación se escribió en un entorno sin acceso a internet. En la primera ronda no se pudo instalar `fastapi`/`sqlalchemy`/`pydantic`/`uvicorn`. En esta segunda ronda se intentó de nuevo explícitamente (incluyendo `uv` y un entorno virtual aparte) y se confirmó que sigue bloqueado a nivel de red (egress), no por configuración local. Para no quedarme en "no se pudo probar", se hizo lo siguiente:

- **Se separó `investment_service.py`** (motor de cálculo puro) de **`investment_orchestrator.py`** (capa que sí usa Pydantic/SQLAlchemy) — así el motor de cálculo se puede importar y probar con Python plano, sin ningún framework instalado.
- **Se creó un shim mínimo de `pydantic_settings`** (`tests/conftest.py`, ~30 líneas, solo se activa si el paquete real no está instalado) que permite importar `app.core.config` y, con eso, **los tres providers reales** (`international.py`, `national.py`, `currency.py`) — y probarlos de verdad con `unittest.mock` interceptando `requests.get`, sin tocar la red.
- **Se generó un PDF real con `reportlab`** para probar la extracción con `pdfplumber` en `national.py` contra un archivo real, no un mock de texto.
- **Se escribió un mini-runner compatible con pytest** (`run_tests_no_pytest.py`, no es parte de la entrega — bórralo cuando quieras) que soporta fixtures, `pytest.approx`, `pytest.raises` y `@patch`, para poder ejecutar toda la suite y obtener un conteo real de aprobados/fallidos sin pytest instalado.

Con esto, **69 pruebas se ejecutaron de verdad** (units, motor de cálculo, exportación, los 3 providers con mocks de red, TRM histórica). Ver la sección 7 para el detalle y qué NO se pudo ejecutar (los tests de integración con `TestClient`, que si necesitan FastAPI real).



---

## 3. Qué está implementado y qué falta

| Fase (según el brief) | Estado |
|---|---|
| 1-2. Arquitectura y estructura de carpetas | ✅ Completo |
| 3. Providers con fallback a demo, nunca datos falsos como "en vivo" | ✅ Completo |
| 4-7. Mercado internacional/nacional, selectores, comparación | ✅ Completo |
| 8-9. Dashboard y gráficas | ✅ Completo |
| 10-11. Calculadora de inversión (todos los cálculos) | ✅ Completo y probado |
| 12-13. Escenarios y análisis de sensibilidad | ✅ Completo y probado |
| 14-15. Capital disponible y análisis de oportunidad | ✅ Completo |
| 16. Directorio de compradores (Colombia) | ✅ Completo — 21 organizaciones reales investigadas |
| 17. Colombia como centro del proyecto | ✅ (departamentos cafeteros representados en el directorio) |
| 18-19. Conversor de unidades y monedas | ✅ Completo y probado |
| 20. Alertas de precio | ✅ Completo (CRUD, activar/desactivar, evaluación automática y manual) |
| 21. Historial de simulaciones | ✅ Completo — crear, listar, obtener, **editar (recalcula), eliminar** |
| 22. Exportación PDF/Excel/CSV | ✅ Completo y probado (los 3 formatos) |
| 23. Diseño UI/UX | ✅ Sistema de diseño propio (verde bosque/blanco/gris + acentos café) |
| 25. API documentada (FastAPI /docs) | ✅ Automático vía FastAPI |
| 32-34. Validaciones y advertencia financiera | ✅ Completo |
| 12 (pruebas automatizadas) | ✅ 69 pruebas unitarias/provider ejecutadas de verdad. Integración con `TestClient` escrita, no ejecutable en este sandbox (ver sección 7) |

---

## 4. Estado real de los datos — LEE ESTO

Se investigaron fuentes reales antes de escribir código (no se inventó ningún proveedor). Así quedó cada una:

### Café internacional (Arábica / Robusta)
- **Fuente:** endpoint público de gráficos de Yahoo Finance (`query1.finance.yahoo.com/.../chart/KC=F`), sin necesidad de API key.
- **Arábica confirmado:** el ticker `KC=F` (futuro Coffee C de ICE) sí existe y se usa ampliamente en el ecosistema financiero abierto (es lo que usa la librería `yfinance`).
- **Robusta sin confirmar:** no encontré un ticker "continuo" gratuito 100% confiable para Robusta al momento de construir esto. Quedó configurable (`INTERNATIONAL_ROBUSTA_TICKER` en `.env`); si Yahoo no lo reconoce, la app cae automáticamente a datos demo — **nunca mostrará un número inventado como si fuera real.**
- Es un endpoint *no oficial* de Yahoo: puede cambiar sin aviso. Por eso todo está en `try/except` con fallback.

### Café nacional (precio interno de referencia, Colombia)
- La Federación Nacional de Cafeteros **no publica una API JSON/CSV estable** — publica un boletín (PDF) diario en su sitio. Esto se confirmó buscando explícitamente antes de programar.
- La app intenta, en este orden: **(1)** un valor que tú ingreses manualmente leyendo el boletín oficial (`POST /api/prices/national/manual` — así es como lo haría una persona real hoy), **(2)** descargar y leer el PDF del boletín con `pdfplumber` (experimental, con validación conservadora del número extraído — nunca antes probado contra el PDF real), **(3)** datos demo.
- Los datos demo del precio nacional están **anclados a cifras reales reportadas públicamente** (no son aleatorios): 11 ago 2026 = $2.265.000/carga, 26 ago 2026 = $2.260.000/carga (fuente: boletín FNC vía prensa económica), 26 ago 2025 = $3.063.000/carga (Portafolio), entre otras — ver `data/generate_demo_data.py` para la lista completa con sus fuentes. Los puntos *entre* esas fechas ancla sí son interpolación sintética.

### TRM (tasa de cambio)
- Se intenta el dataset histórico de TRM en datos.gov.co (API Socrata, sin API key). **Banco de la República migró de portal durante 2026** — verifica `TRM_OPEN_DATA_URL` contra <https://www.banrep.gov.co/es/estadisticas/trm> antes de asumir que el dataset clásico sigue vigente.
- Demo anclado igualmente a valores reales: TRM real informada de \$4.004,51 (26 ago 2025) y \$3.121 (11 ago 2026).

### Unidades de peso (sección 18 del brief)
Se investigó específicamente porque el brief pedía no asumir conversiones ambiguas:
- **1 arroba (café, Colombia) = 12,5 kg** — confirmado en glosarios oficiales de comités departamentales de la FNC.
- **1 carga = 125 kg = 10 arrobas** — confirmado en el boletín oficial de precio de la FNC.
- **1 quintal = AMBIGUO.** Se usó por defecto 100 lb ≈ 45,36 kg (definición más común en el comercio internacional del café), pero algunas fuentes colombianas calculan el quintal como 4 arrobas locales (= 50 kg). Ver `app/core/units.py` — está documentado y es un solo número para cambiar si tu operación usa la otra convención.

### Directorio de compradores (sección 16)
21 organizaciones reales (no inventadas): la FNC, Almacafé, Expocafé, Buencafé, Procafecol/Juan Valdez, Racafé, Carcafé, Sucafina, Olam, Louis Dreyfus, Nutresa/Colcafé, y 9 cooperativas departamentales (Antioquia, Caldas, Huila, Cauca, Nariño, Quindío, Risaralda), más 2 exportadoras de especialidad. Cada registro incluye de dónde salió el dato en `source_note`. Cuando no pude verificar un sitio web o teléfono con confianza, se dejó vacío **a propósito** en vez de inventarlo — ver `data/sellers_colombia.json`.

---

## 5. Arquitectura

```
Provider (fuente externa) → Service (lógica/orquestación) → API (FastAPI) → Frontend (Jinja2 + JS + Chart.js)
```

- **`app/providers/`** — un `BaseProvider` común; `international.py`, `national.py`, `currency.py` lo implementan. Cada uno SIEMPRE devuelve un resultado (nunca lanza una excepción hacia arriba): si la fuente en vivo falla, cae a demo y lo marca con `is_demo=True` + `demo_reason`.
- **`app/services/`** — lógica de negocio. `investment_service.py` está deliberadamente separado en dos capas: funciones puras de Python (sin Pydantic/SQLAlchemy, fáciles de probar) + una clase orquestadora que sí usa los schemas de la API.
- **`app/models/` + `app/schemas/`** — SQLAlchemy (persistencia) y Pydantic (validación/serialización de la API), separados como pide el brief.
- **`app/api/`** — un router por área (`prices`, `markets`, `currency`, `investments`, `sellers`, `simulations`) + `views.py` para las páginas HTML.
- **`app/templates/` + `app/static/`** — Jinja2 server-side + JS vanilla (sin framework) + Chart.js.

### Cambiar de proveedor de datos en el futuro
Escribe una clase nueva que herede de `BaseProvider` e implemente `get_price()`, y reemplázala en `app/services/price_service.py` (dos líneas). El resto de la aplicación no se entera del cambio.

---

## 6. Variables de entorno

Ver `.env.example` — cada variable está comentada con qué hace y, cuando aplica, dónde conseguir la clave. Ninguna clave está escrita en el código.

---

## 7. Pruebas automatizadas — estado real

**Ejecutadas de verdad en este entorno (69/69 pasaron)** vía `python3 run_tests_no_pytest.py` (mini-runner compatible con pytest, ver sección 2). Con `pytest` real instalado deberían pasar igual:

- `tests/test_units.py` (7) — conversión de unidades.
- `tests/test_investment_service.py` (18) — motor de cálculo puro: totales, capital, escenarios, sensibilidad, oportunidad.
- `tests/test_export_service.py` (3) — CSV/Excel/PDF, con inspección visual del PDF.
- `tests/test_alert_service.py` (6) — las 4 condiciones de alerta + casos límite.
- `tests/test_currency_service.py` (5) — TRM histórica alineada por fecha (`build_trm_lookup`): fecha exacta, intermedia, fuera de rango, sin histórico.
- `tests/test_international_provider.py` (13), `test_currency_provider.py` (7), `test_national_provider.py` (10) — los 3 providers reales con `requests` mockeado (éxito, respuesta inválida, vacía, timeout, error HTTP, ticker no encontrado) + un PDF real generado con reportlab para probar la extracción con pdfplumber.

**Escritas pero NO ejecutables en este sandbox** (necesitan FastAPI/pytest reales, no las cubre el shim):
- `tests/test_api_integration.py` — `TestClient` contra los endpoints de prices, markets, currency, investments, sellers, simulations (ciclo completo crear/editar/eliminar) y alerts (ciclo completo + disparo automático al consultar precio). 24 casos. Sintaxis verificada con `py_compile`; lógica revisada línea por línea contra cada endpoint real, pero nunca se ejecutó.

**Falta por completo:** tests de providers para Alpha Vantage (no se usa actualmente) y pruebas de carga/concurrencia.

---

## 8. Próximos pasos sugeridos (no incluidos en esta entrega)

1. **Ejecutar de verdad `pytest tests/test_api_integration.py`** en una máquina con `requirements.txt` instalado — es el mayor hueco de cobertura real que queda.
2. **Probar de verdad la integración en vivo** (Yahoo Finance, datos.gov.co, boletín FNC) en una máquina con internet, y ajustar los `try/except` según los errores reales que aparezcan.
3. **Notificaciones reales de alertas** — hoy la alerta cambia de estado a "disparada" y queda visible en `/alertas`, pero no envía email/SMS/push. Sería la extensión natural.
4. **Editar simulaciones con cambio de tipo de café o de mercado de precio** — la edición actual recalcula con el mismo tipo de café original; cambiar de tipo de café en la edición requeriría exponer ese campo también en el formulario de edición.

---

## 9. Estructura del proyecto

```
coffee-market/
├── app/
│   ├── main.py                  # arranque de FastAPI, monta routers y estáticos
│   ├── api/                     # routers: prices, markets, currency, investments, sellers, simulations, alerts, views
│   ├── core/                    # config (.env), database (SQLAlchemy), units (conversor)
│   ├── models/                  # ORM: price, simulation, seller, alert
│   ├── schemas/                 # Pydantic: price, investment, simulation, seller, alert
│   ├── services/                # investment_service (puro) + investment_orchestrator, price_service, market_service,
│   │                             # currency_service, seller_service, export_service, alert_service (puro) + alert_orchestrator
│   ├── providers/                # fuentes externas (international, national, currency) + base común
│   ├── templates/                # Jinja2: dashboard, markets, investment, sellers, simulations, alerts
│   └── static/{css,js}
├── data/                        # JSON demo (anclados a cifras reales) + directorio de compradores
├── tests/                        # 8 archivos, 69 pruebas ejecutadas + 1 de integración (ver sección 7)
├── run_tests_no_pytest.py       # mini-runner temporal, no es parte de la entrega (ver sección 2)
├── .env.example
├── requirements.txt
└── run.py
```

---

## 10. Advertencia

Esta herramienta es informativa y no constituye asesoría financiera. Los resultados son estimaciones basadas en los datos suministrados y en precios de referencia; no garantizan rentabilidad. Los precios del café pueden variar significativamente.


pytest -v                    # suite normal, sin live (rápido, determinista)
pytest -v -m live            # solo los smoke tests contra fuentes reales
pytest -v -m "live or not live"   # todo