-- Credito Salute SQ - Policy RLS Supabase V2
-- Eseguire dopo docs/supabase-schema-v2.sql.

create or replace function public.profilo_corrente_id()
returns uuid
language sql
stable
security definer
set search_path = public
as $$
  select p.id
  from public.profili p
  where p.auth_user_id = auth.uid()
    and p.attivo = true
  limit 1
$$;

create or replace function public.ruolo_corrente()
returns text
language sql
stable
security definer
set search_path = public
as $$
  select p.ruolo
  from public.profili p
  where p.auth_user_id = auth.uid()
    and p.attivo = true
  limit 1
$$;

create or replace function public.cliente_corrente_id()
returns uuid
language sql
stable
security definer
set search_path = public
as $$
  select c.id
  from public.clienti c
  join public.profili p on p.id = c.profilo_id
  where p.auth_user_id = auth.uid()
    and p.attivo = true
    and c.stato = 'attivo'
  limit 1
$$;

create or replace function public.e_salute_quotidiana()
returns boolean
language sql
stable
security definer
set search_path = public
as $$
  select coalesce(public.ruolo_corrente() = 'salute_quotidiana', false)
$$;

create or replace function public.e_cliente(p_cliente_id uuid)
returns boolean
language sql
stable
security definer
set search_path = public
as $$
  select exists (
    select 1
    from public.clienti c
    join public.profili p on p.id = c.profilo_id
    where c.id = p_cliente_id
      and p.auth_user_id = auth.uid()
      and p.attivo = true
      and c.stato = 'attivo'
  )
$$;

create or replace function public.e_titolare_bar_del_bar(p_bar_id uuid)
returns boolean
language sql
stable
security definer
set search_path = public
as $$
  select exists (
    select 1
    from public.operatori_bar ob
    join public.profili p on p.id = ob.profilo_id
    where ob.bar_id = p_bar_id
      and p.auth_user_id = auth.uid()
      and p.ruolo = 'titolare_bar'
      and p.attivo = true
      and ob.attivo = true
  )
$$;

grant execute on function public.profilo_corrente_id() to authenticated;
grant execute on function public.ruolo_corrente() to authenticated;
grant execute on function public.cliente_corrente_id() to authenticated;
grant execute on function public.e_salute_quotidiana() to authenticated;
grant execute on function public.e_cliente(uuid) to authenticated;
grant execute on function public.e_titolare_bar_del_bar(uuid) to authenticated;

alter table public.profili enable row level security;
alter table public.bar enable row level security;
alter table public.operatori_bar enable row level security;
alter table public.clienti enable row level security;
alter table public.scontrini enable row level security;
alter table public.verifiche_scontrini enable row level security;
alter table public.utilizzi_credito enable row level security;
alter table public.log_operativi enable row level security;

drop policy if exists "profili_select_proprio_o_sq" on public.profili;
create policy "profili_select_proprio_o_sq"
on public.profili
for select
to authenticated
using (
  auth_user_id = auth.uid()
  or public.e_salute_quotidiana()
);

drop policy if exists "profili_insert_cliente_proprio" on public.profili;
create policy "profili_insert_cliente_proprio"
on public.profili
for insert
to authenticated
with check (
  auth_user_id = auth.uid()
  and ruolo = 'cliente'
);

drop policy if exists "profili_update_sq" on public.profili;
create policy "profili_update_sq"
on public.profili
for update
to authenticated
using (public.e_salute_quotidiana())
with check (public.e_salute_quotidiana());

drop policy if exists "bar_select_autenticati" on public.bar;
create policy "bar_select_autenticati"
on public.bar
for select
to authenticated
using (
  attivo = true
  or public.e_salute_quotidiana()
);

drop policy if exists "bar_gestione_sq" on public.bar;
create policy "bar_gestione_sq"
on public.bar
for all
to authenticated
using (public.e_salute_quotidiana())
with check (public.e_salute_quotidiana());

drop policy if exists "operatori_bar_select_proprio_o_sq" on public.operatori_bar;
create policy "operatori_bar_select_proprio_o_sq"
on public.operatori_bar
for select
to authenticated
using (
  profilo_id = public.profilo_corrente_id()
  or public.e_salute_quotidiana()
);

drop policy if exists "operatori_bar_gestione_sq" on public.operatori_bar;
create policy "operatori_bar_gestione_sq"
on public.operatori_bar
for all
to authenticated
using (public.e_salute_quotidiana())
with check (public.e_salute_quotidiana());

drop policy if exists "clienti_select_proprio_o_sq" on public.clienti;
create policy "clienti_select_proprio_o_sq"
on public.clienti
for select
to authenticated
using (
  public.e_cliente(id)
  or public.e_salute_quotidiana()
);

drop policy if exists "clienti_insert_cliente_proprio" on public.clienti;
create policy "clienti_insert_cliente_proprio"
on public.clienti
for insert
to authenticated
with check (
  profilo_id = public.profilo_corrente_id()
  and consenso_programma = true
);

drop policy if exists "clienti_update_proprio_o_sq" on public.clienti;
create policy "clienti_update_proprio_o_sq"
on public.clienti
for update
to authenticated
using (
  public.e_cliente(id)
  or public.e_salute_quotidiana()
)
with check (
  public.e_cliente(id)
  or public.e_salute_quotidiana()
);

drop policy if exists "scontrini_select_per_ruolo" on public.scontrini;
create policy "scontrini_select_per_ruolo"
on public.scontrini
for select
to authenticated
using (
  public.e_cliente(cliente_id)
  or public.e_titolare_bar_del_bar(bar_id)
  or public.e_salute_quotidiana()
);

drop policy if exists "scontrini_insert_cliente" on public.scontrini;
create policy "scontrini_insert_cliente"
on public.scontrini
for insert
to authenticated
with check (
  public.e_cliente(cliente_id)
  and stato = 'in_verifica'
);

drop policy if exists "scontrini_update_bar_o_sq" on public.scontrini;
create policy "scontrini_update_bar_o_sq"
on public.scontrini
for update
to authenticated
using (
  public.e_titolare_bar_del_bar(bar_id)
  or public.e_salute_quotidiana()
)
with check (
  public.e_titolare_bar_del_bar(bar_id)
  or public.e_salute_quotidiana()
);

drop policy if exists "scontrini_delete_sq" on public.scontrini;
create policy "scontrini_delete_sq"
on public.scontrini
for delete
to authenticated
using (public.e_salute_quotidiana());

drop policy if exists "verifiche_select_bar_o_sq" on public.verifiche_scontrini;
create policy "verifiche_select_bar_o_sq"
on public.verifiche_scontrini
for select
to authenticated
using (
  public.e_salute_quotidiana()
  or exists (
    select 1
    from public.scontrini s
    where s.id = verifiche_scontrini.scontrino_id
      and public.e_titolare_bar_del_bar(s.bar_id)
  )
);

drop policy if exists "verifiche_insert_bar_o_sq" on public.verifiche_scontrini;
create policy "verifiche_insert_bar_o_sq"
on public.verifiche_scontrini
for insert
to authenticated
with check (
  public.e_salute_quotidiana()
  or exists (
    select 1
    from public.scontrini s
    where s.id = verifiche_scontrini.scontrino_id
      and public.e_titolare_bar_del_bar(s.bar_id)
  )
);

drop policy if exists "utilizzi_select_cliente_o_sq" on public.utilizzi_credito;
create policy "utilizzi_select_cliente_o_sq"
on public.utilizzi_credito
for select
to authenticated
using (
  public.e_cliente(cliente_id)
  or public.e_salute_quotidiana()
);

drop policy if exists "utilizzi_gestione_sq" on public.utilizzi_credito;
create policy "utilizzi_gestione_sq"
on public.utilizzi_credito
for all
to authenticated
using (public.e_salute_quotidiana())
with check (public.e_salute_quotidiana());

drop policy if exists "log_select_sq" on public.log_operativi;
create policy "log_select_sq"
on public.log_operativi
for select
to authenticated
using (public.e_salute_quotidiana());

drop policy if exists "log_insert_autenticati" on public.log_operativi;
create policy "log_insert_autenticati"
on public.log_operativi
for insert
to authenticated
with check (
  profilo_id = public.profilo_corrente_id()
  or public.e_salute_quotidiana()
);

drop view if exists public.scontrini_bar_verifica;
create view public.scontrini_bar_verifica as
select
  s.id,
  s.bar_id,
  s.cliente_id,
  c.codice_cliente,
  c.nome as nome_cliente,
  c.cognome as cognome_cliente,
  s.percorso_foto,
  s.data_scontrino,
  s.ora_scontrino,
  s.numero_documento,
  s.importo_dichiarato,
  s.importo_ocr,
  s.importo_verificato,
  s.credito_generato,
  s.stato,
  s.avviso_duplicato,
  s.motivo_rifiuto,
  s.created_at,
  s.updated_at
from public.scontrini s
join public.clienti c on c.id = s.cliente_id
where
  public.e_salute_quotidiana()
  or public.e_titolare_bar_del_bar(s.bar_id);

grant select on public.scontrini_bar_verifica to authenticated;

drop view if exists public.saldi_clienti;
create view public.saldi_clienti
with (security_invoker = true)
as
select
  c.id as cliente_id,
  c.codice_cliente,
  c.nome,
  c.cognome,
  coalesce(sum(s.credito_generato) filter (where s.stato = 'confermato'), 0)::numeric(10, 2) as credito_confermato,
  coalesce(sum(s.credito_generato) filter (where s.stato = 'in_verifica'), 0)::numeric(10, 2) as credito_in_verifica,
  coalesce((
    select sum(u.credito_usato)
    from public.utilizzi_credito u
    where u.cliente_id = c.id
  ), 0)::numeric(10, 2) as credito_usato,
  (
    coalesce(sum(s.credito_generato) filter (where s.stato = 'confermato'), 0)
    - coalesce((
      select sum(u.credito_usato)
      from public.utilizzi_credito u
      where u.cliente_id = c.id
    ), 0)
  )::numeric(10, 2) as saldo_disponibile
from public.clienti c
left join public.scontrini s on s.cliente_id = c.id
group by c.id, c.codice_cliente, c.nome, c.cognome;

grant select on public.saldi_clienti to authenticated;

-- Storage foto scontrini.
-- Convenzione percorso file:
-- foto-scontrini/{cliente_id}/{nome_file}

insert into storage.buckets (id, name, public)
values ('foto-scontrini', 'foto-scontrini', false)
on conflict (id) do nothing;

drop policy if exists "foto_scontrini_select_per_ruolo" on storage.objects;
create policy "foto_scontrini_select_per_ruolo"
on storage.objects
for select
to authenticated
using (
  bucket_id = 'foto-scontrini'
  and (
    public.e_salute_quotidiana()
    or public.e_cliente((storage.foldername(name))[1]::uuid)
    or exists (
      select 1
      from public.scontrini s
      where s.percorso_foto = name
        and public.e_titolare_bar_del_bar(s.bar_id)
    )
  )
);

drop policy if exists "foto_scontrini_insert_cliente" on storage.objects;
create policy "foto_scontrini_insert_cliente"
on storage.objects
for insert
to authenticated
with check (
  bucket_id = 'foto-scontrini'
  and public.e_cliente((storage.foldername(name))[1]::uuid)
);

drop policy if exists "foto_scontrini_update_sq" on storage.objects;
create policy "foto_scontrini_update_sq"
on storage.objects
for update
to authenticated
using (
  bucket_id = 'foto-scontrini'
  and public.e_salute_quotidiana()
)
with check (
  bucket_id = 'foto-scontrini'
  and public.e_salute_quotidiana()
);

drop policy if exists "foto_scontrini_delete_sq" on storage.objects;
create policy "foto_scontrini_delete_sq"
on storage.objects
for delete
to authenticated
using (
  bucket_id = 'foto-scontrini'
  and public.e_salute_quotidiana()
);
