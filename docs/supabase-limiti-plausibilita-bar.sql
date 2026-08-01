-- docs/supabase-limiti-plausibilita-bar.sql
-- Fase B — Intervento 3: limiti di plausibilita' configurabili per esercizio.
-- Eseguire in Supabase SQL Editor dopo docs/supabase-anti-duplicato-scontrini.sql.
--
-- Obiettivo:
-- 1. tetto giornaliero di scontrini per cliente (oltre: rifiutato subito, non consuma un ID);
-- 2. importo massimo oltre il quale lo scontrino va in coda di revisione manuale (non rifiutato);
-- 3. soglie per esercizio, non costanti globali.

-- 1. Configurazione per bar. bar_id e' chiave primaria: un solo set di limiti per esercizio.
CREATE TABLE IF NOT EXISTS public.limiti_bar (
  bar_id UUID PRIMARY KEY REFERENCES public.bar(id) ON DELETE CASCADE,
  tetto_giornaliero_scontrini INTEGER NOT NULL DEFAULT 3 CHECK (tetto_giornaliero_scontrini > 0),
  soglia_revisione_manuale NUMERIC(10,2) NOT NULL DEFAULT 30 CHECK (soglia_revisione_manuale > 0),
  sospensione_giorni INTEGER NOT NULL DEFAULT 12 CHECK (sospensione_giorni BETWEEN 1 AND 30),
  codice_banco_finestra_secondi INTEGER NOT NULL DEFAULT 90 CHECK (codice_banco_finestra_secondi >= 30),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

DROP TRIGGER IF EXISTS trg_limiti_bar_updated_at ON public.limiti_bar;
CREATE TRIGGER trg_limiti_bar_updated_at
BEFORE UPDATE ON public.limiti_bar
FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

ALTER TABLE public.limiti_bar ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "limiti_bar_select_autenticati" ON public.limiti_bar;
CREATE POLICY "limiti_bar_select_autenticati"
ON public.limiti_bar
FOR SELECT
TO authenticated
USING (true);

DROP POLICY IF EXISTS "limiti_bar_gestione_admin_sq" ON public.limiti_bar;
CREATE POLICY "limiti_bar_gestione_admin_sq"
ON public.limiti_bar
FOR ALL
TO authenticated
USING (public.e_admin() OR public.e_salute_quotidiana())
WITH CHECK (public.e_admin() OR public.e_salute_quotidiana());

GRANT SELECT ON public.limiti_bar TO authenticated;
REVOKE ALL ON public.limiti_bar FROM anon;

INSERT INTO public.limiti_bar (bar_id)
SELECT id FROM public.bar WHERE nome = 'Bar pilota Francofonte'
ON CONFLICT (bar_id) DO NOTHING;

-- 2. Motivo per cui uno scontrino resta in_verifica, distinto dal generico controllo OCR.
--    Valore ammesso in questa fase: solo 'importo_oltre_soglia' (la Fase C ne aggiunge un secondo).
ALTER TABLE public.scontrini
  ADD COLUMN IF NOT EXISTS motivo_sospensione TEXT;

ALTER TABLE public.scontrini
  DROP CONSTRAINT IF EXISTS scontrini_motivo_sospensione_check;
ALTER TABLE public.scontrini
  ADD CONSTRAINT scontrini_motivo_sospensione_check
  CHECK (motivo_sospensione IS NULL OR motivo_sospensione IN ('importo_oltre_soglia'));

-- 3. Coda di revisione manuale per Salute Quotidiana: solo scontrini sospesi per importo.
DROP VIEW IF EXISTS public.scontrini_revisione_manuale_pilot;
CREATE VIEW public.scontrini_revisione_manuale_pilot
WITH (security_invoker = true)
AS
SELECT
  s.id,
  s.cliente_id,
  c.codice_cliente,
  c.nome,
  c.cognome,
  s.data_scontrino,
  s.numero_documento,
  s.importo_dichiarato,
  s.credito_generato,
  s.created_at
FROM public.scontrini s
JOIN public.clienti c ON c.id = s.cliente_id
WHERE s.stato = 'in_verifica'
  AND s.motivo_sospensione = 'importo_oltre_soglia'
ORDER BY s.created_at DESC;

GRANT SELECT ON public.scontrini_revisione_manuale_pilot TO authenticated;
REVOKE ALL ON public.scontrini_revisione_manuale_pilot FROM anon;

-- 4. Funzione aggiornata: stessa firma del Task 1 (16 parametri), nessun parametro nuovo.
--    I limiti si leggono da limiti_bar usando p_bar_id gia' passato dal client.
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
  limiti RECORD;
  scontrini_oggi INTEGER;
  stato_finale TEXT;
  motivo_sospensione_finale TEXT;
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

  IF p_stato NOT IN ('in_verifica', 'confermato') THEN
    RAISE EXCEPTION 'stato non ammesso';
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

  SELECT * INTO limiti FROM public.limiti_bar WHERE bar_id = p_bar_id;
  IF NOT FOUND THEN
    -- Nessuna riga di configurazione per questo bar: uso i default di progetto.
    limiti.tetto_giornaliero_scontrini := 3;
    limiti.soglia_revisione_manuale := 30;
  END IF;

  SELECT count(*) INTO scontrini_oggi
  FROM public.scontrini s
  WHERE s.cliente_id = p_cliente_id
    AND s.bar_id = p_bar_id
    AND s.data_scontrino = p_data_scontrino
    AND s.stato <> 'rifiutato';

  IF scontrini_oggi >= limiti.tetto_giornaliero_scontrini THEN
    RAISE EXCEPTION 'tetto giornaliero di scontrini raggiunto per questo cliente';
  END IF;

  IF p_importo_dichiarato > limiti.soglia_revisione_manuale THEN
    stato_finale := 'in_verifica';
    motivo_sospensione_finale := 'importo_oltre_soglia';
  ELSE
    stato_finale := p_stato;
    motivo_sospensione_finale := NULL;
  END IF;

  INSERT INTO public.scontrini (
    id, cliente_id, bar_id, testo_ocr,
    data_scontrino, ora_scontrino, numero_documento,
    importo_dichiarato, importo_ocr, importo_verificato,
    credito_generato, stato, avviso_duplicato,
    motivo_rifiuto, operatore_label, matricola_rt, motivo_sospensione
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
    stato_finale,
    COALESCE(p_avviso_duplicato, false),
    NULLIF(TRIM(COALESCE(p_motivo_controllo, '')), ''),
    NULLIF(TRIM(COALESCE(p_operatore_label, '')), ''),
    matricola_normalizzata,
    motivo_sospensione_finale
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
