"""
Cliente para a Community Management API (App 1 — Tráfego Orgânico).
Endpoints: /rest/posts e /rest/organizationalEntityShareStatistics
"""
import datetime as dt

import requests
import streamlit as st
from urllib.parse import quote

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
def buscar_posts_organicos(organization_urn: str) -> list[dict]:
    """
    Busca as publicações orgânicas recentes da página.
    O resultado de 50 posts é cacheado; a filtragem de data 
    ocorre localmente no dashboard via Pandas.
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
def buscar_estatisticas_organicas(organization_urn: str) -> list[dict]:
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


@st.cache_data(ttl=CACHE_TTL_SECONDS, show_spinner=False)
def estatisticas_diarias(organization_urn: str, data_inicio: dt.date, data_fim: dt.date) -> list[dict]:
    """Série orgânica DIÁRIA (janela rolling de 12 meses) para os gráficos e KPIs.

    A query é montada na mão (padrão paid.py): o LinkedIn devolve 400 se
    parênteses/dois-pontos/vírgulas do formato Rest.li forem percent-encoded.
    """
    access_token = get_valid_token("organic")
    if access_token is None:
        raise RuntimeError("Token orgânico não configurado")

    start = int(dt.datetime.combine(data_inicio, dt.time()).timestamp() * 1000)
    fim_mais_um = dt.datetime.combine(data_fim, dt.time()) + dt.timedelta(days=1)
    end = int(fim_mais_um.timestamp() * 1000)
    qs = (
        "q=organizationalEntity"
        f"&organizationalEntity={quote(organization_urn, safe='')}"
        f"&timeIntervals=(timeRange:(start:{start},end:{end}),timeGranularityType:DAY)"
    )
    resp = requests.get(
        f"{LINKEDIN_API_BASE}/organizationalEntityShareStatistics?{qs}",
        headers=_headers(access_token),
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json().get("elements", [])


@st.cache_data(ttl=CACHE_TTL_SECONDS, show_spinner=False)
def estatisticas_por_posts(organization_urn: str, post_urns: tuple[str, ...]) -> dict[str, dict]:
    """{post_urn: estatísticas} LIFETIME por publicação (a API não recorta por período).

    Shares e ugcPosts vão em chamadas separadas com lista no formato List(...):
    colchete indexado (ugcPosts[i]) é percent-encoded pelo requests e o
    LinkedIn rejeita a requisição com 400.
    """
    if not post_urns:
        return {}

    access_token = get_valid_token("organic")
    if access_token is None:
        raise RuntimeError("Token orgânico não configurado")

    base = (
        "q=organizationalEntity"
        f"&organizationalEntity={quote(organization_urn, safe='')}"
    )
    out: dict[str, dict] = {}

    def _get(qs_extra: str) -> None:
        resp = requests.get(
            f"{LINKEDIN_API_BASE}/organizationalEntityShareStatistics?{base}{qs_extra}",
            headers=_headers(access_token),
            timeout=30,
        )
        resp.raise_for_status()
        for el in resp.json().get("elements", []):
            chave = el.get("share") or el.get("ugcPost")
            if chave:
                out[chave] = el.get("totalShareStatistics", {})

    shares = tuple(u for u in post_urns if ":share:" in u)
    ugc = tuple(u for u in post_urns if ":ugcPost:" in u)
    if shares:
        _get("&shares=List(" + ",".join(quote(u, safe="") for u in shares) + ")")
    if ugc:
        _get("&ugcPosts=List(" + ",".join(quote(u, safe="") for u in ugc) + ")")
    return out