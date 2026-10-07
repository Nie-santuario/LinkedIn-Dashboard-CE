"""
Cliente para a Advertising API (App 2 — Tráfego Pago).
Endpoint: /rest/adAnalytics
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


@st.cache_data(ttl=CACHE_TTL_SECONDS, show_spinner=False)
def buscar_analytics_diarios(account_urn: str, data_inicio: dt.date, data_fim: dt.date) -> list[dict]:
    """Série PAGA diária (pivot=ACCOUNT) para os gráficos e KPIs do período.

    ``fields`` explícito: sem ele a API devolve só impressions/clicks e as
    reações/comentários/compartilhamentos pagos ficariam de fora dos totais
    que o export exibe.
    """
    access_token = get_valid_token("paid")
    if access_token is None:
        raise RuntimeError("Token pago não configurado")

    ini = _para_data_linkedin(data_inicio.isoformat())
    fim = _para_data_linkedin(data_fim.isoformat())
    date_range = (
        f"(start:(day:{ini['day']},month:{ini['month']},year:{ini['year']}),"
        f"end:(day:{fim['day']},month:{fim['month']},year:{fim['year']}))"
    )
    query = (
        "q=analytics&pivot=ACCOUNT&timeGranularity=DAILY"
        "&fields=impressions,clicks,reactions,comments,shares,costInLocalCurrency,dateRange"
        f"&dateRange={date_range}&accounts=List({quote(account_urn, safe='')})"
    )

    resp = requests.get(f"{LINKEDIN_API_BASE}/adAnalytics?{query}", headers=_headers(access_token), timeout=30)
    resp.raise_for_status()
    return resp.json().get("elements", [])


@st.cache_data(ttl=CACHE_TTL_SECONDS, show_spinner=False)
def analytics_por_criativo(account_urn: str, data_inicio: dt.date, data_fim: dt.date) -> dict[str, dict]:
    """Totais pagos por criativo (pivot=CREATIVE) no período.

    Retorna ``{creative_urn: {"impressoes": int, "cliques": int, ...}}`` — usado
    para somar a parte patrocinada na métrica do post no Top 5.
    """
    access_token = get_valid_token("paid")
    if access_token is None:
        raise RuntimeError("Token pago não configurado")

    ini = _para_data_linkedin(data_inicio.isoformat())
    fim = _para_data_linkedin(data_fim.isoformat())
    date_range = (
        f"(start:(day:{ini['day']},month:{ini['month']},year:{ini['year']}),"
        f"end:(day:{fim['day']},month:{fim['month']},year:{fim['year']}))"
    )
    query = (
        "q=analytics&pivot=CREATIVE&timeGranularity=DAILY"
        "&fields=impressions,clicks,reactions,comments,shares,costInLocalCurrency,dateRange,pivotValues"
        f"&dateRange={date_range}&accounts=List({quote(account_urn, safe='')})"
    )
    resp = requests.get(f"{LINKEDIN_API_BASE}/adAnalytics?{query}", headers=_headers(access_token), timeout=30)
    resp.raise_for_status()

    totais: dict[str, dict] = {}
    for el in resp.json().get("elements", []):
        for creative in el.get("pivotValues", []):
            t = totais.setdefault(
                creative,
                {"impressoes": 0, "cliques": 0, "reacoes": 0, "comentarios": 0, "compartilhamentos": 0},
            )
            t["impressoes"] += el.get("impressions", 0) or 0
            t["cliques"] += el.get("clicks", 0) or 0
            t["reacoes"] += el.get("reactions", 0) or 0
            t["comentarios"] += el.get("comments", 0) or 0
            t["compartilhamentos"] += el.get("shares", 0) or 0
    return totais


@st.cache_data(ttl=86400, show_spinner=False)
def share_do_creative(account_urn: str, creative_urn: str) -> str | None:
    """Resolve o URN do criativo pago para o URN da publicação (post) associada."""
    access_token = get_valid_token("paid")
    if access_token is None:
        raise RuntimeError("Token pago não configurado")

    account_id = account_urn.split(":")[-1] if account_urn.startswith("urn:") else account_urn
    url = f"{LINKEDIN_API_BASE}/adAccounts/{account_id}/creatives/{quote(creative_urn, safe='')}"
    resp = requests.get(url, headers=_headers(access_token), timeout=20)
    resp.raise_for_status()
    return resp.json().get("content", {}).get("reference")


def _para_data_linkedin(data_iso: str) -> dict:
    ano, mes, dia = data_iso.split("-")
    return {"day": int(dia), "month": int(mes), "year": int(ano)}
