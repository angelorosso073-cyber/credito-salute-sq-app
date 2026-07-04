-- Credito Salute SQ - RLS pilot per salute_quotidiana e admin
-- Obiettivo:
-- 1. usare Supabase Auth per i ruoli riservati;
-- 2. dare a salute_quotidiana il controllo operativo degli scontrini;
-- 3. dare ad admin visibilita' completa;
-- 4. togliere l'accesso anonimo alle viste sensibili.

-- Nota:
-- questo file assume che la tabella public.profili esista e abbia almeno:
-- - id uuid
-- - auth_user_id uuid
-- - ruolo text
-- Se i nomi reali differiscono, aggiorna qui prima di eseguire.

do $$
declare
  constraint_name text;
begin
  select conname
  into constraint_name
  from pg_constraint
  where conrelid = 'public.profili'::regclass
    and contype = 'c'
    and pg_get_constraintdef(oid) ilike '%ruolo%'
  limit 1;

  if constraint_name is not null then
    execute format('alter table public.profili drop constraint %I', constraint_name);
  end if;
end $$;

alter table if exists public.profili
  add constraint profili_ruolo_check
  check (lower(ruolo) in ('cliente', 'bar', 'salute_quotidiana', 'admin', 'titolare_bar', 'controllo_sq'));

create or replace function public.ruolo_corrente()
returns text
language plpgsql
security definer
set search_path = public
as $$
declare
  ruolo_text text := 'guest';
begin
  select lower(coalesce(p.ruolo, 'guest'))
  into ruolo_text
  from public.profili p
  where p.auth_user_id = auth.uid()
  limit 1;

  if ruolo_text is null or ruolo_text = '' or ruolo_text = 'guest' then
    ruolo_text := lower(coalesce(
      auth.jwt() -> 'user_metadata' ->> 'ruolo',
      auth.jwt() -> 'user_metadata' ->> 'role',
      auth.jwt() -> 'app_metadata' ->> 'ruolo',
      auth.jwt() -> 'app_metadata' ->> 'role',
      'guest'
    ));
  end if;

  case ruolo_text
    when 'titolare_bar' then return 'bar';
    when 'controllo_sq' then return 'salute_quotidiana';
    when 'salute' then return 'salute_quotidiana';
    else return ruolo_text;
  end case;
end;
$$;

create or replace function public.e_admin()
returns boolean
language sql
security definer
set search_path = public
as $$
  select public.ruolo_corrente() = 'admin'
$$;

create or replace function public.e_salute_quotidiana()
returns boolean
language sql
security definer
set search_path = public
as $$
  select public.ruolo_corrente() = 'salute_quotidiana'
$$;

create or replace function public.e_bar()
returns boolean
language sql
security definer
set search_path = public
as $$
  select public.ruolo_corrente() = 'bar'
$$;

create or replace function public.e_cliente()
returns boolean
language sql
security definer
set search_path = public
as $$
  select public.ruolo_corrente() = 'cliente'
$$;

grant execute on function public.ruolo_corrente() to authenticated;
grant execute on function public.e_admin() to authenticated;
grant execute on function public.e_salute_quotidiana() to authenticated;
grant execute on function public.e_bar() to authenticated;
grant execute on function public.e_cliente() to authenticated;

alter table public.profili enable row level security;
alter table public.bar enable row level security;
alter table public.operatori_bar enable row level security;
alter table public.clienti enable row level security;
alter table public.scontrini enable row level security;
alter table public.verifiche_scontrini enable row level security;
alter table public.utilizzi_credito enable row level security;
alter table public.log_operativi enable row level security;

drop policy if exists "profili_select_proprio_o_admin" on public.profili;
create policy "profili_select_proprio_o_admin"
on public.profili
for select
to authenticated
using (
  auth_user_id = auth.uid()
  or public.e_admin()
);

drop policy if exists "profili_insert_proprio" on public.profili;
create policy "profili_insert_proprio"
on public.profili
for insert
to authenticated
with check (
  auth_user_id = auth.uid()
  and lower(ruolo) in ('cliente', 'bar', 'salute_quotidiana', 'admin')
);

drop policy if exists "profili_update_admin" on public.profili;
create policy "profili_update_admin"
on public.profili
for update
to authenticated
using (public.e_admin())
with check (public.e_admin());

drop policy if exists "bar_select_autenticati" on public.bar;
create policy "bar_select_autenticati"
on public.bar
for select
to authenticated
using (true);

drop policy if exists "bar_gestione_admin" on public.bar;
create policy "bar_gestione_admin"
on public.bar
for all
to authenticated
using (public.e_admin())
with check (public.e_admin());

drop policy if exists "operatori_bar_select_proprio_o_admin" on public.operatori_bar;
create policy "operatori_bar_select_proprio_o_admin"
on public.operatori_bar
for select
to authenticated
using (
  exists (
    select 1
    from public.profili p
    where p.id = operatori_bar.profilo_id
      and p.auth_user_id = auth.uid()
  )
  or public.e_admin()
);

drop policy if exists "operatori_bar_gestione_admin" on public.operatori_bar;
create policy "operatori_bar_gestione_admin"
on public.operatori_bar
for all
to authenticated
using (public.e_admin())
with check (public.e_admin());

drop policy if exists "clienti_select_proprio_o_sq" on public.clienti;
create policy "clienti_select_proprio_o_sq"
on public.clienti
for select
to authenticated
using (
  public.e_salute_quotidiana()
  or public.e_admin()
  or exists (
    select 1
    from public.profili p
    where p.id = clienti.profilo_id
      and p.auth_user_id = auth.uid()
  )
);

drop policy if exists "clienti_insert_pubblico_pilot" on public.clienti;
create policy "clienti_insert_pubblico_pilot"
on public.clienti
for insert
to anon, authenticated
with check (true);

drop policy if exists "clienti_update_proprio_o_sq" on public.clienti;
create policy "clienti_update_proprio_o_sq"
on public.clienti
for update
to authenticated
using (
  public.e_admin()
  or public.e_salute_quotidiana()
  or exists (
    select 1
    from public.profili p
    where p.id = clienti.profilo_id
      and p.auth_user_id = auth.uid()
  )
)
with check (
  public.e_admin()
  or public.e_salute_quotidiana()
  or exists (
    select 1
    from public.profili p
    where p.id = clienti.profilo_id
      and p.auth_user_id = auth.uid()
  )
);

drop policy if exists "scontrini_select_per_ruolo" on public.scontrini;
create policy "scontrini_select_per_ruolo"
on public.scontrini
for select
to authenticated
using (
  public.e_admin()
  or public.e_salute_quotidiana()
  or exists (
    select 1
    from public.clienti c
    join public.profili p on p.id = c.profilo_id
    where c.id = scontrini.cliente_id
      and p.auth_user_id = auth.uid()
  )
);

drop policy if exists "scontrini_update_sq_o_admin" on public.scontrini;
create policy "scontrini_update_sq_o_admin"
on public.scontrini
for update
to authenticated
using (public.e_admin() or public.e_salute_quotidiana())
with check (public.e_admin() or public.e_salute_quotidiana());

drop policy if exists "scontrini_delete_admin" on public.scontrini;
create policy "scontrini_delete_admin"
on public.scontrini
for delete
to authenticated
using (public.e_admin());

drop policy if exists "verifiche_select_sq_o_admin" on public.verifiche_scontrini;
create policy "verifiche_select_sq_o_admin"
on public.verifiche_scontrini
for select
to authenticated
using (public.e_admin() or public.e_salute_quotidiana());

drop policy if exists "verifiche_insert_sq_o_admin" on public.verifiche_scontrini;
create policy "verifiche_insert_sq_o_admin"
on public.verifiche_scontrini
for insert
to authenticated
with check (public.e_admin() or public.e_salute_quotidiana());

drop policy if exists "utilizzi_select_cliente_o_sq" on public.utilizzi_credito;
create policy "utilizzi_select_cliente_o_sq"
on public.utilizzi_credito
for select
to authenticated
using (
  public.e_admin()
  or public.e_salute_quotidiana()
  or exists (
    select 1
    from public.clienti c
    join public.profili p on p.id = c.profilo_id
    where c.id = utilizzi_credito.cliente_id
      and p.auth_user_id = auth.uid()
  )
);

drop policy if exists "utilizzi_gestione_sq_o_admin" on public.utilizzi_credito;
create policy "utilizzi_gestione_sq_o_admin"
on public.utilizzi_credito
for all
to authenticated
using (public.e_admin() or public.e_salute_quotidiana())
with check (public.e_admin() or public.e_salute_quotidiana());

drop policy if exists "log_select_admin" on public.log_operativi;
create policy "log_select_admin"
on public.log_operativi
for select
to authenticated
using (public.e_admin());

drop policy if exists "log_insert_autenticati" on public.log_operativi;
create policy "log_insert_autenticati"
on public.log_operativi
for insert
to authenticated
with check (true);

drop view if exists public.clienti_app_pilot;
create view public.clienti_app_pilot
with (security_invoker = true)
as
select
  c.id,
  c.codice_cliente,
  c.nome,
  c.cognome,
  c.telefono,
  c.citta,
  c.created_at
from public.clienti c
where c.stato = 'attivo';

grant select on public.clienti_app_pilot to authenticated;

drop view if exists public.scontrini_app_pilot;
create view public.scontrini_app_pilot
with (security_invoker = true)
as
select
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
  s.created_at,
  s.updated_at
from public.scontrini s;

grant select on public.scontrini_app_pilot to authenticated;

drop view if exists public.utilizzi_credito_app_pilot;
create view public.utilizzi_credito_app_pilot
with (security_invoker = true)
as
select
  u.id,
  u.cliente_id,
  u.tipo_prestazione,
  u.prezzo_prestazione,
  u.credito_usato,
  greatest(u.prezzo_prestazione - u.credito_usato, 0)::numeric(10, 2) as importo_pagato,
  'se'::text as beneficiario,
  null::text as note,
  u.created_at
from public.utilizzi_credito u;

grant select on public.utilizzi_credito_app_pilot to authenticated;

drop view if exists public.saldi_clienti_app_pilot;
create view public.saldi_clienti_app_pilot
with (security_invoker = true)
as
select
  c.id as cliente_id,
  c.codice_cliente,
  c.nome,
  c.cognome,
  coalesce(sum(s.credito_generato) filter (where s.stato = 'confermato'), 0)::numeric(10, 2) as credito_confermato,
  coalesce(sum(s.credito_generato) filter (where s.stato = 'in_verifica'), 0)::numeric(10, 2) as credito_in_verifica,
  coalesce(sum(s.credito_generato) filter (where s.stato <> 'rifiutato'), 0)::numeric(10, 2) as credito_totale_generato,
  coalesce((
    select sum(u.credito_usato)
    from public.utilizzi_credito u
    where u.cliente_id = c.id
  ), 0)::numeric(10, 2) as credito_usato,
  greatest(
    coalesce(sum(s.credito_generato) filter (where s.stato = 'confermato'), 0)
    - coalesce((
      select sum(u.credito_usato)
      from public.utilizzi_credito u
      where u.cliente_id = c.id
    ), 0),
    0
  )::numeric(10, 2) as saldo_disponibile
from public.clienti c
left join public.scontrini s on s.cliente_id = c.id
where c.stato = 'attivo'
group by c.id, c.codice_cliente, c.nome, c.cognome;

grant select on public.saldi_clienti_app_pilot to authenticated;

revoke all on public.clienti_app_pilot from anon;
revoke all on public.scontrini_app_pilot from anon;
revoke all on public.utilizzi_credito_app_pilot from anon;
revoke all on public.saldi_clienti_app_pilot from anon;

notify pgrst, 'reload schema';
