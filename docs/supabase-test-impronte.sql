-- docs/supabase-test-impronte.sql
-- Verifica del punteggio impronta. Da lanciare dopo
-- docs/supabase-impronte-esercizio.sql. Non modifica nulla: solo SELECT.
--
-- I primi tre casi sono testi OCR REALI, copiati da public.scontrini del bar
-- pilota il 02/09/2026. Gli altri sono costruiti.
--
-- Atteso: colonna "verifica" uguale a OK su tutte e sette le righe.
-- Punteggi attesi: 9-10 per i casi 1-3, 3 per il caso 4, 0 per i casi 5-7.

WITH bar_pilota AS (
  SELECT id FROM public.bar WHERE nome = 'Bar pilota Francofonte'
),
casi(ordine, nome, testo, atteso_passa) AS (
  VALUES
  (1, 'reale 02/09 con OCR sporco', $t$SOS aa A Jr
NEW CHAT CAFE'
DI MERENDA MICHELE
PARTITA IVA 61468000898
VIA E.GAUDIOSO N 16
FRANCOFONTE (SR)
TEL.095/7842471
TOTALE COMPLESSIVO ~~ 1.28
02-09-2026 07:27
DOCUMENTO N. 2319-0004
AT 20181000611$t$, true),

  (2, 'reale 02/09 con molto rumore', $t$AR ar Aaah Ld
Sa NEW CHAT CAFE' Bia
Sa DI MERENDA MICHELE oP
a PARTITA IVA 01458000898 ij
o VIA E.GAUDIOSO N 10
O FRANCOFONTE (SR)
o TEL .095/7842471
TOTALE COMPLESSIVO 1,20
de 02-09-2026 07:27 i
i RT 26151660611$t$, true),

  (3, 'reale 01/09 pulito', $t$NEW CHAT CAFE'
' DI MERENDA MICHELE
PARTITA IVA 01458000898
VIA E.GAUDIOSO N 10
FRANCOFONTE (SR)
TEL.095/7842471
TOTALE COMPLESSIVO 1,2
i 01-09-2026 16:11
i RT 2C181600611$t$, true),

  (4, 'bar pilota, foto pessima, una parola sola', $t$ii1 |\ NEW CHAT CAFE ,,. ~~
sgv FRANCOFONTE (SR) ...
TOTALE 1,20$t$, true),

  (5, 'supermercato di Francofonte', $t$SUPERMERCATO CONAD
DI RUSSO GIUSEPPE
PARTITA IVA 01999000111
VIA ROMA N 45
FRANCOFONTE (SR)
TEL.095/1234567
TOTALE COMPLESSIVO 12,40$t$, false),

  (6, 'tabaccheria di Francofonte', $t$TABACCHERIA CENTRALE
DI LI CALZI ANTONIO
PARTITA IVA 01777000222
CORSO GARIBALDI N 3
FRANCOFONTE (SR)
TOTALE COMPLESSIVO 5,00$t$, false),

  (7, 'foto illeggibile', $t$~~~ ,,, || \ ... i i i
TOTALE 1 20$t$, false)
)
SELECT
  c.ordine,
  c.nome,
  public.punteggio_impronta_pilot(b.id, c.testo) AS punti,
  (SELECT soglia_impronta FROM public.limiti_bar WHERE bar_id = b.id) AS soglia,
  CASE
    WHEN public.punteggio_impronta_pilot(b.id, c.testo)
         >= (SELECT soglia_impronta FROM public.limiti_bar WHERE bar_id = b.id)
    THEN 'PASSA' ELSE 'FERMA'
  END AS esito,
  CASE
    WHEN (public.punteggio_impronta_pilot(b.id, c.testo)
          >= (SELECT soglia_impronta FROM public.limiti_bar WHERE bar_id = b.id))
         = c.atteso_passa
    THEN 'OK' ELSE 'FUORI ATTESA'
  END AS verifica
FROM casi c CROSS JOIN bar_pilota b
ORDER BY c.ordine;
