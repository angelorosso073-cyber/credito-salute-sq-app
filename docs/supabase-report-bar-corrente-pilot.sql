-- Credito Salute SQ - Report aggregato titolare bar
-- Eseguire in Supabase SQL Editor.
--
-- Obiettivo:
-- 1. il titolare bar vede solo dati aggregati del proprio bar;
-- 2. non vede utilizzi credito, beneficiari, prestazioni o note sanitarie;
-- 3. il frontend chiama solo questa RPC per il ruolo bar.

create or replace function public.report_bar_corrente_pilot()
returns jsonb
language plpgsql
security definer
set search_path = public
as $$
declare
  profilo_corrente record;
  bar_corrente record;
  metriche jsonb;
  scontrini_recenti jsonb;
begin
  select p.id, p.ruolo
  into profilo_corrente
  from public.profili p
  where p.auth_user_id = auth.uid()
    and p.attivo = true
    and lower(p.ruolo) in ('titolare_bar', 'bar')
  limit 1;

  if profilo_corrente.id is null then
    raise exception 'profilo titolare bar non trovato';
  end if;

  select b.id, b.nome, b.citta
  into bar_corrente
  from public.operatori_bar ob
  join public.bar b on b.id = ob.bar_id
  where ob.profilo_id = profilo_corrente.id
    and ob.attivo = true
    and b.attivo = true
  order by b.created_at desc
  limit 1;

  if bar_corrente.id is null then
    raise exception 'titolare bar non collegato a un bar attivo';
  end if;

  select jsonb_build_object(
    'customers', count(distinct s.cliente_id),
    'receipts', count(s.id),
    'pending', count(*) filter (where s.stato = 'in_verifica'),
    'confirmed', count(*) filter (where s.stato = 'confermato'),
    'rejected', count(*) filter (where s.stato = 'rifiutato'),
    'confirmed_amount', coalesce(sum(s.importo_dichiarato) filter (where s.stato = 'confermato'), 0),
    'generated_credit', coalesce(sum(s.credito_generato) filter (where s.stato = 'confermato'), 0),
    'anomalies', count(*) filter (
      where s.avviso_duplicato = true
         or s.stato = 'rifiutato'
         or nullif(trim(coalesce(s.motivo_rifiuto, '')), '') is not null
    )
  )
  into metriche
  from public.scontrini s
  where s.bar_id = bar_corrente.id;

  select coalesce(jsonb_agg(
    jsonb_build_object(
      'id', recente.id,
      'codice_cliente', recente.codice_cliente,
      'data_scontrino', recente.data_scontrino,
      'ora_scontrino', recente.ora_scontrino,
      'numero_documento', recente.numero_documento,
      'importo_dichiarato', recente.importo_dichiarato,
      'credito_generato', recente.credito_generato,
      'stato', recente.stato,
      'avviso_duplicato', recente.avviso_duplicato
    )
    order by recente.created_at desc
  ), '[]'::jsonb)
  into scontrini_recenti
  from (
    select
      s.id,
      c.codice_cliente,
      s.data_scontrino,
      s.ora_scontrino,
      s.numero_documento,
      s.importo_dichiarato,
      s.credito_generato,
      s.stato,
      s.avviso_duplicato,
      s.created_at
    from public.scontrini s
    left join public.clienti c on c.id = s.cliente_id
    where s.bar_id = bar_corrente.id
    order by s.created_at desc
    limit 15
  ) recente;

  return jsonb_build_object(
    'bar_id', bar_corrente.id,
    'bar_name', bar_corrente.nome,
    'bar_city', bar_corrente.citta,
    'updated_at', now(),
    'metrics', metriche,
    'recent_receipts', scontrini_recenti
  );
end;
$$;

grant execute on function public.report_bar_corrente_pilot() to authenticated;

notify pgrst, 'reload schema';
