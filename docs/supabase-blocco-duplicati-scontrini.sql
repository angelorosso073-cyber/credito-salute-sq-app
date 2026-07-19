-- Credito Salute SQ - blocco duplicati scontrini
-- Eseguire in Supabase SQL Editor dopo docs/supabase-hardening-sicurezza-pilot.sql.
--
-- Obiettivo:
-- 1. impedire il reinvio dello stesso scontrino;
-- 2. bloccare il duplicato nel database, non solo nel browser;
-- 3. mantenere ogni nuovo scontrino in stato in_verifica.
-- Nota: il controllo duplicati non usa l'ora, perche' l'OCR o l'inserimento manuale
-- possono produrre piccole differenze anche sulla stessa foto.

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
  documento_normalizzato text;
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

  documento_normalizzato := lower(nullif(trim(coalesce(p_numero_documento, '')), ''));

  if documento_normalizzato is null then
    raise exception 'numero documento mancante';
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

  if exists (
    select 1
    from public.scontrini s
    where s.bar_id = p_bar_id
      and s.data_scontrino = p_data_scontrino
      and lower(trim(coalesce(s.numero_documento, ''))) = documento_normalizzato
      and round(s.importo_dichiarato::numeric, 2) = round(p_importo_dichiarato::numeric, 2)
      and s.stato <> 'rifiutato'
  ) then
    raise exception 'scontrino duplicato: stesso bar, data, numero documento e importo';
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
    documento_normalizzato,
    p_importo_dichiarato,
    p_importo_ocr,
    null,
    credito_calcolato,
    'in_verifica',
    false,
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

notify pgrst, 'reload schema';
