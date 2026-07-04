-- Credito Salute SQ - Funzione controllata per registrare scontrini dal QR pubblico
-- Da preferire all'insert diretto anonimo sulla tabella scontrini.

drop function if exists public.registra_scontrino_pilot(
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
begin
  if p_cliente_id is null then
    raise exception 'cliente mancante';
  end if;

  if p_bar_id is null then
    raise exception 'bar mancante';
  end if;

  if not exists (
    select 1
    from public.clienti c
    where c.id = p_cliente_id
      and c.stato = 'attivo'
  ) then
    raise exception 'cliente non valido o non attivo';
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

  if p_credito_generato is null or p_credito_generato < 0 then
    raise exception 'credito non valido';
  end if;

  if p_stato not in ('in_verifica', 'confermato') then
    raise exception 'stato non ammesso';
  end if;

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
    p_testo_ocr,
    p_data_scontrino,
    p_ora_scontrino,
    nullif(trim(coalesce(p_numero_documento, '')), ''),
    p_importo_dichiarato,
    p_importo_ocr,
    p_importo_verificato,
    p_credito_generato,
    p_stato,
    coalesce(p_avviso_duplicato, false),
    nullif(trim(coalesce(p_motivo_controllo, '')), '')
  )
  returning id into nuovo_id;

  return nuovo_id;
end;
$$;

grant usage on schema public to anon, authenticated;

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
) to anon, authenticated;

notify pgrst, 'reload schema';
