"""
Cliente para a Community Management API (App 1 — Tráfego Orgânico).
Endpoints: /rest/posts e /rest/organizationalEntityShareStatistics
"""
import requests
import streamlit as st

from config import (
    LINKEDIN_API_BASE,
    LINKEDIN_VERSION,
    RESTLI_PROTOCOL_VERSION,
    CACHE_TTL_SECONDS,
)
from api.auth import get_valid_token


def _headers(access_token: str) -> dict:
    return {
        "Authorization": f"Bearer {access_token}",
        "LinkedIn-Version": LINKEDIN_VERSION,
        "X-Restli-Protocol-Version": RESTLI_PROTOCOL_VERSION,
    }


@st.cache_data(ttl=CACHE_TTL_SECONDS, show_spinner=False)
def buscar_posts_organicos(organization_urn: str, data_inicio: str, data_fim: str) -> list[dict]:
    """
    Busca as publicações orgânicas da página no período.
    data_inicio/data_fim no formato 'YYYY-MM-DD' (usados apenas para
    filtrar localmente o resultado, já que o endpoint /rest/posts
    não filtra por data diretamente).
    """
    access_token = get_valid_token("organic")
    if access_token is None:
        raise RuntimeError("Token orgânico não configurado")

    url = f"{LINKEDIN_API_BASE}/posts"
    params = {"q": "author", "author": organization_urn, "count": 50}

    resp = requests.get(url, headers=_headers(access_token), params=params, timeout=20)
    resp.raise_for_status()
    elementos = resp.json().get("elements", [])
    return elementos


@st.cache_data(ttl=CACHE_TTL_SECONDS, show_spinner=False)
def buscar_estatisticas_organicas(organization_urn: str, data_inicio: str, data_fim: str) -> list[dict]:
    """
    Busca impressões, cliques, reações, engajamento por publicação.
    Endpoint: /rest/organizationalEntityShareStatistics
    """
    access_token = get_valid_token("organic")
    if access_token is None:
        raise RuntimeError("Token orgânico não configurado")

    url = f"{LINKEDIN_API_BASE}/organizationalEntityShareStatistics"
    params = {
        "q": "organizationalEntity",
        "organizationalEntity": organization_urn,
    }

    resp = requests.get(url, headers=_headers(access_token), params=params, timeout=20)
    resp.raise_for_status()
    return resp.json().get("elements", [])
