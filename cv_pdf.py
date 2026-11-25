# -*- coding: utf-8 -*-
"""Layout do PDF: mesmo padrao do gerar_curriculo.py, com titulos em portugues.

Diferencas em relacao ao script original, todas para aguentar dados digitados por alunos:
- API do fpdf2 2.8 (new_x/new_y no lugar de ln=True).
- Linhas "texto a esquerda / texto a direita" quebram linha se o texto nao couber,
  em vez de sobrepor a coluna vizinha. Com textos de tamanho normal o resultado e identico.
- Blocos opcionais vazios (ex.: "Contexto:") nao sao impressos.
- Linhas de duas colunas medem a altura antes de desenhar e vao inteiras para a proxima
  pagina se nao couberem (evita que cada coluna caia numa pagina diferente).
"""
from pathlib import Path

from fpdf import FPDF
from fpdf.enums import MethodReturnValue, XPos, YPos

FONTS_DIR = Path(__file__).parent / "fonts"
NEXT_LINE = {"new_x": XPos.LMARGIN, "new_y": YPos.NEXT}


class ResumePDF(FPDF):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.set_auto_page_break(auto=True, margin=15)
        self.set_margins(20, 10, 20)
        self.add_font("DejaVu", "", str(FONTS_DIR / "DejaVuSans.ttf"))
        self.add_font("DejaVu", "B", str(FONTS_DIR / "DejaVuSans-Bold.ttf"))

    def count_lines(self, w, text, style, size):
        self.set_font("DejaVu", style, size)
        return max(len(self.multi_cell(w, 1, text, dry_run=True, output=MethodReturnValue.LINES)), 1)

    def ensure_space(self, h):
        if self.get_y() + h > self.page_break_trigger:
            self.add_page()

    def pair_row(self, h, left, left_style, left_size, right, right_style, right_size):
        """Equivale a cell(85, left) + cell(85, right, align="R") do script original."""
        usable = self.w - self.l_margin - self.r_margin
        y0 = self.get_y()
        right_w = 0
        if right:
            self.set_font("DejaVu", right_style, right_size)
            right_w = min(self.get_string_width(right) + 2 * self.c_margin, usable / 2)
        left_w = usable - right_w - (2 if right_w else 0)

        linhas = self.count_lines(left_w, left, left_style, left_size)
        if right:
            linhas = max(linhas, self.count_lines(right_w, right, right_style, right_size))
        self.ensure_space(linhas * h)
        y0 = self.get_y()

        self.set_xy(self.l_margin, y0)
        self.set_font("DejaVu", left_style, left_size)
        if self.get_string_width(left) + 2 * self.c_margin <= left_w:
            self.cell(left_w, h, left)
            y_left = y0 + h
        else:
            self.multi_cell(left_w, h, left, align="L", **NEXT_LINE)
            y_left = self.get_y()

        y_right = y0
        if right:
            self.set_xy(self.l_margin + usable - right_w, y0)
            self.set_font("DejaVu", right_style, right_size)
            self.multi_cell(right_w, h, right, align="R", **NEXT_LINE)
            y_right = self.get_y()
        self.set_xy(self.l_margin, max(y_left, y_right, y0 + h))

    def full_row(self, h, text, style, size):
        self.set_font("DejaVu", style, size)
        self.multi_cell(0, h, text, align="L", **NEXT_LINE)

    def add_section_title(self, title):
        self.set_font("DejaVu", "B", 12)
        self.cell(0, 8, title, align="L", **NEXT_LINE)
        self.line(self.get_x(), self.get_y(), self.get_x() + 170, self.get_y())
        self.ln(4)

    def add_header(self, data):
        self.full_row(10, data["nome"], "B", 22)
        self.ln(2)
        rotulo = lambda nome, chave: f"{nome}: {data[chave]}" if data.get(chave) else ""
        self.pair_row(5, rotulo("LinkedIn", "linkedin"), "", 9, rotulo("E-mail", "email"), "", 9)
        self.pair_row(5, rotulo("GitHub", "github"), "", 9, rotulo("Celular", "celular"), "", 9)
        self.ln(6)

    def add_summary(self, summary_text):
        self.add_section_title("Resumo")
        self.set_font("DejaVu", "", 10)
        self.multi_cell(0, 5, summary_text, align="J", **NEXT_LINE)
        self.ln(4)

    def add_skills(self, skills):
        self.add_section_title("Habilidades")
        category_col_width = 45
        line_height = 6
        usable = self.w - self.l_margin - self.r_margin
        for skill in skills:
            linhas = max(self.count_lines(category_col_width, f"• {skill['categoria']}:", "B", 10),
                         self.count_lines(usable - category_col_width, skill["itens"], "", 10))
            self.ensure_space(linhas * line_height)
            y_before_line = self.get_y()
            self.set_font("DejaVu", "B", 10)
            self.multi_cell(category_col_width, line_height, f"• {skill['categoria']}:", align="L", **NEXT_LINE)
            y_after_category = self.get_y()
            self.set_xy(self.l_margin + category_col_width, y_before_line)
            self.set_font("DejaVu", "", 10)
            self.multi_cell(0, line_height, skill["itens"], align="L", **NEXT_LINE)
            self.set_y(max(y_after_category, self.get_y()))
            self.ln(1)
        self.ln(4)

    def add_experience(self, experiences):
        self.add_section_title("Experiência")
        for job in experiences:
            self.full_row(6, job["cargo"], "B", 11)
            local_periodo = " ".join(x for x in (job["local"], job["periodo"]) if x)
            self.pair_row(6, job["empresa"], "B", 10, local_periodo, "", 10)
            self.ln(2)
            self.set_font("DejaVu", "", 10)
            for point in job["pontos"]:
                self.cell(6, 5, "•")
                self.multi_cell(0, 5, point, align="J", **NEXT_LINE)
                self.ln(1)
            if job["contexto"]:
                self.set_font("DejaVu", "B", 10)
                self.cell(0, 5, "Contexto:", **NEXT_LINE)
                self.set_font("DejaVu", "", 10)
                self.multi_cell(0, 5, job["contexto"], align="J", **NEXT_LINE)
            self.ln(7)

    def add_education(self, educations):
        self.add_section_title("Formação")
        for edu in educations:
            self.pair_row(6, edu["instituicao"], "B", 11, edu["grau"], "", 10)
            self.pair_row(6, edu["curso"], "", 10, edu["periodo"], "", 10)
            self.ln(3)

    def add_simple_section(self, title, items):
        self.add_section_title(title)
        date_width = 40
        title_width = self.w - self.l_margin - self.r_margin - date_width
        for item in items:
            self.ensure_space(self.count_lines(title_width, item["titulo"], "B", 10) * 6)
            y_start = self.get_y()
            self.set_font("DejaVu", "B", 10)
            self.multi_cell(title_width, 6, item["titulo"], align="J", **NEXT_LINE)
            y_after_title = self.get_y()
            self.set_xy(self.l_margin + title_width, y_start)
            self.set_font("DejaVu", "", 10)
            self.multi_cell(date_width, 6, item["periodo"], align="R", **NEXT_LINE)
            self.set_y(max(y_after_title, self.get_y()))
            self.ln(1)
            if item["descricao"]:
                self.set_font("DejaVu", "", 9)
                self.multi_cell(0, 5, item["descricao"], align="J", **NEXT_LINE)
            self.ln(3)

    def add_certifications(self, certifications):
        self.add_section_title("Certificações")
        for cert in certifications:
            self.pair_row(6, cert["nome"], "", 10, cert["data"], "", 10)
        self.ln(3)

    def add_volunteering(self, volunteering):
        self.add_section_title("Voluntariado")
        for item in volunteering:
            self.pair_row(6, item["funcao"], "B", 10, item["periodo"], "", 10)
            if item["descricao"]:
                self.set_font("DejaVu", "", 9)
                self.multi_cell(0, 5, item["descricao"], align="J", **NEXT_LINE)
            self.ln(3)


def gerar_pdf(cv: dict) -> bytes:
    pdf = ResumePDF()
    pdf.set_title(f"Currículo - {cv['pessoal']['nome']}")
    pdf.add_page()

    pdf.add_header(cv["pessoal"])
    if cv["resumo"]:
        pdf.add_summary(cv["resumo"])
    if cv["habilidades"]:
        pdf.add_skills(cv["habilidades"])
    if cv["experiencias"]:
        pdf.add_experience(cv["experiencias"])
    if cv["formacoes"]:
        pdf.add_education(cv["formacoes"])
    if cv["palestras"]:
        pdf.add_simple_section("Palestras", cv["palestras"])
    if cv["publicacoes"]:
        pdf.add_simple_section("Publicações", cv["publicacoes"])
    if cv["certificacoes"]:
        pdf.add_certifications(cv["certificacoes"])
    if cv["voluntariado"]:
        pdf.add_volunteering(cv["voluntariado"])

    return bytes(pdf.output())
