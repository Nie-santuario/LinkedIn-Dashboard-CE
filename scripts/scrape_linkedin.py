import os
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

# ============================================================
# Configurações
# ============================================================
EXPORT_DIR = Path("export_excel")
PROFILE_DIR = Path("./linkedin_profile")  # Perfil persistente do navegador

LINKEDIN_ORG_ID = "79712925"  # ID da sua organização no LinkedIn

# URL da página de analytics
ANALYTICS_URL = f"https://www.linkedin.com/company/{LINKEDIN_ORG_ID}/admin/analytics/updates/"


def run():
    EXPORT_DIR.mkdir(exist_ok=True)
    PROFILE_DIR.mkdir(exist_ok=True)

    with sync_playwright() as p:
        print("Iniciando navegador com perfil persistente...")

        # ------------------------------------------------------------
        # launch_persistent_context: usa um diretório de perfil real,
        # que mantém cookies, localStorage, cache, etc. entre execuções.
        # ------------------------------------------------------------
        context = p.chromium.launch_persistent_context(
            user_data_dir=PROFILE_DIR,
            headless=False,  # Mantenha False na PRIMEIRA execução para fazer login
            accept_downloads=True,
            viewport={"width": 1280, "height": 720},
        )

        # Como o context já vem com uma página aberta, pegamos ela
        page = context.pages[0] if context.pages else context.new_page()

        # ------------------------------------------------------------
        # Verifica se já está logado
        # ------------------------------------------------------------
        print("Verificando sessão do LinkedIn...")
        page.goto("https://www.linkedin.com/feed/", wait_until="domcontentloaded")

        if "login" in page.url or "checkpoint" in page.url:
            print("⚠️  Você não está logado. Faça o login manualmente na janela do navegador.")
            print("   Após o login, o script continuará automaticamente.")
            # Espera indefinidamente até o usuário logar e a URL mudar
            page.wait_for_url("**/feed/**", timeout=0)
            print("✅ Login detectado! Sessão salva no perfil persistente.")
        else:
            print("✅ Já está logado! Reutilizando sessão existente.")

        # ------------------------------------------------------------
        # Navega para a página de Analytics
        # ------------------------------------------------------------
        print("Acessando página de Analytics...")
        page.goto(ANALYTICS_URL, wait_until="domcontentloaded")

        try:
            # Espera o botão Exportar aparecer
            page.wait_for_selector("button:has-text('Exportar')", timeout=20000)
        except Exception:
            print("❌ Erro ao carregar a página. A página pode ter mudado ou a sessão expirou.")
            page.screenshot(path="debug_linkedin.png", full_page=True)
            print("📸 Screenshot salva como debug_linkedin.png")
            context.close()
            return

        print("Página carregada. Ajustando período para últimos 365 dias...")

        # ------------------------------------------------------------
        # Clica no Dropdown do calendário para selecionar o período
        # ------------------------------------------------------------
        try:
            dropdown_trigger = page.locator("button.artdeco-dropdown__trigger", has_text="Período:")
            if dropdown_trigger.is_visible():
                dropdown_trigger.click()
                time.sleep(1)

                # Tenta clicar na opção "Últimos 365 dias"
                page.locator("text=Últimos 365").first.click()
                time.sleep(2)
                print("✅ Período ajustado.")
            else:
                print("ℹ️  Dropdown de período não encontrado, usando o padrão.")
        except Exception as e:
            print(f"ℹ️  Não foi possível ajustar o período ({e}). Continuando com o padrão.")

        # ------------------------------------------------------------
        # Clica em Exportar e aguarda o download
        # ------------------------------------------------------------
        print("Iniciando download...")
        with page.expect_download(timeout=60000) as download_info:
            page.locator("button:has-text('Exportar')").first.click()

        download = download_info.value

        # Salva o arquivo na pasta correta
        file_path = EXPORT_DIR / download.suggested_filename
        download.save_as(file_path)
        print(f"🎉 Sucesso! Arquivo salvo em: {file_path.resolve()}")

        # ------------------------------------------------------------
        # Fecha o context (isso salva o estado do perfil)
        # ------------------------------------------------------------
        context.close()


if __name__ == "__main__":
    run()