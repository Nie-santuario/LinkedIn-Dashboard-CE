"""Fonte primária de dados do dashboard: LinkedIn API (orgânico + pago).

Espelha a interface de ``data.linkedin_export`` — as mesmas 3 funções — para
que o app troque de fonte sem mudar o consumo. Validação A/B contra o export
oficial: 100% nas métricas diárias (365 dias), no pago e por publicação.

Ressalvas da API (diferente do export):
- Métricas por publicação são LIFETIME (a API não recorta por período);
- A Posts API devolve os 50 posts mais recentes;
- A janela orgânica é rolling de 12 meses.
"""
import datetime as dt

import pandas as pd

from api import organic, paid
from config import get_secret


def _date(valor) -> dt.date:
    """Normaliza para ``date`` (chave estável do cache do Streamlit)."""
    if isinstance(valor, dt.datetime):
        return valor.date()
    if isinstance(valor, dt.date):
        return valor
    return pd.Timestamp(valor).date()


def _posts_periodo(data_inicio, data_fim) -> list[tuple[str, pd.Timestamp, str]]:
    """[(post_urn, data_criacao, texto)] das publicações PUBLISHED no período."""
    urn = get_secret("LINKEDIN_ORGANIZATION_URN")
    posts = organic.buscar_posts_organicos(urn)
    ini = pd.Timestamp(data_inicio)
    fim = pd.Timestamp(data_fim)
    saida = []
    for p in posts:
        if p.get("lifecycleState") != "PUBLISHED":
            continue
        pid = str(p.get("id", ""))
        post_urn = pid if pid.startswith("urn:") else f"urn:li:share:{pid}"
        # O export usa a data de PUBLICAÇÃO (não a de criação — rascunhos
        # criados antes distorcem o mês); publishedAt em UTC bate 41/42.
        criado = pd.Timestamp(
            p.get("publishedAt") or p.get("createdAt", 0), unit="ms", tz="UTC"
        ).tz_localize(None).normalize()
        if not ini <= criado <= fim:
            continue
        saida.append((post_urn, criado, str(p.get("commentary", "") or "")))
    return saida


def _serie_organica(data_inicio, data_fim) -> dict[pd.Timestamp, dict]:
    """{dia: totalShareStatistics} orgânico por dia."""
    urn = get_secret("LINKEDIN_ORGANIZATION_URN")
    serie: dict[pd.Timestamp, dict] = {}
    for el in organic.estatisticas_diarias(urn, _date(data_inicio), _date(data_fim)):
        tr = el.get("timeRange")
        if not tr:
            continue
        dia = pd.Timestamp(tr["start"], unit="ms", tz="UTC").tz_localize(None).normalize()
        serie[dia] = el.get("totalShareStatistics", {})
    return serie


def _serie_paga(data_inicio, data_fim) -> dict[pd.Timestamp, dict]:
    """{dia: element} do adAnalytics (impressions/clicks/reactions/...)."""
    conta = get_secret("LINKEDIN_AD_ACCOUNT_URN")
    serie: dict[pd.Timestamp, dict] = {}
    for el in paid.buscar_analytics_diarios(conta, _date(data_inicio), _date(data_fim)):
        dr = el.get("dateRange", {}).get("start")
        if not dr:
            continue
        serie[pd.Timestamp(year=dr["year"], month=dr["month"], day=dr["day"])] = el
    return serie


def carregar_metricas(data_inicio, data_fim) -> tuple[pd.DataFrame, int, dict]:
    """Série diária de TOTAIS (orgânico + pago), impressões únicas e KPIs pagos.

    Mesma interface/semântica de ``linkedin_export.carregar_metricas``:
    ``incluido_nos_totais=True`` porque o df diário já soma orgânico + pago.
    """
    org = _serie_organica(data_inicio, data_fim)
    pag = _serie_paga(data_inicio, data_fim)
    posts = _posts_periodo(data_inicio, data_fim)

    linhas = []
    for dia in pd.date_range(pd.Timestamp(data_inicio).normalize(), pd.Timestamp(data_fim).normalize()):
        o = org.get(dia, {})
        p = pag.get(dia, {})
        linhas.append(
            {
                "data": dia,
                "resumo": "Métrica diária",
                "impressoes": (o.get("impressionCount", 0) or 0) + (p.get("impressions", 0) or 0),
                "cliques": (o.get("clickCount", 0) or 0) + (p.get("clicks", 0) or 0),
                "reacoes": (o.get("likeCount", 0) or 0) + (p.get("reactions", 0) or 0),
                "comentarios": (o.get("commentCount", 0) or 0) + (p.get("comments", 0) or 0),
                "compartilhamentos": (o.get("shareCount", 0) or 0) + (p.get("shares", 0) or 0),
            }
        )
    dados = pd.DataFrame(linhas)
    dados.attrs["publicacoes"] = len(posts)

    impressoes_unicas = sum((v.get("uniqueImpressionsCount", 0) or 0) for v in org.values())
    pagos = {
        "impressoes": sum((v.get("impressions", 0) or 0) for v in pag.values()),
        "cliques": sum((v.get("clicks", 0) or 0) for v in pag.values()),
        "custo": sum(float(v.get("costInLocalCurrency", 0) or 0) for v in pag.values()),
        "registros": len(posts),
        "incluido_nos_totais": True,
    }
    return dados, impressoes_unicas, pagos


def carregar_top_publicacoes(data_inicio, data_fim) -> pd.DataFrame:
    """Top 5 do mês mais recente (completado com os melhores de meses anteriores).

    Métricas por publicação são LIFETIME da API — para posts do mês corrente
    equivale ao período do export; um post antigo pode aparecer maior.
    """
    posts = _posts_periodo(data_inicio, data_fim)
    if not posts:
        return pd.DataFrame()

    urn = get_secret("LINKEDIN_ORGANIZATION_URN")
    stats = organic.estatisticas_por_posts(urn, tuple(p[0] for p in posts))

    # Parte patrocinada por post (a aba do export traz "Total" = orgânico + pago)
    conta = get_secret("LINKEDIN_AD_ACCOUNT_URN")
    pago_por_share: dict[str, dict] = {}
    for creative_urn, tot in paid.analytics_por_criativo(conta, _date(data_inicio), _date(data_fim)).items():
        share = paid.share_do_creative(conta, creative_urn)
        if not share:
            continue
        acumulado = pago_por_share.setdefault(
            share,
            {"impressoes": 0, "cliques": 0, "reacoes": 0, "comentarios": 0, "compartilhamentos": 0},
        )
        for chave in acumulado:
            acumulado[chave] += tot.get(chave, 0)

    textos_brutos = pd.Series([p[2] for p in posts], dtype=str)
    textos_curtos = textos_brutos.str.replace(r"\s+", " ", regex=True).str.slice(0, 75)
    textos_finais = textos_curtos.where(textos_brutos.str.len() <= 75, textos_curtos + "...")

    df_posts = pd.DataFrame(
        {
            "data": [p[1] for p in posts],
            "resumo": textos_finais,
            "link": [f"https://www.linkedin.com/feed/update/{p[0]}" for p in posts],
        }
    )
    imp, cli, rea, com, comp = [], [], [], [], []
    for p in posts:
        st_ = stats.get(p[0], {})
        pg_ = pago_por_share.get(p[0], {})
        imp.append(int(st_.get("impressionCount", 0) or 0) + int(pg_.get("impressoes", 0) or 0))
        cli.append(int(st_.get("clickCount", 0) or 0) + int(pg_.get("cliques", 0) or 0))
        rea.append(int(st_.get("likeCount", 0) or 0) + int(pg_.get("reacoes", 0) or 0))
        com.append(int(st_.get("commentCount", 0) or 0) + int(pg_.get("comentarios", 0) or 0))
        comp.append(int(st_.get("shareCount", 0) or 0) + int(pg_.get("compartilhamentos", 0) or 0))
    df_posts["impressoes"] = imp
    df_posts["cliques"] = cli
    df_posts["reacoes"] = rea
    df_posts["comentarios"] = com
    df_posts["compartilhamentos"] = comp
    df_posts["engajamento_pct"] = (
        (df_posts["cliques"] + df_posts["reacoes"] + df_posts["comentarios"] + df_posts["compartilhamentos"])
        / df_posts["impressoes"].replace(0, 1)
        * 100
    ).where(df_posts["impressoes"] > 0, 0.0)

    # Top 5 do mês mais recente; se faltar, retrocede mês a mês até fechar 5
    # (não pula direto pros melhores da história — posts do mês passado têm
    # prioridade sobre os antigos).
    ordenado = df_posts.sort_values("data", ascending=False)
    restam = 5
    pedacos = []
    for _, grupo in ordenado.groupby(ordenado["data"].dt.to_period("M"), sort=False):
        if restam <= 0:
            break
        top_do_mes = grupo.sort_values("impressoes", ascending=False).head(restam)
        pedacos.append(top_do_mes)
        restam -= len(top_do_mes)

    top5 = pd.concat(pedacos).sort_values("impressoes", ascending=False).reset_index(drop=True)
    return top5


def carregar_comparativo(data_inicio, data_fim) -> pd.DataFrame:
    """Mês atual vs mês anterior — mesmas 6 linhas do export."""
    inicio = pd.Timestamp(data_inicio)
    fim = pd.Timestamp(data_fim)
    anterior_inicio = inicio - pd.DateOffset(months=1)
    anterior_fim = fim - pd.DateOffset(months=1)

    org = _serie_organica(anterior_inicio, fim)
    pag = _serie_paga(anterior_inicio, fim)

    def totais(ini_p, fim_p) -> list[float]:
        imp = uni = cli = rea = com = comp = 0
        for dia in pd.date_range(pd.Timestamp(ini_p).normalize(), pd.Timestamp(fim_p).normalize()):
            o = org.get(dia, {})
            p = pag.get(dia, {})
            imp += (o.get("impressionCount", 0) or 0) + (p.get("impressions", 0) or 0)
            uni += o.get("uniqueImpressionsCount", 0) or 0
            cli += (o.get("clickCount", 0) or 0) + (p.get("clicks", 0) or 0)
            rea += (o.get("likeCount", 0) or 0) + (p.get("reactions", 0) or 0)
            com += (o.get("commentCount", 0) or 0) + (p.get("comments", 0) or 0)
            comp += (o.get("shareCount", 0) or 0) + (p.get("shares", 0) or 0)
        engajamento = (cli + rea + com + comp) / imp * 100 if imp else 0.0
        ctr = cli / imp * 100 if imp else 0.0
        return [imp, uni, cli, rea, engajamento, ctr]

    anterior = totais(anterior_inicio, anterior_fim)
    atual = totais(inicio, fim)
    return pd.DataFrame(
        [
            {"indicador": "Impressões", "mes_anterior": anterior[0], "mes_atual": atual[0]},
            {"indicador": "Impressões únicas", "mes_anterior": anterior[1], "mes_atual": atual[1]},
            {"indicador": "Cliques", "mes_anterior": anterior[2], "mes_atual": atual[2]},
            {"indicador": "Reações", "mes_anterior": anterior[3], "mes_atual": atual[3]},
            {"indicador": "Engajamento", "mes_anterior": f"{anterior[4]:.2f}%", "mes_atual": f"{atual[4]:.2f}%"},
            {"indicador": "CTR", "mes_anterior": f"{anterior[5]:.2f}%", "mes_atual": f"{atual[5]:.2f}%"},
        ]
    )
