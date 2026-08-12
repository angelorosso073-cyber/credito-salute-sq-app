# Lista dei Silenziosi Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Permettere a un cliente di donare (in forma anonima) il proprio credito SQ a un fondo condiviso; permettere a un paziente/familiare di richiedere l'ammissione al fondo tramite un questionario di bisogni pratici; ripartire automaticamente e dinamicamente il fondo disponibile tra i beneficiari ammessi, in proporzione al loro punteggio di bisogno, senza mai toccare retroattivamente credito già erogato.

**Architecture:** Nuove tabelle Postgres (`valutazioni_bisogno_silenziosi`, `fondo_silenziosi_donazioni`, `fondo_silenziosi_erogazioni`) e due viste calcolate live (`fondo_silenziosi_saldo_v`, `fondo_silenziosi_beneficiari_v`). La donazione riusa il meccanismo esistente di `utilizzi_credito` (aggiungendo una riga con un nuovo campo `tipo_movimento`) così il saldo personale del donante si riduce automaticamente tramite la vista `saldi_clienti_app_pilot` già in uso, senza modificarla. L'erogazione ai beneficiari NON tocca `utilizzi_credito` (per non alterare i saldi personali esistenti) — vive in una tabella dedicata, riportata solo nel nuovo pannello "Lista dei Silenziosi".

**Tech Stack:** Postgres/plpgsql (Supabase, pattern `SECURITY DEFINER` coerente con `supabase-qr-validation.sql`), vanilla JS (`app.js`), HTML statico, CSS.

## Global Constraints

- Stack: vanilla JS senza build step, nessun framework di test (`package.json` assente). Verifica la logica di puro calcolo con script Node standalone prima di fidarti della vista SQL; per il resto, verifica manuale in browser + query dirette su Supabase.
- Non rompere nulla del pilot in corso (v52 QR, v53 Certificato di Cura se già applicato) — solo addizioni. Nessuna modifica alla vista `saldi_clienti_app_pilot` esistente, a `registra_utilizzo_credito_pilot`, o a `utilizzi_credito_app_pilot`.
- Ammissione automatica: l'invio del questionario con consenso valido AMMETTE automaticamente il beneficiario — nessuna approvazione manuale di Angelo prevista in questo piano (scelta esplicita del committente). Rischio residuo: punteggio auto-dichiarato, quindi soggetto a possibile uso improprio — non mitigato in questo piano, da monitorare manualmente da Angelo nel pannello di riepilogo (Task 5).
- Il punteggio di bisogno e le risposte del questionario sono dati sensibili: leggibili SOLO dal ruolo `salute_quotidiana` lato RLS/RPC. Il form richiede un consenso esplicito e separato, non riutilizza `contactConsent`/`rulesConsent` esistenti.
- Il tetto di 50€ SQ per cliente NON si applica ai beneficiari della Lista dei Silenziosi (per decisione esplicita del committente) — si applica invece normalmente al donante quando dona (non può donare più del proprio saldo disponibile).
- Il ricalcolo delle quote è sempre "live" (nessun campo salvato da tenere sincronizzato): ogni lettura della vista `fondo_silenziosi_beneficiari_v` ricalcola dal saldo attuale. Il credito già erogato (tabella `fondo_silenziosi_erogazioni`) non viene mai sottratto due volte né restituito.
- Naming RPC coerente col resto del progetto: verbo_oggetto_pilot.
- Bump `APP_VERSION` e query-string di cache-busting nell'ultimo task, come da convenzione già in uso (v52→v53 se questo piano è il primo eseguito dopo il pilot attuale; adatta il numero se il piano "Certificato di Cura" è stato eseguito prima).

---

## File Structure

- **Create `supabase-lista-silenziosi.sql`** — schema (3 tabelle), 2 viste, 3 RPC. Angelo lo applica manualmente su Supabase (stesso flusso già seguito per `supabase-qr-validation.sql`).
- **Modify `index.html`**
  - Tab `cliente` (sezione "Situazione cliente", dopo `creditRequestForm`): nuovo blocco donazione + nuovo `<details>` questionario bisogni.
  - Tab `salute` (dopo il panel "Registra prestazione", prima della chiusura di `<section class="tab-panel" id="salute">`): nuovo panel "Lista dei Silenziosi".
- **Modify `app.js`**
  - Nuovi `el` refs, nuove funzioni di caricamento/rendering, wiring form.
- **Modify `styles.css`**
  - Stile minimo per la nuova lista beneficiari (riuso `.mini-list`/`.metric-grid` esistenti dove possibile).

---

### Task 1: Schema SQL — tabelle, viste, RPC

**Files:**
- Create: `supabase-lista-silenziosi.sql`

**Interfaces:**
- Produce: tabelle `valutazioni_bisogno_silenziosi`, `fondo_silenziosi_donazioni`, `fondo_silenziosi_erogazioni`; viste `fondo_silenziosi_saldo_v`, `fondo_silenziosi_beneficiari_v`; RPC `invia_valutazione_bisogno_pilot`, `dona_a_lista_silenziosi_pilot`, `eroga_da_lista_silenziosi_pilot`. Usate da Task 3, 4, 5.

- [ ] **Step 1: Scrivere il file SQL completo**

```sql
-- supabase-lista-silenziosi.sql
-- Lista dei Silenziosi: fondo condiviso alimentato da donazioni anonime,
-- ripartito dinamicamente tra beneficiari ammessi tramite questionario bisogni.

-- 1. Nuovo campo su utilizzi_credito per distinguere le donazioni al fondo
--    dalle prestazioni normali. Default 'prestazione' copre tutte le righe
--    esistenti automaticamente: nessuna riga storica viene toccata.
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
--    Solo l'ultima valutazione per cliente conta (DISTINCT ON ... ORDER BY created_at DESC).
--    Un cliente con l'ultima valutazione a consenso_valutazione=false esce dalla lista
--    (il credito gia' erogato in passato resta comunque sottratto per sempre dal saldo totale).
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

-- 8. RPC: donazione al fondo (riduce il saldo personale del donante
--    tramite la vista saldi_clienti_app_pilot gia' esistente, che aggrega
--    tutte le righe di utilizzi_credito senza filtrare per tipo_movimento)
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

-- 9. RPC: erogazione di una prestazione a un beneficiario ammesso,
--    limitata alla quota attualmente disponibile (mai oltre).
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
```

- [ ] **Step 2: Angelo applica il file su Supabase**

Angelo incolla il contenuto di `supabase-lista-silenziosi.sql` nell'SQL Editor del dashboard Supabase e lo esegue (stesso flusso già seguito per `supabase-qr-validation.sql` — vedi task pendente equivalente nella memoria di progetto).

- [ ] **Step 3: Verifica manuale su Supabase**

Dopo l'esecuzione, lancia queste query di controllo nell'SQL Editor:
```sql
SELECT * FROM fondo_silenziosi_saldo_v;
```
Atteso: una riga, `saldo_disponibile = 0.00` (nessuna donazione ancora presente).
```sql
SELECT * FROM fondo_silenziosi_beneficiari_v;
```
Atteso: zero righe (nessun beneficiario ammesso ancora).

- [ ] **Step 4: Commit**

```bash
git add supabase-lista-silenziosi.sql
git commit -m "lista-silenziosi: schema, viste e RPC fondo condiviso"
```

---

### Task 2: Verifica standalone della formula di ripartizione

**Files:**
- Create (temporaneo, non committato): `$CLAUDE_JOB_DIR/tmp/test-quote-silenziosi.js`

**Interfaces:**
- Nessuna — task di sola verifica logica, mirror JS della formula SQL del Task 1 Step 1 (vista `fondo_silenziosi_beneficiari_v`), per validarla prima di fidarsi ciecamente della vista in produzione.

- [ ] **Step 1: Scrivere lo script di verifica**

```javascript
function calcolaQuote(saldoDisponibile, beneficiari) {
  // beneficiari: [{ clienteId, punteggio }]
  const somma = beneficiari.reduce((acc, b) => acc + b.punteggio, 0);
  if (somma <= 0) return beneficiari.map((b) => ({ ...b, quota: 0 }));
  return beneficiari.map((b) => ({
    ...b,
    quota: Math.round((saldoDisponibile * b.punteggio / somma) * 100) / 100
  }));
}

// Caso 1: due beneficiari, punteggi diversi, fondo 100
let r = calcolaQuote(100, [{ clienteId: "A", punteggio: 60 }, { clienteId: "B", punteggio: 40 }]);
console.assert(r[0].quota === 60, `FAIL caso1 A: atteso 60, ottenuto ${r[0].quota}`);
console.assert(r[1].quota === 40, `FAIL caso1 B: atteso 40, ottenuto ${r[1].quota}`);

// Caso 2: nessun beneficiario ammesso
r = calcolaQuote(100, []);
console.assert(r.length === 0, "FAIL caso2: lista vuota deve restare vuota");

// Caso 3: fondo a zero, beneficiari presenti
r = calcolaQuote(0, [{ clienteId: "A", punteggio: 60 }, { clienteId: "B", punteggio: 40 }]);
console.assert(r[0].quota === 0 && r[1].quota === 0, "FAIL caso3: fondo a zero deve dare quote a zero");

// Caso 4: nuovo beneficiario entra, quote di chi era gia' ammesso si riducono proporzionalmente
r = calcolaQuote(100, [{ clienteId: "A", punteggio: 60 }, { clienteId: "B", punteggio: 40 }]);
const soloA = calcolaQuote(100, [{ clienteId: "A", punteggio: 60 }]);
console.assert(soloA[0].quota === 100, `FAIL caso4a: solo A deve avere tutto il fondo, ottenuto ${soloA[0].quota}`);
console.assert(r[0].quota < soloA[0].quota, "FAIL caso4b: quota di A deve scendere quando entra B");

// Caso 5: il fondo residuo dopo un'erogazione non torna mai a un beneficiario diverso oltre il residuo
const saldoDopoErogazione = 100 - 60; // A ha gia' ricevuto 60
r = calcolaQuote(saldoDopoErogazione, [{ clienteId: "A", punteggio: 60 }, { clienteId: "B", punteggio: 40 }]);
const totaleRipartito = r.reduce((acc, b) => acc + b.quota, 0);
console.assert(totaleRipartito <= saldoDopoErogazione, `FAIL caso5: totale ripartito (${totaleRipartito}) non puo' superare il saldo residuo (${saldoDopoErogazione})`);

console.log("OK: tutti gli assert passati");
```

Esegui: `node "$CLAUDE_JOB_DIR/tmp/test-quote-silenziosi.js"`
Atteso: `OK: tutti gli assert passati`, nessun `FAIL`.

- [ ] **Step 2: Confronto con la vista SQL reale**

Su Supabase (dopo Task 1), inserisci dati di prova via SQL Editor:
```sql
INSERT INTO valutazioni_bisogno_silenziosi (cliente_id, punteggio, risposte, consenso_valutazione, compilato_da)
SELECT id, 60, '{}'::jsonb, true, 'paziente' FROM clienti LIMIT 1;
```
(usa un `cliente_id` reale esistente nel tuo ambiente di test, non in produzione). Poi:
```sql
SELECT * FROM fondo_silenziosi_beneficiari_v;
```
Con saldo fondo a 0 (nessuna donazione ancora), la quota deve risultare `0.00` — coerente col Caso 3 dello script Node. **Non lasciare questi dati di test nell'ambiente di produzione**: rimuovili con `DELETE FROM valutazioni_bisogno_silenziosi WHERE risposte = '{}'::jsonb;` prima di procedere ai task successivi.

- [ ] **Step 3: Nessun commit**

Questo task è solo verifica: lo script in `$CLAUDE_JOB_DIR/tmp` non fa parte del repository, non va committato.

---

### Task 3: UI donazione al fondo

**Files:**
- Modify: `index.html` — dopo la chiusura di `creditRequestForm` (circa riga 238, dopo `</form>`, prima di `<div class="mini-list" id="customerCreditRequests">`)
- Modify: `app.js` — `el` object, nuova funzione `handleDonazioneSilenziosi`, wiring eventi

**Interfaces:**
- Consuma: `supabaseClient.rpc("dona_a_lista_silenziosi_pilot", ...)` (Task 1), `getBalances`, `getCurrentCustomerIdForRole` (esistenti).
- Produce: nessuna funzione riusata da altri task.

- [ ] **Step 1: HTML — form donazione**

In `index.html`, subito dopo `</form>` di `creditRequestForm` (circa riga 238):

```html
              <details class="signup-box">
                <summary>Dona il tuo credito alla Lista dei Silenziosi</summary>
                <form id="donazioneSilenziosiForm" class="form">
                  <p class="notice full">
                    Il credito donato non torna indietro e va a sostenere persone fragili del territorio
                    seguite da Salute Quotidiana, in forma anonima.
                  </p>
                  <label>
                    Importo da donare (euro SQ)
                    <input required type="number" min="0.01" step="0.01" name="importo" placeholder="0,00">
                  </label>
                  <p class="form-status full" id="donazioneSilenziosiStatus">Inserisci l'importo che vuoi donare, entro il tuo saldo disponibile.</p>
                  <button class="primary full" type="submit">Dona ora</button>
                </form>
              </details>
```

- [ ] **Step 2: `app.js` — `el` refs**

Nell'oggetto `el`, subito dopo `creditRequestStatus: document.querySelector("#creditRequestStatus"),` (circa riga 127):

```javascript
  donazioneSilenziosiForm: document.querySelector("#donazioneSilenziosiForm"),
  donazioneSilenziosiStatus: document.querySelector("#donazioneSilenziosiStatus"),
```

- [ ] **Step 3: `app.js` — funzione di invio**

Subito dopo `saveCreditRequestToSupabase` (dopo la riga 2301, prima di `function setCreditRequestMessage`):

```javascript
async function handleDonazioneSilenziosiSubmit(event) {
  event.preventDefault();

  const customerId = getCurrentCustomerIdForRole();
  if (!customerId) {
    setDonazioneSilenziosiMessage("Prima completa il profilo cliente.", "error");
    return;
  }

  const form = new FormData(event.currentTarget);
  const importo = parseMoney(form.get("importo"));
  const balance = getBalances(customerId).confirmed;

  if (!importo || importo <= 0) {
    setDonazioneSilenziosiMessage("Inserisci un importo valido.", "error");
    return;
  }

  if (importo > balance) {
    setDonazioneSilenziosiMessage(`Puoi donare al massimo il tuo saldo disponibile: ${formatMoney(balance)} euro.`, "error");
    return;
  }

  if (!supabaseClient) {
    setDonazioneSilenziosiMessage("Database non collegato.", "error");
    return;
  }

  setDonazioneSilenziosiMessage("Donazione in corso.", "loading");
  const { error } = await supabaseClient.rpc("dona_a_lista_silenziosi_pilot", {
    p_cliente_id: customerId,
    p_importo: importo
  });

  if (error) {
    console.error("Errore donazione Lista Silenziosi:", error);
    setDonazioneSilenziosiMessage(`Donazione non riuscita: ${error.message}`, "error");
    return;
  }

  event.currentTarget.reset();
  setDonazioneSilenziosiMessage(`Grazie. Hai donato ${formatMoney(importo)} euro SQ alla Lista dei Silenziosi.`, "success");
  showToast("Donazione registrata. Grazie.");
  loadPilotBalancesFromSupabase();
}

function setDonazioneSilenziosiMessage(message, status) {
  if (!el.donazioneSilenziosiStatus) return;
  el.donazioneSilenziosiStatus.textContent = message;
  el.donazioneSilenziosiStatus.dataset.status = status;
}
```

- [ ] **Step 4: `app.js` — wiring**

Vicino a `el.creditRequestForm.addEventListener("submit", handleCreditRequestSubmit);` (circa riga 857):

```javascript
  if (el.donazioneSilenziosiForm) el.donazioneSilenziosiForm.addEventListener("submit", handleDonazioneSilenziosiSubmit);
```

- [ ] **Step 5: Verifica manuale**

Accedi come cliente con saldo disponibile > 0. Apri "Dona il tuo credito alla Lista dei Silenziosi", inserisci un importo maggiore del saldo: deve comparire l'errore "Puoi donare al massimo...". Inserisci un importo valido: deve comparire il messaggio di successo e il saldo cliente (visibile in "Situazione cliente") deve diminuire dell'importo donato dopo il refresh automatico.

- [ ] **Step 6: Commit**

```bash
git add index.html app.js
git commit -m "lista-silenziosi: form donazione credito al fondo condiviso"
```

---

### Task 4: UI questionario bisogni (ammissione beneficiario)

**Files:**
- Modify: `index.html` — subito dopo il blocco donazione creato nel Task 3
- Modify: `app.js` — `el` object, nuova funzione `handleValutazioneBisogniSubmit`, wiring eventi

**Interfaces:**
- Consuma: `supabaseClient.rpc("invia_valutazione_bisogno_pilot", ...)` (Task 1).
- Produce: nessuna funzione riusata da altri task.

- [ ] **Step 1: HTML — questionario**

In `index.html`, subito dopo il blocco `</details>` del Task 3 (donazione):

```html
              <details class="signup-box">
                <summary>Richiedi di essere ammesso alla Lista dei Silenziosi</summary>
                <form id="valutazioneBisogniForm" class="form">
                  <p class="notice full">
                    Questo questionario aiuta Salute Quotidiana a capire chi ha piu' bisogno di essere
                    sostenuto dal fondo. Non chiede dati sanitari o diagnosi, solo la situazione pratica.
                    Puo' compilarlo il paziente stesso o un familiare per suo conto.
                  </p>
                  <label>
                    Chi compila il questionario
                    <select required name="compilatoDa">
                      <option value="paziente">Il paziente stesso</option>
                      <option value="familiare">Un familiare per suo conto</option>
                    </select>
                  </label>
                  <label>
                    Vive solo, senza nessuno che lo assista quotidianamente?
                    <select required name="q1" data-peso="20">
                      <option value="0">No, c'e' sempre qualcuno</option>
                      <option value="20">Si', vive solo</option>
                    </select>
                  </label>
                  <label>
                    Ha difficolta' a muoversi o uscire di casa da solo?
                    <select required name="q2" data-peso="20">
                      <option value="0">Nessuna difficolta'</option>
                      <option value="10">Qualche difficolta'</option>
                      <option value="20">Difficolta' grave, non esce da solo</option>
                    </select>
                  </label>
                  <label>
                    Ha familiari vicini (figli o parenti nello stesso paese)?
                    <select required name="q3" data-peso="20">
                      <option value="0">Si', presenti e vicini</option>
                      <option value="20">No, nessuno vicino</option>
                    </select>
                  </label>
                  <label>
                    Ha gia' ricevuto credito SQ (proprio o donato da altri) nell'ultimo mese?
                    <select required name="q4" data-peso="20">
                      <option value="0">Si', abbastanza</option>
                      <option value="20">No, nessun credito ricevuto</option>
                    </select>
                  </label>
                  <label>
                    Il reddito familiare e' sufficiente per le cure di cui ha bisogno?
                    <select required name="q5" data-peso="20">
                      <option value="0">Si', sufficiente</option>
                      <option value="20">No, non sufficiente</option>
                    </select>
                  </label>
                  <label class="checkbox full">
                    <input required type="checkbox" name="consensoValutazione">
                    <span>Acconsento a che queste risposte siano trattate da Salute Quotidiana per decidere l'accesso al fondo Lista dei Silenziosi.</span>
                  </label>
                  <p class="form-status full" id="valutazioneBisogniStatus">Rispondi a tutte le domande e conferma il consenso per inviare.</p>
                  <button class="primary full" type="submit">Invia richiesta di ammissione</button>
                </form>
              </details>
```

- [ ] **Step 2: `app.js` — `el` refs**

Subito dopo `donazioneSilenziosiStatus: document.querySelector("#donazioneSilenziosiStatus"),` (Task 3, Step 2):

```javascript
  valutazioneBisogniForm: document.querySelector("#valutazioneBisogniForm"),
  valutazioneBisogniStatus: document.querySelector("#valutazioneBisogniStatus"),
```

- [ ] **Step 3: `app.js` — funzione di invio**

Subito dopo `setDonazioneSilenziosiMessage` (Task 3, Step 3):

```javascript
async function handleValutazioneBisogniSubmit(event) {
  event.preventDefault();

  const customerId = getCurrentCustomerIdForRole();
  if (!customerId) {
    setValutazioneBisogniMessage("Prima completa il profilo cliente.", "error");
    return;
  }

  const form = new FormData(event.currentTarget);
  const compilatoDa = form.get("compilatoDa");
  const risposte = {
    vive_solo: Number(form.get("q1")),
    difficolta_movimento: Number(form.get("q2")),
    rete_familiare_assente: Number(form.get("q3")),
    nessun_credito_recente: Number(form.get("q4")),
    reddito_insufficiente: Number(form.get("q5"))
  };
  const punteggio = Object.values(risposte).reduce((acc, v) => acc + v, 0);
  const consenso = !!form.get("consensoValutazione");

  if (!consenso) {
    setValutazioneBisogniMessage("Serve il consenso per inviare il questionario.", "error");
    return;
  }

  if (!supabaseClient) {
    setValutazioneBisogniMessage("Database non collegato.", "error");
    return;
  }

  setValutazioneBisogniMessage("Invio in corso.", "loading");
  const { error } = await supabaseClient.rpc("invia_valutazione_bisogno_pilot", {
    p_cliente_id: customerId,
    p_punteggio: punteggio,
    p_risposte: risposte,
    p_consenso: consenso,
    p_compilato_da: compilatoDa
  });

  if (error) {
    console.error("Errore invio valutazione bisogni:", error);
    setValutazioneBisogniMessage(`Invio non riuscito: ${error.message}`, "error");
    return;
  }

  event.currentTarget.reset();
  setValutazioneBisogniMessage("Richiesta inviata. Salute Quotidiana la considerera' per il fondo Lista dei Silenziosi.", "success");
  showToast("Questionario inviato.");
}

function setValutazioneBisogniMessage(message, status) {
  if (!el.valutazioneBisogniStatus) return;
  el.valutazioneBisogniStatus.textContent = message;
  el.valutazioneBisogniStatus.dataset.status = status;
}
```

- [ ] **Step 4: `app.js` — wiring**

Vicino al wiring del Task 3, Step 4:

```javascript
  if (el.valutazioneBisogniForm) el.valutazioneBisogniForm.addEventListener("submit", handleValutazioneBisogniSubmit);
```

- [ ] **Step 5: Verifica manuale**

Accedi come cliente, apri "Richiedi di essere ammesso alla Lista dei Silenziosi", rispondi a tutte le domande scegliendo le opzioni che danno punteggio massimo (20 ciascuna), spunta il consenso, invia. Deve comparire il messaggio di successo. Verifica su Supabase (`SELECT * FROM valutazioni_bisogno_silenziosi ORDER BY created_at DESC LIMIT 1;`) che il `punteggio` sia `100` e `consenso_valutazione = true`.

- [ ] **Step 6: Commit**

```bash
git add index.html app.js
git commit -m "lista-silenziosi: questionario bisogni per ammissione beneficiario"
```

---

### Task 5: Pannello Angelo — saldo fondo, beneficiari, erogazione

**Files:**
- Modify: `index.html` — nuovo panel dentro `<section class="tab-panel" id="salute">`, subito prima della sua chiusura (dopo il panel "Registra prestazione")
- Modify: `app.js` — `el` object, nuove funzioni `loadFondoSilenziosi`, `renderFondoSilenziosi`, `handleErogazioneSilenziosiSubmit`, wiring
- Modify: `styles.css` — nessuna nuova classe strettamente necessaria (riuso `.metric-grid`, `.mini-list`, `.form`)

**Interfaces:**
- Consuma: viste `fondo_silenziosi_saldo_v`, `fondo_silenziosi_beneficiari_v`, RPC `eroga_da_lista_silenziosi_pilot` (Task 1); `getCustomer`, `services`, `formatMoney` (esistenti).

- [ ] **Step 1: HTML — nuovo panel**

In `index.html`, dentro `<section class="tab-panel" id="salute">`, subito dopo il tag `</section>` che chiude il panel "Registra prestazione" (dopo `<div class="mini-list" id="redemptionHistory"></div>` e la sua chiusura `</section>`, prima della chiusura del `tab-panel` stesso):

```html
          <section class="panel">
            <div class="section-heading">
              <p class="eyebrow">Fondo condiviso</p>
              <h2>Lista dei Silenziosi</h2>
            </div>
            <div class="notice">
              Fondo alimentato da donazioni anonime, ripartito automaticamente tra i beneficiari ammessi
              in proporzione al loro punteggio di bisogno. Nessun donatore e' mai indicato per nome.
            </div>
            <div class="metric-grid" id="silenziosiFondoMetrics"></div>
            <div class="section-heading section-heading--compact">
              <h2>Beneficiari ammessi</h2>
            </div>
            <div class="mini-list" id="silenziosiBeneficiariList"></div>
            <div class="section-heading section-heading--compact">
              <h2>Eroga prestazione da fondo</h2>
            </div>
            <form id="erogazioneSilenziosiForm" class="form">
              <label>
                Beneficiario
                <select required name="beneficiarioClienteId" id="erogazioneSilenziosiBeneficiario"></select>
              </label>
              <label>
                Prestazione
                <select required name="tipoPrestazione" id="erogazioneSilenziosiPrestazione"></select>
              </label>
              <p class="form-status full" id="erogazioneSilenziosiStatus">Seleziona beneficiario e prestazione: la quota disponibile copre fino al costo pieno.</p>
              <button class="primary full" type="submit">Eroga da fondo</button>
            </form>
          </section>
```

- [ ] **Step 2: `app.js` — `el` refs**

Subito dopo `valutazioneBisogniStatus: document.querySelector("#valutazioneBisogniStatus"),` (Task 4, Step 2):

```javascript
  silenziosiFondoMetrics: document.querySelector("#silenziosiFondoMetrics"),
  silenziosiBeneficiariList: document.querySelector("#silenziosiBeneficiariList"),
  erogazioneSilenziosiForm: document.querySelector("#erogazioneSilenziosiForm"),
  erogazioneSilenziosiBeneficiario: document.querySelector("#erogazioneSilenziosiBeneficiario"),
  erogazioneSilenziosiPrestazione: document.querySelector("#erogazioneSilenziosiPrestazione"),
  erogazioneSilenziosiStatus: document.querySelector("#erogazioneSilenziosiStatus"),
```

- [ ] **Step 3: `app.js` — caricamento e rendering**

Subito dopo `loadPilotRedemptionsFromSupabase` (dopo la riga 744, prima di `function mapSupabaseRedemption`):

```javascript
let silenziosiBeneficiariCache = [];

async function loadFondoSilenziosi() {
  if (!supabaseClient) return;

  const { data: saldoRows, error: saldoError } = await supabaseClient
    .from("fondo_silenziosi_saldo_v")
    .select("saldo_disponibile");

  const { data: beneficiariRows, error: beneficiariError } = await supabaseClient
    .from("fondo_silenziosi_beneficiari_v")
    .select("cliente_id,punteggio,valutato_il,quota_disponibile")
    .order("quota_disponibile", { ascending: false });

  if (saldoError || beneficiariError) {
    console.error("Errore caricamento Lista dei Silenziosi:", saldoError || beneficiariError);
    return;
  }

  const saldoDisponibile = Number(saldoRows?.[0]?.saldo_disponibile || 0);
  silenziosiBeneficiariCache = beneficiariRows || [];
  renderFondoSilenziosi(saldoDisponibile, silenziosiBeneficiariCache);
}

function renderFondoSilenziosi(saldoDisponibile, beneficiari) {
  if (el.silenziosiFondoMetrics) {
    el.silenziosiFondoMetrics.innerHTML = `
      <article><span>Saldo fondo disponibile</span><strong>${formatMoney(saldoDisponibile)} euro SQ</strong></article>
      <article><span>Beneficiari ammessi</span><strong>${beneficiari.length}</strong></article>
    `;
  }

  if (el.silenziosiBeneficiariList) {
    el.silenziosiBeneficiariList.innerHTML = beneficiari.length
      ? beneficiari.map((b) => {
          const customer = getCustomer(b.cliente_id);
          const nome = customer ? `${customer.firstName} ${customer.lastName}` : b.cliente_id;
          return `<div class="mini-list__row"><span>${escapeHtml(nome)} — punteggio ${b.punteggio}</span><strong>${formatMoney(b.quota_disponibile)} euro SQ</strong></div>`;
        }).join("")
      : `<p class="form-status">Nessun beneficiario ammesso al momento.</p>`;
  }

  if (el.erogazioneSilenziosiBeneficiario) {
    el.erogazioneSilenziosiBeneficiario.innerHTML = beneficiari.map((b) => {
      const customer = getCustomer(b.cliente_id);
      const nome = customer ? `${customer.firstName} ${customer.lastName}` : b.cliente_id;
      return `<option value="${b.cliente_id}">${escapeHtml(nome)} — quota ${formatMoney(b.quota_disponibile)} euro</option>`;
    }).join("");
  }

  if (el.erogazioneSilenziosiPrestazione && !el.erogazioneSilenziosiPrestazione.options.length) {
    el.erogazioneSilenziosiPrestazione.innerHTML = Object.entries(services)
      .filter(([, config]) => config.available !== false)
      .map(([name, config]) => `<option value="${escapeHtml(name)}">${escapeHtml(name)} — ${formatMoney(config.price)} euro</option>`)
      .join("");
  }
}
```

- [ ] **Step 4: `app.js` — erogazione**

Subito dopo `renderFondoSilenziosi`:

```javascript
async function handleErogazioneSilenziosiSubmit(event) {
  event.preventDefault();

  if (!requireAccess("salute")) return;

  const form = new FormData(event.currentTarget);
  const beneficiarioClienteId = form.get("beneficiarioClienteId");
  const tipoPrestazione = form.get("tipoPrestazione");
  const serviceConfig = services[tipoPrestazione];

  if (!beneficiarioClienteId || !serviceConfig) {
    setErogazioneSilenziosiMessage("Seleziona beneficiario e prestazione validi.", "error");
    return;
  }

  if (!supabaseClient) {
    setErogazioneSilenziosiMessage("Database non collegato.", "error");
    return;
  }

  setErogazioneSilenziosiMessage("Erogazione in corso.", "loading");
  const { data, error } = await supabaseClient.rpc("eroga_da_lista_silenziosi_pilot", {
    p_beneficiario_cliente_id: beneficiarioClienteId,
    p_tipo_prestazione: tipoPrestazione,
    p_prezzo_prestazione: serviceConfig.price,
    p_importo_pagato_extra: 0
  });

  if (error) {
    console.error("Errore erogazione Lista Silenziosi:", error);
    setErogazioneSilenziosiMessage(`Erogazione non riuscita: ${error.message}`, "error");
    return;
  }

  if (!data?.ok) {
    const messaggi = {
      beneficiario_non_ammesso: "Questo beneficiario non risulta piu' ammesso al fondo.",
      fondo_esaurito: "La quota disponibile per questo beneficiario e' esaurita."
    };
    setErogazioneSilenziosiMessage(messaggi[data?.errore] || "Erogazione non riuscita.", "error");
    return;
  }

  event.currentTarget.reset();
  setErogazioneSilenziosiMessage(
    `Erogati ${formatMoney(data.importo_erogato)} euro SQ dal fondo. Differenza da pagare: ${formatMoney(data.differenza_da_pagare)} euro.`,
    "success"
  );
  showToast("Prestazione erogata dal fondo Lista dei Silenziosi.");
  loadFondoSilenziosi();
}

function setErogazioneSilenziosiMessage(message, status) {
  if (!el.erogazioneSilenziosiStatus) return;
  el.erogazioneSilenziosiStatus.textContent = message;
  el.erogazioneSilenziosiStatus.dataset.status = status;
}
```

- [ ] **Step 5: `app.js` — wiring e caricamento iniziale**

Vicino al wiring del Task 4, Step 4:

```javascript
  if (el.erogazioneSilenziosiForm) el.erogazioneSilenziosiForm.addEventListener("submit", handleErogazioneSilenziosiSubmit);
```

Nel punto in cui `loadPilotRedemptionsFromSupabase()` viene richiamata al caricamento dati per il ruolo `salute_quotidiana` (cerca la funzione che orchestra i caricamenti iniziali per questo ruolo, vicino a dove viene chiamata `loadCreditRequestsFromSupabase()`), aggiungi:

```javascript
  loadFondoSilenziosi();
```

- [ ] **Step 6: Verifica manuale end-to-end**

Come cliente: dona credito (Task 3) e invia un questionario bisogni con punteggio alto (Task 4). Come Salute Quotidiana (tab "Salute Quotidiana"): il panel "Lista dei Silenziosi" deve mostrare il saldo fondo aggiornato e il beneficiario in elenco con la sua quota. Eroga una prestazione economica (es. "Iniezione intramuscolare", 8€) per quel beneficiario: il messaggio deve confermare l'importo erogato, e ricaricando il panel la quota disponibile per quel beneficiario deve essere scesa di conseguenza. Prova a erogare piu' volte fino a esaurire la quota: l'ultimo tentativo oltre il residuo deve mostrare "quota... esaurita" o erogare solo la parte residua con differenza da pagare correttamente calcolata.

- [ ] **Step 7: Commit**

```bash
git add index.html app.js styles.css
git commit -m "lista-silenziosi: pannello Angelo con saldo fondo, beneficiari e erogazione"
```

---

### Task 6: Bump versione e verifica finale

**Files:**
- Modify: `app.js` (`APP_VERSION`)
- Modify: `index.html` (query-string cache-busting)

- [ ] **Step 1: Bump versione**

Aggiorna `APP_VERSION` in `app.js` e i corrispondenti `?v=` in `index.html` (usa il numero successivo a quello già in uso al momento dell'esecuzione — verifica il valore corrente prima di incrementare, potrebbe essere già cambiato da altri piani eseguiti nel frattempo).

- [ ] **Step 2: `node --check app.js`**

Esegui: `node --check app.js`
Atteso: nessun output, exit code 0.

- [ ] **Step 3: Verifica manuale completa**

Ripeti l'intero flusso del Task 5 Step 6 con la versione bumpata. Verifica che i flussi esistenti (QR scontrini, redemption normale, richieste credito) continuino a funzionare senza errori in console.

- [ ] **Step 4: Commit**

```bash
git add app.js index.html
git commit -m "lista-silenziosi: bump versione e chiusura modulo"
```

---

## Self-Review Note (svolta durante la stesura di questo piano)

- **Copertura spec:** donazione anonima al fondo (Task 3) ✓, ammissione via questionario ad hoc non clinico (Task 4) ✓, dato visibile solo a salute_quotidiana + consenso dedicato (Task 1 RLS implicita via RPC `SECURITY DEFINER` + Task 4 checkbox) ✓, ripartizione dinamica proporzionale (Task 1 vista + Task 2 verifica) ✓, nessun tetto 50€ per beneficiari (RPC Task 1 non applica alcun cap) ✓, credito gia' erogato mai ridotto retroattivamente (Task 1 vista, verificato Task 2 Caso 5) ✓.
- **Placeholder scan:** nessun "gestisci errori" generico — ogni step ha codice completo, inclusi i messaggi di errore RPC mappati esplicitamente (Task 5, Step 4).
- **Coerenza tipi/nomi:** `eroga_da_lista_silenziosi_pilot` restituisce `{ ok, id, importo_erogato, differenza_da_pagare }` nella RPC (Task 1) ed e' consumato con gli stessi nomi in `handleErogazioneSilenziosiSubmit` (Task 5). `dona_a_lista_silenziosi_pilot` prende `p_cliente_id`/`p_importo` in entrambi Task 1 e Task 3. `invia_valutazione_bisogno_pilot` prende `p_cliente_id, p_punteggio, p_risposte, p_consenso, p_compilato_da` in Task 1 e Task 4.
- **Rischio noto non mitigato in questo piano:** punteggio bisogno auto-dichiarato senza validazione esterna — accettato per decisione esplicita del committente, da tenere monitorato manualmente da Angelo tramite il pannello del Task 5.
