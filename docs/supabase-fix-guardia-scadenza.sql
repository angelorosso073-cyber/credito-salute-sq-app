-- docs/supabase-fix-guardia-scadenza.sql
-- Correzione della guardia di ruolo di scadi_scontrini_sospesi_pilot().
--
-- IL DIFETTO
-- docs/supabase-cron-decadimento-sospesi.sql introduce il bypass `current_user = 'postgres'`
-- per permettere al job pg_cron di eseguire la funzione senza JWT. Ma la funzione e'
-- SECURITY DEFINER: dentro il suo corpo `current_user` vale sempre il proprietario della
-- funzione, cioe' 'postgres', qualunque sia il chiamante. Il terzo ramo dell'OR e' quindi
-- sempre vero e la guardia non blocca nessuno. Verificato empiricamente: una POST anonima
-- su /rest/v1/rpc/scadi_scontrini_sospesi_pilot con la sola anon key risponde 200 con il
-- conteggio delle righe, invece di sollevare 'ruolo non autorizzato'.
-- Aggravante: nessuna REVOKE esplicita, e Postgres concede EXECUTE a PUBLIC per default
-- sulle funzioni nuove, quindi anche 'anon' ha il permesso di chiamarla.
--
-- LA CORREZIONE
-- `session_user` non viene alterato da SECURITY DEFINER: resta il ruolo di sessione reale.
-- Sotto PostgREST vale sempre 'authenticator' (il SET ROLE verso anon/authenticated cambia
-- current_user, non session_user); sotto un job pg_cron creato dall'SQL Editor vale
-- 'postgres'. E' quindi il discriminante corretto per distinguere il cron dal client.
-- In piu' revochiamo EXECUTE a PUBLIC e ad anon, cosi' la chiamata anonima viene fermata
-- dal permesso prima ancora di entrare nel corpo della funzione.

CREATE OR REPLACE FUNCTION public.scadi_scontrini_sospesi_pilot()
RETURNS INTEGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  righe_aggiornate INTEGER;
BEGIN
  -- session_user, non current_user: vedi nota in testa al file.
  IF NOT (public.e_admin() OR public.e_salute_quotidiana() OR session_user = 'postgres') THEN
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

-- Difesa in profondita': togliamo il permesso a chi non deve nemmeno poter provare.
-- 'authenticated' lo mantiene perche' e' il ruolo con cui Angelo (salute_quotidiana)
-- esegue il fallback manuale; la guardia interna filtra gli altri utenti autenticati.
REVOKE EXECUTE ON FUNCTION public.scadi_scontrini_sospesi_pilot() FROM PUBLIC;
REVOKE EXECUTE ON FUNCTION public.scadi_scontrini_sospesi_pilot() FROM anon;
GRANT EXECUTE ON FUNCTION public.scadi_scontrini_sospesi_pilot() TO authenticated;


-- ── Verifica ──────────────────────────────────────────────────────────────────
-- 1. Nessun EXECUTE residuo per anon o PUBLIC: la query deve restituire 0 righe.
SELECT grantee, privilege_type
FROM information_schema.role_routine_grants
WHERE routine_name = 'scadi_scontrini_sospesi_pilot'
  AND grantee IN ('anon', 'PUBLIC');

-- 2. Il job notturno deve essere ancora schedulato e attivo.
--    (se restituisce 0 righe, pg_cron non e' installato o la schedule non fu creata:
--     in quel caso vale il fallback manuale documentato in supabase-cron-decadimento-sospesi.sql)
SELECT jobid, schedule, command, active
FROM cron.job
WHERE jobname = 'decadimento-scontrini-sospesi';

-- 3. Esecuzione manuale di controllo: da SQL Editor session_user e' 'postgres',
--    quindi deve funzionare e restituire il numero di scontrini scaduti (spesso 0).
SELECT public.scadi_scontrini_sospesi_pilot();
