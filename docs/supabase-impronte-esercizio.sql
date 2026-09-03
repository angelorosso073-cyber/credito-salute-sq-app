-- docs/supabase-impronte-esercizio.sql
-- Verifica di provenienza: parole caratteristiche di ogni esercizio, cercate
-- nel testo OCR che l'app gia' invia insieme allo scontrino.
--
-- Eseguire in Supabase SQL Editor dopo docs/supabase-foto-scontrini-storage.sql.
-- Questo file NON modifica registra_scontrino_pilot: aggiunge solo il
-- meccanismo di punteggio, che il file successivo collega alla decisione.
--
-- Perche' basato su parole e non sulla matricola: su tre scontrini reali del
-- bar pilota l'OCR non ha letto la matricola correttamente nemmeno una volta
-- (2CISI000611 letto come AT 20181000611, RT 26151660611, RT 2C181600611),
-- mentre nome, titolare e via sono stati letti correttamente tutte e tre le
-- volte. L'OCR sbaglia i numeri e azzecca le parole.

-- 1. Elenco delle parole per esercizio.
CREATE TABLE IF NOT EXISTS public.impronte_esercizio (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  bar_id UUID NOT NULL REFERENCES public.bar(id) ON DELETE CASCADE,
  testo TEXT NOT NULL,
  peso INTEGER NOT NULL DEFAULT 1 CHECK (peso BETWEEN 1 AND 5),
  attivo BOOLEAN NOT NULL DEFAULT true,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (bar_id, testo)
);

ALTER TABLE public.impronte_esercizio ENABLE ROW LEVEL SECURITY;

-- Nessuna policy di lettura per i client: l'elenco delle impronte e'
-- esattamente cio' che servirebbe a un imbroglione per costruire un testo
-- falso capace di superare il controllo. Lo legge solo la funzione di
-- punteggio, che e' SECURITY DEFINER.
DROP POLICY IF EXISTS "impronte_gestione_admin_sq" ON public.impronte_esercizio;
CREATE POLICY "impronte_gestione_admin_sq"
ON public.impronte_esercizio
FOR ALL
TO authenticated
USING (public.e_admin() OR public.e_salute_quotidiana())
WITH CHECK (public.e_admin() OR public.e_salute_quotidiana());

REVOKE ALL ON public.impronte_esercizio FROM anon;

-- 2. Soglia per esercizio. 3 significa che una sola parola forte basta:
--    scelta voluta, una fotografia storta che lascia leggere solo il nome
--    dell'esercizio non deve finire in revisione manuale.
ALTER TABLE public.limiti_bar
  ADD COLUMN IF NOT EXISTS soglia_impronta INTEGER NOT NULL DEFAULT 3
  CHECK (soglia_impronta >= 0);

-- 3. Normalizzazione. Serve perche' l'OCR restituisce "TEL .095/7842471",
--    "NEW CHAT CAFE'" e simili: senza normalizzare nessun confronto reggerebbe.
CREATE OR REPLACE FUNCTION public.normalizza_testo_ocr(p_testo TEXT)
RETURNS TEXT
LANGUAGE sql
IMMUTABLE
AS $$
  SELECT TRIM(REGEXP_REPLACE(
    UPPER(TRANSLATE(
      COALESCE(p_testo, ''),
      'ÀÁÂÃÄÈÉÊËÌÍÎÏÒÓÔÕÖÙÚÛÜàáâãäèéêëìíîïòóôõöùúûü',
      'AAAAAEEEEIIIIOOOOOUUUUaaaaaeeeeiiiiooooouuuu'
    )),
    '[^A-Z0-9]+', ' ', 'g'
  ));
$$;

-- 4. Punteggio: somma dei pesi delle impronte attive presenti nel testo.
CREATE OR REPLACE FUNCTION public.punteggio_impronta_pilot(
  p_bar_id UUID,
  p_testo_ocr TEXT
)
RETURNS INTEGER
LANGUAGE plpgsql
STABLE
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  testo_normalizzato TEXT;
  totale INTEGER;
BEGIN
  testo_normalizzato := public.normalizza_testo_ocr(p_testo_ocr);

  IF testo_normalizzato = '' THEN
    RETURN 0;
  END IF;

  SELECT COALESCE(SUM(i.peso), 0)
  INTO totale
  FROM public.impronte_esercizio i
  WHERE i.bar_id = p_bar_id
    AND i.attivo = true
    AND POSITION(public.normalizza_testo_ocr(i.testo) IN testo_normalizzato) > 0;

  RETURN totale;
END;
$$;

-- Non richiamabile dai client: risponderebbe alle domande di chi vuole
-- indovinare le impronte. La chiama solo registra_scontrino_pilot, che gira
-- come proprietario.
REVOKE ALL ON FUNCTION public.punteggio_impronta_pilot(uuid, text) FROM PUBLIC, anon, authenticated;

-- 5. Impronte del bar pilota. Pesi alti alle parole, bassi ai numeri: sui tre
--    scontrini reali la partita IVA e' stata letta correttamente 2 volte su 3,
--    le parole 3 volte su 3.
--    FRANCOFONTE non compare di proposito: sta sullo scontrino di qualunque
--    negozio del paese e non distingue nulla.
INSERT INTO public.impronte_esercizio (bar_id, testo, peso)
SELECT b.id, v.testo, v.peso
FROM public.bar b
CROSS JOIN (VALUES
  ('NEW CHAT CAFE', 3),
  ('MERENDA MICHELE', 3),
  ('GAUDIOSO', 2),
  ('7842471', 1),
  ('01458000898', 1)
) AS v(testo, peso)
WHERE b.nome = 'Bar pilota Francofonte'
ON CONFLICT (bar_id, testo) DO NOTHING;

NOTIFY pgrst, 'reload schema';
