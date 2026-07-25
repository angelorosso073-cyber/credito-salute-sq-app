-- Credito Salute SQ — Opzione C: label operatore cassiere
-- Aggiunge operatore_label alla tabella scontrini e aggiorna la RPC.
-- DA APPLICARE in Supabase SQL Editor.

-- 1. Colonna nullable sulla tabella scontrini
ALTER TABLE public.scontrini
  ADD COLUMN IF NOT EXISTS operatore_label TEXT;

-- 2. Drop vecchia firma RPC (14 parametri)
DROP FUNCTION IF EXISTS public.registra_scontrino_pilot(
  uuid, uuid, uuid, text, date, time, text,
  numeric, numeric, numeric, numeric, text, boolean, text
);

-- 3. Nuova RPC con p_operatore_label (default null = backward-compatible)
CREATE OR REPLACE FUNCTION public.registra_scontrino_pilot(
  p_id                uuid,
  p_cliente_id        uuid,
  p_bar_id            uuid,
  p_testo_ocr         text,
  p_data_scontrino    date,
  p_ora_scontrino     time,
  p_numero_documento  text,
  p_importo_dichiarato numeric,
  p_importo_ocr       numeric,
  p_importo_verificato numeric,
  p_credito_generato  numeric,
  p_stato             text,
  p_avviso_duplicato  boolean,
  p_motivo_controllo  text,
  p_operatore_label   text DEFAULT NULL
)
RETURNS uuid
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  nuovo_id uuid;
BEGIN
  IF p_cliente_id IS NULL THEN
    RAISE EXCEPTION 'cliente mancante';
  END IF;

  IF p_bar_id IS NULL THEN
    RAISE EXCEPTION 'bar mancante';
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

  IF p_stato NOT IN ('in_verifica', 'confermato') THEN
    RAISE EXCEPTION 'stato non ammesso';
  END IF;

  INSERT INTO public.scontrini (
    id, cliente_id, bar_id, testo_ocr,
    data_scontrino, ora_scontrino, numero_documento,
    importo_dichiarato, importo_ocr, importo_verificato,
    credito_generato, stato, avviso_duplicato,
    motivo_rifiuto, operatore_label
  )
  VALUES (
    COALESCE(p_id, gen_random_uuid()),
    p_cliente_id,
    p_bar_id,
    p_testo_ocr,
    p_data_scontrino,
    p_ora_scontrino,
    NULLIF(TRIM(COALESCE(p_numero_documento, '')), ''),
    p_importo_dichiarato,
    p_importo_ocr,
    p_importo_verificato,
    p_credito_generato,
    p_stato,
    COALESCE(p_avviso_duplicato, false),
    NULLIF(TRIM(COALESCE(p_motivo_controllo, '')), ''),
    NULLIF(TRIM(COALESCE(p_operatore_label, '')), '')
  )
  RETURNING id INTO nuovo_id;

  RETURN nuovo_id;
END;
$$;

GRANT EXECUTE ON FUNCTION public.registra_scontrino_pilot(
  uuid, uuid, uuid, text, date, time, text,
  numeric, numeric, numeric, numeric, text, boolean, text, text
) TO anon, authenticated;

NOTIFY pgrst, 'reload schema';
