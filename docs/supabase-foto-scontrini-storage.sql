-- docs/supabase-foto-scontrini-storage.sql
-- Salvataggio foto scontrini su Supabase Storage per fini di controllo.
-- Oggi la foto resta solo nel browser che l'ha caricata (localStorage): se il
-- cliente cambia dispositivo o cancella i dati, la foto sparisce e Salute
-- Quotidiana non puo' mai rivederla per un controllo.
--
-- Eseguire in Supabase SQL Editor dopo docs/supabase-inversione-qr-banco.sql
-- (l'ultimo applicato finora sulla tabella scontrini/funzione registra_scontrino_pilot).
--
-- Convenzione percorso file nel bucket: {cliente_id}/{scontrino_id}.{estensione}

-- 1. Bucket privato (non pubblico: solo signed URL temporanee per la visione).
INSERT INTO storage.buckets (id, name, public)
VALUES ('foto-scontrini', 'foto-scontrini', false)
ON CONFLICT (id) DO NOTHING;

-- 2. RLS su storage.objects per questo bucket.
DROP POLICY IF EXISTS "foto_scontrini_insert_proprio_cliente" ON storage.objects;
CREATE POLICY "foto_scontrini_insert_proprio_cliente"
ON storage.objects
FOR INSERT
TO authenticated
WITH CHECK (
  bucket_id = 'foto-scontrini'
  AND (
    public.e_admin()
    OR public.e_salute_quotidiana()
    OR EXISTS (
      SELECT 1
      FROM public.clienti c
      JOIN public.profili p ON p.id = c.profilo_id
      WHERE c.id::text = (storage.foldername(name))[1]
        AND p.auth_user_id = auth.uid()
        AND c.stato = 'attivo'
    )
  )
);

DROP POLICY IF EXISTS "foto_scontrini_select_per_ruolo" ON storage.objects;
CREATE POLICY "foto_scontrini_select_per_ruolo"
ON storage.objects
FOR SELECT
TO authenticated
USING (
  bucket_id = 'foto-scontrini'
  AND (
    public.e_admin()
    OR public.e_salute_quotidiana()
    OR EXISTS (
      SELECT 1
      FROM public.clienti c
      JOIN public.profili p ON p.id = c.profilo_id
      WHERE c.id::text = (storage.foldername(name))[1]
        AND p.auth_user_id = auth.uid()
    )
  )
);

DROP POLICY IF EXISTS "foto_scontrini_delete_admin_sq" ON storage.objects;
CREATE POLICY "foto_scontrini_delete_admin_sq"
ON storage.objects
FOR DELETE
TO authenticated
USING (
  bucket_id = 'foto-scontrini'
  AND (public.e_admin() OR public.e_salute_quotidiana())
);

-- 3. Colonna sullo scontrino: percorso del file nel bucket (non l'URL, il
--    bucket e' privato e serve una signed URL generata al momento della vista).
ALTER TABLE public.scontrini
  ADD COLUMN IF NOT EXISTS foto_path TEXT;

-- 4. Funzione aggiornata: stessi 17 parametri esistenti + p_foto_path in coda,
--    DEFAULT NULL. Nessuna logica esistente cambiata, solo la nuova colonna
--    valorizzata se il client la passa.
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
  p_matricola_rt       TEXT DEFAULT NULL,
  p_codice_banco       TEXT DEFAULT NULL,
  p_foto_path          TEXT DEFAULT NULL
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
  scadenza_sospensione TIMESTAMPTZ;
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
    limiti.tetto_giornaliero_scontrini := 3;
    limiti.soglia_revisione_manuale := 30;
    limiti.sospensione_giorni := 12;
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
    scadenza_sospensione := NULL;
  ELSIF public.verifica_codice_banco_interna(p_bar_id, p_codice_banco) THEN
    stato_finale := 'confermato';
    motivo_sospensione_finale := NULL;
    scadenza_sospensione := NULL;
  ELSE
    stato_finale := 'in_verifica';
    motivo_sospensione_finale := 'codice_banco_mancante';
    scadenza_sospensione := NOW() + (COALESCE(limiti.sospensione_giorni, 12) || ' days')::INTERVAL;
  END IF;

  INSERT INTO public.scontrini (
    id, cliente_id, bar_id, testo_ocr,
    data_scontrino, ora_scontrino, numero_documento,
    importo_dichiarato, importo_ocr, importo_verificato,
    credito_generato, stato, avviso_duplicato,
    motivo_rifiuto, operatore_label, matricola_rt,
    motivo_sospensione, sospeso_scaduto_il, foto_path
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
    motivo_sospensione_finale,
    scadenza_sospensione,
    NULLIF(TRIM(COALESCE(p_foto_path, '')), '')
  )
  RETURNING id INTO nuovo_id;

  RETURN nuovo_id;
END;
$$;

REVOKE ALL ON FUNCTION public.registra_scontrino_pilot(
  uuid, uuid, uuid, text, date, time, text,
  numeric, numeric, numeric, numeric, text, boolean, text, text, text, text, text
) FROM anon;

GRANT EXECUTE ON FUNCTION public.registra_scontrino_pilot(
  uuid, uuid, uuid, text, date, time, text,
  numeric, numeric, numeric, numeric, text, boolean, text, text, text, text, text
) TO authenticated;

-- 5. Vista scontrini_app_pilot estesa con foto_path (usata sia dal cliente
--    per il proprio storico, sia da Salute Quotidiana per la coda verifica).
DROP VIEW IF EXISTS public.scontrini_app_pilot;
CREATE VIEW public.scontrini_app_pilot
WITH (security_invoker = true)
AS
SELECT
  s.id,
  s.cliente_id,
  s.testo_ocr,
  s.data_scontrino,
  s.ora_scontrino,
  s.numero_documento,
  s.importo_dichiarato,
  s.importo_ocr,
  s.credito_generato,
  s.stato,
  s.avviso_duplicato,
  s.motivo_rifiuto,
  s.motivo_sospensione,
  s.sospeso_scaduto_il,
  s.foto_path,
  s.created_at,
  s.updated_at
FROM public.scontrini s;

GRANT SELECT ON public.scontrini_app_pilot TO authenticated;
REVOKE ALL ON public.scontrini_app_pilot FROM anon;

-- 6. Vista scontrini_revisione_manuale_pilot estesa con foto_path.
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
  s.foto_path,
  s.created_at
FROM public.scontrini s
JOIN public.clienti c ON c.id = s.cliente_id
WHERE s.stato = 'in_verifica'
  AND s.motivo_sospensione = 'importo_oltre_soglia'
ORDER BY s.created_at DESC;

GRANT SELECT ON public.scontrini_revisione_manuale_pilot TO authenticated;
REVOKE ALL ON public.scontrini_revisione_manuale_pilot FROM anon;

NOTIFY pgrst, 'reload schema';
