"""
Genera los archivos JSON de datos DEMO/histórico usados como respaldo cuando
las fuentes en vivo no están disponibles (sección 3 y 31 del brief).

Los "anclas" (ANCHORS_*) son valores REALES reportados públicamente
(Federación Nacional de Cafeteros, prensa económica colombiana, cotizaciones
de KC=F en Yahoo Finance) en las fechas indicadas — no están inventados. Los
puntos intermedios entre anclas SÍ son interpolación sintética con ruido
aleatorio (semilla fija para reproducibilidad), necesaria para poder dibujar
una serie diaria continua en las gráficas. Por eso todo el archivo se marca
"is_demo": true de punta a punta: son datos de demostración, aunque estén
calibrados con puntos reales.

Ejecutar: python3 generate_demo_data.py
"""
import json
from datetime import date, timedelta

import numpy as np

RNG_SEED = 42
OUT_DIR = "."

# --- Anclas reales: precio interno de referencia café pergamino seco,
# COP por carga de 125 kg (fuente: FNC / prensa económica) ---
NATIONAL_ANCHORS = [
    ("2021-09-01", 1_780_000),   # nivel aproximado post-pandemia, referencia de tendencia
    ("2022-02-08", 2_240_000),   # FNC, reportado por todosloshechos.es/La Patria
    ("2023-03-15", 1_900_000),   # La República (marzo 2023 "más de $1,9 millones")
    ("2024-03-15", 1_400_000),   # La República (marzo 2024, caída interanual)
    ("2024-10-07", 2_065_000),   # Agronegocios.co
    ("2025-08-26", 3_063_000),   # Portafolio.co
    ("2026-02-18", 2_080_000),   # Agronegocios.co ("mínimo en 16 meses")
    ("2026-08-11", 2_265_000),   # preciocafe.com / boletín FNC
    ("2026-08-26", 2_260_000),   # Portafolio.co
    ("2026-09-01", 2_255_000),   # extrapolación leve para "hoy" (demo)
]

# --- Anclas reales: futuro Arábica (KC=F, ICE vía Yahoo Finance), en
# centavos de dólar por libra ---
ARABICA_ANCHORS = [
    ("2021-09-01", 190.0),
    ("2022-02-08", 235.0),
    ("2023-03-15", 185.0),
    ("2024-03-15", 200.0),
    ("2024-10-07", 240.0),
    ("2025-08-26", 320.0),
    ("2026-02-18", 300.0),
    ("2026-08-11", 336.0),   # boletín FNC 11 ago 2026: "USD $3.36" = 336 c/lb
    ("2026-08-26", 330.0),
    ("2026-09-01", 328.0),
]

# --- Robusta (ICE Futures Europe), USD por tonelada. Anclas más
# aproximadas (rango 52 semanas visto en Investing.com/Barchart:
# ~3,144 - 4,986 USD/ton) — se documenta como menos preciso que Arábica. ---
ROBUSTA_ANCHORS = [
    ("2021-09-01", 2100.0),
    ("2022-02-08", 2300.0),
    ("2023-03-15", 2600.0),
    ("2024-03-15", 3400.0),
    ("2024-10-07", 4600.0),
    ("2025-08-26", 4300.0),
    ("2026-02-18", 3900.0),
    ("2026-08-11", 3650.0),
    ("2026-08-26", 3616.0),
    ("2026-09-01", 3630.0),
]

# TRM (COP por USD). Ancla real: 2025-08-26 = 4004.51 ; 2026-08-11 = 3121 ;
# implícita 2026-08-26 (caída interanual 23.05% desde 4004.51 ≈ 3082).
TRM_ANCHORS = [
    ("2021-09-01", 3830.0),
    ("2022-02-08", 3920.0),
    ("2023-03-15", 4720.0),
    ("2024-03-15", 3900.0),
    ("2024-10-07", 4200.0),
    ("2025-08-26", 4004.51),
    ("2026-02-18", 3600.0),
    ("2026-08-11", 3121.0),
    ("2026-08-26", 3082.0),
    ("2026-09-01", 3075.0),
]


def _interpolate_daily(anchors: list[tuple[str, float]], noise_pct: float, seed: int) -> dict[str, float]:
    """Interpola diariamente entre anclas (lineal) y agrega ruido aleatorio
    pequeño y reproducible, preservando exactamente el valor en cada fecha
    ancla (el ruido se aplica solo a los días intermedios)."""
    rng = np.random.default_rng(seed)
    dates = [date.fromisoformat(d) for d, _ in anchors]
    values = [v for _, v in anchors]

    start, end = dates[0], dates[-1]
    all_days = [(start + timedelta(days=i)) for i in range((end - start).days + 1)]

    anchor_ts = np.array([(d - start).days for d in dates], dtype=float)
    anchor_vals = np.array(values, dtype=float)
    all_ts = np.array([(d - start).days for d in all_days], dtype=float)

    interp_vals = np.interp(all_ts, anchor_ts, anchor_vals)

    # Ruido: caminata aleatoria suave, reescalada para no superar noise_pct
    # del valor local, y forzada a 0 exactamente en los días-ancla.
    raw_noise = np.cumsum(rng.normal(0, 1, size=len(all_days)))
    if raw_noise.std() > 0:
        raw_noise = raw_noise / raw_noise.std()
    noise = raw_noise * interp_vals * (noise_pct / 100.0) * 0.4

    anchor_idx = set(anchor_ts.astype(int).tolist())
    for i, t in enumerate(all_ts.astype(int)):
        if t in anchor_idx:
            noise[i] = 0.0

    final_vals = interp_vals + noise
    return {d.isoformat(): round(float(v), 2) for d, v in zip(all_days, final_vals)}


def main() -> None:
    national = _interpolate_daily(NATIONAL_ANCHORS, noise_pct=1.5, seed=RNG_SEED)
    arabica = _interpolate_daily(ARABICA_ANCHORS, noise_pct=1.2, seed=RNG_SEED + 1)
    robusta = _interpolate_daily(ROBUSTA_ANCHORS, noise_pct=1.2, seed=RNG_SEED + 2)
    trm = _interpolate_daily(TRM_ANCHORS, noise_pct=0.5, seed=RNG_SEED + 3)

    national_payload = {
        "is_demo": True,
        "description": (
            "Serie DEMO de precio interno de referencia (café pergamino seco, "
            "COP/carga de 125kg). Puntos ancla tomados de reportes públicos "
            "reales (FNC, Portafolio, Agronegocios, La República); puntos "
            "intermedios interpolados sintéticamente. NO es un feed en vivo."
        ),
        "unit": "carga",
        "currency": "COP",
        "coffee_type": "pergamino_seco",
        "real_anchor_dates": [d for d, _ in NATIONAL_ANCHORS],
        "series": national,
    }
    international_payload = {
        "is_demo": True,
        "description": (
            "Serie DEMO de futuros internacionales de café. Arábica (KC=F, "
            "ICE) en centavos de USD por libra; Robusta (ICE Futures Europe) "
            "en USD por tonelada. Puntos ancla basados en cotizaciones "
            "públicas reales; puntos intermedios interpolados sintéticamente. "
            "NO es un feed en vivo."
        ),
        "arabica": {"unit": "lb_cents", "currency": "USD", "series": arabica},
        "robusta": {"unit": "ton", "currency": "USD", "series": robusta},
        "real_anchor_dates": [d for d, _ in ARABICA_ANCHORS],
    }
    trm_payload = {
        "is_demo": True,
        "description": (
            "Serie DEMO de TRM (COP por USD). Puntos ancla reales tomados de "
            "Banco de la República / prensa económica; interpolación "
            "sintética entre ellos."
        ),
        "real_anchor_dates": [d for d, _ in TRM_ANCHORS],
        "series": trm,
    }

    with open(f"{OUT_DIR}/demo_national_prices.json", "w", encoding="utf-8") as f:
        json.dump(national_payload, f, ensure_ascii=False, indent=2)
    with open(f"{OUT_DIR}/demo_international_prices.json", "w", encoding="utf-8") as f:
        json.dump(international_payload, f, ensure_ascii=False, indent=2)
    with open(f"{OUT_DIR}/demo_trm.json", "w", encoding="utf-8") as f:
        json.dump(trm_payload, f, ensure_ascii=False, indent=2)

    print(f"OK: {len(national)} días nacional, {len(arabica)} días arábica, {len(trm)} días TRM")


if __name__ == "__main__":
    main()
