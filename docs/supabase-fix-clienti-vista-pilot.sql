-- Credito Salute SQ - Vista clienti minima per prototipo
-- Serve per far ricaricare alla web app i clienti gia' iscritti.
-- Nota: e' una soluzione da pilot senza login completo.

drop view if exists public.clienti_app_pilot;

create view public.clienti_app_pilot
as
select
  id,
  codice_cliente,
  nome,
  cognome,
  telefono,
  citta,
  created_at
from public.clienti
where stato = 'attivo';

grant select on public.clienti_app_pilot to anon, authenticated;
