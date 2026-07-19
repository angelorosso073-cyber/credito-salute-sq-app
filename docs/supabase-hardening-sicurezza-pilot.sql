-- Credito Salute SQ - hardening sicurezza pilot
-- Eseguire in Supabase SQL Editor dopo:
-- 1. docs/supabase-schema-v2.sql
-- 2. docs/supabase-rls-pilot-salute-admin.sql
-- 3. docs/supabase-report-bar-corrente-pilot.sql
--
-- Obiettivo:
-- 1. togliere accessi anonimi alle funzioni critiche;
-- 2. non fidarsi di credito, stato e ruoli passati dal frontend;
-- 3. lasciare conferma scontrini e utilizzi credito solo a Salute Quotidiana o admin.

revoke execute on function public.registra_scontrino_pilot(
  uuid,
  uuid,
  uuid,
  text,
  date,
  time,
  text,
  numeric,
  numeric,
  numeric,
  numeric,
  text,
  boolean,
  text
) from anon;

revoke execute on function public.aggiorna_scontrino_pilot(
  uuid,
  text,
  numeric,
  numeric,
  numeric,
  text
) from anon;

revoke execute on function public.registra_utilizzo_credito_pilot(
  uuid,
  uuid,
  text,
  numeric,
  numeric,
  numeric,
  text,
  text
) from anon;

revoke insert on public.clienti from anon;
revoke insert on public.scontrini from anon;
revoke all on public.utilizzi_credito_app_pilot from anon;
revoke all on public.saldi_clienti_app_pilot from anon;

drop policy if exists "profili_insert_proprio" on public.profili;
create policy "profili_insert_proprio"
on public.profili
for insert
to authenticated
with check (
  auth_user_id = auth.uid()
  and lower(ruolo) = 'cliente'
);

drop policy if exists "clienti_insert_pubblico_pilot" on public.clienti;
drop policy if exists "clienti_insert_cliente_o_sq" on public.clienti;
create policy "clienti_insert_cliente_o_sq"
on public.clienti
for insert
to authenticated
with check (
  public.e_admin()
  or public.e_salute_quotidiana()
  or exists (
    select 1
    from public.profili p
    where p.id = clienti.profilo_id
      and p.auth_user_id = auth.uid()
      and lower(p.ruolo) = 'cliente'
  )
);

create or replace function public.registra_scontrino_pilot(
  p_id uuid,
  p_cliente_id uuid,
  p_bar_id uuid,
  p_testo_ocr text,
  p_data_scontrino date,
  p_ora_scontrino time,
  p_numero_documento text,
  p_importo_dichiarato numeric,
  p_importo_ocr numeric,
  p_importo_verificato numeric,
  p_credito_generato numeric,
  p_stato text,
  p_avviso_duplicato boolean,
  p_motivo_controllo text
)
returns uuid
language plpgsql
security definer
set search_path = public
as $$
declare
  nuovo_id uuid;
  profilo_corrente_id uuid;
  credito_calcolato numeric(10, 2);
begin
  if auth.uid() is null then
    raise exception 'accesso richiesto';
  end if;

  if p_cliente_id is null then
    raise exception 'cliente mancante';
  end if;

  if p_bar_id is null then
    raise exception 'bar mancante';
  end if;

  select p.id
  into profilo_corrente_id
  from public.profili p
  where p.auth_user_id = auth.uid()
  limit 1;

  if profilo_corrente_id is null then
    raise exception 'profilo non trovato';
  end if;

  if not (
    public.e_admin()
    or public.e_salute_quotidiana()
    or exists (
      select 1
      from public.clienti c
      where c.id = p_cliente_id
        and c.profilo_id = profilo_corrente_id
        and c.stato = 'attivo'
    )
  ) then
    raise exception 'cliente non autorizzato';
  end if;

  if not exists (
    select 1
    from public.bar b
    where b.id = p_bar_id
      and b.attivo = true
  ) then
    raise exception 'bar non valido o non attivo';
  end if;

  if p_importo_dichiarato is null or p_importo_dichiarato <= 0 then
    raise exception 'importo non valido';
  end if;

  if p_data_scontrino is null then
    raise exception 'data scontrino mancante';
  end if;

  if p_data_scontrino > current_date then
    raise exception 'data scontrino futura';
  end if;

  credito_calcolato := round((p_importo_dichiarato * 0.03)::numeric, 2);

  insert into public.scontrini (
    id,
    cliente_id,
    bar_id,
    testo_ocr,
    data_scontrino,
    ora_scontrino,
    numero_documento,
    importo_dichiarato,
    importo_ocr,
    importo_verificato,
    credito_generato,
    stato,
    avviso_duplicato,
    motivo_rifiuto
  )
  values (
    coalesce(p_id, gen_random_uuid()),
    p_cliente_id,
    p_bar_id,
    left(p_testo_ocr, 4000),
    p_data_scontrino,
    p_ora_scontrino,
    nullif(trim(coalesce(p_numero_documento, '')), ''),
    p_importo_dichiarato,
    p_importo_ocr,
    null,
    credito_calcolato,
    'in_verifica',
    coalesce(p_avviso_duplicato, false),
    nullif(trim(coalesce(p_motivo_controllo, '')), '')
  )
  returning id into nuovo_id;

  return nuovo_id;
end;
$$;

grant execute on function public.registra_scontrino_pilot(
  uuid,
  uuid,
  uuid,
  text,
  date,
  time,
  text,
  numeric,
  numeric,
  numeric,
  numeric,
  text,
  boolean,
  text
) to authenticated;

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
declare
  profilo_corrente_id uuid;
  importo_finale numeric;
  credito_calcolato numeric(10, 2);
begin
  if not (public.e_admin() or public.e_salute_quotidiana()) then
    raise exception 'ruolo non autorizzato';
  end if;

  if p_id is null then
    raise exception 'scontrino mancante';
  end if;

  if p_stato not in ('in_verifica', 'confermato', 'rifiutato') then
    raise exception 'stato non ammesso';
  end if;

  select p.id
  into profilo_corrente_id
  from public.profili p
  where p.auth_user_id = auth.uid()
  limit 1;

  if profilo_corrente_id is null then
    raise exception 'profilo non trovato';
  end if;

  importo_finale := coalesce(p_importo_verificato, p_importo_dichiarato);

  if p_stato <> 'rifiutato' and (importo_finale is null or importo_finale <= 0) then
    raise exception 'importo non valido';
  end if;

  credito_calcolato := case
    when p_stato = 'rifiutato' then 0
    else round((importo_finale * 0.03)::numeric, 2)
  end;

  update public.scontrini
  set
    stato = p_stato,
    importo_dichiarato = case
      when p_stato = 'rifiutato' then importo_dichiarato
      else importo_finale
    end,
    importo_verificato = case
      when p_stato = 'confermato' then importo_finale
      else null
    end,
    credito_generato = credito_calcolato,
    motivo_rifiuto = case
      when p_stato = 'rifiutato' then nullif(trim(coalesce(p_motivo_controllo, '')), '')
      else nullif(trim(coalesce(p_motivo_controllo, '')), '')
    end,
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
) to authenticated;

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
  profilo_corrente_id uuid;
begin
  if not (public.e_admin() or public.e_salute_quotidiana()) then
    raise exception 'ruolo non autorizzato';
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
) to authenticated;

notify pgrst, 'reload schema';
