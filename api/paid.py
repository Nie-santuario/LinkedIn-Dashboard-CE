"""
Cliente para a Advertising API (App 2 — Tráfego Pago).
Endpoint: /rest/adAnalytics
"""
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
def buscar_analytics_pagos(account_urn: str, data_inicio: str, data_fim: str) -> list[dict]:
    """
    Busca métricas de campanhas patrocinadas no período.

    A consulta usa a sintaxe atual do Analytics Finder. Sem ``fields``, a API
    retorna as métricas padrão (impressions e clicks), evitando a projeção
    inválida que a conta estava rejeitando.
    """
    access_token = get_valid_token("paid")
    if access_token is None:
        raise RuntimeError("Token pago não configurado")

    url = f"{LINKEDIN_API_BASE}/adAnalytics"
    ini = _para_data_linkedin(data_inicio)
    fim = _para_data_linkedin(data_fim)
    date_range = (
        f"(start:(day:{ini['day']},month:{ini['month']},year:{ini['year']}),"
        f"end:(day:{fim['day']},month:{fim['month']},year:{fim['year']}))"
    )
    query = (
        "q=analytics&pivot=CREATIVE&timeGranularity=DAILY"
        f"&dateRange={date_range}&accounts=List({quote(account_urn, safe='')})"
    )

    resp = requests.get(f"{url}?{query}", headers=_headers(access_token), timeout=20)
    resp.raise_for_status()
    return resp.json().get("elements", [])


def _para_data_linkedin(data_iso: str) -> dict:
    ano, mes, dia = data_iso.split("-")
    return {"day": int(dia), "month": int(mes), "year": int(ano)}
