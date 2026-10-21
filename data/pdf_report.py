"""Gerador do relatório PDF executivo do Dashboard LinkedIn.

O relatório é montado em 3 páginas A4 paisagem, na ordem de leitura
executiva: resumo do período, desempenho e comparação, conteúdo e leitura.

Os gráficos são desenhados em vetor direto no canvas do PDF (sem Plotly,
sem kaleido, sem imagem rasterizada): o documento fica nítido em qualquer
impressora, não depende de binário externo no servidor e é gerado em
milissegundos.

Paleta e tipografia seguem a marca do projeto (config.py) e a regra de
contraste: uma cor de acento (azul institucional), verde/laranja/roxo
apenas como marca de dado dentro do donut e do engajamento.
"""
from io import BytesIO
import datetime as dt
import html
import math
import re

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas as pdf_canvas
from reportlab.platypus import (
    Flowable,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

# ---------------------------------------------------------------------------
# Paleta e medidas
# ---------------------------------------------------------------------------
AZUL_INSTITUCIONAL = colors.HexColor("#003366")
AZUL = colors.HexColor("#1f77b4")
VERDE = colors.HexColor("#2ca02c")
LARANJA = colors.HexColor("#ff7f0e")
ROXO = colors.HexColor("#9467bd")
TEXTO = colors.HexColor("#17324D")
SUAVE = colors.HexColor("#667085")
ROTULO = colors.HexColor("#4B5563")
FUNDO_TABELA = colors.HexColor("#EAF2FB")
FUNDO_BANNER = colors.HexColor("#F8F9FA")
FUNDO_FAIXA = colors.HexColor("#F7F9FC")
GRADE = colors.HexColor("#E6EAF0")
BORDA = colors.HexColor("#D9E1EA")
CINZA_CLARO = colors.HexColor("#D8E7F5")

CORES_MIX = {
    "Cliques": AZUL,
    "Reações": VERDE,
    "Comentários": LARANJA,
    "Compartilhamentos": ROXO,
}

MARGEM_L = 12 * mm
MARGEM_R = 12 * mm
MARGEM_T = 10 * mm
MARGEM_B = 14 * mm
LARG = landscape(A4)[0] - MARGEM_L - MARGEM_R  # 273 mm
ALT_UTIL = landscape(A4)[1] - MARGEM_T - MARGEM_B  # 186 mm

CLIENTE = "Centro de Eventos Padre Vítor Coelho de Almeida"
TITULO_APP = "DASHBOARD DE RESULTADOS | LINKEDIN"

# Caracteres aceitos no PDF. A Helvetica base 14 nao tem emojis nem travessão:
# sem este filtro eles viram quadrados pretos silenciosamente. Todo o ASCII
# imprimivel e os acentos Latin-1 passam; o resto e descartado.
_INVALIDOS = re.compile(r"[^\u0020-\u007E\u00A0-\u00FF\u2022\u00B7\u00D7\r\n\t]")
_PREFIXO_NUMERACAO = re.compile(r"^\s*\d+[.)]\s*")


def _limpa(texto) -> str:
    """Deixa o texto seguro para a Helvetica do reportlab (sem emoji, sem travessão)."""
    limpo = _INVALIDOS.sub("", str(texto if texto is not None else ""))
    return _PREFIXO_NUMERACAO.sub("", limpo).strip()


def _texto_html(texto) -> str:
    """Texto seguro para Paragraph: sem emoji e sem interpretar tags do XML."""
    return html.escape(_limpa(texto))


_PERCENTUAL_INGLES = re.compile(r"(\d)\.(\d{1,2})%")


def _pt_br(texto) -> str:
    """Troca o ponto decimal por virgula nos percentuais que vêm em inglês."""
    return _PERCENTUAL_INGLES.sub(r"\1,\2%", str(texto))


# ---------------------------------------------------------------------------
# Formatação de números (pt-BR)
# ---------------------------------------------------------------------------
def _number(value) -> str:
    """Inteiro com ponto de milhar."""
    try:
        return f"{int(round(float(value))):,}".replace(",", ".")
    except (TypeError, ValueError):
        return "n/d"


def _percent(value, casas: int = 2) -> str:
    """Percentual com vírgula decimal."""
    try:
        return f"{float(value):.{casas}f}%".replace(".", ",")
    except (TypeError, ValueError):
        return "n/d"


def _valor_bruto(value) -> str:
    """Normaliza um valor do comparativo (string com %, numpy, None) para pt-BR."""
    if value is None:
        return "n/d"
    texto = str(value).strip()
    if texto in ("", "nan", "None", "NaN"):
        return "n/d"
    if texto.endswith("%"):
        # percentual: o ponto e decimal, nao separador de milhar
        try:
            return _percent(float(texto[:-1].replace(",", ".")))
        except ValueError:
            return "n/d"
    try:
        return _number(texto.replace(".", ""))
    except (TypeError, ValueError):
        return _texto_html(texto)


def _numero_de(valor):
    """Extrai o número de um valor do comparativo (para calcular a variação)."""
    if valor is None:
        return None
    texto = str(valor).strip()
    if texto in ("", "nan", "None", "NaN", "n/d"):
        return None
    try:
        return float(valor)  # numpy int/float
    except (TypeError, ValueError):
        pass
    if texto.endswith("%"):
        try:
            return float(texto[:-1].replace(",", "."))
        except ValueError:
            return None
    try:
        return float(texto.replace(".", "").replace(",", "."))  # contador com milhar
    except ValueError:
        return None


def _date_label(value) -> str:
    if value is None:
        return "n/d"
    if hasattr(value, "strftime"):
        return value.strftime("%d/%m/%Y")
    try:
        return pd.to_datetime(value).strftime("%d/%m/%Y")
    except (ValueError, TypeError):
        return "n/d"


def _data_curta(value) -> str:
    if value is None:
        return ""
    if hasattr(value, "strftime"):
        return value.strftime("%d/%m")
    try:
        return pd.to_datetime(value).strftime("%d/%m")
    except (ValueError, TypeError):
        return ""


def _trunca(texto, limite: int = 92) -> str:
    """Corta no limite de palavra e marca com reticências."""
    limpo = _limpa(texto) or "Publicação sem texto"
    if len(limpo) <= limite:
        return limpo
    cortado = limpo[:limite]
    if " " in cortado:
        cortado = cortado[: cortado.rfind(" ")]
    return cortado.rstrip() + "..."


_BLOCO_EMOJI = re.compile(r"^\s*([\U0001F300-\U0001FAFF\u2600-\u27BF])")
_ICONE_POR_EMOJI = {
    "\U0001F465": "pessoas",     # grupo de pessoas
    "\U0001F3DF": "estrutura",   # estadio
    "\U0001F3C6": "trofeu",      # troféu
    "\U0001F3AF": "alvo",        # alvo
}
_ICONE_POR_PALAVRA = (
    ("impacto", "pessoas"),
    ("intera", "pessoas"),
    ("estrutura", "estrutura"),
    ("visibilidade", "estrutura"),
    ("reconhecimento", "trofeu"),
    ("autoridade", "trofeu"),
    ("oportunidade", "alvo"),
)
_ICONES_PADRAO = ("pessoas", "estrutura", "trofeu", "alvo")


def _icone_do_insight(emoji: str, titulo: str, indice: int) -> str:
    """Ícone do insight: pelo emoji original, pelo título ou pela posição."""
    if emoji and emoji in _ICONE_POR_EMOJI:
        return _ICONE_POR_EMOJI[emoji]
    texto = (titulo or "").lower()
    for palavra, icone in _ICONE_POR_PALAVRA:
        if palavra in texto:
            return icone
    return _ICONES_PADRAO[indice % len(_ICONES_PADRAO)]


def _blocos_insights(texto: str) -> list[tuple[str, str, str]]:
    """Agrupa o texto de insights em (título, detalhe, emoji do original)."""
    blocos = []
    for bruto in re.split(r"\n\s*\n", str(texto or "")):
        linhas = [linha.strip() for linha in bruto.splitlines() if linha.strip()]
        if not linhas:
            continue
        emoji = _BLOCO_EMOJI.match(linhas[0])
        emoji_texto = emoji.group(1) if emoji else ""
        titulo = _limpa(linhas[0])
        detalhe = " ".join(_limpa(linha) for linha in linhas[1:])
        blocos.append((titulo, detalhe, emoji_texto))
    return blocos


# ---------------------------------------------------------------------------
# Escala dos eixos
# ---------------------------------------------------------------------------
def _serie_numerica(valores) -> list[float]:
    """Converte uma série em float, ignorando valores não numéricos.

    Necessário porque a coluna de engajamento pode chegar como texto
    (dtype object) vinda da camada de cálculo do dashboard.
    """
    saida = []
    for valor in valores:
        try:
            numero = float(valor)
        except (TypeError, ValueError):
            numero = 0.0
        saida.append(numero if math.isfinite(numero) else 0.0)
    return saida


def _escala(maximo, marcas: int = 4):
    """Arredonda o topo do eixo para um valor 'redondo' e devolve as marcas."""
    if not maximo or maximo <= 0:
        return 1.0, [0.0, 0.25, 0.5, 0.75, 1.0]
    bruto = float(maximo) / marcas
    magnitude = 10 ** math.floor(math.log10(bruto))
    for fator in (1, 2, 2.5, 5, 10):
        passo = magnitude * fator
        if passo >= bruto:
            break
    topo = passo * marcas
    return topo, [passo * i for i in range(marcas + 1)]


# ---------------------------------------------------------------------------
# Flowables de apoio
# ---------------------------------------------------------------------------
class _EstadoVazio(Flowable):
    """Retângulo de estado vazio: preserva a altura do bloco que substitui."""

    def __init__(self, largura, altura, texto):
        super().__init__()
        self.width = largura
        self.height = altura
        self.texto = texto

    def wrap(self, availWidth, availHeight):
        return (self.width, self.height)

    def draw(self):
        c = self.canv
        c.saveState()
        c.setFillColor(FUNDO_FAIXA)
        c.setStrokeColor(BORDA)
        c.setLineWidth(0.5)
        c.setDash(1, 2)
        c.rect(0, 0, self.width, self.height, stroke=1, fill=1)
        c.setDash()
        c.setFillColor(SUAVE)
        c.setFont("Helvetica", 8)
        c.drawCentredString(self.width / 2, self.height / 2 - 3, self.texto)
        c.restoreState()


class _Marcador(Flowable):
    """Quadradinho vetorial que substitui o emoji do insight."""

    def __init__(self, tamanho=2.5 * mm, cor=AZUL_INSTITUCIONAL):
        super().__init__()
        self.width = tamanho
        self.height = tamanho
        self.cor = cor

    def wrap(self, availWidth, availHeight):
        return (self.width, self.height)

    def draw(self):
        c = self.canv
        c.saveState()
        c.setFillColor(self.cor)
        c.rect(0, 0, self.width, self.height, stroke=0, fill=1)
        c.restoreState()


class _TituloSecao(Flowable):
    """Título de seção com filete fino na largura do bloco."""

    def __init__(self, texto, largura):
        super().__init__()
        self.texto = _limpa(texto)
        self.width = largura
        self.height = 6 * mm

    def wrap(self, availWidth, availHeight):
        return (self.width, self.height)

    def draw(self):
        c = self.canv
        c.saveState()
        c.setFillColor(AZUL_INSTITUCIONAL)
        c.setFont("Helvetica-Bold", 10)
        c.drawString(0, self.height - 4 * mm, self.texto)
        c.setStrokeColor(GRADE)
        c.setLineWidth(0.5)
        c.line(0, 0.6 * mm, self.width, 0.6 * mm)
        c.restoreState()


# ---------------------------------------------------------------------------
# Gráficos vetoriais
# ---------------------------------------------------------------------------
_MESES_PT = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]


def _agrupa_por_mes(df_periodo) -> list[tuple[str, float]]:
    """Agrega as impressões por mês: [(rótulo, valor), ...] em ordem cronológica."""
    if df_periodo is None or df_periodo.empty or "impressoes" not in df_periodo.columns:
        return []
    grupos: dict[tuple[int, int], float] = {}
    for _, linha in df_periodo.iterrows():
        try:
            marca = pd.to_datetime(linha.get("data"))
        except (ValueError, TypeError):
            continue
        if pd.isna(marca):
            continue
        try:
            valor = float(linha.get("impressoes", 0) or 0)
        except (TypeError, ValueError):
            valor = 0.0
        chave = (marca.year, marca.month)
        grupos[chave] = grupos.get(chave, 0.0) + valor
    return [
        (f"{_MESES_PT[mes - 1]}/{str(ano)[2:]}", grupos[(ano, mes)])
        for ano, mes in sorted(grupos)
    ]


class _Icone(Flowable):
    """Ícone vetorial do insight.

    O emoji original (👥 🏟️ 🏆 🎯) não existe na Helvetica do reportlab e
    sairia como quadrado preto; aqui o ícone é desenhado em vetor, na cor
    da marca, e continua nítido na impressão.
    """

    def __init__(self, tipo="pessoas", tamanho=None):
        super().__init__()
        self.tipo = tipo
        self.width = tamanho or 6 * mm
        self.height = self.width

    def wrap(self, availWidth, availHeight):
        return (self.width, self.height)

    def draw(self):
        c = self.canv
        s = self.width
        c.saveState()
        c.setFillColor(AZUL_INSTITUCIONAL)
        c.setStrokeColor(AZUL_INSTITUCIONAL)
        c.setLineWidth(s * 0.09)
        c.setLineCap(1)
        if self.tipo == "pessoas":
            self._pessoas(c, s)
        elif self.tipo == "estrutura":
            self._estrutura(c, s)
        elif self.tipo == "trofeu":
            self._trofeu(c, s)
        elif self.tipo == "alvo":
            self._alvo(c, s)
        else:
            c.rect(0, 0, s * 0.42, s * 0.42, stroke=0, fill=1)
        c.restoreState()

    def _pessoas(self, c, s):
        for x in (0.34, 0.70):
            c.circle(x * s, 0.70 * s, 0.13 * s, stroke=0, fill=1)
            c.wedge(
                (x - 0.21) * s, 0.22 * s, (x + 0.21) * s, 0.64 * s,
                0, 180, stroke=0, fill=1,
            )

    def _estrutura(self, c, s):
        c.rect(0.12 * s, 0.24 * s, 0.16 * s, 0.38 * s, stroke=0, fill=1)
        c.rect(0.36 * s, 0.24 * s, 0.16 * s, 0.62 * s, stroke=0, fill=1)
        c.rect(0.60 * s, 0.24 * s, 0.16 * s, 0.48 * s, stroke=0, fill=1)
        c.setLineWidth(s * 0.09)
        c.line(0.08 * s, 0.20 * s, 0.80 * s, 0.20 * s)

    def _trofeu(self, c, s):
        caminho = c.beginPath()
        caminho.moveTo(0.26 * s, 0.80 * s)
        caminho.lineTo(0.36 * s, 0.44 * s)
        caminho.lineTo(0.64 * s, 0.44 * s)
        caminho.lineTo(0.74 * s, 0.80 * s)
        caminho.close()
        c.drawPath(caminho, stroke=0, fill=1)
        c.setLineWidth(s * 0.08)
        c.line(0.50 * s, 0.44 * s, 0.50 * s, 0.20 * s)
        c.rect(0.30 * s, 0.08 * s, 0.40 * s, 0.11 * s, stroke=0, fill=1)

    def _alvo(self, c, s):
        c.circle(0.48 * s, 0.56 * s, 0.36 * s, stroke=1, fill=0)
        c.circle(0.48 * s, 0.56 * s, 0.20 * s, stroke=0, fill=1)
        c.setFillColor(colors.white)
        c.circle(0.48 * s, 0.56 * s, 0.08 * s, stroke=0, fill=1)
        c.setStrokeColor(AZUL_INSTITUCIONAL)
        c.setLineWidth(s * 0.09)
        c.line(0.16 * s, 0.16 * s, 0.66 * s, 0.66 * s)


class _GraficoBarrasMensais(Flowable):
    """Impressões agregadas por mês: leitura de tendência em 12 colunas.

    No relatório impresso a série diária (366 pontos) fica ilegível; a
    agregação mensal mostra a tendência sem poluir o papel.
    """

    def __init__(self, grupos, largura, altura):
        super().__init__()
        self.grupos = list(grupos)  # [(rótulo, valor), ...]
        self.width = largura
        self.height = altura

    def wrap(self, availWidth, availHeight):
        return (self.width, self.height)

    def draw(self):
        c = self.canv
        esq = 15 * mm
        dir_ = 4 * mm
        base = 11 * mm
        topo = 6 * mm
        px0, py0 = esq, base
        pw = self.width - esq - dir_
        ph = self.height - base - topo

        c.saveState()
        c.setFillColor(colors.white)
        c.rect(0, 0, self.width, self.height, stroke=0, fill=1)

        if not self.grupos:
            c.setFillColor(SUAVE)
            c.setFont("Helvetica", 8)
            c.drawCentredString(self.width / 2, self.height / 2, "Sem dados no período")
            c.restoreState()
            return

        topo_valor, marcas = _escala(max(v for _, v in self.grupos))
        n = len(self.grupos)
        passo = pw / n
        largura_barra = passo * 0.56

        # grade + eixo Y
        c.setLineWidth(0.4)
        for valor in marcas:
            y = py0 + (ph * (valor / topo_valor if topo_valor else 0))
            c.setStrokeColor(GRADE)
            c.line(px0, y, px0 + pw, y)
            c.setFillColor(SUAVE)
            c.setFont("Helvetica", 6.5)
            c.drawRightString(px0 - 2 * mm, y - 2, _number(valor))

        c.setStrokeColor(BORDA)
        c.setLineWidth(0.5)
        c.line(px0, py0, px0 + pw, py0)

        maior = max(v for _, v in self.grupos)
        for indice, (rotulo, valor) in enumerate(self.grupos):
            x = px0 + (passo * indice) + ((passo - largura_barra) / 2)
            h = ph * (valor / topo_valor if topo_valor else 0)
            # o mês de pico ganha o tom institucional: hierarquia sem inventar cor
            c.setFillColor(AZUL_INSTITUCIONAL if valor == maior else AZUL)
            c.rect(x, py0, largura_barra, h, stroke=0, fill=1)
            # rótulo do mês
            c.setFillColor(SUAVE)
            c.setFont("Helvetica", 6.5)
            c.drawCentredString(x + (largura_barra / 2), py0 - 5 * mm, rotulo)
            # valor em destaque: o maior mês e o último mês
            if valor == maior or indice == n - 1:
                c.setFillColor(AZUL_INSTITUCIONAL)
                c.setFont("Helvetica-Bold", 6.5)
                c.drawCentredString(x + (largura_barra / 2), py0 + h + 1.5 * mm, _number(valor))

        c.restoreState()


class _GraficoBarrasTop(Flowable):
    """Engajamento das 5 melhores publicações: barras horizontais."""

    def __init__(self, itens, largura, altura):
        super().__init__()
        self.itens = list(itens)  # lista de (rotulo, valor)
        self.width = largura
        self.height = altura

    def wrap(self, availWidth, availHeight):
        return (self.width, self.height)

    def draw(self):
        c = self.canv
        esq = 95 * mm
        dir_ = 22 * mm
        py0 = 6 * mm
        ph = self.height - py0 - 4 * mm

        c.saveState()
        c.setFillColor(colors.white)
        c.rect(0, 0, self.width, self.height, stroke=0, fill=1)

        if not self.itens:
            c.setFillColor(SUAVE)
            c.setFont("Helvetica", 8)
            c.drawCentredString(self.width / 2, self.height / 2, "Sem publicações no período")
            c.restoreState()
            return

        maior = max(v for _, v in self.itens) or 1
        altura_linha = ph / len(self.itens)
        altura_barra = altura_linha * 0.52

        for indice, (rotulo, valor) in enumerate(self.itens):
            y = py0 + (altura_linha * (len(self.itens) - 1 - indice))
            # rótulo do post
            c.setFillColor(TEXTO)
            c.setFont("Helvetica", 7.5)
            c.drawRightString(esq - 4 * mm, y + (altura_barra / 2) - 2, rotulo)
            # barra
            largura = (self.width - esq - dir_) * (valor / maior)
            c.setFillColor(VERDE)
            c.rect(esq, y, max(largura, 0.6 * mm), altura_barra, stroke=0, fill=1)
            # valor
            c.setFillColor(AZUL_INSTITUCIONAL)
            c.setFont("Helvetica-Bold", 8)
            c.drawString(esq + max(largura, 0.6 * mm) + 3 * mm, y + (altura_barra / 2) - 2.5,
                         _percent(valor))

        c.restoreState()


class _Donut(Flowable):
    """Mix de interações: donut com furo, total no centro e legenda com números."""

    def __init__(self, itens, largura, altura):
        super().__init__()
        self.itens = list(itens)  # lista de (tipo, quantidade, percentual)
        self.width = largura
        self.height = altura

    def wrap(self, availWidth, availHeight):
        return (self.width, self.height)

    def draw(self):
        c = self.canv
        c.saveState()
        c.setFillColor(colors.white)
        c.rect(0, 0, self.width, self.height, stroke=0, fill=1)

        total = sum(float(q) for _, q, _ in self.itens)
        if not self.itens or total <= 0:
            c.setFillColor(SUAVE)
            c.setFont("Helvetica", 8)
            c.drawCentredString(self.width / 2, self.height / 2, "Sem interações")
            c.restoreState()
            return

        # o donut ocupa a parte de cima do bloco; a legenda fica abaixo
        raio = min(25 * mm, (self.width - 8 * mm) / 2)
        cx = self.width / 2
        cy = self.height - raio - 2 * mm

        # fatias: início às 12h, sentido horário
        angulo = 90.0
        for tipo, quantidade, _ in self.itens:
            valor = float(quantidade)
            if valor <= 0:
                continue
            extensao = 360.0 * (valor / total)
            c.setFillColor(CORES_MIX.get(tipo, AZUL))
            c.setStrokeColor(colors.white)
            c.setLineWidth(0.6)
            c.wedge(
                cx - raio, cy - raio, cx + raio, cy + raio,
                angulo - extensao, extensao, stroke=1, fill=1,
            )
            angulo -= extensao

        # furo
        c.setFillColor(colors.white)
        c.circle(cx, cy, raio * 0.6, stroke=0, fill=1)

        # total no centro
        c.setFillColor(AZUL_INSTITUCIONAL)
        c.setFont("Helvetica-Bold", 11)
        c.drawCentredString(cx, cy + 0.5 * mm, _number(total))
        c.setFillColor(SUAVE)
        c.setFont("Helvetica", 6.5)
        c.drawCentredString(cx, cy - 4 * mm, "Interações totais")

        # legenda empilhada abaixo
        ly = cy - raio - 6 * mm
        for tipo, quantidade, percentual in self.itens:
            c.setFillColor(CORES_MIX.get(tipo, AZUL))
            c.rect(2 * mm, ly - 1 * mm, 3 * mm, 3 * mm, stroke=0, fill=1)
            c.setFillColor(TEXTO)
            c.setFont("Helvetica", 7)
            c.drawString(7 * mm, ly, _limpa(tipo))
            c.setFillColor(SUAVE)
            c.setFont("Helvetica", 6.5)
            c.drawRightString(
                self.width - 2 * mm, ly,
                f"{_number(quantidade)} ({_percent(percentual, 1)})",
            )
            ly -= 5.5 * mm

        c.restoreState()


# ---------------------------------------------------------------------------
# Rodapé com numeração de página
# ---------------------------------------------------------------------------
class _CanvasNumerado(pdf_canvas.Canvas):
    """Canvas que desenha o rodapé em todas as páginas, com total real."""

    def __init__(self, *args, rodape=None, **kwargs):
        pdf_canvas.Canvas.__init__(self, *args, **kwargs)
        self._estados = []
        self._rodape = rodape or {}

    def showPage(self):
        self._estados.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        total = len(self._estados)
        for estado in self._estados:
            self.__dict__.update(estado)
            self._desenha_rodape(total)
            pdf_canvas.Canvas.showPage(self)
        pdf_canvas.Canvas.save(self)

    def _desenha_rodape(self, total):
        c = self
        c.saveState()
        largura, _ = c._pagesize
        y = 8 * mm
        c.setStrokeColor(GRADE)
        c.setLineWidth(0.4)
        c.line(MARGEM_L, y + 4 * mm, largura - MARGEM_R, y + 4 * mm)
        c.setFont("Helvetica", 6.5)
        c.setFillColor(SUAVE)
        c.drawString(MARGEM_L, y, self._rodape.get("esquerda", ""))
        c.drawCentredString(largura / 2, y, self._rodape.get("centro", ""))
        c.drawRightString(
            largura - MARGEM_R, y,
            f"{self._rodape.get('direita', '')}  |  Página {c._pageNumber} de {total}",
        )
        c.restoreState()


# ---------------------------------------------------------------------------
# Blocos de tabela
# ---------------------------------------------------------------------------
def _estilo(pares):
    return ParagraphStyle("p", fontName="Helvetica", fontSize=8, leading=10, textColor=TEXTO)


def _faixa_kpis(kpis: dict):
    """Faixa de 8 KPIs: rótulo, valor e sublegenda, como na tela."""
    estilo_rotulo = ParagraphStyle(
        "kpi_rot", fontName="Helvetica-Bold", fontSize=6.2, leading=7.5,
        textColor=ROTULO, alignment=TA_CENTER,
    )
    estilo_valor = ParagraphStyle(
        "kpi_val", fontName="Helvetica-Bold", fontSize=13, leading=15,
        textColor=AZUL_INSTITUCIONAL, alignment=TA_CENTER,
    )
    estilo_sub = ParagraphStyle(
        "kpi_sub", fontName="Helvetica", fontSize=6, leading=7,
        textColor=SUAVE, alignment=TA_CENTER,
    )

    patrocinadas = int(kpis.get("impressoes_patrocinadas", 0) or 0)
    dados = [
        ("Impressões", _number(kpis.get("impressoes", 0)), "Total de impressões no período"),
        ("Impressões únicas", _number(kpis.get("impressoes_unicas", 0)), "Pessoas alcançadas (contas únicas)"),
        ("Cliques", _number(kpis.get("cliques", 0)), "Total de cliques nas publicações"),
        ("Reações", _number(kpis.get("reacoes", 0)), "Total de reações nas publicações"),
        ("Publicações", _number(kpis.get("publicacoes", 0)), "Publicações realizadas"),
        ("Engajamento médio", _percent(kpis.get("engajamento_medio", 0)), "Média do engajamento das publicações"),
        ("CTR médio", _percent(kpis.get("ctr_medio", 0)), "Média do CTR das publicações"),
        ("Impressões patrocinadas", _number(patrocinadas),
         "Inclui campanhas pagas" if patrocinadas else "Todo o desempenho foi orgânico"),
    ]

    larguras = [LARG / 8] * 8
    linhas = [
        [Paragraph(_limpa(rotulo).upper(), estilo_rotulo) for rotulo, _, _ in dados],
        [Paragraph(valor, estilo_valor) for _, valor, _ in dados],
        [Paragraph(_limpa(sub), estilo_sub) for _, _, sub in dados],
    ]
    tabela = Table(linhas, colWidths=larguras)
    tabela.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.white),
        ("BOX", (0, 0), (-1, -1), 0.5, BORDA),
        ("LINEAFTER", (0, 0), (-1, -2), 0.35, GRADE),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, 0), 2),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 1),
        ("TOPPADDING", (0, 1), (-1, 1), 1),
        ("BOTTOMPADDING", (0, 1), (-1, 1), 1),
        ("TOPPADDING", (0, 2), (-1, 2), 1),
        ("BOTTOMPADDING", (0, 2), (-1, 2), 3),
    ]))
    return tabela


def _banner_ctr(kpis: dict):
    """Faixa de métricas do período com o CTR geral (mesma frase da tela)."""
    estilo = ParagraphStyle(
        "banner", fontName="Helvetica", fontSize=7.5, leading=9.5, textColor=TEXTO,
        alignment=TA_CENTER,
    )
    impressoes = int(kpis.get("impressoes", 0) or 0)
    cliques = int(kpis.get("cliques", 0) or 0)
    ctr = kpis.get("ctr_geral")
    if impressoes > 0:
        if ctr is None:
            ctr = cliques / impressoes * 100
        ctr_txt = f"CTR GERAL DO PERÍODO: {_percent(ctr)}"
        conta = f"({_number(cliques)} cliques / {_number(impressoes)} impressões)"
    else:
        ctr_txt = "CTR GERAL DO PERÍODO: n/d"
        conta = "(sem atividade no período)"
    texto = (
        f"<b>MÉTRICAS DO PERÍODO</b> &nbsp;|&nbsp; <b>{ctr_txt}</b> &nbsp; {conta}"
    )
    tabela = Table([[Paragraph(texto, estilo)]], colWidths=[LARG])
    tabela.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), FUNDO_BANNER),
        ("BOX", (0, 0), (-1, -1), 0.5, BORDA),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    return tabela


def _tabela_top5(df_top: pd.DataFrame):
    """Top 5 com links clicáveis, no mesmo formato da tela."""
    estilo_cab = ParagraphStyle(
        "cab", fontName="Helvetica-Bold", fontSize=7.5, leading=9, textColor=TEXTO,
    )
    estilo_cab_dir = ParagraphStyle("cab_dir", parent=estilo_cab, alignment=TA_RIGHT)
    estilo_data = ParagraphStyle("d", fontName="Helvetica", fontSize=8, leading=9.5, textColor=TEXTO)
    estilo_num = ParagraphStyle("n", parent=estilo_data, alignment=TA_RIGHT)
    estilo_num_bold = ParagraphStyle(
        "nb", parent=estilo_num, fontName="Helvetica-Bold",
    )
    estilo_eng = ParagraphStyle(
        "eng", parent=estilo_num, fontName="Helvetica-Bold", textColor=VERDE,
    )
    estilo_resumo = ParagraphStyle(
        "res", fontName="Helvetica", fontSize=7.5, leading=9, textColor=TEXTO,
    )

    linhas = [[
        Paragraph("<b>Data</b>", estilo_cab),
        Paragraph("<b>Resumo da publicação</b>", estilo_cab),
        Paragraph("<b>Impressões</b>", estilo_cab_dir),
        Paragraph("<b>Cliques</b>", estilo_cab_dir),
        Paragraph("<b>Reações</b>", estilo_cab_dir),
        Paragraph("<b>Engajamento</b>", estilo_cab_dir),
    ]]

    if df_top is None or df_top.empty:
        linhas.append([
            Paragraph("Nenhuma publicação no período selecionado", estilo_data),
            Paragraph("", estilo_data), Paragraph("", estilo_data),
            Paragraph("", estilo_data), Paragraph("", estilo_data),
        ])
    else:
        for _, row in df_top.head(5).iterrows():
            resumo = _trunca(row.get("resumo", ""), 92)
            link = row.get("link", "")
            tem_link = bool(link) and pd.notna(link)
            if tem_link:
                resumo_html = (
                    f'<link href="{_limpa(str(link))}">'
                    f'<font color="#1f77b4"><u>{resumo}</u></font></link>'
                )
            else:
                resumo_html = resumo
            linhas.append([
                Paragraph(_date_label(row.get("data")), estilo_data),
                Paragraph(resumo_html, estilo_resumo),
                Paragraph(_number(row.get("impressoes", 0)), estilo_num_bold),
                Paragraph(_number(row.get("cliques", 0)), estilo_num),
                Paragraph(_number(row.get("reacoes", 0)), estilo_num),
                Paragraph(_percent(row.get("engajamento_pct", 0)), estilo_eng),
            ])

    larguras = [22 * mm, 141 * mm, 28 * mm, 24 * mm, 24 * mm, 34 * mm]
    tabela = Table(linhas, colWidths=larguras, repeatRows=1)
    tabela.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), FUNDO_TABELA),
        ("GRID", (0, 0), (-1, -1), 0.35, BORDA),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    return tabela


def _tabela_comparativo(comparativo: pd.DataFrame):
    """Comparativo mensal com coluna de variação."""
    estilo_cab = ParagraphStyle(
        "cab", fontName="Helvetica-Bold", fontSize=7.5, leading=9, textColor=TEXTO,
    )
    estilo_cab_dir = ParagraphStyle("cab_dir", parent=estilo_cab, alignment=TA_RIGHT)
    estilo_ind = ParagraphStyle("i", fontName="Helvetica", fontSize=8, leading=10, textColor=TEXTO)
    estilo_dir = ParagraphStyle("dir", parent=estilo_ind, alignment=TA_RIGHT)
    estilo_dir_bold = ParagraphStyle(
        "dirb", parent=estilo_dir, fontName="Helvetica-Bold",
    )
    estilo_var = ParagraphStyle(
        "var", parent=estilo_dir, fontName="Helvetica-Bold", textColor=AZUL_INSTITUCIONAL,
    )

    linhas = [[
        Paragraph("<b>Indicador</b>", estilo_cab),
        Paragraph("<b>Mês anterior</b>", estilo_cab_dir),
        Paragraph("<b>Mês atual</b>", estilo_cab_dir),
        Paragraph("<b>Variação</b>", estilo_cab_dir),
    ]]

    if comparativo is None or comparativo.empty:
        linhas.append([
            Paragraph("Sem comparativo disponível", estilo_ind),
            Paragraph("", estilo_ind), Paragraph("", estilo_ind), Paragraph("", estilo_ind),
        ])
    else:
        for _, row in comparativo.iterrows():
            anterior = row.get("mes_anterior")
            atual = row.get("mes_atual")
            num_anterior = _numero_de(anterior)
            num_atual = _numero_de(atual)
            if num_anterior and num_atual is not None and num_anterior != 0:
                variacao = (num_atual - num_anterior) / abs(num_anterior) * 100
                sinal = "+" if variacao >= 0 else "-"
                texto_variacao = f"{sinal}{abs(variacao):.1f}%".replace(".", ",")
            else:
                texto_variacao = "n/d"
            linhas.append([
                Paragraph(_limpa(row.get("indicador", "")), estilo_ind),
                Paragraph(_valor_bruto(anterior), estilo_dir),
                Paragraph(_valor_bruto(atual), estilo_dir_bold),
                Paragraph(texto_variacao, estilo_var),
            ])

    larguras = [89 * mm, 61 * mm, 61 * mm, 62 * mm]
    tabela = Table(linhas, colWidths=larguras, repeatRows=1)
    tabela.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), FUNDO_TABELA),
        ("GRID", (0, 0), (-1, -1), 0.35, BORDA),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    return tabela


def _faixa_formulas():
    """Faixa com as fórmulas dos indicadores (credibilidade para o leitor)."""
    estilo_rot = ParagraphStyle(
        "frot", fontName="Helvetica-Bold", fontSize=6, leading=7.5, textColor=SUAVE,
    )
    estilo_txt = ParagraphStyle(
        "ftxt", fontName="Helvetica", fontSize=7, leading=9, textColor=TEXTO,
    )
    itens = [
        ("Engajamento (%)",
         "(Reações + Comentários + Compartilhamentos + Cliques) / Impressões x 100"),
        ("CTR (%)", "Cliques / Impressões x 100"),
        ("CTR geral do período", "soma(Cliques) / soma(Impressões) x 100"),
    ]
    celulas = [
        [Paragraph(rotulo.upper(), estilo_rot), Paragraph(_texto_html(texto), estilo_txt)]
        for rotulo, texto in itens
    ]
    tabela = Table([celulas], colWidths=[LARG / 3] * 3)
    tabela.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), FUNDO_FAIXA),
        ("LINEAFTER", (0, 0), (-2, -1), 0.4, GRADE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return tabela


def _grid_insights(insights: list[dict]):
    """Insights em coluna única, com ícone vetorial e respiro entre os itens."""
    estilo_tit = ParagraphStyle(
        "it", fontName="Helvetica-Bold", fontSize=9.5, leading=12, textColor=AZUL_INSTITUCIONAL,
    )
    estilo_txt = ParagraphStyle(
        "ix", fontName="Helvetica", fontSize=8.5, leading=11.5, textColor=TEXTO,
    )

    celulas = []
    for item in insights[:4]:
        titulo = _limpa(item.get("titulo", ""))
        texto = _limpa(item.get("texto", ""))
        corpo = f"<b>{titulo}</b>"
        if texto:
            corpo += f"<br/>{texto}"
        celulas.append([
            _Icone(item.get("icone", ""), tamanho=7 * mm),
            Paragraph(corpo, estilo_tit),
        ])

    # celulas vazias precisam ser Paragraph: string crua quebra o reportlab
    vazia = Paragraph("", estilo_tit)
    while len(celulas) < 4:
        celulas.append([vazia, vazia])

    tabela = Table(celulas, colWidths=[9 * mm, LARG - 9 * mm])
    tabela.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    return tabela


# ---------------------------------------------------------------------------
# Geração
# ---------------------------------------------------------------------------
def _criterio_top5(df_top: pd.DataFrame) -> str:
    """Descobre pelo próprio df_top qual critério de ordenação foi usado."""
    if df_top is None or len(df_top) < 2:
        return "por impressões"
    if "impressoes" in df_top.columns and df_top["impressoes"].is_monotonic_decreasing:
        return "por impressões"
    if "engajamento_pct" in df_top.columns and df_top["engajamento_pct"].is_monotonic_decreasing:
        return "por engajamento"
    return "por impressões"


def gerar_pdf_dashboard(
    data_inicio,
    data_fim,
    kpis: dict,
    df_periodo: pd.DataFrame | None = None,
    df_top: pd.DataFrame | None = None,
    df_mix: pd.DataFrame | None = None,
    comparativo: pd.DataFrame | None = None,
    texto_insights: str = "",
    insights: list[dict] | None = None,
    fonte_dados: str = "",
    data_geracao: dt.datetime | None = None,
) -> bytes:
    """Gera o relatório PDF executivo (3 páginas A4 paisagem)."""
    output = BytesIO()
    doc = SimpleDocTemplate(
        output,
        pagesize=landscape(A4),
        leftMargin=MARGEM_L,
        rightMargin=MARGEM_R,
        topMargin=MARGEM_T,
        bottomMargin=MARGEM_B,
        title="Dashboard de Resultados LinkedIn",
        author=CLIENTE,
        subject=f"Período: {_date_label(data_inicio)} a {_date_label(data_fim)}",
        keywords=CLIENTE,
    )

    kpis = kpis or {}
    df_periodo = df_periodo if df_periodo is not None else pd.DataFrame()
    df_top = df_top if df_top is not None else pd.DataFrame()
    df_mix = df_mix if df_mix is not None else pd.DataFrame()
    comparativo = comparativo if comparativo is not None else pd.DataFrame()

    if insights is None:
        insights = []
        for indice, (titulo, texto, emoji) in enumerate(_blocos_insights(texto_insights)):
            insights.append({
                "titulo": titulo,
                "texto": texto,
                "icone": _icone_do_insight(emoji, titulo, indice),
            })
    insights = [
        {
            "titulo": _pt_br(item.get("titulo", "")),
            "texto": _pt_br(item.get("texto", "")),
            "icone": item.get("icone", ""),
        }
        for item in insights
    ]

    gerado = data_geracao or dt.datetime.now()
    fonte = _limpa(fonte_dados) or "API do LinkedIn"

    # ----- dados dos gráficos -----
    datas = [_data_curta(d) for d in df_periodo.get("data", [])] if not df_periodo.empty else []
    impressoes = _serie_numerica(df_periodo.get("impressoes", [])) if not df_periodo.empty else []
    engajamento = _serie_numerica(df_periodo.get("engajamento_pct", [])) if not df_periodo.empty else []
    if len(datas) != len(impressoes):
        datas, impressoes = datas[: len(impressoes)], impressoes[: len(datas)]

    itens_mix = []
    if not df_mix.empty:
        for _, row in df_mix.iterrows():
            itens_mix.append((
                _limpa(row.get("tipo", "")),
                float(row.get("quantidade", 0) or 0),
                float(row.get("percentual", 0) or 0),
            ))

    grupos_mes = _agrupa_por_mes(df_periodo)

    story = []

    # ================= PÁGINA 1: RESUMO =================
    estilo_titulo = ParagraphStyle(
        "tit", fontName="Helvetica-Bold", fontSize=15, leading=18, textColor=colors.white,
    )
    estilo_sub = ParagraphStyle(
        "sub", fontName="Helvetica", fontSize=8, leading=10, textColor=CINZA_CLARO,
    )
    estilo_periodo = ParagraphStyle(
        "per", fontName="Helvetica-Bold", fontSize=8.5, leading=11, textColor=colors.white,
        alignment=TA_RIGHT,
    )
    estilo_fonte = ParagraphStyle(
        "fon", fontName="Helvetica", fontSize=7, leading=9, textColor=CINZA_CLARO,
        alignment=TA_RIGHT,
    )
    cabecalho = Table([[
        Paragraph(TITULO_APP, estilo_titulo),
        Paragraph(f"Período: {_date_label(data_inicio)} a {_date_label(data_fim)}", estilo_periodo),
    ], [
        Paragraph(CLIENTE, estilo_sub),
        Paragraph(f"Fonte: {fonte}", estilo_fonte),
    ]], colWidths=[LARG * 0.68, LARG * 0.32])
    cabecalho.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), AZUL_INSTITUCIONAL),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, 0), 5),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 1),
        ("TOPPADDING", (0, 1), (-1, 1), 1),
        ("BOTTOMPADDING", (0, 1), (-1, 1), 5),
    ]))
    story.extend([cabecalho, Spacer(1, 3 * mm)])
    story.append(_faixa_kpis(kpis))
    story.append(Spacer(1, 3 * mm))
    story.append(_banner_ctr(kpis))
    story.append(Spacer(1, 3 * mm))

    # Dois gráficos na página 1: série mensal em barras e o mix em donut.
    # A série diária do dashboard (366 pontos) não cabe legível no papel.
    altura_grafico = 108 * mm
    largura_barras = 168 * mm
    largura_donut = 101 * mm
    grafico_barras = _GraficoBarrasMensais(grupos_mes, largura_barras, altura_grafico)
    donut = _Donut(itens_mix, largura_donut, altura_grafico)
    bloco_graficos = Table(
        [[grafico_barras, donut]],
        colWidths=[largura_barras, largura_donut],
    )
    bloco_graficos.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 2),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    story.append(bloco_graficos)
    story.append(Spacer(1, 2.5 * mm))

    # legendas: uma linha por gráfico, com o dado em destaque
    estilo_legenda = ParagraphStyle(
        "leg", fontName="Helvetica", fontSize=7, leading=9, textColor=ROTULO,
    )
    pico = ""
    if grupos_mes:
        rotulo_pico, valor_pico = max(grupos_mes, key=lambda item: item[1])
        pico = (
            f"Impressões por mês: o melhor mês foi {rotulo_pico}, "
            f"com {_number(valor_pico)} impressões."
        )
    total_interacoes = sum(q for _, q, _ in itens_mix)
    legenda_donut = (
        f"Mix de interações: {_number(total_interacoes)} interações no período, "
        "repartidas entre cliques, reações, comentários e compartilhamentos."
    )
    for texto in (pico or "Sem atividade no período selecionado.", legenda_donut):
        story.append(Paragraph(_texto_html(texto), estilo_legenda))

    # ================= PÁGINA 2: CONTEÚDO =================
    story.append(PageBreak())

    estilo_apoio = ParagraphStyle(
        "apoio", fontName="Helvetica", fontSize=7, leading=9, textColor=SUAVE,
    )

    story.append(_TituloSecao("Top 5 publicações do período", LARG))
    story.append(Spacer(1, 1.5 * mm))
    story.append(Paragraph(
        f"Top 5 {_criterio_top5(df_top)}. Os títulos são links para a publicação original no LinkedIn.",
        estilo_apoio,
    ))
    story.append(Spacer(1, 3 * mm))
    story.append(_tabela_top5(df_top))
    story.append(Spacer(1, 1.5 * mm))
    story.append(Paragraph(
        "Engajamento (%) = (Reações + Comentários + Compartilhamentos + Cliques) / Impressões x 100",
        estilo_apoio,
    ))
    story.append(Spacer(1, 5 * mm))

    # engajamento das publicações em barras horizontais: leitura gerencial direta
    itens_eng = []
    if not df_top.empty and "engajamento_pct" in df_top.columns:
        for _, linha in df_top.head(5).sort_values("engajamento_pct", ascending=False).iterrows():
            itens_eng.append((
                _trunca(linha.get("resumo", ""), 44),
                float(linha.get("engajamento_pct", 0) or 0),
            ))
    if itens_eng:
        story.append(_TituloSecao("Engajamento das publicações", LARG))
        story.append(Spacer(1, 2 * mm))
        story.append(_GraficoBarrasTop(itens_eng, LARG, 28 * mm))
        story.append(Spacer(1, 3.5 * mm))

    story.append(_TituloSecao("Comparativo mensal", LARG))
    story.append(Spacer(1, 2 * mm))
    story.append(_tabela_comparativo(comparativo))

    # ================= PÁGINA 3: LEITURA DO PERÍODO =================
    story.append(PageBreak())
    story.append(_TituloSecao("Leitura do período", LARG))
    story.append(Spacer(1, 4 * mm))
    if insights:
        story.append(_grid_insights(insights))
    else:
        story.append(_EstadoVazio(
            LARG, 30 * mm,
            "Sem dados suficientes para gerar insights automáticos no período selecionado.",
        ))
    story.append(Spacer(1, 10 * mm))
    story.append(_faixa_formulas())

    rodape = {
        "esquerda": CLIENTE,
        "centro": f"Período: {_date_label(data_inicio)} a {_date_label(data_fim)}",
        "direita": f"Fonte: {fonte} | Gerado em {gerado.strftime('%d/%m/%Y %H:%M')}",
    }

    doc.build(story, canvasmaker=lambda *a, **k: _CanvasNumerado(*a, rodape=rodape, **k))
    return output.getvalue()
