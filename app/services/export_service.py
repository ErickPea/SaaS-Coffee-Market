"""
Exportación de una simulación a CSV, Excel y PDF (sección 22 del brief).

Cada exportador recibe un diccionario ya armado por la API (no objetos
Pydantic/SQLAlchemy directamente), para poder probarse con datos planos de
Python sin necesitar esas dependencias instaladas.

Estructura de contenido en los tres formatos (igual en todos, sección 22):
    Resumen · Datos introducidos · Precio utilizado · Costos · Ingresos ·
    Utilidad · ROI · Punto de equilibrio · Escenarios · Gráficas ·
    Advertencias · Fecha de generación · Fuente de datos
"""
import csv
import io
from datetime import datetime, timezone

DISCLAIMER = (
    "Los resultados son estimaciones basadas en los datos proporcionados por el "
    "usuario y en los precios disponibles. Los precios del café pueden variar y "
    "los resultados no garantizan rentabilidad. Esta herramienta no constituye "
    "asesoría financiera."
)

COST_LABELS = {
    "preparacion_terreno": "Preparación del terreno", "plantulas": "Plántulas",
    "fertilizantes": "Fertilizantes", "mano_de_obra": "Mano de obra",
    "control_plagas": "Control de plagas", "herramientas": "Herramientas",
    "transporte": "Transporte", "cosecha": "Cosecha", "procesamiento": "Procesamiento",
    "secado": "Secado", "almacenamiento": "Almacenamiento",
    "administracion": "Administración", "otros": "Otros",
}


def _fmt_cop(value: float) -> str:
    return f"${value:,.0f}"


# ----------------------------------------------------------------- CSV ----
def export_csv(sim: dict) -> io.StringIO:
    buf = io.StringIO()
    w = csv.writer(buf)

    w.writerow(["Coffee Market Intelligence - Resumen de simulación"])
    w.writerow(["Nombre", sim["name"]])
    w.writerow(["Fecha de generación", datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")])
    w.writerow(["Fuente de precio", sim["price_source"]])
    w.writerow([])

    w.writerow(["Datos introducidos"])
    w.writerow(["Tipo de café", sim["coffee_type"]])
    w.writerow(["Hectáreas", sim["hectares"]])
    w.writerow(["Producción por hectárea (kg)", sim["production_per_hectare_kg"]])
    w.writerow(["Precio utilizado (COP/kg)", sim["price_per_kg"]])
    w.writerow([])

    w.writerow(["Costos"])
    for cat, label in COST_LABELS.items():
        w.writerow([label, sim["costs"].get(cat, 0)])
    w.writerow(["TOTAL INVERSIÓN", sim["total_investment"]])
    w.writerow([])

    w.writerow(["Resultados"])
    w.writerow(["Producción total (kg)", sim["total_production_kg"]])
    w.writerow(["Ingresos", sim["total_income"]])
    w.writerow(["Utilidad", sim["profit"]])
    w.writerow(["ROI (%)", sim["roi_pct"]])
    w.writerow(["Margen (%)", sim["margin_pct"]])
    w.writerow(["Punto de equilibrio (kg)", sim["break_even_kg"]])
    w.writerow([])

    if sim.get("scenarios"):
        w.writerow(["Comparación de escenarios"])
        w.writerow(["Escenario", "Inversión", "Ingresos", "Utilidad", "ROI (%)"])
        for s in sim["scenarios"]:
            w.writerow([s["label"], s["total_investment"], s["total_income"], s["profit"], s["roi_pct"]])
        w.writerow([])

    w.writerow(["Advertencia"])
    w.writerow([DISCLAIMER])

    buf.seek(0)
    return buf


# --------------------------------------------------------------- Excel ----
def export_excel(sim: dict) -> io.BytesIO:
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter

    wb = Workbook()
    ws = wb.active
    ws.title = "Resumen"

    header_fill = PatternFill(start_color="1F4D3A", end_color="1F4D3A", fill_type="solid")
    header_font = Font(color="FFFFFF", bold=True, name="Arial", size=12)
    bold = Font(bold=True, name="Arial")
    normal = Font(name="Arial")

    def write(row, col, value, font=normal):
        cell = ws.cell(row=row, column=col, value=value)
        cell.font = font
        return cell

    r = 1
    ws.merge_cells(f"A{r}:B{r}")
    write(r, 1, "Coffee Market Intelligence — Resumen de simulación", header_font).fill = header_fill
    ws.cell(row=r, column=2).fill = header_fill
    r += 2

    write(r, 1, "Nombre", bold); write(r, 2, sim["name"]); r += 1
    write(r, 1, "Fecha de generación", bold); write(r, 2, datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")); r += 1
    write(r, 1, "Fuente de precio", bold); write(r, 2, sim["price_source"]); r += 2

    write(r, 1, "Datos introducidos", bold); r += 1
    for label, value in [
        ("Tipo de café", sim["coffee_type"]), ("Hectáreas", sim["hectares"]),
        ("Producción por hectárea (kg)", sim["production_per_hectare_kg"]),
        ("Precio utilizado (COP/kg)", sim["price_per_kg"]),
    ]:
        write(r, 1, label); write(r, 2, value); r += 1
    r += 1

    write(r, 1, "Costos", bold); r += 1
    for cat, label in COST_LABELS.items():
        write(r, 1, label); write(r, 2, sim["costs"].get(cat, 0)); r += 1
    write(r, 1, "TOTAL INVERSIÓN", bold); write(r, 2, sim["total_investment"], bold); r += 2

    write(r, 1, "Resultados", bold); r += 1
    for label, value in [
        ("Producción total (kg)", sim["total_production_kg"]), ("Ingresos", sim["total_income"]),
        ("Utilidad", sim["profit"]), ("ROI (%)", sim["roi_pct"]), ("Margen (%)", sim["margin_pct"]),
        ("Punto de equilibrio (kg)", sim["break_even_kg"]),
    ]:
        write(r, 1, label); write(r, 2, value); r += 1
    r += 1

    if sim.get("scenarios"):
        write(r, 1, "Comparación de escenarios", bold); r += 1
        for c, h in enumerate(["Escenario", "Inversión", "Ingresos", "Utilidad", "ROI (%)"], start=1):
            write(r, c, h, bold)
        r += 1
        for s in sim["scenarios"]:
            write(r, 1, s["label"]); write(r, 2, s["total_investment"])
            write(r, 3, s["total_income"]); write(r, 4, s["profit"]); write(r, 5, s["roi_pct"])
            r += 1
        r += 1

    ws.merge_cells(f"A{r}:B{r + 2}")
    cell = write(r, 1, DISCLAIMER)
    cell.alignment = Alignment(wrap_text=True, vertical="top")
    cell.font = Font(italic=True, size=9, name="Arial")

    ws.column_dimensions[get_column_letter(1)].width = 30
    ws.column_dimensions[get_column_letter(2)].width = 22

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf


# ----------------------------------------------------------------- PDF ----
def export_pdf(sim: dict) -> io.BytesIO:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import cm
    from reportlab.platypus import (
        Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
    )

    FOREST = colors.HexColor("#1F4D3A")
    SAGE_PALE = colors.HexColor("#E4EDE6")

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("TitleCM", parent=styles["Title"], textColor=FOREST, fontSize=18)
    h2 = ParagraphStyle("H2CM", parent=styles["Heading2"], textColor=FOREST, spaceBefore=14)
    normal = styles["Normal"]
    small_italic = ParagraphStyle("SmallItalic", parent=styles["Normal"], fontSize=8, textColor=colors.grey)

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=letter,
        topMargin=1.8 * cm, bottomMargin=1.8 * cm, leftMargin=1.8 * cm, rightMargin=1.8 * cm,
    )
    story = []

    story.append(Paragraph("Coffee Market Intelligence", title_style))
    story.append(Paragraph(f"Resumen de simulación de inversión — {sim['name']}", styles["Heading3"]))
    story.append(Paragraph(
        f"Generado: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')} &nbsp;&nbsp;|&nbsp;&nbsp; "
        f"Fuente de precio: {sim['price_source']}", small_italic,
    ))
    story.append(Spacer(1, 12))

    def table_from_rows(rows, col_widths=None):
        t = Table(rows, colWidths=col_widths, hAlign="LEFT")
        t.setStyle(TableStyle([
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
            ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.white, SAGE_PALE]),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("LINEBELOW", (0, 0), (-1, -1), 0.4, colors.HexColor("#DDE3DC")),
        ]))
        return t

    story.append(Paragraph("Datos introducidos", h2))
    story.append(table_from_rows([
        ["Tipo de café", str(sim["coffee_type"])],
        ["Hectáreas", f"{sim['hectares']:g}"],
        ["Producción por hectárea", f"{sim['production_per_hectare_kg']:g} kg"],
        ["Precio utilizado", f"{_fmt_cop(sim['price_per_kg'])} / kg"],
    ], col_widths=[7 * cm, 8 * cm]))

    story.append(Paragraph("Costos", h2))
    cost_rows = [["Categoría", "Valor (COP)"]]
    for cat, label in COST_LABELS.items():
        cost_rows.append([label, _fmt_cop(sim["costs"].get(cat, 0))])
    cost_rows.append(["TOTAL INVERSIÓN", _fmt_cop(sim["total_investment"])])
    story.append(table_from_rows(cost_rows, col_widths=[7 * cm, 8 * cm]))

    story.append(Paragraph("Resultados: ingresos, utilidad, ROI y punto de equilibrio", h2))
    story.append(table_from_rows([
        ["Producción total", f"{sim['total_production_kg']:,.0f} kg"],
        ["Ingresos", _fmt_cop(sim["total_income"])],
        ["Utilidad", _fmt_cop(sim["profit"])],
        ["ROI", f"{sim['roi_pct']:.2f}%"],
        ["Margen", f"{sim['margin_pct']:.2f}%"],
        ["Punto de equilibrio", f"{sim['break_even_kg']:,.1f} kg"],
    ], col_widths=[7 * cm, 8 * cm]))

    if sim.get("scenarios"):
        story.append(Paragraph("Comparación de escenarios", h2))
        rows = [["Escenario", "Inversión", "Ingresos", "Utilidad", "ROI"]]
        for s in sim["scenarios"]:
            rows.append([
                s["label"], _fmt_cop(s["total_investment"]), _fmt_cop(s["total_income"]),
                _fmt_cop(s["profit"]), f"{s['roi_pct']:.1f}%",
            ])
        story.append(table_from_rows(rows, col_widths=[3.5 * cm, 3.6 * cm, 3.6 * cm, 3.6 * cm, 2.3 * cm]))
        story.append(Spacer(1, 10))

        chart_flowable = _scenario_bar_chart(sim["scenarios"])
        if chart_flowable is not None:
            story.append(Paragraph("Gráfica: ingresos, inversión y utilidad por escenario", h2))
            story.append(chart_flowable)

    story.append(Spacer(1, 16))
    story.append(Paragraph("Advertencia", h2))
    story.append(Paragraph(DISCLAIMER, normal))

    doc.build(story)
    buf.seek(0)
    return buf


def _scenario_bar_chart(scenarios: list[dict]):
    """Gráfica de barras (Inversión/Ingresos/Utilidad por escenario) para
    incrustar en el PDF, usando reportlab.graphics (sin dependencias
    adicionales)."""
    try:
        from reportlab.graphics.charts.barcharts import VerticalBarChart
        from reportlab.graphics.charts.legends import Legend
        from reportlab.graphics.shapes import Drawing
        from reportlab.lib import colors as rl_colors
    except ImportError:  # pragma: no cover
        return None

    data = [
        [s["total_investment"] for s in scenarios],
        [s["total_income"] for s in scenarios],
        [s["profit"] for s in scenarios],
    ]
    labels = [s["label"] for s in scenarios]

    drawing = Drawing(430, 200)
    chart = VerticalBarChart()
    chart.x, chart.y = 40, 30
    chart.width, chart.height = 320, 140
    chart.data = data
    chart.categoryAxis.categoryNames = labels
    chart.bars[0].fillColor = rl_colors.HexColor("#5C6B60")
    chart.bars[1].fillColor = rl_colors.HexColor("#1F4D3A")
    chart.bars[2].fillColor = rl_colors.HexColor("#7A4A2E")
    chart.valueAxis.valueMin = 0
    chart.groupSpacing = 14
    chart.barSpacing = 2

    legend = Legend()
    legend.alignment = "right"
    legend.x = 375
    legend.y = 110
    legend.colorNamePairs = [
        (rl_colors.HexColor("#5C6B60"), "Inversión"),
        (rl_colors.HexColor("#1F4D3A"), "Ingresos"),
        (rl_colors.HexColor("#7A4A2E"), "Utilidad"),
    ]
    legend.fontSize = 7
    legend.dy = 6
    legend.dx = 6

    drawing.add(chart)
    drawing.add(legend)
    return drawing
