-- Credito Salute SQ - RPC pilot per Controllo SQ e saldo da Supabase
-- Eseguire in Supabase SQL Editor dopo la vista scontrini_app_pilot.
-- Obiettivo:
-- 1. aggiornare gli scontrini dal pannello Controllo SQ senza update diretto anonimo;
-- 2. registrare gli utilizzi credito su Supabase;
-- 3. far leggere alla web app gli utilizzi credito del pilot.

create or replace function public.aggiorna_scontrino_pilot(
  p_id uuid,
  p_stato text,
  p_importo_dichiarato numeric,
  p_importo_verificato numeric,
  p_credito_generato numeric,
  p_motivo_controllo text
)
returns uuid
language plpgsql
security definer
set search_path = public
as $$
begin
  if p_id is null then
    raise exception 'scontrino mancante';
  end if;

  if p_stato not in ('in_verifica', 'confermato', 'rifiutato') then
    raise exception 'stato non ammesso';
  end if;

  if p_stato <> 'rifiutato' and (p_importo_dichiarato is null or p_importo_dichiarato <= 0) then
    raise exception 'importo non valido';
  end if;

  update public.scontrini
  set
    stato = p_stato,
    importo_dichiarato = case
      when p_stato = 'rifiutato' then importo_dichiarato
      else coalesce(p_importo_dichiarato, importo_dichiarato)
    end,
    importo_verificato = case
      when p_stato = 'confermato' then coalesce(p_importo_verificato, p_importo_dichiarato, importo_dichiarato)
      else null
    end,
    credito_generato = case
      when p_stato = 'rifiutato' then 0
      else coalesce(p_credito_generato, credito_generato)
    end,
    motivo_rifiuto = nullif(trim(coalesce(p_motivo_controllo, '')), ''),
    verificato_at = now(),
    updated_at = now()
  where id = p_id;

  if not found then
    raise exception 'scontrino non trovato';
  end if;

  return p_id;
end;
$$;

grant execute on function public.aggiorna_scontrino_pilot(
  uuid,
  text,
  numeric,
  numeric,
  numeric,
  text
) to anon, authenticated;

create or replace function public.registra_utilizzo_credito_pilot(
  p_id uuid,
  p_cliente_id uuid,
  p_tipo_prestazione text,
  p_prezzo_prestazione numeric,
  p_credito_usato numeric,
  p_importo_pagato numeric,
  p_beneficiario text,
  p_note text
)
returns uuid
language plpgsql
security definer
set search_path = public
as $$
declare
  nuovo_id uuid;
  saldo_disponibile numeric;
begin
  if p_cliente_id is null then
    raise exception 'cliente mancante';
  end if;

  if not exists (
    select 1
    from public.clienti c
    where c.id = p_cliente_id
      and c.stato = 'attivo'
  ) then
    raise exception 'cliente non valido o non attivo';
  end if;

  if p_credito_usato is null or p_credito_usato <= 0 then
    raise exception 'credito usato non valido';
  end if;

  if p_prezzo_prestazione is null or p_prezzo_prestazione < 0 then
    raise exception 'prezzo prestazione non valido';
  end if;

  if p_credito_usato > p_prezzo_prestazione then
    raise exception 'credito superiore al prezzo prestazione';
  end if;

  select
    coalesce(sum(s.credito_generato) filter (where s.stato = 'confermato'), 0)
    - coalesce((
      select sum(u.credito_usato)
      from public.utilizzi_credito u
      where u.cliente_id = p_cliente_id
    ), 0)
  into saldo_disponibile
  from public.scontrini s
  where s.cliente_id = p_cliente_id;

  if p_credito_usato > coalesce(saldo_disponibile, 0) then
    raise exception 'credito confermato insufficiente';
  end if;

  insert into public.utilizzi_credito (
    id,
    cliente_id,
    tipo_prestazione,
    prezzo_prestazione,
    credito_usato
  )
  values (
    coalesce(p_id, gen_random_uuid()),
    p_cliente_id,
    nullif(trim(coalesce(p_tipo_prestazione, '')), ''),
    p_prezzo_prestazione,
    p_credito_usato
  )
  returning id into nuovo_id;

  return nuovo_id;
end;
$$;

grant execute on function public.registra_utilizzo_credito_pilot(
  uuid,
  uuid,
  text,
  numeric,
  numeric,
  numeric,
  text,
  text
) to anon, authenticated;

drop view if exists public.utilizzi_credito_app_pilot;

create view public.utilizzi_credito_app_pilot
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

grant select on public.utilizzi_credito_app_pilot to anon, authenticated;

drop view if exists public.saldi_clienti_app_pilot;

create view public.saldi_clienti_app_pilot
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

grant select on public.saldi_clienti_app_pilot to anon, authenticated;

notify pgrst, 'reload schema';
