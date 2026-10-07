# Dashboard LinkedIn — Centro de Eventos Padre Vítor Coelho de Almeida

Aplicação [Streamlit](https://streamlit.io/) que mostra os resultados orgânicos e pagos da página do LinkedIn numa única tela: KPIs, gráficos diários, comparativo mensal, Top 5 de publicações, insights e exportação em PDF.

Este README é o manual de manutenção: quem nunca viu o código consegue rodar, entender e alterar o app seguindo os passos abaixo.

---

## 1. Como funciona por dentro (resumo em 30 segundos)

```
  Usuário abre o app
        │
        ▼
  Login 
        │
        ▼
  ┌─────────────────────────────────────────────┐
  │ 1ª tentativa: API DO LINKEDIN (ao vivo)     │  ← fonte principal
  │   · orgânico: posts + estatísticas diárias  │
  │   · pago: adAnalytics por criativo          │
  │   · tudo em cache por 12 horas              │
  └─────────────────────────────────────────────┘
        │ deu certo                │ falhou (401/429/rede/…)
        ▼                          ▼
   Mostra "Fonte: API"      ┌──────────────────────────────┐
                            │ Fallback: planilha da pasta  │
                            │ export_excel/ (download      │
                            │ manual do LinkedIn)          │
                            │ + aviso com a data dos dados │
                            └──────────────────────────────┘
        │
        ▼
  KPIs · gráficos · Top 5 · comparativo · insights · PDF
```

Pontos importantes:

- **O app nunca trava por erro da API.** Se a API falhar, ele mostra os dados da planilha com um aviso na caixa "Consulta concluída" e segue funcionando.
- **Cache de 12 horas** (`@st.cache_data`): o primeiro carregamento faz ~6 chamadas à API; depois disso, zero até expirar. O limite de desenvolvimento do LinkedIn é 500 chamadas/dia — não há risco no uso normal.
- **Tokens do LinkedIn valem 60 dias.** O app renova sozinho via refresh token. Se a renovação for recusada, aparece um aviso amarelo; quando a API recusar de vez (HTTP 401), o fallback assume e a mensagem explica o que fazer (ver seção 7).

---

## 2. Como rodar o app (máquina local)

### Pré-requisito

**Python 3.10 ou superior:** [baixar aqui](https://www.python.org/downloads/)
> ⚠️ Na primeira tela do instalador, marque **"Add Python to PATH"** antes de instalar.

### Passo 1 — Baixar o código

**Opção A — Git (recomendado):**
```bash
git clone https://github.com/Nie-santuario/LinkedIn-Dashboard-CE.git
cd LinkedIn-Dashboard-CE
```

**Opção B — ZIP (sem Git):** abra a página do repositório no GitHub → botão verde **Code** → **Download ZIP** → extraia e abra o terminal na pasta.

### Passo 2 — Ambiente virtual (isola as bibliotecas do seu computador)

```bash
python -m venv venv
```
Ative:
- Windows: `venv\Scripts\activate`
- Linux/Mac: `source venv/bin/activate`

> Deu certo quando aparece `(venv)` no início da linha do terminal.

### Passo 3 — Instalar as bibliotecas

```bash
pip install -r requirements.txt
```

### Passo 4 — Configurar os segredos (`secrets.toml`)

O arquivo `.streamlit/secrets.toml` **não é versionado** (está no `.gitignore`). Crie-o a partir do exemplo:

1. Copie `.streamlit/secrets.toml.example` para `.streamlit/secrets.toml`.
2. Preencha com os valores reais (peça ao administrador da conta — ver seção 5).
3. Para ativar o login, adicione **no final**:

```toml
[login]
rafael = "senha123"
michelle = "senha456"
```

> Sem a seção `[login]`, o app abre sem senha. Erro de formatação no TOML faz o Streamlit falhar ao iniciar — `[login]` fica numa linha sozinho, cada usuário em uma linha abaixo.

### Passo 5 — Executar

```bash
streamlit run app.py
```

O navegador abre em `http://localhost:8501`. Para parar: `Ctrl + C` no terminal.

---

## 3. Estrutura do projeto

| Arquivo / pasta | O que faz |
|---|---|
| **`app.py`** | **Entrada do app.** Tela principal, seleção de período, chamada de dados (API com fallback), montagem das seções. |
| **`config.py`** | Constantes (URLs do LinkedIn, cores) e leitura segura de secrets. |
| **`api/auth.py`** | Renovação automática dos tokens OAuth (refresh quando vencem). |
| **`api/organic.py`** | Chamadas da API orgânica: lista de posts e estatísticas (diárias e por post). |
| **`api/paid.py`** | Chamadas da API de anúncios: analytics diário, por criativo e resolução do post pago. |
| **`data/api_source.py`** | **Fonte primária.** Monta os DataFrames (KPIs, Top 5, comparativo) a partir da API — mesma interface do export. |
| **`data/linkedin_export.py`** | **Fallback.** Lê a planilha `export_excel/*_content_*.xls` e monta os mesmos DataFrames. |
| **`data/transform.py`** | Cálculos: KPIs do período, métricas por post, mix de interações, comparativo. |
| **`data/pdf_report.py`** | Geração do relatório PDF (reportlab). |
| **`data/insights_store.py`** | Salva/carrega os insights de marketing (arquivo local `insights_marketing.json`). |
| **`ui/login.py`** | Tela de usuário/senha (ligada só se os secrets têm `[login]`). |
| **`ui/components.py`** | Blocos da interface: cartões de KPI, gráficos Plotly, tabelas. |
| **`ui/styles.py`** | CSS da identidade visual (inspecionado via `st.markdown`). |
| **`export_excel/`** | Planilhas baixadas do LinkedIn (fallback). Arquivo `*_content_*.xls` é o usado. |
| **`.streamlit/secrets.toml`** | Segredos locais (gitignoreado). Em produção: painel do Streamlit Cloud. |
| **`_teste_fonte_api.py`** | Teste local: compara API vs planilha (não versionado). |
| **`_teste_fallback.py`** | Teste local: simula falha da API (401/429/rede) e valida o fallback (não versionado). |

---

## 4. Guia rápido de manutenção — "Quero mudar X, onde mexo?"

| Quero mudar… | Mexer em |
|---|---|
| Um KPI novo (cálculo) | `data/transform.py` → `kpis_periodo()` |
| Um KPI novo (aparecer na tela) | `ui/components.py` → `render_kpis()` (adicionar `_kpi_card`) |
| Título, texto, botão, layout do topo | `app.py` |
| Gráfico (tipo, cor, legenda, eixo) | `ui/components.py` → `render_grafico_*` / `render_donut_mix` |
| Cores, fontes, bordas, "premium" | `ui/styles.py` (CSS) + cores em `config.py` |
| Top 5 de publicações (regra) | `data/api_source.py` **e** `data/linkedin_export.py` → `carregar_top_publicacoes*` (manter os dois iguais) |
| Comparativo mensal | `data/api_source.py` e `data/linkedin_export.py` → `carregar_comparativo` |
| Layout/estilo do PDF | `data/pdf_report.py` → `gerar_pdf_dashboard()` |
| Mensagem de erro traduzida | `app.py` → `_descricao_erro_api()` |
| Período máximo (hoje: 1 ano) | `app.py` (linhas de `_DATA_MINIMA` e a validação de 365 dias) |
| Tempo de cache (hoje: 12h) | `config.py` → `CACHE_TTL_SECONDS` |
| Tela de login | `ui/login.py` + seção `[login]` nos secrets |

> **Regra de ouro:** `data/api_source.py` (API) e `data/linkedin_export.py` (planilha) implementam a **mesma interface com as mesmas regras**. Se alterar a lógica de um, altere do outro — caso contrário o número muda dependendo da fonte usada.

---

## 5. Configuração dos segredos (`secrets.toml`)

O mesmo conteúdo serve para o **local** (arquivo) e para o **Streamlit Cloud** (painel → Settings → Secrets).

```toml
# --- Onde buscar os dados ---
LINKEDIN_ORGANIZATION_URN = "urn:li:organization:XXXXXXX"
LINKEDIN_AD_ACCOUNT_URN = "urn:li:sponsoredAccount:XXXXXXX"

# --- App 1: dados orgânicos (Community Management API) ---
LINKEDIN_ORGANIC_ACCESS_TOKEN = "..."
LINKEDIN_ORGANIC_REFRESH_TOKEN = "..."
LINKEDIN_ORGANIC_CLIENT_SECRET = "..."
LINKEDIN_ORGANIC_EXPIRES_IN = 5184000

# --- App 2: dados pagos (Advertising API) ---
LINKEDIN_PAID_ACCESS_TOKEN = "..."
LINKEDIN_PAID_REFRESH_TOKEN = "..."
LINKEDIN_PAID_CLIENT_SECRET = "..."
LINKEDIN_PAID_EXPIRES_IN = 5184000

# --- Tela de acesso (opcional) ---
[login]
usuario = "senha"
```

Onde pegar cada valor: [LinkedIn Developer Portal](https://www.linkedin.com/developers/apps) → seu app → **Products/Products autorizados** e **Auth** (client id/secret, tokens do fluxo OAuth).

---

## 6. Rotina mensal: atualizar a planilha de fallback

A planilha em `export_excel/` é só a rede de segurança (usada só se a API falhar). Mantenha-a com no máximo 1–2 meses de defasagem:

1. No LinkedIn da página: **Análise → Conteúdo**.
2. Escolha o período (ex.: últimos 12 meses) e clique em **Exportar**.
3. Salve o arquivo baixado dentro de `export_excel/` (o app sempre usa o `*_content_*.xls` mais recente; os antigos podem ser apagados).
4. Reinicie o app (ou espere o cache de 12h expirar) para reconhecer o arquivo novo.

---

## 7. Erros comuns e o que fazer

Todas as mensagens aparecem na caixa expansível **"Consulta concluída"**, no topo da página. O app **nunca fica inoperante** por erro da API: ele troca para a planilha e avisa.

| Mensagem (resumo) | Causa | O que fazer |
|---|---|---|
| `token do LinkedIn expirado ou inválido (HTTP 401)` | Tokens venceram ou foram revogados | Gerar tokens novos no Developer Portal e atualizar os secrets (**local e Streamlit Cloud**). |
| `Não consegui renovar o token… (HTTP …)` (aviso amarelo) | O refresh token foi recusado | Renovar os tokens manualmente e atualizar os secrets em breve. |
| `limite de consultas da API atingido (HTTP 429)` | Estourou as 500 chamadas/dia do app de desenvolvimento | Nada a fazer: o cache tenta sozinho em até 12h. Se recorrente, pedir aprovação de uso no Developer Portal. |
| `sem permissão para estes dados (HTTP 403)` | App sem o produto liberado | Conferir os produtos do app no Developer Portal. |
| `sem conexão / tempo esgotado` | Internet do servidor | Verificar a conexão e recarregar. |
| `ERRO CRÍTICO NA PLANILHA DE EXPORTAÇÃO` | Arquivo `*_content_*.xls` ausente/corrompido | Baixar export novo (seção 6) para `export_excel/`. |
| `Usuário ou senha inválidos.` | Login errado | Conferir a seção `[login]` dos secrets. |
| Números levemente diferentes do site do LinkedIn | Dado ao vivo (impressões mudam a cada minuto) | Diferença de ~0,1% é normal. Acima de 2–3%, conferir período no seletor e recarregar. |

---

## 8. Publicação no Streamlit Community Cloud

1. O repositório no GitHub (`Nie-santuario/LinkedIn-Dashboard-CE`, branch `main`) é a fonte do deploy.
2. No [Streamlit Cloud](https://share.streamlit.io/), aponte o app para o arquivo `app.py`.
3. Em **Settings → Secrets**, cole o mesmo conteúdo do `secrets.toml` (seção 5), incluindo o bloco `[login]`.
4. Alterações no código: `git push` no `main` → o Streamlit Cloud redesenha sozinho. Alterações nos secrets: salvar no painel já recarrega.

---

## 9. Segurança (não negociável)

- **Nunca** commitar `.streamlit/secrets.toml` — ele está no `.gitignore` e nunca deve sair da máquina.
- **Nunca** colocar token, client secret ou senha em código Python. Tudo vem de `st.secrets`.
- O arquivo `.streamlit/secrets.toml.example` é só um modelo com placeholders — é o único que é versionado.
- Tokens com acesso a dados da empresa: mantenha-os apenas nos secrets e rotacione quando o app avisar (seção 7).
