# Informe de optimización de rendimiento — Coffee Market Intelligence

**Fecha:** 15 de octubre de 2026
**Ámbito:** Mejoras de rendimiento bajo carga concurrente
**Estado:** Verificado con pruebas de carga de 199 usuarios simultáneos durante 48 minutos

---

## 1. Resumen ejecutivo

El proyecto pasó de **colapsar con 199 usuarios concurrentes** (p50 de 15 000 ms, RPS de 8.4) a **servirlos con p50 de 140 ms y 120 RPS sostenidos**. La mejora principal fue un factor de ~100× en latencia mediana y ~14× en throughput.

En el camino aparecieron y se resolvieron tres cuellos de botella encadenados:

| # | Cuello | Causa raíz | Solución aplicada |
|---|---|---|---|
| 1 | Caché de precios roto | Filtro por `timestamp` (fecha del dato) en vez de `fetched_at` (fecha de inserción) | Añadir columna `fetched_at` y filtrar por ella |
| 2 | Caché de TRM ausente | `get_trm()` golpeaba datos.gov.co en cada request | Caché en memoria con TTL |
| 3 | Pool de conexiones agotado | 199 usuarios concurrentes vs. 60 conexiones máximas | Ampliar `pool_size` y `max_overflow` |

---

## 2. Punto de partida

### 2.1 Síntoma inicial

Con 199 usuarios concurrentes simulados con Locust:

| Métrica | Valor |
|---|---|
| p50 (mediana) | 15 000 ms |
| p95 | 34 000 ms |
| p99 | 37 000 ms |
| RPS agregado | 8.4 |
| Fallos | 0 |

Todos los endpoints tardaban entre 6 y 27 segundos. La app era funcional pero **inutilizable bajo carga real**.

### 2.2 Diagnóstico

Se identificaron tres causas independientes que se sumaban:

1. **Sin caché efectivo**: cada request golpeaba Yahoo Finance, datos.gov.co o el boletín FNC en vivo. Sin red disponible, caía al demo tras esperar el timeout del provider (6 s por defecto).

2. **Caché implementado pero roto**: existía una capa de caché que filtraba por `PriceRecord.timestamp`, que es la fecha del dato según el provider (puede ser de hace semanas en un demo). El filtro `timestamp >= now - 15 min` nunca encontraba nada.

3. **Escrituras concurrentes sin deduplicar**: cada consulta, incluso con caché, insertaba un `PriceRecord` nuevo. Con 199 usuarios, cuando la caché expiraba, todos escribían a la vez → contención de SQLite.

---

## 3. Cambios aplicados

### 3.1 Añadir columna `fetched_at` a `PriceRecord`

**Archivo:** `app/models/price.py`

**Motivo:** separar dos conceptos que se estaban mezclando.

- `timestamp` → cuándo **ocurrió** el precio según el provider (fecha del tick en Yahoo, fecha del dato en un demo).
- `fetched_at` → cuándo **guardamos** nosotros el registro.

El caché debe usar `fetched_at` ("¿hace cuánto consultamos?"), no `timestamp` ("¿de cuándo es el dato?").

**Cambio:**

```python
class PriceRecord(Base):
    __tablename__ = "price_records"

    # ... columnas existentes ...

    # -- timestamp: cuándo OCURRIÓ el precio según el provider.
    timestamp: Mapped[datetime] = mapped_column(
        DateTime, index=True, default=lambda: datetime.now(timezone.utc)
    )

    # -- fetched_at: cuándo GUARDAMOS este registro nosotros.
    #    Es el campo correcto para el caché.
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime, index=True, default=lambda: datetime.now(timezone.utc)
    )