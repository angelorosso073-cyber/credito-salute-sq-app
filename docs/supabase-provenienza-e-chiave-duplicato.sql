-- docs/supabase-provenienza-e-chiave-duplicato.sql
-- Collega la verifica di provenienza alla decisione sullo scontrino, e
-- corregge due difetti emersi dai dati reali.
--
-- Eseguire dopo docs/supabase-impronte-esercizio.sql e dopo
-- docs/supabase-bonifica-doppioni.sql (l'indice unico fallirebbe se il
-- database contenesse ancora doppioni).
--
-- Per tornare indietro: la versione precedente della funzione e' integra in
-- docs/supabase-foto-scontrini-storage.sql, sezione 4. Rilanciare quella
-- sezione riporta la funzione com'era; l'indice va riportato alla forma
-- vecchia (con importo_dichiarato) nello stesso giro.

-- 1. Nuovo motivo di sospensione, senza togliere quelli esistenti.
ALTER TABLE public.scontrini
  DROP CONSTRAINT IF EXISTS scontrini_motivo_sospensione_check;
ALTER TABLE public.scontrini
  ADD CONSTRAINT scontrini_motivo_sospensione_check
  CHECK (motivo_sospensione IS NULL OR motivo_sospensione IN (
    'importo_oltre_soglia',
    'codice_banco_mancante',
    'provenienza_da_verificare'
  ));

-- 2. Punteggio ottenuto, salvato sulla riga: serve per tarare le soglie sui
--    dati veri invece che a intuito.
ALTER TABLE public.scontrini
  ADD COLUMN IF NOT EXISTS punteggio_impronta INTEGER;

-- 3. Nuova chiave anti-duplicato: senza importo.
--    Motivo: lo stesso scontrino e' stato accettato due volte perche' l'OCR
--    ne ha letto il totale una volta 1,20 e una volta 1.28. Con l'importo
--    nella chiave basta un errore di lettura di un centesimo, o una modifica
--    fatta apposta, per aggirare il controllo.
DROP INDEX IF EXISTS idx_scontrini_chiave_duplicato;
CREATE UNIQUE INDEX idx_scontrini_chiave_duplicato
  ON public.scontrini (matricola_rt, numero_documento, data_scontrino)
  WHERE matricola_rt IS NOT NULL AND stato <> 'rifiutato';

-- 4. La funzione completa.
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
  registratori_attivi INTEGER;
  limiti RECORD;
  scontrini_oggi INTEGER;
  punteggio INTEGER;
  caricato_dall_esercizio BOOLEAN;
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

  caricato_dall_esercizio := public.e_admin()
    OR public.e_salute_quotidiana()
    OR public.e_bar();

  IF NOT (
    caricato_dall_esercizio
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

  -- Quando la matricola non arriva (flusso cassiere: nessuna fotografia,
  -- quindi nessun OCR e nessun campo), la ricava il server dal registro.
  -- Senza questo, il controllo sui doppioni piu' sotto non partirebbe
  -- affatto, e lo stesso scontrino potrebbe essere caricato due volte per
  -- distrazione.
  IF matricola_normalizzata IS NULL THEN
    SELECT count(*) INTO registratori_attivi
    FROM public.registratori_telematici rt
    WHERE rt.bar_id = p_bar_id AND rt.attivo = true;

    IF registratori_attivi = 1 THEN
      SELECT UPPER(rt.matricola) INTO matricola_normalizzata
      FROM public.registratori_telematici rt
      WHERE rt.bar_id = p_bar_id AND rt.attivo = true;
    END IF;
    -- Con zero o piu' di un registratore attivo non esiste un valore
    -- univoco da ricavare: la matricola resta nulla e il controllo sui
    -- doppioni resta inattivo per quell'esercizio, come oggi. Rinuncia
    -- consapevole, da riprendere quando arrivera' un esercizio con due casse.
  END IF;

  IF matricola_normalizzata IS NOT NULL THEN
    IF NOT EXISTS (
      SELECT 1 FROM public.registratori_telematici rt
      WHERE rt.bar_id = p_bar_id
        AND UPPER(rt.matricola) = matricola_normalizzata
        AND rt.attivo = true
    ) THEN
      RAISE EXCEPTION 'matricola registratore non riconosciuta per questo esercizio';
    END IF;

    -- Chiave senza importo: stesso registratore, stesso numero documento,
    -- stessa data significa stesso scontrino, qualunque cifra ne abbia
    -- letto l'OCR.
    IF EXISTS (
      SELECT 1 FROM public.scontrini s
      WHERE UPPER(s.matricola_rt) = matricola_normalizzata
        AND LOWER(TRIM(COALESCE(s.numero_documento, ''))) = LOWER(documento_normalizzato)
        AND s.data_scontrino = p_data_scontrino
        AND s.stato <> 'rifiutato'
    ) THEN
      RAISE EXCEPTION 'scontrino duplicato: stessa matricola, numero documento e data';
    END IF;
  END IF;

  SELECT * INTO limiti FROM public.limiti_bar WHERE bar_id = p_bar_id;
  IF NOT FOUND THEN
    limiti.tetto_giornaliero_scontrini := 3;
    limiti.soglia_revisione_manuale := 30;
    limiti.sospensione_giorni := 12;
    limiti.soglia_impronta := 3;
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

  punteggio := public.punteggio_impronta_pilot(p_bar_id, p_testo_ocr);

  -- Catena a cinque rami. L'ordine conta.
  IF p_importo_dichiarato > limiti.soglia_revisione_manuale THEN
    -- Sopra soglia si guarda sempre, da chiunque arrivi: il controllo non
    -- riguarda la fiducia in chi carica ma la plausibilita' della cifra.
    stato_finale := 'in_verifica';
    motivo_sospensione_finale := 'importo_oltre_soglia';
    scadenza_sospensione := NULL;

  ELSIF caricato_dall_esercizio THEN
    -- Carica l'esercizio stesso, o Salute Quotidiana. Provenienza e presenza
    -- sono dimostrate per definizione: e' il titolare del registratore che
    -- attesta la consumazione, davanti al cliente. Chiedergli il codice che
    -- espone lui stesso, o l'OCR di una fotografia che non scatta, non
    -- dimostrerebbe nulla di piu'.
    -- Questo ramo corregge anche il credito dei clienti senza smartphone, che
    -- fino a oggi restava sospeso in attesa di un'attivazione impossibile e
    -- scadeva dopo 12 giorni.
    stato_finale := 'confermato';
    motivo_sospensione_finale := NULL;
    scadenza_sospensione := NULL;

  ELSIF punteggio < COALESCE(limiti.soglia_impronta, 3) THEN
    -- Il testo letto dalla fotografia non contiene abbastanza elementi
    -- dell'esercizio. Prima del codice banco: un codice valido non deve
    -- confermare uno scontrino estraneo.
    stato_finale := 'in_verifica';
    motivo_sospensione_finale := 'provenienza_da_verificare';
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
    motivo_sospensione, sospeso_scaduto_il, foto_path,
    punteggio_impronta
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
    NULLIF(TRIM(COALESCE(p_foto_path, '')), ''),
    punteggio
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

-- 5. La coda di revisione deve mostrare entrambi i motivi, con il punteggio e
--    la fotografia: la revisione si fa guardando la foto.
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
  s.motivo_sospensione,
  s.punteggio_impronta,
  s.foto_path,
  s.created_at
FROM public.scontrini s
JOIN public.clienti c ON c.id = s.cliente_id
WHERE s.stato = 'in_verifica'
  AND s.motivo_sospensione IN ('importo_oltre_soglia', 'provenienza_da_verificare')
ORDER BY s.created_at DESC;

GRANT SELECT ON public.scontrini_revisione_manuale_pilot TO authenticated;
REVOKE ALL ON public.scontrini_revisione_manuale_pilot FROM anon;

-- 6. La vista del cliente espone il nuovo motivo, per il messaggio in app.
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
  s.punteggio_impronta,
  s.created_at,
  s.updated_at
FROM public.scontrini s;

GRANT SELECT ON public.scontrini_app_pilot TO authenticated;
REVOKE ALL ON public.scontrini_app_pilot FROM anon;

NOTIFY pgrst, 'reload schema';
