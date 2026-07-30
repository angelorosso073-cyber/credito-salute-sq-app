-- supabase-lista-silenziosi.sql
-- Lista dei Silenziosi: fondo condiviso alimentato da donazioni anonime,
-- ripartito dinamicamente tra beneficiari ammessi tramite questionario bisogni.

-- 1. Nuovo campo su utilizzi_credito per distinguere donazioni da prestazioni normali.
--    Default 'prestazione' copre tutte le righe esistenti automaticamente.
ALTER TABLE utilizzi_credito
  ADD COLUMN IF NOT EXISTS tipo_movimento TEXT NOT NULL DEFAULT 'prestazione';

ALTER TABLE utilizzi_credito
  ADD CONSTRAINT utilizzi_credito_tipo_movimento_check
  CHECK (tipo_movimento IN ('prestazione', 'donazione_lista_silenziosi'));

-- 2. Valutazioni bisogno (ammissione beneficiari)
CREATE TABLE IF NOT EXISTS valutazioni_bisogno_silenziosi (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  cliente_id UUID NOT NULL REFERENCES clienti(id),
  punteggio INTEGER NOT NULL CHECK (punteggio BETWEEN 0 AND 100),
  risposte JSONB NOT NULL,
  consenso_valutazione BOOLEAN NOT NULL DEFAULT false,
  compilato_da TEXT NOT NULL CHECK (compilato_da IN ('paziente', 'familiare')),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_valutazioni_bisogno_cliente
  ON valutazioni_bisogno_silenziosi (cliente_id, created_at DESC);

-- 3. Donazioni al fondo
CREATE TABLE IF NOT EXISTS fondo_silenziosi_donazioni (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  cliente_id UUID NOT NULL REFERENCES clienti(id),
  importo NUMERIC(10,2) NOT NULL CHECK (importo > 0),
  utilizzo_credito_id UUID REFERENCES utilizzi_credito(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 4. Erogazioni dal fondo ai beneficiari ammessi
CREATE TABLE IF NOT EXISTS fondo_silenziosi_erogazioni (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  beneficiario_cliente_id UUID NOT NULL REFERENCES clienti(id),
  tipo_prestazione TEXT NOT NULL,
  prezzo_prestazione NUMERIC(10,2) NOT NULL CHECK (prezzo_prestazione >= 0),
  importo_erogato NUMERIC(10,2) NOT NULL CHECK (importo_erogato > 0),
  differenza_da_pagare NUMERIC(10,2) NOT NULL DEFAULT 0,
  note TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 5. Saldo fondo — ricalcolato live ad ogni lettura
CREATE OR REPLACE VIEW fondo_silenziosi_saldo_v AS
SELECT
  COALESCE((SELECT SUM(importo) FROM fondo_silenziosi_donazioni), 0)
  - COALESCE((SELECT SUM(importo_erogato) FROM fondo_silenziosi_erogazioni), 0)
  AS saldo_disponibile;

-- 6. Beneficiari ammessi + quota dinamica proporzionale al punteggio.
--    Solo l'ultima valutazione per cliente conta.
CREATE OR REPLACE VIEW fondo_silenziosi_beneficiari_v AS
WITH ultima_valutazione AS (
  SELECT DISTINCT ON (cliente_id) cliente_id, punteggio, created_at
  FROM valutazioni_bisogno_silenziosi
  WHERE consenso_valutazione = true
  ORDER BY cliente_id, created_at DESC
),
totale_punteggio AS (
  SELECT COALESCE(SUM(punteggio), 0) AS somma FROM ultima_valutazione
)
SELECT
  uv.cliente_id,
  uv.punteggio,
  uv.created_at AS valutato_il,
  CASE WHEN t.somma > 0
    THEN ROUND((SELECT saldo_disponibile FROM fondo_silenziosi_saldo_v) * uv.punteggio / t.somma, 2)
    ELSE 0
  END AS quota_disponibile
FROM ultima_valutazione uv, totale_punteggio t;

-- 7. RPC: invio questionario bisogni (ammissione/aggiornamento beneficiario)
CREATE OR REPLACE FUNCTION invia_valutazione_bisogno_pilot(
  p_cliente_id UUID,
  p_punteggio INTEGER,
  p_risposte JSONB,
  p_consenso BOOLEAN,
  p_compilato_da TEXT
)
RETURNS UUID
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
  v_id UUID;
BEGIN
  IF NOT p_consenso THEN
    RAISE EXCEPTION 'consenso_valutazione_richiesto';
  END IF;
  IF p_punteggio < 0 OR p_punteggio > 100 THEN
    RAISE EXCEPTION 'punteggio_fuori_intervallo';
  END IF;

  INSERT INTO valutazioni_bisogno_silenziosi
    (cliente_id, punteggio, risposte, consenso_valutazione, compilato_da)
  VALUES
    (p_cliente_id, p_punteggio, p_risposte, p_consenso, p_compilato_da)
  RETURNING id INTO v_id;

  RETURN v_id;
END;
$$;

-- 8. RPC: donazione al fondo (riduce saldo personale del donante)
CREATE OR REPLACE FUNCTION dona_a_lista_silenziosi_pilot(
  p_cliente_id UUID,
  p_importo NUMERIC
)
RETURNS UUID
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
  v_saldo_disponibile NUMERIC;
  v_utilizzo_id UUID;
  v_donazione_id UUID;
BEGIN
  IF p_importo IS NULL OR p_importo <= 0 THEN
    RAISE EXCEPTION 'importo_non_valido';
  END IF;

  SELECT saldo_disponibile INTO v_saldo_disponibile
  FROM saldi_clienti_app_pilot
  WHERE cliente_id = p_cliente_id;

  IF v_saldo_disponibile IS NULL OR v_saldo_disponibile < p_importo THEN
    RAISE EXCEPTION 'saldo_insufficiente';
  END IF;

  v_utilizzo_id := gen_random_uuid();
  INSERT INTO utilizzi_credito
    (id, cliente_id, tipo_prestazione, prezzo_prestazione, credito_usato,
     importo_pagato, beneficiario, note, conferma_sq, conferma_cliente,
     stato_pagamento, incassato_at, tipo_movimento)
  VALUES
    (v_utilizzo_id, p_cliente_id, 'Donazione Lista dei Silenziosi', 0, p_importo,
     0, 'donazione', 'Donazione anonima al fondo Lista dei Silenziosi', true, true,
     'incassato', NOW(), 'donazione_lista_silenziosi');

  INSERT INTO fondo_silenziosi_donazioni (cliente_id, importo, utilizzo_credito_id)
  VALUES (p_cliente_id, p_importo, v_utilizzo_id)
  RETURNING id INTO v_donazione_id;

  RETURN v_donazione_id;
END;
$$;

-- 9. RPC: erogazione di una prestazione a un beneficiario ammesso
CREATE OR REPLACE FUNCTION eroga_da_lista_silenziosi_pilot(
  p_beneficiario_cliente_id UUID,
  p_tipo_prestazione TEXT,
  p_prezzo_prestazione NUMERIC,
  p_importo_pagato_extra NUMERIC DEFAULT 0
)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
  v_quota NUMERIC;
  v_importo_erogato NUMERIC;
  v_differenza NUMERIC;
  v_id UUID;
BEGIN
  SELECT quota_disponibile INTO v_quota
  FROM fondo_silenziosi_beneficiari_v
  WHERE cliente_id = p_beneficiario_cliente_id;

  IF v_quota IS NULL THEN
    RETURN jsonb_build_object('ok', false, 'errore', 'beneficiario_non_ammesso');
  END IF;

  v_importo_erogato := LEAST(v_quota, p_prezzo_prestazione);
  IF v_importo_erogato <= 0 THEN
    RETURN jsonb_build_object('ok', false, 'errore', 'fondo_esaurito');
  END IF;

  v_differenza := GREATEST(p_prezzo_prestazione - v_importo_erogato, 0) + COALESCE(p_importo_pagato_extra, 0);

  INSERT INTO fondo_silenziosi_erogazioni
    (beneficiario_cliente_id, tipo_prestazione, prezzo_prestazione, importo_erogato, differenza_da_pagare)
  VALUES
    (p_beneficiario_cliente_id, p_tipo_prestazione, p_prezzo_prestazione, v_importo_erogato, v_differenza)
  RETURNING id INTO v_id;

  RETURN jsonb_build_object(
    'ok', true,
    'id', v_id,
    'importo_erogato', v_importo_erogato,
    'differenza_da_pagare', v_differenza
  );
END;
$$;
