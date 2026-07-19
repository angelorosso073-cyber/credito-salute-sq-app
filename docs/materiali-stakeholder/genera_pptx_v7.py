# -*- coding: utf-8 -*-
"""
Genera 7-presentazione-generale-2.pptx
Aggiunge slide PREMESSA (versione lunga + wireframe 3 schermate) come slide 2.
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

# ── Importa tutto da genera_pptx ─────────────────────────────────────────────
sys.path.insert(0, str(Path(__file__).parent))
from genera_pptx import (
    new_prs, blank_layout, add_rect, add_textbox, tf_para, set_tf,
    add_body_text, add_table_sq, slide_with_header,
    slide_cover, slide_2, slide_3, slide_4, slide_5, slide_6,
    slide_7, slide_8, slide_9, slide_10, slide_11, slide_chiusura,
    BLU_SCURO, BLU_MEDIO, VERDE, GRIGIO_TESTO, BIANCO,
    GRIGIO_LIGHT, GRIGIO_RIGA, FONT, W, H, L, R, CW, CT, CB
)

OUTPUT = Path(__file__).parent / "7-presentazione-generale-2.pptx"

# ── Colori aggiuntivi ─────────────────────────────────────────────────────────
VERDE_LT = RGBColor(0xD6, 0xEE, 0xE2)
BLU_LT   = RGBColor(0xD6, 0xE4, 0xF0)

# ── Costanti layout premessa ──────────────────────────────────────────────────
CONTENT_H   = H - CT - Cm(1.2)          # altezza area contenuto
TEXT_H      = CONTENT_H * 0.37          # 37% al testo
WIRE_TOP    = CT + TEXT_H + Cm(0.35)    # wireframe inizia qui
WIRE_H      = H - WIRE_TOP - Cm(0.9)   # altezza area wireframe


def add_para(tf, text, size, color=GRIGIO_TESTO, bold=False, italic=False,
             align=PP_ALIGN.LEFT, spc_b=0, spc_a=1, line_pct=90):
    """Aggiunge paragrafo con spaziatura fine."""
    if tf.paragraphs and tf.paragraphs[0].text == '' and not tf.paragraphs[0].runs:
        p = tf.paragraphs[0]
    else:
        p = tf.add_paragraph()
    p.alignment = align
    run = p.add_run()
    run.text = text
    run.font.name   = FONT
    run.font.size   = Pt(size)
    run.font.bold   = bold
    run.font.italic = italic
    run.font.color.rgb = color
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


def draw_text_premessa(slide):
    """Versione lunga della premessa ideologica — top 37% del contenuto."""
    tb = add_textbox(slide, L, CT, CW, TEXT_H)
    tf = tb.text_frame
    tf.word_wrap = True

    add_para(tf, 'Non siamo nati per competere. Siamo nati per costruire.',
             10, BLU_SCURO, bold=True, spc_b=0, spc_a=3)

    add_para(tf, 'Chi gestisce un’attivit\xe0 commerciale oggi lo sa meglio di chiunque altro: '
                 'il sistema premia chi taglia, chi sgomita, chi mette il proprio interesse davanti a tutto il resto. '
                 'Ti dicono che \xe8 sempre stato cos\xec. Che \xe8 la natura delle cose. Che non c’\xe8 alternativa.',
             7, GRIGIO_TESTO, spc_b=0, spc_a=0)

    add_para(tf, 'Non \xe8 vero.',
             7.5, BLU_SCURO, bold=True, spc_b=2, spc_a=2)

    add_para(tf, 'Per secoli le comunit\xe0 hanno prosperato non perch\xe9 i pi\xf9 forti schiacciassero i pi\xf9 deboli, '
                 'ma perch\xe9 le persone hanno scelto di stare dalla stessa parte. '
                 'Il macellaio, il farmacista, il bar sotto casa non erano concorrenti — '
                 'erano parte dello stesso tessuto. Si reggevano a vicenda. Reggevano il quartiere.',
             7, GRIGIO_TESTO, spc_b=0, spc_a=0)

    add_para(tf, 'Quel tessuto si \xe8 sfilacciato. Non da solo — \xe8 stato sfilacciato. '
                 'Da logiche lontane da qui, da interessi che con la tua bottega, il tuo negozio, '
                 'la tua famiglia non hanno nulla a che fare.',
             7, GRIGIO_TESTO, spc_b=2, spc_a=0)

    add_para(tf, 'Salute Quotidiana nasce da una domanda semplice: '
                 'e se ogni gesto quotidiano — una spesa, un caff\xe8, un acquisto — '
                 'diventasse un atto di cura verso qualcuno della tua comunit\xe0?',
             7, BLU_SCURO, spc_b=2, spc_a=0)

    add_para(tf, 'Non charity. Non beneficenza. Un meccanismo concreto, misurabile, sostenibile — '
                 'dove chi compra accumula salute, chi vende costruisce fiducia, '
                 'chi cura riceve dignit\xe0 economica.',
             7, GRIGIO_TESTO, spc_b=2, spc_a=0)

    add_para(tf, 'Nessuno si arricchisce sulle spalle degli altri. Il valore rimane qui, circola qui, serve qui.',
             7, GRIGIO_TESTO, spc_b=1, spc_a=0)

    add_para(tf, 'Aderire a Salute Quotidiana non \xe8 una scelta di marketing. '
                 '\xc8 una scelta di campo. '
                 '\xc8 decidere, con un gesto piccolo e quotidiano, '
                 'che esiste un altro modo di stare nel mondo.',
             7, GRIGIO_TESTO, spc_b=2, spc_a=0)

    add_para(tf, 'E che quel mondo comincia dal tuo negozio.',
             8.5, BLU_SCURO, bold=True, spc_b=3, spc_a=0)

    add_para(tf, '— Eccolo, dall’interno.',
             7, VERDE, italic=True, spc_b=3, spc_a=0)


def draw_screen(slide, sx, sw, sh, header_text, rows, header_color=BLU_SCURO):
    """Disegna una schermata mockup nel range y=[WIRE_TOP, WIRE_TOP+sh]."""
    sy = WIRE_TOP
    HDR_H  = Cm(0.75)
    PAD    = Cm(0.22)
    ROW_H  = (sh - HDR_H - PAD * 2) / max(len(rows), 1)

    # Bordo esterno
    border = slide.shapes.add_shape(1, sx, sy, sw, sh)
    border.fill.solid(); border.fill.fore_color.rgb = BIANCO
    border.line.color.rgb = BLU_SCURO
    border.line.width = Cm(0.04)

    # Header bar
    hdr = add_rect(slide, sx, sy, sw, HDR_H, header_color)

    # Header text
    tb_h = add_textbox(slide, sx + PAD, sy + Cm(0.1), sw - PAD * 2, HDR_H)
    tf_h = tb_h.text_frame
    p_h  = tf_h.paragraphs[0]; p_h.alignment = PP_ALIGN.LEFT
    run  = p_h.add_run()
    run.text = header_text
    run.font.name = FONT; run.font.size = Pt(6.5)
    run.font.bold = True; run.font.color.rgb = BIANCO

    # Righe contenuto
    cy = sy + HDR_H + PAD
    for row in rows:
        text    = row.get('text', '')
        size    = row.get('size', 6.5)
        color   = row.get('color', GRIGIO_TESTO)
        bold    = row.get('bold', False)
        italic  = row.get('italic', False)
        bg      = row.get('bg', None)
        align   = row.get('align', PP_ALIGN.LEFT)
        h_mult  = row.get('h', 1.0)
        rh      = ROW_H * h_mult

        if bg:
            add_rect(slide, sx + PAD * 0.3, cy, sw - PAD * 0.6, rh - Cm(0.04), bg)

        if text:
            tb_r = add_textbox(slide, sx + PAD, cy + Cm(0.04),
                               sw - PAD * 2, rh)
            tf_r = tb_r.text_frame; tf_r.word_wrap = True
            p_r  = tf_r.paragraphs[0]; p_r.alignment = align
            run_r = p_r.add_run()
            run_r.text = text
            run_r.font.name   = FONT
            run_r.font.size   = Pt(size)
            run_r.font.bold   = bold
            run_r.font.italic = italic
            run_r.font.color.rgb = color

        cy += rh


def slide_premessa_con_mockup(prs):
    slide = slide_with_header(prs, "Prima di tutto.", "Perch\xe9 esiste Salute Quotidiana")

    # ── Testo versione lunga (top 37%) ────────────────────────────────────────
    draw_text_premessa(slide)

    # ── Separatore ────────────────────────────────────────────────────────────
    sep_y = WIRE_TOP - Cm(0.2)
    add_rect(slide, L, sep_y, CW, Cm(0.04), BLU_LT)

    # ── 3 schermate (bottom 60%) ──────────────────────────────────────────────
    GAP    = Cm(0.4)
    SCR_W  = (CW - GAP * 2) / 3
    SCR_H  = WIRE_H

    sx0 = L
    sx1 = L + SCR_W + GAP
    sx2 = L + (SCR_W + GAP) * 2

    # ── Etichette sopra le schermate ──────────────────────────────────────────
    labels = ['APP CLIENTE — Wallet', 'APP CLIENTE — Prenotazione', 'APP CLIENTE — Conferma']
    for lbl, sx in zip(labels, [sx0, sx1, sx2]):
        tb_l = add_textbox(slide, sx, WIRE_TOP - Cm(0.32), SCR_W, Cm(0.3))
        p_l  = tb_l.text_frame.paragraphs[0]; p_l.alignment = PP_ALIGN.CENTER
        run_l = p_l.add_run()
        run_l.text = lbl
        run_l.font.name = FONT; run_l.font.size = Pt(6)
        run_l.font.bold = True; run_l.font.color.rgb = BLU_SCURO

    # ── Schermata 1: Wallet ───────────────────────────────────────────────────
    wallet_rows = [
        {'text': 'Ciao, Marco  —  Livello GOLD',  'size': 6.5, 'bold': True, 'color': BLU_SCURO},
        {'text': ''},
        {'text': 'Il tuo saldo Credito SQ',           'size': 6,   'color': GRIGIO_TESTO},
        {'text': '15,00 euro SQ  (su 20 max)',         'size': 7.5, 'bold': True, 'color': VERDE},
        {'text': 'Prossima prestazione a soli 5 euro SQ',
                                                       'size': 6,   'color': BLU_MEDIO, 'italic': True},
        {'text': ''},
        {'text': 'CARICA SCONTRINO', 'size': 6.5, 'bold': True,
         'color': BIANCO, 'bg': BLU_SCURO, 'align': PP_ALIGN.CENTER},
        {'text': ''},
        {'text': 'ULTIMI ACQUISTI',  'size': 6,   'bold': True, 'color': BLU_SCURO},
        {'text': 'Farmacia Rossi        +2,40 €SQ', 'size': 6,   'color': GRIGIO_TESTO, 'bg': GRIGIO_LIGHT},
        {'text': 'Bar Centrale          +0,80 €SQ', 'size': 6,   'color': GRIGIO_TESTO},
        {'text': 'Supermercato          +1,50 €SQ', 'size': 6,   'color': GRIGIO_TESTO, 'bg': GRIGIO_LIGHT},
    ]
    draw_screen(slide, sx0, SCR_W, SCR_H, 'Salute Quotidiana  |  WALLET', wallet_rows)

    # ── Schermata 2: Prenotazione ─────────────────────────────────────────────
    prenot_rows = [
        {'text': 'Saldo disponibile: 15,00 €SQ', 'size': 6.5, 'bold': True, 'color': BLU_SCURO},
        {'text': ''},
        {'text': '✓  Iniezione I.M.              8 €SQ',
         'size': 6, 'color': VERDE, 'bold': True, 'bg': VERDE_LT},
        {'text': '✓  Prelievo periferico        10 €SQ',
         'size': 6, 'color': VERDE, 'bold': True},
        {'text': '✓  Medicazione semplice       13 €SQ',
         'size': 6, 'color': VERDE, 'bold': True, 'bg': VERDE_LT},
        {'text': '○  Controllo parametri        16 €SQ',
         'size': 6, 'color': GRIGIO_TESTO},
        {'text': '○  Prelievo arterioso         20 €SQ',
         'size': 6, 'color': GRIGIO_TESTO, 'bg': GRIGIO_LIGHT},
        {'text': '○  Gest. tracheostomia        30 €SQ',
         'size': 6, 'color': GRIGIO_TESTO},
        {'text': ''},
        {'text': '✓ disponibile con il tuo saldo', 'size': 5.5, 'color': VERDE, 'italic': True},
        {'text': ''},
        {'text': 'PRENOTA', 'size': 6.5, 'bold': True,
         'color': BIANCO, 'bg': VERDE, 'align': PP_ALIGN.CENTER},
    ]
    draw_screen(slide, sx1, SCR_W, SCR_H, 'Prenota Prestazione', prenot_rows, header_color=BLU_MEDIO)

    # ── Schermata 3: Conferma ─────────────────────────────────────────────────
    conf_rows = [
        {'text': '✓  Prenotazione Confermata!', 'size': 8, 'bold': True, 'color': VERDE,
         'align': PP_ALIGN.CENTER, 'h': 1.4},
        {'text': ''},
        {'text': 'Prelievo periferico',            'size': 7,   'bold': True, 'color': BLU_SCURO, 'align': PP_ALIGN.CENTER},
        {'text': 'Infermiere: Mario R.',            'size': 6.5, 'color': GRIGIO_TESTO,  'align': PP_ALIGN.CENTER},
        {'text': ''},
        {'text': 'Data:    Mer 16/03  —  ore 09:30', 'size': 6.5, 'color': GRIGIO_TESTO, 'bg': GRIGIO_LIGHT},
        {'text': 'Luogo:   a domicilio',             'size': 6.5, 'color': GRIGIO_TESTO},
        {'text': ''},
        {'text': 'Credito usato:   10,00 €SQ',  'size': 6.5, 'color': BLU_SCURO},
        {'text': 'Saldo residuo:    5,00 €SQ',  'size': 6.5, 'color': VERDE, 'bold': True, 'bg': VERDE_LT},
        {'text': ''},
        {'text': '+ AGGIUNGI AL CALENDARIO', 'size': 6, 'color': BLU_SCURO,
         'bg': BLU_LT, 'align': PP_ALIGN.CENTER},
    ]
    draw_screen(slide, sx2, SCR_W, SCR_H, 'Conferma Prenotazione', conf_rows, header_color=VERDE)


def main():
    prs = new_prs()

    # Sequenza: cover → PREMESSA → slide 2-11 → chiusura
    slide_cover(prs)
    slide_premessa_con_mockup(prs)   # <-- nuova slide
    slide_2(prs)
    slide_3(prs)
    slide_4(prs)
    slide_5(prs)
    slide_6(prs)
    slide_7(prs)
    slide_8(prs)
    slide_9(prs)
    slide_10(prs)
    slide_11(prs)
    slide_chiusura(prs)

    prs.save(str(OUTPUT))
    print(f'Salvato: {OUTPUT}')
    print(f'Slide totali: {len(prs.slides)}')


if __name__ == '__main__':
    main()
