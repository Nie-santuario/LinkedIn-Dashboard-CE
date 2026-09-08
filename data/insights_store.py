"""
Persistência do texto de "Insights do Mês" digitado pelo time de marketing.

Usa JSON em disco (conforme decisão do projeto: 1 usuário hoje, no máximo
3 no futuro, raramente simultâneos). Para reduzir o risco de dois usuários
salvarem ao mesmo tempo e um sobrescrever o outro, usamos um lock de arquivo
simples (filelock). Se o volume de usuários crescer de verdade, trocar isso
por SQLite é o próximo passo natural — não por Postgres, ainda é baixo volume.
"""
import json
import os
from filelock import FileLock

CAMINHO_ARQUIVO = os.path.join(os.path.dirname(__file__), "..", "insights_marketing.json")
CAMINHO_LOCK = CAMINHO_ARQUIVO + ".lock"


def carregar_insights() -> str:
    if not os.path.exists(CAMINHO_ARQUIVO):
        return ""
    try:
        with FileLock(CAMINHO_LOCK, timeout=5):
            with open(CAMINHO_ARQUIVO, "r", encoding="utf-8") as f:
                return json.load(f).get("texto", "")
    except Exception:
        return ""


def salvar_insights(texto: str) -> bool:
    try:
        with FileLock(CAMINHO_LOCK, timeout=5):
            with open(CAMINHO_ARQUIVO, "w", encoding="utf-8") as f:
                json.dump({"texto": texto}, f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False
