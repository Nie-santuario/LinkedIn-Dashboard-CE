import datetime
import pandas as pd
from pathlib import Path
import sys

# Adiciona o diretório raiz ao path para importar 'config' e 'api'
sys.path.append(str(Path(__file__).resolve().parent.parent))

from config import get_secret
from api.organic import buscar_estatisticas_organicas, buscar_posts_organicos
from api.paid import buscar_analytics_pagos

EXPORT_DIR = Path("export_excel")

def main():
    print("Iniciando sincronização com a API do LinkedIn...")
    
    token_org = get_secret("LINKEDIN_ORGANIC_ACCESS_TOKEN")
    token_pago = get_secret("LINKEDIN_PAID_ACCESS_TOKEN")
    org_urn = get_secret("LINKEDIN_ORGANIZATION_URN")
    ad_urn = get_secret("LINKEDIN_AD_ACCOUNT_URN")
    
    hoje = datetime.date.today()
    inicio = hoje - datetime.timedelta(days=364)
    print(f"Período: {inicio} a {hoje}")
    
    # --- 1. Buscar Diário Orgânico ---
    print("Buscando métricas orgânicas diárias...")
    elementos_org = buscar_estatisticas_organicas(org_urn)
    dados_org = []
    for e in elementos_org:
        stats = e.get("totalShareStatistics", {})
        ts = e.get("timeRange", {}).get("start")
        if ts:
            dt = datetime.datetime.fromtimestamp(ts / 1000.0).date()
            if inicio <= dt <= hoje:
                dados_org.append({
                    "Data": dt,
                    "Impressões Totais": stats.get("impressionCount", 0),
                    "Impressões Únicas": stats.get("uniqueImpressionsCount", 0),
                    "Cliques Totais": stats.get("clickCount", 0),
                    "Reações": stats.get("likeCount", 0),
                    "Comentários": stats.get("commentCount", 0),
                    "Compartilhamentos": stats.get("shareCount", 0)
                })
                
    df_org = pd.DataFrame(dados_org)
    if not df_org.empty:
        df_org = df_org.groupby("Data").sum()

    # --- 2. Buscar Diário Pago ---
    print("Buscando métricas pagas diárias...")
    elementos_pagos = buscar_analytics_pagos(ad_urn, inicio.isoformat(), hoje.isoformat())
    dados_pagos = []
    for e in elementos_pagos:
        stat = e
        dr = stat.get("dateRange", {}).get("start", {})
        if "year" in dr and "month" in dr and "day" in dr:
            dt = datetime.date(dr.get("year"), dr.get("month"), dr.get("day"))
            dados_pagos.append({
                "Data": dt,
                "Impressões Patrocinadas": stat.get("impressions", 0),
                "Cliques Patrocinados": stat.get("clicks", 0)
            })
            
    df_paid = pd.DataFrame(dados_pagos)
    if not df_paid.empty:
        df_paid = df_paid.groupby("Data").sum()
    
    # --- Combinar ---
    if not df_org.empty and not df_paid.empty:
        df_diario = df_org.join(df_paid, how="outer").fillna(0)
    elif not df_org.empty:
        df_diario = df_org.fillna(0)
    elif not df_paid.empty:
        df_diario = df_paid.fillna(0)
        for col in ["Impressões Totais", "Impressões Únicas", "Cliques Totais", "Reações", "Comentários", "Compartilhamentos"]:
            df_diario[col] = 0
    else:
        df_diario = pd.DataFrame(columns=["Data", "Impressões Patrocinadas", "Impressões Totais", "Impressões Únicas", "Cliques Patrocinados", "Cliques Totais", "Reações", "Comentários", "Compartilhamentos"])
        df_diario.set_index("Data", inplace=True)
        
    df_diario.reset_index(inplace=True)
    
    # Formatar colunas igual ao excel
    sheet0 = pd.DataFrame(index=df_diario.index, columns=range(20))
    sheet0.iloc[:, 0] = df_diario["Data"].apply(lambda x: x.strftime("%m/%d/%Y"))
    sheet0.iloc[:, 2] = df_diario["Impressões Patrocinadas"]
    sheet0.iloc[:, 3] = df_diario["Impressões Totais"] + df_diario["Impressões Patrocinadas"]
    sheet0.iloc[:, 4] = df_diario["Impressões Únicas"]
    sheet0.iloc[:, 6] = df_diario["Cliques Patrocinados"]
    sheet0.iloc[:, 7] = df_diario["Cliques Totais"] + df_diario["Cliques Patrocinados"]
    sheet0.iloc[:, 10] = df_diario["Reações"]
    sheet0.iloc[:, 13] = df_diario["Comentários"]
    sheet0.iloc[:, 16] = df_diario["Compartilhamentos"]
    
    header_rows = pd.DataFrame([[""]*20, ["Data", "", "Impressões Patrocinadas", "Impressões Totais", "Impressões Únicas", "", "Cliques em anúncios", "Cliques Totais", "", "", "Reações", "", "", "Comentários", "", "", "Compartilhamentos", "", "", ""]])
    sheet0_final = pd.concat([header_rows, sheet0]).reset_index(drop=True)

    # --- 3. Buscar Posts ---
    print("Buscando publicações recentes...")
    posts = buscar_posts_organicos(org_urn)
    post_rows = []
    for p in posts:
        texto = p.get("commentary", "Post sem texto")
        created_ms = p.get("createdAt", 0)
        dt_post = ""
        if created_ms:
            dt_post = datetime.datetime.fromtimestamp(created_ms / 1000.0).strftime("%m/%d/%Y %H:%M:%S")
            
        post_rows.append({
            "Texto": texto,
            "Link": p.get("id"),
            "Tipo": "Orgânico",
            "Data de criação": dt_post,
            "Impressões": 0,
            "Cliques": 0,
            "Reações": 0,
            "Comentários": 0,
            "Compartilhamentos": 0
        })
        
    df_posts = pd.DataFrame(post_rows)
    sheet1 = pd.DataFrame(index=df_posts.index, columns=range(20))
    if not df_posts.empty:
        sheet1.iloc[:, 0] = df_posts["Texto"]
        sheet1.iloc[:, 1] = df_posts["Link"]
        sheet1.iloc[:, 2] = df_posts["Tipo"]
        sheet1.iloc[:, 3] = df_posts["Impressões"]
        sheet1.iloc[:, 5] = df_posts["Data de criação"]
        sheet1.iloc[:, 6] = df_posts["Cliques"]
        sheet1.iloc[:, 9] = df_posts["Reações"]
        sheet1.iloc[:, 12] = df_posts["Comentários"]
        sheet1.iloc[:, 15] = df_posts["Compartilhamentos"]
    
    header_rows_p = pd.DataFrame([[""]*20, ["Título da publicação", "Link", "Tipo de campanha", "Impressões", "", "Data de criação", "Cliques", "", "", "Reações", "", "", "Comentários", "", "", "Compartilhamentos", "", "", "", ""]])
    sheet1_final = pd.concat([header_rows_p, sheet1]).reset_index(drop=True)

    # --- 4. Salvar .xls ---
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    nome_arquivo = f"export_automatico_content_diario.xls"
    caminho_final = EXPORT_DIR / nome_arquivo
    
    print(f"Salvando em {caminho_final} usando motor xlwt...")
    # Aqui a mágica acontece: engine="xlwt" gera o .xls binário do Excel 97
    with pd.ExcelWriter(caminho_final, engine="xlwt") as writer:
        sheet0_final.to_excel(writer, sheet_name="Métricas", index=False, header=False)
        sheet1_final.to_excel(writer, sheet_name="Atualizações", index=False, header=False)
        
    print("Sincronização concluída com sucesso!")

if __name__ == "__main__":
    main()
