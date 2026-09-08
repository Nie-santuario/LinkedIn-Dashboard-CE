# LinkedIn-Dashboard-CE

Dashboard de Resultados LinkedIn

Dashboard em Streamlit para o Centro de Eventos Padre Vítor Coelho de Almeida,
consumindo a Community Management API (orgânico) e a Advertising API (pago)
do LinkedIn.

## Rodando localmente

```bash
pip install -r requirements.txt
streamlit run app.py
```

Sem nenhum secret configurado, o app roda automaticamente em **modo
demonstração** com os dados fictícios do wireframe (isso é intencional —
assim você valida o layout antes de plugar a API real).

## Configurando as credenciais reais

1. Copie `.streamlit/secrets.toml.example` para `.streamlit/secrets.toml`
2. Preencha com seus valores reais (URNs, access tokens, refresh tokens,
   client secrets)
3. **Nunca** commite `secrets.toml` — já está no `.gitignore`

## Deploy no share.streamlit.io

1. Crie um repositório GitHub privado para este projeto.
2. Envie o conteúdo desta pasta para o repositório. O arquivo real
  `.streamlit/secrets.toml` já está no `.gitignore` e não deve ser enviado.
3. Mantenha a pasta `export_excel` no repositório se quiser usar a exportação
  oficial como fallback quando a API atingir quota.
4. Em `share.streamlit.io`, selecione o repositório, a branch e o arquivo
  `app.py` como entrada.
5. Em **Settings > Secrets**, cole os valores reais do arquivo local
  `.streamlit/secrets.toml`.
6. Publique e valide o botão **Buscar dados**.

### Segurança antes do deploy

As credenciais que estavam no antigo template foram removidas. Como elas já
foram expostas durante o desenvolvimento, gere novos access tokens, refresh
tokens e client secrets no LinkedIn antes de publicar.

## Status atual da integração com a API real

O cliente HTTP das duas APIs (`api/organic.py`, `api/paid.py`) já está
implementado e autenticando corretamente. **O que falta antes de tirar do
modo mock**: mapear o JSON real retornado por `organizationalEntityShareStatistics`
e `adAnalytics` para o formato que `data/transform.py` espera (colunas:
`data`, `resumo`, `impressoes`, `cliques`, `reacoes`, `comentarios`,
`compartilhamentos`). Isso está marcado com `# TODO` em `app.py`, na seção
"2. Carregamento dos dados" — assim que você tiver uma resposta real da API
em mãos (rode uma chamada e cole o JSON), eu faço esse mapeamento.

## Estrutura do projeto

```
app.py                    # orquestração principal + layout
config.py                 # constantes, leitura de secrets
api/
  auth.py                 # gestão de token + refresh automático
  organic.py               # Community Management API
  paid.py                  # Advertising API
data/
  mock.py                  # dados fictícios (fallback)
  transform.py              # cálculo de CTR, engajamento, mix
  insights_store.py         # persistência do textarea de insights
ui/
  styles.py                 # CSS customizado
  components.py              # header, KPIs, gráficos, tabelas
.streamlit/
  secrets.toml.example       # template — copiar para secrets.toml
```

## Sobre persistência de "Insights do Mês"

Salvo em `insights_marketing.json` com file lock (`filelock`), adequado
para 1–3 usuários raramente simultâneos, como definido para este projeto.
Se o número de acessos concorrentes crescer de forma consistente no
futuro, vale migrar para SQLite.
