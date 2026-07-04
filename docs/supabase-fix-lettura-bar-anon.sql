-- Credito Salute SQ - Fix lettura bar prima del login
-- Serve per permettere alla web app pubblica di leggere i bar attivi.
-- Non espone dati sensibili: mostra solo i bar attivi del progetto.

drop policy if exists "bar_select_autenticati" on public.bar;
drop policy if exists "bar_select_pubblico_attivi" on public.bar;

create policy "bar_select_pubblico_attivi"
on public.bar
for select
to anon, authenticated
using (
  attivo = true
  or public.e_salute_quotidiana()
);

insert into public.bar (nome, citta, indirizzo, attivo)
select 'Bar pilota Francofonte', 'Francofonte', null, true
where not exists (
  select 1
  from public.bar
  where nome = 'Bar pilota Francofonte'
);
