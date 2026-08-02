-- docs/supabase-cron-decadimento-sospesi.sql
-- Programma l'esecuzione giornaliera di scadi_scontrini_sospesi_pilot() via pg_cron.
-- Se pg_cron non e' disponibile sul tuo piano Supabase, questo file fallisce alla prima
-- riga: in quel caso usa il fallback manuale descritto nello Step 3 del Task 8.

CREATE EXTENSION IF NOT EXISTS pg_cron;

SELECT cron.schedule(
  'decadimento-scontrini-sospesi',
  '0 4 * * *',  -- ogni giorno alle 04:00 UTC
  $$SELECT public.scadi_scontrini_sospesi_pilot();$$
);
