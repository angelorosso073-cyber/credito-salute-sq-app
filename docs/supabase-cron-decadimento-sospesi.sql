-- docs/supabase-cron-decadimento-sospesi.sql
-- Programma l'esecuzione giornaliera di scadi_scontrini_sospesi_pilot() via pg_cron.
-- Se pg_cron non e' disponibile sul tuo piano Supabase, questo file fallisce alla prima
-- riga: in quel caso usa il fallback manuale descritto nello Step 3 del Task 8.

CREATE EXTENSION IF NOT EXISTS pg_cron;

-- Riconciliazione segnalata dal commento lasciato nel Task 5 (docs/supabase-inversione-qr-banco.sql):
-- la guardia di ruolo su scadi_scontrini_sospesi_pilot() si basa su auth.uid(), che e' sempre
-- NULL nel contesto di un job pg_cron (nessun JWT). Senza questa modifica il job schedulato
-- sotto fallirebbe ogni notte con 'ruolo non autorizzato'. Su Supabase i job pg_cron creati
-- dall'SQL Editor girano come ruolo 'postgres': aggiungo un bypass esplicito solo per quel
-- ruolo, che PostgREST non puo' mai assumere per una chiamata anon/authenticated (quelle
-- girano sempre come ruolo 'anon' o 'authenticated' dopo il SET ROLE di PostgREST).
CREATE OR REPLACE FUNCTION public.scadi_scontrini_sospesi_pilot()
RETURNS INTEGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  righe_aggiornate INTEGER;
BEGIN
  IF NOT (public.e_admin() OR public.e_salute_quotidiana() OR current_user = 'postgres') THEN
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

SELECT cron.schedule(
  'decadimento-scontrini-sospesi',
  '0 4 * * *',  -- ogni giorno alle 04:00 UTC
  $$SELECT public.scadi_scontrini_sospesi_pilot();$$
);
