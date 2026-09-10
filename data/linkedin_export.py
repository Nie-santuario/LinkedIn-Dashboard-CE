from pathlib import Path
import pandas as pd

EXPORT_DIR = Path(__file__).resolve().parents[1] / "export_excel"

def _content_file() -> Path:
    files = sorted(EXPORT_DIR.glob("*_content_*.xls"))
    if not files:
        raise FileNotFoundError("Exportação *_content_*.xls não encontrada em export_excel")
    return files[-1]

def carregar_metricas(data_inicio, data_fim) -> tuple[pd.DataFrame, int, dict]:
    """Carrega a aba diária (Aba 0) para alimentar os gráficos e KPIs globais."""
    arquivo = _content_file()
    metricas = pd.read_excel(arquivo, sheet_name=0, header=1)
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
            "resumo": "Métrica diária",
            "impressoes": pd.to_numeric(periodo.iloc[:, 3], errors="coerce").fillna(0),
            "cliques": pd.to_numeric(periodo.iloc[:, 7], errors="coerce").fillna(0),
            "reacoes": pd.to_numeric(periodo.iloc[:, 10], errors="coerce").fillna(0),
            "comentarios": pd.to_numeric(periodo.iloc[:, 13], errors="coerce").fillna(0),
            "compartilhamentos": pd.to_numeric(periodo.iloc[:, 16], errors="coerce").fillna(0),
        }
    ).dropna(subset=["data"])
    
    tipos = posts_periodo.iloc[:, 2].astype(str).str.lower() if not posts_periodo.empty else []
    dados.attrs["publicacoes"] = int((tipos != "total").sum()) if len(tipos) > 0 else len(dados)

    impressoes_unicas = total(4)
    pagos = {
        "impressoes": total(2),
        "cliques": total(6),
        "custo": 0.0,
        "registros": len(posts_periodo),
        "incluido_nos_totais": True,
    }
    return dados, impressoes_unicas, pagos

def carregar_top_publicacoes_excel(data_inicio, data_fim) -> pd.DataFrame:
    """Carrega os posts da Aba 1 mapeando as colunas dinamicamente e limitando aos 10 principais."""
    try:
        arquivo = _content_file()
        posts = pd.read_excel(arquivo, sheet_name=1, header=1)
        
        cols_lower = {str(c).strip().lower(): c for c in posts.columns}
        
        col_texto = next((cols_lower[c] for c in cols_lower if any(k in c for k in ['texto', 'publicação', 'content', 'post', 'title'])), posts.columns[0])
        col_data = next((cols_lower[c] for c in cols_lower if any(k in c for k in ['data', 'date', 'criação', 'published'])), posts.columns[5])
        col_imp = next((cols_lower[c] for c in cols_lower if any(k in c for k in ['impress', 'visualiz'])), posts.columns[3])
        col_cli = next((cols_lower[c] for c in cols_lower if any(k in c for k in ['clique', 'click'])), posts.columns[6])
        col_rea = next((cols_lower[c] for c in cols_lower if any(k in c for k in ['reaç', 'reaction', 'like'])), posts.columns[9])
        col_com = next((cols_lower[c] for c in cols_lower if any(k in c for k in ['coment', 'comment'])), posts.columns[12])
        col_comp = next((cols_lower[c] for c in cols_lower if any(k in c for k in ['compart', 'share'])), posts.columns[15])

        posts["_data"] = pd.to_datetime(posts[col_data], dayfirst=False, errors="coerce")
        inicio = pd.to_datetime(data_inicio)
        fim = pd.to_datetime(data_fim)
        posts_periodo = posts.loc[posts["_data"].between(inicio, fim)].copy()

        if posts_periodo.empty:
            return pd.DataFrame()

        textos_brutos = posts_periodo[col_texto].astype(str).fillna("Publicação sem texto")
        textos_curtos = textos_brutos.str.replace(r'\s+', ' ', regex=True).str.slice(0, 75)
        textos_finais = textos_curtos.where(textos_brutos.str.len() <= 75, textos_curtos + '...')

        imp = pd.to_numeric(posts_periodo[col_imp], errors="coerce").fillna(0)
        cli = pd.to_numeric(posts_periodo[col_cli], errors="coerce").fillna(0)
        rea = pd.to_numeric(posts_periodo[col_rea], errors="coerce").fillna(0)
        com = pd.to_numeric(posts_periodo[col_com], errors="coerce").fillna(0)
        comp = pd.to_numeric(posts_periodo[col_comp], errors="coerce").fillna(0)

        engajamento = ((cli + rea + com + comp) / imp.replace(0, 1) * 100)
        engajamento = engajamento.where(imp > 0, 0.0)

        df_posts = pd.DataFrame({
            "data": posts_periodo["_data"].dt.normalize(),
            "resumo": textos_finais,
            "impressoes": imp,
            "cliques": cli,
            "reacoes": rea,
            "comentarios": com,
            "compartilhamentos": comp,
            "engajamento_pct": engajamento
        }).dropna(subset=["data"])

        # Retorna ordenado por impressões, limitado estritamente aos 10 principais
        return df_posts.sort_values(by="impressoes", ascending=False).head(5)
    except Exception as e:
        print(f"Erro ao carregar top publicações: {e}")
        return pd.DataFrame()

def carregar_comparativo(data_inicio, data_fim) -> pd.DataFrame:
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