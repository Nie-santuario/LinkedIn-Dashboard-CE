import datetime as dt

import streamlit as st

from config import modo_mock_ativo, get_secret
from ui.styles import load_css
from ui.components import (
    render_kpis,
    render_grafico_impressoes,
    render_grafico_combo,
    render_donut_mix,
    render_top_publicacoes,
    render_comparativo,
)
from data import mock, transform, insights_store
from data import linkedin_export
from api import organic, paid

st.set_page_config(page_title="Dashboard LinkedIn", layout="wide", initial_sidebar_state="collapsed")
load_css()
dashboard_panel = st.container(border=True)

st.session_state.setdefault("periodo_inicio", dt.date(2026, 7, 1))
st.session_state.setdefault("periodo_fim", dt.date(2026, 7, 31))
st.session_state.setdefault("consultar_api", False)
st.session_state.setdefault("status_api", [])

with dashboard_panel:
    st.markdown("<div class='header-row'>", unsafe_allow_html=True)
    header_info, header_controls = st.columns(
        [1.7, 2.3], gap=None, vertical_alignment="center"
    )
    with header_info:
        st.markdown(
            f"<div class='app-header'><h1>{'DASHBOARD DE RESULTADOS | LINKEDIN'}</h1>"
            f"<p>Centro de Eventos Padre Vítor Coelho de Almeida</p></div>",
            unsafe_allow_html=True,
        )
    with header_controls:
        with st.form("periodo_form", border=False):
            col_inicio, col_fim, col_periodo, col_buscar = st.columns([1, 1, 1.5, 1])
            with col_inicio:
                data_inicio_selecionada = st.date_input(
                    "De",
                    value=st.session_state.periodo_inicio,
                    format="DD/MM/YYYY",
                    key="periodo_inicio_input",
                )
            with col_fim:
                data_fim_selecionada = st.date_input(
                    "Até",
                    value=st.session_state.periodo_fim,
                    format="DD/MM/YYYY",
                    key="periodo_fim_input",
                )
            with col_periodo:
                st.markdown(
                    "<div class='toolbar-period'>Período analisado:<br><strong>"
                    f"{st.session_state.periodo_inicio.strftime('%d/%m/%Y')} a "
                    f"{st.session_state.periodo_fim.strftime('%d/%m/%Y')}</strong></div>",
                    unsafe_allow_html=True,
                )
            with col_buscar:
                buscar_dados = st.form_submit_button(
                    "Buscar dados",
                    type="primary",
                    icon=":material/search:",
                    width="stretch",
                )
    st.markdown("</div>", unsafe_allow_html=True)

    if buscar_dados:
        if data_inicio_selecionada > data_fim_selecionada:
            st.error("A data inicial não pode ser depois da data final.")
        else:
            st.session_state.periodo_inicio = data_inicio_selecionada
            st.session_state.periodo_fim = data_fim_selecionada
            st.session_state.consultar_api = True
            st.rerun()

data_inicio = st.session_state.periodo_inicio
data_fim = st.session_state.periodo_fim

if data_inicio > data_fim:
    st.error("A data inicial não pode ser depois da data final.")
    st.stop()


# --------------------------------------------------------------------------
# 2. Carregamento dos dados (real via API ou mock)
# --------------------------------------------------------------------------
usar_mock = modo_mock_ativo()
status_api = []
pagos = {
    "impressoes": 0,
    "cliques": 0,
    "custo": 0,
    "registros": 0,
    "incluido_nos_totais": False,
}
fonte_dados = "demonstração"

if usar_mock and not st.session_state.consultar_api:
    aviso_mock = "🔧 Rodando em **modo demonstração** com dados fictícios — configure os secrets para conectar às APIs reais."
    df_posts_bruto = mock.posts_mock()
    impressoes_unicas = mock.impressoes_unicas_mock()
else:
    organization_urn = get_secret("LINKEDIN_ORGANIZATION_URN")
    ad_account_urn = get_secret("LINKEDIN_AD_ACCOUNT_URN")
    with st.status("Consultando as APIs do LinkedIn...", expanded=True) as consulta_status:
        try:
            posts_reais = organic.buscar_posts_organicos(
                organization_urn, data_inicio.isoformat(), data_fim.isoformat()
            )
            elementos = organic.buscar_estatisticas_organicas(
                organization_urn, data_inicio.isoformat(), data_fim.isoformat()
            )
            status_api.append(f"Orgânica: {len(posts_reais)} posts e {len(elementos)} registros de estatísticas.")
        except Exception as e:
            status_api.append(f"Orgânica: falhou ({type(e).__name__}: {e}).")
            elementos = []

        try:
            analytics_pagos = paid.buscar_analytics_pagos(
                ad_account_urn, data_inicio.isoformat(), data_fim.isoformat()
            )
            pagos = transform.metricas_pagas(analytics_pagos)
            status_api.append(
                f"Paga: {len(analytics_pagos)} registros | "
                f"{pagos['impressoes']} impressões patrocinadas | "
                f"{pagos['cliques']} cliques pagos."
            )
        except Exception as e:
            status_api.append(f"Paga: falhou ({type(e).__name__}: {e}).")
            analytics_pagos = []

        consulta_status.update(label="Consulta das APIs concluída", state="complete")
    st.session_state.status_api = status_api
    st.session_state.consultar_api = False

    try:
        df_posts_bruto, impressoes_unicas, pagos_export = linkedin_export.carregar_metricas(
            data_inicio, data_fim
        )
        # A exportação já traz o total orgânico + patrocinado. Ela é a fonte
        # única dos KPIs quando usada como fallback, evitando dupla contagem
        # das métricas pagas retornadas pela API.
        pagos = pagos_export
        fonte_dados = "exportação oficial do LinkedIn"
        status_api.append("Dados exibidos: exportação oficial do LinkedIn (fallback de produção).")
    except Exception as e:
        aviso_mock = f"Falha na API e na exportação oficial ({e}). Exibindo dados de demonstração."
        df_posts_bruto = mock.posts_mock()
        impressoes_unicas = mock.impressoes_unicas_mock()


# --------------------------------------------------------------------------
# 3. Transformação
# --------------------------------------------------------------------------
df_periodo = transform.filtrar_periodo(df_posts_bruto, data_inicio, data_fim)
df_periodo = transform.calcular_metricas_por_post(df_periodo)
kpis = transform.kpis_periodo(df_periodo, impressoes_unicas, pagos)
df_mix = transform.mix_de_interacoes(df_periodo)
df_top = transform.top_publicacoes(df_periodo)
try:
    comparativo = linkedin_export.carregar_comparativo(data_inicio, data_fim)
except Exception:
    comparativo = mock.comparativo_mensal_mock()


# --------------------------------------------------------------------------
# 4. Layout
# --------------------------------------------------------------------------
with dashboard_panel:
    st.caption(f"Fonte dos dados: {fonte_dados}")
    if status_api:
        for mensagem in status_api:
            st.info(mensagem, icon=":material/cloud_done:")
    elif st.session_state.status_api:
        for mensagem in st.session_state.status_api:
            st.info(mensagem, icon=":material/cloud_done:")
    elif usar_mock:
        st.info(aviso_mock, icon="ℹ️")
    render_kpis(kpis)

    st.markdown("<br>", unsafe_allow_html=True)
    g1, g2, g3 = st.columns([1, 1.3, 1])

    with g1:
        st.markdown("<div class='section-title'>📊 IMPRESSÕES POR PUBLICAÇÃO</div>", unsafe_allow_html=True)
        st.plotly_chart(render_grafico_impressoes(df_periodo), width="stretch", config={"displayModeBar": False})
        st.markdown(
            '<div class="chart-caption">A publicação com maior número de impressões se destacou no período.</div>',
            unsafe_allow_html=True,
        )

    with g2:
        st.markdown("<div class='section-title'>📈 IMPRESSÕES × ENGAJAMENTO POR PUBLICAÇÃO</div>", unsafe_allow_html=True)
        st.plotly_chart(render_grafico_combo(df_periodo), width="stretch", config={"displayModeBar": False})
        st.markdown(
            '<div class="chart-caption">Compare alcance (impressões) com a taxa de engajamento de cada publicação.</div>',
            unsafe_allow_html=True,
        )

    with g3:
        st.markdown("<div class='section-title'>🍩 MIX DE INTERAÇÕES</div>", unsafe_allow_html=True)
        st.plotly_chart(render_donut_mix(df_mix), width="stretch", config={"displayModeBar": False})
        for _, row in df_mix.iterrows():
            st.markdown(
                f"<span style='font-size:12px'>{row['tipo']}: <b>{int(row['quantidade'])}</b> ({row['percentual']}%)</span>",
                unsafe_allow_html=True,
            )

    st.markdown("<br>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([2, 1.5, 1.5])

    with c1:
        st.markdown("<div class='section-title'>🏆 TOP PUBLICAÇÕES DO MÊS</div>", unsafe_allow_html=True)
        render_top_publicacoes(df_top)

    with c2:
        st.markdown("<div class='section-title'>💡 INSIGHTS DO MÊS</div>", unsafe_allow_html=True)
        texto_salvo = insights_store.carregar_insights()
        texto_novo = st.text_area(
            "Escreva os principais destaques do período",
            value=texto_salvo,
            height=220,
            label_visibility="collapsed",
            key="insights_textarea",
        )
        if texto_novo != texto_salvo:
            if insights_store.salvar_insights(texto_novo):
                st.caption("✅ Salvo automaticamente.")
            else:
                st.caption("⚠️ Não foi possível salvar agora — tente novamente.")

    with c3:
        st.markdown("<div class='section-title'>📊 COMPARATIVO MENSAL</div>", unsafe_allow_html=True)
        render_comparativo(comparativo)

    st.markdown(
        f"<div class='info-banner'>ℹ️ Este relatório considera todas as interações das publicações "
        f"ocorridas no período de {data_inicio.strftime('%d/%m/%Y')} a {data_fim.strftime('%d/%m/%Y')}.</div>",
        unsafe_allow_html=True,
    )
