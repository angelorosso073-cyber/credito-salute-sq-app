-- Credito Salute SQ - Diagnosi e fix collegamento cliente test
--
-- Quando usarlo:
-- 1. Il login cliente funziona.
-- 2. La web app mostra ancora "Completa il tuo profilo".
-- 3. In Supabase esiste gia' una scheda cliente, per esempio "cliente test".
--
-- Cosa fa:
-- 1. Cerca l'utente Auth tramite email.
-- 2. Cerca il profilo cliente collegato all'utente Auth oppure alla stessa email.
-- 3. Cerca la scheda cliente tramite email, telefono oppure nome/cognome.
-- 4. Crea il profilo cliente se manca.
-- 5. Collega profili.auth_user_id all'utente Auth se manca.
-- 6. Collega o riallinea clienti.profilo_id al profilo corretto.
-- 7. Se non trova nessuna scheda cliente, puo' crearne una per il test.
--
-- IMPORTANTE:
-- Sostituisci qui sotto:
-- 1. l'email reale usata per il login "cliente test";
-- 2. se serve, telefono/nome/cognome presenti nella tabella clienti.
-- 3. se la ricerca automatica non trova il cliente, inserisci cliente_id_manuale
--    oppure codice_cliente_manuale dopo averlo recuperato dalla tabella clienti.
-- 4. lascia crea_cliente_se_manca = true solo per account di test.

begin;

with params as (
  select
    lower('angelo2017@outlook.it')::text as email_cliente,
    regexp_replace('', '\D', '', 'g')::text as telefono_cliente,
    lower('cliente')::text as nome_cliente,
    lower('test')::text as cognome_cliente,
    nullif('', '')::uuid as cliente_id_manuale,
    lower('')::text as codice_cliente_manuale,
    true::boolean as crea_cliente_se_manca
),
auth_cliente as (
  select u.id, lower(u.email) as email
  from auth.users u
  join params p on lower(u.email) = p.email_cliente
  limit 1
),
profilo_esistente as (
  select p.*
  from public.profili p
  left join auth_cliente a on true
  join params par on true
  where lower(p.ruolo) = 'cliente'
    and (
      p.auth_user_id = a.id
      or lower(coalesce(p.email, '')) = par.email_cliente
    )
  order by
    case when p.auth_user_id = (select id from auth_cliente) then 0 else 1 end,
    p.created_at desc
  limit 1
),
profilo_creato as (
  insert into public.profili (
    auth_user_id,
    ruolo,
    nome_completo,
    telefono,
    email,
    attivo
  )
  select
    a.id,
    'cliente',
    a.email,
    null,
    a.email,
    true
  from auth_cliente a
  where not exists (select 1 from profilo_esistente)
  returning *
),
profilo_finale as (
  select * from profilo_esistente
  union all
  select * from profilo_creato
  limit 1
),
cliente_esistente as (
  select c.*
  from public.clienti c
  join params p on true
  where c.stato = 'attivo'
    and (
      (p.cliente_id_manuale is not null and c.id = p.cliente_id_manuale)
      or (
        p.codice_cliente_manuale <> ''
        and lower(coalesce(c.codice_cliente, '')) = p.codice_cliente_manuale
      )
      or lower(coalesce(c.email, '')) = p.email_cliente
      or (
        p.telefono_cliente <> ''
        and regexp_replace(coalesce(c.telefono, ''), '\D', '', 'g') = p.telefono_cliente
      )
      or (
        p.nome_cliente <> ''
        and p.cognome_cliente <> ''
        and lower(coalesce(c.nome, '')) = p.nome_cliente
        and lower(coalesce(c.cognome, '')) = p.cognome_cliente
      )
    )
  order by
    case
      when p.cliente_id_manuale is not null and c.id = p.cliente_id_manuale then 0
      when p.codice_cliente_manuale <> '' and lower(coalesce(c.codice_cliente, '')) = p.codice_cliente_manuale then 1
      when lower(coalesce(c.email, '')) = p.email_cliente then 2
      when p.telefono_cliente <> '' and regexp_replace(coalesce(c.telefono, ''), '\D', '', 'g') = p.telefono_cliente then 3
      else 4
    end,
    c.created_at desc
  limit 1
),
cliente_creato as (
  insert into public.clienti (
    id,
    profilo_id,
    codice_cliente,
    nome,
    cognome,
    telefono,
    email,
    citta,
    consenso_programma,
    privacy_accettata_at,
    stato
  )
  select
    gen_random_uuid(),
    pf.id,
    'SQTEST' || to_char(now(), 'YYMMDDHH24MISS'),
    initcap(p.nome_cliente),
    initcap(p.cognome_cliente),
    coalesce(nullif(p.telefono_cliente, ''), '0000000000'),
    p.email_cliente,
    'Francofonte',
    true,
    now(),
    'attivo'
  from params p
  join profilo_finale pf on true
  where p.crea_cliente_se_manca = true
    and not exists (select 1 from cliente_esistente)
  returning *
),
cliente_finale as (
  select * from cliente_esistente
  union all
  select * from cliente_creato
  limit 1
),
fix_profilo as (
  update public.profili p
  set auth_user_id = a.id
  from auth_cliente a, profilo_finale pe
  where p.id = pe.id
    and p.auth_user_id is null
  returning p.id
),
fix_cliente as (
  update public.clienti c
  set profilo_id = pe.id
  from profilo_finale pe, cliente_finale ce
  where c.id = ce.id
    and (
      c.profilo_id is null
      or c.profilo_id <> pe.id
    )
  returning c.id
)
select
  (select email_cliente from params) as email_cercata,
  (select telefono_cliente from params) as telefono_cercato,
  (select cliente_id_manuale from params) as cliente_id_manuale_usato,
  (select codice_cliente_manuale from params) as codice_cliente_manuale_usato,
  (select id from auth_cliente) as auth_user_id_trovato,
  (select id from profilo_finale) as profilo_id_trovato,
  (select id from cliente_finale) as cliente_id_trovato,
  (select profilo_id from cliente_finale) as cliente_profilo_id_prima_del_fix,
  (select count(*) from profilo_creato) as profili_creati,
  (select count(*) from cliente_creato) as clienti_creati,
  (select count(*) from fix_profilo) as profili_collegati_auth,
  (select count(*) from fix_cliente) as clienti_collegati_profilo;

commit;

create or replace view public.clienti_app_pilot
with (security_invoker = true)
as
select
  c.id,
  c.codice_cliente,
  c.nome,
  c.cognome,
  c.telefono,
  c.citta,
  c.created_at,
  c.email,
  c.profilo_id
from public.clienti c
where c.stato = 'attivo';

grant select on public.clienti_app_pilot to authenticated;
revoke all on public.clienti_app_pilot from anon;

notify pgrst, 'reload schema';

-- Dopo l'esecuzione:
-- 1. Ricarica la web app con Ctrl + F5.
-- 2. Fai logout.
-- 3. Fai login di nuovo con il cliente test.
-- 4. Se compare ancora "Completa il tuo profilo", esegui solo questa query di controllo:
--
-- Per trovare il cliente da collegare manualmente, usa prima questa query:
--
-- select
--   id,
--   codice_cliente,
--   nome,
--   cognome,
--   email,
--   telefono,
--   stato,
--   profilo_id,
--   created_at
-- from public.clienti
-- order by created_at desc
-- limit 30;
--
-- select
--   c.id as cliente_id,
--   c.nome,
--   c.cognome,
--   c.email,
--   c.profilo_id,
--   p.id as profilo_id,
--   p.email as profilo_email,
--   p.auth_user_id,
--   u.email as auth_email
-- from public.clienti c
-- left join public.profili p on p.id = c.profilo_id
-- left join auth.users u on u.id = p.auth_user_id
-- where lower(coalesce(c.email, '')) = lower('angelo2017@outlook.it');
