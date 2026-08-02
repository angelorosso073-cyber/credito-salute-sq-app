-- docs/supabase-inversione-qr-banco.sql
-- Fase C — Intervento 1: inversione del QR. Il banco espone un codice a 6 cifre rinnovato
-- ogni 90 secondi (calcolato server-side via HMAC, il segreto non lascia mai il database).
-- Il cliente inquadra o digita il codice mentre carica lo scontrino: se valido, il credito e'
-- confermato subito. Se manca (offline, caricamento da casa), il credito resta visibile ma
-- non spendibile per un numero di giorni configurabile, poi decade.
--
-- Eseguire in Supabase SQL Editor dopo docs/supabase-limiti-plausibilita-bar.sql.

-- 1. Dispositivo banco: un bar puo' avere un solo dispositivo attivo alla volta.
--    Il segreto (bytea) non e' mai leggibile da anon/authenticated: nessuna policy SELECT
--    lo espone, solo le funzioni SECURITY DEFINER di questo file lo leggono internamente.
CREATE TABLE IF NOT EXISTS public.banco_dispositivi (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  bar_id UUID NOT NULL REFERENCES public.bar(id) ON DELETE CASCADE,
  banco_token UUID NOT NULL UNIQUE DEFAULT gen_random_uuid(),
  secret BYTEA NOT NULL DEFAULT gen_random_bytes(32),
  attivo BOOLEAN NOT NULL DEFAULT true,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE public.banco_dispositivi ENABLE ROW LEVEL SECURITY;

-- Nessuna policy SELECT per anon/authenticated: la tabella si legge SOLO dall'interno
-- delle funzioni SECURITY DEFINER sotto, mai direttamente dal client.
DROP POLICY IF EXISTS "banco_dispositivi_gestione_admin_sq" ON public.banco_dispositivi;
CREATE POLICY "banco_dispositivi_gestione_admin_sq"
ON public.banco_dispositivi
FOR ALL
TO authenticated
USING (public.e_admin() OR public.e_salute_quotidiana())
WITH CHECK (public.e_admin() OR public.e_salute_quotidiana());

REVOKE ALL ON public.banco_dispositivi FROM anon, authenticated;

-- 2. Colonne aggiuntive su scontrini per il ciclo di vita del credito sospeso.
ALTER TABLE public.scontrini
  ADD COLUMN IF NOT EXISTS sospeso_scaduto_il TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS attivato_codice_banco_at TIMESTAMPTZ;

-- 3. Allargamento CHECK su motivo_sospensione: aggiunge 'codice_banco_mancante'
--    senza togliere 'importo_oltre_soglia' (Task 3).
ALTER TABLE public.scontrini
  DROP CONSTRAINT IF EXISTS scontrini_motivo_sospensione_check;
ALTER TABLE public.scontrini
  ADD CONSTRAINT scontrini_motivo_sospensione_check
  CHECK (motivo_sospensione IS NULL OR motivo_sospensione IN ('importo_oltre_soglia', 'codice_banco_mancante'));

-- 4. Allargamento CHECK su stato: aggiunge 'scaduto' ai tre valori esistenti.
ALTER TABLE public.scontrini
  DROP CONSTRAINT IF EXISTS scontrini_stato_check;
ALTER TABLE public.scontrini
  ADD CONSTRAINT scontrini_stato_check
  CHECK (stato IN ('in_verifica', 'confermato', 'rifiutato', 'scaduto'));

-- 5. Funzione interna (NON concessa a nessuno: ne' anon ne' authenticated hanno EXECUTE).
--    Postgres concede EXECUTE a PUBLIC per default sulle nuove funzioni: la REVOKE esplicita
--    e' cio' che la rende davvero non richiamabile dal client, altrimenti sarebbe un oracolo
--    per un attacco a forza bruta sulle 6 cifre.
CREATE OR REPLACE FUNCTION public.verifica_codice_banco_interna(p_bar_id UUID, p_codice TEXT)
RETURNS BOOLEAN
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  dispositivo RECORD;
  finestra_secondi INTEGER := 90;
  finestra_corrente BIGINT;
  codice_pulito TEXT;
BEGIN
  codice_pulito := NULLIF(TRIM(COALESCE(p_codice, '')), '');
  IF codice_pulito IS NULL THEN
    RETURN false;
  END IF;

  SELECT * INTO dispositivo
  FROM public.banco_dispositivi
  WHERE bar_id = p_bar_id AND attivo = true
  LIMIT 1;

  IF NOT FOUND THEN
    RETURN false;
  END IF;

  SELECT codice_banco_finestra_secondi INTO finestra_secondi
  FROM public.limiti_bar WHERE bar_id = p_bar_id;
  finestra_secondi := COALESCE(finestra_secondi, 90);

  finestra_corrente := FLOOR(EXTRACT(EPOCH FROM NOW()) / finestra_secondi)::BIGINT;

  -- Tolleranza sulla finestra precedente per assorbire la latenza tra la lettura
  -- del codice al banco e l'invio dal cliente.
  RETURN codice_pulito IN (
    LPAD((('x' || ENCODE(SUBSTRING(HMAC(dispositivo.bar_id::text || ':' || finestra_corrente::text, dispositivo.secret, 'sha256') FROM 1 FOR 4), 'hex'))::BIT(32)::BIGINT % 1000000)::TEXT, 6, '0'),
    LPAD((('x' || ENCODE(SUBSTRING(HMAC(dispositivo.bar_id::text || ':' || (finestra_corrente - 1)::text, dispositivo.secret, 'sha256') FROM 1 FOR 4), 'hex'))::BIT(32)::BIGINT % 1000000)::TEXT, 6, '0')
  );
END;
$$;

REVOKE ALL ON FUNCTION public.verifica_codice_banco_interna(uuid, text) FROM PUBLIC, anon, authenticated;

-- 6. RPC pubblica per il dispositivo banco (nessun login): restituisce solo il codice
--    attuale e i secondi rimanenti, mai il segreto.
CREATE OR REPLACE FUNCTION public.richiedi_codice_banco_pilot(p_banco_token UUID)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  dispositivo RECORD;
  bar_nome TEXT;
  finestra_secondi INTEGER;
  finestra_corrente BIGINT;
  codice_attuale TEXT;
  secondi_rimanenti INTEGER;
BEGIN
  SELECT bd.*, b.nome AS nome_bar INTO dispositivo
  FROM public.banco_dispositivi bd
  JOIN public.bar b ON b.id = bd.bar_id
  WHERE bd.banco_token = p_banco_token AND bd.attivo = true
  LIMIT 1;

  IF NOT FOUND THEN
    RETURN jsonb_build_object('ok', false, 'errore', 'dispositivo_non_trovato');
  END IF;

  SELECT codice_banco_finestra_secondi INTO finestra_secondi
  FROM public.limiti_bar WHERE bar_id = dispositivo.bar_id;
  finestra_secondi := COALESCE(finestra_secondi, 90);

  finestra_corrente := FLOOR(EXTRACT(EPOCH FROM NOW()) / finestra_secondi)::BIGINT;
  codice_attuale := LPAD((('x' || ENCODE(SUBSTRING(HMAC(dispositivo.bar_id::text || ':' || finestra_corrente::text, dispositivo.secret, 'sha256') FROM 1 FOR 4), 'hex'))::BIT(32)::BIGINT % 1000000)::TEXT, 6, '0');
  secondi_rimanenti := finestra_secondi - (EXTRACT(EPOCH FROM NOW())::BIGINT % finestra_secondi);

  RETURN jsonb_build_object(
    'ok', true,
    'bar_nome', dispositivo.nome_bar,
    'codice', codice_attuale,
    'secondi_rimanenti', secondi_rimanenti,
    'finestra_secondi', finestra_secondi
  );
END;
$$;

GRANT EXECUTE ON FUNCTION public.richiedi_codice_banco_pilot(uuid) TO anon, authenticated;

-- 7. RPC admin/SQ per generare un dispositivo banco per un bar (una tantum per esercizio).
CREATE OR REPLACE FUNCTION public.crea_dispositivo_banco_pilot(p_bar_id UUID)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  nuovo_token UUID;
BEGIN
  IF NOT (public.e_admin() OR public.e_salute_quotidiana()) THEN
    RAISE EXCEPTION 'ruolo non autorizzato';
  END IF;

  UPDATE public.banco_dispositivi SET attivo = false WHERE bar_id = p_bar_id AND attivo = true;

  INSERT INTO public.banco_dispositivi (bar_id)
  VALUES (p_bar_id)
  RETURNING banco_token INTO nuovo_token;

  RETURN jsonb_build_object('ok', true, 'banco_token', nuovo_token);
END;
$$;

GRANT EXECUTE ON FUNCTION public.crea_dispositivo_banco_pilot(uuid) TO authenticated;

-- 8. RPC per attivare in un secondo momento uno scontrino rimasto sospeso (il cliente torna
--    al bar dopo aver caricato lo scontrino da casa).
CREATE OR REPLACE FUNCTION public.attiva_scontrino_con_codice_banco_pilot(
  p_scontrino_id UUID,
  p_codice TEXT
)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  scontrino RECORD;
  profilo_corrente_id UUID;
BEGIN
  IF auth.uid() IS NULL THEN
    RAISE EXCEPTION 'accesso richiesto';
  END IF;

  SELECT p.id INTO profilo_corrente_id
  FROM public.profili p WHERE p.auth_user_id = auth.uid() LIMIT 1;

  SELECT s.* INTO scontrino
  FROM public.scontrini s
  WHERE s.id = p_scontrino_id;

  IF NOT FOUND THEN
    RETURN jsonb_build_object('ok', false, 'errore', 'scontrino_non_trovato');
  END IF;

  IF NOT (
    public.e_admin()
    OR public.e_salute_quotidiana()
    OR EXISTS (
      SELECT 1 FROM public.clienti c
      WHERE c.id = scontrino.cliente_id AND c.profilo_id = profilo_corrente_id
    )
  ) THEN
    RAISE EXCEPTION 'non autorizzato ad attivare questo scontrino';
  END IF;

  IF scontrino.stato <> 'in_verifica' OR scontrino.motivo_sospensione <> 'codice_banco_mancante' THEN
    RETURN jsonb_build_object('ok', false, 'errore', 'non_attivabile');
  END IF;

  IF scontrino.sospeso_scaduto_il IS NOT NULL AND scontrino.sospeso_scaduto_il < NOW() THEN
    RETURN jsonb_build_object('ok', false, 'errore', 'scaduto');
  END IF;

  IF NOT public.verifica_codice_banco_interna(scontrino.bar_id, p_codice) THEN
    RETURN jsonb_build_object('ok', false, 'errore', 'codice_non_valido');
  END IF;

  UPDATE public.scontrini
  SET stato = 'confermato',
      motivo_sospensione = NULL,
      sospeso_scaduto_il = NULL,
      attivato_codice_banco_at = NOW(),
      verificato_at = NOW()
  WHERE id = p_scontrino_id;

  RETURN jsonb_build_object('ok', true);
END;
$$;

GRANT EXECUTE ON FUNCTION public.attiva_scontrino_con_codice_banco_pilot(uuid, text) TO authenticated;

-- 9. Decadimento: scontrini sospesi per mancanza di codice banco, mai attivati entro la
--    finestra configurata, passano a 'scaduto'. Pensata per essere lanciata da pg_cron
--    (Task 10) o a mano da Angelo come fallback.
CREATE OR REPLACE FUNCTION public.scadi_scontrini_sospesi_pilot()
RETURNS INTEGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  righe_aggiornate INTEGER;
BEGIN
  -- Nota per Task 8 (pg_cron): questa guardia richiede che il job pg_cron esegua in un
  -- contesto che soddisfa e_admin()/e_salute_quotidiana() (es. SECURITY DEFINER con un
  -- ruolo/profilo idoneo, o un service role riconosciuto da quelle funzioni) — da
  -- riconciliare quando si configura lo scheduling.
  IF NOT (public.e_admin() OR public.e_salute_quotidiana()) THEN
    RAISE EXCEPTION 'ruolo non autorizzato';
  END IF;

  UPDATE public.scontrini
  SET stato = 'scaduto'
  WHERE stato = 'in_verifica'
    AND motivo_sospensione = 'codice_banco_mancante'
    AND sospeso_scaduto_il IS NOT NULL
    AND sospeso_scaduto_il < NOW();

  GET DIAGNOSTICS righe_aggiornate = ROW_COUNT;
  RETURN righe_aggiornate;
END;
$$;

GRANT EXECUTE ON FUNCTION public.scadi_scontrini_sospesi_pilot() TO authenticated;

-- 10. Vista scontrini_app_pilot estesa con i campi necessari al cliente per capire
--     se il proprio credito e' sospeso e quando scade.
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
  s.created_at,
  s.updated_at
FROM public.scontrini s;

GRANT SELECT ON public.scontrini_app_pilot TO authenticated;
REVOKE ALL ON public.scontrini_app_pilot FROM anon;

-- 11. Funzione finale registra_scontrino_pilot: 17 parametri (16 esistenti + p_codice_banco
--     in coda con DEFAULT NULL). p_stato passato dal client ora viene ignorato quando
--     l'importo e' entro soglia: lo stato lo decide sempre il server in base a duplicato,
--     tetto giornaliero, soglia importo e codice banco — mai il client.
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
  p_codice_banco       TEXT DEFAULT NULL
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
    -- Sopra soglia: sempre in coda di revisione manuale, indipendentemente dal codice banco.
    stato_finale := 'in_verifica';
    motivo_sospensione_finale := 'importo_oltre_soglia';
    scadenza_sospensione := NULL;
  ELSIF public.verifica_codice_banco_interna(p_bar_id, p_codice_banco) THEN
    -- Codice banco valido: presenza fisica dimostrata, confermato subito.
    stato_finale := 'confermato';
    motivo_sospensione_finale := NULL;
    scadenza_sospensione := NULL;
  ELSE
    -- Nessun codice valido (offline al bar, o caricamento da casa): credito visibile
    -- ma non spendibile finche' il cliente non torna al bar e attiva con un codice valido.
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
    motivo_sospensione, sospeso_scaduto_il
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
    scadenza_sospensione
  )
  RETURNING id INTO nuovo_id;

  RETURN nuovo_id;
END;
$$;

REVOKE ALL ON FUNCTION public.registra_scontrino_pilot(
  uuid, uuid, uuid, text, date, time, text,
  numeric, numeric, numeric, numeric, text, boolean, text, text, text, text
) FROM anon;

GRANT EXECUTE ON FUNCTION public.registra_scontrino_pilot(
  uuid, uuid, uuid, text, date, time, text,
  numeric, numeric, numeric, numeric, text, boolean, text, text, text, text
) TO authenticated;

NOTIFY pgrst, 'reload schema';
