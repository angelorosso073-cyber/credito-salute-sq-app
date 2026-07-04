-- Credito Salute SQ - Schema Supabase V2
-- Primo schema dati centrale.
-- Nota: le policy RLS vanno aggiunte in un passaggio successivo.

create extension if not exists "pgcrypto";

create table if not exists public.profili (
  id uuid primary key default gen_random_uuid(),
  auth_user_id uuid unique references auth.users(id) on delete cascade,
  ruolo text not null check (ruolo in ('cliente', 'titolare_bar', 'salute_quotidiana')),
  nome_completo text not null,
  telefono text,
  email text,
  attivo boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.bar (
  id uuid primary key default gen_random_uuid(),
  nome text not null,
  citta text not null,
  indirizzo text,
  attivo boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.operatori_bar (
  id uuid primary key default gen_random_uuid(),
  bar_id uuid not null references public.bar(id) on delete cascade,
  profilo_id uuid not null references public.profili(id) on delete cascade,
  ruolo_operativo text not null default 'titolare' check (ruolo_operativo in ('titolare', 'operatore')),
  attivo boolean not null default true,
  created_at timestamptz not null default now(),
  unique (bar_id, profilo_id)
);

create table if not exists public.clienti (
  id uuid primary key default gen_random_uuid(),
  profilo_id uuid unique references public.profili(id) on delete set null,
  codice_cliente text not null unique,
  nome text not null,
  cognome text not null,
  telefono text not null,
  email text,
  citta text,
  privacy_accettata_at timestamptz,
  consenso_programma boolean not null default false,
  consenso_marketing boolean not null default false,
  stato text not null default 'attivo' check (stato in ('attivo', 'sospeso', 'chiuso')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.scontrini (
  id uuid primary key default gen_random_uuid(),
  cliente_id uuid not null references public.clienti(id) on delete cascade,
  bar_id uuid not null references public.bar(id) on delete restrict,
  caricato_da_profilo_id uuid references public.profili(id) on delete set null,
  percorso_foto text,
  testo_ocr text,
  data_scontrino date,
  ora_scontrino time,
  numero_documento text,
  importo_dichiarato numeric(10, 2) not null check (importo_dichiarato >= 0),
  importo_ocr numeric(10, 2) check (importo_ocr is null or importo_ocr >= 0),
  importo_verificato numeric(10, 2) check (importo_verificato is null or importo_verificato >= 0),
  credito_generato numeric(10, 2) not null default 0 check (credito_generato >= 0),
  stato text not null default 'in_verifica' check (stato in ('in_verifica', 'confermato', 'rifiutato')),
  avviso_duplicato boolean not null default false,
  motivo_rifiuto text,
  verificato_da_profilo_id uuid references public.profili(id) on delete set null,
  verificato_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.verifiche_scontrini (
  id uuid primary key default gen_random_uuid(),
  scontrino_id uuid not null references public.scontrini(id) on delete cascade,
  verificato_da_profilo_id uuid references public.profili(id) on delete set null,
  stato_precedente text check (stato_precedente in ('in_verifica', 'confermato', 'rifiutato')),
  nuovo_stato text not null check (nuovo_stato in ('in_verifica', 'confermato', 'rifiutato')),
  importo_precedente numeric(10, 2),
  nuovo_importo numeric(10, 2),
  nota text,
  created_at timestamptz not null default now()
);

create table if not exists public.utilizzi_credito (
  id uuid primary key default gen_random_uuid(),
  cliente_id uuid not null references public.clienti(id) on delete cascade,
  registrato_da_profilo_id uuid references public.profili(id) on delete set null,
  tipo_prestazione text not null,
  data_prestazione date not null default current_date,
  prezzo_prestazione numeric(10, 2) not null check (prezzo_prestazione >= 0),
  credito_usato numeric(10, 2) not null check (credito_usato > 0),
  differenza_pagata numeric(10, 2) not null default 0 check (differenza_pagata >= 0),
  nota_interna text,
  created_at timestamptz not null default now()
);

create table if not exists public.log_operativi (
  id uuid primary key default gen_random_uuid(),
  profilo_id uuid references public.profili(id) on delete set null,
  azione text not null,
  tipo_entita text not null,
  entita_id uuid,
  dettagli jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create index if not exists idx_profili_auth_user_id on public.profili(auth_user_id);
create index if not exists idx_profili_ruolo on public.profili(ruolo);

create index if not exists idx_operatori_bar_bar_id on public.operatori_bar(bar_id);
create index if not exists idx_operatori_bar_profilo_id on public.operatori_bar(profilo_id);

create index if not exists idx_clienti_profilo_id on public.clienti(profilo_id);
create index if not exists idx_clienti_telefono on public.clienti(telefono);

create index if not exists idx_scontrini_cliente_id on public.scontrini(cliente_id);
create index if not exists idx_scontrini_bar_id on public.scontrini(bar_id);
create index if not exists idx_scontrini_stato on public.scontrini(stato);
create index if not exists idx_scontrini_numero_documento on public.scontrini(numero_documento);
create index if not exists idx_scontrini_data on public.scontrini(data_scontrino);

create index if not exists idx_verifiche_scontrini_scontrino_id on public.verifiche_scontrini(scontrino_id);
create index if not exists idx_utilizzi_credito_cliente_id on public.utilizzi_credito(cliente_id);

create or replace view public.saldi_clienti as
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

create or replace function public.set_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

drop trigger if exists trg_profili_updated_at on public.profili;
create trigger trg_profili_updated_at
before update on public.profili
for each row execute function public.set_updated_at();

drop trigger if exists trg_bar_updated_at on public.bar;
create trigger trg_bar_updated_at
before update on public.bar
for each row execute function public.set_updated_at();

drop trigger if exists trg_clienti_updated_at on public.clienti;
create trigger trg_clienti_updated_at
before update on public.clienti
for each row execute function public.set_updated_at();

drop trigger if exists trg_scontrini_updated_at on public.scontrini;
create trigger trg_scontrini_updated_at
before update on public.scontrini
for each row execute function public.set_updated_at();

insert into public.bar (nome, citta, indirizzo)
values ('Bar pilota Francofonte', 'Francofonte', null)
on conflict do nothing;
