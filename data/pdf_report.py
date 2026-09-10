from io import BytesIO
import pandas as pd
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
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
    """Gera o relatório PDF corporativo com formatação limpa e alinhada."""
    output = BytesIO()
    doc = SimpleDocTemplate(
        output,
        pagesize=landscape(A4),
        rightMargin=10 * mm,
        leftMargin=10 * mm,
        topMargin=10 * mm,
        bottomMargin=10 * mm,
        title="Dashboard de Resultados LinkedIn",
        author="Dashboard LinkedIn",
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "PdfTitle", parent=styles["Title"], fontName="Helvetica-Bold", fontSize=16,
        leading=20, textColor=colors.white, alignment=TA_LEFT, spaceAfter=2,
    )
    subtitle_style = ParagraphStyle(
        "PdfSubtitle", parent=styles["Normal"], fontSize=8.5, textColor=colors.HexColor("#D8E7F5"),
    )
    section_style = ParagraphStyle(
        "PdfSection", parent=styles["Heading2"], fontName="Helvetica-Bold", fontSize=10,
        leading=13, textColor=TEXT, spaceBefore=6, spaceAfter=3,
    )
    body_style = ParagraphStyle(
        "PdfBody", parent=styles["Normal"], fontSize=7.5, leading=9.5, textColor=TEXT,
    )
    body_center = ParagraphStyle(
        "PdfBodyCenter", parent=body_style, alignment=TA_CENTER,
    )
    body_right = ParagraphStyle(
        "PdfBodyRight", parent=body_style, alignment=TA_RIGHT,
    )
    small_style = ParagraphStyle(
        "PdfSmall", parent=body_style, fontSize=7, leading=8.5, textColor=MUTED,
    )
    kpi_label_style = ParagraphStyle(
        "PdfKpiLabel", parent=body_style, fontSize=6.5, alignment=TA_CENTER, textColor=MUTED,
    )
    kpi_value_style = ParagraphStyle(
        "PdfKpiValue", parent=body_style, fontName="Helvetica-Bold", fontSize=13,
        alignment=TA_CENTER, textColor=BLUE,
    )

    story = []

    # 1. Cabeçalho
    header = Table(
        [[
            _text("DASHBOARD DE RESULTADOS | LINKEDIN", title_style),
            _text(
                f"Centro de Eventos Padre Vítor Coelho de Almeida<br/>"
                f"Período: {_date_label(data_inicio)} a {_date_label(data_fim)}",
                subtitle_style,
            ),
        ]],
        colWidths=[185 * mm, 92 * mm],
    )
    header.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), BLUE),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.extend([header, Spacer(1, 3 * mm)])

    # 2. KPIs (8 colunas perfeitamente distribuídas nos 277mm úteis da página paisagem)
    kpi_values = [
        ("Impressões", _number(kpis.get("impressoes", 0))),
        ("Impressões únicas", _number(kpis.get("impressoes_unicas", 0))),
        ("Cliques", _number(kpis.get("cliques", 0))),
        ("Reações", _number(kpis.get("reacoes", 0))),
        ("Publicações", _number(kpis.get("publicacoes", 0))),
        ("Engajamento", _percent(kpis.get("engajamento_medio", 0))),
        ("CTR médio", _percent(kpis.get("ctr_medio", 0))),
        ("Patrocinadas", _number(kpis.get("impressoes_patrocinadas", 0))),
    ]
    kpi_table = Table(
        [[_text(label, kpi_label_style) for label, _ in kpi_values],
         [_text(value, kpi_value_style) for _, value in kpi_values]],
        colWidths=[34.6 * mm] * 8,
    )
    kpi_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.white),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#D9E1EA")),
        ("INNERGRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#E6EAF0")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.extend([kpi_table, Spacer(1, 3 * mm)])

    # 3. Mix de Interações
    story.append(_text("Mix de Interações", section_style))
    mix_rows = [[_text("<b>Tipo</b>", body_style), _text("<b>Quantidade</b>", body_right), _text("<b>Percentual</b>", body_right)]]
    for _, row in df_mix.iterrows():
        mix_rows.append([
            _text(row.get("tipo", ""), body_style),
            _text(_number(row.get("quantidade", 0)), body_right),
            _text(f"{row.get('percentual', 0):.1f}%".replace(".", ","), body_right),
        ])
    mix_table = Table(mix_rows, colWidths=[97 * mm, 90 * mm, 90 * mm])
    mix_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), LIGHT_BLUE),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#D9E1EA")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.extend([mix_table, Spacer(1, 3 * mm)])

    # 4. Top Publicações
    story.append(_text("Top Publicações do Período", section_style))
    top_rows = [[
        _text("<b>Data</b>", body_style), 
        _text("<b>Resumo da Publicação</b>", body_style), 
        _text("<b>Impressões</b>", body_right),
        _text("<b>Cliques</b>", body_right), 
        _text("<b>Reações</b>", body_right), 
        _text("<b>Engajamento</b>", body_right),
    ]]
    for _, row in df_top.head(10).iterrows():
        data = row.get("data")
        data_label = data.strftime("%d/%m/%Y") if hasattr(data, "strftime") else data
        top_rows.append([
            _text(data_label, small_style),
            _text(str(row.get("resumo", ""))[:110], small_style),
            _text(_number(row.get("impressoes", 0)), body_right),
            _text(_number(row.get("cliques", 0)), body_right),
            _text(_number(row.get("reacoes", 0)), body_right),
            _text(_percent(row.get("engajamento_pct", 0)), body_right),
        ])
    top_table = Table(top_rows, colWidths=[22 * mm, 145 * mm, 30 * mm, 23 * mm, 23 * mm, 34 * mm], repeatRows=1)
    top_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), LIGHT_BLUE),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#D9E1EA")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.extend([top_table, Spacer(1, 3 * mm)])

    # 5. Comparativo Mensal (Corrigido os nomes das colunas e alinhamentos)
    story.append(_text("Comparativo Mensal", section_style))
    comp_rows = [[
        _text("<b>Indicador</b>", body_style), 
        _text("<b>Mês Anterior</b>", body_right), 
        _text("<b>Mês Atual</b>", body_right)
    ]]
    for _, row in comparativo.iterrows():
        comp_rows.append([
            _text(str(row.get("indicador", "")), small_style),
            _text(str(row.get("mes_anterior", "")), body_right),
            _text(str(row.get("mes_atual", "")), body_right),
        ])
    comp_table = Table(comp_rows, colWidths=[117 * mm, 80 * mm, 80 * mm], repeatRows=1)
    comp_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), LIGHT_BLUE),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#D9E1EA")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(comp_table)

    doc.build(story)
    return output.getvalue()