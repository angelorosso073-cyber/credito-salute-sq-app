"""
Converte tutti i file .md in questa cartella in PDF usando reportlab.
"""
import os
import re
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, PageBreak, Flowable, KeepTogether
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER

FOLDER = Path(__file__).parent

# --- stili ---
BASE_FONT = "Helvetica"
BOLD_FONT = "Helvetica-Bold"
ITALIC_FONT = "Helvetica-Oblique"

def build_styles():
    s = getSampleStyleSheet()
    styles = {}
    styles["h1"] = ParagraphStyle(
        "h1", fontName=BOLD_FONT, fontSize=18, leading=24,
        spaceBefore=18, spaceAfter=10, textColor=colors.HexColor("#1a3a5c")
    )
    styles["h2"] = ParagraphStyle(
        "h2", fontName=BOLD_FONT, fontSize=14, leading=19,
        spaceBefore=14, spaceAfter=6, textColor=colors.HexColor("#1a3a5c")
    )
    styles["h3"] = ParagraphStyle(
        "h3", fontName=BOLD_FONT, fontSize=12, leading=16,
        spaceBefore=10, spaceAfter=4, textColor=colors.HexColor("#2d6a4f")
    )
    styles["h4"] = ParagraphStyle(
        "h4", fontName=BOLD_FONT, fontSize=11, leading=15,
        spaceBefore=8, spaceAfter=3, textColor=colors.HexColor("#555555")
    )
    styles["body"] = ParagraphStyle(
        "body", fontName=BASE_FONT, fontSize=10, leading=15,
        spaceBefore=2, spaceAfter=4
    )
    styles["bullet"] = ParagraphStyle(
        "bullet", fontName=BASE_FONT, fontSize=10, leading=14,
        leftIndent=18, spaceBefore=1, spaceAfter=1,
        bulletIndent=6, bulletFontName=BASE_FONT
    )
    styles["bullet2"] = ParagraphStyle(
        "bullet2", fontName=BASE_FONT, fontSize=10, leading=14,
        leftIndent=34, spaceBefore=1, spaceAfter=1,
        bulletIndent=20, bulletFontName=BASE_FONT
    )
    styles["blockquote"] = ParagraphStyle(
        "blockquote", fontName=ITALIC_FONT, fontSize=10, leading=14,
        leftIndent=24, rightIndent=12, spaceBefore=6, spaceAfter=6,
        textColor=colors.HexColor("#444444"),
        borderPadding=(6, 8, 6, 8),
        backColor=colors.HexColor("#f4f4f4"),
        borderColor=colors.HexColor("#cccccc"),
        borderWidth=0,
        borderRadius=2,
    )
    styles["note"] = ParagraphStyle(
        "note", fontName=ITALIC_FONT, fontSize=9, leading=13,
        spaceBefore=4, spaceAfter=4, textColor=colors.HexColor("#666666")
    )
    styles["table_header"] = ParagraphStyle(
        "table_header", fontName=BOLD_FONT, fontSize=9, leading=12,
        textColor=colors.white
    )
    styles["table_cell"] = ParagraphStyle(
        "table_cell", fontName=BASE_FONT, fontSize=9, leading=12
    )
    return styles


class PhoneMockup(Flowable):
    """Disegna un mockup smartphone della vista cliente."""

    _PW = 188
    _PH = 336
    _TOTAL_H = 400

    # Layout constants (altezze elementi schermata)
    _HDR_H = 26
    _CARD_H = 56
    _BTN1_H = 20
    _BTN2_H = 18
    _SP_HDR = 8
    _SP_CARD = 8
    _SP_BTN1 = 6
    _SP_BTN2 = 10

    def wrap(self, avail_w, avail_h):
        self._aw = float(avail_w)
        return (avail_w, self._TOTAL_H)

    def draw(self):
        c = self.canv
        aw = getattr(self, '_aw', 440.0)
        pw, ph = self._PW, self._PH

        px = (aw - pw) / 2.0
        py = 30.0

        # didascalia
        c.setFont("Helvetica", 6.5)
        c.setFillColor(colors.HexColor("#666666"))
        c.drawCentredString(aw / 2, py - 18,
            "Schermata principale — vista cliente (browser mobile, nessuna installazione)")

        # corpo telefono
        c.saveState()
        c.setFillColor(colors.HexColor("#2c3e50"))
        c.setStrokeColor(colors.HexColor("#1a252f"))
        c.setLineWidth(1.5)
        c.roundRect(px, py, pw, ph, 20, fill=1, stroke=1)
        c.restoreState()

        # indicatore home
        c.setFillColor(colors.HexColor("#4a5a6a"))
        c.roundRect(px + (pw - 50) / 2, py + 7, 50, 4, 2, fill=1, stroke=0)

        # schermo
        scr_x = px + 7
        scr_bot = py + 20
        scr_top = py + ph - 22
        scr_w = pw - 14
        c.setFillColor(colors.HexColor("#f5f7fa"))
        c.setStrokeColor(colors.HexColor("#cccccc"))
        c.setLineWidth(0.4)
        c.rect(scr_x, scr_bot, scr_w, scr_top - scr_bot, fill=1, stroke=1)

        # notch
        c.setFillColor(colors.HexColor("#2c3e50"))
        c.roundRect(px + (pw - 52) / 2, py + ph - 13, 52, 9, 4, fill=1, stroke=0)

        self._content(c, scr_x, scr_bot, scr_w, scr_top)
        self._callouts(c, px, py, pw, ph, scr_x, scr_bot, scr_w, scr_top, aw)

    def _content(self, c, sx, sb, sw, st):
        # --- header ---
        hdr_bot = st - self._HDR_H
        c.setFillColor(colors.HexColor("#1a3a5c"))
        c.rect(sx, hdr_bot, sw, self._HDR_H, fill=1, stroke=0)
        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 6.5)
        c.drawString(sx + 7, hdr_bot + 10, "Credito Salute SQ")
        c.setFont("Helvetica", 5.5)
        c.drawRightString(sx + sw - 7, hdr_bot + 10, "Maria R.")

        y = hdr_bot - self._SP_HDR

        # --- card saldo ---
        card_bot = y - self._CARD_H
        c.setFillColor(colors.HexColor("#1a3a5c"))
        c.roundRect(sx + 7, card_bot, sw - 14, self._CARD_H, 5, fill=1, stroke=0)
        c.setFillColor(colors.HexColor("#2c5282"))
        c.roundRect(sx + 7, y - 16, sw - 14, 16, 5, fill=1, stroke=0)
        c.setFillColor(colors.HexColor("#a0bcd4"))
        c.setFont("Helvetica", 5)
        c.drawString(sx + 14, y - 12, "Saldo disponibile")
        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 17)
        c.drawString(sx + 14, card_bot + self._CARD_H - 33, "12,50")
        c.setFillColor(colors.HexColor("#a0bcd4"))
        c.setFont("Helvetica", 5)
        c.drawString(sx + 58, card_bot + self._CARD_H - 26, "crediti SQ")
        # badge in verifica
        c.setFillColor(colors.HexColor("#c88a00"))
        c.roundRect(sx + sw - 64, card_bot + 8, 57, 13, 3, fill=1, stroke=0)
        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 4.5)
        c.drawCentredString(sx + sw - 35.5, card_bot + 13.5, "In verifica: 3,50")

        y = card_bot - self._SP_CARD

        # --- pulsante carica scontrino ---
        btn1_bot = y - self._BTN1_H
        c.setFillColor(colors.HexColor("#27ae60"))
        c.roundRect(sx + 7, btn1_bot, sw - 14, self._BTN1_H, 5, fill=1, stroke=0)
        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 6.5)
        c.drawCentredString(sx + sw / 2, btn1_bot + 7, "Carica scontrino")

        y = btn1_bot - self._SP_BTN1

        # --- pulsante prenota ---
        btn2_bot = y - self._BTN2_H
        c.setFillColor(colors.HexColor("#dce8f5"))
        c.roundRect(sx + 7, btn2_bot, sw - 14, self._BTN2_H, 5, fill=1, stroke=0)
        c.setFillColor(colors.HexColor("#2c5282"))
        c.setFont("Helvetica", 6)
        c.drawCentredString(sx + sw / 2, btn2_bot + 6, "Prenota prestazione")

        y = btn2_bot - self._SP_BTN2

        # --- storico ---
        c.setFillColor(colors.HexColor("#444444"))
        c.setFont("Helvetica-Bold", 5.5)
        c.drawString(sx + 7, y, "Storico movimenti")
        c.setFillColor(colors.HexColor("#888888"))
        c.setFont("Helvetica", 5)
        c.drawRightString(sx + sw - 7, y, "vedi tutti >")
        y -= 4

        items = [
            ("Oggi",  "Scontrino bar — in verifica", "+3,50", True),
            ("03/07", "Scontrino bar — confermato",   "+6,00", True),
            ("28/06", "Visita infermiere",             "-10,00", False),
        ]
        for idx, (date, desc, amount, pos) in enumerate(items):
            row_bot = y - 16
            if row_bot < sb + 24:
                break
            bg = colors.HexColor("#ffffff") if idx % 2 == 0 else colors.HexColor("#f0f4f8")
            c.setFillColor(bg)
            c.rect(sx + 2, row_bot, sw - 4, 15, fill=1, stroke=0)
            c.setFillColor(colors.HexColor("#888888"))
            c.setFont("Helvetica", 4.5)
            c.drawString(sx + 5, row_bot + 4.5, date)
            c.setFillColor(colors.HexColor("#333333"))
            c.setFont("Helvetica", 4.5)
            c.drawString(sx + 30, row_bot + 4.5, desc)
            c.setFillColor(colors.HexColor("#27ae60") if pos else colors.HexColor("#e74c3c"))
            c.setFont("Helvetica-Bold", 4.5)
            c.drawRightString(sx + sw - 5, row_bot + 4.5, amount)
            y = row_bot

        # --- bottom nav ---
        nav_h = 22
        c.setFillColor(colors.white)
        c.setStrokeColor(colors.HexColor("#dddddd"))
        c.setLineWidth(0.4)
        c.rect(sx, sb, sw, nav_h, fill=1, stroke=1)
        for j, tab in enumerate(["Saldo", "Scontrini", "Regole"]):
            tx = sx + (j + 0.5) * sw / 3
            active = j == 0
            c.setFillColor(colors.HexColor("#1a3a5c") if active else colors.HexColor("#aaaaaa"))
            c.setFont("Helvetica-Bold" if active else "Helvetica", 5)
            c.drawCentredString(tx, sb + 7, tab)
            if active:
                c.setFillColor(colors.HexColor("#1a3a5c"))
                c.roundRect(tx - 14, sb + nav_h - 3.5, 28, 3, 1.5, fill=1, stroke=0)

    def _callouts(self, c, px, py, pw, ph, sx, sb, sw, st, aw):
        # posizioni Y calcolate sulle stesse costanti di _content
        hdr_mid   = st - self._HDR_H / 2
        card_bot  = st - self._HDR_H - self._SP_HDR - self._CARD_H
        card_mid  = card_bot + self._CARD_H / 2
        btn1_bot  = card_bot - self._SP_CARD - self._BTN1_H
        btn1_mid  = btn1_bot + self._BTN1_H / 2
        btn2_bot  = btn1_bot - self._SP_BTN1 - self._BTN2_H
        btn2_mid  = btn2_bot + self._BTN2_H / 2
        storico_y = btn2_bot - self._SP_BTN2 - 4 - 24

        phone_right = px + pw
        phone_left  = px

        def dot(x, y):
            c.setFillColor(colors.HexColor("#1a3a5c"))
            c.circle(x, y, 2.5, fill=1, stroke=0)

        def callout_r(ay, text):
            lx2 = phone_right + 34
            c.setStrokeColor(colors.HexColor("#1a3a5c"))
            c.setLineWidth(0.6)
            c.line(phone_right, ay, lx2, ay)
            dot(phone_right, ay)
            lines = text.split("\n")
            c.setFont("Helvetica", 5.5)
            c.setFillColor(colors.HexColor("#1a3a5c"))
            offset = (len(lines) - 1) * 3.5
            for k, l in enumerate(lines):
                c.drawString(lx2 + 3, ay + offset - k * 7, l)

        def callout_l(ay, text):
            lx2 = phone_left - 34
            c.setStrokeColor(colors.HexColor("#1a3a5c"))
            c.setLineWidth(0.6)
            c.line(phone_left, ay, lx2, ay)
            dot(phone_left, ay)
            lines = text.split("\n")
            c.setFont("Helvetica", 5.5)
            c.setFillColor(colors.HexColor("#1a3a5c"))
            offset = (len(lines) - 1) * 3.5
            for k, l in enumerate(lines):
                c.drawRightString(lx2 - 3, ay + offset - k * 7, l)

        callout_l(hdr_mid,   "Profilo cliente\nautomatico")
        callout_l(storico_y, "Storico movimenti\ne scontrini")
        callout_r(card_mid,  "Saldo credito\nin tempo reale")
        callout_r(btn1_mid,  "Carica scontrino\ncon foto")
        callout_r(btn2_mid,  "Prenota prestazione\ncon i crediti")


def inline_md(text, style_name="body"):
    """Converte markdown inline (**bold**, ~~strike~~, `code`) in tag XML reportlab."""
    # escape XML chars prima
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    # bold
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"__(.+?)__", r"<b>\1</b>", text)
    # italic
    text = re.sub(r"\*(.+?)\*", r"<i>\1</i>", text)
    text = re.sub(r"_(.+?)_", r"<i>\1</i>", text)
    # strikethrough → mantieni come testo con prefisso visivo
    text = re.sub(r"~~(.+?)~~", r"<i>[EVITARE: \1]</i>", text)
    # inline code
    text = re.sub(r"`(.+?)`", r"<font face='Courier' size='9'>\1</font>", text)
    return text


def parse_table(lines, styles):
    """Parsa una tabella markdown e restituisce un flowable Table."""
    rows = []
    for line in lines:
        if re.match(r"^\s*\|[-:| ]+\|\s*$", line):
            continue  # riga separatore
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        rows.append(cells)
    if not rows:
        return None

    col_count = max(len(r) for r in rows)
    table_data = []
    for i, row in enumerate(rows):
        # padding celle mancanti
        while len(row) < col_count:
            row.append("")
        if i == 0:
            table_data.append([
                Paragraph(inline_md(c), styles["table_header"]) for c in row
            ])
        else:
            table_data.append([
                Paragraph(inline_md(c), styles["table_cell"]) for c in row
            ])

    page_width = A4[0] - 4 * cm
    col_width = page_width / col_count

    t = Table(table_data, colWidths=[col_width] * col_count)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a3a5c")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#eef2f7")]),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cccccc")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]))
    return t


def md_to_flowables(md_text, styles):
    flowables = []
    lines = md_text.splitlines()
    i = 0

    while i < len(lines):
        line = lines[i]

        # H1
        if line.startswith("# "):
            flowables.append(Paragraph(inline_md(line[2:]), styles["h1"]))
            i += 1
            continue

        # H2
        if line.startswith("## "):
            flowables.append(Paragraph(inline_md(line[3:]), styles["h2"]))
            i += 1
            continue

        # H3
        if line.startswith("### "):
            flowables.append(Paragraph(inline_md(line[4:]), styles["h3"]))
            i += 1
            continue

        # H4
        if line.startswith("#### "):
            flowables.append(Paragraph(inline_md(line[5:]), styles["h4"]))
            i += 1
            continue

        # HR
        if re.match(r"^---+\s*$", line):
            flowables.append(Spacer(1, 4))
            flowables.append(HRFlowable(
                width="100%", thickness=1,
                color=colors.HexColor("#1a3a5c"), spaceAfter=6
            ))
            i += 1
            continue

        # Tabella
        if line.startswith("|"):
            table_lines = []
            while i < len(lines) and lines[i].startswith("|"):
                table_lines.append(lines[i])
                i += 1
            t = parse_table(table_lines, styles)
            if t:
                flowables.append(Spacer(1, 6))
                flowables.append(t)
                flowables.append(Spacer(1, 8))
            continue

        # Blockquote
        if line.startswith("> "):
            bq_lines = []
            while i < len(lines) and lines[i].startswith("> "):
                bq_lines.append(lines[i][2:])
                i += 1
            bq_text = " ".join(bq_lines)
            # Box visivo: tabella 1x1
            t = Table(
                [[Paragraph(inline_md(bq_text), styles["blockquote"])]],
                colWidths=[A4[0] - 5 * cm]
            )
            t.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f0f4f8")),
                ("LEFTPADDING", (0, 0), (-1, -1), 12),
                ("RIGHTPADDING", (0, 0), (-1, -1), 12),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("LINEBEFORE", (0, 0), (0, -1), 3, colors.HexColor("#1a3a5c")),
            ]))
            flowables.append(Spacer(1, 4))
            flowables.append(t)
            flowables.append(Spacer(1, 4))
            continue

        # Bullet livello 2 (doppio spazio + - o *)
        if re.match(r"^   +[-*] ", line) or re.match(r"^\t[-*] ", line):
            text = re.sub(r"^[ \t]+[-*] ", "", line)
            flowables.append(Paragraph(
                "&#x2013; " + inline_md(text), styles["bullet2"]
            ))
            i += 1
            continue

        # Bullet livello 1
        if re.match(r"^[-*] ", line) or re.match(r"^\d+\. ", line):
            is_numbered = bool(re.match(r"^\d+\.", line))
            if is_numbered:
                num = re.match(r"^(\d+)\. (.*)", line)
                text = f"{num.group(1)}. {num.group(2)}" if num else line
            else:
                text = "&#x2022; " + inline_md(line[2:])
            flowables.append(Paragraph(text if is_numbered else text, styles["bullet"]))
            i += 1
            continue

        # Phone mockup marker
        if line.strip() == "[[[PHONE_MOCKUP]]]":
            flowables.append(PhoneMockup())
            i += 1
            continue

        # Riga vuota
        if line.strip() == "":
            flowables.append(Spacer(1, 4))
            i += 1
            continue

        # Paragrafo normale
        flowables.append(Paragraph(inline_md(line.strip()), styles["body"]))
        i += 1

    return flowables


def group_headings(flowables):
    """Wrap each heading with the following content to prevent orphaned headings."""
    heading_styles = {"h2", "h3", "h4"}
    result = []
    i = 0
    while i < len(flowables):
        f = flowables[i]
        if isinstance(f, Paragraph) and f.style.name in heading_styles:
            group = [f]
            j = i + 1
            while j < len(flowables) and isinstance(flowables[j], Spacer):
                group.append(flowables[j])
                j += 1
            if j < len(flowables) and not isinstance(flowables[j], HRFlowable):
                group.append(flowables[j])
                j += 1
            result.append(KeepTogether(group))
            i = j
        else:
            result.append(f)
            i += 1
    return result


def convert_file(md_path: Path, styles):
    pdf_path = md_path.with_suffix(".pdf")
    doc = SimpleDocTemplate(
        str(pdf_path),
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=2.5 * cm,
        bottomMargin=2.5 * cm,
        title=md_path.stem.replace("-", " ").title(),
        author="Salute Quotidiana",
    )
    md_text = md_path.read_text(encoding="utf-8")
    flowables = md_to_flowables(md_text, styles)
    flowables = group_headings(flowables)
    doc.build(flowables)
    print(f"  OK  {pdf_path.name}")


def main():
    styles = build_styles()
    md_files = sorted(FOLDER.glob("*.md"))
    print(f"Trovati {len(md_files)} file .md\n")
    for md_file in md_files:
        try:
            convert_file(md_file, styles)
        except Exception as e:
            print(f"  ERR {md_file.name}: {e}")
    print("\nConversione completata.")


if __name__ == "__main__":
    main()
