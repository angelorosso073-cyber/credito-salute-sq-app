-- docs/supabase-anti-duplicato-scontrini.sql
-- Fase A — Intervento 2: chiave anti-duplicato su matricola RT + numero documento + data + importo.
-- Eseguire in Supabase SQL Editor dopo docs/supabase-operatore-label.sql (l'ultimo applicato finora).
--
-- Obiettivo:
-- 1. impedire il caricamento due volte dello stesso scontrino, anche da clienti diversi;
-- 2. validare che la matricola appartenga a un registratore dell'esercizio aderente;
-- 3. bloccare data futura e data precedente all'avvio del programma;
-- 4. ripristinare il controllo auth.uid() rimosso per errore da docs/supabase-operatore-label.sql.

-- 1. Colonna nullable: nessuna riga storica viene invalidata.
ALTER TABLE public.scontrini
  ADD COLUMN IF NOT EXISTS matricola_rt TEXT;

-- 2. Registro dei registratori telematici per esercizio aderente.
CREATE TABLE IF NOT EXISTS public.registratori_telematici (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  bar_id UUID NOT NULL REFERENCES public.bar(id) ON DELETE CASCADE,
  matricola TEXT NOT NULL,
  attivo BOOLEAN NOT NULL DEFAULT true,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (bar_id, matricola)
);

ALTER TABLE public.registratori_telematici ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "registratori_select_autenticati" ON public.registratori_telematici;
CREATE POLICY "registratori_select_autenticati"
ON public.registratori_telematici
FOR SELECT
TO authenticated
USING (true);

DROP POLICY IF EXISTS "registratori_gestione_admin_sq" ON public.registratori_telematici;
CREATE POLICY "registratori_gestione_admin_sq"
ON public.registratori_telematici
FOR ALL
TO authenticated
USING (public.e_admin() OR public.e_salute_quotidiana())
WITH CHECK (public.e_admin() OR public.e_salute_quotidiana());

GRANT SELECT ON public.registratori_telematici TO authenticated;
REVOKE ALL ON public.registratori_telematici FROM anon;

-- 3. Vincolo di unicita' anti-duplicato: attivo solo quando la matricola e' presente
--    (le righe storiche senza matricola non vengono mai toccate ne' bloccate) e
--    lo scontrino non e' stato rifiutato (un rifiuto libera la combinazione, cosi'
--    un cliente puo' ricaricare uno scontrino corretto dopo un rifiuto per errore).
CREATE UNIQUE INDEX IF NOT EXISTS idx_scontrini_chiave_duplicato
  ON public.scontrini (matricola_rt, numero_documento, data_scontrino, importo_dichiarato)
  WHERE matricola_rt IS NOT NULL AND stato <> 'rifiutato';

-- 4. Funzione aggiornata: stessi 15 parametri esistenti (0..14) + p_matricola_rt in coda.
CREATE OR REPLACE FUNCTION public.registra_scontrino_pilot(
  p_id                 UUID,
  p_cliente_id         UUID,
  p_bar_id             UUID,
  p_testo_ocr          TEXT,
  p_data_scontrino     DATE,
  p_ora_scontrino      TIME,
  p_numero_documento   TEXT,
  p_importo_dichiarato NUMERIC,
  p_importo_ocr        NUMERIC,
  p_importo_verificato NUMERIC,
  p_credito_generato   NUMERIC,
  p_stato              TEXT,
  p_avviso_duplicato   BOOLEAN,
  p_motivo_controllo   TEXT,
  p_operatore_label    TEXT DEFAULT NULL,
  p_matricola_rt       TEXT DEFAULT NULL
)
RETURNS UUID
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  nuovo_id UUID;
  profilo_corrente_id UUID;
  documento_normalizzato TEXT;
  matricola_normalizzata TEXT;
  PROGRAM_START_DATE CONSTANT DATE := '2026-07-04';
BEGIN
  IF auth.uid() IS NULL THEN
    RAISE EXCEPTION 'accesso richiesto';
  END IF;

  IF p_cliente_id IS NULL THEN
    RAISE EXCEPTION 'cliente mancante';
  END IF;

  IF p_bar_id IS NULL THEN
    RAISE EXCEPTION 'bar mancante';
  END IF;

  SELECT p.id
  INTO profilo_corrente_id
  FROM public.profili p
  WHERE p.auth_user_id = auth.uid()
  LIMIT 1;

  IF profilo_corrente_id IS NULL THEN
    RAISE EXCEPTION 'profilo non trovato';
  END IF;

  IF NOT (
    public.e_admin()
    OR public.e_salute_quotidiana()
    OR public.e_bar()
    OR EXISTS (
      SELECT 1
      FROM public.clienti c
      WHERE c.id = p_cliente_id
        AND c.profilo_id = profilo_corrente_id
        AND c.stato = 'attivo'
    )
  ) THEN
    RAISE EXCEPTION 'cliente non autorizzato';
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM public.clienti c
    WHERE c.id = p_cliente_id AND c.stato = 'attivo'
  ) THEN
    RAISE EXCEPTION 'cliente non valido o non attivo';
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM public.bar b
    WHERE b.id = p_bar_id AND b.attivo = true
  ) THEN
    RAISE EXCEPTION 'bar non valido o non attivo';
  END IF;

  IF p_importo_dichiarato IS NULL OR p_importo_dichiarato <= 0 THEN
    RAISE EXCEPTION 'importo non valido';
  END IF;

  IF p_credito_generato IS NULL OR p_credito_generato < 0 THEN
    RAISE EXCEPTION 'credito non valido';
  END IF;

  IF p_data_scontrino IS NULL THEN
    RAISE EXCEPTION 'data scontrino mancante';
  END IF;

  IF p_data_scontrino > CURRENT_DATE THEN
    RAISE EXCEPTION 'data scontrino futura';
  END IF;

  IF p_data_scontrino < PROGRAM_START_DATE THEN
    RAISE EXCEPTION 'data scontrino precedente all''avvio del programma';
  END IF;

  documento_normalizzato := NULLIF(TRIM(COALESCE(p_numero_documento, '')), '');
  IF documento_normalizzato IS NULL THEN
    RAISE EXCEPTION 'numero documento mancante';
  END IF;

  matricola_normalizzata := UPPER(NULLIF(TRIM(COALESCE(p_matricola_rt, '')), ''));

  IF matricola_normalizzata IS NOT NULL THEN
    IF NOT EXISTS (
      SELECT 1 FROM public.registratori_telematici rt
      WHERE rt.bar_id = p_bar_id
        AND UPPER(rt.matricola) = matricola_normalizzata
        AND rt.attivo = true
    ) THEN
      RAISE EXCEPTION 'matricola registratore non riconosciuta per questo esercizio';
    END IF;

    IF EXISTS (
      SELECT 1 FROM public.scontrini s
      WHERE UPPER(s.matricola_rt) = matricola_normalizzata
        AND LOWER(TRIM(COALESCE(s.numero_documento, ''))) = LOWER(documento_normalizzato)
        AND s.data_scontrino = p_data_scontrino
        AND ROUND(s.importo_dichiarato::numeric, 2) = ROUND(p_importo_dichiarato::numeric, 2)
        AND s.stato <> 'rifiutato'
    ) THEN
      RAISE EXCEPTION 'scontrino duplicato: stessa matricola, numero documento, data e importo';
    END IF;
  END IF;

  INSERT INTO public.scontrini (
    id, cliente_id, bar_id, testo_ocr,
    data_scontrino, ora_scontrino, numero_documento,
    importo_dichiarato, importo_ocr, importo_verificato,
    credito_generato, stato, avviso_duplicato,
    motivo_rifiuto, operatore_label, matricola_rt
  )
  VALUES (
    COALESCE(p_id, gen_random_uuid()),
    p_cliente_id,
    p_bar_id,
    p_testo_ocr,
    p_data_scontrino,
    p_ora_scontrino,
    documento_normalizzato,
    p_importo_dichiarato,
    p_importo_ocr,
    p_importo_verificato,
    p_credito_generato,
    p_stato,
    COALESCE(p_avviso_duplicato, false),
    NULLIF(TRIM(COALESCE(p_motivo_controllo, '')), ''),
    NULLIF(TRIM(COALESCE(p_operatore_label, '')), ''),
    matricola_normalizzata
  )
  RETURNING id INTO nuovo_id;

  RETURN nuovo_id;
END;
$$;

REVOKE ALL ON FUNCTION public.registra_scontrino_pilot(
  uuid, uuid, uuid, text, date, time, text,
  numeric, numeric, numeric, numeric, text, boolean, text, text, text
) FROM anon;

GRANT EXECUTE ON FUNCTION public.registra_scontrino_pilot(
  uuid, uuid, uuid, text, date, time, text,
  numeric, numeric, numeric, numeric, text, boolean, text, text, text
) TO authenticated;

NOTIFY pgrst, 'reload schema';
