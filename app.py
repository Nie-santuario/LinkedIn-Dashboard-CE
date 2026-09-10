import datetime as dt

import streamlit as st

from config import get_secret
from ui.styles import load_css
from ui.components import (
    render_kpis,
    render_grafico_impressoes,
    render_grafico_combo,
    render_donut_mix,
    render_top_publicacoes,
    render_comparativo,
)
from data import transform, insights_store
from data import linkedin_export
from data.pdf_report import gerar_pdf_dashboard
from api import organic, paid

st.set_page_config(page_title="Dashboard LinkedIn", layout="wide", initial_sidebar_state="collapsed")
load_css()

st.session_state.setdefault("periodo_inicio", dt.date(2026, 7, 1))
st.session_state.setdefault("periodo_fim", dt.date(2026, 7, 31))
st.session_state.setdefault("consultar_api", False)
st.session_state.setdefault("status_api", [])

with st.container(key="topbar"):
    with st.form("periodo_form", border=False):
        header_info, header_controls, header_action = st.columns(
            [2.2, 4.6, 1.2], gap="small", vertical_alignment="center"
        )
        with header_info:
            st.markdown(
                "<div class='topbar-brand'><h1>DASHBOARD DE RESULTADOS | LINKEDIN</h1>"
                "<p>Centro de Eventos Padre Vítor Coelho de Almeida</p></div>",
                unsafe_allow_html=True,
            )
        with header_controls:
            col_inicio, col_fim, col_periodo = st.columns([1, 1, 1.35], gap="small")
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
        with header_action:
            buscar_dados = st.form_submit_button(
                "Buscar dados",
                type="primary",
                icon=":material/search:",
                width="stretch",
            )

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
# 2. Carregamento dos dados
# --------------------------------------------------------------------------
status_api = []
pagos = {
    "impressoes": 0,
    "cliques": 0,
    "custo": 0,
    "registros": 0,
    "incluido_nos_totais": False,
}

with st.status("Carregando dados oficiais...", expanded=True) as consulta_status:
    organization_urn = get_secret("LINKEDIN_ORGANIZATION_URN")
    ad_account_urn = get_secret("LINKEDIN_AD_ACCOUNT_URN")
    
    try:
        posts_reais = organic.buscar_posts_organicos(organization_urn)
        elementos = organic.buscar_estatisticas_organicas(organization_urn)
        msg_org = f"Orgânica: {len(posts_reais)} posts e {len(elementos)} registros de estatísticas."
        status_api.append(msg_org)
        st.info(msg_org)
    except Exception as e:
        msg_erro_org = f"Orgânica: falhou ({type(e).__name__}: {e})."
        status_api.append(msg_erro_org)
        st.error(msg_erro_org)
        elementos = []

    try:
        analytics_pagos = paid.buscar_analytics_pagos(
            ad_account_urn, data_inicio.isoformat(), data_fim.isoformat()
        )
        pagos = transform.metricas_pagas(analytics_pagos)
        msg_paga = f"Paga: {len(analytics_pagos)} registros | {pagos['impressoes']} impressões patrocinadas | {pagos['cliques']} cliques pagos."
        status_api.append(msg_paga)
        st.info(msg_paga)
    except Exception as e:
        msg_erro_paga = f"Paga: falhou ({type(e).__name__}: {e})."
        status_api.append(msg_erro_paga)
        st.error(msg_erro_paga)
        analytics_pagos = []

    try:
        df_posts_bruto, impressoes_unicas, pagos_export = linkedin_export.carregar_metricas(
            data_inicio, data_fim
        )
        pagos = pagos_export
        msg_fonte = "Dados exibidos: exportação oficial do LinkedIn (produção)."
        status_api.append(msg_fonte)
        st.info(msg_fonte)
    except Exception as e:
        st.error(f"ERRO CRÍTICO NA PLANILHA DE EXPORTAÇÃO: {e}")
        raise e

    consulta_status.update(label="Consulta concluída", state="complete", expanded=False)

st.session_state.status_api = status_api
st.session_state.consultar_api = False


# --------------------------------------------------------------------------
# 3. Transformação
# --------------------------------------------------------------------------
df_periodo = transform.filtrar_periodo(df_posts_bruto, data_inicio, data_fim)
df_periodo = transform.calcular_metricas_por_post(df_periodo)
kpis = transform.kpis_periodo(df_periodo, impressoes_unicas, pagos)
df_mix = transform.mix_de_interacoes(df_periodo)

# Carrega os top posts diretamente da Aba 1 do Excel com mapeamento dinâmico
df_top = linkedin_export.carregar_top_publicacoes_excel(data_inicio, data_fim)
if df_top.empty:
    df_top = transform.top_publicacoes(df_periodo)

try:
    comparativo = linkedin_export.carregar_comparativo(data_inicio, data_fim)
except Exception as e:
    st.error(f"Erro ao carregar comparativo mensal da planilha: {e}")
    raise e

pdf_bytes = gerar_pdf_dashboard(
    data_inicio=data_inicio,
    data_fim=data_fim,
    kpis=kpis,
    df_top=df_top,
    df_mix=df_mix,
    comparativo=comparativo,
)


# --------------------------------------------------------------------------
# 4. Layout
# --------------------------------------------------------------------------
dashboard_panel = st.container(border=True)
with dashboard_panel:
    st.download_button(
        "Exportar PDF",
        data=pdf_bytes,
        file_name=f"dashboard_linkedin_{data_inicio:%Y%m%d}_{data_fim:%Y%m%d}.pdf",
        mime="application/pdf",
        type="primary",
        icon=":material/download:",
    )
    render_kpis(kpis)

    # BARRA DINÂMICA DE CTR CALCULADA DIRETAMENTE DOS KPIS TRATADOS
    tot_imp = int(kpis.get("impressoes", 0))
    tot_cli = int(kpis.get("cliques", 0))
    ctr_geral = (tot_cli / tot_imp * 100) if tot_imp > 0 else 0.0
    ctr_formatado = f"{ctr_geral:.2f}".replace(".", ",")

    st.markdown(
        f"<div class='info-banner' style='margin-top: 15px; margin-bottom: 25px; text-align: center; padding: 10px; background-color: #f8f9fa; border: 1px solid #ddd; border-radius: 5px; font-size: 14px;'>"
        f"ℹ️ <b>MÉTRICAS DO PERÍODO</b> (todas as interações das publicações no período analisado) &nbsp;|&nbsp; "
        f"<b>CTR GERAL DO PERÍODO: {ctr_formatado}%</b> &nbsp;({tot_cli} cliques &divide; {tot_imp} impressões)</div>",
        unsafe_allow_html=True,
    )

    g1, g2, g3 = st.columns([1, 1.3, 1])

    with g1:
        st.markdown("<div class='section-title'>📊 IMPRESSÕES POR PUBLICAÇÃO</div>", unsafe_allow_html=True)
        fig_imp = render_grafico_impressoes(df_periodo)
        fig_imp.update_layout(height=350)
        st.plotly_chart(fig_imp, width="stretch", config={"displayModeBar": False})
        st.markdown('<div class="chart-caption">A publicação com maior número de impressões se destacou no período.</div>', unsafe_allow_html=True)

    with g2:
        st.markdown("<div class='section-title'>📈 IMPRESSÕES × ENGAJAMENTO POR PUBLICAÇÃO</div>", unsafe_allow_html=True)
        fig_combo = render_grafico_combo(df_periodo)
        fig_combo.update_layout(height=350)
        st.plotly_chart(fig_combo, width="stretch", config={"displayModeBar": False})
        st.markdown('<div class="chart-caption">Compare alcance (impressões) com a taxa de engajamento de cada publicação.</div>', unsafe_allow_html=True)

    with g3:
        st.markdown("<div class='section-title'>🍩 MIX DE INTERAÇÕES</div>", unsafe_allow_html=True)
        fig_donut = render_donut_mix(df_mix)
        fig_donut.update_layout(height=350)
        st.plotly_chart(fig_donut, width="stretch", config={"displayModeBar": False})

    st.markdown("<br>", unsafe_allow_html=True)
    
    c1, c2, c3 = st.columns([2, 1.6, 1.4]) 

    with c1:
        st.markdown("<div class='section-title'>🏆 TOP 5 PUBLICAÇÕES DO MÊS</div>", unsafe_allow_html=True)
        render_top_publicacoes(df_top)

    with c2:
        st.markdown("<div class='section-title'>💡 INSIGHTS DO MÊS</div>", unsafe_allow_html=True)
        
        # ANÁLISE DINÂMICA OBRIGATÓRIA BASEADA NOS DADOS REAIS DO PERÍODO
        if not df_top.empty:
            df_ordenado_eng = df_top.sort_values(by="engajamento_pct", ascending=False)
            df_ordenado_imp = df_top.sort_values(by="impressoes", ascending=False)
            
            post_eng = df_ordenado_eng.iloc[0]["resumo"] if not df_ordenado_eng.empty else "N/A"
            taxa_eng = df_ordenado_eng.iloc[0]["engajamento_pct"] if not df_ordenado_eng.empty else 0.0
            
            post_imp = df_ordenado_imp.iloc[0]["resumo"] if not df_ordenado_imp.empty else "N/A"
            total_imp = df_ordenado_imp.iloc[0]["impressoes"] if not df_ordenado_imp.empty else 0
            
            texto_insights = (
                f"👥 1. Conteúdos de impacto geram maior interação\n"
                f"A publicação '{post_eng}' liderou o engajamento do período alcançando {taxa_eng:.2f}%.\n\n"
                f"🏟️ 2. Conteúdos de estrutura geram visibilidade\n"
                f"A publicação com maior alcance obteve {int(total_imp)} impressões totais ('{post_imp}').\n\n"
                f"🏆 3. Reconhecimento fortalece a autoridade\n"
                f"Conteúdos relacionados a premiações e reconhecimentos institucionais continuam apresentando boa resposta em reações.\n\n"
                f"🎯 4. Oportunidade para o próximo mês\n"
                f"Combinar estrutura + eventos realizados + resultados + impacto em histórias concretas de sucesso."
            )
        else:
            texto_insights = "Sem dados suficientes para gerar insights automáticos no período selecionado."

        # Exibição analítica direta (sem gravar estado fixo em arquivo)
        st.text_area(
            "Insights automáticos do período:",
            value=texto_insights,
            height=320,
            label_visibility="collapsed",
            key="insights_dinamicos_view",
        )

    with c3:
        st.markdown("<div class='section-title'>📊 COMPARATIVO MENSAL</div>", unsafe_allow_html=True)
        render_comparativo(comparativo)