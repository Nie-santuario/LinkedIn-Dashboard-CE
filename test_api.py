"""
Script avulso para testar as duas APIs do LinkedIn e capturar a estrutura
real do JSON de resposta — SEM depender do Streamlit rodando.

Como usar:
1. Preencha .streamlit/secrets.toml (mesmo arquivo usado pelo app.py) com
   os tokens reais. Este script lê dali. Se preferir, pode usar variáveis
   de ambiente em vez disso (veja _get() abaixo).
2. Rode: python test_api.py
3. O resultado é salvo em: api_debug_output.json (também aparece no console)
4. Me envie o conteúdo de api_debug_output.json (ou cole aqui no chat) —
   NÃO precisa reenviar o token, só o JSON de resposta da API.

Este script NÃO imprime o access_token no console/arquivo, para evitar
vazamento acidental caso você copie e cole a saída em algum lugar.
"""
import json
import os
import sys
from pathlib import Path

import requests

try:
    import tomllib  # Python 3.11+
except ModuleNotFoundError:
    import tomli as tomllib  # type: ignore  # pip install tomli, se Python < 3.11

LINKEDIN_VERSION = "202601"
RESTLI_PROTOCOL_VERSION = "2.0.0"
LINKEDIN_API_BASE = "https://api.linkedin.com/rest"

SECRETS_PATH = Path(__file__).parent / ".streamlit" / "secrets.toml"


def _load_secrets() -> dict:
    if SECRETS_PATH.exists():
        with open(SECRETS_PATH, "rb") as f:
            return tomllib.load(f)
    return {}


def _get(secrets: dict, key: str) -> str | None:
    """Prioriza variável de ambiente; cai para secrets.toml se não achar."""
    return os.environ.get(key) or secrets.get(key)


def _headers(access_token: str) -> dict:
    return {
        "Authorization": f"Bearer {access_token}",
        "LinkedIn-Version": LINKEDIN_VERSION,
        "X-Restli-Protocol-Version": RESTLI_PROTOCOL_VERSION,
    }


def testar_organico(secrets: dict) -> dict:
    token = _get(secrets, "LINKEDIN_ORGANIC_ACCESS_TOKEN")
    org_urn = _get(secrets, "LINKEDIN_ORGANIZATION_URN")

    if not token or not org_urn:
        return {"erro": "LINKEDIN_ORGANIC_ACCESS_TOKEN ou LINKEDIN_ORGANIZATION_URN não configurados."}

    url = f"{LINKEDIN_API_BASE}/organizationalEntityShareStatistics"
    params = {"q": "organizationalEntity", "organizationalEntity": org_urn}

    resp = requests.get(url, headers=_headers(token), params=params, timeout=20)
    resultado = {
        "endpoint": url,
        "status_code": resp.status_code,
    }
    try:
        resultado["body"] = resp.json()
    except ValueError:
        resultado["body_raw"] = resp.text[:2000]
    return resultado


def testar_pago(secrets: dict) -> dict:
    token = _get(secrets, "LINKEDIN_PAID_ACCESS_TOKEN")
    account_urn = _get(secrets, "LINKEDIN_AD_ACCOUNT_URN")

    if not token or not account_urn:
        return {"erro": "LINKEDIN_PAID_ACCESS_TOKEN ou LINKEDIN_AD_ACCOUNT_URN não configurados."}

    url = f"{LINKEDIN_API_BASE}/adAnalytics"
    params = {
        "q": "analytics",
        "pivot": "CREATIVE",
        "dateRange.start.day": 1,
        "dateRange.start.month": 7,
        "dateRange.start.year": 2026,
        "dateRange.end.day": 31,
        "dateRange.end.month": 7,
        "dateRange.end.year": 2026,
        "timeGranularity": "DAILY",
        "accounts[0]": account_urn,
        "fields": "impressions,clicks,costInLocalCurrency,dateRange",
    }

    resp = requests.get(url, headers=_headers(token), params=params, timeout=20)
    resultado = {
        "endpoint": url,
        "status_code": resp.status_code,
    }
    try:
        resultado["body"] = resp.json()
    except ValueError:
        resultado["body_raw"] = resp.text[:2000]
    return resultado


def main():
    secrets = _load_secrets()

    print("=== Testando API orgânica (Community Management) ===")
    resultado_organico = testar_organico(secrets)
    print(json.dumps(resultado_organico, indent=2, ensure_ascii=False))

    print("\n=== Testando API paga (Advertising) ===")
    resultado_pago = testar_pago(secrets)
    print(json.dumps(resultado_pago, indent=2, ensure_ascii=False))

    saida = {"organico": resultado_organico, "pago": resultado_pago}
    caminho_saida = Path(__file__).parent / "api_debug_output.json"
    with open(caminho_saida, "w", encoding="utf-8") as f:
        json.dump(saida, f, indent=2, ensure_ascii=False)

    print(f"\n✅ Resultado salvo em: {caminho_saida}")
    print("Envie o conteúdo desse arquivo (é só estrutura de dados, sem token) para eu mapear os campos.")


if __name__ == "__main__":
    sys.exit(main())
