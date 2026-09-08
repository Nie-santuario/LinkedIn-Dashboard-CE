"""
Gerenciamento de tokens OAuth2 do LinkedIn.

O LinkedIn usa access tokens de 60 dias e refresh tokens de 1 ano
(quando o app tem o produto "Sign In with LinkedIn using OpenID Connect"
ou fluxo de 3-legged OAuth habilitado). Este módulo tenta usar o access
token direto e, se expirado, tenta renovautomaticamente via refresh_token.

IMPORTANTE: client_secret, access_token e refresh_token nunca devem
aparecer no código. Eles vêm de st.secrets.
"""
import time
import requests
import streamlit as st

from config import get_secret, LINKEDIN_OAUTH_TOKEN_URL, ORGANIC_CLIENT_ID, PAID_CLIENT_ID


class TokenBundle:
    def __init__(self, access_token: str, expires_at: float, refresh_token: str | None = None):
        self.access_token = access_token
        self.expires_at = expires_at  # timestamp unix
        self.refresh_token = refresh_token

    @property
    def expirado(self) -> bool:
        # margem de segurança de 5 minutos
        return time.time() > (self.expires_at - 300)


def _refresh_access_token(client_id: str, client_secret: str, refresh_token: str) -> dict:
    """Chama o endpoint de refresh do LinkedIn OAuth2. Retorna o JSON de resposta."""
    resp = requests.post(
        LINKEDIN_OAUTH_TOKEN_URL,
        data={
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": client_id,
            "client_secret": client_secret,
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()


@st.cache_resource(ttl=3600)  # revalida token no máximo 1x por hora
def _token_cache_key(app_name: str):
    """Cache_resource guarda objeto Python mutável (TokenBundle) por sessão
    de servidor — assim não refazemos refresh a cada rerun do Streamlit."""
    return {"bundle": None}


def get_valid_token(app_name: str) -> str | None:
    """
    app_name: "organic" ou "paid".
    Retorna um access_token válido, renovando via refresh_token se necessário.
    Retorna None se não houver credenciais configuradas (modo mock deve
    ser usado nesse caso pelo chamador).
    """
    prefix = "LINKEDIN_ORGANIC" if app_name == "organic" else "LINKEDIN_PAID"
    client_id = ORGANIC_CLIENT_ID if app_name == "organic" else PAID_CLIENT_ID

    access_token = get_secret(f"{prefix}_ACCESS_TOKEN")
    refresh_token = get_secret(f"{prefix}_REFRESH_TOKEN")
    client_secret = get_secret(f"{prefix}_CLIENT_SECRET")
    # expires_in vindo do secrets é opcional; se ausente assume 55 dias (token de 60d, com folga)
    expires_in = int(get_secret(f"{prefix}_EXPIRES_IN", 60 * 24 * 60 * 60))

    if not access_token:
        return None

    cache = _token_cache_key(app_name)
    if cache["bundle"] is None:
        cache["bundle"] = TokenBundle(
            access_token=access_token,
            expires_at=time.time() + expires_in,
            refresh_token=refresh_token,
        )

    bundle: TokenBundle = cache["bundle"]

    if bundle.expirado and bundle.refresh_token and client_secret:
        try:
            data = _refresh_access_token(client_id, client_secret, bundle.refresh_token)
            bundle.access_token = data["access_token"]
            bundle.expires_at = time.time() + data.get("expires_in", expires_in)
            if "refresh_token" in data:
                bundle.refresh_token = data["refresh_token"]
        except requests.HTTPError as e:
            st.warning(
                f"Falha ao renovar token do app '{app_name}': {e}. "
                "Usando o token atual até expirar de vez — atualize os secrets em breve."
            )

    return bundle.access_token
