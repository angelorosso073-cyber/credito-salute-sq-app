-- Credito Salute SQ - collega cliente corrente al profilo Supabase
-- Eseguire in Supabase SQL Editor se un cliente registrato fa login
-- ma la web app mostra "Nessun cliente registrato".

create or replace function public.collega_cliente_corrente_pilot()
returns uuid
language plpgsql
security definer
set search_path = public
as $$
declare
  profilo_corrente public.profili%rowtype;
  cliente_corrente_id uuid;
  email_corrente text;
  telefono_corrente text;
begin
  select *
  into profilo_corrente
  from public.profili
  where auth_user_id = auth.uid()
    and lower(ruolo) = 'cliente'
  limit 1;

  if profilo_corrente.id is null then
    return null;
  end if;

  select c.id
  into cliente_corrente_id
  from public.clienti c
  where c.profilo_id = profilo_corrente.id
    and c.stato = 'attivo'
  order by c.created_at desc
  limit 1;

  if cliente_corrente_id is not null then
    return cliente_corrente_id;
  end if;

  email_corrente := lower(coalesce(profilo_corrente.email, auth.jwt() ->> 'email', ''));
  telefono_corrente := regexp_replace(coalesce(profilo_corrente.telefono, ''), '\D', '', 'g');

  select c.id
  into cliente_corrente_id
  from public.clienti c
  where c.profilo_id is null
    and c.stato = 'attivo'
    and (
      (email_corrente <> '' and lower(coalesce(c.email, '')) = email_corrente)
      or (
        telefono_corrente <> ''
        and regexp_replace(coalesce(c.telefono, ''), '\D', '', 'g') = telefono_corrente
      )
    )
  order by
    case when email_corrente <> '' and lower(coalesce(c.email, '')) = email_corrente then 0 else 1 end,
    c.created_at desc
  limit 1;

  if cliente_corrente_id is null then
    return null;
  end if;

  update public.clienti
  set profilo_id = profilo_corrente.id
  where id = cliente_corrente_id
    and profilo_id is null;

  return cliente_corrente_id;
end;
$$;

grant execute on function public.collega_cliente_corrente_pilot() to authenticated;

notify pgrst, 'reload schema';
