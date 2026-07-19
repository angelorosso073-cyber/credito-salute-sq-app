# -*- coding: utf-8 -*-
"""
Genera salute-quotidiana-investor-deck.pptx  (15 slide, finanziatore)
Poi tenta conversione PDF via win32com (PowerPoint) o LibreOffice.
"""
import sys, io, subprocess, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from pathlib import Path
from pptx import Presentation
from pptx.util import Inches, Pt, Cm, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.oxml.ns import qn
from lxml import etree

# ── Percorsi output ───────────────────────────────────────────────────────────
BASE    = Path(__file__).parent
PPTX_OUT = BASE / "salute-quotidiana-investor-deck.pptx"
PDF_OUT  = BASE / "salute-quotidiana-investor-deck.pdf"

# ── Palette ───────────────────────────────────────────────────────────────────
BLU     = RGBColor(0x1A, 0x3A, 0x5C)   # blu scuro primario
BLU_M   = RGBColor(0x2E, 0x6D, 0xA8)   # blu medio
VERDE   = RGBColor(0x2D, 0x6A, 0x4F)   # verde salute
VERDE_LT= RGBColor(0xD6, 0xEE, 0xE2)   # verde chiaro sfondo
BLU_LT  = RGBColor(0xD6, 0xE4, 0xF0)   # blu chiaro sfondo
GRIGIO  = RGBColor(0x33, 0x33, 0x33)   # testo corpo
G_LIGHT = RGBColor(0xF0, 0xF4, 0xF8)   # sfondo card
G_ROW   = RGBColor(0xE0, 0xE8, 0xF0)   # righe alternate
BIANCO  = RGBColor(0xFF, 0xFF, 0xFF)
ROSSO   = RGBColor(0xC0, 0x39, 0x2B)   # perdita
AMBRA   = RGBColor(0xB7, 0x77, 0x0D)   # warning

FONT = "Calibri"
W    = Inches(13.33)
H    = Inches(7.5)

# ── Posizioni standard ────────────────────────────────────────────────────────
L    = Cm(1.5)
CW   = W - Cm(3.0)
CT   = Cm(2.5)      # content top (dopo header 2cm)
HDR  = Cm(2.0)      # altezza header
FTR  = Cm(0.7)      # altezza footer

# ── Helpers ───────────────────────────────────────────────────────────────────
def new_prs():
    p = Presentation()
    p.slide_width  = W
    p.slide_height = H
    return p

def blank(prs):
    return prs.slides.add_slide(prs.slide_layouts[6])

def rect(slide, x, y, w, h, fill, line=None, lw=None, radius=False):
    if radius:
        from pptx.enum.shapes import MSO_SHAPE_TYPE
        s = slide.shapes.add_shape(5, x, y, w, h)   # rounded rect
    else:
        s = slide.shapes.add_shape(1, x, y, w, h)
    s.fill.solid(); s.fill.fore_color.rgb = fill
    if line:
        s.line.color.rgb = line
        if lw: s.line.width = lw
    else:
        s.line.fill.background()
    return s

def tb(slide, x, y, w, h):
    return slide.shapes.add_textbox(x, y, w, h)

def run(para, text, size, color=GRIGIO, bold=False, italic=False):
    r = para.add_run()
    r.text = text
    r.font.name  = FONT
    r.font.size  = Pt(size)
    r.font.bold  = bold
    r.font.italic = italic
    r.font.color.rgb = color
    return r

def para(tf, text, size, color=GRIGIO, bold=False, italic=False,
         align=PP_ALIGN.LEFT, spc_b=0, spc_a=2, line_pct=100):
    if tf.paragraphs and tf.paragraphs[0].text == '' and not tf.paragraphs[0].runs:
        p = tf.paragraphs[0]
    else:
        p = tf.add_paragraph()
    p.alignment = align
    run(p, text, size, color, bold, italic)
    pPr = p._p.get_or_add_pPr()
    if spc_b:
        sb = etree.SubElement(pPr, qn('a:spcBef'))
        etree.SubElement(sb, qn('a:spcPts')).set('val', str(int(spc_b * 100)))
    if spc_a:
        sa = etree.SubElement(pPr, qn('a:spcAft'))
        etree.SubElement(sa, qn('a:spcPts')).set('val', str(int(spc_a * 100)))
    ln = etree.SubElement(pPr, qn('a:lnSpc'))
    etree.SubElement(ln, qn('a:spcPct')).set('val', str(line_pct * 1000))
    return p

def header_slide(prs, title, subtitle=None):
    slide = blank(prs)
    rect(slide, 0, 0, W, H, G_LIGHT)
    rect(slide, 0, 0, W, HDR, BLU)
    rect(slide, 0, 0, Cm(0.45), H, VERDE)
    # titolo header
    t = tb(slide, Cm(1.2), Cm(0.18), W - Cm(2), HDR)
    tf = t.text_frame; tf.word_wrap = True
    para(tf, title, 22, BIANCO, bold=True, spc_b=0, spc_a=0)
    if subtitle:
        t2 = tb(slide, Cm(1.2), Cm(1.4), W - Cm(2), Cm(0.7))
        tf2 = t2.text_frame
        para(tf2, subtitle, 11, G_ROW, spc_b=0, spc_a=0)
    # footer
    rect(slide, 0, H - FTR, W, FTR, BLU)
    t3 = tb(slide, Cm(1.2), H - FTR + Cm(0.1), W - Cm(2), FTR)
    tf3 = t3.text_frame
    para(tf3, "Credito Salute SQ  ·  Salute Quotidiana  ·  Riservato", 8, BIANCO,
         align=PP_ALIGN.RIGHT, spc_b=0, spc_a=0)
    return slide

def body_tb(slide, top=CT, left=L, width=None, height=None):
    w = width  or CW
    h = height or (H - top - FTR - Cm(0.3))
    t = tb(slide, left, top, w, h)
    t.text_frame.word_wrap = True
    return t.text_frame

def card(slide, x, y, w, h, fill=None, border=None):
    c = rect(slide, x, y, w, h, fill or G_LIGHT, line=border or BLU_LT, lw=Cm(0.04))
    return c

# ── SLIDE 1 — Cover ───────────────────────────────────────────────────────────
def slide_1_cover(prs):
    slide = blank(prs)
    rect(slide, 0, 0, W, H, BLU)
    rect(slide, 0, H - Cm(1.5), W, Cm(1.5), VERDE)
    rect(slide, 0, 0, Cm(0.45), H, VERDE)
    # titolo
    t1 = tb(slide, Cm(2), Cm(1.8), W - Cm(4), Cm(2))
    para(t1.text_frame, "Credito Salute SQ", 48, BIANCO, bold=True)
    # tagline
    t2 = tb(slide, Cm(2), Cm(4.0), W - Cm(4), Cm(1.4))
    para(t2.text_frame,
         "La spesa quotidiana trasformata in accesso alle cure sanitarie a domicilio.",
         16, G_ROW)
    # sottotitolo
    t3 = tb(slide, Cm(2), Cm(5.5), W - Cm(4), Cm(0.8))
    para(t3.text_frame, "Un programma di Salute Quotidiana", 13, VERDE_LT)
    # data
    t4 = tb(slide, Cm(2), H - Cm(2.0), Cm(10), Cm(0.7))
    para(t4.text_frame, "Investor Deck  ·  Luglio 2026", 10, G_ROW)

# ── SLIDE 2 — La Premessa ─────────────────────────────────────────────────────
def slide_2_premessa(prs):
    slide = blank(prs)
    rect(slide, 0, 0, W, H, G_LIGHT)
    rect(slide, 0, 0, W, HDR, BLU)
    rect(slide, 0, 0, Cm(0.45), H, VERDE)
    rect(slide, 0, H - FTR, W, FTR, BLU)

    # header
    t = tb(slide, Cm(1.2), Cm(0.18), W - Cm(2), HDR)
    para(t.text_frame, "Prima di tutto.", 22, BIANCO, bold=True, spc_b=0, spc_a=0)
    t2 = tb(slide, Cm(1.2), Cm(1.4), W - Cm(2), Cm(0.7))
    para(t2.text_frame, "Perch\xe9 esiste Salute Quotidiana", 11, G_ROW, spc_b=0, spc_a=0)

    # testo premessa (condensato, leggibile)
    tf = body_tb(slide, top=CT, left=Cm(2.0), width=CW - Cm(1.0))

    para(tf, "Non siamo nati per competere. Siamo nati per costruire.",
         16, BLU, bold=True, spc_b=0, spc_a=6, line_pct=110)

    para(tf, "Il sistema ha convinto tutti che il profitto personale fosse l’unico motore possibile. "
             "Che il successo di uno significasse la sconfitta di un altro. "
             "Ti dicono che \xe8 sempre stato cos\xec. Che non c’\xe8 alternativa.",
         13, GRIGIO, spc_b=0, spc_a=4, line_pct=120)

    para(tf, "Non \xe8 vero.",
         14, BLU, bold=True, spc_b=2, spc_a=6)

    para(tf, "Per secoli le comunit\xe0 hanno prosperato perch\xe9 le persone hanno scelto di stare dalla stessa parte. "
             "Il macellaio, il farmacista, il bar sotto casa non erano concorrenti — "
             "erano parte dello stesso tessuto. Si reggevano a vicenda. Reggevano il quartiere.",
         13, GRIGIO, spc_b=0, spc_a=4, line_pct=120)

    para(tf, "Salute Quotidiana trasforma ogni acquisto quotidiano in credito per cure sanitarie a domicilio. "
             "Il valore rimane nella comunit\xe0. Nessuno si arricchisce sulle spalle degli altri.",
         13, GRIGIO, spc_b=4, spc_a=4, line_pct=120)

    para(tf, "Aderire non \xe8 una scelta di marketing. \xc8 una scelta di campo.",
         13, BLU, bold=True, spc_b=4, spc_a=4)

    para(tf, "E che quel mondo comincia dal tuo negozio.",
         14, VERDE, bold=True, spc_b=6, spc_a=0)

    # footer
    t3 = tb(slide, Cm(1.2), H - FTR + Cm(0.1), W - Cm(2), FTR)
    para(t3.text_frame, "Credito Salute SQ  ·  Salute Quotidiana  ·  Riservato", 8, BIANCO,
         align=PP_ALIGN.RIGHT, spc_b=0, spc_a=0)

# ── SLIDE 3 — Il Problema ─────────────────────────────────────────────────────
def slide_3_problema(prs):
    slide = header_slide(prs, "Il problema", "Tre fratture nel sistema")

    stats = [
        ("1 su 3", "italiani rinuncia a curarsi\nper costi o tempi di attesa", BLU),
        ("60–180", "giorni di attesa media SSN\nper una visita specialistica", BLU_M),
        ("€ 12 mld", "spesi ogni anno in promozione\nlocale senza effetto misurabile", VERDE),
    ]
    col_w = CW / 3 - Cm(0.3)
    for i, (num, desc, col) in enumerate(stats):
        x = L + i * (col_w + Cm(0.45))
        card(slide, x, CT, col_w, H - CT - FTR - Cm(0.4))
        rect(slide, x, CT, col_w, Cm(0.5), col)

        t1 = tb(slide, x + Cm(0.3), CT + Cm(0.7), col_w - Cm(0.6), Cm(1.8))
        para(t1.text_frame, num, 36, col, bold=True, align=PP_ALIGN.CENTER, spc_b=0, spc_a=0)

        t2 = tb(slide, x + Cm(0.3), CT + Cm(2.6), col_w - Cm(0.6),
                H - CT - FTR - Cm(3.5))
        tf2 = t2.text_frame; tf2.word_wrap = True
        para(tf2, desc, 13, GRIGIO, align=PP_ALIGN.CENTER, line_pct=120, spc_b=0, spc_a=0)

    # insight finale
    ty = H - FTR - Cm(1.6)
    t = tb(slide, L, ty, CW, Cm(1.2))
    para(t.text_frame,
         "C’\xe8 un modo per collegare queste due realt\xe0: "
         "il budget promozionale degli esercizi locali e il bisogno di salute delle famiglie.",
         13, VERDE, bold=True, align=PP_ALIGN.CENTER, spc_b=0, spc_a=0)

# ── SLIDE 4 — La Soluzione ────────────────────────────────────────────────────
def slide_4_soluzione(prs):
    slide = header_slide(prs, "La soluzione", "Il budget promozionale diventa qualcosa che dura")
    tf = body_tb(slide)

    para(tf, "L’esercizio commerciale destina una quota del proprio budget promozionale "
             "a un fondo gestito da Salute Quotidiana.",
         14, GRIGIO, spc_b=0, spc_a=6, line_pct=120)

    para(tf, "I clienti accumulano Credito SQ con gli acquisti abituali. "
             "Il credito \xe8 spendibile su prestazioni infermieristiche a domicilio.",
         14, GRIGIO, spc_b=0, spc_a=10, line_pct=120)

    para(tf, "Nessun gadget. Nessun volantino.", 16, BLU, bold=True, spc_b=0, spc_a=4)
    para(tf, "Un beneficio concreto, spendibile, vicino alla vita reale delle persone.",
         16, BLU, bold=True, spc_b=0, spc_a=14)

    # flusso visivo
    steps = ["Acquisto\nquotidiano", "15% della\nspesa → Credito", "Prenota\nprestazione", "Infermiere\na domicilio"]
    cols  = [BLU, BLU_M, VERDE, VERDE]
    sw    = CW / 5
    sy    = H - FTR - Cm(2.2)
    sh    = Cm(1.8)
    for i, (step, col) in enumerate(zip(steps, cols)):
        x = L + i * (sw + Cm(0.15))
        rect(slide, x, sy, sw - Cm(0.1), sh, col)
        t = tb(slide, x + Cm(0.1), sy + Cm(0.15), sw - Cm(0.2), sh - Cm(0.2))
        para(t.text_frame, step, 11, BIANCO, bold=True,
             align=PP_ALIGN.CENTER, spc_b=0, spc_a=0, line_pct=110)
        if i < len(steps) - 1:
            ax = x + sw
            t2 = tb(slide, ax, sy + Cm(0.6), Cm(0.2), Cm(0.6))
            para(t2.text_frame, "▶", 10, BLU_M,
                 align=PP_ALIGN.CENTER, spc_b=0, spc_a=0)

# ── SLIDE 5 — Come Funziona ───────────────────────────────────────────────────
def slide_5_come_funziona(prs):
    slide = header_slide(prs, "Come funziona", "Tre ruoli. Un meccanismo semplice.")

    roles = [
        ("Esercizio\ncommerciale", [
            "Stanzia il fondo promozionale",
            "Espone il materiale informativo",
            "Invita i clienti a partecipare",
            "Non gestisce nulla di sanitario",
        ], BLU),
        ("Cliente", [
            "Si iscrive alla piattaforma",
            "Carica gli scontrini via browser",
            "Accumula Credito SQ verificato",
            "Usa il credito per le prestazioni",
        ], BLU_M),
        ("Salute Quotidiana", [
            "Gestisce iscrizioni e verifiche",
            "Amministra il fondo",
            "Organizza le prestazioni",
            "Produce il report per l’esercizio",
        ], VERDE),
    ]

    col_w = CW / 3 - Cm(0.3)
    for i, (title, items, col) in enumerate(roles):
        x = L + i * (col_w + Cm(0.45))
        rect(slide, x, CT, col_w, Cm(1.0), col)
        t = tb(slide, x + Cm(0.2), CT + Cm(0.1), col_w - Cm(0.4), Cm(0.85))
        para(t.text_frame, title, 12, BIANCO, bold=True,
             align=PP_ALIGN.CENTER, spc_b=0, spc_a=0, line_pct=100)

        body_y = CT + Cm(1.1)
        body_h = H - body_y - FTR - Cm(0.4)
        card(slide, x, body_y, col_w, body_h)
        tf = body_tb(slide, top=body_y + Cm(0.25), left=x + Cm(0.25),
                     width=col_w - Cm(0.5), height=body_h - Cm(0.5))
        for j, item in enumerate(items):
            para(tf, "•  " + item, 13, GRIGIO,
                 spc_b=0, spc_a=5, line_pct=110)

# ── SLIDE 6 — Le Prestazioni ──────────────────────────────────────────────────
def slide_6_prestazioni(prs):
    slide = header_slide(prs, "Le prestazioni", "Tutto ci\xf2 che si pu\xf2 fare con il Credito SQ")

    headers = ["Prestazione", "Costo"]
    rows_inf = [
        ("Iniezione intramuscolare I.M. (su prescrizione)", "8 €"),
        ("Prelievo ematico periferico", "10 €"),
        ("Medicazione semplice", "13 €"),
        ("Controllo parametri di base + educazione sanitaria", "16 €"),
        ("Prelievo arterioso", "20 €"),
        ("Gestione medicazione tracheostomia", "30 €"),
    ]
    rows_tele = [
        ("ECG a 12 derivazioni (telemedicina)", "25 €"),
        ("Holter ECG 24h", "45 €"),
        ("Holter Pressorio 24h", "40 €"),
        ("Spirometria semplice", "30 €"),
    ]

    def draw_table(slide, rows, top, left=L, width=CW, hdr_color=BLU):
        row_h = Cm(0.6)
        col_widths = [width * 0.78, width * 0.22]
        # header
        rect(slide, left, top, width, row_h, hdr_color)
        for ci, hdr in enumerate(headers):
            tx = left + sum(col_widths[:ci])
            t = tb(slide, tx + Cm(0.1), top + Cm(0.08), col_widths[ci] - Cm(0.1), row_h)
            para(t.text_frame, hdr, 10, BIANCO, bold=True, spc_b=0, spc_a=0)
        # rows
        for ri, (name, cost) in enumerate(rows):
            ry = top + row_h * (ri + 1)
            bg = G_LIGHT if ri % 2 == 0 else BIANCO
            rect(slide, left, ry, width, row_h, bg)
            # col 0
            t0 = tb(slide, left + Cm(0.1), ry + Cm(0.08),
                    col_widths[0] - Cm(0.2), row_h)
            para(t0.text_frame, name, 11, GRIGIO, spc_b=0, spc_a=0)
            # col 1
            t1 = tb(slide, left + col_widths[0], ry + Cm(0.08),
                    col_widths[1] - Cm(0.1), row_h)
            para(t1.text_frame, cost, 11, BLU, bold=True,
                 align=PP_ALIGN.CENTER, spc_b=0, spc_a=0)

    # etichette sezione
    tl = tb(slide, L, CT, CW * 0.5, Cm(0.5))
    para(tl.text_frame, "Prestazioni infermieristiche a domicilio", 11, BLU, bold=True, spc_b=0, spc_a=0)

    draw_table(slide, rows_inf, top=CT + Cm(0.55), left=L, width=CW * 0.5 - Cm(0.3))

    tl2 = tb(slide, L + CW * 0.5 + Cm(0.3), CT, CW * 0.5, Cm(0.5))
    para(tl2.text_frame, "Telemedicina a domicilio (in arrivo)", 11, VERDE, bold=True, spc_b=0, spc_a=0)
    draw_table(slide, rows_tele, top=CT + Cm(0.55),
               left=L + CW * 0.5 + Cm(0.3), width=CW * 0.5 - Cm(0.3),
               hdr_color=VERDE)

# ── SLIDE 7 — Business Model ─────────────────────────────────────────────────
def slide_7_business(prs):
    slide = header_slide(prs, "Modello di business", "Come genera valore per tutte le parti")

    # Schema flusso denaro
    flow_y = CT + Cm(0.3)
    flow_h = Cm(1.1)
    flows = [
        ("Esercente\nversa il fondo", BLU,   L),
        ("20% → Salute\nQuotidiana", VERDE, L + CW * 0.33),
        ("80% →\nProfessionista", BLU_M, L + CW * 0.66),
    ]
    for label, col, x in flows:
        fw = CW / 3 - Cm(0.3)
        rect(slide, x, flow_y, fw, flow_h, col)
        t = tb(slide, x + Cm(0.15), flow_y + Cm(0.1), fw - Cm(0.3), flow_h)
        para(t.text_frame, label, 12, BIANCO, bold=True,
             align=PP_ALIGN.CENTER, spc_b=0, spc_a=0, line_pct=100)

    # unit economics
    ue_y = flow_y + flow_h + Cm(0.6)
    cards = [
        ("Fondo tipico\nper esercente/ciclo", "1.000 €", "fisso, zero variabile", BLU),
        ("Ricavo SQ\nper esercente/mese", "150 €", "media su utilizzo 75%", VERDE),
        ("Ciclo\nstandard", "30 giorni", "renovabile ogni mese", BLU_M),
        ("Clienti per\nciclo pilot", "20", "scalabile senza limite", BLU_M),
    ]
    cw2 = CW / 4 - Cm(0.25)
    for i, (lbl, val, note, col) in enumerate(cards):
        cx = L + i * (cw2 + Cm(0.33))
        card(slide, cx, ue_y, cw2, H - ue_y - FTR - Cm(0.4))
        rect(slide, cx, ue_y, cw2, Cm(0.35), col)
        t1 = tb(slide, cx + Cm(0.2), ue_y + Cm(0.5), cw2 - Cm(0.4), Cm(1.3))
        para(t1.text_frame, lbl, 11, GRIGIO, spc_b=0, spc_a=0, line_pct=110)
        t2 = tb(slide, cx + Cm(0.2), ue_y + Cm(1.9), cw2 - Cm(0.4), Cm(1.0))
        para(t2.text_frame, val, 20, col, bold=True,
             align=PP_ALIGN.CENTER, spc_b=0, spc_a=0)
        t3 = tb(slide, cx + Cm(0.2), ue_y + Cm(3.0), cw2 - Cm(0.4),
                H - ue_y - FTR - Cm(3.8))
        para(t3.text_frame, note, 10, GRIGIO,
             italic=True, align=PP_ALIGN.CENTER, spc_b=0, spc_a=0, line_pct=110)

# ── SLIDE 8 — Il Mercato ─────────────────────────────────────────────────────
def slide_8_mercato(prs):
    slide = header_slide(prs, "Il mercato", "TAM / SAM / SOM — Italia")

    market = [
        ("TAM", "Spesa privata sanitaria Italia", "40 mld €/anno",
         "Intero mercato privato: visite, diagnostica, domiciliare.", BLU,   0),
        ("SAM", "Home nursing + Telemedicina",   "2 mld €/anno",
         "Segmento infermieristico domiciliare e telemedicina.", BLU_M, 1),
        ("SOM", "Mercato raggiungibile Y3",       "15 mln €/anno",
         "Esercizi locali partner in Sicilia/Sud Italia, 3–5 anni.", VERDE, 2),
    ]

    bh = (H - CT - FTR - Cm(1.2)) / 3
    for label, title, value, desc, col, i in market:
        by = CT + i * (bh + Cm(0.15))
        # barra colorata sinistra
        rect(slide, L, by, Cm(0.4), bh - Cm(0.1), col)
        # etichetta
        t0 = tb(slide, L + Cm(0.6), by + Cm(0.1), Cm(1.2), bh - Cm(0.2))
        para(t0.text_frame, label, 14, col, bold=True, spc_b=0, spc_a=0)
        # titolo
        t1 = tb(slide, L + Cm(1.9), by + Cm(0.1), CW * 0.4, Cm(0.65))
        para(t1.text_frame, title, 13, BLU, bold=True, spc_b=0, spc_a=0)
        # valore
        t2 = tb(slide, L + CW * 0.5, by + Cm(0.05), CW * 0.25, Cm(0.75))
        para(t2.text_frame, value, 16, col, bold=True,
             align=PP_ALIGN.RIGHT, spc_b=0, spc_a=0)
        # descrizione
        t3 = tb(slide, L + Cm(1.9), by + Cm(0.85), CW - Cm(1.4), bh - Cm(1.0))
        para(t3.text_frame, desc, 12, GRIGIO, spc_b=0, spc_a=0, line_pct=110)

    # nota
    tn = tb(slide, L, H - FTR - Cm(0.9), CW, Cm(0.7))
    para(tn.text_frame,
         "Obiettivo Anno 3: 60 esercenti attivi → €108.000 ricavi SQ (0,72% del SOM)",
         11, VERDE, bold=True, spc_b=0, spc_a=0)

# ── SLIDE 9 — La Piattaforma ─────────────────────────────────────────────────
def slide_9_piattaforma(prs):
    slide = header_slide(prs, "La piattaforma", "Web app operativa — nessuna installazione richiesta")

    # testo sinistra
    tf = body_tb(slide, left=L, width=CW * 0.42, top=CT)
    para(tf, "Il sistema \xe8 gi\xe0 operativo.", 14, BLU, bold=True, spc_b=0, spc_a=6)
    para(tf, "Accessibile da qualsiasi smartphone via browser.", 13, GRIGIO, spc_b=0, spc_a=4)
    para(tf, "Tre viste dedicate:", 12, GRIGIO, bold=True, spc_b=4, spc_a=4)
    for item in [
        "•  Cliente — saldo, scontrini, prenotazione",
        "•  Esercente — report, clienti, fondo",
        "•  Admin SQ — validazioni, analytics",
    ]:
        para(tf, item, 12, GRIGIO, spc_b=0, spc_a=3, line_pct=110)

    para(tf, "Stack: Next.js 14 + Supabase (PostgreSQL)", 11, BLU_M, italic=True, spc_b=8, spc_a=2)
    para(tf, "Deploy: Vercel (SLA 99,9%)", 11, BLU_M, italic=True, spc_b=0, spc_a=0)

    # 3 schermate mockup (destra)
    SCR_X0 = L + CW * 0.45
    SCR_TOTAL_W = W - SCR_X0 - Cm(1.0)
    SCR_H = H - CT - FTR - Cm(0.6)
    GAP = Cm(0.25)
    SW  = (SCR_TOTAL_W - GAP * 2) / 3

    screens = [
        ("WALLET", [
            ("Saldo: 12,50 Credito SQ",   BLU,    True,  False),
            ("In verifica: 3,50",          AMBRA,  False, True),
            ("",                           BIANCO, False, False),
            ("CARICA SCONTRINO",           BIANCO, True,  False),
            ("",                           BIANCO, False, False),
            ("Farmacia  +2,40 SQ",         GRIGIO, False, False),
            ("Bar       +0,80 SQ",         GRIGIO, False, False),
            ("Supermercato +1,50 SQ",      GRIGIO, False, False),
        ], BLU),
        ("PRENOTA", [
            ("Saldo: 12,50 SQ",           BLU,    True,  False),
            ("",                           BIANCO, False, False),
            ("✓ Iniezione I.M.   8 SQ",  VERDE,  True,  False),
            ("✓ Prelievo        10 SQ",   VERDE,  True,  False),
            ("✓ Medicazione     13 SQ",   VERDE,  True,  False),
            ("  Controllo       16 SQ",   GRIGIO, False, False),
            ("  Prelievo art.   20 SQ",   GRIGIO, False, False),
            ("",                           BIANCO, False, False),
            ("PRENOTA",                    BIANCO, True,  False),
        ], BLU_M),
        ("CONFERMA", [
            ("✓  Confermata!",              VERDE,  True,  False),
            ("",                            BIANCO, False, False),
            ("Prelievo periferico",         BLU,    True,  False),
            ("Infermiere: Mario R.",        GRIGIO, False, False),
            ("",                            BIANCO, False, False),
            ("Mer 16/03  —  ore 09:30",    GRIGIO, False, False),
            ("A domicilio",                 GRIGIO, False, False),
            ("",                            BIANCO, False, False),
            ("Usati: 10 SQ  |  Residuo: 2,50", VERDE, True, False),
        ], VERDE),
    ]

    HDR_H = Cm(0.55)
    ROW_H_BASE = (SCR_H - HDR_H) / 9.5

    for i, (label, rows, col) in enumerate(screens):
        sx = SCR_X0 + i * (SW + GAP)
        # frame
        s = slide.shapes.add_shape(1, sx, CT, SW, SCR_H)
        s.fill.solid(); s.fill.fore_color.rgb = BIANCO
        s.line.color.rgb = col; s.line.width = Cm(0.05)
        # header
        rect(slide, sx, CT, SW, HDR_H, col)
        th = tb(slide, sx + Cm(0.1), CT + Cm(0.08), SW - Cm(0.2), HDR_H)
        para(th.text_frame, label, 7, BIANCO, bold=True,
             align=PP_ALIGN.CENTER, spc_b=0, spc_a=0)
        # rows
        ry = CT + HDR_H + Cm(0.1)
        for txt, tc, bold, badge in rows:
            if not txt:
                ry += ROW_H_BASE * 0.4
                continue
            bg = VERDE_LT if (tc == VERDE and bold) else (BLU_LT if (tc == BLU and bold) else BIANCO)
            if "CARICA" in txt or "PRENOTA" in txt:
                bg = col; tc = BIANCO
            rect(slide, sx + Cm(0.08), ry, SW - Cm(0.16), ROW_H_BASE, bg)
            tr = tb(slide, sx + Cm(0.15), ry + Cm(0.05), SW - Cm(0.3), ROW_H_BASE)
            para(tr.text_frame, txt, 6.5, tc, bold=bold,
                 align=PP_ALIGN.CENTER if ("CARICA" in txt or "PRENOTA" in txt or "✓  C" in txt) else PP_ALIGN.LEFT,
                 spc_b=0, spc_a=0)
            ry += ROW_H_BASE

# ── SLIDE 10 — Il Pilot ──────────────────────────────────────────────────────
def slide_10_pilot(prs):
    slide = header_slide(prs, "Il pilot", "Dati reali da un test reale")

    # 4 parametri in riga
    params = [
        ("1", "esercizio\ncommerciale", BLU),
        ("20", "clienti\nper ciclo", BLU_M),
        ("30", "giorni\ndi durata", VERDE),
        ("1.000 €", "fondo\nstanziato", VERDE),
    ]
    pw = CW / 4 - Cm(0.3)
    ph = Cm(2.5)
    for i, (val, lbl, col) in enumerate(params):
        px = L + i * (pw + Cm(0.4))
        rect(slide, px, CT, pw, ph, col)
        tv = tb(slide, px + Cm(0.15), CT + Cm(0.2), pw - Cm(0.3), Cm(1.2))
        para(tv.text_frame, val, 28, BIANCO, bold=True,
             align=PP_ALIGN.CENTER, spc_b=0, spc_a=0)
        tl = tb(slide, px + Cm(0.15), CT + Cm(1.5), pw - Cm(0.3), Cm(0.9))
        para(tl.text_frame, lbl, 11, BIANCO,
             align=PP_ALIGN.CENTER, spc_b=0, spc_a=0, line_pct=100)

    tf = body_tb(slide, top=CT + ph + Cm(0.5))
    para(tf, "Il pilot produce dati concreti:", 14, BLU, bold=True, spc_b=0, spc_a=6)
    for item in [
        "quanti clienti si iscrivono e con quale velocit\xe0",
        "quanto credito accumulano e in che tempi",
        "quali prestazioni scelgono con maggiore frequenza",
        "tasso di utilizzo del credito accumulato",
    ]:
        para(tf, "•  " + item, 13, GRIGIO, spc_b=0, spc_a=4, line_pct=110)

    para(tf, "Il rischio \xe8 contenuto e definito. "
             "Il fondo stanziato \xe8 il massimo esponibile. "
             "Nessun costo variabile aperto.",
         13, VERDE, bold=True, spc_b=10, spc_a=0)

# ── SLIDE 11 — Proiezioni Finanziarie ────────────────────────────────────────
def slide_11_proiezioni(prs):
    slide = header_slide(prs, "Proiezioni finanziarie", "3 anni — scenario base")

    # tabella proiezioni
    headers_f = ["", "Anno 1", "Anno 2", "Anno 3"]
    rows_f = [
        ("Esercenti attivi (media)",  "3",       "20",       "60"),
        ("Fondi gestiti",             "36.000 €",  "240.000 €", "720.000 €"),
        ("Ricavi SQ (20%)",           "7.200 €",   "48.000 €",  "144.000 €"),
        ("Costi operativi",           "17.000 €",  "28.000 €",   "55.000 €"),
        ("EBITDA",                    "−9.800 €", "+20.000 €", "+89.000 €"),
    ]

    row_h = Cm(0.75)
    col_w = [CW * 0.34, CW * 0.22, CW * 0.22, CW * 0.22]
    table_y = CT

    # header tabella
    rect(slide, L, table_y, CW, row_h, BLU)
    cx = L
    for ci, hdr in enumerate(headers_f):
        t = tb(slide, cx + Cm(0.1), table_y + Cm(0.12), col_w[ci] - Cm(0.1), row_h)
        para(t.text_frame, hdr, 11, BIANCO, bold=True,
             align=PP_ALIGN.CENTER if ci > 0 else PP_ALIGN.LEFT, spc_b=0, spc_a=0)
        cx += col_w[ci]

    for ri, (label, *vals) in enumerate(rows_f):
        ry = table_y + row_h * (ri + 1)
        bg = G_LIGHT if ri % 2 == 0 else BIANCO
        is_ebitda = label == "EBITDA"
        if is_ebitda:
            bg = VERDE_LT
        rect(slide, L, ry, CW, row_h, bg)
        # label
        t0 = tb(slide, L + Cm(0.15), ry + Cm(0.12), col_w[0] - Cm(0.2), row_h)
        para(t0.text_frame, label, 12 if not is_ebitda else 13,
             BLU if not is_ebitda else VERDE,
             bold=is_ebitda, spc_b=0, spc_a=0)
        # valori
        cx = L + col_w[0]
        for ci, val in enumerate(vals):
            t_v = tb(slide, cx + Cm(0.1), ry + Cm(0.12), col_w[ci + 1] - Cm(0.2), row_h)
            is_neg = val.startswith("−")
            color = ROSSO if is_neg else (VERDE if is_ebitda else GRIGIO)
            para(t_v.text_frame, val, 12 if not is_ebitda else 13,
                 color, bold=is_ebitda,
                 align=PP_ALIGN.CENTER, spc_b=0, spc_a=0)
            cx += col_w[ci + 1]

    # note
    note_y = table_y + row_h * 6 + Cm(0.4)
    notes = [
        ("●  Breakeven previsto: Q3 Anno 2 (~mese 20)",   VERDE),
        ("●  Nessun costo variabile aperto: rischio cap to fondo stanziato", BLU),
        ("●  Scenario conservativo: 70% utilizzo crediti, 1 ciclo/mese/esercente", GRIGIO),
    ]
    for note, col in notes:
        tn = tb(slide, L, note_y, CW, Cm(0.5))
        para(tn.text_frame, note, 11, col, spc_b=0, spc_a=0)
        note_y += Cm(0.55)

# ── SLIDE 12 — Uso dei Fondi ─────────────────────────────────────────────────
def slide_12_fondi(prs):
    slide = header_slide(prs, "Richiesta di investimento", "Seed round — 20.000 €")

    # titolo importo
    t_big = tb(slide, L, CT, CW * 0.4, Cm(1.6))
    para(t_big.text_frame, "20.000 €", 40, BLU, bold=True, spc_b=0, spc_a=0)
    t_sub = tb(slide, L, CT + Cm(1.7), CW * 0.4, Cm(0.6))
    para(t_sub.text_frame, "seed round  —  equity o revenue share", 12, GRIGIO, spc_b=0, spc_a=0)

    # uso fondi (4 card)
    allocations = [
        ("Tech & MVP", "5.000 €", "25%",
         "Sviluppo web app, integrazione Supabase, testing.", BLU),
        ("Operativit\xe0 Y1", "10.000 €", "50%",
         "Gestione pilot, coordinamento professionisti, admin.", VERDE),
        ("Marketing & BD", "3.500 €", "17,5%",
         "Acquisizione esercenti partner, materiali, eventi.", BLU_M),
        ("Contingency", "1.500 €", "7,5%",
         "Riserva operativa per imprevisti del primo ciclo.", GRIGIO),
    ]

    fw = CW / 4 - Cm(0.3)
    for i, (title, amount, pct, desc, col) in enumerate(allocations):
        fx = L + i * (fw + Cm(0.4))
        fy = CT + Cm(2.3)
        fh = H - fy - FTR - Cm(0.5)
        card(slide, fx, fy, fw, fh)
        rect(slide, fx, fy, fw, Cm(0.35), col)

        t1 = tb(slide, fx + Cm(0.2), fy + Cm(0.5), fw - Cm(0.4), Cm(0.55))
        para(t1.text_frame, title, 12, col, bold=True, spc_b=0, spc_a=0)

        t2 = tb(slide, fx + Cm(0.2), fy + Cm(1.1), fw - Cm(0.4), Cm(0.85))
        para(t2.text_frame, amount, 18, col, bold=True,
             align=PP_ALIGN.CENTER, spc_b=0, spc_a=0)

        t3 = tb(slide, fx + Cm(0.2), fy + Cm(2.1), fw - Cm(0.4), Cm(0.5))
        para(t3.text_frame, pct, 14, GRIGIO,
             align=PP_ALIGN.CENTER, spc_b=0, spc_a=0)

        t4 = tb(slide, fx + Cm(0.2), fy + Cm(2.8), fw - Cm(0.4), fh - Cm(3.0))
        t4.text_frame.word_wrap = True
        para(t4.text_frame, desc, 11, GRIGIO, spc_b=0, spc_a=0, line_pct=110)

    # ROI investor
    roi_y = H - FTR - Cm(0.8)
    tr = tb(slide, L, roi_y, CW, Cm(0.65))
    para(tr.text_frame,
         "ROI stimato per investitore al 20% equity:  "
         "valutazione Y3 ≈ €1.08M  →  quota = €216.000  →  ~10x in 3 anni",
         12, VERDE, bold=True, align=PP_ALIGN.CENTER, spc_b=0, spc_a=0)

# ── SLIDE 13 — Roadmap ───────────────────────────────────────────────────────
def slide_13_roadmap(prs):
    slide = header_slide(prs, "Roadmap", "Dal pilot alla scala")

    milestones = [
        ("Q3 2026", "Pilot", [
            "1 esercente, 20 clienti",
            "30 giorni, fondo €1.000",
            "Raccolta dati reali",
        ], BLU),
        ("Q4 2026", "Early Traction", [
            "3–5 esercenti attivi",
            "Ottimizzazione onboarding",
            "Report validazione modello",
        ], BLU_M),
        ("2027", "Espansione", [
            "20 esercenti in Sicilia",
            "Aggiunta telemedicina",
            "Breakeven Q2 2027",
        ], VERDE),
        ("2028", "Scala", [
            "60+ esercenti Sud Italia",
            "Partnership sanitarie",
            "Ricavi €144.000",
        ], VERDE),
    ]

    mw = CW / 4 - Cm(0.3)
    for i, (period, title, items, col) in enumerate(milestones):
        mx = L + i * (mw + Cm(0.4))
        my = CT
        # linea timeline
        rect(slide, mx, my + Cm(0.35), mw - Cm(0.1), Cm(0.08), col)
        # dot
        dot = slide.shapes.add_shape(9, mx + mw / 2 - Cm(0.25), my + Cm(0.1), Cm(0.5), Cm(0.5))
        dot.fill.solid(); dot.fill.fore_color.rgb = col
        dot.line.fill.background()
        # periodo
        tp = tb(slide, mx, my + Cm(0.65), mw, Cm(0.55))
        para(tp.text_frame, period, 11, col, bold=True,
             align=PP_ALIGN.CENTER, spc_b=0, spc_a=0)
        # card
        card_y = my + Cm(1.25)
        card_h = H - card_y - FTR - Cm(0.4)
        card(slide, mx, card_y, mw, card_h)
        rect(slide, mx, card_y, mw, Cm(0.6), col)
        tt = tb(slide, mx + Cm(0.15), card_y + Cm(0.08), mw - Cm(0.3), Cm(0.5))
        para(tt.text_frame, title, 12, BIANCO, bold=True,
             align=PP_ALIGN.CENTER, spc_b=0, spc_a=0)
        tf = body_tb(slide, top=card_y + Cm(0.75), left=mx + Cm(0.15),
                     width=mw - Cm(0.3), height=card_h - Cm(0.9))
        for item in items:
            para(tf, "•  " + item, 12, GRIGIO, spc_b=0, spc_a=5, line_pct=110)

# ── SLIDE 14 — Il Team ───────────────────────────────────────────────────────
def slide_14_team(prs):
    slide = header_slide(prs, "Il team", "Chi c’\xe8 dietro Salute Quotidiana")

    # founder card
    card(slide, L, CT, CW * 0.45, H - CT - FTR - Cm(0.5))
    rect(slide, L, CT, CW * 0.45, Cm(0.45), BLU)

    tf = body_tb(slide, top=CT + Cm(0.6), left=L + Cm(0.3),
                 width=CW * 0.45 - Cm(0.6))
    para(tf, "Angelo Rosso", 18, BLU, bold=True, spc_b=0, spc_a=4)
    para(tf, "Fondatore & CEO", 13, VERDE, bold=True, spc_b=0, spc_a=8)
    for item in [
        "Professionista sanitario con esperienza diretta sul territorio",
        "Conoscenza operativa del sistema infermieristico domiciliare",
        "Sviluppo digitale: architettura web app Credito SQ",
        "Focus: Sicilia orientale (Francofonte, Lentini, Carlentini)",
    ]:
        para(tf, "•  " + item, 13, GRIGIO, spc_b=0, spc_a=5, line_pct=115)

    # ricerca advisor
    card(slide, L + CW * 0.48, CT, CW * 0.52, H - CT - FTR - Cm(0.5))
    rect(slide, L + CW * 0.48, CT, CW * 0.52, Cm(0.45), BLU_M)

    tf2 = body_tb(slide, top=CT + Cm(0.6), left=L + CW * 0.48 + Cm(0.3),
                  width=CW * 0.52 - Cm(0.6))
    para(tf2, "Profili in ricerca", 14, BLU_M, bold=True, spc_b=0, spc_a=8)
    for role in [
        ("CFO / Advisor finanziario", "gestione fondi, reporting investitore"),
        ("Partnership manager", "acquisizione esercenti, contratti"),
        ("Clinical supervisor", "supervisione qualit\xe0 prestazioni"),
    ]:
        para(tf2, role[0], 13, BLU_M, bold=True, spc_b=4, spc_a=1)
        para(tf2, role[1], 12, GRIGIO, spc_b=0, spc_a=4)

# ── SLIDE 15 — Chiusura ──────────────────────────────────────────────────────
def slide_15_chiusura(prs):
    slide = blank(prs)
    rect(slide, 0, 0, W, H, BLU)
    rect(slide, 0, H - Cm(1.5), W, Cm(1.5), VERDE)
    rect(slide, 0, 0, Cm(0.45), H, VERDE)

    t1 = tb(slide, Cm(2), Cm(1.5), W - Cm(4), Cm(2.0))
    para(t1.text_frame,
         "Un modo diverso di stare nel mercato.", 32, BIANCO, bold=True,
         spc_b=0, spc_a=0)

    t2 = tb(slide, Cm(2), Cm(3.8), W - Cm(4), Cm(1.6))
    t2.text_frame.word_wrap = True
    para(t2.text_frame,
         "Non serve spendere di pi\xf9. "
         "Serve spendere in modo che le persone ricordino — "
         "e che faccia qualcosa di concreto per la comunit\xe0 in cui si lavora.",
         14, G_ROW, spc_b=0, spc_a=0, line_pct=130)

    # CTA
    for i, (label, val) in enumerate([
        ("Email", "angelo.rosso073@gmail.com"),
        ("Programma", "Credito Salute SQ · Luglio 2026"),
        ("Pilot disponibile", "da subito — rischio zero"),
    ]):
        ey = Cm(5.6) + i * Cm(0.85)
        tl = tb(slide, Cm(2), ey, Cm(4.5), Cm(0.7))
        para(tl.text_frame, label + ":", 12, VERDE_LT, bold=True, spc_b=0, spc_a=0)
        tv = tb(slide, Cm(6.8), ey, W - Cm(8), Cm(0.7))
        para(tv.text_frame, val, 12, BIANCO, spc_b=0, spc_a=0)

    t3 = tb(slide, Cm(2), H - Cm(2.4), Cm(8), Cm(0.8))
    para(t3.text_frame, "Credito Salute SQ · Salute Quotidiana",
         14, VERDE, bold=True, spc_b=0, spc_a=0)

# ── Conversione PDF ───────────────────────────────────────────────────────────
def convert_to_pdf(pptx_path: Path, pdf_path: Path):
    # Tentativo 1: LibreOffice
    for soffice in ["soffice", "libreoffice",
                    r"C:\Program Files\LibreOffice\program\soffice.exe",
                    r"C:\Program Files (x86)\LibreOffice\program\soffice.exe"]:
        try:
            r = subprocess.run(
                [soffice, "--headless", "--convert-to", "pdf",
                 "--outdir", str(pdf_path.parent), str(pptx_path)],
                capture_output=True, timeout=60
            )
            if r.returncode == 0 and pdf_path.exists():
                print(f"PDF (LibreOffice): {pdf_path.name}")
                return True
        except (FileNotFoundError, subprocess.TimeoutExpired):
            continue

    # Tentativo 2: PowerPoint COM (Windows)
    try:
        import comtypes.client
        ppt = comtypes.client.CreateObject("Powerpoint.Application")
        ppt.Visible = 1
        deck = ppt.Presentations.Open(str(pptx_path.resolve()))
        deck.SaveAs(str(pdf_path.resolve()), 32)  # ppSaveAsPDF
        deck.Close()
        ppt.Quit()
        print(f"PDF (PowerPoint COM): {pdf_path.name}")
        return True
    except Exception:
        pass

    # Tentativo 3: win32com
    try:
        import win32com.client
        ppt = win32com.client.Dispatch("Powerpoint.Application")
        ppt.Visible = 1
        deck = ppt.Presentations.Open(str(pptx_path.resolve()))
        deck.SaveAs(str(pdf_path.resolve()), 32)
        deck.Close()
        ppt.Quit()
        print(f"PDF (win32com): {pdf_path.name}")
        return True
    except Exception:
        pass

    print("PDF: nessun convertitore disponibile. Apri il PPTX in PowerPoint e salva come PDF.")
    return False

# ── Main ─────────────────────────────────────────────────────────────────────
def main():
    prs = new_prs()
    slide_1_cover(prs)
    slide_2_premessa(prs)
    slide_3_problema(prs)
    slide_4_soluzione(prs)
    slide_5_come_funziona(prs)
    slide_6_prestazioni(prs)
    slide_7_business(prs)
    slide_8_mercato(prs)
    slide_9_piattaforma(prs)
    slide_10_pilot(prs)
    slide_11_proiezioni(prs)
    slide_12_fondi(prs)
    slide_13_roadmap(prs)
    slide_14_team(prs)
    slide_15_chiusura(prs)

    prs.save(str(PPTX_OUT))
    print(f"PPTX: {PPTX_OUT.name}  ({len(prs.slides)} slide)")

    convert_to_pdf(PPTX_OUT, PDF_OUT)

if __name__ == "__main__":
    main()
