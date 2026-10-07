from pathlib import Path
import pandas as pd

EXPORT_DIR = Path(__file__).resolve().parents[1] / "export_excel"

def _content_file() -> Path:
    files = sorted(EXPORT_DIR.glob("*_content_*.xls"))
    if not files:
        raise FileNotFoundError("Exportação *_content_*.xls não encontrada em export_excel")
    return files[-1]

def data_atualizacao_export() -> str:
    """Data máxima dos dados da planilha (frescor do fallback), dd/mm/aaaa."""
    try:
        metricas = pd.read_excel(_content_file(), sheet_name=0, header=1, usecols=[0])
        datas = pd.to_datetime(metricas.iloc[:, 0], dayfirst=False, errors="coerce").dropna()
        if datas.empty:
            return "desconhecida"
        return datas.max().strftime("%d/%m/%Y")
    except Exception:
        return "desconhecida"


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
    # Conta posts únicos (linhas Orgânico/Patrocinado/Total do mesmo post
    # não podem virar várias publicações).
    if len(tipos) > 0:
        dados.attrs["publicacoes"] = int(posts_periodo.iloc[:, 1].astype(str).nunique())
    else:
        dados.attrs["publicacoes"] = len(dados)

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
        col_link = next((cols_lower[c] for c in cols_lower if 'link' in c), posts.columns[1])
        col_data = next((cols_lower[c] for c in cols_lower if any(k in c for k in ['data', 'date', 'criação', 'published'])), posts.columns[5])
        col_imp = next((cols_lower[c] for c in cols_lower if any(k in c for k in ['impress', 'visualiz'])), posts.columns[3])
        col_cli = next((cols_lower[c] for c in cols_lower if any(k in c for k in ['clique', 'click'])), posts.columns[6])
        col_rea = next((cols_lower[c] for c in cols_lower if any(k in c for k in ['reaç', 'reaction', 'like', 'gostaram', 'curti'])), posts.columns[9])
        col_com = next((cols_lower[c] for c in cols_lower if any(k in c for k in ['coment', 'comment'])), posts.columns[12])
        col_comp = next((cols_lower[c] for c in cols_lower if any(k in c for k in ['compart', 'share'])), posts.columns[15])

        # A aba traz linhas separadas por tipo (Orgânico / Patrocinado / Total) para
        # posts promovidos; sem consolidar, o mesmo post entra no ranking 2x.
        col_tipo = next((cols_lower[c] for c in cols_lower if 'tipo de publicação' in c), None)
        if col_tipo is not None and col_link in posts.columns:
            tipo_norm = posts[col_tipo].astype(str).str.strip().str.lower()
            links_total = set(posts.loc[tipo_norm == 'total', col_link].astype(str))
            if links_total:
                posts = posts[tipo_norm.eq('total') | ~posts[col_link].astype(str).isin(links_total)].copy()
            posts = posts.drop_duplicates(subset=[col_link], keep='first').copy()

        posts["_data"] = pd.to_datetime(posts[col_data], dayfirst=False, errors="coerce")
        inicio = pd.to_datetime(data_inicio)
        fim = pd.to_datetime(data_fim)
        posts_periodo = posts.loc[posts["_data"].between(inicio, fim)].copy()

        if posts_periodo.empty:
            return pd.DataFrame()

        textos_brutos = posts_periodo[col_texto].astype(str).fillna("Publicação sem texto")
        textos_curtos = textos_brutos.str.replace(r'\s+', ' ', regex=True).str.slice(0, 75)
        textos_finais = textos_curtos.where(textos_brutos.str.len() <= 75, textos_curtos + '...')
        
        links = posts_periodo[col_link].astype(str).fillna("")

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
            "link": links,
            "impressoes": imp,
            "cliques": cli,
            "reacoes": rea,
            "comentarios": com,
            "compartilhamentos": comp,
            "engajamento_pct": engajamento
        }).dropna(subset=["data"])

        if df_posts.empty:
            return pd.DataFrame()

        # Top 5 do mês mais recente; se faltar, retrocede mês a mês até fechar 5
        # (não pula direto pros melhores da história — posts do mês passado têm
        # prioridade sobre os antigos).
        ordenado = df_posts.sort_values("data", ascending=False)
        restam = 5
        pedacos = []
        for _, grupo in ordenado.groupby(ordenado["data"].dt.to_period("M"), sort=False):
            if restam <= 0:
                break
            top_do_mes = grupo.sort_values(by="impressoes", ascending=False).head(restam)
            pedacos.append(top_do_mes)
            restam -= len(top_do_mes)

        return pd.concat(pedacos).sort_values(by="impressoes", ascending=False).reset_index(drop=True)
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