"""
Todas as métricas derivadas exibidas no dashboard são calculadas aqui,
a partir do dataframe "cru" de publicações (uma linha por post).

Fórmulas replicadas do wireframe:
- Engajamento (%) por post = (Reações + Comentários + Compartilhamentos + Cliques) / Impressões * 100
- CTR (%) por post = Cliques / Impressões * 100
- CTR geral do período = soma(Cliques) / soma(Impressões) * 100
- Engajamento médio = média do engajamento (%) das publicações
- CTR médio = média do CTR (%) das publicações
"""
import pandas as pd


def filtrar_periodo(df: pd.DataFrame, data_inicio, data_fim) -> pd.DataFrame:
    mask = (df["data"] >= pd.to_datetime(data_inicio)) & (df["data"] <= pd.to_datetime(data_fim))
    return df.loc[mask].sort_values("data").reset_index(drop=True)


def calcular_metricas_por_post(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    interacoes = df["reacoes"] + df["comentarios"] + df["compartilhamentos"] + df["cliques"]

    df["engajamento_pct"] = (interacoes / df["impressoes"].replace(0, pd.NA) * 100).fillna(0).round(2)
    df["ctr_pct"] = (df["cliques"] / df["impressoes"].replace(0, pd.NA) * 100).fillna(0).round(2)
    df["interacoes_totais"] = interacoes
    return df


def metricas_pagas(analytics: list[dict]) -> dict:
    """Soma as métricas retornadas pelo Analytics Finder pago."""
    return {
        "impressoes": sum(int(item.get("impressions", 0) or 0) for item in analytics),
        "cliques": sum(int(item.get("clicks", 0) or 0) for item in analytics),
        "custo": sum(float(item.get("costInLocalCurrency", 0) or 0) for item in analytics),
        "registros": len(analytics),
        "incluido_nos_totais": False,
    }


def kpis_periodo(df: pd.DataFrame, impressoes_unicas: int, pagos: dict | None = None) -> dict:
    """Retorna os valores dos 8 cards de KPI do topo."""
    pagos = pagos or {
        "impressoes": 0,
        "cliques": 0,
        "custo": 0,
        "registros": 0,
        "incluido_nos_totais": False,
    }
    total_impressoes = int(df["impressoes"].sum())
    total_cliques = int(df["cliques"].sum())
    total_reacoes = int(df["reacoes"].sum())
    total_publicacoes = int(df.attrs.get("publicacoes", len(df)))

    engajamento_medio = round(df["engajamento_pct"].mean(), 2) if len(df) else 0.0
    ctr_medio = round(df["ctr_pct"].mean(), 2) if len(df) else 0.0
    if pagos.get("incluido_nos_totais", False):
        total_impressoes_com_pagos = total_impressoes
        total_cliques_com_pagos = total_cliques
    else:
        total_impressoes_com_pagos = total_impressoes + pagos["impressoes"]
        total_cliques_com_pagos = total_cliques + pagos["cliques"]
    ctr_geral = (
        round((total_cliques_com_pagos / total_impressoes_com_pagos * 100), 2)
        if total_impressoes_com_pagos
        else 0.0
    )

    return {
        "impressoes": total_impressoes_com_pagos,
        "impressoes_unicas": impressoes_unicas,
        "cliques": total_cliques_com_pagos,
        "reacoes": total_reacoes,
        "publicacoes": total_publicacoes,
        "engajamento_medio": engajamento_medio,
        "ctr_medio": ctr_medio,
        "impressoes_patrocinadas": pagos["impressoes"],
        "ctr_geral": ctr_geral,
    }


def mix_de_interacoes(df: pd.DataFrame) -> pd.DataFrame:
    totais = {
        "Cliques": int(df["cliques"].sum()),
        "Reações": int(df["reacoes"].sum()),
        "Comentários": int(df["comentarios"].sum()),
        "Compartilhamentos": int(df["compartilhamentos"].sum()),
    }
    total_geral = sum(totais.values()) or 1
    linhas = [
        {"tipo": k, "quantidade": v, "percentual": round(v / total_geral * 100, 1)}
        for k, v in totais.items()
    ]
    return pd.DataFrame(linhas)


def top_publicacoes(df: pd.DataFrame) -> pd.DataFrame:
    """Ordena por data (mais recentes primeiro) — no wireframe as 4 publicações
    do mês aparecem todas; se houver mais de 4 no período, pega as de maior
    engajamento."""
    cols = ["data", "resumo", "impressoes", "cliques", "reacoes", "engajamento_pct"]
    ordenado = df.sort_values("engajamento_pct", ascending=False)
    return ordenado[cols].head(6).reset_index(drop=True)
