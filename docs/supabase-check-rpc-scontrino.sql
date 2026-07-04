-- Credito Salute SQ - Controllo funzione registra_scontrino_pilot
-- Esegui questo file in Supabase SQL Editor.

select
  p.proname as nome_funzione,
  pg_get_function_identity_arguments(p.oid) as argomenti,
  pg_get_function_result(p.oid) as risultato
from pg_proc p
join pg_namespace n on n.oid = p.pronamespace
where n.nspname = 'public'
  and p.proname = 'registra_scontrino_pilot';

select pg_notify('pgrst', 'reload schema') as reload_schema;
