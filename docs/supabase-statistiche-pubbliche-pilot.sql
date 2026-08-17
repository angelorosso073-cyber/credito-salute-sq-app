-- Statistiche pubbliche aggregate per splash/login Credito Salute SQ.
-- Espone solo conteggi totali, senza nomi, telefoni, prestazioni o dettagli sanitari.

create or replace function public.statistiche_pubbliche_pilot()
returns jsonb
language sql
stable
security definer
set search_path = public
as $$
  select jsonb_build_object(
    'iscritti', (
      select count(*)::int
      from public.clienti c
      where c.stato = 'attivo'
    ),
    'scontrini_caricati', (
      select count(*)::int
      from public.scontrini s
    ),
    'richieste_credito_avviate', (
      select count(*)::int
      from public.richieste_utilizzo_credito r
    )
  )
$$;

revoke all on function public.statistiche_pubbliche_pilot() from public;
grant execute on function public.statistiche_pubbliche_pilot() to anon, authenticated;
