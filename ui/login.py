"""Autenticação simples do dashboard (usuário + senha).

Ativa somente quando os secrets do Streamlit têm a seção [login]:

    [login]
    ana = "senha123"
    joao = "senha456"

Sem essa seção (ex.: máquina local sem a seção, ou secrets.toml
ausente), o acesso fica aberto — credenciais_login devolve None e o
app roda igual sempre. As senhas vivem no painel do Streamlit Cloud
(Settings > Secrets) ou no .streamlit/secrets.toml local (gitignored),
nunca no repositório.
"""

import hmac

import streamlit as st

from config import NOME_CLIENTE, TITULO_APP


def credenciais_login(secrets) -> dict | None:
    """Devolve {usuario: senha} se a seção [login] existir; senão None.

    `secrets` é o objeto st.secrets (ou qualquer mapping). Arquivo
    ausente (máquina local) => login desligado (None). TOML quebrado ou
    seção inválida => a exceção PROPAGA (tela de erro, dados bloqueados)
    — nunca desliga o login em silêncio.
    """
    try:
        if "login" not in secrets:
            return None
    except FileNotFoundError:
        # Sem secrets.toml (máquina local): acesso aberto, por desenho.
        return None
    secao = secrets["login"]
    return {str(u).strip(): str(s).strip() for u, s in dict(secao).items()}


def autenticar(credenciais: dict | None, usuario: str, senha: str) -> bool:
    """True se usuario/senha conferem com as credenciais carregadas."""
    if not credenciais:
        return False
    esperado = credenciais.get(usuario.strip())
    if esperado is None:
        return False
    # compare_digest evita timing side-channel; custo zero aqui.
    return hmac.compare_digest(esperado.encode("utf-8"), senha.strip().encode("utf-8"))


def render_tela_login(credenciais: dict) -> None:
    """Tela de acesso — roda ANTES de qualquer dado (o chamador dá st.stop())."""
    st.markdown(
        f"""
    <style>
    .login-card {{
        max-width: 380px;
        margin: 5rem auto 0 auto;
        background: white;
        border-radius: 0.75rem;
        border: 1px solid #e2e8f0;
        box-shadow: 0 4px 16px rgba(0,0,0,0.08);
        padding: 2rem 1.75rem 1.5rem 1.75rem;
        text-align: center;
    }}
    .login-card h2 {{
        font-weight: 700;
        font-size: 1.25rem;
        color: #0f172a;
        margin: 0.75rem 0 0.25rem 0;
    }}
    .login-card p {{
        font-size: 0.8125rem;
        color: #64748b;
        margin: 0;
    }}
    .login-card .stForm {{
        text-align: left;
    }}
    </style>
    <div class="login-card">
        <div style="font-size: 2.25rem;">📊</div>
        <h2>{TITULO_APP}</h2>
        <p>{NOME_CLIENTE}</p>
    </div>
    """,
        unsafe_allow_html=True,
    )

    with st.form("login_form"):
        usuario = st.text_input("Usuário")
        senha = st.text_input("Senha", type="password")
        enviado = st.form_submit_button("Entrar", width="stretch")

    if enviado:
        if autenticar(credenciais, usuario, senha):
            st.session_state["logado"] = True
            st.rerun()
        else:
            st.error("Usuário ou senha inválidos.")
