-- Credito Salute SQ - funzioni test accumulo credito
-- Uso: solo per test interni della web app.
-- Non usare per credito reale.
--
-- Obiettivo:
-- 1. simulare credito SQ confermato su un cliente;
-- 2. testare card "Richiedi utilizzo credito" a 20/25/30 euro SQ;
-- 3. poter rimuovere facilmente gli scontrini test.

create or replace function public.test_simula_credito_sq(
  p_cliente_id uuid,
  p_credito_sq numeric
)
returns uuid
language plpgsql
security definer
set search_path = public
as $$
declare
  nuovo_id uuid;
  bar_corrente_id uuid;
  importo_simulato numeric(10, 2);
begin
  if not (public.e_admin() or public.e_salute_quotidiana()) then
    raise exception 'ruolo non autorizzato';
  end if;

  if p_cliente_id is null then
    raise exception 'cliente mancante';
  end if;

  if p_credito_sq is null or p_credito_sq <= 0 then
    raise exception 'credito SQ non valido';
  end if;

  if p_credito_sq > 100 then
    raise exception 'credito SQ test troppo alto';
  end if;

  if not exists (
    select 1
    from public.clienti c
    where c.id = p_cliente_id
      and c.stato = 'attivo'
  ) then
    raise exception 'cliente non valido o non attivo';
  end if;

  select b.id
  into bar_corrente_id
  from public.bar b
  where b.attivo = true
  order by b.created_at asc
  limit 1;

  if bar_corrente_id is null then
    raise exception 'bar attivo non trovato';
  end if;

  importo_simulato := round((p_credito_sq / 0.03)::numeric, 2);

  insert into public.scontrini (
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
    motivo_rifiuto,
    verificato_at
  )
  values (
    p_cliente_id,
    bar_corrente_id,
    'TEST INTERNO - credito SQ simulato per verifica card richiesta utilizzo credito',
    current_date,
    current_time(0),
    'TEST-SQ-' || upper(left(gen_random_uuid()::text, 8)),
    importo_simulato,
    importo_simulato,
    importo_simulato,
    round(p_credito_sq::numeric, 2),
    'confermato',
    false,
    'TEST INTERNO - rimuovere con test_rimuovi_credito_sq',
    now()
  )
  returning id into nuovo_id;

  return nuovo_id;
end;
$$;

grant execute on function public.test_simula_credito_sq(uuid, numeric) to authenticated;

create or replace function public.test_rimuovi_credito_sq(
  p_cliente_id uuid default null
)
returns integer
language plpgsql
security definer
set search_path = public
as $$
declare
  righe_cancellate integer;
begin
  if not (public.e_admin() or public.e_salute_quotidiana()) then
    raise exception 'ruolo non autorizzato';
  end if;

  delete from public.scontrini s
  where s.numero_documento like 'TEST-SQ-%'
    and (p_cliente_id is null or s.cliente_id = p_cliente_id);

  get diagnostics righe_cancellate = row_count;
  return righe_cancellate;
end;
$$;

grant execute on function public.test_rimuovi_credito_sq(uuid) to authenticated;

notify pgrst, 'reload schema';
