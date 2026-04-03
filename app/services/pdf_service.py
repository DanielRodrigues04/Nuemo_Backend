from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime

from app.schemas.report import CompanyDetailReport

PAGE_WIDTH = 595.0
PAGE_HEIGHT = 842.0
PAGE_MARGIN_X = 36.0
CONTENT_WIDTH = PAGE_WIDTH - (PAGE_MARGIN_X * 2)
HEADER_HEIGHT = 110.0
BODY_TOP_Y = PAGE_HEIGHT - HEADER_HEIGHT - 24.0
BODY_BOTTOM_Y = 56.0

FONT_REGULAR = "F1"
FONT_BOLD = "F2"

Color = tuple[float, float, float]


def hex_to_rgb(value: str) -> Color:
    value = value.strip().lstrip("#")
    return tuple(max(0.0, min(1.0, int(value[index : index + 2], 16) / 255.0)) for index in (0, 2, 4))


COLOR_WHITE = (1.0, 1.0, 1.0)
COLOR_TEXT = hex_to_rgb("172535")
COLOR_MUTED = hex_to_rgb("627183")
COLOR_LINE = hex_to_rgb("D8E0E8")
COLOR_NAVY = hex_to_rgb("16324F")
COLOR_NAVY_SOFT = hex_to_rgb("1E486F")
COLOR_HEADER_TEXT = hex_to_rgb("E7EFF7")
COLOR_HEADER_SUBTEXT = hex_to_rgb("BCD0E3")
COLOR_PANEL = hex_to_rgb("F5F8FC")
COLOR_PANEL_ALT = hex_to_rgb("EEF3F8")
COLOR_ACCENT = hex_to_rgb("2C8A78")
COLOR_GOLD = hex_to_rgb("D39C43")
COLOR_SUCCESS_BG = hex_to_rgb("E5F4EA")
COLOR_SUCCESS_TEXT = hex_to_rgb("1F6B3C")
COLOR_PENDING_BG = hex_to_rgb("FFF1DB")
COLOR_PENDING_TEXT = hex_to_rgb("9B5A00")

MONTH_NAMES = {
    "01": "Janeiro",
    "02": "Fevereiro",
    "03": "Marco",
    "04": "Abril",
    "05": "Maio",
    "06": "Junho",
    "07": "Julho",
    "08": "Agosto",
    "09": "Setembro",
    "10": "Outubro",
    "11": "Novembro",
    "12": "Dezembro",
}


@dataclass
class PdfPage:
    commands: list[str] = field(default_factory=list)


def normalize_display_text(value: str | None) -> str:
    if value is None:
        return ""

    normalized = unicodedata.normalize("NFKD", str(value))
    prepared = " ".join(normalized.replace("\r", " ").replace("\n", " ").split())
    return prepared.encode("latin-1", "ignore").decode("latin-1")


def sanitize_pdf_text(value: str) -> str:
    return normalize_display_text(value).replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def estimate_character_width(character: str) -> float:
    if character in " ilI.,'`|!:":
        return 0.26
    if character in "frt()[]/\\-":
        return 0.34
    if character in "mwMW@%&#":
        return 0.9
    if character.isupper():
        return 0.63
    if character.isdigit():
        return 0.56
    return 0.52


def estimate_text_width(text: str, font_size: float) -> float:
    return sum(estimate_character_width(character) for character in text) * font_size


def truncate_text(text: str, max_width: float, font_size: float, suffix: str = "...") -> str:
    prepared = normalize_display_text(text)
    if not prepared:
        return ""
    if estimate_text_width(prepared, font_size) <= max_width:
        return prepared

    current = prepared
    suffix_width = estimate_text_width(suffix, font_size)
    available_width = max(0.0, max_width - suffix_width)

    while current and estimate_text_width(current, font_size) > available_width:
        current = current[:-1]

    return f"{current.rstrip()}{suffix}" if current else suffix


def wrap_text(text: str, max_width: float, font_size: float, *, max_lines: int | None = None) -> list[str]:
    prepared = normalize_display_text(text)
    if not prepared:
        return [""]

    words = prepared.split(" ")
    lines: list[str] = []
    current = ""

    for word in words:
        candidate = word if not current else f"{current} {word}"
        if estimate_text_width(candidate, font_size) <= max_width:
            current = candidate
            continue

        if current:
            lines.append(current)
            current = ""
            if max_lines is not None and len(lines) >= max_lines:
                lines[-1] = truncate_text(lines[-1], max_width, font_size)
                return lines

        if estimate_text_width(word, font_size) <= max_width:
            current = word
            continue

        fragment = ""
        for character in word:
            candidate_fragment = f"{fragment}{character}"
            if fragment and estimate_text_width(candidate_fragment, font_size) > max_width:
                lines.append(fragment)
                if max_lines is not None and len(lines) >= max_lines:
                    lines[-1] = truncate_text(lines[-1], max_width, font_size)
                    return lines
                fragment = character
            else:
                fragment = candidate_fragment

        current = fragment

    if current:
        lines.append(current)

    if not lines:
        return [prepared]

    if max_lines is not None and len(lines) > max_lines:
        lines = lines[:max_lines]
        lines[-1] = truncate_text(lines[-1], max_width, font_size)

    return lines


def rgb(color: Color) -> str:
    return " ".join(f"{channel:.3f}" for channel in color)


def add_rect(
    page: PdfPage,
    x: float,
    y: float,
    width: float,
    height: float,
    *,
    fill: Color | None = None,
    stroke: Color | None = None,
    line_width: float = 1.0,
) -> None:
    if fill is None and stroke is None:
        return

    if fill is not None:
        page.commands.append(f"{rgb(fill)} rg")
    if stroke is not None:
        page.commands.append(f"{rgb(stroke)} RG")
        page.commands.append(f"{line_width:.2f} w")

    operator = "B" if fill is not None and stroke is not None else "f" if fill is not None else "S"
    page.commands.append(f"{x:.2f} {y:.2f} {width:.2f} {height:.2f} re {operator}")


def add_line(
    page: PdfPage,
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    *,
    stroke: Color,
    line_width: float = 1.0,
) -> None:
    page.commands.extend(
        [
            f"{rgb(stroke)} RG",
            f"{line_width:.2f} w",
            f"{x1:.2f} {y1:.2f} m {x2:.2f} {y2:.2f} l S",
        ]
    )


def add_text(
    page: PdfPage,
    text: str,
    x: float,
    y: float,
    *,
    font: str = FONT_REGULAR,
    size: float = 11.0,
    color: Color = COLOR_TEXT,
    align: str = "left",
) -> None:
    prepared = normalize_display_text(text)
    if not prepared:
        return

    draw_x = x
    text_width = estimate_text_width(prepared, size)
    if align == "center":
        draw_x = x - (text_width / 2)
    elif align == "right":
        draw_x = x - text_width

    page.commands.extend(
        [
            "BT",
            f"/{font} {size:.2f} Tf",
            f"{rgb(color)} rg",
            f"1 0 0 1 {draw_x:.2f} {y:.2f} Tm",
            f"({sanitize_pdf_text(prepared)}) Tj",
            "ET",
        ]
    )


def add_wrapped_text(
    page: PdfPage,
    text: str,
    x: float,
    y: float,
    max_width: float,
    *,
    font: str = FONT_REGULAR,
    size: float = 11.0,
    color: Color = COLOR_TEXT,
    line_height: float | None = None,
    max_lines: int | None = None,
) -> float:
    current_y = y
    actual_line_height = line_height or (size + 4.0)

    for line in wrap_text(text, max_width, size, max_lines=max_lines):
        add_text(page, line, x, current_y, font=font, size=size, color=color)
        current_y -= actual_line_height

    return current_y


def format_currency(value: float) -> str:
    raw = f"{value:,.2f}"
    return f"R$ {raw.replace(',', 'X').replace('.', ',').replace('X', '.')}"


def format_percentage(value: float) -> str:
    return f"{value:.1f}%".replace(".", ",")


def format_date(value: datetime | str | None) -> str:
    if value is None:
        return "--"
    if isinstance(value, datetime):
        return value.strftime("%d/%m/%Y")

    text = normalize_display_text(value)
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
        year, month, day = text.split("-")
        return f"{day}/{month}/{year}"
    if re.fullmatch(r"\d{4}-\d{2}", text):
        year, month = text.split("-")
        return f"{month}/{year}"
    return text


def format_period_label(value: str) -> str:
    text = normalize_display_text(value) or "Historico completo"

    if re.fullmatch(r"\d{4}-\d{2}", text):
        year, month = text.split("-")
        return f"{MONTH_NAMES.get(month, month)} de {year}"

    range_match = re.fullmatch(r"(\d{4}-\d{2}-\d{2}) a (\d{4}-\d{2}-\d{2})", text)
    if range_match:
        return f"{format_date(range_match.group(1))} a {format_date(range_match.group(2))}"

    return text


def format_document(value: str | None) -> str:
    digits = re.sub(r"\D", "", value or "")
    if len(digits) == 11:
        return f"{digits[0:3]}.{digits[3:6]}.{digits[6:9]}-{digits[9:11]}"
    if len(digits) == 14:
        return f"{digits[0:2]}.{digits[2:5]}.{digits[5:8]}/{digits[8:12]}-{digits[12:14]}"
    return normalize_display_text(value) or "Nao informado"


def format_company_type(value: object) -> str:
    raw = normalize_display_text(getattr(value, "value", value))
    if raw == "empresa":
        return "Empresa"
    if raw == "pessoa_fisica":
        return "Pessoa fisica"
    return raw.replace("_", " ").title() or "Nao informado"


def format_status_label(value: object) -> str:
    raw = normalize_display_text(getattr(value, "value", value))
    if raw == "pago":
        return "Pago"
    return "Em aberto"


def build_pdf_document(pages: list[PdfPage]) -> bytes:
    objects: list[bytes] = []
    page_object_numbers: list[int] = []
    object_number = 5

    objects.append(b"<< /Type /Catalog /Pages 2 0 R >>")
    objects.append(b"<< /Type /Pages /Count 0 /Kids [] >>")
    objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>")
    objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>")

    for page in pages:
        page_number = object_number
        content_number = object_number + 1
        page_object_numbers.append(page_number)

        stream = "\n".join(page.commands).encode("latin-1", "ignore")
        page_object = (
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {PAGE_WIDTH:.0f} {PAGE_HEIGHT:.0f}] "
            f"/Resources << /Font << /F1 3 0 R /F2 4 0 R >> >> /Contents {content_number} 0 R >>"
        ).encode("latin-1")
        content_object = f"<< /Length {len(stream)} >>\nstream\n".encode("latin-1") + stream + b"\nendstream"

        objects.append(page_object)
        objects.append(content_object)
        object_number += 2

    kids = " ".join(f"{number} 0 R" for number in page_object_numbers)
    objects[1] = f"<< /Type /Pages /Count {len(page_object_numbers)} /Kids [{kids}] >>".encode("latin-1")

    pdf = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]

    for index, obj in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf.extend(f"{index} 0 obj\n".encode("latin-1"))
        pdf.extend(obj)
        pdf.extend(b"\nendobj\n")

    xref_offset = len(pdf)
    pdf.extend(f"xref\n0 {len(objects) + 1}\n".encode("latin-1"))
    pdf.extend(b"0000000000 65535 f \n")

    for offset in offsets[1:]:
        pdf.extend(f"{offset:010d} 00000 n \n".encode("latin-1"))

    pdf.extend(
        (
            f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
            f"startxref\n{xref_offset}\n%%EOF"
        ).encode("latin-1")
    )
    return bytes(pdf)


class CompanyStatementPdfRenderer:
    def __init__(
        self,
        report: CompanyDetailReport,
        *,
        clinic_name: str,
        period_label: str,
        generated_at: datetime | None = None,
    ) -> None:
        self.report = report
        self.clinic_name = normalize_display_text(clinic_name) or "Clinica"
        self.period_label = format_period_label(period_label)
        self.generated_at = generated_at or datetime.now()
        self.generated_label = self.generated_at.strftime("%d/%m/%Y %H:%M")
        self.pending_count = sum(1 for attendance in report.atendimentos if format_status_label(attendance.status) != "Pago")
        self.pages: list[PdfPage] = []
        self.current_page = self._start_new_page()

    @property
    def cursor_y(self) -> float:
        return self._cursor_y

    @cursor_y.setter
    def cursor_y(self, value: float) -> None:
        self._cursor_y = value

    def _start_new_page(self) -> PdfPage:
        page = PdfPage()
        self.pages.append(page)
        self.current_page = page
        self.cursor_y = BODY_TOP_Y
        return page

    def _ensure_space(self, height: float) -> None:
        if self.cursor_y - height < BODY_BOTTOM_Y:
            self._start_new_page()

    def _page_chrome(self, page_number: int, total_pages: int) -> list[str]:
        page = PdfPage()
        header_bottom = PAGE_HEIGHT - HEADER_HEIGHT
        meta_box_x = PAGE_WIDTH - PAGE_MARGIN_X - 172.0
        meta_box_y = PAGE_HEIGHT - 87.0

        add_rect(page, 0.0, header_bottom, PAGE_WIDTH, HEADER_HEIGHT, fill=COLOR_NAVY)
        add_rect(page, 0.0, PAGE_HEIGHT - 6.0, PAGE_WIDTH, 6.0, fill=COLOR_GOLD)
        add_rect(page, meta_box_x, meta_box_y, 172.0, 52.0, fill=COLOR_WHITE, stroke=COLOR_LINE)

        add_text(page, self.clinic_name.upper(), PAGE_MARGIN_X, PAGE_HEIGHT - 30.0, font=FONT_BOLD, size=9.0, color=COLOR_HEADER_TEXT)
        add_text(page, "Extrato de Cobranca", PAGE_MARGIN_X, PAGE_HEIGHT - 58.0, font=FONT_BOLD, size=22.0, color=COLOR_WHITE)
        add_text(
            page,
            truncate_text(self.report.empresa.nome, 300.0, 12.0),
            PAGE_MARGIN_X,
            PAGE_HEIGHT - 80.0,
            font=FONT_BOLD,
            size=12.0,
            color=COLOR_HEADER_TEXT,
        )
        add_text(
            page,
            "Relatorio financeiro consolidado para conferencia e cobranca.",
            PAGE_MARGIN_X,
            PAGE_HEIGHT - 97.0,
            font=FONT_REGULAR,
            size=10.0,
            color=COLOR_HEADER_SUBTEXT,
        )

        add_text(page, "Periodo", meta_box_x + 12.0, meta_box_y + 35.0, font=FONT_BOLD, size=8.0, color=COLOR_MUTED)
        add_text(
            page,
            truncate_text(self.period_label, 148.0, 10.0),
            meta_box_x + 12.0,
            meta_box_y + 21.0,
            font=FONT_BOLD,
            size=10.0,
            color=COLOR_TEXT,
        )
        add_text(page, "Emitido em", meta_box_x + 12.0, meta_box_y + 8.0, font=FONT_BOLD, size=8.0, color=COLOR_MUTED)
        add_text(page, self.generated_label, meta_box_x + 74.0, meta_box_y + 8.0, font=FONT_REGULAR, size=8.0, color=COLOR_TEXT)

        add_line(page, PAGE_MARGIN_X, 38.0, PAGE_WIDTH - PAGE_MARGIN_X, 38.0, stroke=COLOR_LINE)
        add_text(page, self.clinic_name, PAGE_MARGIN_X, 24.0, font=FONT_REGULAR, size=8.5, color=COLOR_MUTED)
        add_text(
            page,
            f"Pagina {page_number}/{total_pages}",
            PAGE_WIDTH - PAGE_MARGIN_X,
            24.0,
            font=FONT_BOLD,
            size=8.5,
            color=COLOR_MUTED,
            align="right",
        )

        return page.commands

    def _draw_section_heading(self, title: str, subtitle: str) -> None:
        self._ensure_space(30.0)
        add_rect(self.current_page, PAGE_MARGIN_X, self.cursor_y - 4.0, 5.0, 18.0, fill=COLOR_ACCENT)
        add_text(self.current_page, title, PAGE_MARGIN_X + 14.0, self.cursor_y, font=FONT_BOLD, size=13.0, color=COLOR_NAVY)
        add_text(
            self.current_page,
            truncate_text(subtitle, 250.0, 9.0),
            PAGE_WIDTH - PAGE_MARGIN_X,
            self.cursor_y + 1.0,
            font=FONT_REGULAR,
            size=9.0,
            color=COLOR_MUTED,
            align="right",
        )
        self.cursor_y -= 28.0

    def _draw_company_box(self) -> None:
        self._draw_section_heading("Dados da cobranca", "Empresa contratante e canal de contato")
        self._ensure_space(116.0)

        box_height = 98.0
        box_bottom = self.cursor_y - box_height
        column_width = CONTENT_WIDTH / 2

        add_rect(self.current_page, PAGE_MARGIN_X, box_bottom, CONTENT_WIDTH, box_height, fill=COLOR_WHITE, stroke=COLOR_LINE)
        add_rect(self.current_page, PAGE_MARGIN_X, box_bottom, 6.0, box_height, fill=COLOR_NAVY_SOFT)
        add_line(
            self.current_page,
            PAGE_MARGIN_X + column_width,
            box_bottom,
            PAGE_MARGIN_X + column_width,
            box_bottom + box_height,
            stroke=COLOR_LINE,
        )
        add_line(
            self.current_page,
            PAGE_MARGIN_X + 6.0,
            box_bottom + box_height / 2,
            PAGE_MARGIN_X + CONTENT_WIDTH,
            box_bottom + box_height / 2,
            stroke=COLOR_LINE,
        )

        fields = [
            ("Empresa", self.report.empresa.nome, PAGE_MARGIN_X + 18.0, box_bottom + 70.0, column_width - 30.0),
            ("Documento", format_document(self.report.empresa.documento), PAGE_MARGIN_X + column_width + 14.0, box_bottom + 70.0, column_width - 28.0),
            ("Contato", normalize_display_text(self.report.empresa.contato) or "Nao informado", PAGE_MARGIN_X + 18.0, box_bottom + 22.0, column_width - 30.0),
            ("Tipo", format_company_type(self.report.empresa.tipo), PAGE_MARGIN_X + column_width + 14.0, box_bottom + 22.0, column_width - 28.0),
        ]

        for label, value, x, y, width in fields:
            add_text(self.current_page, label.upper(), x, y + 16.0, font=FONT_BOLD, size=8.0, color=COLOR_MUTED)
            add_wrapped_text(
                self.current_page,
                value,
                x,
                y,
                width,
                font=FONT_BOLD,
                size=12.0,
                color=COLOR_TEXT,
                line_height=14.0,
                max_lines=2,
            )

        self.cursor_y = box_bottom - 18.0

    def _draw_summary_cards(self) -> None:
        self._draw_section_heading("Visao executiva", "Totais consolidados para conferencia rapida")
        self._ensure_space(96.0)

        card_gap = 10.0
        card_width = (CONTENT_WIDTH - (card_gap * 3)) / 4
        card_height = 78.0
        card_bottom = self.cursor_y - card_height

        cards = [
            ("Total faturado", format_currency(self.report.valor_total), "Base completa do periodo", COLOR_NAVY_SOFT),
            ("Recebido", format_currency(self.report.valor_recebido), "Valores com baixa confirmada", COLOR_ACCENT),
            (
                "Em aberto",
                format_currency(self.report.valor_pendente),
                f"{self.pending_count} atendimento(s) aguardando pagamento",
                COLOR_GOLD,
            ),
            ("Atendimentos", str(self.report.total_exames), "Registros incluidos no extrato", COLOR_MUTED),
        ]

        for index, (label, value, helper, accent) in enumerate(cards):
            x = PAGE_MARGIN_X + (index * (card_width + card_gap))
            add_rect(self.current_page, x, card_bottom, card_width, card_height, fill=COLOR_WHITE, stroke=COLOR_LINE)
            add_rect(self.current_page, x, card_bottom + card_height - 6.0, card_width, 6.0, fill=accent)
            add_text(self.current_page, label.upper(), x + 12.0, card_bottom + 52.0, font=FONT_BOLD, size=8.0, color=COLOR_MUTED)
            add_text(
                self.current_page,
                truncate_text(value, card_width - 24.0, 15.0),
                x + 12.0,
                card_bottom + 30.0,
                font=FONT_BOLD,
                size=15.0,
                color=COLOR_TEXT,
            )
            add_wrapped_text(
                self.current_page,
                helper,
                x + 12.0,
                card_bottom + 16.0,
                card_width - 24.0,
                font=FONT_REGULAR,
                size=8.5,
                color=COLOR_MUTED,
                line_height=10.0,
                max_lines=2,
            )

        self.cursor_y = card_bottom - 18.0

    def _draw_exam_table_header(self) -> list[tuple[str, float, str]]:
        columns = [
            ("Exame", 250.0, "left"),
            ("Qtde", 65.0, "center"),
            ("Participacao", 110.0, "center"),
            ("Valor total", 98.0, "right"),
        ]
        header_height = 24.0
        header_bottom = self.cursor_y - header_height
        x = PAGE_MARGIN_X

        add_rect(self.current_page, PAGE_MARGIN_X, header_bottom, CONTENT_WIDTH, header_height, fill=COLOR_NAVY, stroke=COLOR_NAVY)

        for label, width, align in columns:
            if align == "left":
                text_x = x + 10.0
            elif align == "center":
                text_x = x + (width / 2)
            else:
                text_x = x + width - 10.0

            add_text(self.current_page, label, text_x, header_bottom + 8.0, font=FONT_BOLD, size=9.0, color=COLOR_WHITE, align=align)
            x += width

        self.cursor_y = header_bottom
        return columns

    def _draw_exam_summary(self) -> None:
        self._draw_section_heading("Resumo por exame", "Distribuicao do faturamento no periodo selecionado")

        if not self.report.exames_por_tipo:
            self._ensure_space(72.0)
            panel_bottom = self.cursor_y - 58.0
            add_rect(self.current_page, PAGE_MARGIN_X, panel_bottom, CONTENT_WIDTH, 58.0, fill=COLOR_PANEL, stroke=COLOR_LINE)
            add_text(self.current_page, "Nenhum exame encontrado no periodo informado.", PAGE_MARGIN_X + 16.0, panel_bottom + 28.0, font=FONT_BOLD, size=11.0, color=COLOR_TEXT)
            add_text(self.current_page, "O extrato foi emitido sem agrupamentos de faturamento.", PAGE_MARGIN_X + 16.0, panel_bottom + 14.0, font=FONT_REGULAR, size=9.0, color=COLOR_MUTED)
            self.cursor_y = panel_bottom - 16.0
            return

        columns = self._draw_exam_table_header()
        row_height = 24.0

        for index, item in enumerate(self.report.exames_por_tipo):
            if self.cursor_y - row_height < BODY_BOTTOM_Y:
                self._start_new_page()
                self._draw_section_heading("Resumo por exame", "Continuidade do agrupamento financeiro")
                columns = self._draw_exam_table_header()

            row_bottom = self.cursor_y - row_height
            row_fill = COLOR_PANEL if index % 2 else COLOR_WHITE
            add_rect(self.current_page, PAGE_MARGIN_X, row_bottom, CONTENT_WIDTH, row_height, fill=row_fill, stroke=COLOR_LINE)

            share = (item.valor_total / self.report.valor_total * 100.0) if self.report.valor_total else 0.0
            values = [
                truncate_text(item.exame_nome, columns[0][1] - 18.0, 10.0),
                str(item.quantidade),
                format_percentage(share),
                format_currency(item.valor_total),
            ]

            x = PAGE_MARGIN_X
            for (label, width, align), value in zip(columns, values):
                if align == "left":
                    text_x = x + 10.0
                elif align == "center":
                    text_x = x + (width / 2)
                else:
                    text_x = x + width - 10.0

                add_text(self.current_page, value, text_x, row_bottom + 8.0, font=FONT_REGULAR, size=10.0, color=COLOR_TEXT, align=align)
                x += width

            self.cursor_y = row_bottom

        self.cursor_y -= 16.0

    def _draw_note_box(self) -> None:
        self._ensure_space(72.0)

        is_pending = self.pending_count > 0
        panel_bottom = self.cursor_y - 58.0
        fill = COLOR_PENDING_BG if is_pending else COLOR_SUCCESS_BG
        accent = COLOR_GOLD if is_pending else COLOR_ACCENT
        text = (
            f"Ha {self.pending_count} atendimento(s) pendente(s) neste extrato. Eles seguem em aberto ate a baixa financeira."
            if is_pending
            else "Todos os atendimentos deste extrato ja foram baixados como pagos no sistema."
        )

        add_rect(self.current_page, PAGE_MARGIN_X, panel_bottom, CONTENT_WIDTH, 58.0, fill=fill, stroke=COLOR_LINE)
        add_rect(self.current_page, PAGE_MARGIN_X, panel_bottom, 6.0, 58.0, fill=accent)
        add_text(self.current_page, "Observacao operacional", PAGE_MARGIN_X + 18.0, panel_bottom + 34.0, font=FONT_BOLD, size=10.0, color=COLOR_TEXT)
        add_wrapped_text(
            self.current_page,
            text,
            PAGE_MARGIN_X + 18.0,
            panel_bottom + 18.0,
            CONTENT_WIDTH - 32.0,
            font=FONT_REGULAR,
            size=9.0,
            color=COLOR_MUTED,
            line_height=11.0,
            max_lines=2,
        )

        self.cursor_y = panel_bottom - 16.0

    def _draw_attendance_table_header(self) -> list[tuple[str, float, str]]:
        columns = [
            ("Data", 58.0, "left"),
            ("Paciente", 138.0, "left"),
            ("CPF", 78.0, "left"),
            ("Exame", 112.0, "left"),
            ("Status", 60.0, "center"),
            ("Valor", 77.0, "right"),
        ]
        header_height = 26.0
        header_bottom = self.cursor_y - header_height
        x = PAGE_MARGIN_X

        add_rect(self.current_page, PAGE_MARGIN_X, header_bottom, CONTENT_WIDTH, header_height, fill=COLOR_NAVY, stroke=COLOR_NAVY)

        for label, width, align in columns:
            if align == "left":
                text_x = x + 10.0
            elif align == "center":
                text_x = x + (width / 2)
            else:
                text_x = x + width - 10.0

            add_text(self.current_page, label, text_x, header_bottom + 9.0, font=FONT_BOLD, size=9.0, color=COLOR_WHITE, align=align)
            x += width

        self.cursor_y = header_bottom
        return columns

    def _draw_attendance_details(self) -> None:
        self._draw_section_heading("Detalhamento dos atendimentos", "Itens incluidos no extrato para conferencia")

        if not self.report.atendimentos:
            self._ensure_space(72.0)
            panel_bottom = self.cursor_y - 58.0
            add_rect(self.current_page, PAGE_MARGIN_X, panel_bottom, CONTENT_WIDTH, 58.0, fill=COLOR_PANEL, stroke=COLOR_LINE)
            add_text(self.current_page, "Nenhum atendimento encontrado no periodo informado.", PAGE_MARGIN_X + 16.0, panel_bottom + 28.0, font=FONT_BOLD, size=11.0, color=COLOR_TEXT)
            add_text(self.current_page, "Revise os filtros antes de reenviar o extrato.", PAGE_MARGIN_X + 16.0, panel_bottom + 14.0, font=FONT_REGULAR, size=9.0, color=COLOR_MUTED)
            self.cursor_y = panel_bottom - 16.0
            return

        columns = self._draw_attendance_table_header()
        row_height = 28.0

        for index, attendance in enumerate(self.report.atendimentos):
            if self.cursor_y - row_height < BODY_BOTTOM_Y:
                self._start_new_page()
                self._draw_section_heading("Detalhamento dos atendimentos", "Continuidade do extrato financeiro")
                columns = self._draw_attendance_table_header()

            row_bottom = self.cursor_y - row_height
            row_fill = COLOR_PANEL if index % 2 else COLOR_WHITE
            add_rect(self.current_page, PAGE_MARGIN_X, row_bottom, CONTENT_WIDTH, row_height, fill=row_fill, stroke=COLOR_LINE)

            x = PAGE_MARGIN_X
            baseline = row_bottom + 10.0
            values = [
                format_date(attendance.data),
                truncate_text(attendance.nome_paciente, columns[1][1] - 16.0, 9.5),
                truncate_text(format_document(attendance.cpf_paciente), columns[2][1] - 16.0, 9.5),
                truncate_text(attendance.exame_nome, columns[3][1] - 16.0, 9.5),
            ]

            for value, (label, width, align) in zip(values, columns[:4]):
                add_text(self.current_page, value, x + 10.0, baseline, font=FONT_REGULAR, size=9.5, color=COLOR_TEXT)
                x += width

            status_raw = format_status_label(attendance.status)
            status_fill = COLOR_SUCCESS_BG if status_raw == "Pago" else COLOR_PENDING_BG
            status_text = COLOR_SUCCESS_TEXT if status_raw == "Pago" else COLOR_PENDING_TEXT
            status_width = columns[4][1]
            pill_width = status_width - 16.0
            pill_height = 16.0
            pill_x = x + ((status_width - pill_width) / 2)
            pill_y = row_bottom + 6.0
            add_rect(self.current_page, pill_x, pill_y, pill_width, pill_height, fill=status_fill, stroke=None)
            add_text(
                self.current_page,
                status_raw,
                x + (status_width / 2),
                row_bottom + 11.0,
                font=FONT_BOLD,
                size=8.0,
                color=status_text,
                align="center",
            )
            x += status_width

            add_text(
                self.current_page,
                format_currency(attendance.valor),
                x + columns[5][1] - 10.0,
                baseline,
                font=FONT_BOLD,
                size=9.5,
                color=COLOR_TEXT,
                align="right",
            )

            self.cursor_y = row_bottom

    def render(self) -> bytes:
        self._draw_company_box()
        self._draw_summary_cards()
        self._draw_exam_summary()
        self._draw_note_box()

        if self.report.atendimentos:
            self._start_new_page()
            self._draw_attendance_details()

        total_pages = len(self.pages)
        final_pages: list[PdfPage] = []

        for index, page in enumerate(self.pages, start=1):
            final_pages.append(PdfPage(commands=self._page_chrome(index, total_pages) + page.commands))

        return build_pdf_document(final_pages)


def generate_company_statement_pdf(
    report: CompanyDetailReport,
    *,
    clinic_name: str,
    period_label: str,
    generated_at: datetime | None = None,
) -> bytes:
    renderer = CompanyStatementPdfRenderer(
        report,
        clinic_name=clinic_name,
        period_label=period_label,
        generated_at=generated_at,
    )
    return renderer.render()
