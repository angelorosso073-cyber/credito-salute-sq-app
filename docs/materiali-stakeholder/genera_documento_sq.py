# -*- coding: utf-8 -*-
"""
genera_documento_sq.py  v5
Credito Salute SQ — Documento A4 · ReportLab only
"""
import sys, io, tempfile, shutil
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from pathlib import Path
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT, TA_JUSTIFY
from reportlab.platypus import (
    BaseDocTemplate, PageTemplate, Frame, Flowable,
    Paragraph, Spacer, Table, TableStyle, HRFlowable,
    KeepTogether, PageBreak, CondPageBreak, NextPageTemplate
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

_FINAL_OUT = Path(__file__).parent / "9-documento-sq-v5.pdf"
OUT = Path(tempfile.mktemp(suffix=".pdf"))
LOGO_ICON_PATH = Path(__file__).parent / "logo-icon-only.png"

# ── Font ──────────────────────────────────────────────────────────────────────
FONT_BODY = "Helvetica"
FONT_BOLD = "Helvetica-Bold"
FONT_ITAL = "Helvetica-Oblique"

_WIN_FONTS = [
    ("Calibri",  r"C:\Windows\Fonts\calibri.ttf"),
    ("CalibriB", r"C:\Windows\Fonts\calibrib.ttf"),
    ("CalibriI", r"C:\Windows\Fonts\calibrii.ttf"),
]
_ok = True
for _fn, _fp in _WIN_FONTS:
    try:
        pdfmetrics.registerFont(TTFont(_fn, _fp))
    except Exception:
        _ok = False
        break
if _ok:
    FONT_BODY = "Calibri"
    FONT_BOLD = "CalibriB"
    FONT_ITAL = "CalibriI"

# ── Palette ───────────────────────────────────────────────────────────────────
BLU       = colors.HexColor("#1A3A5C")
BLU_M     = colors.HexColor("#2E6DA8")
BLU_LT    = colors.HexColor("#D6E4F0")
BLU_DARK  = colors.HexColor("#0F2238")
BLU_XD    = colors.HexColor("#071525")
VERDE     = colors.HexColor("#2D6A4F")
VERDE_LT  = colors.HexColor("#D6EEE2")
VERDE_D   = colors.HexColor("#1D4E35")
VERDE_XD  = colors.HexColor("#0F2E1F")
ORO       = colors.HexColor("#C9A84C")
ORO_LT    = colors.HexColor("#F5EDD4")
GRIGIO    = colors.HexColor("#2A2A2A")
G_MED     = colors.HexColor("#E8EEF5")
G_LIGHT   = colors.HexColor("#F4F7FB")
G_XL      = colors.HexColor("#FAFCFF")
BIANCO    = colors.white
MUTED     = colors.HexColor("#6B7F94")
MUTED_LT  = colors.HexColor("#A0B4C8")

# ── Layout ────────────────────────────────────────────────────────────────────
PW, PH = A4
ML     = 2.0 * cm
MR     = 1.8 * cm
MT     = 2.2 * cm
MB     = 2.0 * cm
STRIPE = 0.5 * cm
BODY_W = PW - ML - MR - STRIPE


# ── Styles ────────────────────────────────────────────────────────────────────
def _S(name, **kw):
    return ParagraphStyle(name, **kw)

ST = {
    "cover_eye":  _S("cover_eye",  fontName=FONT_BOLD, fontSize=9,  leading=13,
                      textColor=ORO, spaceAfter=6),
    "cover_title":_S("cover_title",fontName=FONT_BOLD, fontSize=40, leading=46,
                      textColor=BIANCO, spaceAfter=12),
    "cover_sub":  _S("cover_sub",  fontName=FONT_BODY, fontSize=15, leading=23,
                      textColor=colors.HexColor("#C8DCEE"), spaceAfter=0),
    "cover_date": _S("cover_date", fontName=FONT_BODY, fontSize=9,  leading=13,
                      textColor=MUTED_LT),
    "h1":   _S("h1",  fontName=FONT_BOLD, fontSize=18, leading=24,
                textColor=BLU, spaceBefore=0, spaceAfter=8),
    "h2":   _S("h2",  fontName=FONT_BOLD, fontSize=14, leading=20,
                textColor=BLU, spaceBefore=16, spaceAfter=6),
    "h3":   _S("h3",  fontName=FONT_BOLD, fontSize=11, leading=16,
                textColor=VERDE, spaceBefore=10, spaceAfter=4),
    "body": _S("body",fontName=FONT_BODY, fontSize=10.5, leading=16,
                textColor=GRIGIO, spaceBefore=2, spaceAfter=5,
                alignment=TA_JUSTIFY),
    "body_l":_S("body_l",fontName=FONT_BODY, fontSize=10.5, leading=16,
                 textColor=GRIGIO, spaceBefore=2, spaceAfter=5),
    "bullet":_S("bullet",fontName=FONT_BODY, fontSize=10.5, leading=15,
                 textColor=GRIGIO, leftIndent=16, spaceBefore=2, spaceAfter=3),
    "bul_b": _S("bul_b",fontName=FONT_BOLD, fontSize=10.5, leading=15,
                 textColor=BLU,   leftIndent=16, spaceBefore=2, spaceAfter=3),
    "bul_w": _S("bul_w",fontName=FONT_BODY, fontSize=10,   leading=15,
                 textColor=BIANCO,leftIndent=14, spaceBefore=2, spaceAfter=3),
    "callout":    _S("callout",   fontName=FONT_BOLD, fontSize=12, leading=17,
                      textColor=BIANCO, alignment=TA_CENTER),
    "callout_sub":_S("callout_sub",fontName=FONT_BODY,fontSize=10, leading=15,
                      textColor=VERDE_LT, alignment=TA_CENTER),
    "callout_oro":_S("callout_oro",fontName=FONT_BOLD,fontSize=12, leading=17,
                      textColor=ORO, alignment=TA_CENTER),
    "label_w":_S("label_w",fontName=FONT_BOLD,fontSize=8,leading=11,
                  textColor=ORO, spaceAfter=3),
    "caption":_S("caption",fontName=FONT_ITAL,fontSize=8.5,leading=12,
                  textColor=MUTED, alignment=TA_CENTER),
    "wordmark_cover":_S("wordmark_cover",fontName=FONT_BOLD,fontSize=21,leading=25,
                      textColor=BIANCO, alignment=TA_CENTER, spaceAfter=0),
    "wordmark_pref":_S("wordmark_pref",fontName=FONT_BOLD,fontSize=16,leading=20,
                      textColor=BLU, alignment=TA_CENTER, spaceAfter=0),
    "th":   _S("th",  fontName=FONT_BOLD, fontSize=10, leading=14, textColor=BIANCO),
    "td":   _S("td",  fontName=FONT_BODY, fontSize=10, leading=14, textColor=GRIGIO),
    "td_p": _S("td_p",fontName=FONT_BOLD, fontSize=11, leading=14,
                textColor=BLU_M, alignment=TA_CENTER),
}


# ── Flowables ─────────────────────────────────────────────────────────────────

class GradBox(Flowable):
    """Rounded box with simulated top→bottom gradient."""
    def __init__(self, rows, top_c, bot_c, width=None,
                 px=0.4*cm, py=0.4*cm, r=6, steps=14):
        super().__init__()
        self._rows  = rows
        self._tc    = top_c
        self._bc    = bot_c
        self._w     = width
        self._px    = px
        self._py    = py
        self._r     = r
        self._steps = steps

    def wrap(self, aw, ah):
        self._aw = self._w or aw
        inn = self._aw - 2 * self._px
        self._dims = [p.wrap(inn, 9999) for p in self._rows]
        h = sum(d[1] for d in self._dims) + 2*self._py + (len(self._rows)-1)*4
        self._th = h
        return (self._aw, h)

    def draw(self):
        c = self.canv
        c.saveState()
        p = c.beginPath()
        p.roundRect(0, 0, self._aw, self._th, self._r)
        c.clipPath(p, stroke=0)
        tr, tg, tb = self._tc.red, self._tc.green, self._tc.blue
        br, bg, bb = self._bc.red, self._bc.green, self._bc.blue
        sh = self._th / self._steps
        for i in range(self._steps):
            t = i / max(self._steps - 1, 1)
            c.setFillColorRGB(tr+(br-tr)*t, tg+(bg-tg)*t, tb+(bb-tb)*t)
            c.rect(0, self._th-(i+1)*sh, self._aw, sh+1, fill=1, stroke=0)
        y = self._th - self._py
        for i, (para, (_, h)) in enumerate(zip(self._rows, self._dims)):
            y -= h
            para.drawOn(c, self._px, y)
            if i < len(self._rows)-1:
                y -= 4
        c.restoreState()


class ColorBox(Flowable):
    """Solid rounded box, optional border."""
    def __init__(self, rows, bg, width=None,
                 px=0.4*cm, py=0.35*cm, r=5,
                 border=None, border_w=1.0):
        super().__init__()
        self._rows = rows
        self._bg   = bg
        self._w    = width
        self._px   = px
        self._py   = py
        self._r    = r
        self._bdr  = border
        self._bw   = border_w

    def wrap(self, aw, ah):
        self._aw = self._w or aw
        inn = self._aw - 2*self._px
        self._dims = [p.wrap(inn, 9999) for p in self._rows]
        h = sum(d[1] for d in self._dims) + 2*self._py + (len(self._rows)-1)*4
        self._th = h
        return (self._aw, h)

    def draw(self):
        c = self.canv
        c.saveState()
        c.setFillColor(self._bg)
        if self._bdr:
            c.setStrokeColor(self._bdr)
            c.setLineWidth(self._bw)
            c.roundRect(0, 0, self._aw, self._th, self._r, fill=1, stroke=1)
        else:
            c.roundRect(0, 0, self._aw, self._th, self._r, fill=1, stroke=0)
        y = self._th - self._py
        for i, (para, (_, h)) in enumerate(zip(self._rows, self._dims)):
            y -= h
            para.drawOn(c, self._px, y)
            if i < len(self._rows)-1:
                y -= 4
        c.restoreState()


class LeftBar(Flowable):
    def __init__(self, paras, bar_c=BLU, bg=G_LIGHT,
                 bar_w=4, width=None, px=0.45*cm, py=0.35*cm):
        super().__init__()
        self._paras = paras
        self._bc  = bar_c
        self._bg  = bg
        self._bw  = bar_w
        self._w   = width
        self._px  = px
        self._py  = py

    def wrap(self, aw, ah):
        self._aw = self._w or aw
        inn = self._aw - self._bw - self._px*2
        self._dims = [p.wrap(inn, 9999) for p in self._paras]
        h = sum(d[1] for d in self._dims) + 2*self._py + (len(self._paras)-1)*4
        self._th = h
        return (self._aw, h)

    def draw(self):
        c = self.canv
        c.saveState()
        c.setFillColor(self._bg)
        c.roundRect(0, 0, self._aw, self._th, 5, fill=1, stroke=0)
        c.setFillColor(self._bc)
        c.roundRect(0, 0, self._bw+5, self._th, 5, fill=1, stroke=0)
        c.rect(self._bw, 0, 5, self._th, fill=1, stroke=0)
        y = self._th - self._py
        for i, (p, (_, h)) in enumerate(zip(self._paras, self._dims)):
            y -= h
            p.drawOn(c, self._bw+self._px, y)
            if i < len(self._paras)-1:
                y -= 4
        c.restoreState()


class TwoColBox(Flowable):
    def __init__(self, left_items, right_items, left_hdr, right_hdr,
                 left_col=BLU, right_col=VERDE, width=None, gap=0.4*cm):
        super().__init__()
        self._li  = left_items
        self._ri  = right_items
        self._lh  = left_hdr
        self._rh  = right_hdr
        self._lc  = left_col
        self._rc  = right_col
        self._w   = width
        self._gap = gap

    def wrap(self, aw, ah):
        self._aw = self._w or aw
        cw = (self._aw - self._gap) / 2
        self._cw = cw
        HDR, PAD = 0.62*cm, 0.38*cm
        self._hdr_h = HDR
        def col_h(items):
            h = HDR + PAD
            for p in items:
                _, ph = p.wrap(cw - 0.7*cm, 9999)
                h += ph + 4
            return h + PAD
        self._th = max(col_h(self._li), col_h(self._ri))
        return (self._aw, self._th)

    def _col(self, c, x, items, hdr, col):
        HDR, PAD = self._hdr_h, 0.38*cm
        cw, th = self._cw, self._th
        c.setFillColor(G_LIGHT)
        c.roundRect(x, 0, cw, th, 6, fill=1, stroke=0)
        c.setFillColor(col)
        c.roundRect(x, th-HDR, cw, HDR, 6, fill=1, stroke=0)
        c.rect(x, th-HDR, cw, HDR/2, fill=1, stroke=0)
        hp = Paragraph(hdr, ST["th"])
        _, hh = hp.wrap(cw-0.5*cm, 9999)
        hp.drawOn(c, x+0.25*cm, th-HDR+(HDR-hh)/2)
        y = th - HDR - PAD
        for p in items:
            _, ph = p.wrap(cw-0.7*cm, 9999)
            y -= ph
            p.drawOn(c, x+0.35*cm, y)
            y -= 4
        c.setStrokeColor(col)
        c.setLineWidth(1.4)
        c.roundRect(x, 0, cw, th, 6, fill=0, stroke=1)

    def draw(self):
        c = self.canv
        c.saveState()
        self._col(c, 0,              self._li, self._lh, self._lc)
        self._col(c, self._cw+self._gap, self._ri, self._rh, self._rc)
        c.restoreState()


class BigNumber(Flowable):
    def __init__(self, items, width=None):
        super().__init__()
        self._items = items
        self._w = width

    def wrap(self, aw, ah):
        self._aw = self._w or aw
        self._th = 3.3*cm
        return (self._aw, self._th + 4)

    def draw(self):
        c = self.canv
        c.saveState()
        n   = len(self._items)
        gap = 0.35*cm
        bw  = (self._aw - gap*(n-1)) / n
        for i, (val, label, col) in enumerate(self._items):
            x, th = i*(bw+gap), self._th
            # shadow
            c.setFillColor(colors.HexColor("#B8C4D0"))
            c.roundRect(x+3, -3, bw, th, 7, fill=1, stroke=0)
            # gradient: darker top half → lighter bottom
            dr = int(col.red   * 255 * 0.75)
            dg = int(col.green * 255 * 0.75)
            db = int(col.blue  * 255 * 0.75)
            darker = colors.HexColor(f"#{dr:02x}{dg:02x}{db:02x}")
            c.setFillColor(darker)
            c.roundRect(x, 0, bw, th, 7, fill=1, stroke=0)
            c.setFillColor(col)
            c.roundRect(x, 0, bw, th*0.58, 7, fill=1, stroke=0)
            c.rect(x, th*0.58-6, bw, 6, fill=1, stroke=0)
            # value
            c.setFillColor(BIANCO)
            c.setFont(FONT_BOLD, 30)
            c.drawCentredString(x+bw/2, th-1.48*cm, val)
            # label
            c.setFont(FONT_BODY, 8.5)
            c.setFillColor(colors.HexColor("#C8DCEE"))
            for j, part in enumerate(label.split("\n")):
                c.drawCentredString(x+bw/2, 0.62*cm - j*0.33*cm, part)
        c.restoreState()


class StepFlow(Flowable):
    def __init__(self, steps, width=None):
        super().__init__()
        self._steps = steps
        self._w = width

    def wrap(self, aw, ah):
        self._aw = self._w or aw
        self._th = 3.6*cm
        return (self._aw, self._th)

    def draw(self):
        c = self.canv
        c.saveState()
        n   = len(self._steps)
        gap = 0.55*cm
        bw  = (self._aw - gap*(n-1)) / n
        cr  = 0.68*cm
        for i, (num, label, col) in enumerate(self._steps):
            x      = i*(bw+gap)
            card_h = self._th - cr
            # card shadow
            c.setFillColor(colors.HexColor("#C0CAD6"))
            c.roundRect(x+2, -2, bw, card_h, 7, fill=1, stroke=0)
            # card
            c.setFillColor(G_LIGHT)
            c.roundRect(x, 0, bw, card_h, 7, fill=1, stroke=0)
            c.setStrokeColor(col)
            c.setLineWidth(1.6)
            c.roundRect(x, 0, bw, card_h, 7, fill=0, stroke=1)
            # circle shadow
            cx, cy = x+bw/2, self._th-cr
            c.setFillColor(colors.HexColor("#B0BCC8"))
            c.circle(cx+2, cy-2, cr, fill=1, stroke=0)
            # circle
            c.setFillColor(col)
            c.circle(cx, cy, cr, fill=1, stroke=0)
            c.setStrokeColor(colors.HexColor("#FFFFFF40"))
            c.setLineWidth(1.5)
            c.circle(cx, cy, cr-3, fill=0, stroke=1)
            # number
            c.setFillColor(BIANCO)
            c.setFont(FONT_BOLD, 21)
            c.drawCentredString(cx, cy-0.26*cm, num)
            # label
            c.setFillColor(col)
            c.setFont(FONT_BOLD, 11)
            lines = label.split("\n")
            sy = card_h/2 + len(lines)*0.21*cm
            for j, part in enumerate(lines):
                c.drawCentredString(cx, sy - j*0.43*cm, part)
            # arrow
            if i < n-1:
                c.setFillColor(MUTED)
                c.setFont(FONT_BOLD, 18)
                c.drawCentredString(x+bw+gap/2, card_h/2-0.22*cm, "›")
        c.restoreState()


class CircleLogo(Flowable):
    """Circular badge: plate + ring + centered icon image, clipped to circle."""
    def __init__(self, path, d, ring_c=ORO, ring_w=1.4, bg=BIANCO, shadow=True):
        super().__init__()
        self._path = str(path)
        self._d = d
        self._ring = ring_c
        self._rw = ring_w
        self._bg = bg
        self._shadow = shadow

    def wrap(self, aw, ah):
        return (self._d, self._d)

    def draw(self):
        c = self.canv
        c.saveState()
        r = self._d / 2
        if self._shadow:
            c.setFillColor(colors.HexColor("#00000022"))
            c.circle(r + 1.5, r - 1.5, r, fill=1, stroke=0)
        c.setFillColor(self._bg)
        c.circle(r, r, r, fill=1, stroke=0)
        inset = self._d * 0.16
        p = c.beginPath()
        p.circle(r, r, r - inset)
        c.clipPath(p, stroke=0)
        c.drawImage(self._path, inset, inset, self._d - 2*inset, self._d - 2*inset,
                    mask='auto', preserveAspectRatio=True)
        c.restoreState()
        c.saveState()
        c.setStrokeColor(self._ring)
        c.setLineWidth(self._rw)
        c.circle(r, r, r, fill=0, stroke=1)
        c.restoreState()


class SecBadge(Flowable):
    """Pill badge with section number."""
    def __init__(self, num, w=1.5*cm, h=1.5*cm):
        super().__init__()
        self._num = num
        self._w   = w
        self._h   = h

    def wrap(self, aw, ah):
        return (self._w, self._h)

    def draw(self):
        c = self.canv
        c.saveState()
        # pill
        c.setFillColor(VERDE)
        c.roundRect(0, 0, self._w, self._h, self._h/2, fill=1, stroke=0)
        # oro ring
        c.setStrokeColor(ORO)
        c.setLineWidth(1.0)
        c.roundRect(1, 1, self._w-2, self._h-2, (self._h-2)/2, fill=0, stroke=1)
        c.setFillColor(BIANCO)
        c.setFont(FONT_BOLD, 15)
        c.drawCentredString(self._w/2, (self._h-15*0.72)/2+1, self._num)
        c.restoreState()


# ── Page chrome ───────────────────────────────────────────────────────────────
def _chrome(canv, doc, cover=False):
    canv.saveState()
    if cover:
        # background
        canv.setFillColor(BLU_DARK)
        canv.rect(0, 0, PW, PH, fill=1, stroke=0)
        # deco circles top-right
        canv.setFillColor(colors.HexColor("#1C3F68"))
        canv.circle(PW-1.2*cm, PH-0.8*cm, 5.8*cm, fill=1, stroke=0)
        canv.setFillColor(colors.HexColor("#163255"))
        canv.circle(PW-0.5*cm, PH-0.2*cm, 3.9*cm, fill=1, stroke=0)
        # deco circle bottom-left
        canv.setFillColor(colors.HexColor("#1C3F68"))
        canv.circle(1.2*cm, 2.2*cm, 2.4*cm, fill=1, stroke=0)
        # left stripe
        canv.setFillColor(VERDE)
        canv.rect(0, 0, STRIPE, PH, fill=1, stroke=0)
        # bottom band
        canv.setFillColor(VERDE_D)
        canv.rect(0, 0, PW, 1.5*cm, fill=1, stroke=0)
        # gold accent line above bottom band
        canv.setFillColor(ORO)
        canv.rect(STRIPE, 1.5*cm, PW-STRIPE, 2.5, fill=1, stroke=0)
    else:
        canv.setFillColor(G_XL)
        canv.rect(0, 0, PW, PH, fill=1, stroke=0)
        # left stripe
        canv.setFillColor(VERDE)
        canv.rect(0, 0, STRIPE, PH, fill=1, stroke=0)
        # header bar
        canv.setFillColor(BLU)
        canv.rect(0, PH-1.05*cm, PW, 1.05*cm, fill=1, stroke=0)
        # gold line under header
        canv.setFillColor(ORO)
        canv.rect(0, PH-1.05*cm-2.5, PW, 2.5, fill=1, stroke=0)
        canv.setFillColor(BIANCO)
        canv.setFont(FONT_BOLD, 8)
        canv.drawString(ML+STRIPE+0.2*cm, PH-0.68*cm, "Credito Salute SQ")
        canv.setFont(FONT_BODY, 8)
        canv.setFillColor(MUTED_LT)
        canv.drawRightString(PW-MR, PH-0.68*cm, "Salute Quotidiana")
        # footer
        canv.setFillColor(BLU_DARK)
        canv.rect(0, 0, PW, 0.88*cm, fill=1, stroke=0)
        canv.setFillColor(VERDE)
        canv.rect(STRIPE, 0, PW-STRIPE, 2.5, fill=1, stroke=0)
        canv.setFont(FONT_BODY, 7)
        canv.setFillColor(MUTED_LT)
        canv.drawString(ML+STRIPE+0.2*cm, 0.31*cm, "Documento riservato · Luglio 2026")
        if hasattr(doc, 'page'):
            canv.setFont(FONT_BOLD, 8)
            canv.setFillColor(BIANCO)
            canv.drawRightString(PW-MR, 0.31*cm, str(doc.page))
    canv.restoreState()


class CoverTpl(PageTemplate):
    def __init__(self):
        f = Frame(ML+STRIPE, 1.5*cm, BODY_W, PH-1.5*cm-2.8*cm,
                  leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
        super().__init__('cover', [f])
    def beforeDrawPage(self, canv, doc):
        _chrome(canv, doc, cover=True)


class BodyTpl(PageTemplate):
    def __init__(self):
        f = Frame(ML+STRIPE, MB+0.88*cm, BODY_W,
                  PH-MT-MB-1.05*cm-0.88*cm,
                  leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
        super().__init__('body', [f])
    def beforeDrawPage(self, canv, doc):
        _chrome(canv, doc, cover=False)


# ── Helpers ───────────────────────────────────────────────────────────────────
def P(text, s="body"):
    return Paragraph(text, ST[s] if isinstance(s, str) else s)

def SP(h=0.3):
    return Spacer(1, h*cm)

def HR(col=BLU_LT, t=0.8):
    return HRFlowable(width="100%", thickness=t, color=col,
                      spaceAfter=8, spaceBefore=4)


def sec_hdr(num, title):
    """Returns list of flowables: badge+title row + gold rule."""
    bw = 1.55*cm
    return [
        SP(0.3),
        Table(
            [[SecBadge(num, bw, 1.55*cm),
              Table([[P(title, "h1")]],
                    colWidths=[BODY_W-bw-0.3*cm],
                    style=TableStyle([
                        ("LEFTPADDING",(0,0),(-1,-1),10),
                        ("RIGHTPADDING",(0,0),(-1,-1),0),
                        ("TOPPADDING",(0,0),(-1,-1),0),
                        ("BOTTOMPADDING",(0,0),(-1,-1),0),
                        ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
                    ]))]],
            colWidths=[bw, BODY_W-bw],
            style=TableStyle([
                ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
                ("LEFTPADDING",(0,0),(-1,-1),0),
                ("RIGHTPADDING",(0,0),(-1,-1),0),
                ("TOPPADDING",(0,0),(-1,-1),2),
                ("BOTTOMPADDING",(0,0),(-1,-1),2),
            ])
        ),
        HRFlowable(width="100%", thickness=2, color=ORO,
                   spaceAfter=10, spaceBefore=4),
    ]


def sec_block(num, title, *first_items):
    """CondPageBreak + KeepTogether([header + first_items])."""
    hdr = sec_hdr(num, title)
    return [
        CondPageBreak(9*cm),
        KeepTogether(hdr + list(first_items)),
    ]


def listino(rows_inf, rows_tele):
    half = (BODY_W - 0.5*cm) / 2

    def mk(rows, hcol):
        data = [[P("Prestazione","th"), P("Costo","th")]]
        for n, p in rows:
            data.append([P(n,"td"), P(p,"td_p")])
        t = Table(data, colWidths=[half*0.78, half*0.22])
        t.setStyle(TableStyle([
            ("BACKGROUND",    (0,0),(-1,0), hcol),
            ("ROWBACKGROUNDS",(0,1),(-1,-1),[BIANCO, G_MED]),
            ("GRID",          (0,0),(-1,-1), 0.5, BLU_LT),
            ("LINEBELOW",     (0,0),(-1,0),  1.5, hcol),
            ("VALIGN",        (0,0),(-1,-1),"MIDDLE"),
            ("TOPPADDING",    (0,0),(-1,-1), 6),
            ("BOTTOMPADDING", (0,0),(-1,-1), 6),
            ("LEFTPADDING",   (0,0),(-1,-1), 8),
            ("RIGHTPADDING",  (0,0),(-1,-1), 8),
        ]))
        return t

    ti = mk(rows_inf,  BLU)
    tt = mk(rows_tele, VERDE)
    outer = Table([[ti, SP(0), tt]], colWidths=[half, 0.5*cm, half])
    outer.setStyle(TableStyle([
        ("VALIGN",(0,0),(-1,-1),"TOP"),
        ("LEFTPADDING",(0,0),(-1,-1),0),
        ("RIGHTPADDING",(0,0),(-1,-1),0),
        ("TOPPADDING",(0,0),(-1,-1),0),
        ("BOTTOMPADDING",(0,0),(-1,-1),0),
    ]))
    return outer


# ── Story ─────────────────────────────────────────────────────────────────────
def build_story():
    story = []

    # COVER
    logo_cover = CircleLogo(LOGO_ICON_PATH, 3.2*cm, ring_c=ORO, bg=BIANCO)
    logo_cover.hAlign = "CENTER"
    story += [
        SP(2.0),
        logo_cover,
        SP(0.4),
        P("Salute Quotidiana", "wordmark_cover"),
        SP(0.5),
        P("UN PROGRAMMA DI SALUTE QUOTIDIANA", "cover_eye"),
        SP(0.3),
        P("Credito Salute SQ", "cover_title"),
        SP(0.5),
        P("La spesa di tutti i giorni diventa accesso<br/>"
          "a cure infermieristiche a domicilio.", "cover_sub"),
        SP(2.8),
        P("Luglio 2026", "cover_date"),
        PageBreak(),
    ]

    # ── PREFAZIONE ────────────────────────────────────────────────────────────
    logo_pref = CircleLogo(LOGO_ICON_PATH, 2.4*cm, ring_c=VERDE, bg=BIANCO)
    logo_pref.hAlign = "CENTER"
    story += [
        SP(0.2),
        logo_pref,
        SP(0.3),
        P("Salute Quotidiana", "wordmark_pref"),
        SP(0.4),
        P("Prefazione", "h1"),
        HRFlowable(width="100%", thickness=2, color=ORO, spaceAfter=10, spaceBefore=4),
        P("Perché nasce Salute Quotidiana", "h2"),
        P("Da oltre un decennio la spesa sanitaria pubblica italiana cresce meno del "
          "fabbisogno reale. La Fondazione GIMBE, il riferimento indipendente più citato "
          "in Italia sul finanziamento del Servizio Sanitario Nazionale, documenta ogni "
          "anno un definanziamento strutturale del SSN: la spesa pubblica resta stabilmente "
          "sotto la media dei paesi europei ad economia comparabile. La Corte dei Conti, "
          "nelle relazioni annuali sulla gestione finanziaria degli enti sanitari, segnala "
          "gli stessi squilibri: liste d'attesa più lunghe, personale insufficiente, "
          "prestazioni rinviate anno dopo anno."),
        SP(0.3),
        P("Non è un'emergenza improvvisa, è l'effetto accumulato di anni di risorse "
          "insufficienti rispetto ai bisogni reali della popolazione. Lo misura direttamente "
          "l'ISTAT: una parte crescente di famiglie italiane rinuncia a curarsi. Non per "
          "mancanza di bisogno, ma per i costi, per i tempi di attesa, per la fatica di "
          "organizzare anche una prestazione semplice. Chi è anziano, ha mobilità ridotta o "
          "vive in un piccolo centro lontano dai servizi resta indietro più di tutti."),
        SP(0.3),
        LeftBar([
            P("Salute Quotidiana nasce da qui. Non sostituisce il sistema sanitario pubblico "
              "e non interviene sulle sue politiche: risponde in modo pratico e locale a un "
              "bisogno concreto. È <b>una rete di prossimità che usa risorse già presenti sul "
              "territorio</b>, il budget promozionale degli esercizi commerciali di prossimità, "
              "per avvicinare l'accesso a prestazioni infermieristiche di base, qui e adesso, "
              "senza aspettare che il quadro nazionale cambi.", "body_l"),
        ], bar_c=VERDE, bg=VERDE_LT, width=BODY_W),
        SP(0.4),
        P("Fonti: Fondazione GIMBE, Rapporto annuale sul definanziamento del SSN · "
          "Corte dei Conti, Relazione sulla gestione finanziaria degli enti del Servizio "
          "sanitario nazionale · ISTAT, indagini su rinuncia alle cure.", "caption"),
        PageBreak(),
    ]

    # ── 01 ────────────────────────────────────────────────────────────────────
    story += sec_block("01", "Il budget promozionale non lascia nulla",
        P("Ogni anno, esercizi commerciali investono in gadget, volantini, calendari e omaggi. "
          "Il cliente li dimentica nel giro di pochi giorni. Il budget è speso, "
          "la fidelizzazione non c'è, e l'anno dopo si ricomincia da capo."),
        SP(0.3),
        P("Il vero problema è dove finisce quel budget, non quanto se ne investe."),
    )
    story += [
        SP(0.5),
        TwoColBox(
            left_items=[
                P("❌  Gadget che nessuno usa", "bullet"),
                P("❌  Volantini dimenticati il giorno dopo", "bullet"),
                P("❌  Calendari appesi e poi gettati", "bullet"),
                P("❌  Nessun ritorno misurabile", "bullet"),
                SP(0.2),
                P("<b>Risultato: budget speso, fidelizzazione zero.</b>", "body_l"),
            ],
            right_items=[
                P("✔  Credito reale su cure infermieristiche", "bul_b"),
                P("✔  Accumulato con acquisti già abituali", "bul_b"),
                P("✔  Cedibile a chiunque il cliente voglia", "bul_b"),
                P("✔  Report periodico con dati reali", "bul_b"),
                SP(0.2),
                P("<b>Risultato: budget reinvestito, fiducia costruita.</b>", "body_l"),
            ],
            left_hdr="PROMOZIONE TRADIZIONALE",
            right_hdr="CON CREDITO SALUTE SQ",
            left_col=colors.HexColor("#7A1A1A"),
            right_col=VERDE,
            width=BODY_W,
        ),
        SP(0.5),
    ]

    # ── 02 ────────────────────────────────────────────────────────────────────
    story += sec_block("02", "Le famiglie rimandano cure che potrebbero fare adesso",
        P("1 italiano su 3 rinuncia a curarsi. Non per scarsità di offerta sanitaria, "
          "ma per costi, per i tempi di attesa, per la complessità organizzativa "
          "di prenotare anche una prestazione semplice."),
        SP(0.3),
        P("Prelievi, medicazioni, iniezioni, controlli di base: prestazioni tecnicamente "
          "semplici che molte famiglie rimandano di settimane. "
          "Chi è anziano o ha mobilità ridotta aspetta più di tutti."),
    )
    story += [
        SP(0.5),
        LeftBar([
            P("<b>L'opportunità:</b> è concreta e locale, per chi già serve queste famiglie "
              "ogni giorno. Non serve aspettare un cambiamento della sanità pubblica.",
              "body_l"),
        ], bar_c=VERDE, bg=VERDE_LT, width=BODY_W),
        SP(0.5),
    ]

    # ── 03 ────────────────────────────────────────────────────────────────────
    story += sec_block("03", "Il budget già esiste — mancava solo dove farlo atterrare",
        P("Salute Quotidiana prende il budget promozionale di un esercizio commerciale "
          "e lo orienta verso un beneficio che i clienti ricordano: "
          "accesso a prestazioni infermieristiche domiciliari."),
    )
    _cw = (BODY_W - 1.2*cm) / 3
    _arr = ParagraphStyle("arr", fontName=FONT_BOLD, fontSize=18,
                          textColor=MUTED, alignment=TA_CENTER)
    flow_t = Table([[
        GradBox([P("Budget<br/>promozionale","callout"),
                 P("già stanziato dall'esercizio","callout_sub")],
                BLU, BLU_DARK, width=_cw, py=0.5*cm),
        Paragraph("▶", _arr),
        GradBox([P("Fondo<br/>Credito SQ","callout"),
                 P("gestito da Salute Quotidiana","callout_sub")],
                VERDE, VERDE_D, width=_cw, py=0.5*cm),
        Paragraph("▶", _arr),
        GradBox([P("Cura<br/>a domicilio","callout"),
                 P("per i clienti dell'esercizio","callout_sub")],
                VERDE_D, VERDE_XD, width=_cw, py=0.5*cm),
    ]], colWidths=[_cw, 0.6*cm, _cw, 0.6*cm, _cw])
    flow_t.setStyle(TableStyle([
        ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
        ("LEFTPADDING",(0,0),(-1,-1),0), ("RIGHTPADDING",(0,0),(-1,-1),0),
        ("TOPPADDING",(0,0),(-1,-1),0),  ("BOTTOMPADDING",(0,0),(-1,-1),0),
    ]))
    story += [
        SP(0.4), flow_t, SP(0.4),
        LeftBar([
            P("Il valore resta nel territorio, senza intermediari finanziari. "
              "<b>È lo stesso budget di sempre, solo indirizzato dove conta davvero.</b>",
              "body_l"),
        ], bar_c=BLU_M, bg=BLU_LT, width=BODY_W),
        SP(0.5),
    ]

    # ── 04 ────────────────────────────────────────────────────────────────────
    story += sec_block("04", "La formula: 15% della spesa diventa credito reale",
        P("Ogni euro speso dal cliente presso l'esercizio aderente genera credito "
          "Credito SQ, spendibile direttamente sulle prestazioni infermieristiche."),
    )
    _hw = (BODY_W - 0.5*cm) / 2
    formula_l = [
        SP(0.1),
        P("• <b>15%</b> della spesa valida → Credito Salute SQ", "bullet"),
        P("• 1 euro SQ = 1 euro di sconto sulle prestazioni", "bullet"),
        P("• Cedibile a chiunque, senza vincoli di parentela", "bullet"),
        P("• Fondo fisso all'avvio: zero costi variabili per l'esercizio", "bullet"),
    ]
    formula_r = GradBox([
        P("ESEMPIO PRATICO", "label_w"),
        SP(0.1),
        P("100 € al mese di acquisti abituali", "callout_sub"),
        P("<b>→ 15 euro SQ al mese</b>", "callout"),
        SP(0.1),
        P("In 2 mesi: prelievo + medicazione", "callout_sub"),
        P("<b>a costo zero.</b>", "callout_oro"),
    ], VERDE, VERDE_D, width=_hw, py=0.45*cm)

    ftbl = Table(
        [[Table([[p] for p in formula_l], colWidths=[_hw],
                style=TableStyle([
                    ("LEFTPADDING",(0,0),(-1,-1),0),("RIGHTPADDING",(0,0),(-1,-1),0),
                    ("TOPPADDING",(0,0),(-1,-1),0), ("BOTTOMPADDING",(0,0),(-1,-1),2),
                ])),
          Spacer(0.5*cm, 1), formula_r]],
        colWidths=[_hw, 0.5*cm, _hw]
    )
    ftbl.setStyle(TableStyle([
        ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
        ("LEFTPADDING",(0,0),(-1,-1),0),("RIGHTPADDING",(0,0),(-1,-1),0),
        ("TOPPADDING",(0,0),(-1,-1),0), ("BOTTOMPADDING",(0,0),(-1,-1),0),
    ]))
    story += [SP(0.35), ftbl, SP(0.5)]

    # ── 05 ────────────────────────────────────────────────────────────────────
    story += sec_block("05", "Tre ruoli, zero gestione sanitaria per l'esercizio",
        P("Il programma funziona perché ogni ruolo è separato e non si sovrappone. "
          "L'esercizio non tocca mai nulla di sanitario."),
    )
    cw3 = (BODY_W - 0.6*cm) / 3
    _note = ParagraphStyle("note_w", fontName=FONT_ITAL, fontSize=9,
                           textColor=BLU_LT, leading=13)
    roles = Table([[
        GradBox([P("Esercizio commerciale","th"), SP(0.15),
                 P("• Stanzia il fondo promozionale","bul_w"),
                 P("• Espone il materiale informativo","bul_w"),
                 P("• Invita i clienti con parole proprie","bul_w"),
                 SP(0.1), Paragraph("<i>Impegno: 3 azioni. Poi gira da solo.</i>", _note)],
                BLU, BLU_DARK, width=cw3, py=0.4*cm),
        Spacer(0.3*cm, 1),
        GradBox([P("Cliente","th"), SP(0.15),
                 P("• Si iscrive una sola volta","bul_w"),
                 P("• Carica gli scontrini via browser","bul_w"),
                 P("• Accumula credito verificato","bul_w"),
                 P("• Usa il credito quando vuole","bul_w")],
                BLU_M, BLU, width=cw3, py=0.4*cm),
        Spacer(0.3*cm, 1),
        GradBox([P("Salute Quotidiana","th"), SP(0.15),
                 P("• Gestisce iscrizioni e verifiche","bul_w"),
                 P("• Amministra il fondo","bul_w"),
                 P("• Organizza prenotazioni e prestazioni","bul_w"),
                 P("• Produce il report periodico","bul_w")],
                VERDE, VERDE_D, width=cw3, py=0.4*cm),
    ]], colWidths=[cw3, 0.3*cm, cw3, 0.3*cm, cw3])
    roles.setStyle(TableStyle([
        ("VALIGN",(0,0),(-1,-1),"TOP"),
        ("LEFTPADDING",(0,0),(-1,-1),0),("RIGHTPADDING",(0,0),(-1,-1),0),
        ("TOPPADDING",(0,0),(-1,-1),0), ("BOTTOMPADDING",(0,0),(-1,-1),0),
    ]))
    story += [SP(0.45), roles, SP(0.5)]

    # ── 06 — sempre su pagina nuova ───────────────────────────────────────────
    story.append(PageBreak())
    story += sec_hdr("06", "Dodici prestazioni a domicilio")
    story += [
        SP(0.1),
        P("Tutte le prestazioni sono erogate da un professionista infermieristico abilitato, "
          "su appuntamento, presso il domicilio del cliente o della persona indicata. "
          "Con 100 euro al mese di acquisti abituali si accumulano 15 crediti SQ: "
          "sufficienti per un prelievo e una medicazione in due mesi, a costo zero."),
        SP(0.4),
        Table(
            [[P("Prestazioni infermieristiche a domicilio","h3"),
              SP(0),
              P("Telemedicina a domicilio <i>(in arrivo)</i>","h3")]],
            colWidths=[(BODY_W-0.5*cm)/2, 0.5*cm, (BODY_W-0.5*cm)/2],
            style=TableStyle([("LEFTPADDING",(0,0),(-1,-1),0),
                              ("RIGHTPADDING",(0,0),(-1,-1),0),
                              ("TOPPADDING",(0,0),(-1,-1),0),
                              ("BOTTOMPADDING",(0,0),(-1,-1),0)])
        ),
        SP(0.15),
        listino(
            rows_inf=[
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
            ],
            rows_tele=[
                ("ECG a 12 derivazioni", "30 €"),
                ("Holter ECG 24h", "45 €"),
                ("Holter Pressorio 24h", "40 €"),
                ("Spirometria semplice", "30 €"),
            ],
        ),
        SP(0.5),
    ]

    # ── 07 ────────────────────────────────────────────────────────────────────
    story += sec_block("07", "Per l'esercizio: tre passi, poi il programma gira da solo",
        P("L'impegno per l'esercizio è minimo e si esaurisce nell'avvio. "
          "Non è richiesto alcun training per il personale, "
          "né alcuna gestione quotidiana delle attività sanitarie."),
    )
    story += [
        SP(0.5),
        StepFlow([("1","Firma\nil contratto",BLU),
                  ("2","Versa\nil fondo",BLU_M),
                  ("3","Invita\ni clienti",VERDE)], width=BODY_W),
        SP(0.55),
        LeftBar([
            P("<b>Tutto il resto è gestito da Salute Quotidiana:</b> "
              "iscrizioni, verifiche, prenotazioni, prestazioni.", "body_l"),
            P("A fine periodo: report con dati reali — iscritti, credito accumulato, "
              "credito utilizzato, fondo residuo.", "body_l"),
        ], bar_c=VERDE, bg=VERDE_LT, width=BODY_W),
        SP(0.5),
    ]

    # ── 08 ────────────────────────────────────────────────────────────────────
    story += sec_block("08", "Il credito si usa per sé — o si dà a chi ne ha bisogno",
        P("Il credito Salute SQ non è vincolato alla persona che l'ha accumulato. "
          "Il titolare può cedere tutto o parte del proprio credito a chiunque voglia: "
          "un familiare, un vicino, un amico — senza vincoli di parentela o convivenza."),
        SP(0.3),
        P("L'unica condizione è che il destinatario sia iscritto alla piattaforma "
          "(iscrizione gratuita, richiesta a fini statistici). "
          "Nessun abbonamento, nessuna spesa aggiuntiva."),
    )
    story += [
        SP(0.45),
        GradBox([
            P("Un beneficio che si condivide, non solo un vantaggio individuale.", "callout"),
            P("Con la cedibilità, il credito smette di essere solo del cliente "
              "e diventa un beneficio per la comunità.", "callout_sub"),
        ], BLU, BLU_DARK, width=BODY_W, py=0.45*cm),
        SP(0.4),
        LeftBar([
            P("<b>Lista dei Silenziosi:</b> chi vuole può donare credito in forma anonima "
              "a un fondo condiviso. Chi ha bisogno accede compilando un questionario "
              "riservato: la ripartizione tra beneficiari è dinamica e proporzionale "
              "al bisogno espresso, senza tetto di spesa.", "body_l"),
        ], bar_c=VERDE, bg=VERDE_LT, width=BODY_W),
        SP(0.5),
    ]

    # ── 09 ────────────────────────────────────────────────────────────────────
    story += sec_block("09", "Il pilot: rischio massimo già definito prima di firmare",
        P("Il primo ciclo è un pilot a scala controllata: pensato per produrre dati concreti "
          "tenendo il rischio al minimo."),
    )
    story += [
        SP(0.45),
        BigNumber([
            ("1",      "esercizio\ncommerciale", BLU),
            ("20",     "clienti\nper ciclo",     BLU_M),
            ("30",     "giorni\ndi durata",      VERDE),
            ("1.000 €","fondo\nstanziato",       VERDE_D),
        ], width=BODY_W),
        SP(0.55),
        P("Il pilot produce dati concreti su:", "h3"),
        P("• Quanti clienti si iscrivono e con quale velocità", "bullet"),
        P("• Quanto credito accumulano e in che tempi", "bullet"),
        P("• Quali prestazioni scelgono con maggiore frequenza", "bullet"),
        SP(0.35),
        GradBox([
            P("Rischio massimo = fondo stanziato.", "callout"),
            P("Nessun costo variabile fuori controllo: quello che si versa è quello "
              "che si rischia, non un euro di più.", "callout_sub"),
        ], VERDE, VERDE_D, width=BODY_W, py=0.4*cm),
        SP(0.5),
    ]

    # ── 10 ────────────────────────────────────────────────────────────────────
    story += sec_block("10", "La piattaforma funziona già",
        P("Si usa da qualsiasi smartphone via browser, senza installare nulla e senza "
          "training per lo staff. Ogni ruolo ha una vista dedicata "
          "con accesso esclusivo ai propri dati."),
    )
    cw3b = (BODY_W - 0.6*cm) / 3
    _roles10 = [
        ("Cliente",           BLU,   BLU_DARK, ["Saldo credito in tempo reale",
                                                 "Caricamento scontrino con foto",
                                                 "Storico movimenti e scontrini",
                                                 "Prenotazione prestazione con i crediti",
                                                 "Conferma prestazione con QR anti-imbroglio"]),
        ("Esercizio",         BLU_M, BLU,      ["Dashboard iscritti e crediti",
                                                 "Verifica stato del fondo",
                                                 "Accesso al report periodico",
                                                 "Esportazione PDF a fine ciclo"]),
        ("Salute Quotidiana", VERDE, VERDE_D,  ["Gestione iscrizioni e profili",
                                                 "Verifica scontrini e crediti",
                                                 "Amministrazione prenotazioni",
                                                 "Report completo per esercizio"]),
    ]
    p_cells = []
    for title, tc, bc, bullets in _roles10:
        rows = [P(title, "th"), SP(0.12)] + [P("• "+b, "bul_w") for b in bullets]
        p_cells.append(GradBox(rows, tc, bc, width=cw3b, py=0.4*cm))
    pt = Table(
        [[p_cells[0], Spacer(0.3*cm,1), p_cells[1], Spacer(0.3*cm,1), p_cells[2]]],
        colWidths=[cw3b, 0.3*cm, cw3b, 0.3*cm, cw3b]
    )
    pt.setStyle(TableStyle([
        ("VALIGN",(0,0),(-1,-1),"TOP"),
        ("LEFTPADDING",(0,0),(-1,-1),0),("RIGHTPADDING",(0,0),(-1,-1),0),
        ("TOPPADDING",(0,0),(-1,-1),0), ("BOTTOMPADDING",(0,0),(-1,-1),0),
    ]))
    story += [
        SP(0.4), pt, SP(0.3),
        P("Stack: HTML/CSS/JS + Supabase, nessuna installazione richiesta. "
          "Funziona su qualsiasi smartphone, anche datato.", "caption"),
        SP(0.5),
    ]

    # ── 11 ────────────────────────────────────────────────────────────────────
    story += sec_block("11", "Il programma parte questa settimana",
        P("Il primo esercizio è già attivo. "
          "Il pilot è in corso, i dati saranno disponibili a fine ciclo."),
    )
    cta_w = (BODY_W - 0.5*cm) / 2
    cta_l = GradBox([
        P("PER L'ESERCIZIO COMMERCIALE", "label_w"), SP(0.12),
        P("1.  Contatta Salute Quotidiana", "bul_w"),
        P("2.  Definisci fondo e durata",   "bul_w"),
        P("3.  Firma il contratto",         "bul_w"),
        P("4.  Avvia il programma",         "bul_w"),
    ], BLU, BLU_XD, width=cta_w, py=0.45*cm)
    cta_r = GradBox([
        P("PER IL PARTNER / FINANZIATORE", "label_w"), SP(0.12),
        P("1.  Richiedi i risultati del pilot",      "bul_w"),
        P("2.  Valuta l'estensione del modello",     "bul_w"),
        P("3.  Definisci l'accordo di partnership",  "bul_w"),
    ], VERDE, VERDE_XD, width=cta_w, py=0.45*cm)
    cta_t = Table([[cta_l, Spacer(0.5*cm,1), cta_r]],
                  colWidths=[cta_w, 0.5*cm, cta_w])
    cta_t.setStyle(TableStyle([
        ("VALIGN",(0,0),(-1,-1),"TOP"),
        ("LEFTPADDING",(0,0),(-1,-1),0),("RIGHTPADDING",(0,0),(-1,-1),0),
        ("TOPPADDING",(0,0),(-1,-1),0), ("BOTTOMPADDING",(0,0),(-1,-1),0),
    ]))
    story += [
        SP(0.45),
        KeepTogether([cta_t]),
        SP(0.55),
        LeftBar([
            P("<b>Contatti:</b> angelo.rosso073@gmail.com", "body_l"),
            P("Pilot già attivo, rischio già definito prima di firmare.", "body_l"),
        ], bar_c=ORO, bg=ORO_LT, width=BODY_W),
        SP(0.9),
        HR(BLU_LT),
        P("Credito Salute SQ  ·  Salute Quotidiana  ·  Documento riservato  ·  Luglio 2026",
          "caption"),
    ]

    return story


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    doc = BaseDocTemplate(
        str(OUT), pagesize=A4,
        leftMargin=0, rightMargin=0, topMargin=0, bottomMargin=0,
        title="Credito Salute SQ — Presentazione",
        author="Salute Quotidiana",
        subject="Documento di presentazione commerciale",
    )
    doc.addPageTemplates([CoverTpl(), BodyTpl()])
    story = build_story()
    story.insert(0, NextPageTemplate('cover'))
    pb_idx = next(i for i,f in enumerate(story) if isinstance(f, PageBreak))
    story.insert(pb_idx, NextPageTemplate('body'))
    doc.build(story)
    shutil.move(str(OUT), str(_FINAL_OUT))
    print(f"OK  {_FINAL_OUT.name}")


if __name__ == "__main__":
    main()
