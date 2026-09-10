from io import BytesIO

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


BLUE = colors.HexColor("#003366")
LIGHT_BLUE = colors.HexColor("#EAF2FB")
TEXT = colors.HexColor("#17324D")
MUTED = colors.HexColor("#667085")


def _text(value, style):
    return Paragraph(str(value), style)


def _number(value):
    return f"{int(value):,}".replace(",", ".")


def _percent(value):
    return f"{float(value):.2f}%".replace(".", ",")


def _date_label(value):
    if hasattr(value, "strftime"):
        return value.strftime("%d/%m/%Y")
    return pd.to_datetime(value).strftime("%d/%m/%Y")


def gerar_pdf_dashboard(
    data_inicio,
    data_fim,
    kpis: dict,
    df_top: pd.DataFrame,
    df_mix: pd.DataFrame,
    comparativo: pd.DataFrame,
) -> bytes:
    """Gera o relatório PDF com os mesmos dados exibidos no dashboard."""
    output = BytesIO()
    doc = SimpleDocTemplate(
        output,
        pagesize=landscape(A4),
        rightMargin=12 * mm,
        leftMargin=12 * mm,
        topMargin=10 * mm,
        bottomMargin=10 * mm,
        title="Dashboard de Resultados LinkedIn",
        author="Dashboard LinkedIn",
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "PdfTitle", parent=styles["Title"], fontName="Helvetica-Bold", fontSize=18,
        leading=22, textColor=colors.white, alignment=TA_LEFT, spaceAfter=2,
    )
    subtitle_style = ParagraphStyle(
        "PdfSubtitle", parent=styles["Normal"], fontSize=9, textColor=colors.HexColor("#D8E7F5"),
    )
    section_style = ParagraphStyle(
        "PdfSection", parent=styles["Heading2"], fontName="Helvetica-Bold", fontSize=11,
        leading=14, textColor=TEXT, spaceBefore=8, spaceAfter=5,
    )
    body_style = ParagraphStyle(
        "PdfBody", parent=styles["Normal"], fontSize=8, leading=10, textColor=TEXT,
    )
    small_style = ParagraphStyle(
        "PdfSmall", parent=body_style, fontSize=7, leading=9, textColor=MUTED,
    )
    kpi_label_style = ParagraphStyle(
        "PdfKpiLabel", parent=body_style, fontSize=7, alignment=TA_CENTER, textColor=MUTED,
    )
    kpi_value_style = ParagraphStyle(
        "PdfKpiValue", parent=body_style, fontName="Helvetica-Bold", fontSize=15,
        alignment=TA_CENTER, textColor=BLUE,
    )

    story = []
    header = Table(
        [[
            _text("DASHBOARD DE RESULTADOS | LINKEDIN", title_style),
            _text(
                f"Centro de Eventos Padre Vítor Coelho de Almeida<br/>"
                f"Período: {_date_label(data_inicio)} a {_date_label(data_fim)}",
                subtitle_style,
            ),
        ]],
        colWidths=[170 * mm, 95 * mm],
    )
    header.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), BLUE),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.extend([header, Spacer(1, 5 * mm)])

    kpi_values = [
        ("Impressões", _number(kpis.get("impressoes", 0))),
        ("Impressões únicas", _number(kpis.get("impressoes_unicas", 0))),
        ("Cliques", _number(kpis.get("cliques", 0))),
        ("Reações", _number(kpis.get("reacoes", 0))),
        ("Publicações", _number(kpis.get("publicacoes", 0))),
        ("Engajamento médio", _percent(kpis.get("engajamento_medio", 0))),
        ("CTR médio", _percent(kpis.get("ctr_medio", 0))),
        ("Impressões patrocinadas", _number(kpis.get("impressoes_patrocinadas", 0))),
    ]
    kpi_table = Table(
        [[_text(label, kpi_label_style) for label, _ in kpi_values],
         [_text(value, kpi_value_style) for _, value in kpi_values]],
        colWidths=[33.1 * mm] * 8,
    )
    kpi_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.white),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#D9E1EA")),
        ("INNERGRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#E6EAF0")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.extend([kpi_table, Spacer(1, 3 * mm)])

    story.append(_text("Mix de interações", section_style))
    mix_rows = [[_text("Tipo", body_style), _text("Quantidade", body_style), _text("Percentual", body_style)]]
    for _, row in df_mix.iterrows():
        mix_rows.append([
            _text(row.get("tipo", ""), body_style),
            _text(_number(row.get("quantidade", 0)), body_style),
            _text(f"{row.get('percentual', 0):.1f}%".replace(".", ","), body_style),
        ])
    mix_table = Table(mix_rows, colWidths=[55 * mm, 35 * mm, 35 * mm])
    mix_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), LIGHT_BLUE),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#D9E1EA")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(mix_table)

    story.append(_text("Top publicações", section_style))
    top_rows = [[
        _text("Data", body_style), _text("Resumo", body_style), _text("Impressões", body_style),
        _text("Cliques", body_style), _text("Reações", body_style), _text("Engajamento", body_style),
    ]]
    for _, row in df_top.head(6).iterrows():
        data = row.get("data")
        data_label = data.strftime("%d/%m/%Y") if hasattr(data, "strftime") else data
        top_rows.append([
            _text(data_label, small_style),
            _text(str(row.get("resumo", ""))[:100], small_style),
            _text(_number(row.get("impressoes", 0)), small_style),
            _text(_number(row.get("cliques", 0)), small_style),
            _text(_number(row.get("reacoes", 0)), small_style),
            _text(_percent(row.get("engajamento_pct", 0)), small_style),
        ])
    top_table = Table(top_rows, colWidths=[25 * mm, 118 * mm, 28 * mm, 23 * mm, 23 * mm, 30 * mm], repeatRows=1)
    top_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), LIGHT_BLUE),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#D9E1EA")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(top_table)

    story.append(_text("Comparativo mensal", section_style))
    comparison_rows = [[_text(str(column), body_style) for column in comparativo.columns]]
    for _, row in comparativo.iterrows():
        comparison_rows.append([_text(str(row[column]), small_style) for column in comparativo.columns])
    comparison_table = Table(comparison_rows, colWidths=[65 * mm, 45 * mm, 45 * mm], repeatRows=1)
    comparison_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), LIGHT_BLUE),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#D9E1EA")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(comparison_table)

    doc.build(story)
    return output.getvalue()
