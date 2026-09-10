import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from config import NOME_CLIENTE, TITULO_APP, COR_AZUL, COR_VERDE, COR_ROXO, COR_LARANJA


def render_header(data_inicio, data_fim):
    st.markdown(
        f"""
        <div class="app-header">
            <div>
                <h1>{TITULO_APP}</h1>
                <p>{NOME_CLIENTE}</p>
            </div>
            <div style="color:white; text-align:right; font-size:13px;">
                Período analisado:<br>
                <b>{data_inicio.strftime('%d/%m/%Y')} a {data_fim.strftime('%d/%m/%Y')}</b>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _kpi_card(col, titulo, valor, sub):
    with col:
        st.markdown(
            f"""
            <div class="kpi-card">
                <div class="kpi-title">{titulo}</div>
                <div class="kpi-value">{valor}</div>
                <div class="kpi-sub">{sub}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_kpis(kpis: dict):
    cols = st.columns(8)
    _kpi_card(cols[0], "Impressões", kpis["impressoes"], "Total de impressões no período")
    _kpi_card(cols[1], "Impressões únicas", kpis["impressoes_unicas"], "Pessoas alcançadas (contas únicas)")
    _kpi_card(cols[2], "Cliques", kpis["cliques"], "Total de cliques nas publicações")
    _kpi_card(cols[3], "Reações", kpis["reacoes"], "Total de reações nas publicações")
    _kpi_card(cols[4], "Publicações", kpis["publicacoes"], "Publicações realizadas")
    _kpi_card(cols[5], "Engajamento médio", f"{kpis['engajamento_medio']:.2f}%".replace(".", ","), "Média do engajamento das publicações")
    _kpi_card(cols[6], "CTR médio (publicações)", f"{kpis['ctr_medio']:.2f}%".replace(".", ","), "Média do CTR das publicações")
    _kpi_card(cols[7], "Impressões patrocinadas", kpis["impressoes_patrocinadas"], "Todo o desempenho foi orgânico" if kpis["impressoes_patrocinadas"] == 0 else "Inclui campanhas pagas")


def render_grafico_impressoes(df):
    fig = go.Figure(go.Bar(
        x=df["data"].dt.strftime("%d/%m"),
        y=df["impressoes"],
        marker_color=COR_AZUL,
    ))

    fig.update_layout(
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        margin=dict(t=20, b=20, l=20, r=20),
        xaxis=dict(showgrid=False),
        yaxis=dict(showgrid=True, gridcolor="rgba(200,200,200,0.2)"),
    )

    return fig


def render_grafico_combo(df):
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(
        go.Bar(x=df["data"].dt.strftime("%d/%m"), y=df["impressoes"], name="Impressões", marker_color=COR_AZUL),
        secondary_y=False,
    )
    fig.add_trace(
        go.Scatter(
            x=df["data"].dt.strftime("%d/%m"),
            y=df["engajamento_pct"],
            name="Taxa de Engajamento (%)",
            mode="lines+markers",
            line=dict(color=COR_VERDE, width=2),
        ),
        secondary_y=True,
    )
    fig.update_layout(
        template="plotly_white",
        xaxis=dict(showgrid=False, title="Data da publicação", nticks=12, tickangle=0),
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        margin=dict(t=30, b=10, l=10, r=10),
        height=280,
    )
    fig.update_yaxes(title_text="Impressões", showgrid=True, secondary_y=False)
    fig.update_yaxes(title_text="Engajamento (%)", showgrid=False, secondary_y=True)
    return fig


def render_donut_mix(df_mix):
    cores = {"Cliques": COR_AZUL, "Reações": COR_VERDE, "Comentários": COR_LARANJA, "Compartilhamentos": COR_ROXO}
    total = int(df_mix["quantidade"].sum())
    fig = go.Figure(go.Pie(
        labels=df_mix["tipo"],
        values=df_mix["quantidade"],
        hole=0.6,
        marker_colors=[cores[t] for t in df_mix["tipo"]],
        textinfo="none",
    ))
    fig.update_layout(
        template="plotly_white",
        showlegend=True,
        legend=dict(orientation="v", yanchor="top", y=0.5, xanchor="left", x=1.0),
        margin=dict(t=10, b=10, l=10, r=10),
        height=260,
        annotations=[dict(text=f"<b>{total}</b><br>Interações totais", x=0.5, y=0.5, font_size=14, showarrow=False)],
    )
    return fig


def render_top_publicacoes(df_top):
    header = st.columns([1.2, 3, 1, 1, 1, 1.2])
    for c, t in zip(header, ["Data", "Resumo", "Impress.", "Cliques", "Reações", "Engajamento"]):
        c.markdown(f"<span style='font-size:12px;color:#666;font-weight:700'>{t}</span>", unsafe_allow_html=True)

    for _, row in df_top.iterrows():
        cols = st.columns([1.2, 3, 1, 1, 1, 1.2])
        cols[0].markdown(f"<span style='font-size:12px'>{row['data'].strftime('%d/%m/%Y')}</span>", unsafe_allow_html=True)
        cols[1].markdown(f"<span style='font-size:12px'>{row['resumo']}</span>", unsafe_allow_html=True)
        cols[2].markdown(f"<b>{int(row['impressoes'])}</b>", unsafe_allow_html=True)
        cols[3].markdown(f"{int(row['cliques'])}", unsafe_allow_html=True)
        cols[4].markdown(f"{int(row['reacoes'])}", unsafe_allow_html=True)
        cols[5].markdown(f"<span style='color:{COR_VERDE};font-weight:700'>{row['engajamento_pct']:.2f}%</span>".replace(".", ","), unsafe_allow_html=True)

    st.caption("* Engajamento (%) = (Reações + Comentários + Compartilhamentos + Cliques) ÷ Impressões × 100")


def render_comparativo(df_comp):
    st.dataframe(df_comp.astype(str), hide_index=True, width="stretch")