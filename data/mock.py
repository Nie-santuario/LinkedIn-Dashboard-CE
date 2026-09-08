"""
Dados fictícios hardcoded que refletem exatamente os valores do wireframe
(modelo_cliente.png) para validar o layout enquanto as chaves reais da
API não estão configuradas ou enquanto uma chamada real falha.
"""
import pandas as pd


def posts_mock() -> pd.DataFrame:
    """Uma linha por publicação, granularidade que o app agrega depois."""
    dados = [
        {
            "data": "2026-07-03",
            "resumo": "Um evento esportivo é feito de muito mais do que medalhas e resultados...",
            "impressoes": 58,
            "cliques": 14,
            "reacoes": 4,
            "comentarios": 0,
            "compartilhamentos": 0,
        },
        {
            "data": "2026-07-10",
            "resumo": "O reconhecimento de quem realiza grandes eventos é o reflexo de u...",
            "impressoes": 64,
            "cliques": 1,
            "reacoes": 2,
            "comentarios": 0,
            "compartilhamentos": 0,
        },
        {
            "data": "2026-07-17",
            "resumo": "Uma estrutura preparada faz toda a diferença na realização de um...",
            "impressoes": 123,
            "cliques": 0,
            "reacoes": 3,
            "comentarios": 0,
            "compartilhamentos": 0,
        },
        {
            "data": "2026-07-30",
            "resumo": "Grandes eventos esportivos exigem mais do que uma boa organizaçã...",
            "impressoes": 53,
            "cliques": 0,
            "reacoes": 6,
            "comentarios": 0,
            "compartilhamentos": 0,
        },
    ]
    df = pd.DataFrame(dados)
    df["data"] = pd.to_datetime(df["data"])
    return df


def impressoes_patrocinadas_mock() -> pd.DataFrame:
    """No período de referência, desempenho 100% orgânico -> zero patrocinado."""
    return pd.DataFrame(columns=["data", "impressoes_pagas", "cliques_pagos", "custo"])


def comparativo_mensal_mock() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"indicador": "Impressões", "mes_anterior": None, "mes_atual": 362},
            {"indicador": "Impressões únicas", "mes_anterior": None, "mes_atual": 180},
            {"indicador": "Cliques", "mes_anterior": None, "mes_atual": 15},
            {"indicador": "Reações", "mes_anterior": None, "mes_atual": 18},
            {"indicador": "Publicações", "mes_anterior": None, "mes_atual": 4},
            {"indicador": "Engajamento médio", "mes_anterior": None, "mes_atual": "12,37%"},
            {"indicador": "CTR médio (publicações)", "mes_anterior": None, "mes_atual": "6,43%"},
        ]
    )


def impressoes_unicas_mock() -> int:
    return 180
