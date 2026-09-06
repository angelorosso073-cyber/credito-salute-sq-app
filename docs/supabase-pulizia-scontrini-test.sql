-- Pulizia scontrini di test (sessioni di debug 25/08 - 02/09/2026)
-- Cliente id: b6b5556c-81b1-42b5-9aed-e31b782a72af, importo 1,20 euro ripetuto
-- su piu' giorni -- confermato dati di test di Angelo, pilot non ancora avviato
-- con clienti reali (vedi memoria "Stato pilot e GDPR" 17/08/2026).

-- STEP 1: verifica prima di cancellare. Controlla che nome/cognome sotto
-- siano davvero il cliente di test e non un cliente vero.
select
  s.id,
  s.data_scontrino,
  s.numero_documento,
  s.importo_dichiarato,
  s.stato,
  s.created_at,
  c.nome,
  c.cognome,
  c.codice_cliente
from public.scontrini s
join public.clienti c on c.id = s.cliente_id
where s.cliente_id = 'b6b5556c-81b1-42b5-9aed-e31b782a72af'
order by s.created_at;

-- STEP 2: solo dopo aver controllato lo STEP 1, esegui la cancellazione.
-- on delete cascade su verifiche_scontrini si occupa delle righe collegate.
delete from public.scontrini
where cliente_id = 'b6b5556c-81b1-42b5-9aed-e31b782a72af';

-- Nota: le foto su Storage (bucket scontrini) collegate a questi id NON
-- vengono cancellate da questo script -- restano orfane (difetto noto,
-- non bloccante). Da pulire a mano nel pannello Storage se vuoi anche
-- liberare spazio: percorso {cliente_id}/{scontrino_id}.estensione.

-- STEP 3 (opzionale): se il cliente stesso e' solo un record di test e non
-- deve restare visibile nelle liste clienti, decommenta ed esegui.
-- Verifica prima che non abbia utilizzi_credito o richieste collegate.
-- delete from public.clienti where id = 'b6b5556c-81b1-42b5-9aed-e31b782a72af';
