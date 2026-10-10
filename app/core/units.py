"""
Conversión centralizada de unidades de peso usadas en el mercado del café.

IMPORTANTE — LEER ANTES DE MODIFICAR:
Varias de estas unidades son ambiguas fuera de un contexto específico
(especialmente "quintal", que cambia de valor según el país e incluso según
el eslabón de la cadena del café al que se refiera). Las equivalencias de
abajo fueron verificadas contra fuentes públicas colombianas (glosario oficial
de Comités Departamentales de la Federación Nacional de Cafeteros y el
boletín oficial de precio de la FNC) en la fecha indicada en cada constante.
Si vas a cambiar un valor, documenta la fuente igual que aquí.

Todas las conversiones internas de la aplicación pasan primero por
kilogramos (KG) como unidad "pivote". Para agregar una unidad nueva basta
con añadir su factor de conversión A kilogramos: no se necesitan fórmulas
cruzadas entre cada par de unidades.
"""
from enum import Enum


class WeightUnit(str, Enum):
    KG = "kg"
    LB = "lb"
    ARROBA = "arroba"
    CARGA = "carga"
    QUINTAL = "quintal"
    TON = "ton"


# Factor de conversión de cada unidad A kilogramos (1 unidad = X kg).
# Fuente de cada valor documentada al lado.
KG_PER_UNIT: dict[WeightUnit, float] = {
    WeightUnit.KG: 1.0,
    # Libra internacional (avoirdupois). Unidad de peso universal, sin ambigüedad.
    WeightUnit.LB: 0.45359237,
    # Arroba cafetera colombiana = 12.5 kg. Confirmado en los glosarios
    # oficiales de los Comités Departamentales de Cafeteros (Quindío, Cauca,
    # Magdalena, entre otros) — federaciondecafeteros.org, sección "Glosario".
    # OJO: la arroba castellana genérica (~11.5 kg) es DISTINTA; en el
    # contexto cafetero colombiano siempre se usa 12.5 kg.
    WeightUnit.ARROBA: 12.5,
    # Carga de café pergamino seco = 125 kg = 10 arrobas. Es la unidad en la
    # que la FNC publica oficialmente el "precio interno de referencia"
    # (ver boletín diario de precio_cafe.pdf en federaciondecafeteros.org).
    WeightUnit.CARGA: 125.0,
    # Quintal — UNIDAD AMBIGUA, ver nota abajo. Se usa aquí la definición
    # más común en el comercio internacional del café: 100 libras ≈ 45.359 kg.
    # Alternativa documentada: en algunas fuentes colombianas se calcula como
    # 4 arrobas locales (4 × 12.5 kg = 50 kg). Si tu operación usa esa
    # definición, cambia QUINTAL_ALTERNATIVE_KG más abajo y ajústalo aquí.
    WeightUnit.QUINTAL: 45.359237,
    # Tonelada métrica.
    WeightUnit.TON: 1000.0,
}

# Definición alternativa de quintal (4 arrobas colombianas). No se usa por
# defecto; se deja documentada para que quien despliegue la app en una
# cooperativa o región específica pueda saber cuál corresponde a su caso y
# cambiar QUINTAL en KG_PER_UNIT si es necesario.
QUINTAL_ALTERNATIVE_KG = 50.0

UNIT_LABELS: dict[WeightUnit, str] = {
    WeightUnit.KG: "Kilogramo",
    WeightUnit.LB: "Libra",
    WeightUnit.ARROBA: "Arroba (12.5 kg)",
    WeightUnit.CARGA: "Carga (125 kg)",
    WeightUnit.QUINTAL: "Quintal (100 lb ≈ 45.36 kg)",
    WeightUnit.TON: "Tonelada métrica",
}


def to_kg(amount: float, unit: WeightUnit) -> float:
    """Convierte una cantidad en `unit` a kilogramos."""
    if unit not in KG_PER_UNIT:
        raise ValueError(f"Unidad de peso no soportada: {unit}")
    return amount * KG_PER_UNIT[unit]


def from_kg(amount_kg: float, unit: WeightUnit) -> float:
    """Convierte una cantidad en kilogramos a `unit`."""
    if unit not in KG_PER_UNIT:
        raise ValueError(f"Unidad de peso no soportada: {unit}")
    return amount_kg / KG_PER_UNIT[unit]


def convert(amount: float, from_unit: WeightUnit, to_unit: WeightUnit) -> float:
    """Convierte entre dos unidades de peso cualesquiera, vía kilogramos."""
    return from_kg(to_kg(amount, from_unit), to_unit)


def price_per_kg(price: float, unit: WeightUnit) -> float:
    """
    Convierte un precio expresado 'por `unit`' a un precio 'por kilogramo'.
    Ej: price_per_kg(1_400_000, WeightUnit.CARGA) -> precio por kg equivalente
    a una carga de 1'400.000 COP.
    """
    kg_in_unit = KG_PER_UNIT[unit]
    if kg_in_unit <= 0:
        raise ValueError("Factor de conversión inválido")
    return price / kg_in_unit


def price_per_unit(price_per_kg_value: float, unit: WeightUnit) -> float:
    """Convierte un precio 'por kilogramo' a un precio 'por `unit`'."""
    return price_per_kg_value * KG_PER_UNIT[unit]
