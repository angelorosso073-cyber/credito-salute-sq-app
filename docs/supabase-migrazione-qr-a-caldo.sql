-- docs/supabase-migrazione-qr-a-caldo.sql
-- Migrazione a caldo, una tantum: al momento del deploy del Task 9, alcuni scontrini
-- possono essere 'in_verifica' con un QR generato (vecchio meccanismo) mai scansionato
-- dal bar. Con il vecchio meccanismo disattivato, quel QR non verra' mai piu' scansionato:
-- diamo a questi scontrini lo stesso percorso di un caricamento "senza codice banco" nel
-- nuovo sistema — restano in_verifica, sospesi, con una finestra per andare al bar e
-- attivarli col nuovo codice.
--
-- ESEGUI PRIMA LA SELECT (anteprima), controlla il numero di righe, poi la UPDATE.

-- Anteprima: quanti scontrini sono in transito col vecchio QR non scansionato.
SELECT id, cliente_id, data_scontrino, importo_dichiarato, qr_generated_at
FROM public.scontrini
WHERE stato = 'in_verifica'
  AND qr_generated_at IS NOT NULL
  AND qr_scanned_at IS NULL;

-- Se il numero di righe ti sembra ragionevole (dovrebbero essere pochissime, il pilot
-- ha 20 clienti), esegui la UPDATE:
UPDATE public.scontrini
SET motivo_sospensione = 'codice_banco_mancante',
    sospeso_scaduto_il = NOW() + (
      COALESCE(
        (SELECT sospensione_giorni FROM public.limiti_bar WHERE bar_id = scontrini.bar_id),
        12
      ) || ' days'
    )::INTERVAL
WHERE stato = 'in_verifica'
  AND qr_generated_at IS NOT NULL
  AND qr_scanned_at IS NULL;

-- Verifica: le righe appena aggiornate devono ora comparire nell'area "credito sospeso"
-- del cliente corrispondente nell'app, con una scadenza a partire da oggi.
SELECT id, cliente_id, motivo_sospensione, sospeso_scaduto_il
FROM public.scontrini
WHERE motivo_sospensione = 'codice_banco_mancante'
  AND qr_generated_at IS NOT NULL;
