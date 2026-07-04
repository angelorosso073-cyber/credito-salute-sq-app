-- Credito Salute SQ - Rivalidazione scontrini gia' presenti
-- Applica le regole automatiche agli scontrini gia' salvati in Supabase.
--
-- Nota:
-- Il database non contiene la confidenza OCR come campo separato.
-- Per gli scontrini gia' presenti usiamo quindi una regola prudente:
-- testo_ocr presente e abbastanza lungo.

with valutazione as (
  select
    s.id,
    array_remove(array[
      case when s.data_scontrino is null then 'data scontrino mancante' end,
      case when s.ora_scontrino is null then 'ora scontrino mancante' end,
      case when nullif(trim(coalesce(s.numero_documento, '')), '') is null then 'numero documento mancante' end,
      case when s.importo_dichiarato is null or s.importo_dichiarato <= 0 then 'importo non valido' end,
      case when s.importo_dichiarato > 30 then 'importo sopra soglia auto: 30 euro' end,
      case when s.data_scontrino > current_date then 'data scontrino futura' end,
      case when s.data_scontrino < current_date - interval '14 days' then 'scontrino piu'' vecchio di 14 giorni' end,
      case when nullif(trim(coalesce(s.testo_ocr, '')), '') is null then 'testo OCR assente' end,
      case when length(trim(coalesce(s.testo_ocr, ''))) < 30 then 'testo OCR troppo breve' end,
      case
        when lower(coalesce(s.testo_ocr, '')) similar to '%(scommess|lotto|superenalotto|gratta|vincita|ricarica|tabac|sigarette|pagamento bollett|servizi lis)%'
        then 'termine escluso rilevato'
      end,
      case
        when exists (
          select 1
          from public.scontrini d
          where d.id <> s.id
            and d.bar_id = s.bar_id
            and d.data_scontrino = s.data_scontrino
            and lower(coalesce(d.numero_documento, '')) = lower(coalesce(s.numero_documento, ''))
        )
        then 'possibile duplicato'
      end
    ], null) as problemi
  from public.scontrini s
  where s.stato in ('in_verifica', 'confermato')
)
update public.scontrini s
set
  stato = case
    when cardinality(v.problemi) = 0 then 'confermato'
    else 'in_verifica'
  end,
  importo_verificato = case
    when cardinality(v.problemi) = 0 then s.importo_dichiarato
    else null
  end,
  motivo_rifiuto = case
    when cardinality(v.problemi) = 0 then null
    else 'Controllo SQ richiesto: ' || array_to_string(v.problemi, '; ') || '.'
  end,
  updated_at = now()
from valutazione v
where s.id = v.id;
