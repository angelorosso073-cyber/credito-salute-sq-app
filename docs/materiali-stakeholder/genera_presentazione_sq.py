# -*- coding: utf-8 -*-
"""
genera_presentazione_sq.py
Credito Salute SQ — Presentazione Commerciale (12 slide, deck-wow)
Widescreen 16:9  |  python-pptx
"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from pathlib import Path
from pptx import Presentation
from pptx.util import Inches, Pt, Cm
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.oxml.ns import qn
from lxml import etree

BASE     = Path(__file__).parent
PPTX_OUT = BASE / "8-presentazione-sq.pptx"

# ── Palette ───────────────────────────────────────────────────────────────────
BLU      = RGBColor(0x1A, 0x3A, 0x5C)
BLU_M    = RGBColor(0x2E, 0x6D, 0xA8)
VERDE    = RGBColor(0x2D, 0x6A, 0x4F)
VERDE_LT = RGBColor(0xD6, 0xEE, 0xE2)
BLU_LT   = RGBColor(0xD6, 0xE4, 0xF0)
GRIGIO   = RGBColor(0x33, 0x33, 0x33)
G_LIGHT  = RGBColor(0xF0, 0xF4, 0xF8)
G_MED    = RGBColor(0xE0, 0xE8, 0xF0)
BIANCO   = RGBColor(0xFF, 0xFF, 0xFF)
MUTED    = RGBColor(0xAA, 0xBB, 0xCC)
ROSSO    = RGBColor(0xB5, 0x2B, 0x2B)

FONT = "Calibri"
W    = Inches(13.33)
H    = Inches(7.5)
L    = Cm(1.5)
CW   = W - Cm(3.0)
CT   = Cm(2.5)
HDR  = Cm(2.0)
FTR  = Cm(0.7)


# ── Core helpers ──────────────────────────────────────────────────────────────

def new_prs():
    p = Presentation()
    p.slide_width  = W
    p.slide_height = H
    return p

def blank(prs):
    return prs.slides.add_slide(prs.slide_layouts[6])

def rect(slide, x, y, w, h, fill, line_color=None, line_w=None):
    s = slide.shapes.add_shape(1, x, y, w, h)
    s.fill.solid(); s.fill.fore_color.rgb = fill
    if line_color:
        s.line.color.rgb = line_color
        if line_w: s.line.width = line_w
    else:
        s.line.fill.background()
    return s

def oval(slide, x, y, w, h, fill):
    s = slide.shapes.add_shape(9, x, y, w, h)
    s.fill.solid(); s.fill.fore_color.rgb = fill
    s.line.fill.background()
    return s

def textbox(slide, x, y, w, h):
    t = slide.shapes.add_textbox(x, y, w, h)
    return t

def para(tf, text, size, color=GRIGIO, bold=False, italic=False,
         align=PP_ALIGN.LEFT, spc_b=0, spc_a=2, line_pct=100):
    if tf.paragraphs and tf.paragraphs[0].text == '' and not tf.paragraphs[0].runs:
        p = tf.paragraphs[0]
    else:
        p = tf.add_paragraph()
    p.alignment = align
    r = p.add_run()
    r.text = text
    r.font.name   = FONT
    r.font.size   = Pt(size)
    r.font.bold   = bold
    r.font.italic = italic
    r.font.color.rgb = color
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

def add_chrome(slide, title, subtitle=None, dark=False):
    """Header bar + verde stripe + footer."""
    bg = BLU if dark else G_LIGHT
    rect(slide, 0, 0, W, H, bg)
    rect(slide, 0, 0, W, HDR, BLU)
    rect(slide, 0, 0, Cm(0.5), H, VERDE)
    rect(slide, 0, H - FTR, W, FTR, BLU)
    t = textbox(slide, Cm(1.3), Cm(0.2), W - Cm(2.5), Cm(1.15))
    para(t.text_frame, title, 22, BIANCO, bold=True, spc_b=0, spc_a=0)
    if subtitle:
        t2 = textbox(slide, Cm(1.3), Cm(1.35), W - Cm(2.5), Cm(0.72))
        para(t2.text_frame, subtitle, 11, G_MED, spc_b=0, spc_a=0)
    tf = textbox(slide, Cm(1.3), H - FTR + Cm(0.08), W - Cm(2.5), FTR)
    para(tf.text_frame, "Credito Salute SQ  \xb7  Salute Quotidiana",
         8, BIANCO, align=PP_ALIGN.RIGHT, spc_b=0, spc_a=0)
    return slide

def header_slide(prs, title, subtitle=None, dark=False):
    slide = blank(prs)
    add_chrome(slide, title, subtitle, dark)
    return slide

def card(slide, x, y, w, h, fill=None):
    c = rect(slide, x, y, w, h, fill or BIANCO)
    c.line.color.rgb = BLU_LT
    c.line.width = Cm(0.04)
    return c

def body_tf(slide, top=CT, left=None, width=None, height=None):
    lft = left if left is not None else L
    w   = width  or CW
    h   = height or (H - top - FTR - Cm(0.4))
    t   = textbox(slide, lft, top, w, h)
    t.text_frame.word_wrap = True
    return t.text_frame


# ── SLIDE 1 — Cover ───────────────────────────────────────────────────────────
def slide_1_cover(prs):
    slide = blank(prs)
    rect(slide, 0, 0, W, H, BLU)
    rect(slide, 0, H - Cm(1.6), W, Cm(1.6), VERDE)
    rect(slide, 0, 0, Cm(0.5), H, VERDE)
    # decorative horizontal accent line
    rect(slide, Cm(2.0), Cm(3.7), Cm(9.0), Cm(0.1), BLU_M)

    t1 = textbox(slide, Cm(2.0), Cm(1.4), W - Cm(4), Cm(2.4))
    para(t1.text_frame, "Credito Salute SQ", 52, BIANCO, bold=True, spc_b=0, spc_a=0)

    t2 = textbox(slide, Cm(2.0), Cm(3.9), W - Cm(5), Cm(1.8))
    t2.text_frame.word_wrap = True
    para(t2.text_frame,
         "La spesa di tutti i giorni diventa accesso\na cure infermieristiche a domicilio.",
         19, G_MED, spc_b=0, spc_a=0, line_pct=125)

    t3 = textbox(slide, Cm(2.0), Cm(5.8), W - Cm(4), Cm(0.8))
    para(t3.text_frame, "Un programma di Salute Quotidiana", 13, VERDE_LT, spc_b=0, spc_a=0)

    t4 = textbox(slide, Cm(2.0), H - Cm(2.2), Cm(8), Cm(0.6))
    para(t4.text_frame, "Luglio 2026", 10, MUTED, spc_b=0, spc_a=0)


# ── SLIDE 2 — Hook: contrasto promozione ──────────────────────────────────────
def slide_2_hook(prs):
    slide = header_slide(prs,
        "Il budget promozionale locale finisce spesso per non lasciare nulla.",
        "Due realt\xe0 che non si sono ancora incrociate.")

    GAP = Cm(0.4)
    CW2 = (CW - GAP) / 2

    # LEFT card — "prima" (muted, problema)
    card_l = card(slide, L, CT, CW2, H - CT - FTR - Cm(0.5), fill=G_MED)
    card_l.line.color.rgb = G_MED

    rect(slide, L, CT, CW2, Cm(0.5), RGBColor(0xCC, 0xDD, 0xEE))
    tl0 = textbox(slide, L + Cm(0.3), CT + Cm(0.05), CW2 - Cm(0.6), Cm(0.45))
    para(tl0.text_frame, "OGGI — PROMOZIONE TRADIZIONALE", 8, BLU_M,
         bold=True, spc_b=0, spc_a=0)

    items_l = [
        ("❌  Gadget che nessuno usa", ROSSO),
        ("❌  Volantini dimenticati il giorno dopo", ROSSO),
        ("❌  Calendari appesi e poi gettati", ROSSO),
        ("❌  Nessuna traccia, nessun ritorno misurabile", ROSSO),
    ]
    y = CT + Cm(0.9)
    for txt, col in items_l:
        ti = textbox(slide, L + Cm(0.4), y, CW2 - Cm(0.8), Cm(0.7))
        para(ti.text_frame, txt, 13, col, spc_b=0, spc_a=0)
        y += Cm(0.85)

    rect(slide, L + Cm(0.4), y + Cm(0.3), CW2 - Cm(0.8), Cm(0.08), BLU_LT)

    tb_l = textbox(slide, L + Cm(0.4), y + Cm(0.6), CW2 - Cm(0.8),
                   H - (y + Cm(0.6)) - FTR - Cm(0.7))
    tb_l.text_frame.word_wrap = True
    para(tb_l.text_frame, "Budget speso.", 15, GRIGIO, bold=True, spc_b=0, spc_a=3)
    para(tb_l.text_frame, "Fidelizzazione zero.", 15, GRIGIO, bold=True, spc_b=0, spc_a=0)

    # CENTER arrow
    ax = L + CW2 + Cm(0.05)
    ay = CT + (H - CT - FTR - Cm(0.5)) / 2 - Cm(0.4)
    ta = textbox(slide, ax, ay, GAP, Cm(0.8))
    para(ta.text_frame, "▶", 18, BLU_M, align=PP_ALIGN.CENTER, spc_b=0, spc_a=0)

    # RIGHT card — "con Credito SQ" (verde, opportunita)
    card_r_x = L + CW2 + GAP
    card_r = card(slide, card_r_x, CT, CW2, H - CT - FTR - Cm(0.5), fill=VERDE_LT)
    card_r.line.color.rgb = VERDE

    rect(slide, card_r_x, CT, CW2, Cm(0.5), VERDE)
    tl0r = textbox(slide, card_r_x + Cm(0.3), CT + Cm(0.05), CW2 - Cm(0.6), Cm(0.45))
    para(tl0r.text_frame, "CON CREDITO SALUTE SQ", 8, BIANCO, bold=True, spc_b=0, spc_a=0)

    items_r = [
        ("✔  Credito reale su cure infermieristiche", VERDE),
        ("✔  Accumulato con acquisti gi\xe0 abituali", VERDE),
        ("✔  Cedibile a chiunque il cliente voglia", VERDE),
        ("✔  Report periodico con dati reali", VERDE),
    ]
    y2 = CT + Cm(0.9)
    for txt, col in items_r:
        ti2 = textbox(slide, card_r_x + Cm(0.4), y2, CW2 - Cm(0.8), Cm(0.7))
        para(ti2.text_frame, txt, 13, col, bold=True, spc_b=0, spc_a=0)
        y2 += Cm(0.85)

    rect(slide, card_r_x + Cm(0.4), y2 + Cm(0.3), CW2 - Cm(0.8), Cm(0.08), VERDE)

    tb_r = textbox(slide, card_r_x + Cm(0.4), y2 + Cm(0.6), CW2 - Cm(0.8),
                   H - (y2 + Cm(0.6)) - FTR - Cm(0.7))
    tb_r.text_frame.word_wrap = True
    para(tb_r.text_frame, "Budget reinvestito.", 15, VERDE, bold=True, spc_b=0, spc_a=3)
    para(tb_r.text_frame, "Fiducia costruita.", 15, VERDE, bold=True, spc_b=0, spc_a=0)


# ── SLIDE 3 — Dark statement: famiglie rimandano cure ─────────────────────────
def slide_3_famiglie(prs):
    slide = blank(prs)
    rect(slide, 0, 0, W, H, BLU)
    rect(slide, 0, 0, Cm(0.5), H, VERDE)
    rect(slide, 0, H - FTR, W, FTR, RGBColor(0x0F, 0x22, 0x38))

    # footer
    tf = textbox(slide, Cm(1.3), H - FTR + Cm(0.08), W - Cm(2.5), FTR)
    para(tf.text_frame, "Credito Salute SQ  \xb7  Salute Quotidiana",
         8, MUTED, align=PP_ALIGN.RIGHT, spc_b=0, spc_a=0)

    # Grandi numeri centrati
    # "1 SU 3" italiani rinuncia a curarsi
    t_big = textbox(slide, L, Cm(1.0), CW * 0.35, Cm(3.5))
    para(t_big.text_frame, "1 su 3", 88, VERDE, bold=True,
         align=PP_ALIGN.CENTER, spc_b=0, spc_a=0)

    t_lbl = textbox(slide, L, Cm(4.3), CW * 0.35, Cm(1.0))
    para(t_lbl.text_frame, "italiani rinuncia\na curarsi", 15, G_MED,
         align=PP_ALIGN.CENTER, spc_b=0, spc_a=0, line_pct=120)

    # Linea verticale divisoria
    rect(slide, L + CW * 0.38, Cm(1.2), Cm(0.06), H - Cm(2.5), BLU_M)

    # Testo destra
    tx = L + CW * 0.42
    tw = CW - CW * 0.42

    t1 = textbox(slide, tx, Cm(1.2), tw, Cm(1.2))
    para(t1.text_frame, "Non per scarsit\xe0 di offerta.", 20, BIANCO,
         bold=True, spc_b=0, spc_a=0)

    t2 = textbox(slide, tx, Cm(2.5), tw, Cm(2.0))
    t2.text_frame.word_wrap = True
    para(t2.text_frame,
         "Per costi, per i tempi di attesa, per la complessit\xe0 "
         "di organizzare anche una prestazione semplice.",
         15, G_MED, spc_b=0, spc_a=0, line_pct=130)

    t3 = textbox(slide, tx, Cm(4.8), tw, Cm(0.8))
    para(t3.text_frame, "Prelievi. Medicazioni. Iniezioni. Controlli di base.",
         14, MUTED, spc_b=0, spc_a=0)

    # Striscia verde con frase chiave
    rect(slide, 0, H - FTR - Cm(1.4), W, Cm(1.4), VERDE)
    t4 = textbox(slide, Cm(1.3), H - FTR - Cm(1.3), W - Cm(2.5), Cm(1.2))
    para(t4.text_frame,
         "Prestazioni tecnicamente semplici. "
         "Chi \xe8 anziano o ha mobilit\xe0 ridotta aspetta pi\xf9 di tutti.",
         14, BIANCO, bold=True, align=PP_ALIGN.CENTER, spc_b=0, spc_a=0)


# ── SLIDE 4 — Dark insight: il budget già esiste ──────────────────────────────
def slide_4_insight(prs):
    slide = blank(prs)
    rect(slide, 0, 0, W, H, BLU)
    rect(slide, 0, 0, Cm(0.5), H, VERDE)
    rect(slide, 0, H - FTR, W, FTR, RGBColor(0x0F, 0x22, 0x38))

    tf = textbox(slide, Cm(1.3), H - FTR + Cm(0.08), W - Cm(2.5), FTR)
    para(tf.text_frame, "Credito Salute SQ  \xb7  Salute Quotidiana",
         8, MUTED, align=PP_ALIGN.RIGHT, spc_b=0, spc_a=0)

    # Titolo grande centrato
    t1 = textbox(slide, L, Cm(0.5), CW, Cm(1.4))
    t1.text_frame.word_wrap = True
    para(t1.text_frame,
         "Il budget promozionale gi\xe0 esiste.", 28, BIANCO, bold=True,
         align=PP_ALIGN.CENTER, spc_b=0, spc_a=0)

    t1b = textbox(slide, L, Cm(1.85), CW, Cm(0.7))
    para(t1b.text_frame, "Mancava solo un posto dove farlo atterrare.",
         18, VERDE_LT, align=PP_ALIGN.CENTER, spc_b=0, spc_a=0)

    # Linea sottile
    rect(slide, L + CW * 0.25, Cm(2.7), CW * 0.5, Cm(0.06), BLU_M)

    # Flow: 3 box + frecce
    BOX_W  = CW * 0.26
    BOX_H  = Cm(2.6)
    BOX_Y  = Cm(3.1)
    ARR_W  = CW * 0.07
    GAP    = (CW - BOX_W * 3 - ARR_W * 2) / 2

    boxes = [
        ("Budget\npromozionale", "gi\xe0 stanziato\ndall'esercizio", BLU_M,
         RGBColor(0x1E, 0x50, 0x80)),
        ("Fondo\nCredito SQ", "gestito da\nSalute Quotidiana", RGBColor(0x1D, 0x4E, 0x35),
         VERDE),
        ("Cura\na domicilio", "per i clienti\ndell'esercizio", VERDE,
         RGBColor(0x14, 0x38, 0x25)),
    ]

    bx = L + GAP / 2
    for i, (title, sub, fill, dark_fill) in enumerate(boxes):
        # box background
        rect(slide, bx, BOX_Y, BOX_W, BOX_H, dark_fill)
        rect(slide, bx, BOX_Y, BOX_W, Cm(0.5), fill)
        # title
        tt = textbox(slide, bx + Cm(0.3), BOX_Y + Cm(0.6), BOX_W - Cm(0.6), Cm(1.2))
        tt.text_frame.word_wrap = True
        para(tt.text_frame, title, 20, BIANCO, bold=True,
             align=PP_ALIGN.CENTER, spc_b=0, spc_a=0, line_pct=110)
        # subtitle
        ts = textbox(slide, bx + Cm(0.3), BOX_Y + Cm(1.9), BOX_W - Cm(0.6), Cm(0.8))
        ts.text_frame.word_wrap = True
        para(ts.text_frame, sub, 11, MUTED, align=PP_ALIGN.CENTER,
             spc_b=0, spc_a=0, line_pct=110)

        if i < 2:
            # arrow between boxes
            ax = bx + BOX_W
            ta = textbox(slide, ax, BOX_Y + Cm(0.9), ARR_W, Cm(0.8))
            para(ta.text_frame, "▶", 22, G_MED,
                 align=PP_ALIGN.CENTER, spc_b=0, spc_a=0)
            bx += BOX_W + ARR_W
        else:
            bx += BOX_W

    # Insight text bottom
    t2 = textbox(slide, L, Cm(6.1), CW, Cm(0.8))
    t2.text_frame.word_wrap = True
    para(t2.text_frame,
         "Il valore resta nel territorio. Nessun intermediario finanziario.",
         14, VERDE_LT, align=PP_ALIGN.CENTER, spc_b=0, spc_a=0)

    # Bottom emphasis bar
    rect(slide, 0, H - FTR - Cm(1.0), W, Cm(1.0), RGBColor(0x0F, 0x22, 0x38))
    t3 = textbox(slide, Cm(1.3), H - FTR - Cm(0.92), W - Cm(2.5), Cm(0.85))
    para(t3.text_frame,
         "Non \xe8 un costo diverso. \xc8 lo stesso budget che arriva dove conta.",
         14, VERDE_LT, bold=True, align=PP_ALIGN.CENTER, spc_b=0, spc_a=0)


# ── SLIDE 5 — Formula: 15% ────────────────────────────────────────────────────
def slide_5_formula(prs):
    slide = header_slide(prs, "15% della spesa diventa credito spendibile su prestazioni reali.",
                         "La formula che rende il programma concreto e misurabile.")

    # Big "15%" left side
    rect(slide, L, CT, CW * 0.30, H - CT - FTR - Cm(0.5), BLU)
    t_pct = textbox(slide, L, CT + Cm(0.5), CW * 0.30, Cm(2.8))
    para(t_pct.text_frame, "15%", 80, BIANCO, bold=True,
         align=PP_ALIGN.CENTER, spc_b=0, spc_a=0)
    t_sub = textbox(slide, L + Cm(0.3), CT + Cm(3.4), CW * 0.30 - Cm(0.6), Cm(1.0))
    t_sub.text_frame.word_wrap = True
    para(t_sub.text_frame, "della spesa\nvalida\n= Credito SQ",
         13, VERDE_LT, align=PP_ALIGN.CENTER,
         spc_b=0, spc_a=0, line_pct=130)

    # Right side: rules + example
    rx = L + CW * 0.33
    rw = CW - CW * 0.33

    rules = [
        ("1 euro SQ  =  1 euro di sconto sulle prestazioni", True),
        ("Cedibile a chiunque, senza vincoli di parentela o convivenza", False),
        ("Il fondo \xe8 fisso all'avvio: nessun costo variabile per l'esercizio", False),
    ]
    ry = CT + Cm(0.2)
    for txt, bold in rules:
        tr = textbox(slide, rx, ry, rw, Cm(0.75))
        tr.text_frame.word_wrap = True
        col = BLU if bold else GRIGIO
        prefix = "•  "
        para(tr.text_frame, prefix + txt, 13, col, bold=bold, spc_b=0, spc_a=0, line_pct=115)
        ry += Cm(0.9)

    # Example card
    rect(slide, rx, ry + Cm(0.4), rw, H - (ry + Cm(0.4)) - FTR - Cm(0.5), VERDE)
    t_ex_lbl = textbox(slide, rx + Cm(0.4), ry + Cm(0.55), rw - Cm(0.8), Cm(0.55))
    para(t_ex_lbl.text_frame, "ESEMPIO PRATICO", 9, VERDE_LT, bold=True, spc_b=0, spc_a=0)

    example_lines = [
        ("100 euro al mese di spesa", 14, BIANCO, False),
        ("→  15 euro SQ al mese", 17, VERDE_LT, True),
        ("In 2 mesi: prelievo + medicazione", 13, BIANCO, False),
        ("a costo zero.", 17, VERDE_LT, True),
    ]
    ey = ry + Cm(1.2)
    for txt, sz, col, bold in example_lines:
        te = textbox(slide, rx + Cm(0.4), ey, rw - Cm(0.8), Cm(0.75))
        para(te.text_frame, txt, sz, col, bold=bold, spc_b=0, spc_a=0)
        ey += Cm(0.78)


# ── SLIDE 6 — Tre ruoli ───────────────────────────────────────────────────────
def slide_6_ruoli(prs):
    slide = header_slide(prs, "Tre ruoli. Zero gestione sanitaria per l'esercizio.",
                         "Chi fa cosa — e dove si ferma il coinvolgimento del titolare.")

    roles = [
        ("Esercizio\ncommerciale", [
            "Stanzia il fondo promozionale",
            "Espone il materiale informativo",
            "Invita i clienti con parole proprie",
            "Non tocca nulla di sanitario",
        ], BLU),
        ("Cliente", [
            "Si iscrive (una sola volta)",
            "Carica gli scontrini via browser",
            "Accumula Credito SQ verificato",
            "Usa il credito quando vuole",
        ], BLU_M),
        ("Salute Quotidiana", [
            "Gestisce iscrizioni e verifiche",
            "Amministra il fondo",
            "Organizza prenotazioni e prestazioni",
            "Produce il report per l'esercizio",
        ], VERDE),
    ]

    col_w = CW / 3 - Cm(0.3)
    for i, (title, items, col) in enumerate(roles):
        x = L + i * (col_w + Cm(0.45))
        # colored header block
        rect(slide, x, CT, col_w, Cm(1.2), col)
        t0 = textbox(slide, x + Cm(0.2), CT + Cm(0.1), col_w - Cm(0.4), Cm(1.1))
        t0.text_frame.word_wrap = True
        para(t0.text_frame, title, 14, BIANCO, bold=True,
             align=PP_ALIGN.CENTER, spc_b=0, spc_a=0, line_pct=105)

        # white card body
        body_y = CT + Cm(1.2)
        body_h = H - body_y - FTR - Cm(0.5)
        card(slide, x, body_y, col_w, body_h)

        tf = body_tf(slide, top=body_y + Cm(0.3), left=x + Cm(0.3),
                     width=col_w - Cm(0.6), height=body_h - Cm(0.5))
        for item in items:
            para(tf, "•  " + item, 13, GRIGIO, spc_b=0, spc_a=6, line_pct=115)

        # special note for esercizio
        if i == 0:
            note_y = body_y + body_h - Cm(0.9)
            rect(slide, x, note_y, col_w, Cm(0.7), BLU_LT)
            tn = textbox(slide, x + Cm(0.2), note_y + Cm(0.1),
                         col_w - Cm(0.4), Cm(0.55))
            para(tn.text_frame, "Impegno: 3 azioni. Poi gira da solo.",
                 10, BLU, bold=True, align=PP_ALIGN.CENTER, spc_b=0, spc_a=0)


# ── SLIDE 7 — Prestazioni ────────────────────────────────────────────────────
def slide_7_prestazioni(prs):
    slide = header_slide(prs,
        "Dodici prestazioni a domicilio, raggiungibili con acquisti gi\xe0 abituali.",
        "Erogate da professionista abilitato, su appuntamento.")

    ROW_H  = Cm(0.58)
    COL_P  = CW * 0.50 - Cm(0.25)
    COL_T  = CW * 0.50 - Cm(0.25)
    TX_T   = L + CW * 0.50 + Cm(0.25)

    def draw_table(x, w, label, label_col, rows, hdr_col):
        tl = textbox(slide, x, CT, w, Cm(0.5))
        para(tl.text_frame, label, 10, label_col, bold=True, spc_b=0, spc_a=0)
        ty = CT + Cm(0.5)
        # header
        rect(slide, x, ty, w, ROW_H, hdr_col)
        th0 = textbox(slide, x + Cm(0.15), ty + Cm(0.08), w * 0.77, ROW_H)
        para(th0.text_frame, "Prestazione", 9, BIANCO, bold=True, spc_b=0, spc_a=0)
        th1 = textbox(slide, x + w * 0.77, ty + Cm(0.08), w * 0.23 - Cm(0.1), ROW_H)
        para(th1.text_frame, "Costo", 9, BIANCO, bold=True,
             align=PP_ALIGN.CENTER, spc_b=0, spc_a=0)
        ty += ROW_H
        for ri, (name, cost) in enumerate(rows):
            bg = G_LIGHT if ri % 2 == 0 else BIANCO
            rect(slide, x, ty, w, ROW_H, bg)
            t0 = textbox(slide, x + Cm(0.15), ty + Cm(0.07),
                         w * 0.77 - Cm(0.15), ROW_H)
            para(t0.text_frame, name, 10, GRIGIO, spc_b=0, spc_a=0)
            t1 = textbox(slide, x + w * 0.77, ty + Cm(0.07),
                         w * 0.23 - Cm(0.1), ROW_H)
            para(t1.text_frame, cost, 10, hdr_col, bold=True,
                 align=PP_ALIGN.CENTER, spc_b=0, spc_a=0)
            ty += ROW_H
        return ty

    rows_inf = [
        ("Iniezione intramuscolare I.M. (su prescrizione)", "8 €"),
        ("Prelievo ematico periferico", "10 €"),
        ("Medicazione semplice", "13 €"),
        ("Controllo parametri + educazione sanitaria", "16 €"),
        ("Prelievo arterioso", "20 €"),
        ("Medicazioni complesse", "20 €"),
        ("Ulcere ipertrofiche e piede diabetico", "20 €"),
        ("Gestione medicazione tracheostomia", "30 €"),
        ("Catetere vescicale / cateterismo estemporaneo", "35 €"),
        ("Gestione PICC (cateteri venosi centrali)", "35 €"),
        ("Posizionamento sondino naso gastrico", "40 €"),
        ("Posizionamento ago di Huber", "45 €"),
    ]

    rows_tele = [
        ("ECG a 12 derivazioni", "30 €"),
        ("Holter ECG 24h", "45 €"),
        ("Holter Pressorio 24h", "40 €"),
        ("Spirometria semplice", "30 €"),
    ]

    draw_table(L, COL_P,
               "Prestazioni infermieristiche a domicilio", BLU, rows_inf, BLU)
    draw_table(TX_T, COL_T,
               "Telemedicina a domicilio (in arrivo)", VERDE, rows_tele, VERDE)

    # example at bottom
    ex_y = H - FTR - Cm(1.0)
    rect(slide, L, ex_y, CW, Cm(0.85), BLU)
    te = textbox(slide, L + Cm(0.4), ex_y + Cm(0.12), CW - Cm(0.8), Cm(0.65))
    para(te.text_frame,
         "Con 100 €/mese di acquisti abituali: 15 SQ al mese  "
         "→  prelievo + medicazione disponibili in 2 mesi, a costo zero.",
         12, BIANCO, bold=True, align=PP_ALIGN.CENTER, spc_b=0, spc_a=0)


# ── SLIDE 8 — Tre passi per l'esercizio ──────────────────────────────────────
def slide_8_tre_passi(prs):
    slide = header_slide(prs, "Per l'esercizio: tre passi, poi il programma gira da solo.",
                         "L'impegno \xe8 minimo. La gestione rimane a Salute Quotidiana.")

    steps = [
        ("1", "Firma\nil contratto", BLU),
        ("2", "Versa\nil fondo", BLU_M),
        ("3", "Invita\ni clienti", VERDE),
    ]

    STEP_W = CW * 0.27
    STEP_H = Cm(3.6)
    STEP_Y = CT + Cm(0.4)
    GAP_S  = (CW - STEP_W * 3) / 4

    for i, (num, label, col) in enumerate(steps):
        sx = L + GAP_S * (i + 0.5) + STEP_W * i

        # Circle with number
        circ_r = Cm(1.0)
        cx = sx + STEP_W / 2 - circ_r
        cy = STEP_Y - circ_r * 0.5
        oval(slide, cx, cy, circ_r * 2, circ_r * 2, col)
        tn = textbox(slide, cx, cy + Cm(0.15), circ_r * 2, circ_r * 1.7)
        para(tn.text_frame, num, 22, BIANCO, bold=True,
             align=PP_ALIGN.CENTER, spc_b=0, spc_a=0)

        # Step card
        card(slide, sx, STEP_Y + Cm(1.3), STEP_W, STEP_H)
        rect(slide, sx, STEP_Y + Cm(1.3), STEP_W, Cm(0.45), col)

        tl = textbox(slide, sx + Cm(0.3), STEP_Y + Cm(2.0), STEP_W - Cm(0.6), Cm(1.3))
        tl.text_frame.word_wrap = True
        para(tl.text_frame, label, 18, col, bold=True,
             align=PP_ALIGN.CENTER, spc_b=0, spc_a=0, line_pct=115)

        # Arrow between steps
        if i < 2:
            ax2 = sx + STEP_W
            ta2 = textbox(slide, ax2, STEP_Y + Cm(2.3), GAP_S, Cm(0.8))
            para(ta2.text_frame, "▶", 18, G_MED,
                 align=PP_ALIGN.CENTER, spc_b=0, spc_a=0)

    # "Tutto il resto" card
    rest_y = STEP_Y + Cm(1.3) + STEP_H + Cm(0.5)
    rect(slide, L, rest_y, CW, H - rest_y - FTR - Cm(0.5), G_LIGHT)
    rect(slide, L, rest_y, Cm(0.4), H - rest_y - FTR - Cm(0.5), VERDE)

    tbody = textbox(slide, L + Cm(0.8), rest_y + Cm(0.2), CW - Cm(1.0),
                    H - rest_y - FTR - Cm(0.7))
    tbody.text_frame.word_wrap = True
    para(tbody.text_frame,
         "Tutto il resto \xe8 gestito da Salute Quotidiana: "
         "iscrizioni, verifiche, prenotazioni, prestazioni.",
         13, GRIGIO, spc_b=0, spc_a=4, line_pct=115)
    para(tbody.text_frame,
         "A fine periodo: report con dati reali — iscritti, credito accumulato, "
         "credito utilizzato, fondo residuo.",
         13, GRIGIO, spc_b=0, spc_a=0, line_pct=115)


# ── SLIDE 9 — Dark statement: cedibilità ─────────────────────────────────────
def slide_9_cedibile(prs):
    slide = blank(prs)
    rect(slide, 0, 0, W, H, BLU)
    rect(slide, 0, 0, Cm(0.5), H, VERDE)
    rect(slide, 0, H - FTR, W, FTR, RGBColor(0x0F, 0x22, 0x38))

    tf = textbox(slide, Cm(1.3), H - FTR + Cm(0.08), W - Cm(2.5), FTR)
    para(tf.text_frame, "Credito Salute SQ  \xb7  Salute Quotidiana",
         8, MUTED, align=PP_ALIGN.RIGHT, spc_b=0, spc_a=0)

    # Big statement
    t1 = textbox(slide, L, Cm(1.0), CW, Cm(2.2))
    t1.text_frame.word_wrap = True
    para(t1.text_frame, "Il credito si usa per s\xe9.", 34, BIANCO, bold=True,
         spc_b=0, spc_a=0)
    t1b = textbox(slide, L, Cm(2.9), CW, Cm(1.4))
    para(t1b.text_frame, "O si d\xe0 al vicino che non pu\xf2 muoversi.", 34, VERDE_LT,
         bold=True, spc_b=0, spc_a=0)

    # Divider
    rect(slide, L, Cm(4.5), CW * 0.6, Cm(0.06), BLU_M)

    # Supporting details in two columns
    details = [
        "Cedibile a chiunque il titolare voglia,\nsenza vincoli di parentela o convivenza.",
        "Un familiare, un vicino, un amico:\nbasta che sia iscritto alla piattaforma.",
        "Nessun abbonamento.\nNessuna spesa aggiuntiva.",
        "Non \xe8 un vantaggio individuale.\n\xc8 un beneficio che si condivide.",
    ]

    col_w2 = CW / 2 - Cm(0.3)
    for i, txt in enumerate(details):
        col = i % 2
        row = i // 2
        dx = L + col * (col_w2 + Cm(0.6))
        dy = Cm(4.8) + row * Cm(1.3)
        td = textbox(slide, dx, dy, col_w2, Cm(1.2))
        td.text_frame.word_wrap = True
        para(td.text_frame, txt, 13, G_MED, spc_b=0, spc_a=0, line_pct=130)


# ── SLIDE 10 — Pilot: 4 big numbers ─────────────────────────────────────────
def slide_10_pilot(prs):
    slide = header_slide(prs, "Un esercizio, 20 clienti, 30 giorni. Il rischio massimo \xe8 gi\xe0 definito.",
                         "Dati reali da un test reale — senza costi variabili aperti.")

    params = [
        ("1", "esercizio\ncommerciale", BLU),
        ("20", "clienti\nper ciclo", BLU_M),
        ("30", "giorni\ndi durata", VERDE),
        ("1.000 €", "fondo\nstanziato", RGBColor(0x1D, 0x4E, 0x35)),
    ]

    pw = CW / 4 - Cm(0.3)
    ph = Cm(2.8)
    py = CT + Cm(0.2)

    for i, (val, lbl, col) in enumerate(params):
        px = L + i * (pw + Cm(0.4))
        rect(slide, px, py, pw, ph, col)
        # big number
        tv = textbox(slide, px + Cm(0.15), py + Cm(0.25), pw - Cm(0.3), Cm(1.6))
        para(tv.text_frame, val, 32, BIANCO, bold=True,
             align=PP_ALIGN.CENTER, spc_b=0, spc_a=0)
        # label
        tl = textbox(slide, px + Cm(0.15), py + Cm(1.9), pw - Cm(0.3), Cm(0.8))
        para(tl.text_frame, lbl, 11, BIANCO,
             align=PP_ALIGN.CENTER, spc_b=0, spc_a=0, line_pct=100)

    # Bullet list below
    tf = body_tf(slide, top=py + ph + Cm(0.5))
    para(tf, "Il pilot produce dati concreti su:", 14, BLU, bold=True,
         spc_b=0, spc_a=6)
    items_p = [
        "quanti clienti si iscrivono e con quale velocit\xe0",
        "quanto credito accumulano e in che tempi",
        "quali prestazioni scelgono con maggiore frequenza",
    ]
    for item in items_p:
        para(tf, "•  " + item, 13, GRIGIO, spc_b=0, spc_a=4, line_pct=110)

    # Risk emphasis
    risk_y = H - FTR - Cm(1.0)
    rect(slide, L, risk_y, CW, Cm(0.85), VERDE)
    tr = textbox(slide, L + Cm(0.4), risk_y + Cm(0.12), CW - Cm(0.8), Cm(0.65))
    para(tr.text_frame,
         "Rischio massimo = fondo stanziato.  Nessun costo variabile aperto.",
         14, BIANCO, bold=True, align=PP_ALIGN.CENTER, spc_b=0, spc_a=0)


# ── SLIDE 11 — Piattaforma: 3 mockup screens ─────────────────────────────────
def slide_11_piattaforma(prs):
    slide = header_slide(prs, "La piattaforma funziona gi\xe0. Nessuna installazione, nessun training.",
                         "Accessibile da qualsiasi smartphone via browser. Tre viste dedicate.")

    # Text left
    tf = body_tf(slide, left=L, width=CW * 0.30, top=CT)
    para(tf, "Ogni ruolo ha\nla sua vista.", 16, BLU, bold=True,
         spc_b=0, spc_a=10, line_pct=115)
    for item in [
        "Cliente",
        "Esercizio",
        "Salute Quotidiana",
    ]:
        para(tf, "•  " + item, 13, GRIGIO, spc_b=0, spc_a=5, line_pct=110)

    para(tf, "Stack:", 11, BLU_M, bold=True, spc_b=14, spc_a=2)
    para(tf, "HTML/CSS/JS + Supabase", 11, GRIGIO, spc_b=0, spc_a=2)
    para(tf, "Zero installazione", 11, GRIGIO, spc_b=0, spc_a=2)
    para(tf, "Funziona su qualsiasi\nsmartphone", 11, GRIGIO,
         spc_b=0, spc_a=0, line_pct=115)

    # 3 mockup screens right
    SCR_X0   = L + CW * 0.33
    SCR_TOTW = W - SCR_X0 - Cm(1.2)
    SCR_H    = H - CT - FTR - Cm(0.6)
    GAP      = Cm(0.3)
    SW       = (SCR_TOTW - GAP * 2) / 3
    HDR_H    = Cm(0.55)
    ROW_H    = (SCR_H - HDR_H) / 10

    screens = [
        ("CLIENTE — Saldo", [
            ("Saldo: 12,50 SQ", BLU, True),
            ("In verifica: 3,50", RGBColor(0xB7, 0x77, 0x0D), False),
            ("", BIANCO, False),
            ("CARICA SCONTRINO", BIANCO, True),
            ("", BIANCO, False),
            ("Farmacia   +2,40 SQ", GRIGIO, False),
            ("Bar        +0,80 SQ", GRIGIO, False),
            ("Supermercato +1,50 SQ", GRIGIO, False),
        ], BLU),
        ("CLIENTE — Prenota", [
            ("Saldo: 12,50 SQ", BLU, True),
            ("", BIANCO, False),
            ("✔ Iniezione I.M.  8 SQ", VERDE, True),
            ("✔ Prelievo       10 SQ", VERDE, True),
            ("✔ Medicazione   13 SQ", VERDE, True),
            ("  Controllo      16 SQ", GRIGIO, False),
            ("  Prelievo art.  20 SQ", GRIGIO, False),
            ("", BIANCO, False),
            ("PRENOTA", BIANCO, True),
        ], BLU_M),
        ("ESERCIZIO — Report", [
            ("Periodo: luglio 2026", BLU, True),
            ("", BIANCO, False),
            ("Iscritti attivi:       18", GRIGIO, False),
            ("Scontrini caricati:   143", GRIGIO, False),
            ("Credito accumulato: 234 SQ", GRIGIO, False),
            ("Credito usato:       86 SQ", GRIGIO, False),
            ("Fondo residuo:      766 €", VERDE, True),
            ("", BIANCO, False),
            ("ESPORTA PDF", BIANCO, True),
        ], VERDE),
    ]

    for i, (label, rows, col) in enumerate(screens):
        sx = SCR_X0 + i * (SW + GAP)
        # frame
        s = slide.shapes.add_shape(1, sx, CT, SW, SCR_H)
        s.fill.solid(); s.fill.fore_color.rgb = BIANCO
        s.line.color.rgb = col; s.line.width = Cm(0.05)
        # header
        rect(slide, sx, CT, SW, HDR_H, col)
        th = textbox(slide, sx + Cm(0.1), CT + Cm(0.08), SW - Cm(0.2), HDR_H)
        para(th.text_frame, label, 7, BIANCO, bold=True,
             align=PP_ALIGN.CENTER, spc_b=0, spc_a=0)
        # rows
        ry = CT + HDR_H + Cm(0.05)
        for txt, tc, bold in rows:
            if not txt:
                ry += ROW_H * 0.5
                continue
            is_btn = ("CARICA" in txt or "PRENOTA" in txt or "ESPORTA" in txt)
            bg = col if is_btn else (
                VERDE_LT if (tc == VERDE and bold) else (
                BLU_LT if (tc == BLU and bold) else BIANCO))
            rect(slide, sx + Cm(0.06), ry, SW - Cm(0.12), ROW_H, bg)
            tr2 = textbox(slide, sx + Cm(0.12), ry + Cm(0.04),
                          SW - Cm(0.24), ROW_H)
            tc2 = BIANCO if is_btn else tc
            para(tr2.text_frame, txt, 6.5, tc2, bold=bold,
                 align=PP_ALIGN.CENTER if is_btn else PP_ALIGN.LEFT,
                 spc_b=0, spc_a=0)
            ry += ROW_H


# ── SLIDE 12 — CTA finale ────────────────────────────────────────────────────
def slide_12_cta(prs):
    slide = blank(prs)
    rect(slide, 0, 0, W, H, BLU)
    rect(slide, 0, H - Cm(1.8), W, Cm(1.8), VERDE)
    rect(slide, 0, 0, Cm(0.5), H, VERDE)

    # Header
    rect(slide, 0, 0, W, HDR, RGBColor(0x0F, 0x22, 0x38))
    th = textbox(slide, Cm(1.3), Cm(0.22), W - Cm(2.5), Cm(1.1))
    para(th.text_frame,
         "Il programma parte questa settimana. Il primo esercizio \xe8 gi\xe0 attivo.",
         20, BIANCO, bold=True, spc_b=0, spc_a=0)

    # Divider line
    rect(slide, Cm(1.3), Cm(2.3), Cm(10), Cm(0.06), BLU_M)

    # Two-column CTA
    col_w3 = CW / 2 - Cm(0.4)

    # LEFT — Per l'esercizio
    rect(slide, L, CT, col_w3, H - CT - Cm(2.2), RGBColor(0x12, 0x2B, 0x47))
    rect(slide, L, CT, col_w3, Cm(0.5), BLU_M)
    tl0 = textbox(slide, L + Cm(0.3), CT + Cm(0.05), col_w3 - Cm(0.6), Cm(0.45))
    para(tl0.text_frame, "PER L'ESERCIZIO COMMERCIALE",
         9, BIANCO, bold=True, spc_b=0, spc_a=0)

    steps_l = [
        "1.  Contatta Salute Quotidiana",
        "2.  Definisci fondo e durata",
        "3.  Firma il contratto",
        "4.  Avvia il programma",
    ]
    sy_l = CT + Cm(0.8)
    for step in steps_l:
        ts = textbox(slide, L + Cm(0.4), sy_l, col_w3 - Cm(0.8), Cm(0.7))
        para(ts.text_frame, step, 13, G_MED, spc_b=0, spc_a=0)
        sy_l += Cm(0.75)

    # RIGHT — Per il partner
    rx3 = L + col_w3 + Cm(0.8)
    rect(slide, rx3, CT, col_w3, H - CT - Cm(2.2), RGBColor(0x12, 0x2B, 0x47))
    rect(slide, rx3, CT, col_w3, Cm(0.5), VERDE)
    tr0 = textbox(slide, rx3 + Cm(0.3), CT + Cm(0.05), col_w3 - Cm(0.6), Cm(0.45))
    para(tr0.text_frame, "PER IL PARTNER / FINANZIATORE",
         9, BIANCO, bold=True, spc_b=0, spc_a=0)

    steps_r = [
        "1.  Richiedi i risultati del pilot",
        "2.  Valuta l'estensione del modello",
        "3.  Definisci l'accordo di partnership",
    ]
    sy_r = CT + Cm(0.8)
    for step in steps_r:
        ts2 = textbox(slide, rx3 + Cm(0.4), sy_r, col_w3 - Cm(0.8), Cm(0.7))
        para(ts2.text_frame, step, 13, G_MED, spc_b=0, spc_a=0)
        sy_r += Cm(0.75)

    # Contact info
    for j, (lbl, val) in enumerate([
        ("Email:", "angelo.rosso073@gmail.com"),
        ("Pilot:", "gi\xe0 attivo — rischio zero"),
    ]):
        cy2 = Cm(5.5) + j * Cm(0.85)
        tla = textbox(slide, Cm(1.3), cy2, Cm(3.5), Cm(0.7))
        para(tla.text_frame, lbl, 12, VERDE_LT, bold=True, spc_b=0, spc_a=0)
        tva = textbox(slide, Cm(5.0), cy2, W - Cm(6.5), Cm(0.7))
        para(tva.text_frame, val, 12, BIANCO, spc_b=0, spc_a=0)

    # Bottom branding
    tb_br = textbox(slide, Cm(1.3), H - Cm(2.0), Cm(9), Cm(0.8))
    para(tb_br.text_frame, "Credito Salute SQ  \xb7  Salute Quotidiana",
         14, VERDE_LT, bold=True, spc_b=0, spc_a=0)


# ── Main ─────────────────────────────────────────────────────────────────────
def main():
    prs = new_prs()
    slide_1_cover(prs)
    slide_2_hook(prs)
    slide_3_famiglie(prs)
    slide_4_insight(prs)
    slide_5_formula(prs)
    slide_6_ruoli(prs)
    slide_7_prestazioni(prs)
    slide_8_tre_passi(prs)
    slide_9_cedibile(prs)
    slide_10_pilot(prs)
    slide_11_piattaforma(prs)
    slide_12_cta(prs)

    prs.save(str(PPTX_OUT))
    print(f"OK  {PPTX_OUT.name}  ({len(prs.slides)} slide)")


if __name__ == "__main__":
    main()
