from pathlib import Path

import pandas as pd


EXPORT_DIR = Path(__file__).resolve().parents[1] / "export_excel"


def _content_file() -> Path:
    files = sorted(EXPORT_DIR.glob("*_content_*.xls"))
    if not files:
        raise FileNotFoundError("Exportação *_content_*.xls não encontrada em export_excel")
    return files[-1]


def carregar_metricas(data_inicio, data_fim) -> tuple[pd.DataFrame, int, dict]:
    """Carrega a exportação oficial do LinkedIn como fallback de produção.

    A aba Métricas é diária e é a fonte dos KPIs agregados. A aba Todas as
    publicações é usada para manter o detalhamento real das publicações.
    """
    arquivo = _content_file()
    metricas = pd.read_excel(arquivo, sheet_name=0, header=1)
    # O XLS exportado pelo LinkedIn grava as datas como MM/DD/YYYY.
    metricas["_data"] = pd.to_datetime(metricas.iloc[:, 0], dayfirst=False, errors="coerce")
    inicio = pd.to_datetime(data_inicio)
    fim = pd.to_datetime(data_fim)
    periodo = metricas.loc[metricas["_data"].between(inicio, fim)].copy()

    posts = pd.read_excel(arquivo, sheet_name=1, header=1)
    posts["_data"] = pd.to_datetime(posts.iloc[:, 5], dayfirst=False, errors="coerce")
    posts_periodo = posts.loc[posts["_data"].between(inicio, fim)].copy()

    def total(column_index: int) -> int:
        return int(pd.to_numeric(periodo.iloc[:, column_index], errors="coerce").fillna(0).sum())

    dados = pd.DataFrame(
        {
            "data": periodo["_data"].dt.normalize(),
            "resumo": "LinkedIn exportação oficial",
            "impressoes": pd.to_numeric(periodo.iloc[:, 3], errors="coerce").fillna(0),
            "cliques": pd.to_numeric(periodo.iloc[:, 7], errors="coerce").fillna(0),
            "reacoes": pd.to_numeric(periodo.iloc[:, 10], errors="coerce").fillna(0),
            "comentarios": pd.to_numeric(periodo.iloc[:, 13], errors="coerce").fillna(0),
            "compartilhamentos": pd.to_numeric(periodo.iloc[:, 16], errors="coerce").fillna(0),
        }
    ).dropna(subset=["data"])
    tipos = posts_periodo.iloc[:, 2].astype(str).str.lower()
    dados.attrs["publicacoes"] = int((tipos != "total").sum())

    impressoes_unicas = total(4)
    pagos = {
        "impressoes": total(2),
        "cliques": total(6),
        "custo": 0.0,
        "registros": len(posts_periodo),
        "incluido_nos_totais": True,
    }
    return dados, impressoes_unicas, pagos


def carregar_comparativo(data_inicio, data_fim) -> pd.DataFrame:
    """Compara o período selecionado com o mesmo intervalo do mês anterior."""
    arquivo = _content_file()
    metricas = pd.read_excel(arquivo, sheet_name=0, header=1)
    datas = pd.to_datetime(metricas.iloc[:, 0], dayfirst=False, errors="coerce")
    inicio = pd.Timestamp(data_inicio)
    fim = pd.Timestamp(data_fim)
    anterior_inicio = inicio - pd.DateOffset(months=1)
    anterior_fim = fim - pd.DateOffset(months=1)

    def totais(inicio_periodo, fim_periodo):
        linhas = metricas.loc[datas.between(inicio_periodo, fim_periodo)]
        valores = [
            pd.to_numeric(linhas.iloc[:, index], errors="coerce").fillna(0).sum()
            for index in (3, 4, 7, 10, 13, 16)
        ]
        impressoes, unicas, cliques, reacoes, comentarios, compartilhamentos = valores
        engajamento = (
            (cliques + reacoes + comentarios + compartilhamentos) / impressoes * 100
            if impressoes
            else 0
        )
        ctr = cliques / impressoes * 100 if impressoes else 0
        return [impressoes, unicas, cliques, reacoes, engajamento, ctr]

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