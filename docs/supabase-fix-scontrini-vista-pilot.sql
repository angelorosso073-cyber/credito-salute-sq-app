-- Credito Salute SQ - Vista scontrini minima per prototipo
-- Serve per far leggere alla web app gli scontrini salvati su Supabase.
-- Nota: soluzione da pilot senza login completo.

drop view if exists public.scontrini_app_pilot;

create view public.scontrini_app_pilot
as
select
  s.id,
  s.cliente_id,
  s.bar_id,
  s.testo_ocr,
  s.data_scontrino,
  s.ora_scontrino,
  s.numero_documento,
  s.importo_dichiarato,
  s.importo_ocr,
  s.importo_verificato,
  s.credito_generato,
  s.stato,
  s.avviso_duplicato,
  s.motivo_rifiuto,
  s.created_at,
  s.updated_at
from public.scontrini s;

grant select on public.scontrini_app_pilot to anon, authenticated;
