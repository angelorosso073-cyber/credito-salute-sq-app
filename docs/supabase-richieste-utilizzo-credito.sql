-- Credito Salute SQ - richieste utilizzo credito
-- Eseguire in Supabase SQL Editor dopo:
-- 1. docs/supabase-hardening-sicurezza-pilot.sql
-- 2. docs/supabase-blocco-duplicati-scontrini.sql
--
-- Obiettivo:
-- 1. il cliente puo' richiedere uso credito quando ha almeno credito confermato maggiore di zero;
-- 2. la richiesta non conferma appuntamenti e non consuma credito;
-- 3. Salute Quotidiana controlla e aggiorna manualmente lo stato;
-- 4. il titolare bar non vede richieste, beneficiari o prestazioni.

create table if not exists public.richieste_utilizzo_credito (
  id uuid primary key default gen_random_uuid(),
  cliente_id uuid not null references public.clienti(id) on delete cascade,
  prestazione text not null,
  prezzo_prestazione numeric(10, 2) not null,
  credito_richiesto numeric(10, 2) not null,
  beneficiario_tipo text not null default 'se',
  beneficiario_nome text,
  beneficiario_telefono text,
  giorno_preferito date,
  fascia_oraria_preferita text,
  consenso_contatto boolean not null default false,
  note_cliente text,
  stato text not null default 'inviata',
  gestito_da_profilo_id uuid references public.profili(id) on delete set null,
  note_interne_sq text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  check (prezzo_prestazione > 0),
  check (credito_richiesto > 0),
  check (credito_richiesto <= prezzo_prestazione),
  check (beneficiario_tipo in ('se', 'altra_persona')),
  check (stato in ('inviata', 'in_contatto', 'confermata', 'rifiutata', 'annullata'))
);

create index if not exists idx_richieste_utilizzo_cliente
on public.richieste_utilizzo_credito(cliente_id);

create index if not exists idx_richieste_utilizzo_stato
on public.richieste_utilizzo_credito(stato, created_at desc);

drop trigger if exists trg_richieste_utilizzo_updated_at on public.richieste_utilizzo_credito;
create trigger trg_richieste_utilizzo_updated_at
before update on public.richieste_utilizzo_credito
for each row execute function public.set_updated_at();

alter table public.richieste_utilizzo_credito enable row level security;

drop policy if exists "richieste_select_cliente_o_sq" on public.richieste_utilizzo_credito;
create policy "richieste_select_cliente_o_sq"
on public.richieste_utilizzo_credito
for select
to authenticated
using (
  public.e_admin()
  or public.e_salute_quotidiana()
  or exists (
    select 1
    from public.clienti c
    join public.profili p on p.id = c.profilo_id
    where c.id = richieste_utilizzo_credito.cliente_id
      and p.auth_user_id = auth.uid()
  )
);

drop policy if exists "richieste_no_insert_diretto" on public.richieste_utilizzo_credito;
create policy "richieste_no_insert_diretto"
on public.richieste_utilizzo_credito
for insert
to authenticated
with check (false);

drop policy if exists "richieste_update_sq_o_admin" on public.richieste_utilizzo_credito;
create policy "richieste_update_sq_o_admin"
on public.richieste_utilizzo_credito
for update
to authenticated
using (public.e_admin() or public.e_salute_quotidiana())
with check (public.e_admin() or public.e_salute_quotidiana());

drop view if exists public.richieste_utilizzo_credito_app_pilot;
create view public.richieste_utilizzo_credito_app_pilot
with (security_invoker = true)
as
select
  r.id,
  r.cliente_id,
  c.codice_cliente,
  c.nome as cliente_nome,
  c.cognome as cliente_cognome,
  r.prestazione,
  r.prezzo_prestazione,
  r.credito_richiesto,
  r.beneficiario_tipo,
  r.beneficiario_nome,
  r.beneficiario_telefono,
  r.giorno_preferito,
  r.fascia_oraria_preferita,
  r.consenso_contatto,
  r.note_cliente,
  r.stato,
  r.note_interne_sq,
  r.created_at,
  r.updated_at
from public.richieste_utilizzo_credito r
join public.clienti c on c.id = r.cliente_id;

grant select on public.richieste_utilizzo_credito_app_pilot to authenticated;
revoke all on public.richieste_utilizzo_credito_app_pilot from anon;

create or replace function public.saldo_cliente_confermato(p_cliente_id uuid)
returns numeric
language sql
security definer
set search_path = public
as $$
  select greatest(
    coalesce((
      select sum(s.credito_generato)
      from public.scontrini s
      where s.cliente_id = p_cliente_id
        and s.stato = 'confermato'
    ), 0)
    - coalesce((
      select sum(u.credito_usato)
      from public.utilizzi_credito u
      where u.cliente_id = p_cliente_id
    ), 0),
    0
  )::numeric(10, 2)
$$;

grant execute on function public.saldo_cliente_confermato(uuid) to authenticated;

create or replace function public.crea_richiesta_utilizzo_credito_pilot(
  p_cliente_id uuid,
  p_prestazione text,
  p_prezzo_prestazione numeric,
  p_beneficiario_tipo text,
  p_beneficiario_nome text,
  p_beneficiario_telefono text,
  p_giorno_preferito date,
  p_fascia_oraria_preferita text,
  p_consenso_contatto boolean,
  p_note_cliente text
)
returns uuid
language plpgsql
security definer
set search_path = public
as $$
declare
  nuovo_id uuid;
  profilo_corrente_id uuid;
  saldo_disponibile numeric;
  credito_applicabile numeric(10, 2);
  prestazione_pulita text;
  beneficiario_tipo_pulito text;
begin
  if auth.uid() is null then
    raise exception 'accesso richiesto';
  end if;

  if p_cliente_id is null then
    raise exception 'cliente mancante';
  end if;

  select p.id
  into profilo_corrente_id
  from public.profili p
  where p.auth_user_id = auth.uid()
  limit 1;

  if profilo_corrente_id is null then
    raise exception 'profilo non trovato';
  end if;

  if not exists (
    select 1
    from public.clienti c
    where c.id = p_cliente_id
      and c.profilo_id = profilo_corrente_id
      and c.stato = 'attivo'
  ) then
    raise exception 'cliente non autorizzato';
  end if;

  prestazione_pulita := trim(coalesce(p_prestazione, ''));
  beneficiario_tipo_pulito := coalesce(nullif(trim(p_beneficiario_tipo), ''), 'se');

  if prestazione_pulita not in (
    'Controllo parametri base a domicilio',
    'Controllo parametri completo a domicilio',
    'Parametri + breve educazione sanitaria'
  ) then
    raise exception 'prestazione non ammessa';
  end if;

  if prestazione_pulita = 'Controllo parametri base a domicilio' and p_prezzo_prestazione <> 20 then
    raise exception 'prezzo prestazione non valido';
  end if;

  if prestazione_pulita = 'Controllo parametri completo a domicilio' and p_prezzo_prestazione <> 25 then
    raise exception 'prezzo prestazione non valido';
  end if;

  if prestazione_pulita = 'Parametri + breve educazione sanitaria' and p_prezzo_prestazione <> 30 then
    raise exception 'prezzo prestazione non valido';
  end if;

  if beneficiario_tipo_pulito not in ('se', 'altra_persona') then
    raise exception 'beneficiario non valido';
  end if;

  if beneficiario_tipo_pulito = 'altra_persona'
    and nullif(trim(coalesce(p_beneficiario_nome, '')), '') is null then
    raise exception 'nome beneficiario richiesto';
  end if;

  if p_consenso_contatto is not true then
    raise exception 'consenso al contatto richiesto';
  end if;

  if p_giorno_preferito is not null and p_giorno_preferito < current_date then
    raise exception 'giorno preferito non valido';
  end if;

  if exists (
    select 1
    from public.richieste_utilizzo_credito r
    where r.cliente_id = p_cliente_id
      and r.stato in ('inviata', 'in_contatto', 'confermata')
  ) then
    raise exception 'esiste gia una richiesta utilizzo credito attiva';
  end if;

  saldo_disponibile := public.saldo_cliente_confermato(p_cliente_id);

  if saldo_disponibile <= 0 then
    raise exception 'serve almeno un credito SQ confermato';
  end if;

  credito_applicabile := round(least(saldo_disponibile, p_prezzo_prestazione)::numeric, 2);

  insert into public.richieste_utilizzo_credito (
    cliente_id,
    prestazione,
    prezzo_prestazione,
    credito_richiesto,
    beneficiario_tipo,
    beneficiario_nome,
    beneficiario_telefono,
    giorno_preferito,
    fascia_oraria_preferita,
    consenso_contatto,
    note_cliente,
    stato
  )
  values (
    p_cliente_id,
    prestazione_pulita,
    p_prezzo_prestazione,
    credito_applicabile,
    beneficiario_tipo_pulito,
    nullif(trim(coalesce(p_beneficiario_nome, '')), ''),
    nullif(trim(coalesce(p_beneficiario_telefono, '')), ''),
    p_giorno_preferito,
    nullif(trim(coalesce(p_fascia_oraria_preferita, '')), ''),
    p_consenso_contatto,
    left(nullif(trim(coalesce(p_note_cliente, '')), ''), 500),
    'inviata'
  )
  returning id into nuovo_id;

  return nuovo_id;
end;
$$;

grant execute on function public.crea_richiesta_utilizzo_credito_pilot(
  uuid,
  text,
  numeric,
  text,
  text,
  text,
  date,
  text,
  boolean,
  text
) to authenticated;

create or replace function public.aggiorna_richiesta_utilizzo_credito_pilot(
  p_id uuid,
  p_stato text,
  p_note_interne_sq text
)
returns uuid
language plpgsql
security definer
set search_path = public
as $$
declare
  profilo_corrente_id uuid;
begin
  if not (public.e_admin() or public.e_salute_quotidiana()) then
    raise exception 'ruolo non autorizzato';
  end if;

  if p_id is null then
    raise exception 'richiesta mancante';
  end if;

  if p_stato not in ('inviata', 'in_contatto', 'confermata', 'rifiutata', 'annullata') then
    raise exception 'stato richiesta non ammesso';
  end if;

  select p.id
  into profilo_corrente_id
  from public.profili p
  where p.auth_user_id = auth.uid()
  limit 1;

  update public.richieste_utilizzo_credito
  set
    stato = p_stato,
    gestito_da_profilo_id = profilo_corrente_id,
    note_interne_sq = left(nullif(trim(coalesce(p_note_interne_sq, '')), ''), 500),
    updated_at = now()
  where id = p_id;

  if not found then
    raise exception 'richiesta non trovata';
  end if;

  return p_id;
end;
$$;

grant execute on function public.aggiorna_richiesta_utilizzo_credito_pilot(
  uuid,
  text,
  text
) to authenticated;

notify pgrst, 'reload schema';
