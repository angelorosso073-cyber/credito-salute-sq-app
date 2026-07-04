-- Credito Salute SQ - Fix iscrizione cliente prima del login
-- Permette alla pagina pubblica del QR di creare una scheda cliente.
-- Non permette agli utenti anonimi di leggere la tabella clienti.

drop policy if exists "clienti_insert_cliente_proprio" on public.clienti;
drop policy if exists "clienti_insert_pubblico_pilot" on public.clienti;

grant usage on schema public to anon, authenticated, public;
grant insert on public.clienti to anon, authenticated, public;

create policy "clienti_insert_pubblico_pilot"
on public.clienti
for insert
to public
with check (true);
