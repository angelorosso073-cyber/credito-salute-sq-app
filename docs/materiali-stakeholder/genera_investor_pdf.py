# -*- coding: utf-8 -*-
"""
Genera salute-quotidiana-investor-deck.pdf via reportlab (15 pagine).
"""
import sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from pathlib import Path
from reportlab.pdfgen import canvas as rlcanvas
from reportlab.lib.colors import HexColor
from reportlab.lib.units import cm as CM, inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase.pdfmetrics import stringWidth

BASE    = Path(__file__).parent
PDF_OUT = BASE / "salute-quotidiana-investor-deck.pdf"

# ── Palette ───────────────────────────────────────────────────────────────────
BLU      = HexColor("#1A3A5C")
BLU_M    = HexColor("#2E6DA8")
VERDE    = HexColor("#2D6A4F")
VERDE_LT = HexColor("#D6EEE2")
BLU_LT   = HexColor("#D6E4F0")
GRIGIO   = HexColor("#333333")
G_LIGHT  = HexColor("#F0F4F8")
G_ROW    = HexColor("#E0E8F0")
BIANCO   = HexColor("#FFFFFF")
ROSSO    = HexColor("#C0392B")
AMBRA    = HexColor("#B7770D")

# ── Font (Calibri se disponibile, altrimenti Helvetica) ───────────────────────
FN  = "Helvetica"
FNB = "Helvetica-Bold"
FNI = "Helvetica-Oblique"
FNBI= "Helvetica-BoldOblique"

_fonts_dir = r"C:\Windows\Fonts"
_cfiles = {"calibri.ttf":"Cal","calibrib.ttf":"Cal-B","calibrii.ttf":"Cal-I","calibriz.ttf":"Cal-BI"}
try:
    for fn, alias in _cfiles.items():
        pdfmetrics.registerFont(TTFont(alias, os.path.join(_fonts_dir, fn)))
    pdfmetrics.registerFontFamily("Cal", normal="Cal", bold="Cal-B",
                                  italic="Cal-I", boldItalic="Cal-BI")
    FN = "Cal"; FNB = "Cal-B"; FNI = "Cal-I"; FNBI = "Cal-BI"
    print("Font: Calibri")
except Exception:
    print("Font: Helvetica (fallback)")

def _fn(bold, italic):
    if bold and italic: return FNBI
    if bold:            return FNB
    if italic:          return FNI
    return FN

# ── Dimensioni pagina 13.33" × 7.5" (formato presentazione 16:9) ─────────────
PW = 13.33 * inch   # 959.76 pt
PH = 7.5  * inch    # 540.00 pt

L   = 1.5  * CM
CW  = PW - 3.0 * CM
CT  = 2.5  * CM
HDR = 2.0  * CM
FTR = 0.7  * CM

# ── Coordinate: y è distanza dal top; yrl converte per reportlab ──────────────
def yrl(y):
    return PH - y

# ── Rettangolo (y dal top) ────────────────────────────────────────────────────
def box(c, x, y, w, h, fill, stroke=None, sw=0.5):
    c.setFillColor(fill)
    if stroke:
        c.setStrokeColor(stroke)
        c.setLineWidth(sw)
        c.rect(x, yrl(y + h), w, h, fill=1, stroke=1)
    else:
        c.setStrokeColor(fill)
        c.rect(x, yrl(y + h), w, h, fill=1, stroke=0)

# ── Testo singola riga (y = baseline dal top) ─────────────────────────────────
def tl(c, x, y, text, size, color, bold=False, italic=False,
        align="left", max_w=None):
    if not text: return
    c.setFillColor(color)
    fname = _fn(bold, italic)
    c.setFont(fname, size)
    tw = stringWidth(text, fname, size)
    if align == "center" and max_w is not None:
        x = x + (max_w - tw) / 2
    elif align == "right" and max_w is not None:
        x = x + max_w - tw
    c.drawString(x, yrl(y), text)

# ── Wrap testo in righe che stiano in max_w ───────────────────────────────────
def wrap(text, fname, size, max_w):
    if not text.strip(): return [""]
    words = text.split()
    lines, cur = [], ""
    for w in words:
        t = (cur + " " + w).strip() if cur else w
        if stringWidth(t, fname, size) <= max_w:
            cur = t
        else:
            if cur: lines.append(cur)
            cur = w
    if cur: lines.append(cur)
    return lines if lines else [text]

# ── Blocco testo: items = [(text, size, color, bold, italic, align)] ──────────
def tb(c, x, y, w, items, lsp=1.3):
    """Disegna blocco testo. y = top del blocco dal top. Ritorna y finale."""
    cy = y
    for item in items:
        if isinstance(item, str):
            txt, sz, col, bd, it, al = item, 12, GRIGIO, False, False, "left"
        else:
            txt = item[0]
            sz  = item[1] if len(item) > 1 else 12
            col = item[2] if len(item) > 2 else GRIGIO
            bd  = item[3] if len(item) > 3 else False
            it  = item[4] if len(item) > 4 else False
            al  = item[5] if len(item) > 5 else "left"
        if txt == "":
            cy += sz * 0.4 if sz else 5
            continue
        fname = _fn(bd, it)
        for line in wrap(txt, fname, sz, w):
            tw = stringWidth(line, fname, sz)
            lx = x
            if al == "center": lx = x + (w - tw) / 2
            elif al == "right": lx = x + w - tw
            c.setFillColor(col)
            c.setFont(fname, sz)
            c.drawString(lx, yrl(cy + sz), line)
            cy += sz * lsp
        cy += sz * 0.1
    return cy

# ── Elementi comuni ───────────────────────────────────────────────────────────
def hdr_bar(c, title, subtitle=None):
    box(c, 0, 0, PW, HDR, BLU)
    tl(c, 1.2*CM, 0.18*CM + 22, title, 22, BIANCO, bold=True)
    if subtitle:
        tl(c, 1.2*CM, 1.4*CM + 11, subtitle, 11, G_ROW)

def ftr_bar(c):
    box(c, 0, PH - FTR, PW, FTR, BLU)
    txt = "Credito Salute SQ  ·  Salute Quotidiana  ·  Riservato"
    fname = FN
    tw = stringWidth(txt, fname, 8)
    c.setFillColor(BIANCO); c.setFont(fname, 8)
    c.drawString(PW - tw - 1.2*CM, yrl(PH - FTR + 0.1*CM + 8), txt)

def stripe(c):
    box(c, 0, 0, 0.45*CM, PH, VERDE)

def slide_frame(c, bg=G_LIGHT, title=None, subtitle=None, cover=False):
    box(c, 0, 0, PW, PH, bg)
    if not cover:
        hdr_bar(c, title or "", subtitle)
        stripe(c)
        ftr_bar(c)

# ═══════════════════════════════════════════════════════════════════════════════
# SLIDE 1 — Cover
# ═══════════════════════════════════════════════════════════════════════════════
def s1(c):
    box(c, 0, 0, PW, PH, BLU)
    box(c, 0, PH - 1.5*CM, PW, 1.5*CM, VERDE)
    stripe(c)
    tl(c, 2*CM, 1.8*CM + 48, "Credito Salute SQ", 48, BIANCO, bold=True)
    tl(c, 2*CM, 4.0*CM + 16,
       "La spesa quotidiana trasformata in accesso alle cure sanitarie a domicilio.",
       16, G_ROW, max_w=PW - 4*CM)
    tl(c, 2*CM, 5.5*CM + 13, "Un programma di Salute Quotidiana", 13, VERDE_LT)
    tl(c, 2*CM, PH - 2.0*CM + 10, "Investor Deck  ·  Luglio 2026", 10, G_ROW)

# ═══════════════════════════════════════════════════════════════════════════════
# SLIDE 2 — Premessa
# ═══════════════════════════════════════════════════════════════════════════════
def s2(c):
    slide_frame(c, title="Prima di tutto.",
                subtitle="Perch\xe9 esiste Salute Quotidiana")
    items = [
        ("Non siamo nati per competere. Siamo nati per costruire.",
         16, BLU, True),
        ("", 5),
        ("Il sistema ha convinto tutti che il profitto personale fosse l’unico "
         "motore possibile. Che il successo di uno significasse la sconfitta di un "
         "altro. Ti dicono che \xe8 sempre stato cos\xec. Che non c’\xe8 alternativa.",
         13, GRIGIO),
        ("", 5),
        ("Non \xe8 vero.", 14, BLU, True),
        ("", 5),
        ("Per secoli le comunit\xe0 hanno prosperato perch\xe9 le persone hanno scelto "
         "di stare dalla stessa parte. Il macellaio, il farmacista, il bar sotto casa "
         "non erano concorrenti — erano parte dello stesso tessuto. "
         "Si reggevano a vicenda. Reggevano il quartiere.", 13, GRIGIO),
        ("", 5),
        ("Salute Quotidiana trasforma ogni acquisto quotidiano in credito per cure "
         "sanitarie a domicilio. Il valore rimane nella comunit\xe0. "
         "Nessuno si arricchisce sulle spalle degli altri.", 13, GRIGIO),
        ("", 5),
        ("Aderire non \xe8 una scelta di marketing. \xc8 una scelta di campo.",
         13, BLU, True),
        ("", 5),
        ("E che quel mondo comincia dal tuo negozio.", 14, VERDE, True),
    ]
    tb(c, 2.0*CM, CT, CW - 1.0*CM, items, lsp=1.25)

# ═══════════════════════════════════════════════════════════════════════════════
# SLIDE 3 — Problema
# ═══════════════════════════════════════════════════════════════════════════════
def s3(c):
    slide_frame(c, title="Il problema", subtitle="Tre fratture nel sistema")
    col_w = CW / 3 - 0.3*CM
    stats = [
        ("1 su 3",   "italiani rinuncia a curarsi\nper costi o tempi di attesa", BLU),
        ("60–180", "giorni di attesa media SSN\nper una visita specialistica", BLU_M),
        ("€ 12 mld", "spesi ogni anno in promozione\nlocale senza effetto misurabile", VERDE),
    ]
    card_h = PH - CT - FTR - 0.4*CM
    for i, (num, desc, col) in enumerate(stats):
        x = L + i * (col_w + 0.45*CM)
        box(c, x, CT, col_w, card_h, G_LIGHT, stroke=BLU_LT, sw=0.5)
        box(c, x, CT, col_w, 0.5*CM, col)
        tl(c, x, CT + 0.7*CM + 36, num, 36, col, bold=True, align="center", max_w=col_w)
        dy = CT + 2.6*CM
        for line in desc.split('\n'):
            tl(c, x, dy + 13, line, 13, GRIGIO, align="center", max_w=col_w)
            dy += 13 * 1.35
    ins = ("C’\xe8 un modo per collegare queste due realt\xe0: il budget promozionale "
           "degli esercizi locali e il bisogno di salute delle famiglie.")
    tb(c, L, PH - FTR - 1.6*CM, CW, [(ins, 13, VERDE, True, False, "center")], lsp=1.3)

# ═══════════════════════════════════════════════════════════════════════════════
# SLIDE 4 — Soluzione
# ═══════════════════════════════════════════════════════════════════════════════
def s4(c):
    slide_frame(c, title="La soluzione",
                subtitle="Il budget promozionale diventa qualcosa che dura")
    items = [
        ("L’esercizio commerciale destina una quota del proprio budget "
         "promozionale a un fondo gestito da Salute Quotidiana.", 14, GRIGIO),
        ("", 6),
        ("I clienti accumulano Credito SQ con gli acquisti abituali. "
         "Il credito \xe8 spendibile su prestazioni infermieristiche a domicilio.",
         14, GRIGIO),
        ("", 6),
        ("Nessun gadget. Nessun volantino.", 16, BLU, True),
        ("Un beneficio concreto, spendibile, vicino alla vita reale delle persone.",
         16, BLU, True),
    ]
    tb(c, L, CT, CW, items, lsp=1.3)
    steps  = ["Acquisto\nquotidiano", "3% della\nspesa → Credito",
              "Prenota\nprestazione", "Infermiere\na domicilio"]
    colors = [BLU, BLU_M, VERDE, VERDE]
    sw2 = CW / 5
    sy  = PH - FTR - 2.2*CM; sh = 1.8*CM
    for i, (step, col) in enumerate(zip(steps, colors)):
        x = L + i * (sw2 + 0.15*CM)
        box(c, x, sy, sw2 - 0.1*CM, sh, col)
        for j, ln in enumerate(step.split('\n')):
            tl(c, x, sy + 0.4*CM + j*11*1.2 + 11, ln, 11, BIANCO,
               bold=True, align="center", max_w=sw2 - 0.1*CM)
        if i < len(steps) - 1:
            tl(c, x + sw2, sy + sh/2 + 5, ">", 10, BLU_M)

# ═══════════════════════════════════════════════════════════════════════════════
# SLIDE 5 — Come funziona
# ═══════════════════════════════════════════════════════════════════════════════
def s5(c):
    slide_frame(c, title="Come funziona",
                subtitle="Tre ruoli. Un meccanismo semplice.")
    roles = [
        ("Esercizio\ncommerciale",
         ["Stanzia il fondo promozionale","Espone il materiale informativo",
          "Invita i clienti a partecipare","Non gestisce nulla di sanitario"], BLU),
        ("Cliente",
         ["Si iscrive alla piattaforma","Carica gli scontrini via browser",
          "Accumula Credito SQ verificato","Usa il credito per le prestazioni"], BLU_M),
        ("Salute Quotidiana",
         ["Gestisce iscrizioni e verifiche","Amministra il fondo",
          "Organizza le prestazioni","Produce il report per l’esercizio"], VERDE),
    ]
    col_w = CW / 3 - 0.3*CM
    for i, (title, citems, col) in enumerate(roles):
        x = L + i * (col_w + 0.45*CM)
        box(c, x, CT, col_w, 1.0*CM, col)
        for j, ln in enumerate(title.split('\n')):
            tl(c, x, CT + 0.15*CM + j*12*1.1 + 12, ln, 12, BIANCO,
               bold=True, align="center", max_w=col_w)
        by = CT + 1.1*CM
        bh = PH - by - FTR - 0.4*CM
        box(c, x, by, col_w, bh, G_LIGHT, stroke=BLU_LT, sw=0.5)
        for k, it in enumerate(citems):
            tl(c, x + 0.25*CM, by + 0.35*CM + k*13*1.45 + 13,
               "•  " + it, 13, GRIGIO)

# ═══════════════════════════════════════════════════════════════════════════════
# SLIDE 6 — Prestazioni
# ═══════════════════════════════════════════════════════════════════════════════
def s6(c):
    slide_frame(c, title="Le prestazioni",
                subtitle="Tutto ci\xf2 che si pu\xf2 fare con il Credito SQ")
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

    def draw_tbl(x, w, rows, hcol):
        rh = 0.6*CM; c0 = w * 0.78; c1 = w * 0.22
        ty0 = CT + 0.55*CM
        box(c, x, ty0, w, rh, hcol)
        tl(c, x + 0.1*CM, ty0 + 0.08*CM + 10, "Prestazione", 10, BIANCO, bold=True)
        tl(c, x + c0,     ty0 + 0.08*CM + 10, "Costo",       10, BIANCO, bold=True)
        for ri, (name, cost) in enumerate(rows):
            ry2 = ty0 + rh * (ri + 1)
            bg = G_LIGHT if ri % 2 == 0 else BIANCO
            box(c, x, ry2, w, rh, bg)
            tl(c, x + 0.1*CM, ry2 + 0.08*CM + 11, name, 11, GRIGIO)
            tl(c, x + c0, ry2 + 0.08*CM + 11, cost, 11, hcol, bold=True,
               align="center", max_w=c1)

    half = CW * 0.5 - 0.15*CM
    tl(c, L, CT + 11, "Prestazioni infermieristiche a domicilio", 11, BLU, bold=True)
    draw_tbl(L, half, rows_inf, BLU)
    x2 = L + CW * 0.5 + 0.3*CM
    tl(c, x2, CT + 11, "Telemedicina a domicilio (in arrivo)", 11, VERDE, bold=True)
    draw_tbl(x2, half, rows_tele, VERDE)

# ═══════════════════════════════════════════════════════════════════════════════
# SLIDE 7 — Business model
# ═══════════════════════════════════════════════════════════════════════════════
def s7(c):
    slide_frame(c, title="Modello di business",
                subtitle="Come genera valore per tutte le parti")
    fy = CT + 0.3*CM; fh = 1.1*CM; fw = CW / 3 - 0.3*CM
    flows = [
        ("Esercente versa il fondo", BLU,   L),
        ("20% → Salute Quotidiana",  VERDE, L + CW * 0.33),
        ("80% → Professionista",     BLU_M, L + CW * 0.66),
    ]
    for label, col, x in flows:
        box(c, x, fy, fw, fh, col)
        tl(c, x, fy + fh/2 + 6, label, 12, BIANCO, bold=True, align="center", max_w=fw)

    cards = [
        ("Fondo tipico\nper esercente/ciclo", "1.000 €", "fisso, zero variabile", BLU),
        ("Ricavo SQ\nper esercente/mese",    "150 €",    "media su utilizzo 75%", VERDE),
        ("Ciclo\nstandard",                  "30 giorni",     "renovabile ogni mese",  BLU_M),
        ("Clienti per\nciclo pilot",         "20",            "scalabile senza limite", BLU_M),
    ]
    ue_y = fy + fh + 0.6*CM; cw2 = CW / 4 - 0.25*CM
    for i, (lbl, val, note, col) in enumerate(cards):
        cx = L + i * (cw2 + 0.33*CM)
        ch = PH - ue_y - FTR - 0.4*CM
        box(c, cx, ue_y, cw2, ch, G_LIGHT, stroke=BLU_LT, sw=0.5)
        box(c, cx, ue_y, cw2, 0.35*CM, col)
        for j, ln in enumerate(lbl.split('\n')):
            tl(c, cx + 0.2*CM, ue_y + 0.5*CM + j*11*1.2 + 11, ln, 11, GRIGIO)
        tl(c, cx, ue_y + 1.9*CM + 20, val, 20, col, bold=True, align="center", max_w=cw2)
        tl(c, cx, ue_y + 3.0*CM + 10, note, 10, GRIGIO, italic=True, align="center", max_w=cw2)

# ═══════════════════════════════════════════════════════════════════════════════
# SLIDE 8 — Mercato
# ═══════════════════════════════════════════════════════════════════════════════
def s8(c):
    slide_frame(c, title="Il mercato", subtitle="TAM / SAM / SOM — Italia")
    market = [
        ("TAM", "Spesa privata sanitaria Italia", "40 mld €/anno",
         "Intero mercato privato: visite, diagnostica, domiciliare.", BLU, 0),
        ("SAM", "Home nursing + Telemedicina", "2 mld €/anno",
         "Segmento infermieristico domiciliare e telemedicina.", BLU_M, 1),
        ("SOM", "Mercato raggiungibile Y3", "15 mln €/anno",
         "Esercizi locali partner in Sicilia/Sud Italia, 3–5 anni.", VERDE, 2),
    ]
    bh = (PH - CT - FTR - 1.2*CM) / 3
    for label, title, value, desc, col, i in market:
        by = CT + i * (bh + 0.15*CM)
        box(c, L, by, 0.4*CM, bh - 0.1*CM, col)
        tl(c, L + 0.6*CM,  by + 0.1*CM + 14, label, 14, col, bold=True)
        tl(c, L + 1.9*CM,  by + 0.1*CM + 13, title, 13, BLU, bold=True)
        tl(c, L + CW*0.5,  by + 0.05*CM + 16, value, 16, col, bold=True,
           align="right", max_w=CW * 0.25)
        tb(c, L + 1.9*CM, by + 0.85*CM, CW - 1.4*CM, [(desc, 12, GRIGIO)], lsp=1.2)
    tl(c, L, PH - FTR - 0.9*CM + 11,
       "Obiettivo Anno 3: 60 esercenti attivi → €108.000 ricavi SQ (0,72% del SOM)",
       11, VERDE, bold=True)

# ═══════════════════════════════════════════════════════════════════════════════
# SLIDE 9 — Piattaforma
# ═══════════════════════════════════════════════════════════════════════════════
def s9(c):
    slide_frame(c, title="La piattaforma",
                subtitle="Web app operativa — nessuna installazione richiesta")
    lw = CW * 0.42
    items = [
        ("Il sistema \xe8 gi\xe0 operativo.", 14, BLU, True),
        ("Accessibile da qualsiasi smartphone via browser.", 13, GRIGIO),
        ("", 4),
        ("Tre viste dedicate:", 12, GRIGIO, True),
        ("•  Cliente — saldo, scontrini, prenotazione", 12, GRIGIO),
        ("•  Esercente — report, clienti, fondo", 12, GRIGIO),
        ("•  Admin SQ — validazioni, analytics", 12, GRIGIO),
        ("", 4),
        ("Stack: Next.js 14 + Supabase (PostgreSQL)", 11, BLU_M, False, True),
        ("Deploy: Vercel (SLA 99,9%)", 11, BLU_M, False, True),
    ]
    tb(c, L, CT, lw, items, lsp=1.3)

    SCR_X0 = L + CW * 0.45
    STOT   = PW - SCR_X0 - 1.0*CM
    SCR_H  = PH - CT - FTR - 0.6*CM
    GAP    = 0.25*CM
    SW3    = (STOT - GAP * 2) / 3
    HDR_H  = 0.55*CM
    ROW_H  = (SCR_H - HDR_H) / 9.5

    screens = [
        ("WALLET", [
            ("Saldo: 12,50 Credito SQ", BLU, True),
            ("In verifica: 3,50",        AMBRA, False),
            ("",                          None,  False),
            ("CARICA SCONTRINO",          None,  True),
            ("",                          None,  False),
            ("Farmacia  +2,40 SQ",        GRIGIO, False),
            ("Bar       +0,80 SQ",        GRIGIO, False),
            ("Supermercato +1,50 SQ",     GRIGIO, False),
        ], BLU),
        ("PRENOTA", [
            ("Saldo: 12,50 SQ",           BLU,   True),
            ("",                           None,  False),
            ("v  Iniezione I.M.   8 SQ",  VERDE, True),
            ("v  Prelievo        10 SQ",   VERDE, True),
            ("v  Medicazione     13 SQ",   VERDE, True),
            ("   Controllo       16 SQ",   GRIGIO, False),
            ("   Prelievo art.   20 SQ",   GRIGIO, False),
            ("",                           None,  False),
            ("PRENOTA",                    None,  True),
        ], BLU_M),
        ("CONFERMA", [
            ("v  Confermata!",             VERDE,  True),
            ("",                           None,   False),
            ("Prelievo periferico",        BLU,    True),
            ("Infermiere: Mario R.",       GRIGIO, False),
            ("",                           None,   False),
            ("Mer 16/03  —  ore 09:30", GRIGIO, False),
            ("A domicilio",                GRIGIO, False),
            ("",                           None,   False),
            ("Usati: 10 SQ  |  Residuo: 2,50", VERDE, True),
        ], VERDE),
    ]

    for i, (label, rows, col) in enumerate(screens):
        sx = SCR_X0 + i * (SW3 + GAP)
        box(c, sx, CT, SW3, SCR_H, BIANCO, stroke=col, sw=1.5)
        box(c, sx, CT, SW3, HDR_H, col)
        tl(c, sx, CT + HDR_H/2 + 3.5, label, 7, BIANCO, bold=True, align="center", max_w=SW3)
        ry2 = CT + HDR_H + 0.1*CM
        for txt, tc, bd in rows:
            if not txt:
                ry2 += ROW_H * 0.4; continue
            is_btn = "CARICA" in txt or txt == "PRENOTA"
            bg = col if is_btn else (VERDE_LT if (tc == VERDE and bd) else
                                     (BLU_LT  if (tc == BLU   and bd) else BIANCO))
            tc2 = BIANCO if is_btn else (tc or GRIGIO)
            box(c, sx + 0.08*CM, ry2, SW3 - 0.16*CM, ROW_H, bg)
            al = "center" if (is_btn or "v  C" in txt) else "left"
            tl(c, sx + 0.15*CM, ry2 + 0.05*CM + 6.5, txt, 6.5, tc2,
               bold=bd, align=al, max_w=SW3 - 0.3*CM)
            ry2 += ROW_H

# ═══════════════════════════════════════════════════════════════════════════════
# SLIDE 10 — Pilot
# ═══════════════════════════════════════════════════════════════════════════════
def s10(c):
    slide_frame(c, title="Il pilot", subtitle="Dati reali da un test reale")
    params = [
        ("1",        "esercizio\ncommerciale", BLU),
        ("20",       "clienti\nper ciclo",     BLU_M),
        ("30",       "giorni\ndi durata",       VERDE),
        ("1.000 €", "fondo\nstanziato",    VERDE),
    ]
    pw2 = CW / 4 - 0.3*CM; ph2 = 2.5*CM
    for i, (val, lbl, col) in enumerate(params):
        px = L + i * (pw2 + 0.4*CM)
        box(c, px, CT, pw2, ph2, col)
        tl(c, px, CT + 0.2*CM + 28, val, 28, BIANCO, bold=True, align="center", max_w=pw2)
        for j, ln in enumerate(lbl.split('\n')):
            tl(c, px, CT + 1.5*CM + j*11*1.1 + 11, ln, 11, BIANCO, align="center", max_w=pw2)
    items = [
        ("Il pilot produce dati concreti:", 14, BLU, True),
        ("•  quanti clienti si iscrivono e con quale velocit\xe0", 13, GRIGIO),
        ("•  quanto credito accumulano e in che tempi", 13, GRIGIO),
        ("•  quali prestazioni scelgono con maggiore frequenza", 13, GRIGIO),
        ("•  tasso di utilizzo del credito accumulato", 13, GRIGIO),
        ("", 6),
        ("Il rischio \xe8 contenuto e definito. Il fondo stanziato \xe8 il massimo "
         "esponibile. Nessun costo variabile aperto.", 13, VERDE, True),
    ]
    tb(c, L, CT + ph2 + 0.5*CM, CW, items, lsp=1.3)

# ═══════════════════════════════════════════════════════════════════════════════
# SLIDE 11 — Proiezioni
# ═══════════════════════════════════════════════════════════════════════════════
def s11(c):
    slide_frame(c, title="Proiezioni finanziarie", subtitle="3 anni — scenario base")
    hdrs = ["", "Anno 1", "Anno 2", "Anno 3"]
    rows_f = [
        ("Esercenti attivi (media)", "3",          "20",         "60"),
        ("Fondi gestiti",            "36.000 €",  "240.000 €", "720.000 €"),
        ("Ricavi SQ (20%)",          "7.200 €",   "48.000 €",  "144.000 €"),
        ("Costi operativi",          "17.000 €",  "28.000 €",  "55.000 €"),
        ("EBITDA",                   "−9.800 €", "+20.000 €", "+89.000 €"),
    ]
    rh  = 0.75*CM
    cws = [CW*0.34, CW*0.22, CW*0.22, CW*0.22]
    # header
    box(c, L, CT, CW, rh, BLU)
    cx = L
    for ci, h in enumerate(hdrs):
        al = "center" if ci > 0 else "left"
        tl(c, cx + 0.1*CM, CT + 0.12*CM + 11, h, 11, BIANCO, bold=True,
           align=al, max_w=cws[ci])
        cx += cws[ci]
    # rows
    for ri, (label, *vals) in enumerate(rows_f):
        ry2 = CT + rh * (ri + 1)
        ebitda = label == "EBITDA"
        bg = VERDE_LT if ebitda else (G_LIGHT if ri % 2 == 0 else BIANCO)
        box(c, L, ry2, CW, rh, bg)
        sz = 13 if ebitda else 12
        tl(c, L + 0.15*CM, ry2 + 0.12*CM + sz, label, sz,
           VERDE if ebitda else BLU, bold=ebitda)
        cx = L + cws[0]
        for ci2, val in enumerate(vals):
            vcol = ROSSO if val.startswith("−") else (VERDE if ebitda else GRIGIO)
            tl(c, cx + 0.1*CM, ry2 + 0.12*CM + sz, val, sz, vcol,
               bold=ebitda, align="center", max_w=cws[ci2+1] - 0.2*CM)
            cx += cws[ci2+1]
    notes = [
        ("●  Breakeven previsto: Q3 Anno 2 (~mese 20)", VERDE),
        ("●  Nessun costo variabile aperto: rischio cap to fondo stanziato", BLU),
        ("●  Scenario conservativo: 70% utilizzo crediti, 1 ciclo/mese/esercente", GRIGIO),
    ]
    ny = CT + rh * 6 + 0.4*CM
    for note, col in notes:
        tl(c, L, ny + 11, note, 11, col)
        ny += 0.55*CM

# ═══════════════════════════════════════════════════════════════════════════════
# SLIDE 12 — Investimento
# ═══════════════════════════════════════════════════════════════════════════════
def s12(c):
    slide_frame(c, title="Richiesta di investimento", subtitle="Seed round — 20.000 €")
    tl(c, L, CT + 40, "20.000 €", 40, BLU, bold=True)
    tl(c, L, CT + 1.7*CM + 12, "seed round  —  equity o revenue share", 12, GRIGIO)
    allocations = [
        ("Tech & MVP",       "5.000 €",  "25%",   "Sviluppo web app, integrazione Supabase, testing.", BLU),
        ("Operativit\xe0 Y1","10.000 €", "50%",   "Gestione pilot, coordinamento professionisti, admin.", VERDE),
        ("Marketing & BD",   "3.500 €",  "17,5%", "Acquisizione esercenti partner, materiali, eventi.", BLU_M),
        ("Contingency",      "1.500 €",  "7,5%",  "Riserva operativa per imprevisti del primo ciclo.", GRIGIO),
    ]
    fw = CW / 4 - 0.3*CM
    for i, (title, amount, pct, desc, col) in enumerate(allocations):
        fx = L + i * (fw + 0.4*CM); fy = CT + 2.3*CM
        fh = PH - fy - FTR - 0.5*CM
        box(c, fx, fy, fw, fh, G_LIGHT, stroke=BLU_LT, sw=0.5)
        box(c, fx, fy, fw, 0.35*CM, col)
        tl(c, fx + 0.2*CM, fy + 0.5*CM + 12, title, 12, col, bold=True)
        tl(c, fx, fy + 1.1*CM + 18, amount, 18, col, bold=True, align="center", max_w=fw)
        tl(c, fx, fy + 2.1*CM + 14, pct, 14, GRIGIO, align="center", max_w=fw)
        tb(c, fx + 0.2*CM, fy + 2.8*CM, fw - 0.4*CM, [(desc, 11, GRIGIO)], lsp=1.2)
    roi = ("ROI stimato per investitore al 20% equity:  "
           "valutazione Y3 ≈ €1,08M  →  quota = €216.000  →  ~10x in 3 anni")
    tl(c, L, PH - FTR - 0.8*CM + 12, roi, 12, VERDE, bold=True, align="center", max_w=CW)

# ═══════════════════════════════════════════════════════════════════════════════
# SLIDE 13 — Roadmap
# ═══════════════════════════════════════════════════════════════════════════════
def s13(c):
    slide_frame(c, title="Roadmap", subtitle="Dal pilot alla scala")
    milestones = [
        ("Q3 2026", "Pilot",
         ["1 esercente, 20 clienti","30 giorni, fondo €1.000","Raccolta dati reali"], BLU),
        ("Q4 2026", "Early Traction",
         ["3–5 esercenti attivi","Ottimizzazione onboarding","Report validazione modello"], BLU_M),
        ("2027", "Espansione",
         ["20 esercenti in Sicilia","Aggiunta telemedicina","Breakeven Q2 2027"], VERDE),
        ("2028", "Scala",
         ["60+ esercenti Sud Italia","Partnership sanitarie","Ricavi €144.000"], VERDE),
    ]
    mw = CW / 4 - 0.3*CM
    for i, (period, title, citems, col) in enumerate(milestones):
        mx = L + i * (mw + 0.4*CM)
        box(c, mx, CT + 0.35*CM, mw - 0.1*CM, 0.08*CM, col)
        box(c, mx + mw/2 - 0.25*CM, CT + 0.1*CM, 0.5*CM, 0.5*CM, col)
        tl(c, mx, CT + 0.65*CM + 11, period, 11, col, bold=True, align="center", max_w=mw)
        cy = CT + 1.25*CM; ch = PH - cy - FTR - 0.4*CM
        box(c, mx, cy, mw, ch, G_LIGHT, stroke=BLU_LT, sw=0.5)
        box(c, mx, cy, mw, 0.6*CM, col)
        tl(c, mx, cy + 0.08*CM + 12, title, 12, BIANCO, bold=True, align="center", max_w=mw)
        for k, it in enumerate(citems):
            tl(c, mx + 0.15*CM, cy + 0.75*CM + k*12*1.45 + 12, "•  " + it, 12, GRIGIO)

# ═══════════════════════════════════════════════════════════════════════════════
# SLIDE 14 — Team
# ═══════════════════════════════════════════════════════════════════════════════
def s14(c):
    slide_frame(c, title="Il team", subtitle="Chi c’\xe8 dietro Salute Quotidiana")
    hw = CW * 0.45; hh = PH - CT - FTR - 0.5*CM
    box(c, L, CT, hw, hh, G_LIGHT, stroke=BLU_LT, sw=0.5)
    box(c, L, CT, hw, 0.45*CM, BLU)
    tl(c, L + 0.3*CM, CT + 0.6*CM + 18, "Angelo Rosso", 18, BLU, bold=True)
    tl(c, L + 0.3*CM, CT + 1.2*CM + 13, "Fondatore & CEO", 13, VERDE, bold=True)
    fp = ["Professionista sanitario con esperienza diretta sul territorio",
          "Conoscenza operativa del sistema infermieristico domiciliare",
          "Sviluppo digitale: architettura web app Credito SQ",
          "Focus: Sicilia orientale (Francofonte, Lentini, Carlentini)"]
    for k, it in enumerate(fp):
        tl(c, L + 0.3*CM, CT + 1.8*CM + k*13*1.5 + 13, "•  " + it, 13, GRIGIO)

    x2 = L + CW*0.48; w2 = CW*0.52
    box(c, x2, CT, w2, hh, G_LIGHT, stroke=BLU_LT, sw=0.5)
    box(c, x2, CT, w2, 0.45*CM, BLU_M)
    tl(c, x2 + 0.3*CM, CT + 0.6*CM + 14, "Profili in ricerca", 14, BLU_M, bold=True)
    advisors = [
        ("CFO / Advisor finanziario",  "gestione fondi, reporting investitore"),
        ("Partnership manager",         "acquisizione esercenti, contratti"),
        ("Clinical supervisor",         "supervisione qualit\xe0 prestazioni"),
    ]
    for k, (role, desc) in enumerate(advisors):
        tl(c, x2 + 0.3*CM, CT + 1.3*CM + k*13*2.5 + 13, role, 13, BLU_M, bold=True)
        tl(c, x2 + 0.3*CM, CT + 1.3*CM + k*13*2.5 + 13 + 13*1.3, desc, 12, GRIGIO)

# ═══════════════════════════════════════════════════════════════════════════════
# SLIDE 15 — Chiusura
# ═══════════════════════════════════════════════════════════════════════════════
def s15(c):
    box(c, 0, 0, PW, PH, BLU)
    box(c, 0, PH - 1.5*CM, PW, 1.5*CM, VERDE)
    stripe(c)
    items = [
        ("Un modo diverso di stare nel mercato.", 32, BIANCO, True),
        ("", 8),
        ("Non serve spendere di pi\xf9. Serve spendere in modo che le persone "
         "ricordino — e che faccia qualcosa di concreto per la comunit\xe0 "
         "in cui si lavora.", 14, G_ROW),
    ]
    tb(c, 2*CM, 1.5*CM, PW - 4*CM, items, lsp=1.3)
    contacts = [
        ("Email:",             "angelo.rosso073@gmail.com"),
        ("Programma:",         "Credito Salute SQ · Luglio 2026"),
        ("Pilot disponibile:", "da subito — rischio zero"),
    ]
    for i, (label, val) in enumerate(contacts):
        ey = 5.6*CM + i * 0.85*CM
        tl(c, 2*CM,   ey + 12, label, 12, VERDE_LT, bold=True)
        tl(c, 6.8*CM, ey + 12, val,   12, BIANCO)
    tl(c, 2*CM, PH - 2.4*CM + 14,
       "Credito Salute SQ · Salute Quotidiana", 14, VERDE, bold=True)

# ═══════════════════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════════════════
def main():
    cv = rlcanvas.Canvas(str(PDF_OUT), pagesize=(PW, PH))
    slides = [s1, s2, s3, s4, s5, s6, s7, s8, s9, s10, s11, s12, s13, s14, s15]
    for i, fn in enumerate(slides, 1):
        fn(cv)
        cv.showPage()
        print(f"  Slide {i}/15")
    cv.save()
    print(f"\nPDF: {PDF_OUT}")
    print(f"Dimensione: {PDF_OUT.stat().st_size:,} byte")

if __name__ == "__main__":
    main()
