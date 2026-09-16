# Dashboard LinkedIn - Centro de Eventos Padre Vítor Coelho de Almeida

Bem-vindo à documentação oficial do projeto **Dashboard de Resultados do LinkedIn**. 
Este projeto é uma aplicação [Streamlit](https://streamlit.io/) desenvolvida para visualizar, analisar e exportar relatórios de métricas (orgânicas e pagas) do LinkedIn.

---

## 1. Visão Geral

O propósito principal deste dashboard é centralizar a análise de desempenho do LinkedIn, combinando dados orgânicos e pagos. Ele oferece:
- **Métricas Visuais (KPIs):** Acompanhamento de Impressões, Cliques, Reações, Engajamento Médio e CTR Geral.
- **Gráficos Interativos:** Visualização da evolução diária, comparativos de impressões vs engajamento e mix de interações (utilizando Plotly).
- **Geração de Relatórios (PDF):** Exportação de um relatório executivo formatado (paisagem, A4) contendo o panorama geral, top publicações e insights gerados automaticamente.

---

## 2. Estrutura do Projeto

Abaixo está o mapeamento dos principais arquivos e suas respectivas responsabilidades:

- **`app.py`**
  - **Função:** Arquivo principal de entrada da aplicação.
  - **Responsabilidades:** Controle de estado da sessão (session state), configuração do layout, navegação (abas), formulário de seleção de datas e chamadas às funções de renderização de componentes e exportação.

- **`data/transform.py`**
  - **Função:** Módulo de ETL (Extract, Transform, Load) e cálculos matemáticos.
  - **Responsabilidades:** Cálculo de KPIs (Impressões, Cliques, Reações), taxas derivadas (Engajamento e CTR), ordenação de publicações, consolidação das métricas pagas (Ads) e manipulação geral dos DataFrames do Pandas.

- **`data/pdf_report.py`**
  - **Função:** Geração de relatórios PDF corporativos.
  - **Responsabilidades:** Utiliza a biblioteca `reportlab` para desenhar um PDF executivo (formato paisagem). Inclui tabelas estilizadas de Top Posts, comparativos mensais, insights dinâmicos e o CTR geral, tudo com estilos corporativos predefinidos.

- **`ui/components.py`**
  - **Função:** Construção dos blocos visuais da interface (Frontend Streamlit).
  - **Responsabilidades:** Funções para renderizar cartões de KPI (`render_kpis`), gráficos do Plotly (`render_grafico_impressoes`, `render_donut_mix`, etc.), lista das Top Publicações e tabelas comparativas.

- **`ui/styles.py`**
  - **Função:** Injeção de estilos customizados.
  - **Responsabilidades:** Contém código CSS bruto (inserido via `st.markdown(unsafe_allow_html=True)`) que define a aparência premium do cabeçalho, tipografia, bordas arredondadas e cores baseadas no padrão da marca.

- **`.streamlit/config.toml` & `secrets.toml`** (Não versionados por segurança)
  - **Função:** Configuração do ambiente e credenciais.
  - **Responsabilidades:** O `config.toml` define o tema do Streamlit e definições do servidor. O `secrets.toml` armazena as chaves de API, `LINKEDIN_ORGANIZATION_URN`, `LINKEDIN_AD_ACCOUNT_URN` e senhas de forma segura.

---

## 3. Instruções de Instalação e Execução (Passo a Passo)

### 🔹 Pré-requisitos
Antes de começar, você precisa ter instalado no seu computador:
 **Python 3.10 ou superior:** [Baixar Python no site oficial](https://www.python.org/downloads/)
   > ⚠️ **MUITO IMPORTANTE:** Na primeira tela de instalação do Python, marque a caixinha **"Add Python to PATH"** (Adicionar Python ao PATH) antes de clicar em instalar.


### 🔹 Passo 1: Baixar o Projeto para o seu Computador

Você pode escolher **uma** das duas opções abaixo:

#### Opção A: Usando o Git (Recomendado)
1. Abra o **Prompt de Comando (CMD)** ou **PowerShell** no seu computador.
2. Navegue até a pasta onde deseja salvar o projeto (ex: sua pasta de Documentos):
   ```bash
   cd Documents
   ```
3. Digite o comando abaixo e aperte `Enter`:
   ```bash
   git clone https://github.com/Nie-santuario/LinkedIn-Dashboard-CE.git
   ```
4. Entre na pasta do projeto que acabou de ser baixada:
   ```bash
   cd LinkedIn-Dashboard-CE
   ```

#### Opção B: Baixando como arquivo ZIP (Sem precisar do Git)
1. Acesse a página do repositório no GitHub: `https://github.com/Nie-santuario/LinkedIn-Dashboard-CE`
2. Clique no botão verde **`<> Code`** no canto superior direito da lista de arquivos.
3. Clique em **`Download ZIP`**.
4. Extraia a pasta baixada em um local de sua preferência (ex: em `Documentos`).
5. Abra a pasta extraída, clique na barra de endereços do Windows Explorer, digite `cmd` ou `powershell` e pressione `Enter` para abrir o terminal diretamente nessa pasta.

---

### 🔹 Passo 2: Criar e Ativar o Ambiente Virtual (venv)

O ambiente virtual serve como uma "caixa isolada" para instalar as bibliotecas do projeto sem bagunçar os outros programas do seu computador.

1. No terminal aberto dentro da pasta do projeto, digite o comando abaixo para criar o ambiente:
   ```bash
   python -m venv venv
   ```
   *(Aguarde alguns segundos até o comando finalizar)*

2. Agora, **ative** o ambiente virtual:
   - **No Windows (Prompt de Comando ou PowerShell):**
     ```bash
     venv\Scripts\activate
     ```
     > 💡 **Como saber se deu certo?** O nome `(venv)` aparecerá no início da linha do terminal (ex: `(venv) C:\Users\...`).
   - **No Linux ou Mac:**
     ```bash
     source venv/bin/activate
     ```

---

### 🔹 Passo 3: Instalar as Dependências

O arquivo `requirements.txt` contém a lista de todas as ferramentas e bibliotecas que o dashboard precisa para funcionar (como Streamlit, Pandas, Plotly e ReportLab).

Com o ambiente virtual ativado `(venv)`, execute:
```bash
pip install -r requirements.txt
```
*(Aguarde o download e a instalação de todos os pacotes)*

---

### 🔹 Passo 4: Configurar as Credenciais e Acessos (`secrets.toml`)

Por questões de segurança, chaves de API e senhas não ficam salvas publicamente no GitHub. Você precisará configurá-las localmente:

1. Na raiz da pasta do projeto, crie uma pasta chamada `.streamlit` (com o ponto no início).
2. Dentro da pasta `.streamlit`, crie um arquivo de texto chamado `secrets.toml`.
3. Abra esse arquivo com o Bloco de Notas ou VS Code e preencha com as credenciais fornecidas pelo administrador da conta:
   ```toml
   LINKEDIN_ORGANIZATION_URN = "urn:li:organization:SEU_ID_AQUI"
   LINKEDIN_AD_ACCOUNT_URN = "urn:li:sponsoredAccount:SEU_ID_AQUI"
   ```
4. Salve e feche o arquivo.

---

### 🔹 Passo 5: Executar o Dashboard

Com tudo configurado e com o ambiente `(venv)` ativo, inicie a aplicação com o comando:
```bash
streamlit run app.py
```

🎉 **Pronto!** O Streamlit iniciará o servidor local e abrirá automaticamente uma aba no seu navegador padrão no endereço `http://localhost:8501`.

> 🛑 **Como fechar/parar o dashboard quando terminar?**  
> Volte na janela do terminal onde o Streamlit está rodando e pressione **`Ctrl + C`**.

---

## 4. Guia de Manutenção

Este guia serve como referência rápida para futuras alterações na aplicação.

### 4.1. Adicionando/Alterando Novas Métricas ou KPIs
- **Cálculo da Métrica:** Acesse `data/transform.py` e adicione a lógica de cálculo (ex: dentro da função `kpis_periodo` ou `calcular_metricas_por_post`). 
- **Exibição na Tela:** Após calcular, vá em `ui/components.py` e modifique a função `render_kpis()` para adicionar um novo `_kpi_card()`. Não se esqueça de ajustar o número de colunas criadas por `st.columns()` no Streamlit.

### 4.2. Alterando Textos, Botões ou Inputs no Frontend
- Se for uma mudança no título da página, seletor de datas, barra de pesquisas ou layout de abas da página principal, edite **`app.py`**.
- Se for a mudança no título de um gráfico, no eixo do Plotly, ou na cor da linha de uma legenda, edite o respectivo método em **`ui/components.py`**.

### 4.3. Alterando o CSS e Identidade Visual (Cores)
- Para alterar cores de fundo, esconder elementos padrões do Streamlit (como header/footer), ou mexer no padding, altere o arquivo **`ui/styles.py`**.
- A cor base primária normalmente está mapeada no arquivo `config.py` e é importada para os estilos e componentes.

### 4.4. Alterando o Layout do PDF (ReportLab)
- Todo o código responsável pela exportação em PDF está restrito ao **`data/pdf_report.py`**.
- Para mudar a fonte, tamanho do texto ou cores de tabelas, altere os `ParagraphStyle` no início da função `gerar_pdf_dashboard`.
- Para adicionar novos blocos (uma nova página, por exemplo), crie novos objetos `Table` ou `Paragraph` e faça o `story.append()` antes de chamar `doc.build(story)`. 
- **Dica:** O ReportLab lida com layout através da lista `story`. A ordem em que você insere os elementos nessa lista determina a ordem de renderização no arquivo PDF.
