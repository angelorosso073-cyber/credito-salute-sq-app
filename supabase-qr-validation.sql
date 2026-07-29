-- supabase-qr-validation.sql
-- v52: sistema QR anti-imbroglio per scontrini
-- Flusso: cliente carica scontrino → QR generato → barista scansiona entro 15 min → confermato

ALTER TABLE scontrini
  ADD COLUMN IF NOT EXISTS qr_token UUID,
  ADD COLUMN IF NOT EXISTS qr_generated_at TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS qr_scanned_at TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS qr_scanned_by TEXT;

CREATE INDEX IF NOT EXISTS idx_scontrini_qr_token
  ON scontrini (qr_token)
  WHERE qr_token IS NOT NULL;

-- Genera token QR per uno scontrino appena caricato
CREATE OR REPLACE FUNCTION genera_qr_scontrino_pilot(p_scontrino_id UUID)
RETURNS UUID
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
  v_token UUID;
BEGIN
  v_token := gen_random_uuid();
  UPDATE scontrini
  SET qr_token        = v_token,
      qr_generated_at = NOW()
  WHERE id = p_scontrino_id;
  IF NOT FOUND THEN
    RAISE EXCEPTION 'scontrino non trovato: %', p_scontrino_id;
  END IF;
  RETURN v_token;
END;
$$;

-- Conferma scansione QR da parte del barista
-- Verifica: token esiste, non scaduto (15 min), non gia' usato
-- Se scontrino era in_verifica → confermato; se gia' confermato → audit trail
CREATE OR REPLACE FUNCTION conferma_qr_scontrino_pilot(
  p_token    UUID,
  p_operatore TEXT DEFAULT NULL
)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
  v_rec RECORD;
BEGIN
  SELECT
    s.id,
    s.stato,
    s.qr_generated_at,
    s.qr_scanned_at,
    s.importo_dichiarato,
    s.credito_generato,
    c.codice_cliente
  INTO v_rec
  FROM scontrini s
  LEFT JOIN clienti c ON c.id = s.cliente_id
  WHERE s.qr_token = p_token;

  IF NOT FOUND THEN
    RETURN jsonb_build_object('ok', false, 'errore', 'token_non_trovato');
  END IF;

  IF v_rec.qr_scanned_at IS NOT NULL THEN
    RETURN jsonb_build_object('ok', false, 'errore', 'gia_scansionato');
  END IF;

  IF v_rec.qr_generated_at IS NULL
     OR NOW() > v_rec.qr_generated_at + INTERVAL '15 minutes' THEN
    RETURN jsonb_build_object('ok', false, 'errore', 'scaduto');
  END IF;

  UPDATE scontrini
  SET
    qr_scanned_at = NOW(),
    qr_scanned_by = p_operatore,
    stato         = CASE WHEN stato = 'in_verifica' THEN 'confermato' ELSE stato END
  WHERE id = v_rec.id;

  RETURN jsonb_build_object(
    'ok',             true,
    'scontrino_id',   v_rec.id,
    'codice_cliente', v_rec.codice_cliente,
    'importo',        v_rec.importo_dichiarato,
    'credito',        v_rec.credito_generato
  );
END;
$$;
