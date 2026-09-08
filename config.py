"""
Configurações centrais do dashboard.
Nenhum segredo (client secret, access token, refresh token) deve
ser hardcoded aqui. Tudo vem de st.secrets (local: .streamlit/secrets.toml,
produção: painel de Secrets do Streamlit Community Cloud).
"""
import streamlit as st

# --- Identidade visual / textos fixos ---
NOME_CLIENTE = "Centro de Eventos Padre Vítor Coelho de Almeida"
TITULO_APP = "DASHBOARD DE RESULTADOS | LINKEDIN"
COR_HEADER = "#003366"
COR_AZUL = "#1f77b4"
COR_VERDE = "#2ca02c"
COR_LARANJA = "#ff7f0e"
COR_ROXO = "#9467bd"

# --- LinkedIn API ---
LINKEDIN_VERSION = "202601"  # header LinkedIn-Version
RESTLI_PROTOCOL_VERSION = "2.0.0"

LINKEDIN_API_BASE = "https://api.linkedin.com/rest"
LINKEDIN_OAUTH_TOKEN_URL = "https://www.linkedin.com/oauth/v2/accessToken"

# Client IDs não são segredo (são públicos por design do OAuth2),
# mas ficam centralizados aqui para facilitar troca futura.
ORGANIC_CLIENT_ID = "77ic20ktvrsmzm"
PAID_CLIENT_ID = "77zhnwtyvva5g0"


def get_secret(key: str, default=None):
    """Lê um segredo de st.secrets sem quebrar o app se não existir
    (permite rodar em modo mock antes das chaves reais serem configuradas)."""
    try:
        return st.secrets[key]
    except (KeyError, FileNotFoundError):
        return default


# --- Flags de execução ---
def modo_mock_ativo() -> bool:
    """Retorna True se as credenciais reais não estiverem configuradas —
    nesse caso o app roda 100% com dados fictícios para validar o layout."""
    tem_organic = get_secret("LINKEDIN_ORGANIC_ACCESS_TOKEN") is not None
    tem_paid = get_secret("LINKEDIN_PAID_ACCESS_TOKEN") is not None
    return not (tem_organic and tem_paid)


CACHE_TTL_SECONDS = 60 * 60 * 12  # 12 horas, conforme brief
