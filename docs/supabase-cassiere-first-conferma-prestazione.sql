-- Credito Salute SQ - Cassiere-First e Conferma Prestazione
-- Eseguire in Supabase SQL Editor dopo:
-- 1. docs/supabase-rls-pilot-salute-admin.sql
-- 2. docs/supabase-hardening-sicurezza-pilot.sql
--
-- Obiettivo:
-- 1. token pubblico per link saldo senza login (clienti anziani via WhatsApp);
-- 2. conferma doppia prestazione avvenuta (SQ + cliente verbale);
-- 3. stato pagamento bar (da_incassare / incassato);
-- 4. registrazione rapida cliente da cassiere bar;
-- 5. pagina saldo pubblica accessibile da anon via token.

-- 1. Token pubblico saldo per clienti
alter table public.clienti
  add column if not exists saldo_token uuid not null default gen_random_uuid();

create unique index if not exists idx_clienti_saldo_token
  on public.clienti(saldo_token);

-- 2. Conferme e stato pagamento su utilizzi_credito
alter table public.utilizzi_credito
  add column if not exists conferma_sq boolean not null default false,
  add column if not exists conferma_sq_at timestamptz,
  add column if not exists conferma_cliente boolean not null default false,
  add column if not exists conferma_cliente_at timestamptz,
  add column if not exists stato_pagamento text not null default 'da_incassare'
    check (stato_pagamento in ('da_incassare', 'incassato')),
  add column if not exists incassato_at timestamptz;

-- 3. Aggiorna vista clienti per includere saldo_token
drop view if exists public.clienti_app_pilot;
create view public.clienti_app_pilot
as
select
  c.id,
  c.codice_cliente,
  c.nome,
  c.cognome,
  c.telefono,
  c.citta,
  c.saldo_token,
  c.created_at
from public.clienti c
where c.stato = 'attivo';

grant select on public.clienti_app_pilot to authenticated;
revoke all on public.clienti_app_pilot from anon;

-- 4. Aggiorna vista utilizzi credito per includere nuovi campi
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
  coalesce(u.nota_interna, '') as note,
  u.conferma_sq,
  u.conferma_sq_at,
  u.conferma_cliente,
  u.conferma_cliente_at,
  u.stato_pagamento,
  u.incassato_at,
  u.created_at
from public.utilizzi_credito u;

grant select on public.utilizzi_credito_app_pilot to authenticated;
revoke all on public.utilizzi_credito_app_pilot from anon;

-- 5. RPC saldo pubblico per token (accessibile senza login)
create or replace function public.saldo_pubblico_per_token(p_token uuid)
returns jsonb
language plpgsql
security definer
set search_path = public
as $$
declare
  v_cliente record;
  v_confermato numeric(10, 2);
  v_in_verifica numeric(10, 2);
  v_usato numeric(10, 2);
begin
  select c.id, c.nome, c.cognome, c.codice_cliente
  into v_cliente
  from public.clienti c
  where c.saldo_token = p_token
    and c.stato = 'attivo'
  limit 1;

  if not found then
    raise exception 'token non valido';
  end if;

  select
    coalesce(sum(s.credito_generato) filter (where s.stato = 'confermato'), 0),
    coalesce(sum(s.credito_generato) filter (where s.stato = 'in_verifica'), 0)
  into v_confermato, v_in_verifica
  from public.scontrini s
  where s.cliente_id = v_cliente.id;

  select coalesce(sum(u.credito_usato), 0)
  into v_usato
  from public.utilizzi_credito u
  where u.cliente_id = v_cliente.id;

  v_confermato := greatest(v_confermato - v_usato, 0);

  return jsonb_build_object(
    'nome', v_cliente.nome,
    'cognome', v_cliente.cognome,
    'codice', v_cliente.codice_cliente,
    'confermato', v_confermato,
    'in_verifica', v_in_verifica
  );
end;
$$;

grant execute on function public.saldo_pubblico_per_token(uuid) to anon, authenticated;

-- 6. RPC registrazione rapida cliente da cassiere bar
create or replace function public.registra_cliente_rapido_pilot(
  p_nome text,
  p_cognome text,
  p_telefono text
)
returns jsonb
language plpgsql
security definer
set search_path = public
as $$
declare
  v_id uuid;
  v_token uuid;
  v_codice text;
  v_n int;
  v_ruolo text;
begin
  select p.ruolo into v_ruolo
  from public.profili p
  where p.auth_user_id = auth.uid()
  limit 1;

  if v_ruolo not in ('titolare_bar', 'bar', 'salute_quotidiana', 'admin') then
    raise exception 'ruolo non autorizzato';
  end if;

  if nullif(trim(p_nome), '') is null then raise exception 'nome richiesto'; end if;
  if nullif(trim(p_cognome), '') is null then raise exception 'cognome richiesto'; end if;
  if nullif(trim(p_telefono), '') is null then raise exception 'telefono richiesto'; end if;

  -- Se esiste gia per telefono, restituisce quello esistente
  select c.id, c.saldo_token
  into v_id, v_token
  from public.clienti c
  where c.telefono = trim(p_telefono)
  limit 1;

  if found then
    return jsonb_build_object('id', v_id, 'saldo_token', v_token, 'exists', true);
  end if;

  select count(*) + 1 into v_n from public.clienti;
  v_codice := 'SQ-' || lpad(v_n::text, 3, '0');

  insert into public.clienti (
    codice_cliente, nome, cognome, telefono, consenso_programma, stato
  ) values (
    v_codice, trim(p_nome), trim(p_cognome), trim(p_telefono), true, 'attivo'
  )
  returning id, saldo_token into v_id, v_token;

  return jsonb_build_object('id', v_id, 'saldo_token', v_token, 'exists', false);
end;
$$;

grant execute on function public.registra_cliente_rapido_pilot(text, text, text) to authenticated;

-- 7. RPC conferma prestazione avvenuta (doppia: SQ + cliente verbale)
create or replace function public.conferma_prestazione_pilot(
  p_id uuid,
  p_conferma_sq boolean,
  p_conferma_cliente boolean
)
returns uuid
language plpgsql
security definer
set search_path = public
as $$
begin
  if not (public.e_admin() or public.e_salute_quotidiana()) then
    raise exception 'ruolo non autorizzato';
  end if;

  if p_id is null then raise exception 'utilizzo mancante'; end if;

  update public.utilizzi_credito
  set
    conferma_sq = coalesce(p_conferma_sq, conferma_sq),
    conferma_sq_at = case
      when p_conferma_sq = true and conferma_sq = false then now()
      else conferma_sq_at
    end,
    conferma_cliente = coalesce(p_conferma_cliente, conferma_cliente),
    conferma_cliente_at = case
      when p_conferma_cliente = true and conferma_cliente = false then now()
      else conferma_cliente_at
    end
  where id = p_id;

  if not found then raise exception 'utilizzo non trovato'; end if;

  return p_id;
end;
$$;

grant execute on function public.conferma_prestazione_pilot(uuid, boolean, boolean) to authenticated;

-- 8. RPC segna pagamento ricevuto dal bar
create or replace function public.segna_pagamento_incassato_pilot(p_id uuid)
returns uuid
language plpgsql
security definer
set search_path = public
as $$
begin
  if not (public.e_admin() or public.e_salute_quotidiana()) then
    raise exception 'ruolo non autorizzato';
  end if;

  if p_id is null then raise exception 'utilizzo mancante'; end if;

  update public.utilizzi_credito
  set
    stato_pagamento = 'incassato',
    incassato_at = now()
  where id = p_id
    and stato_pagamento = 'da_incassare';

  if not found then
    raise exception 'utilizzo non trovato o gia incassato';
  end if;

  return p_id;
end;
$$;

grant execute on function public.segna_pagamento_incassato_pilot(uuid) to authenticated;

notify pgrst, 'reload schema';
