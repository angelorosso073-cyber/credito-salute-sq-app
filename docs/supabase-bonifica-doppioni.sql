-- docs/supabase-bonifica-doppioni.sql
-- Precondizione per la nuova chiave anti-duplicato senza importo.
--
-- Perche' serve: fino a oggi la chiave includeva l'importo, quindi due letture
-- diverse dello stesso totale (1,20 e 1.28 sullo stesso scontrino) risultavano
-- due scontrini distinti. Nel database ci sono righe cosi'. Il nuovo indice
-- unico le rifiuterebbe e non verrebbe creato.
--
-- LANCIARE PRIMA SOLO LA PARTE 1 E LEGGERE IL RISULTATO.
-- La parte 2 modifica dati: eseguirla solo dopo aver visto cosa tocca.

-- ---------------------------------------------------------------------------
-- PARTE 1 - Anteprima. Non modifica niente.
-- ---------------------------------------------------------------------------
SELECT
  s.matricola_rt,
  s.numero_documento,
  s.data_scontrino,
  count(*) AS righe_non_rifiutate,
  array_agg(s.importo_dichiarato ORDER BY s.created_at) AS importi,
  array_agg(s.stato ORDER BY s.created_at) AS stati,
  array_agg(s.created_at ORDER BY s.created_at) AS caricati_il
FROM public.scontrini s
WHERE s.matricola_rt IS NOT NULL
  AND s.stato <> 'rifiutato'
GROUP BY s.matricola_rt, s.numero_documento, s.data_scontrino
HAVING count(*) > 1
ORDER BY s.data_scontrino DESC;

-- ---------------------------------------------------------------------------
-- PARTE 2 - Bonifica. Di ogni gruppo tiene una riga sola e rifiuta le altre.
-- Eseguire solo dopo aver letto l'anteprima.
--
-- Quale riga viene tenuta: prima le confermate, poi a parita' la piu' recente.
-- L'ordine conta. Tenere semplicemente la piu' recente rischierebbe, in un
-- gruppo dove la riga vecchia e' gia' confermata e la nuova e' ancora da
-- verificare, di rifiutare un credito gia' accreditato al cliente: il danno
-- peggiore che questa bonifica possa fare.
-- ---------------------------------------------------------------------------
WITH ordinati AS (
  SELECT
    s.id,
    row_number() OVER (
      PARTITION BY s.matricola_rt, s.numero_documento, s.data_scontrino
      ORDER BY (s.stato = 'confermato') DESC, s.created_at DESC
    ) AS posizione
  FROM public.scontrini s
  WHERE s.matricola_rt IS NOT NULL
    AND s.stato <> 'rifiutato'
)
UPDATE public.scontrini s
SET stato = 'rifiutato',
    motivo_rifiuto = 'Doppione dello stesso scontrino: stesso registratore, stesso numero documento e stessa data. Rifiutato durante la bonifica del 02/09/2026.'
FROM ordinati o
WHERE s.id = o.id
  AND o.posizione > 1;

-- ---------------------------------------------------------------------------
-- PARTE 3 - Controllo. Deve restituire zero righe.
-- ---------------------------------------------------------------------------
SELECT
  s.matricola_rt, s.numero_documento, s.data_scontrino, count(*)
FROM public.scontrini s
WHERE s.matricola_rt IS NOT NULL
  AND s.stato <> 'rifiutato'
GROUP BY s.matricola_rt, s.numero_documento, s.data_scontrino
HAVING count(*) > 1;
