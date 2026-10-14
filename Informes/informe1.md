# Informe de correcciones y mejoras — Coffee Market Intelligence

**Fecha:** 14 de octubre de 2026
**Autor:** Equipo de desarrollo
**Alcance:** Corrección de deuda técnica acumulada, verificación de la suite de
pruebas y cierre de huecos documentados en `ARQUITECTURA_Y_GUIA_DEL_PROYECTO.md`.

---

## 1. Resumen ejecutivo

El proyecto pasó de un estado en el que **la suite de integración nunca se había
ejecutado** (según la documentación previa) a un estado completamente verificado:

| Métrica | Antes | Ahora |
|---|---|---|
| Tests ejecutables con `pytest` real | 69 unitarios (runner casero) | **100 con `pytest`** |
| Tests de integración | 24 sin ejecutar nunca | **31 pasando** |
| Tests smoke contra fuentes reales | No existían | **3 pasando** (`-m live`) |
| Deprecation warnings | 18 | **10** (solo de SQLAlchemy interno + tests) |
| Cadena de fallback de precios internacionales | Yahoo → demo | **Yahoo → Alpha Vantage → demo** |
| CI/CD | No existía | **GitHub Actions configurado** (2 jobs) |

**Todos los cambios son compatibles con el comportamiento previo:** la API
pública, los schemas Pydantic y el frontend no se modificaron. Solo se
endureció la implementación interna de los providers y se amplió la cobertura
de pruebas.

---

## 2. Correcciones realizadas

### 2.1. Migración de `datetime.utcnow()` a `datetime.now(timezone.utc)`

**Motivo:** `datetime.utcnow()` está marcado como deprecado desde Python 3.12
y será eliminado en una versión futura. Además, devuelve un `datetime` "naive"
(sin zona horaria), lo que puede causar bugs sutiles al comparar timestamps
entre mercados o al serializar a JSON.

**Archivos modificados:**

- `app/models/price.py` — columna `PriceRecord.timestamp`
- `app/models/alert.py` — columna `Alert.created_at`
- `app/models/simulation.py` — columna `Simulation.created_at`
- `app/providers/base.py` — campo `ProviderResult.last_updated`
- `app/providers/national.py` — usos puntuales en `_from_manual` y `_fetch_fnc_bulletin`
- `app/providers/international.py` — uso puntual en `_fetch_yahoo`
- `app/providers/currency.py` — uso puntual en `_fetch_open_data`
- `app/services/alert_orchestrator.py` — timestamp en `_apply_evaluation`
- `app/services/export_service.py` — 3 usos en CSV/XLSX/PDF

**Patrón aplicado:**

- En **columnas SQLAlchemy** (`default=`): se usó `lambda` para evitar que
  Python evalúe la expresión una sola vez al definir la clase:
  ```python
  default=lambda: datetime.now(timezone.utc)