-- Credito Salute SQ - Fix caricamento scontrino prima del login
-- Permette alla pagina pubblica del QR di creare scontrini in verifica.
-- Non permette agli utenti anonimi di leggere tutti gli scontrini.

drop policy if exists "scontrini_insert_cliente" on public.scontrini;
drop policy if exists "scontrini_insert_pubblico_pilot" on public.scontrini;
drop policy if exists "scontrini_insert_pubblico_pilot_v2" on public.scontrini;

grant usage on schema public to anon, authenticated, public;
grant insert on public.scontrini to anon, authenticated, public;

create policy "scontrini_insert_pubblico_pilot_v2"
on public.scontrini
for insert
to anon, authenticated
with check (
  true
);
