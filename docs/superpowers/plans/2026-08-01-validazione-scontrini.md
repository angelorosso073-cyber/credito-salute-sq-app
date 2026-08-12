# Validazione Scontrini — Inversione QR, Anti-Duplicato, Limiti di Plausibilità — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) o superpowers:executing-plans per eseguire questo piano task per task. Gli step usano checkbox (`- [ ]`) per il tracking.

**Goal:** Sostituire il QR attuale (bar scansiona cliente) con un QR/codice invertito (banco espone, cliente inquadra) che dimostra la presenza fisica nel locale; aggiungere un vincolo di unicità anti-duplicato basato su matricola registratore telematico; aggiungere limiti di plausibilità configurabili per esercizio (tetto giornaliero, soglia di revisione manuale).

**Architecture:** Estensione additiva di `scontrini` (nuove colonne nullable), due nuove tabelle di configurazione (`registratori_telematici`, `limiti_bar`) e una nuova tabella per i dispositivi banco (`banco_dispositivi`, contiene il segreto HMAC lato server). La funzione esistente `registra_scontrino_pilot` viene estesa con parametri opzionali aggiuntivi (mai rimossi, sempre `DEFAULT NULL` in coda) e la logica che decide lo stato iniziale dello scontrino si sposta interamente lato server: duplicato → rifiuto; oltre soglia → coda di revisione; codice banco valido → confermato subito; nessun codice → sospeso con scadenza. La distinzione "credito confermato/spendibile" vs "credito in verifica/non spendibile" **esiste già** in `saldi_clienti_app_pilot` e `saldo_cliente_confermato()` (filtrano su `scontrini.stato = 'confermato'`): non introduco un sistema parallelo, ci appoggio sopra. Il vecchio meccanismo QR (bar scansiona cliente) resta intatto in database ma smette di essere richiamato dal frontend.

**Tech Stack:** Postgres/plpgsql (Supabase, `pgcrypto` già abilitato per `hmac()`), vanilla JS (`app.js`), HTML statico (`index.html` + nuovo `banco.html` standalone), CSS. Nessun framework di test — verifica manuale in browser + query dirette su Supabase, come per i piani precedenti.

## Correzioni allo stato di partenza dichiarato nel brief

Verificato sul repository prima di scrivere questo piano — due punti del brief non corrispondono più allo stato reale:

1. **`APP_VERSION` è già `"v53"`** (non `"v52"`), bumpata dal piano "Lista dei Silenziosi" eseguito il 2026-07-30. Questo piano bump a **`v54`**.
2. **Il credito è già al 15%**, non al 3%: `CREDIT_RATE = 0.15` in `app.js:3`. Un vecchio file (`docs/supabase-blocco-duplicati-scontrini.sql`, mai più applicato dopo `docs/supabase-operatore-label.sql`) conteneva un ricalcolo server-side al 3%: è codice morto, ignoralo.

**Anomalia di sicurezza trovata mentre indagavo la funzione che questo piano deve comunque riscrivere** (non richiesta esplicitamente dal brief, ma la tocco comunque e la lascerei rotta se non la segnalassi): `docs/supabase-hardening-sicurezza-pilot.sql` (2026-07-19) aveva tolto l'accesso `anon` a `registra_scontrino_pilot` e aggiunto un controllo `auth.uid() IS NULL → RAISE EXCEPTION`. Il file successivo `docs/supabase-operatore-label.sql` (2026-07-25) ha **ricreato la funzione da zero** per aggiungere `p_operatore_label`, e la nuova versione non ha riportato né il controllo `auth.uid()` né la restrizione dei grant — la funzione live oggi è di nuovo eseguibile da `anon` e non verifica che il chiamante sia autenticato o proprietario del cliente. Il Task 1 di questo piano riscrive comunque questa funzione: ne approfitto per **reintrodurre** il controllo (stessa logica già presente in `docs/supabase-hardening-sicurezza-pilot.sql`, non è una modifica nuova, è un ripristino). Se preferisci non toccarlo in questo piano dimmelo prima di eseguire il Task 1 — per ora l'ho incluso perché lasciare la falla mentre riscrivo la stessa funzione mi è sembrato peggio che ignorarla.

## Domande aperte — rispondi prima di eseguire i task indicati

1. **Matricola reale del registratore telematico del Bar pilota Francofonte.** Il Task 1 crea la tabella `registratori_telematici` e richiede di inserire la matricola vera con una query che ti preparo — senza quel valore il vincolo "la matricola deve appartenere a un registratore dell'esercizio aderente" non può essere verificato e ogni scontrino verrà rifiutato. Recuperala dallo scontrino fiscale del bar (di solito stampata in basso, dicitura "MF" o "matricola") o chiedila al titolare.
2. **Valori dei parametri configurabili** (Task 5, tabella `limiti_bar`): ho messo valori di default ragionevoli per un bar con cassa presidiata — tetto **3 scontrini/giorno per cliente**, soglia di revisione manuale **30 euro** (uguale all'attuale `AUTO_APPROVE_MAX_AMOUNT`), sospensione codice banco **12 giorni** (nel range 10–15 richiesto), finestra codice **90 secondi** (fisso, come richiesto). Confermali o dimmi altri numeri prima del Task 5 Step 2 — sono comunque modificabili in qualsiasi momento con un `UPDATE` a riga singola, senza bisogno di ridistribuire codice.
3. **Testo del messaggio ai 20 clienti per la migrazione a caldo** (Task 11): ho scritto una bozza WhatsApp, ma è tua la decisione se e quando inviarla — il piano non la invia automaticamente.
4. **Disponibilità di `pg_cron` sul progetto Supabase** (Task 10): il decadimento automatico dei crediti sospesi lo usa. Se l'estensione non è abilitabile dal tuo piano Supabase, il Task 10 include comunque un fallback manuale (una query da lanciare ogni tanto), ma è meglio saperlo prima.

## Global Constraints

- **Solo addizioni. Non rompere il pilot in corso** (20 clienti reali, fondo 1.000 €). Nessuna tabella droppata, nessuna vista ricreata in modo incompatibile, nessun dato cancellato.
- Ogni funzione riscritta usa `CREATE OR REPLACE FUNCTION` con i parametri esistenti invariati e nuovi parametri **sempre aggiunti in coda con `DEFAULT NULL`** — mai `DROP FUNCTION`, mai cambio di tipo di ritorno. Compatibile con qualunque chiamante non ancora aggiornato.
- Ogni vincolo `CHECK` esistente che va allargato (es. `scontrini.stato`, `scontrini.motivo_sospensione`) viene modificato con `DROP CONSTRAINT` + `ADD CONSTRAINT` che include **tutti** i valori vecchi più quelli nuovi — mai una sostituzione che restringe.
- Naming coerente col resto del progetto: tabelle senza suffisso (`limiti_bar`, `registratori_telematici`, `banco_dispositivi`), RPC `verbo_oggetto_pilot`, viste `nome_app_pilot` o `nome_pilot`.
- Bump `APP_VERSION` a **v54** e cache-busting (`styles.css?v=56`, `app.js?v=54`) nell'ultimo task.
- Il vecchio meccanismo QR (`genera_qr_scontrino_pilot`, `conferma_qr_scontrino_pilot`, `operatori_bar`, `verifiche_scontrini`, vista `scontrini_bar_verifica`) **non va toccato in database** — solo scollegato dal frontend. Vedi Task 9 per l'elenco di cosa resta orfano.
- Fasi ordinate per rischio crescente: Fase A (Intervento 2, anti-duplicato) e Fase B (Intervento 3, limiti di plausibilità) non toccano il flusso di conferma esistente, solo aggiungono controlli. Fase C (Intervento 1, inversione QR) sostituisce un meccanismo vivo — è l'ultima e ha un task dedicato alla migrazione a caldo.

---

## File Structure

- **Create `docs/supabase-anti-duplicato-scontrini.sql`** — Fase A: colonna `matricola_rt`, tabella `registratori_telematici`, indice unico parziale anti-duplicato, riscrittura di `registra_scontrino_pilot` (+ripristino controllo auth, +controllo data futura/data-avvio-programma, +controllo matricola).
- **Create `docs/supabase-limiti-plausibilita-bar.sql`** — Fase B: tabella `limiti_bar`, colonna `motivo_sospensione`, vista `scontrini_revisione_manuale_pilot`, riscrittura di `registra_scontrino_pilot` (+tetto giornaliero, +soglia revisione).
- **Create `docs/supabase-inversione-qr-banco.sql`** — Fase C: tabella `banco_dispositivi`, colonne `sospeso_scaduto_il`/`attivato_codice_banco_at`, allargamento CHECK su `motivo_sospensione` e `stato` (nuovo valore `'scaduto'`), RPC `richiedi_codice_banco_pilot`, `verifica_codice_banco_interna` (non concessa a nessuno, solo uso interno), `attiva_scontrino_con_codice_banco_pilot`, `crea_dispositivo_banco_pilot`, `scadi_scontrini_sospesi_pilot`, riscrittura finale di `registra_scontrino_pilot` (+parametro `p_codice_banco`), estensione vista `scontrini_app_pilot`.
- **Create `docs/supabase-migrazione-qr-a-caldo.sql`** — Fase C, task a parte: script una-tantum per gli scontrini in transito col vecchio QR al momento del deploy.
- **Create `banco.html`** — pagina statica standalone per il dispositivo al banco (nessuna dipendenza da `index.html`/`app.js`/`styles.css`, CSS inline).
- **Modify `index.html`** — Fase A: campo matricola nel form scontrino. Fase C: sostituzione dell'area "mostra QR al barista" con "digita o inquadra il codice del banco"; rimozione dell'area "scansiona QR cliente" dal tab `bar_report`.
- **Modify `app.js`** — Fase A: campo matricola, mappatura errore duplicato. Fase B: pannello revisione manuale, mappatura errore tetto giornaliero. Fase C: flusso codice banco lato cliente, rimozione funzioni vecchio scanner bar-side, nuova label di stato `scaduto`.
- **Modify `styles.css`** — classe `.status-expired` e badge "credito sospeso" (riuso `.mini-list`/`.notice` dove possibile).

---

## Fase A — Intervento 2: chiave anti-duplicato

### Task 1: Schema SQL — matricola, registro registratori, vincolo unico, funzione aggiornata

**Rischio:** riscrive `registra_scontrino_pilot`, funzione già in uso dal pilot. Nessun parametro esistente viene tolto o riordinato, solo aggiunto `p_matricola_rt` in coda con `DEFAULT NULL` — i client non aggiornati continuano a funzionare esattamente come prima (matricola nulla → nessun controllo di registro, nessun blocco). **Rollback:** se qualcosa va storto, ri-applica il contenuto di `docs/supabase-operatore-label.sql` per tornare alla versione precedente della funzione; le nuove colonne/tabelle restano innocue (nullable, non referenziate da nessun altro oggetto).

**Files:**
- Create: `docs/supabase-anti-duplicato-scontrini.sql`

**Interfaces:**
- Produce: tabella `registratori_telematici`; colonna `scontrini.matricola_rt`; funzione `registra_scontrino_pilot` con nuovo parametro opzionale `p_matricola_rt text default null` in coda. Usata da Task 2 (frontend).

- [ ] **Step 1: Scrivere il file SQL completo**

```sql
-- docs/supabase-anti-duplicato-scontrini.sql
-- Fase A — Intervento 2: chiave anti-duplicato su matricola RT + numero documento + data + importo.
-- Eseguire in Supabase SQL Editor dopo docs/supabase-operatore-label.sql (l'ultimo applicato finora).
--
-- Obiettivo:
-- 1. impedire il caricamento due volte dello stesso scontrino, anche da clienti diversi;
-- 2. validare che la matricola appartenga a un registratore dell'esercizio aderente;
-- 3. bloccare data futura e data precedente all'avvio del programma;
-- 4. ripristinare il controllo auth.uid() rimosso per errore da docs/supabase-operatore-label.sql.

-- 1. Colonna nullable: nessuna riga storica viene invalidata.
ALTER TABLE public.scontrini
  ADD COLUMN IF NOT EXISTS matricola_rt TEXT;

-- 2. Registro dei registratori telematici per esercizio aderente.
CREATE TABLE IF NOT EXISTS public.registratori_telematici (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  bar_id UUID NOT NULL REFERENCES public.bar(id) ON DELETE CASCADE,
  matricola TEXT NOT NULL,
  attivo BOOLEAN NOT NULL DEFAULT true,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (bar_id, matricola)
);

ALTER TABLE public.registratori_telematici ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "registratori_select_autenticati" ON public.registratori_telematici;
CREATE POLICY "registratori_select_autenticati"
ON public.registratori_telematici
FOR SELECT
TO authenticated
USING (true);

DROP POLICY IF EXISTS "registratori_gestione_admin_sq" ON public.registratori_telematici;
CREATE POLICY "registratori_gestione_admin_sq"
ON public.registratori_telematici
FOR ALL
TO authenticated
USING (public.e_admin() OR public.e_salute_quotidiana())
WITH CHECK (public.e_admin() OR public.e_salute_quotidiana());

GRANT SELECT ON public.registratori_telematici TO authenticated;
REVOKE ALL ON public.registratori_telematici FROM anon;

-- 3. Vincolo di unicita' anti-duplicato: attivo solo quando la matricola e' presente
--    (le righe storiche senza matricola non vengono mai toccate ne' bloccate) e
--    lo scontrino non e' stato rifiutato (un rifiuto libera la combinazione, cosi'
--    un cliente puo' ricaricare uno scontrino corretto dopo un rifiuto per errore).
CREATE UNIQUE INDEX IF NOT EXISTS idx_scontrini_chiave_duplicato
  ON public.scontrini (matricola_rt, numero_documento, data_scontrino, importo_dichiarato)
  WHERE matricola_rt IS NOT NULL AND stato <> 'rifiutato';

-- 4. Funzione aggiornata: stessi 15 parametri esistenti (0..14) + p_matricola_rt in coda.
CREATE OR REPLACE FUNCTION public.registra_scontrino_pilot(
  p_id                 UUID,
  p_cliente_id         UUID,
  p_bar_id             UUID,
  p_testo_ocr          TEXT,
  p_data_scontrino     DATE,
  p_ora_scontrino      TIME,
  p_numero_documento   TEXT,
  p_importo_dichiarato NUMERIC,
  p_importo_ocr        NUMERIC,
  p_importo_verificato NUMERIC,
  p_credito_generato   NUMERIC,
  p_stato              TEXT,
  p_avviso_duplicato   BOOLEAN,
  p_motivo_controllo   TEXT,
  p_operatore_label    TEXT DEFAULT NULL,
  p_matricola_rt       TEXT DEFAULT NULL
)
RETURNS UUID
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  nuovo_id UUID;
  profilo_corrente_id UUID;
  documento_normalizzato TEXT;
  matricola_normalizzata TEXT;
  PROGRAM_START_DATE CONSTANT DATE := '2026-07-04';
BEGIN
  IF auth.uid() IS NULL THEN
    RAISE EXCEPTION 'accesso richiesto';
  END IF;

  IF p_cliente_id IS NULL THEN
    RAISE EXCEPTION 'cliente mancante';
  END IF;

  IF p_bar_id IS NULL THEN
    RAISE EXCEPTION 'bar mancante';
  END IF;

  SELECT p.id
  INTO profilo_corrente_id
  FROM public.profili p
  WHERE p.auth_user_id = auth.uid()
  LIMIT 1;

  IF profilo_corrente_id IS NULL THEN
    RAISE EXCEPTION 'profilo non trovato';
  END IF;

  IF NOT (
    public.e_admin()
    OR public.e_salute_quotidiana()
    OR public.e_bar()
    OR EXISTS (
      SELECT 1
      FROM public.clienti c
      WHERE c.id = p_cliente_id
        AND c.profilo_id = profilo_corrente_id
        AND c.stato = 'attivo'
    )
  ) THEN
    RAISE EXCEPTION 'cliente non autorizzato';
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM public.clienti c
    WHERE c.id = p_cliente_id AND c.stato = 'attivo'
  ) THEN
    RAISE EXCEPTION 'cliente non valido o non attivo';
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM public.bar b
    WHERE b.id = p_bar_id AND b.attivo = true
  ) THEN
    RAISE EXCEPTION 'bar non valido o non attivo';
  END IF;

  IF p_importo_dichiarato IS NULL OR p_importo_dichiarato <= 0 THEN
    RAISE EXCEPTION 'importo non valido';
  END IF;

  IF p_credito_generato IS NULL OR p_credito_generato < 0 THEN
    RAISE EXCEPTION 'credito non valido';
  END IF;

  IF p_data_scontrino IS NULL THEN
    RAISE EXCEPTION 'data scontrino mancante';
  END IF;

  IF p_data_scontrino > CURRENT_DATE THEN
    RAISE EXCEPTION 'data scontrino futura';
  END IF;

  IF p_data_scontrino < PROGRAM_START_DATE THEN
    RAISE EXCEPTION 'data scontrino precedente all''avvio del programma';
  END IF;

  documento_normalizzato := NULLIF(TRIM(COALESCE(p_numero_documento, '')), '');
  IF documento_normalizzato IS NULL THEN
    RAISE EXCEPTION 'numero documento mancante';
  END IF;

  matricola_normalizzata := UPPER(NULLIF(TRIM(COALESCE(p_matricola_rt, '')), ''));

  IF matricola_normalizzata IS NOT NULL THEN
    IF NOT EXISTS (
      SELECT 1 FROM public.registratori_telematici rt
      WHERE rt.bar_id = p_bar_id
        AND UPPER(rt.matricola) = matricola_normalizzata
        AND rt.attivo = true
    ) THEN
      RAISE EXCEPTION 'matricola registratore non riconosciuta per questo esercizio';
    END IF;

    IF EXISTS (
      SELECT 1 FROM public.scontrini s
      WHERE UPPER(s.matricola_rt) = matricola_normalizzata
        AND LOWER(TRIM(COALESCE(s.numero_documento, ''))) = LOWER(documento_normalizzato)
        AND s.data_scontrino = p_data_scontrino
        AND ROUND(s.importo_dichiarato::numeric, 2) = ROUND(p_importo_dichiarato::numeric, 2)
        AND s.stato <> 'rifiutato'
    ) THEN
      RAISE EXCEPTION 'scontrino duplicato: stessa matricola, numero documento, data e importo';
    END IF;
  END IF;

  INSERT INTO public.scontrini (
    id, cliente_id, bar_id, testo_ocr,
    data_scontrino, ora_scontrino, numero_documento,
    importo_dichiarato, importo_ocr, importo_verificato,
    credito_generato, stato, avviso_duplicato,
    motivo_rifiuto, operatore_label, matricola_rt
  )
  VALUES (
    COALESCE(p_id, gen_random_uuid()),
    p_cliente_id,
    p_bar_id,
    p_testo_ocr,
    p_data_scontrino,
    p_ora_scontrino,
    documento_normalizzato,
    p_importo_dichiarato,
    p_importo_ocr,
    p_importo_verificato,
    p_credito_generato,
    p_stato,
    COALESCE(p_avviso_duplicato, false),
    NULLIF(TRIM(COALESCE(p_motivo_controllo, '')), ''),
    NULLIF(TRIM(COALESCE(p_operatore_label, '')), ''),
    matricola_normalizzata
  )
  RETURNING id INTO nuovo_id;

  RETURN nuovo_id;
END;
$$;

REVOKE ALL ON FUNCTION public.registra_scontrino_pilot(
  uuid, uuid, uuid, text, date, time, text,
  numeric, numeric, numeric, numeric, text, boolean, text, text, text
) FROM anon;

GRANT EXECUTE ON FUNCTION public.registra_scontrino_pilot(
  uuid, uuid, uuid, text, date, time, text,
  numeric, numeric, numeric, numeric, text, boolean, text, text, text
) TO authenticated;

NOTIFY pgrst, 'reload schema';
```

- [ ] **Step 2: Angelo applica il file su Supabase**

Incolla ed esegui `docs/supabase-anti-duplicato-scontrini.sql` nell'SQL Editor di Supabase.

- [ ] **Step 3: Inserire la matricola reale del Bar pilota Francofonte**

Esegui questa query nell'SQL Editor, **sostituendo `'XXXXXXX'` con la matricola vera** (Domanda aperta 1 in testa al piano):

```sql
INSERT INTO public.registratori_telematici (bar_id, matricola)
SELECT id, 'XXXXXXX'
FROM public.bar
WHERE nome = 'Bar pilota Francofonte'
ON CONFLICT (bar_id, matricola) DO NOTHING;
```

- [ ] **Step 4: Verifica manuale su Supabase**

```sql
SELECT * FROM public.registratori_telematici;
```
Atteso: una riga, `matricola` = quella reale, `attivo = true`.

```sql
SELECT count(*) FROM pg_indexes WHERE indexname = 'idx_scontrini_chiave_duplicato';
```
Atteso: `1`.

- [ ] **Step 5: Commit**

```bash
git add docs/supabase-anti-duplicato-scontrini.sql
git commit -m "v54: schema anti-duplicato scontrini — matricola RT, indice unico, controlli data"
```

---

### Task 2: Frontend — campo matricola nel caricamento scontrino

**Files:**
- Modify: `index.html` — subito dopo il campo "Numero documento" nel form `receiptForm` (circa riga 337-340)
- Modify: `app.js` — lettura campo, invio parametro RPC, messaggio riepilogo, mappatura errore duplicato/matricola

**Interfaces:**
- Consuma: `registra_scontrino_pilot` con `p_matricola_rt` (Task 1).

- [ ] **Step 1: HTML — campo matricola**

In `index.html`, subito dopo il blocco:
```html
              <label>
                Numero documento
                <input required name="documentNumber" placeholder="Es. 183">
              </label>
```
aggiungi:
```html
              <label>
                Matricola registratore telematico (RT)
                <input required name="matricolaRt" placeholder="Es. 12345678" autocomplete="off">
              </label>
              <p class="notice full">
                La trovi stampata sullo scontrino, di solito in basso, vicino alla dicitura "MF" o "matricola".
              </p>
```

- [ ] **Step 2: `app.js` — validazione e invio**

In `submitReceipt` (circa riga 1434), subito dopo il controllo del numero documento:
```javascript
  if (!cleanText(form.get("documentNumber"))) {
    stopReceiptSubmit("Inserisci il numero documento dello scontrino.");
    return;
  }
```
aggiungi:
```javascript
  if (!cleanText(form.get("matricolaRt"))) {
    stopReceiptSubmit("Inserisci la matricola del registratore telematico (la trovi sullo scontrino).");
    return;
  }
```

Nella costruzione dell'oggetto `receipt` (circa riga 1457), aggiungi il campo:
```javascript
  const receipt = {
    id: crypto.randomUUID(),
    customerId: selectedCustomerId,
    barName: BAR_NAME,
    receiptDate: form.get("receiptDate"),
    receiptTime: form.get("receiptTime"),
    documentNumber: cleanText(form.get("documentNumber")),
    matricolaRt: cleanText(form.get("matricolaRt")),
    amount,
    credit: roundMoney(amount * CREDIT_RATE),
    status: "pending",
    note: "",
    ocr: currentOcrResult,
    imageData,
    createdAt: new Date().toISOString()
  };
```

In `confirmReceiptData` (circa riga 1709-1721), aggiungi la riga della matricola al riepilogo:
```javascript
function confirmReceiptData(receipt) {
  return window.confirm([
    "Controlla i dati dello scontrino prima di inviare:",
    "",
    `Data: ${receipt.receiptDate || "mancante"}`,
    `Ora: ${receipt.receiptTime || "mancante"}`,
    `Documento: ${receipt.documentNumber || "mancante"}`,
    `Matricola RT: ${receipt.matricolaRt || "mancante"}`,
    `Importo: ${formatMoney(receipt.amount)} euro`,
    `Credito SQ: ${formatMoney(receipt.credit)} euro`,
    "",
    "Se sono corretti, premi OK.",
    "Se sono sbagliati, premi Annulla e correggi i campi."
  ].join("\n"));
}
```

In `saveReceiptToSupabase` (circa riga 1798), aggiungi il parametro alla chiamata RPC:
```javascript
  const { data, error } = await supabaseClient.rpc("registra_scontrino_pilot", {
    p_id: receipt.id,
    p_cliente_id: receipt.customerId,
    p_bar_id: activeBar.id,
    p_testo_ocr: receipt.ocr?.text || null,
    p_data_scontrino: receipt.receiptDate,
    p_ora_scontrino: receipt.receiptTime,
    p_numero_documento: receipt.documentNumber,
    p_importo_dichiarato: receipt.amount,
    p_importo_ocr: receipt.ocr?.fields?.amount || null,
    p_importo_verificato: null,
    p_credito_generato: receipt.credit,
    p_stato: "in_verifica",
    p_avviso_duplicato: Boolean(duplicate),
    p_motivo_controllo: validation.message,
    p_operatore_label: receipt.operatorLabel || null,
    p_matricola_rt: receipt.matricolaRt
  });

  if (error) {
    console.error("Errore salvataggio scontrino Supabase:", error);
    const messaggiErrore = {
      "scontrino duplicato: stessa matricola, numero documento, data e importo":
        "Questo scontrino risulta gia' caricato (stessa matricola, numero documento, data e importo).",
      "matricola registratore non riconosciuta per questo esercizio":
        "Matricola non riconosciuta: controlla di averla copiata correttamente dallo scontrino.",
      "data scontrino precedente all''avvio del programma":
        "La data dello scontrino e' precedente all'avvio del programma."
    };
    const messaggioLeggibile = messaggiErrore[error.message] || error.message;
    return { ok: false, message: messaggioLeggibile };
  }
```

- [ ] **Step 3: Verifica manuale**

Come cliente, carica uno scontrino con matricola corretta: deve andare a buon fine. Ricarica **lo stesso** scontrino (stessa matricola, stesso numero documento, stessa data, stesso importo): deve comparire l'errore "Questo scontrino risulta gia' caricato...". Prova con una matricola inventata: deve comparire "Matricola non riconosciuta...".

- [ ] **Step 4: Commit**

```bash
git add index.html app.js
git commit -m "v54: campo matricola RT nel caricamento scontrino, errori anti-duplicato"
```

---

## Fase B — Intervento 3: limiti di plausibilità configurabili per esercizio

### Task 3: Schema SQL — tabella limiti, colonna motivo_sospensione, vista revisione, funzione aggiornata

**Rischio:** riscrive di nuovo `registra_scontrino_pilot` (Task 1 l'aveva già toccata). Stesso principio: nessun parametro tolto, nessun parametro nuovo aggiunto in questa fase (i limiti si leggono lato server dal `bar_id` già passato, il client non deve sapere nulla di nuovo). **Rollback:** ri-applica `docs/supabase-anti-duplicato-scontrini.sql` per tornare alla versione del Task 1.

**Files:**
- Create: `docs/supabase-limiti-plausibilita-bar.sql`

**Interfaces:**
- Produce: tabella `limiti_bar`; colonna `scontrini.motivo_sospensione`; vista `scontrini_revisione_manuale_pilot`. Usata da Task 4 (frontend pannello SQ).

- [ ] **Step 1: Scrivere il file SQL completo**

```sql
-- docs/supabase-limiti-plausibilita-bar.sql
-- Fase B — Intervento 3: limiti di plausibilita' configurabili per esercizio.
-- Eseguire in Supabase SQL Editor dopo docs/supabase-anti-duplicato-scontrini.sql.
--
-- Obiettivo:
-- 1. tetto giornaliero di scontrini per cliente (oltre: rifiutato subito, non consuma un ID);
-- 2. importo massimo oltre il quale lo scontrino va in coda di revisione manuale (non rifiutato);
-- 3. soglie per esercizio, non costanti globali.

-- 1. Configurazione per bar. bar_id e' chiave primaria: un solo set di limiti per esercizio.
CREATE TABLE IF NOT EXISTS public.limiti_bar (
  bar_id UUID PRIMARY KEY REFERENCES public.bar(id) ON DELETE CASCADE,
  tetto_giornaliero_scontrini INTEGER NOT NULL DEFAULT 3 CHECK (tetto_giornaliero_scontrini > 0),
  soglia_revisione_manuale NUMERIC(10,2) NOT NULL DEFAULT 30 CHECK (soglia_revisione_manuale > 0),
  sospensione_giorni INTEGER NOT NULL DEFAULT 12 CHECK (sospensione_giorni BETWEEN 1 AND 30),
  codice_banco_finestra_secondi INTEGER NOT NULL DEFAULT 90 CHECK (codice_banco_finestra_secondi >= 30),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

DROP TRIGGER IF EXISTS trg_limiti_bar_updated_at ON public.limiti_bar;
CREATE TRIGGER trg_limiti_bar_updated_at
BEFORE UPDATE ON public.limiti_bar
FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

ALTER TABLE public.limiti_bar ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "limiti_bar_select_autenticati" ON public.limiti_bar;
CREATE POLICY "limiti_bar_select_autenticati"
ON public.limiti_bar
FOR SELECT
TO authenticated
USING (true);

DROP POLICY IF EXISTS "limiti_bar_gestione_admin_sq" ON public.limiti_bar;
CREATE POLICY "limiti_bar_gestione_admin_sq"
ON public.limiti_bar
FOR ALL
TO authenticated
USING (public.e_admin() OR public.e_salute_quotidiana())
WITH CHECK (public.e_admin() OR public.e_salute_quotidiana());

GRANT SELECT ON public.limiti_bar TO authenticated;
REVOKE ALL ON public.limiti_bar FROM anon;

INSERT INTO public.limiti_bar (bar_id)
SELECT id FROM public.bar WHERE nome = 'Bar pilota Francofonte'
ON CONFLICT (bar_id) DO NOTHING;

-- 2. Motivo per cui uno scontrino resta in_verifica, distinto dal generico controllo OCR.
--    Valore ammesso in questa fase: solo 'importo_oltre_soglia' (la Fase C ne aggiunge un secondo).
ALTER TABLE public.scontrini
  ADD COLUMN IF NOT EXISTS motivo_sospensione TEXT;

ALTER TABLE public.scontrini
  DROP CONSTRAINT IF EXISTS scontrini_motivo_sospensione_check;
ALTER TABLE public.scontrini
  ADD CONSTRAINT scontrini_motivo_sospensione_check
  CHECK (motivo_sospensione IS NULL OR motivo_sospensione IN ('importo_oltre_soglia'));

-- 3. Coda di revisione manuale per Salute Quotidiana: solo scontrini sospesi per importo.
DROP VIEW IF EXISTS public.scontrini_revisione_manuale_pilot;
CREATE VIEW public.scontrini_revisione_manuale_pilot
WITH (security_invoker = true)
AS
SELECT
  s.id,
  s.cliente_id,
  c.codice_cliente,
  c.nome,
  c.cognome,
  s.data_scontrino,
  s.numero_documento,
  s.importo_dichiarato,
  s.credito_generato,
  s.created_at
FROM public.scontrini s
JOIN public.clienti c ON c.id = s.cliente_id
WHERE s.stato = 'in_verifica'
  AND s.motivo_sospensione = 'importo_oltre_soglia'
ORDER BY s.created_at DESC;

GRANT SELECT ON public.scontrini_revisione_manuale_pilot TO authenticated;
REVOKE ALL ON public.scontrini_revisione_manuale_pilot FROM anon;

-- 4. Funzione aggiornata: stessa firma del Task 1 (16 parametri), nessun parametro nuovo.
--    I limiti si leggono da limiti_bar usando p_bar_id gia' passato dal client.
CREATE OR REPLACE FUNCTION public.registra_scontrino_pilot(
  p_id                 UUID,
  p_cliente_id         UUID,
  p_bar_id             UUID,
  p_testo_ocr          TEXT,
  p_data_scontrino     DATE,
  p_ora_scontrino      TIME,
  p_numero_documento   TEXT,
  p_importo_dichiarato NUMERIC,
  p_importo_ocr        NUMERIC,
  p_importo_verificato NUMERIC,
  p_credito_generato   NUMERIC,
  p_stato              TEXT,
  p_avviso_duplicato   BOOLEAN,
  p_motivo_controllo   TEXT,
  p_operatore_label    TEXT DEFAULT NULL,
  p_matricola_rt       TEXT DEFAULT NULL
)
RETURNS UUID
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  nuovo_id UUID;
  profilo_corrente_id UUID;
  documento_normalizzato TEXT;
  matricola_normalizzata TEXT;
  limiti RECORD;
  scontrini_oggi INTEGER;
  stato_finale TEXT;
  motivo_sospensione_finale TEXT;
  PROGRAM_START_DATE CONSTANT DATE := '2026-07-04';
BEGIN
  IF auth.uid() IS NULL THEN
    RAISE EXCEPTION 'accesso richiesto';
  END IF;

  IF p_cliente_id IS NULL THEN
    RAISE EXCEPTION 'cliente mancante';
  END IF;

  IF p_bar_id IS NULL THEN
    RAISE EXCEPTION 'bar mancante';
  END IF;

  SELECT p.id
  INTO profilo_corrente_id
  FROM public.profili p
  WHERE p.auth_user_id = auth.uid()
  LIMIT 1;

  IF profilo_corrente_id IS NULL THEN
    RAISE EXCEPTION 'profilo non trovato';
  END IF;

  IF NOT (
    public.e_admin()
    OR public.e_salute_quotidiana()
    OR public.e_bar()
    OR EXISTS (
      SELECT 1
      FROM public.clienti c
      WHERE c.id = p_cliente_id
        AND c.profilo_id = profilo_corrente_id
        AND c.stato = 'attivo'
    )
  ) THEN
    RAISE EXCEPTION 'cliente non autorizzato';
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM public.clienti c
    WHERE c.id = p_cliente_id AND c.stato = 'attivo'
  ) THEN
    RAISE EXCEPTION 'cliente non valido o non attivo';
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM public.bar b
    WHERE b.id = p_bar_id AND b.attivo = true
  ) THEN
    RAISE EXCEPTION 'bar non valido o non attivo';
  END IF;

  IF p_importo_dichiarato IS NULL OR p_importo_dichiarato <= 0 THEN
    RAISE EXCEPTION 'importo non valido';
  END IF;

  IF p_credito_generato IS NULL OR p_credito_generato < 0 THEN
    RAISE EXCEPTION 'credito non valido';
  END IF;

  IF p_data_scontrino IS NULL THEN
    RAISE EXCEPTION 'data scontrino mancante';
  END IF;

  IF p_data_scontrino > CURRENT_DATE THEN
    RAISE EXCEPTION 'data scontrino futura';
  END IF;

  IF p_data_scontrino < PROGRAM_START_DATE THEN
    RAISE EXCEPTION 'data scontrino precedente all''avvio del programma';
  END IF;

  documento_normalizzato := NULLIF(TRIM(COALESCE(p_numero_documento, '')), '');
  IF documento_normalizzato IS NULL THEN
    RAISE EXCEPTION 'numero documento mancante';
  END IF;

  matricola_normalizzata := UPPER(NULLIF(TRIM(COALESCE(p_matricola_rt, '')), ''));

  IF matricola_normalizzata IS NOT NULL THEN
    IF NOT EXISTS (
      SELECT 1 FROM public.registratori_telematici rt
      WHERE rt.bar_id = p_bar_id
        AND UPPER(rt.matricola) = matricola_normalizzata
        AND rt.attivo = true
    ) THEN
      RAISE EXCEPTION 'matricola registratore non riconosciuta per questo esercizio';
    END IF;

    IF EXISTS (
      SELECT 1 FROM public.scontrini s
      WHERE UPPER(s.matricola_rt) = matricola_normalizzata
        AND LOWER(TRIM(COALESCE(s.numero_documento, ''))) = LOWER(documento_normalizzato)
        AND s.data_scontrino = p_data_scontrino
        AND ROUND(s.importo_dichiarato::numeric, 2) = ROUND(p_importo_dichiarato::numeric, 2)
        AND s.stato <> 'rifiutato'
    ) THEN
      RAISE EXCEPTION 'scontrino duplicato: stessa matricola, numero documento, data e importo';
    END IF;
  END IF;

  SELECT * INTO limiti FROM public.limiti_bar WHERE bar_id = p_bar_id;
  IF NOT FOUND THEN
    -- Nessuna riga di configurazione per questo bar: uso i default di progetto.
    limiti.tetto_giornaliero_scontrini := 3;
    limiti.soglia_revisione_manuale := 30;
  END IF;

  SELECT count(*) INTO scontrini_oggi
  FROM public.scontrini s
  WHERE s.cliente_id = p_cliente_id
    AND s.bar_id = p_bar_id
    AND s.data_scontrino = p_data_scontrino
    AND s.stato <> 'rifiutato';

  IF scontrini_oggi >= limiti.tetto_giornaliero_scontrini THEN
    RAISE EXCEPTION 'tetto giornaliero di scontrini raggiunto per questo cliente';
  END IF;

  IF p_importo_dichiarato > limiti.soglia_revisione_manuale THEN
    stato_finale := 'in_verifica';
    motivo_sospensione_finale := 'importo_oltre_soglia';
  ELSE
    stato_finale := p_stato;
    motivo_sospensione_finale := NULL;
  END IF;

  INSERT INTO public.scontrini (
    id, cliente_id, bar_id, testo_ocr,
    data_scontrino, ora_scontrino, numero_documento,
    importo_dichiarato, importo_ocr, importo_verificato,
    credito_generato, stato, avviso_duplicato,
    motivo_rifiuto, operatore_label, matricola_rt, motivo_sospensione
  )
  VALUES (
    COALESCE(p_id, gen_random_uuid()),
    p_cliente_id,
    p_bar_id,
    p_testo_ocr,
    p_data_scontrino,
    p_ora_scontrino,
    documento_normalizzato,
    p_importo_dichiarato,
    p_importo_ocr,
    p_importo_verificato,
    p_credito_generato,
    stato_finale,
    COALESCE(p_avviso_duplicato, false),
    NULLIF(TRIM(COALESCE(p_motivo_controllo, '')), ''),
    NULLIF(TRIM(COALESCE(p_operatore_label, '')), ''),
    matricola_normalizzata,
    motivo_sospensione_finale
  )
  RETURNING id INTO nuovo_id;

  RETURN nuovo_id;
END;
$$;

REVOKE ALL ON FUNCTION public.registra_scontrino_pilot(
  uuid, uuid, uuid, text, date, time, text,
  numeric, numeric, numeric, numeric, text, boolean, text, text, text
) FROM anon;

GRANT EXECUTE ON FUNCTION public.registra_scontrino_pilot(
  uuid, uuid, uuid, text, date, time, text,
  numeric, numeric, numeric, numeric, text, boolean, text, text, text
) TO authenticated;

NOTIFY pgrst, 'reload schema';
```

Nota: la colonna `motivo_sospensione` aggiunta qui viene letta anche da `motivo_rifiuto`/UI esistente? No — resta un campo nuovo, separato da `motivo_rifiuto` (che continua a significare "perche' e' stato rifiutato"). `motivo_sospensione` significa "perche' e' in sospeso pur non essendo rifiutato".

- [ ] **Step 2: Angelo applica il file e conferma/aggiusta i parametri**

Incolla ed esegui `docs/supabase-limiti-plausibilita-bar.sql`. Poi, se vuoi valori diversi dai default (Domanda aperta 2), esegui:

```sql
UPDATE public.limiti_bar
SET tetto_giornaliero_scontrini = 3,       -- cambia se vuoi un altro numero
    soglia_revisione_manuale = 30          -- cambia se vuoi un'altra soglia in euro
WHERE bar_id = (SELECT id FROM public.bar WHERE nome = 'Bar pilota Francofonte');
```

- [ ] **Step 3: Verifica manuale su Supabase**

```sql
SELECT * FROM public.limiti_bar;
```
Atteso: una riga con i valori confermati.

```sql
SELECT * FROM public.scontrini_revisione_manuale_pilot;
```
Atteso: zero righe (nessuno scontrino sopra soglia ancora caricato).

- [ ] **Step 4: Commit**

```bash
git add docs/supabase-limiti-plausibilita-bar.sql
git commit -m "v54: limiti di plausibilita per esercizio — tetto giornaliero e soglia revisione"
```

---

### Task 4: Frontend — pannello revisione manuale per Salute Quotidiana

**Files:**
- Modify: `index.html` — nuovo panel dentro `<section class="tab-panel" id="salute">`
- Modify: `app.js` — `el` refs, `loadRevisioneManuale`, `renderRevisioneManuale`, wiring, mappatura errore tetto giornaliero

**Interfaces:**
- Consuma: vista `scontrini_revisione_manuale_pilot` (Task 3), RPC `aggiorna_scontrino_pilot` (esistente, invariata).

- [ ] **Step 1: HTML — nuovo panel**

In `index.html`, dentro `<section class="tab-panel" id="salute">`, prima della chiusura della sezione (stesso punto usato dal piano "Lista dei Silenziosi" per il proprio panel — subito dopo quel blocco, se già presente, altrimenti dopo il panel "Registra prestazione"):

```html
          <section class="panel">
            <div class="section-heading">
              <p class="eyebrow">Controllo SQ</p>
              <h2>Scontrini in revisione manuale</h2>
            </div>
            <div class="notice">
              Scontrini con importo oltre la soglia configurata per l'esercizio: non sono rifiutati automaticamente,
              vanno confermati o rifiutati a mano.
            </div>
            <div class="mini-list" id="revisioneManualeList"></div>
          </section>
```

- [ ] **Step 2: `app.js` — `el` refs**

Nell'oggetto `el`:
```javascript
  revisioneManualeList: document.querySelector("#revisioneManualeList"),
```

- [ ] **Step 3: `app.js` — caricamento e rendering**

Subito dopo `mapSupabaseReceiptStatus` (circa riga 701):

```javascript
async function loadRevisioneManuale() {
  if (!supabaseClient) return;

  const { data, error } = await supabaseClient
    .from("scontrini_revisione_manuale_pilot")
    .select("id,cliente_id,codice_cliente,nome,cognome,data_scontrino,numero_documento,importo_dichiarato,credito_generato,created_at");

  if (error) {
    console.error("Errore caricamento revisione manuale:", error);
    return;
  }

  renderRevisioneManuale(data || []);
}

function renderRevisioneManuale(righe) {
  if (!el.revisioneManualeList) return;

  el.revisioneManualeList.innerHTML = righe.length
    ? righe.map((r) => `
        <div class="mini-list__row">
          <span>${escapeHtml(r.nome)} ${escapeHtml(r.cognome)} (${escapeHtml(r.codice_cliente)}) — ${r.data_scontrino} — doc. ${escapeHtml(r.numero_documento || "-")}</span>
          <strong>${formatMoney(r.importo_dichiarato)} euro — credito ${formatMoney(r.credito_generato)} euro SQ</strong>
          <div class="mini-list__actions">
            <button type="button" class="secondary small" data-revisione-conferma="${r.id}" data-revisione-importo="${r.importo_dichiarato}" data-revisione-credito="${r.credito_generato}">Conferma</button>
            <button type="button" class="secondary small" data-revisione-rifiuta="${r.id}">Rifiuta</button>
          </div>
        </div>
      `).join("")
    : `<p class="form-status">Nessuno scontrino in revisione manuale.</p>`;
}

async function handleRevisioneManualeClick(event) {
  const confermaId = event.target.dataset.revisioneConferma;
  const rifiutaId = event.target.dataset.revisioneRifiuta;
  if (!confermaId && !rifiutaId) return;

  if (!supabaseClient) return;

  if (confermaId) {
    const importo = Number(event.target.dataset.revisioneImporto);
    const credito = Number(event.target.dataset.revisioneCredito);
    const { error } = await supabaseClient.rpc("aggiorna_scontrino_pilot", {
      p_id: confermaId,
      p_stato: "confermato",
      p_importo_dichiarato: importo,
      p_importo_verificato: importo,
      p_credito_generato: credito,
      p_motivo_controllo: "Confermato manualmente dopo revisione importo elevato."
    });
    if (error) {
      console.error("Errore conferma revisione manuale:", error);
      showToast(`Errore: ${error.message}`);
      return;
    }
    showToast("Scontrino confermato.");
  }

  if (rifiutaId) {
    const { error } = await supabaseClient.rpc("aggiorna_scontrino_pilot", {
      p_id: rifiutaId,
      p_stato: "rifiutato",
      p_importo_dichiarato: null,
      p_importo_verificato: null,
      p_credito_generato: 0,
      p_motivo_controllo: "Rifiutato dopo revisione manuale importo elevato."
    });
    if (error) {
      console.error("Errore rifiuto revisione manuale:", error);
      showToast(`Errore: ${error.message}`);
      return;
    }
    showToast("Scontrino rifiutato.");
  }

  loadRevisioneManuale();
  loadPilotReceiptsFromSupabase();
  loadPilotBalancesFromSupabase();
}
```

- [ ] **Step 4: `app.js` — wiring e caricamento iniziale, mappatura errore tetto giornaliero**

Vicino al wiring esistente (circa riga 940, dove viene collegato `el.receiptForm`):
```javascript
  if (el.revisioneManualeList) el.revisioneManualeList.addEventListener("click", handleRevisioneManualeClick);
```

Nel punto in cui vengono lanciati i caricamenti iniziali per il ruolo `salute_quotidiana` (dove viene chiamata `loadFondoSilenziosi()` se il piano "Lista dei Silenziosi" è già stato eseguito, altrimenti vicino a `loadCreditRequestsFromSupabase()`), aggiungi:
```javascript
  loadRevisioneManuale();
```

Nella mappa `messaggiErrore` dentro `saveReceiptToSupabase` (aggiunta nel Task 2), aggiungi una voce:
```javascript
    const messaggiErrore = {
      "scontrino duplicato: stessa matricola, numero documento, data e importo":
        "Questo scontrino risulta gia' caricato (stessa matricola, numero documento, data e importo).",
      "matricola registratore non riconosciuta per questo esercizio":
        "Matricola non riconosciuta: controlla di averla copiata correttamente dallo scontrino.",
      "data scontrino precedente all''avvio del programma":
        "La data dello scontrino e' precedente all'avvio del programma.",
      "tetto giornaliero di scontrini raggiunto per questo cliente":
        "Hai raggiunto il numero massimo di scontrini caricabili oggi. Riprova domani."
    };
```

- [ ] **Step 5: Verifica manuale end-to-end**

Come cliente, carica uno scontrino con importo sopra la soglia configurata (es. 35€ se la soglia è 30€). Come Salute Quotidiana, apri il tab "Salute Quotidiana": deve comparire nel panel "Scontrini in revisione manuale". Premi "Conferma": deve sparire dalla lista e il saldo confermato del cliente deve aumentare. Ripeti caricando un altro scontrino sopra soglia e premi "Rifiuta": deve sparire senza toccare il saldo. Poi, come lo stesso cliente, carica scontrini fino a superare il tetto giornaliero configurato: l'ultimo tentativo deve mostrare "Hai raggiunto il numero massimo di scontrini caricabili oggi...".

- [ ] **Step 6: Commit**

```bash
git add index.html app.js
git commit -m "v54: pannello revisione manuale scontrini oltre soglia"
```

---

## Fase C — Intervento 1: inversione del QR

### Task 5: Schema SQL — dispositivo banco, codice rotante, funzione finale

**Rischio:** riscrive `registra_scontrino_pilot` una terza volta (aggiunge `p_codice_banco` in coda, `DEFAULT NULL` — se il frontend non lo passa ancora, il comportamento è "nessun codice", quindi lo scontrino va sempre in sospeso: è per questo che i Task 6-8 (frontend) vanno applicati subito dopo, nella stessa sessione di lavoro, altrimenti tutti i nuovi scontrini finiscono sospesi finché il frontend non manda il codice). Allarga il `CHECK` su `motivo_sospensione` (aggiunge un valore, non ne toglie) e su `stato` (aggiunge `'scaduto'`, non tocca gli altri tre). **Rollback:** ri-applica `docs/supabase-limiti-plausibilita-bar.sql` per tornare alla versione del Task 3; le nuove tabelle/colonne restano innocue.

**Files:**
- Create: `docs/supabase-inversione-qr-banco.sql`

**Interfaces:**
- Produce: tabella `banco_dispositivi`; colonne `scontrini.sospeso_scaduto_il`, `scontrini.attivato_codice_banco_at`; RPC `richiedi_codice_banco_pilot(p_banco_token)` (anon), `attiva_scontrino_con_codice_banco_pilot(p_scontrino_id, p_codice)` (authenticated), `crea_dispositivo_banco_pilot(p_bar_id)` (admin/SQ), `scadi_scontrini_sospesi_pilot()` (admin/SQ + cron); vista `scontrini_app_pilot` estesa. Usata da Task 6 (`banco.html`), Task 7-8 (frontend cliente).

- [ ] **Step 1: Scrivere il file SQL completo**

```sql
-- docs/supabase-inversione-qr-banco.sql
-- Fase C — Intervento 1: inversione del QR. Il banco espone un codice a 6 cifre rinnovato
-- ogni 90 secondi (calcolato server-side via HMAC, il segreto non lascia mai il database).
-- Il cliente inquadra o digita il codice mentre carica lo scontrino: se valido, il credito e'
-- confermato subito. Se manca (offline, caricamento da casa), il credito resta visibile ma
-- non spendibile per un numero di giorni configurabile, poi decade.
--
-- Eseguire in Supabase SQL Editor dopo docs/supabase-limiti-plausibilita-bar.sql.

-- 1. Dispositivo banco: un bar puo' avere un solo dispositivo attivo alla volta.
--    Il segreto (bytea) non e' mai leggibile da anon/authenticated: nessuna policy SELECT
--    lo espone, solo le funzioni SECURITY DEFINER di questo file lo leggono internamente.
CREATE TABLE IF NOT EXISTS public.banco_dispositivi (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  bar_id UUID NOT NULL REFERENCES public.bar(id) ON DELETE CASCADE,
  banco_token UUID NOT NULL UNIQUE DEFAULT gen_random_uuid(),
  secret BYTEA NOT NULL DEFAULT gen_random_bytes(32),
  attivo BOOLEAN NOT NULL DEFAULT true,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE public.banco_dispositivi ENABLE ROW LEVEL SECURITY;

-- Nessuna policy SELECT per anon/authenticated: la tabella si legge SOLO dall'interno
-- delle funzioni SECURITY DEFINER sotto, mai direttamente dal client.
DROP POLICY IF EXISTS "banco_dispositivi_gestione_admin_sq" ON public.banco_dispositivi;
CREATE POLICY "banco_dispositivi_gestione_admin_sq"
ON public.banco_dispositivi
FOR ALL
TO authenticated
USING (public.e_admin() OR public.e_salute_quotidiana())
WITH CHECK (public.e_admin() OR public.e_salute_quotidiana());

REVOKE ALL ON public.banco_dispositivi FROM anon, authenticated;

-- 2. Colonne aggiuntive su scontrini per il ciclo di vita del credito sospeso.
ALTER TABLE public.scontrini
  ADD COLUMN IF NOT EXISTS sospeso_scaduto_il TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS attivato_codice_banco_at TIMESTAMPTZ;

-- 3. Allargamento CHECK su motivo_sospensione: aggiunge 'codice_banco_mancante'
--    senza togliere 'importo_oltre_soglia' (Task 3).
ALTER TABLE public.scontrini
  DROP CONSTRAINT IF EXISTS scontrini_motivo_sospensione_check;
ALTER TABLE public.scontrini
  ADD CONSTRAINT scontrini_motivo_sospensione_check
  CHECK (motivo_sospensione IS NULL OR motivo_sospensione IN ('importo_oltre_soglia', 'codice_banco_mancante'));

-- 4. Allargamento CHECK su stato: aggiunge 'scaduto' ai tre valori esistenti.
ALTER TABLE public.scontrini
  DROP CONSTRAINT IF EXISTS scontrini_stato_check;
ALTER TABLE public.scontrini
  ADD CONSTRAINT scontrini_stato_check
  CHECK (stato IN ('in_verifica', 'confermato', 'rifiutato', 'scaduto'));

-- 5. Funzione interna (NON concessa a nessuno: ne' anon ne' authenticated hanno EXECUTE).
--    Postgres concede EXECUTE a PUBLIC per default sulle nuove funzioni: la REVOKE esplicita
--    e' cio' che la rende davvero non richiamabile dal client, altrimenti sarebbe un oracolo
--    per un attacco a forza bruta sulle 6 cifre.
CREATE OR REPLACE FUNCTION public.verifica_codice_banco_interna(p_bar_id UUID, p_codice TEXT)
RETURNS BOOLEAN
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  dispositivo RECORD;
  finestra_secondi INTEGER := 90;
  finestra_corrente BIGINT;
  codice_pulito TEXT;
BEGIN
  codice_pulito := NULLIF(TRIM(COALESCE(p_codice, '')), '');
  IF codice_pulito IS NULL THEN
    RETURN false;
  END IF;

  SELECT * INTO dispositivo
  FROM public.banco_dispositivi
  WHERE bar_id = p_bar_id AND attivo = true
  LIMIT 1;

  IF NOT FOUND THEN
    RETURN false;
  END IF;

  SELECT codice_banco_finestra_secondi INTO finestra_secondi
  FROM public.limiti_bar WHERE bar_id = p_bar_id;
  finestra_secondi := COALESCE(finestra_secondi, 90);

  finestra_corrente := FLOOR(EXTRACT(EPOCH FROM NOW()) / finestra_secondi)::BIGINT;

  -- Tolleranza sulla finestra precedente per assorbire la latenza tra la lettura
  -- del codice al banco e l'invio dal cliente.
  RETURN codice_pulito IN (
    LPAD((('x' || ENCODE(SUBSTRING(HMAC(dispositivo.bar_id::text || ':' || finestra_corrente::text, dispositivo.secret, 'sha256') FROM 1 FOR 4), 'hex'))::BIT(32)::BIGINT % 1000000)::TEXT, 6, '0'),
    LPAD((('x' || ENCODE(SUBSTRING(HMAC(dispositivo.bar_id::text || ':' || (finestra_corrente - 1)::text, dispositivo.secret, 'sha256') FROM 1 FOR 4), 'hex'))::BIT(32)::BIGINT % 1000000)::TEXT, 6, '0')
  );
END;
$$;

REVOKE ALL ON FUNCTION public.verifica_codice_banco_interna(uuid, text) FROM PUBLIC;

-- 6. RPC pubblica per il dispositivo banco (nessun login): restituisce solo il codice
--    attuale e i secondi rimanenti, mai il segreto.
CREATE OR REPLACE FUNCTION public.richiedi_codice_banco_pilot(p_banco_token UUID)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  dispositivo RECORD;
  bar_nome TEXT;
  finestra_secondi INTEGER;
  finestra_corrente BIGINT;
  codice_attuale TEXT;
  secondi_rimanenti INTEGER;
BEGIN
  SELECT bd.*, b.nome AS nome_bar INTO dispositivo
  FROM public.banco_dispositivi bd
  JOIN public.bar b ON b.id = bd.bar_id
  WHERE bd.banco_token = p_banco_token AND bd.attivo = true
  LIMIT 1;

  IF NOT FOUND THEN
    RETURN jsonb_build_object('ok', false, 'errore', 'dispositivo_non_trovato');
  END IF;

  SELECT codice_banco_finestra_secondi INTO finestra_secondi
  FROM public.limiti_bar WHERE bar_id = dispositivo.bar_id;
  finestra_secondi := COALESCE(finestra_secondi, 90);

  finestra_corrente := FLOOR(EXTRACT(EPOCH FROM NOW()) / finestra_secondi)::BIGINT;
  codice_attuale := LPAD((('x' || ENCODE(SUBSTRING(HMAC(dispositivo.bar_id::text || ':' || finestra_corrente::text, dispositivo.secret, 'sha256') FROM 1 FOR 4), 'hex'))::BIT(32)::BIGINT % 1000000)::TEXT, 6, '0');
  secondi_rimanenti := finestra_secondi - (EXTRACT(EPOCH FROM NOW())::BIGINT % finestra_secondi);

  RETURN jsonb_build_object(
    'ok', true,
    'bar_nome', dispositivo.nome_bar,
    'codice', codice_attuale,
    'secondi_rimanenti', secondi_rimanenti,
    'finestra_secondi', finestra_secondi
  );
END;
$$;

GRANT EXECUTE ON FUNCTION public.richiedi_codice_banco_pilot(uuid) TO anon, authenticated;

-- 7. RPC admin/SQ per generare un dispositivo banco per un bar (una tantum per esercizio).
CREATE OR REPLACE FUNCTION public.crea_dispositivo_banco_pilot(p_bar_id UUID)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  nuovo_token UUID;
BEGIN
  IF NOT (public.e_admin() OR public.e_salute_quotidiana()) THEN
    RAISE EXCEPTION 'ruolo non autorizzato';
  END IF;

  UPDATE public.banco_dispositivi SET attivo = false WHERE bar_id = p_bar_id AND attivo = true;

  INSERT INTO public.banco_dispositivi (bar_id)
  VALUES (p_bar_id)
  RETURNING banco_token INTO nuovo_token;

  RETURN jsonb_build_object('ok', true, 'banco_token', nuovo_token);
END;
$$;

GRANT EXECUTE ON FUNCTION public.crea_dispositivo_banco_pilot(uuid) TO authenticated;

-- 8. RPC per attivare in un secondo momento uno scontrino rimasto sospeso (il cliente torna
--    al bar dopo aver caricato lo scontrino da casa).
CREATE OR REPLACE FUNCTION public.attiva_scontrino_con_codice_banco_pilot(
  p_scontrino_id UUID,
  p_codice TEXT
)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  scontrino RECORD;
  profilo_corrente_id UUID;
BEGIN
  IF auth.uid() IS NULL THEN
    RAISE EXCEPTION 'accesso richiesto';
  END IF;

  SELECT p.id INTO profilo_corrente_id
  FROM public.profili p WHERE p.auth_user_id = auth.uid() LIMIT 1;

  SELECT s.* INTO scontrino
  FROM public.scontrini s
  WHERE s.id = p_scontrino_id;

  IF NOT FOUND THEN
    RETURN jsonb_build_object('ok', false, 'errore', 'scontrino_non_trovato');
  END IF;

  IF NOT (
    public.e_admin()
    OR public.e_salute_quotidiana()
    OR EXISTS (
      SELECT 1 FROM public.clienti c
      WHERE c.id = scontrino.cliente_id AND c.profilo_id = profilo_corrente_id
    )
  ) THEN
    RAISE EXCEPTION 'non autorizzato ad attivare questo scontrino';
  END IF;

  IF scontrino.stato <> 'in_verifica' OR scontrino.motivo_sospensione <> 'codice_banco_mancante' THEN
    RETURN jsonb_build_object('ok', false, 'errore', 'non_attivabile');
  END IF;

  IF scontrino.sospeso_scaduto_il IS NOT NULL AND scontrino.sospeso_scaduto_il < NOW() THEN
    RETURN jsonb_build_object('ok', false, 'errore', 'scaduto');
  END IF;

  IF NOT public.verifica_codice_banco_interna(scontrino.bar_id, p_codice) THEN
    RETURN jsonb_build_object('ok', false, 'errore', 'codice_non_valido');
  END IF;

  UPDATE public.scontrini
  SET stato = 'confermato',
      motivo_sospensione = NULL,
      sospeso_scaduto_il = NULL,
      attivato_codice_banco_at = NOW(),
      verificato_at = NOW()
  WHERE id = p_scontrino_id;

  RETURN jsonb_build_object('ok', true);
END;
$$;

GRANT EXECUTE ON FUNCTION public.attiva_scontrino_con_codice_banco_pilot(uuid, text) TO authenticated;

-- 9. Decadimento: scontrini sospesi per mancanza di codice banco, mai attivati entro la
--    finestra configurata, passano a 'scaduto'. Pensata per essere lanciata da pg_cron
--    (Task 10) o a mano da Angelo come fallback.
CREATE OR REPLACE FUNCTION public.scadi_scontrini_sospesi_pilot()
RETURNS INTEGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  righe_aggiornate INTEGER;
BEGIN
  UPDATE public.scontrini
  SET stato = 'scaduto'
  WHERE stato = 'in_verifica'
    AND motivo_sospensione = 'codice_banco_mancante'
    AND sospeso_scaduto_il IS NOT NULL
    AND sospeso_scaduto_il < NOW();

  GET DIAGNOSTICS righe_aggiornate = ROW_COUNT;
  RETURN righe_aggiornate;
END;
$$;

GRANT EXECUTE ON FUNCTION public.scadi_scontrini_sospesi_pilot() TO authenticated;

-- 10. Vista scontrini_app_pilot estesa con i campi necessari al cliente per capire
--     se il proprio credito e' sospeso e quando scade.
DROP VIEW IF EXISTS public.scontrini_app_pilot;
CREATE VIEW public.scontrini_app_pilot
WITH (security_invoker = true)
AS
SELECT
  s.id,
  s.cliente_id,
  s.testo_ocr,
  s.data_scontrino,
  s.ora_scontrino,
  s.numero_documento,
  s.importo_dichiarato,
  s.importo_ocr,
  s.credito_generato,
  s.stato,
  s.avviso_duplicato,
  s.motivo_rifiuto,
  s.motivo_sospensione,
  s.sospeso_scaduto_il,
  s.created_at,
  s.updated_at
FROM public.scontrini s;

GRANT SELECT ON public.scontrini_app_pilot TO authenticated;
REVOKE ALL ON public.scontrini_app_pilot FROM anon;

-- 11. Funzione finale registra_scontrino_pilot: 17 parametri (16 esistenti + p_codice_banco
--     in coda con DEFAULT NULL). p_stato passato dal client ora viene ignorato quando
--     l'importo e' entro soglia: lo stato lo decide sempre il server in base a duplicato,
--     tetto giornaliero, soglia importo e codice banco — mai il client.
CREATE OR REPLACE FUNCTION public.registra_scontrino_pilot(
  p_id                 UUID,
  p_cliente_id         UUID,
  p_bar_id             UUID,
  p_testo_ocr          TEXT,
  p_data_scontrino     DATE,
  p_ora_scontrino      TIME,
  p_numero_documento   TEXT,
  p_importo_dichiarato NUMERIC,
  p_importo_ocr        NUMERIC,
  p_importo_verificato NUMERIC,
  p_credito_generato   NUMERIC,
  p_stato              TEXT,
  p_avviso_duplicato   BOOLEAN,
  p_motivo_controllo   TEXT,
  p_operatore_label    TEXT DEFAULT NULL,
  p_matricola_rt       TEXT DEFAULT NULL,
  p_codice_banco       TEXT DEFAULT NULL
)
RETURNS UUID
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  nuovo_id UUID;
  profilo_corrente_id UUID;
  documento_normalizzato TEXT;
  matricola_normalizzata TEXT;
  limiti RECORD;
  scontrini_oggi INTEGER;
  stato_finale TEXT;
  motivo_sospensione_finale TEXT;
  scadenza_sospensione TIMESTAMPTZ;
  PROGRAM_START_DATE CONSTANT DATE := '2026-07-04';
BEGIN
  IF auth.uid() IS NULL THEN
    RAISE EXCEPTION 'accesso richiesto';
  END IF;

  IF p_cliente_id IS NULL THEN
    RAISE EXCEPTION 'cliente mancante';
  END IF;

  IF p_bar_id IS NULL THEN
    RAISE EXCEPTION 'bar mancante';
  END IF;

  SELECT p.id
  INTO profilo_corrente_id
  FROM public.profili p
  WHERE p.auth_user_id = auth.uid()
  LIMIT 1;

  IF profilo_corrente_id IS NULL THEN
    RAISE EXCEPTION 'profilo non trovato';
  END IF;

  IF NOT (
    public.e_admin()
    OR public.e_salute_quotidiana()
    OR public.e_bar()
    OR EXISTS (
      SELECT 1
      FROM public.clienti c
      WHERE c.id = p_cliente_id
        AND c.profilo_id = profilo_corrente_id
        AND c.stato = 'attivo'
    )
  ) THEN
    RAISE EXCEPTION 'cliente non autorizzato';
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM public.clienti c
    WHERE c.id = p_cliente_id AND c.stato = 'attivo'
  ) THEN
    RAISE EXCEPTION 'cliente non valido o non attivo';
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM public.bar b
    WHERE b.id = p_bar_id AND b.attivo = true
  ) THEN
    RAISE EXCEPTION 'bar non valido o non attivo';
  END IF;

  IF p_importo_dichiarato IS NULL OR p_importo_dichiarato <= 0 THEN
    RAISE EXCEPTION 'importo non valido';
  END IF;

  IF p_credito_generato IS NULL OR p_credito_generato < 0 THEN
    RAISE EXCEPTION 'credito non valido';
  END IF;

  IF p_data_scontrino IS NULL THEN
    RAISE EXCEPTION 'data scontrino mancante';
  END IF;

  IF p_data_scontrino > CURRENT_DATE THEN
    RAISE EXCEPTION 'data scontrino futura';
  END IF;

  IF p_data_scontrino < PROGRAM_START_DATE THEN
    RAISE EXCEPTION 'data scontrino precedente all''avvio del programma';
  END IF;

  documento_normalizzato := NULLIF(TRIM(COALESCE(p_numero_documento, '')), '');
  IF documento_normalizzato IS NULL THEN
    RAISE EXCEPTION 'numero documento mancante';
  END IF;

  matricola_normalizzata := UPPER(NULLIF(TRIM(COALESCE(p_matricola_rt, '')), ''));

  IF matricola_normalizzata IS NOT NULL THEN
    IF NOT EXISTS (
      SELECT 1 FROM public.registratori_telematici rt
      WHERE rt.bar_id = p_bar_id
        AND UPPER(rt.matricola) = matricola_normalizzata
        AND rt.attivo = true
    ) THEN
      RAISE EXCEPTION 'matricola registratore non riconosciuta per questo esercizio';
    END IF;

    IF EXISTS (
      SELECT 1 FROM public.scontrini s
      WHERE UPPER(s.matricola_rt) = matricola_normalizzata
        AND LOWER(TRIM(COALESCE(s.numero_documento, ''))) = LOWER(documento_normalizzato)
        AND s.data_scontrino = p_data_scontrino
        AND ROUND(s.importo_dichiarato::numeric, 2) = ROUND(p_importo_dichiarato::numeric, 2)
        AND s.stato <> 'rifiutato'
    ) THEN
      RAISE EXCEPTION 'scontrino duplicato: stessa matricola, numero documento, data e importo';
    END IF;
  END IF;

  SELECT * INTO limiti FROM public.limiti_bar WHERE bar_id = p_bar_id;
  IF NOT FOUND THEN
    limiti.tetto_giornaliero_scontrini := 3;
    limiti.soglia_revisione_manuale := 30;
    limiti.sospensione_giorni := 12;
  END IF;

  SELECT count(*) INTO scontrini_oggi
  FROM public.scontrini s
  WHERE s.cliente_id = p_cliente_id
    AND s.bar_id = p_bar_id
    AND s.data_scontrino = p_data_scontrino
    AND s.stato <> 'rifiutato';

  IF scontrini_oggi >= limiti.tetto_giornaliero_scontrini THEN
    RAISE EXCEPTION 'tetto giornaliero di scontrini raggiunto per questo cliente';
  END IF;

  IF p_importo_dichiarato > limiti.soglia_revisione_manuale THEN
    -- Sopra soglia: sempre in coda di revisione manuale, indipendentemente dal codice banco.
    stato_finale := 'in_verifica';
    motivo_sospensione_finale := 'importo_oltre_soglia';
    scadenza_sospensione := NULL;
  ELSIF public.verifica_codice_banco_interna(p_bar_id, p_codice_banco) THEN
    -- Codice banco valido: presenza fisica dimostrata, confermato subito.
    stato_finale := 'confermato';
    motivo_sospensione_finale := NULL;
    scadenza_sospensione := NULL;
  ELSE
    -- Nessun codice valido (offline al bar, o caricamento da casa): credito visibile
    -- ma non spendibile finche' il cliente non torna al bar e attiva con un codice valido.
    stato_finale := 'in_verifica';
    motivo_sospensione_finale := 'codice_banco_mancante';
    scadenza_sospensione := NOW() + (COALESCE(limiti.sospensione_giorni, 12) || ' days')::INTERVAL;
  END IF;

  INSERT INTO public.scontrini (
    id, cliente_id, bar_id, testo_ocr,
    data_scontrino, ora_scontrino, numero_documento,
    importo_dichiarato, importo_ocr, importo_verificato,
    credito_generato, stato, avviso_duplicato,
    motivo_rifiuto, operatore_label, matricola_rt,
    motivo_sospensione, sospeso_scaduto_il
  )
  VALUES (
    COALESCE(p_id, gen_random_uuid()),
    p_cliente_id,
    p_bar_id,
    p_testo_ocr,
    p_data_scontrino,
    p_ora_scontrino,
    documento_normalizzato,
    p_importo_dichiarato,
    p_importo_ocr,
    p_importo_verificato,
    p_credito_generato,
    stato_finale,
    COALESCE(p_avviso_duplicato, false),
    NULLIF(TRIM(COALESCE(p_motivo_controllo, '')), ''),
    NULLIF(TRIM(COALESCE(p_operatore_label, '')), ''),
    matricola_normalizzata,
    motivo_sospensione_finale,
    scadenza_sospensione
  )
  RETURNING id INTO nuovo_id;

  RETURN nuovo_id;
END;
$$;

REVOKE ALL ON FUNCTION public.registra_scontrino_pilot(
  uuid, uuid, uuid, text, date, time, text,
  numeric, numeric, numeric, numeric, text, boolean, text, text, text, text
) FROM anon;

GRANT EXECUTE ON FUNCTION public.registra_scontrino_pilot(
  uuid, uuid, uuid, text, date, time, text,
  numeric, numeric, numeric, numeric, text, boolean, text, text, text, text
) TO authenticated;

NOTIFY pgrst, 'reload schema';
```

- [ ] **Step 2: Angelo applica il file e crea il dispositivo banco**

Incolla ed esegui `docs/supabase-inversione-qr-banco.sql`. Poi, da autenticato come Salute Quotidiana o admin nella console del browser sull'app (o con una chiamata RPC diretta se preferisci farlo da SQL Editor con `auth.uid()` impostato — più semplice farlo dal browser), esegui una volta:

```javascript
const { data } = await supabaseClient.rpc("crea_dispositivo_banco_pilot", {
  p_bar_id: "<uuid del Bar pilota Francofonte>"
});
console.log(data.banco_token);
```

Prendi nota del `banco_token` restituito: ti serve per l'URL di `banco.html` nel Task 6. Se preferisci, il Task 6 include anche un modo per generarlo dalla stessa pagina `banco.html` la prima volta.

- [ ] **Step 3: Verifica manuale su Supabase**

```sql
SELECT bar_id, banco_token, attivo FROM public.banco_dispositivi;
```
Atteso: una riga attiva per il Bar pilota Francofonte.

```sql
SELECT conname, pg_get_constraintdef(oid) FROM pg_constraint WHERE conname = 'scontrini_stato_check';
```
Atteso: la definizione include `'scaduto'`.

- [ ] **Step 4: Commit**

```bash
git add docs/supabase-inversione-qr-banco.sql
git commit -m "v54: schema inversione QR — dispositivo banco, codice rotante, decadimento"
```

---

### Task 6: Pagina banco standalone

**Files:**
- Create: `banco.html`

**Interfaces:**
- Consuma: RPC `richiedi_codice_banco_pilot(p_banco_token)` (Task 5, `anon`).

- [ ] **Step 1: Scrivere il file completo**

```html
<!DOCTYPE html>
<html lang="it">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no">
<title>Codice bar — Credito Salute SQ</title>
<style>
  * { box-sizing: border-box; }
  html, body {
    margin: 0;
    height: 100%;
    background: #0f2438;
    color: #ffffff;
    font-family: Arial, Helvetica, sans-serif;
    display: flex;
    align-items: center;
    justify-content: center;
    -webkit-user-select: none;
    user-select: none;
  }
  .schermo {
    width: min(100%, 520px);
    padding: 32px;
    text-align: center;
  }
  .eyebrow {
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: #7fb0e0;
    font-size: 14px;
    margin: 0 0 6px;
  }
  h1 {
    font-size: 22px;
    margin: 0 0 28px;
  }
  .codice {
    font-size: 88px;
    font-weight: bold;
    letter-spacing: 0.12em;
    line-height: 1;
    margin: 0 0 20px;
    font-variant-numeric: tabular-nums;
  }
  canvas {
    background: #ffffff;
    padding: 12px;
    border-radius: 12px;
  }
  .barra {
    width: 100%;
    height: 8px;
    background: rgba(255,255,255,0.15);
    border-radius: 4px;
    overflow: hidden;
    margin: 24px 0 8px;
  }
  .barra__interno {
    height: 100%;
    background: #4ea1f7;
    transition: width 1s linear;
  }
  .stato {
    font-size: 15px;
    color: #a9c4e0;
    min-height: 20px;
  }
  .setup {
    margin-top: 24px;
  }
  .setup input {
    width: 100%;
    padding: 10px;
    border-radius: 8px;
    border: none;
    font-size: 15px;
  }
  .setup button {
    margin-top: 10px;
    padding: 10px 16px;
    border-radius: 8px;
    border: none;
    background: #4ea1f7;
    color: #06111d;
    font-weight: bold;
    font-size: 15px;
    cursor: pointer;
  }
</style>
</head>
<body>
  <div class="schermo">
    <div id="areaCodice" hidden>
      <p class="eyebrow" id="nomeBar">Bar</p>
      <h1>Mostra questo codice al cliente per attivare il credito SQ</h1>
      <p class="codice" id="cifreCodice">------</p>
      <canvas id="qrCanvas" width="220" height="220"></canvas>
      <div class="barra"><div class="barra__interno" id="barraInterno"></div></div>
      <p class="stato" id="stato">Connessione in corso.</p>
    </div>
    <div id="areaSetup" class="setup" hidden>
      <p class="eyebrow">Configurazione dispositivo</p>
      <p>Incolla qui il link ricevuto da Salute Quotidiana (contiene già il codice del dispositivo), oppure il solo token.</p>
      <input id="inputToken" type="text" placeholder="Token dispositivo banco">
      <button type="button" id="salvaToken">Salva e continua</button>
    </div>
  </div>

  <script src="https://cdn.jsdelivr.net/npm/qrcode@1.5.4/build/qrcode.min.js"></script>
  <script>
    const SUPABASE_URL = window.__SQ_BANCO_SUPABASE_URL__ || "INSERISCI_QUI_URL_SUPABASE";
    const SUPABASE_ANON_KEY = window.__SQ_BANCO_SUPABASE_ANON_KEY__ || "INSERISCI_QUI_ANON_KEY";

    const areaCodice = document.getElementById("areaCodice");
    const areaSetup = document.getElementById("areaSetup");
    const nomeBarEl = document.getElementById("nomeBar");
    const cifreCodiceEl = document.getElementById("cifreCodice");
    const statoEl = document.getElementById("stato");
    const barraInternoEl = document.getElementById("barraInterno");
    const qrCanvas = document.getElementById("qrCanvas");
    const inputToken = document.getElementById("inputToken");
    const salvaTokenBtn = document.getElementById("salvaToken");

    let refreshTimer = null;
    let countdownTimer = null;

    function getToken() {
      const params = new URLSearchParams(window.location.search);
      const daUrl = params.get("token");
      if (daUrl) return daUrl;
      return localStorage.getItem("sq_banco_token");
    }

    function estraiToken(valore) {
      const pulito = valore.trim();
      try {
        const url = new URL(pulito);
        const dallaQuery = url.searchParams.get("token");
        if (dallaQuery) return dallaQuery;
      } catch {
        // non e' un URL, va bene: e' probabilmente gia' il token
      }
      return pulito;
    }

    async function chiamaRpc(nome, corpo) {
      const risposta = await fetch(`${SUPABASE_URL}/rest/v1/rpc/${nome}`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "apikey": SUPABASE_ANON_KEY,
          "Authorization": `Bearer ${SUPABASE_ANON_KEY}`
        },
        body: JSON.stringify(corpo)
      });
      return risposta.json();
    }

    async function aggiornaCodice() {
      const token = getToken();
      if (!token) {
        mostraSetup();
        return;
      }

      const dati = await chiamaRpc("richiedi_codice_banco_pilot", { p_banco_token: token });

      if (!dati?.ok) {
        statoEl.textContent = "Dispositivo non riconosciuto. Verifica il token.";
        return;
      }

      areaSetup.hidden = true;
      areaCodice.hidden = false;
      nomeBarEl.textContent = dati.bar_nome || "Bar";
      cifreCodiceEl.textContent = dati.codice;
      statoEl.textContent = "Codice attivo.";

      try {
        await QRCode.toCanvas(qrCanvas, dati.codice, { width: 220, margin: 1 });
      } catch (err) {
        console.error("Errore disegno QR banco:", err);
      }

      avviaCountdown(dati.secondi_rimanenti, dati.finestra_secondi);
    }

    function avviaCountdown(secondiRimanenti, finestraSecondi) {
      if (countdownTimer) clearInterval(countdownTimer);
      let restanti = secondiRimanenti;
      const aggiorna = () => {
        const percentuale = Math.max(0, Math.min(100, (restanti / finestraSecondi) * 100));
        barraInternoEl.style.width = `${percentuale}%`;
        restanti -= 1;
        if (restanti < 0) {
          clearInterval(countdownTimer);
        }
      };
      aggiorna();
      countdownTimer = setInterval(aggiorna, 1000);
    }

    function mostraSetup() {
      areaCodice.hidden = true;
      areaSetup.hidden = false;
    }

    salvaTokenBtn.addEventListener("click", () => {
      const valore = estraiToken(inputToken.value);
      if (!valore) return;
      localStorage.setItem("sq_banco_token", valore);
      aggiornaCodice();
    });

    aggiornaCodice();
    refreshTimer = setInterval(aggiornaCodice, 15000);

    window.addEventListener("beforeunload", () => {
      if (refreshTimer) clearInterval(refreshTimer);
      if (countdownTimer) clearInterval(countdownTimer);
    });
  </script>
</body>
</html>
```

Nota di sicurezza: il segreto HMAC non compare mai in questo file — solo il codice a 6 cifre calcolato lato server, richiesto ogni 15 secondi (ben dentro la finestra di 90). Aprendo gli strumenti di sviluppo su questa pagina si vede al massimo il codice corrente, non il segreto: non basta per generare codici futuri.

Sostituisci `INSERISCI_QUI_URL_SUPABASE` e `INSERISCI_QUI_ANON_KEY` con i valori già presenti in `supabase-config.js` (stesso progetto Supabase, stessa `anon key` pubblica già usata dal resto dell'app — non è un segreto nuovo).

- [ ] **Step 2: Angelo salva il link sul dispositivo del banco**

Apri `https://<tuo-dominio>/banco.html?token=<banco_token ottenuto nel Task 5 Step 2>` sul tablet/telefono che resterà acceso al banco. La pagina salva il token in `localStorage`: da quel momento puoi aprire anche solo `banco.html` senza query string e la pagina se lo ricorda. Metti il dispositivo in modalità "resta sempre acceso" (impostazioni schermo) e collegalo alla corrente.

- [ ] **Step 3: Verifica manuale**

Apri `banco.html` con il token valido: deve comparire un codice a 6 cifre e un QR entro 2-3 secondi. Aspetta 90 secondi: il codice deve cambiare. Apri gli strumenti sviluppatore (F12) → tab Network: verifica che l'unica cosa scambiata sia `{ "ok": true, "codice": "123456", ... }`, mai un valore che somigli a una chiave lunga o un segreto.

- [ ] **Step 4: Commit**

```bash
git add banco.html
git commit -m "v54: pagina standalone banco — codice rotante per validazione presenza"
```

---

### Task 7: Frontend cliente — digita/inquadra il codice banco al caricamento

**Files:**
- Modify: `index.html` — sostituzione del blocco `qrScontrinoArea` (mostra QR al barista) con input codice + scanner
- Modify: `app.js` — invio `p_codice_banco`, gestione risposta (confermato / sospeso), scanner lato cliente, rimozione vecchie funzioni QR-al-barista

**Interfaces:**
- Consuma: `registra_scontrino_pilot` con `p_codice_banco` (Task 5); vista `scontrini_app_pilot` estesa con `motivo_sospensione`/`sospeso_scaduto_il` (Task 5).

- [ ] **Step 1: HTML — sostituire l'area QR-al-barista**

In `index.html`, sostituisci interamente:
```html
            <div class="qr-scontrino-area" id="qrScontrinoArea" hidden>
              <p class="form-label">Mostra questo QR al barista entro 15 minuti per confermare il credito:</p>
              <canvas id="qrCanvas" class="qr-canvas"></canvas>
              <p class="qr-timer" id="qrTimer">15:00</p>
              <p class="form-status" id="qrStatus">QR generato. In attesa di scansione da parte del bar.</p>
            </div>
```
con:
```html
            <div class="codice-banco-area full">
              <p class="form-label">Codice del banco</p>
              <p class="notice full">
                Al banco del bar trovi un codice a 6 cifre che cambia ogni 90 secondi. Digitalo o inquadra il QR
                mentre carichi lo scontrino: dimostra che sei nel locale in questo momento.
              </p>
              <label>
                Codice (6 cifre)
                <input name="codiceBanco" id="codiceBancoInput" inputmode="numeric" pattern="[0-9]{6}" maxlength="6" placeholder="000000" autocomplete="off">
              </label>
              <div class="camera-tool__actions">
                <button type="button" class="secondary" id="openCodiceBancoScan">Inquadra il QR del banco</button>
                <button type="button" class="secondary" id="closeCodiceBancoScan" disabled>Chiudi scanner</button>
              </div>
              <div class="qr-scan-preview" id="codiceBancoScanPreview" hidden>
                <video id="codiceBancoScanVideo" autoplay playsinline muted></video>
              </div>
              <canvas id="codiceBancoScanCanvas" hidden></canvas>
              <p class="form-status full" id="codiceBancoStatus">
                Non hai il codice sottomano? Puoi comunque inviare: il credito resta visibile ma non spendibile finche' non torni al bar per attivarlo.
              </p>
            </div>
            <div class="credito-sospeso-area full" id="creditoSospesoArea" hidden>
              <p class="notice full" data-status="warning">
                Credito in sospeso: <strong id="creditoSospesoScadenza"></strong>. Passa dal bar per attivarlo.
              </p>
              <label>
                Codice del banco per attivare
                <input inputmode="numeric" pattern="[0-9]{6}" maxlength="6" id="attivaCodiceInput" placeholder="000000">
              </label>
              <button type="button" class="secondary" id="attivaCodiceBtn">Attiva ora</button>
              <p class="form-status" id="attivaCodiceStatus"></p>
            </div>
```

- [ ] **Step 2: HTML — rimuovere lo scanner lato bar**

In `index.html`, rimuovi interamente il blocco (il bar non scansiona più nulla):
```html
            <div class="section-heading section-heading--compact">
              <h2>Scansiona QR cliente</h2>
            </div>
            <div class="qr-scan-area" id="qrScanArea">
              <div class="camera-tool__actions">
                <button type="button" class="secondary" id="openQrScan">Apri scanner QR</button>
                <button type="button" class="secondary" id="closeQrScan" disabled>Chiudi scanner</button>
              </div>
              <div class="qr-scan-preview" id="qrScanPreview" hidden>
                <video id="qrScanVideo" autoplay playsinline muted></video>
              </div>
              <canvas id="qrScanCanvas" hidden></canvas>
              <p class="form-status" id="qrScanStatus">Apri lo scanner e inquadra il QR mostrato dal cliente.</p>
            </div>
```

- [ ] **Step 3: `app.js` — sostituire `el` refs**

In `app.js`, righe 193-203, rimuovi questo blocco dall'oggetto `el`:
```javascript
  qrScontrinoArea: document.querySelector("#qrScontrinoArea"),
  qrCanvas: document.querySelector("#qrCanvas"),
  qrTimer: document.querySelector("#qrTimer"),
  qrStatus: document.querySelector("#qrStatus"),
  qrScanArea: document.querySelector("#qrScanArea"),
  openQrScan: document.querySelector("#openQrScan"),
  closeQrScan: document.querySelector("#closeQrScan"),
  qrScanPreview: document.querySelector("#qrScanPreview"),
  qrScanVideo: document.querySelector("#qrScanVideo"),
  qrScanCanvas: document.querySelector("#qrScanCanvas"),
  qrScanStatus: document.querySelector("#qrScanStatus")
```
(l'ultima riga del blocco originale non ha la virgola finale perché è l'ultima proprietà dell'oggetto letterale in quel punto — se dopo la rimozione la proprietà che resta subito prima nell'oggetto finisce senza virgola, aggiungila).

Aggiungi al loro posto:
```javascript
  codiceBancoInput: document.querySelector("#codiceBancoInput"),
  openCodiceBancoScan: document.querySelector("#openCodiceBancoScan"),
  closeCodiceBancoScan: document.querySelector("#closeCodiceBancoScan"),
  codiceBancoScanPreview: document.querySelector("#codiceBancoScanPreview"),
  codiceBancoScanVideo: document.querySelector("#codiceBancoScanVideo"),
  codiceBancoScanCanvas: document.querySelector("#codiceBancoScanCanvas"),
  codiceBancoStatus: document.querySelector("#codiceBancoStatus"),
  creditoSospesoArea: document.querySelector("#creditoSospesoArea"),
  creditoSospesoScadenza: document.querySelector("#creditoSospesoScadenza"),
  attivaCodiceInput: document.querySelector("#attivaCodiceInput"),
  attivaCodiceBtn: document.querySelector("#attivaCodiceBtn"),
  attivaCodiceStatus: document.querySelector("#attivaCodiceStatus"),
```

- [ ] **Step 4: `app.js` — rimuovere le vecchie funzioni QR-al-barista e scanner lato bar**

Rimuovi interamente queste funzioni (non più richiamate da nessun punto dopo gli Step 1-2, circa righe 1521-1696): `generateAndShowQr`, `startQrCountdown`, `setQrStatus`, `openQrScanner`, `closeQrScanner`, `scanQrLoop`, `handleQrTokenFound`, `setQrScanStatus`.

Rimuovi anche le tre variabili di modulo dichiarate a riga 100-102:
```javascript
let qrTimerInterval = null;
let qrScanStream = null;
let qrScanAnimFrame = null;
```
(sono usate solo dentro le funzioni appena rimosse — nessun altro punto di `app.js` le referenzia).

Rimuovi la chiamata `await generateAndShowQr(receipt.id);` dentro `submitReceipt` (circa riga 1516) — verrà comunque sostituita nello Step 6 di questo task insieme al resto del blocco di messaggio finale.

Rimuovi il wiring a riga 972-973:
```javascript
  if (el.openQrScan) el.openQrScan.addEventListener("click", openQrScanner);
  if (el.closeQrScan) el.closeQrScan.addEventListener("click", closeQrScanner);
```

- [ ] **Step 5: `app.js` — nuovo scanner lato cliente per il codice banco**

Aggiungi, nello stesso punto dove prima stavano le funzioni rimosse:

```javascript
let codiceBancoScanStream = null;
let codiceBancoScanAnimFrame = null;

async function openCodiceBancoScanner() {
  if (!el.codiceBancoScanVideo || !el.codiceBancoScanCanvas) return;
  if (typeof jsQR === "undefined") {
    setCodiceBancoStatus("Libreria scanner QR non caricata. Digita il codice a mano.", "error");
    return;
  }

  try {
    codiceBancoScanStream = await navigator.mediaDevices.getUserMedia({
      video: { facingMode: "environment" }
    });
  } catch (err) {
    setCodiceBancoStatus("Impossibile accedere alla fotocamera. Digita il codice a mano.", "error");
    return;
  }

  el.codiceBancoScanVideo.srcObject = codiceBancoScanStream;
  el.codiceBancoScanPreview.hidden = false;
  el.openCodiceBancoScan.disabled = true;
  el.closeCodiceBancoScan.disabled = false;
  setCodiceBancoStatus("Inquadra il QR mostrato al banco.", "loading");

  await el.codiceBancoScanVideo.play();
  codiceBancoScanLoop();
}

function closeCodiceBancoScanner() {
  if (codiceBancoScanAnimFrame) {
    cancelAnimationFrame(codiceBancoScanAnimFrame);
    codiceBancoScanAnimFrame = null;
  }
  if (codiceBancoScanStream) {
    codiceBancoScanStream.getTracks().forEach((track) => track.stop());
    codiceBancoScanStream = null;
  }
  if (el.codiceBancoScanVideo) el.codiceBancoScanVideo.srcObject = null;
  if (el.codiceBancoScanPreview) el.codiceBancoScanPreview.hidden = true;
  if (el.openCodiceBancoScan) el.openCodiceBancoScan.disabled = false;
  if (el.closeCodiceBancoScan) el.closeCodiceBancoScan.disabled = true;
}

function codiceBancoScanLoop() {
  if (!codiceBancoScanStream || !el.codiceBancoScanVideo.videoWidth) {
    codiceBancoScanAnimFrame = requestAnimationFrame(codiceBancoScanLoop);
    return;
  }

  const canvas = el.codiceBancoScanCanvas;
  canvas.width = el.codiceBancoScanVideo.videoWidth;
  canvas.height = el.codiceBancoScanVideo.videoHeight;
  const ctx = canvas.getContext("2d");
  ctx.drawImage(el.codiceBancoScanVideo, 0, 0, canvas.width, canvas.height);
  const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
  const code = jsQR(imageData.data, canvas.width, canvas.height);

  if (code?.data && /^\d{6}$/.test(code.data.trim())) {
    if (el.codiceBancoInput) el.codiceBancoInput.value = code.data.trim();
    setCodiceBancoStatus("Codice letto dal QR del banco.", "success");
    closeCodiceBancoScanner();
    return;
  }

  codiceBancoScanAnimFrame = requestAnimationFrame(codiceBancoScanLoop);
}

function setCodiceBancoStatus(message, status) {
  if (!el.codiceBancoStatus) return;
  el.codiceBancoStatus.textContent = message;
  el.codiceBancoStatus.dataset.status = status;
}
```

- [ ] **Step 6: `app.js` — includere il codice nell'invio e gestire la risposta**

Nell'oggetto `receipt` costruito in `submitReceipt` (già modificato nel Task 2), aggiungi:
```javascript
    codiceBanco: cleanText(form.get("codiceBanco")),
```

In `saveReceiptToSupabase`, aggiungi il parametro alla chiamata RPC:
```javascript
    p_matricola_rt: receipt.matricolaRt,
    p_codice_banco: receipt.codiceBanco || null
```

Dopo l'insert riuscito, prima del `return { ok: true, id: data, autoApproved }`, recupera lo stato reale deciso dal server (non più deducibile lato client, perché ora lo decide sempre `registra_scontrino_pilot`):
```javascript
  const { data: rigaInserita, error: erroreLettura } = await supabaseClient
    .from("scontrini_app_pilot")
    .select("stato,motivo_sospensione,sospeso_scaduto_il")
    .eq("id", data)
    .single();

  if (erroreLettura || !rigaInserita) {
    return { ok: true, id: data, autoApproved: false };
  }

  return {
    ok: true,
    id: data,
    autoApproved: rigaInserita.stato === "confermato",
    motivoSospensione: rigaInserita.motivo_sospensione,
    sospesoScadutoIl: rigaInserita.sospeso_scaduto_il
  };
```

In `submitReceipt`, dopo `const supabaseResult = await saveReceiptToSupabase(...)`, sostituisci il blocco di messaggio finale:
```javascript
  if (supabaseResult.autoApproved) {
    receipt.status = "confirmed";
    receipt.note = "Approvato automaticamente.";
  }
  state.receipts.unshift(receipt);
  saveState();
  receiptForm.reset();
  cameraReceiptFile = null;
  setTodayDefaults();
  resetOcrBox();
  updateReceiptCalculation();
  render();
  if (supabaseResult.autoApproved) {
    setReceiptSubmitStatus("Credito accreditato automaticamente.", "success");
    showToast("Credito accreditato.");
  } else if (supabaseResult.motivoSospensione === "codice_banco_mancante") {
    const scadenza = supabaseResult.sospesoScadutoIl
      ? new Date(supabaseResult.sospesoScadutoIl).toLocaleDateString("it-IT")
      : "";
    setReceiptSubmitStatus(
      `Scontrino inviato. Credito in sospeso: passa dal bar per attivarlo${scadenza ? ` entro il ${scadenza}` : ""}.`,
      "success"
    );
    showToast("Credito in sospeso: passa dal bar per attivarlo.");
  } else {
    setReceiptSubmitStatus("Scontrino inviato — in attesa di verifica SQ.", "success");
    showToast("Scontrino inviato. In attesa di verifica SQ.");
  }
  loadPilotReceiptsFromSupabase();
  loadPilotBalancesFromSupabase();
}
```
(rimuovi la vecchia riga `await generateAndShowQr(receipt.id);` se non l'hai già tolta nello Step 4).

- [ ] **Step 7: `app.js` — wiring scanner e attivazione a posteriori**

Nella sezione di wiring:
```javascript
  if (el.openCodiceBancoScan) el.openCodiceBancoScan.addEventListener("click", openCodiceBancoScanner);
  if (el.closeCodiceBancoScan) el.closeCodiceBancoScan.addEventListener("click", closeCodiceBancoScanner);
  if (el.attivaCodiceBtn) el.attivaCodiceBtn.addEventListener("click", handleAttivaCodiceBanco);
```

Aggiungi la funzione di attivazione a posteriori, vicino alle altre funzioni del Task:
```javascript
async function handleAttivaCodiceBanco() {
  const scontrinoId = el.attivaCodiceBtn?.dataset.scontrinoId;
  const codice = cleanText(el.attivaCodiceInput?.value);

  if (!scontrinoId || !codice) {
    setAttivaCodiceStatus("Inserisci il codice mostrato al banco.", "error");
    return;
  }

  if (!supabaseClient) {
    setAttivaCodiceStatus("Database non collegato.", "error");
    return;
  }

  setAttivaCodiceStatus("Verifica in corso.", "loading");
  const { data, error } = await supabaseClient.rpc("attiva_scontrino_con_codice_banco_pilot", {
    p_scontrino_id: scontrinoId,
    p_codice: codice
  });

  if (error) {
    console.error("Errore attivazione codice banco:", error);
    setAttivaCodiceStatus(`Errore: ${error.message}`, "error");
    return;
  }

  if (!data?.ok) {
    const messaggi = {
      codice_non_valido: "Codice non valido: controlla che sia quello mostrato ora al banco.",
      scaduto: "Il periodo per attivare questo credito e' scaduto.",
      non_attivabile: "Questo scontrino non e' (piu') attivabile con un codice."
    };
    setAttivaCodiceStatus(messaggi[data?.errore] || "Attivazione non riuscita.", "error");
    return;
  }

  setAttivaCodiceStatus("Credito attivato. Ora e' spendibile.", "success");
  showToast("Credito attivato.");
  if (el.creditoSospesoArea) el.creditoSospesoArea.hidden = true;
  loadPilotReceiptsFromSupabase();
  loadPilotBalancesFromSupabase();
}

function setAttivaCodiceStatus(message, status) {
  if (!el.attivaCodiceStatus) return;
  el.attivaCodiceStatus.textContent = message;
  el.attivaCodiceStatus.dataset.status = status;
}
```

- [ ] **Step 8: `app.js` — mostrare l'area "credito sospeso" per lo scontrino sospeso più recente del cliente**

Nella funzione che già renderizza lo storico scontrini del cliente (cerca `renderCustomerDetail` o `renderReceiptList` — quella che itera `state.receipts` per il cliente corrente), aggiungi questa logica, da richiamare dopo il caricamento scontrini (es. dentro `render()` o subito dopo `loadPilotReceiptsFromSupabase()`):

```javascript
function aggiornaAreaCreditoSospeso() {
  if (!el.creditoSospesoArea) return;

  const customerId = getCurrentCustomerIdForRole();
  const sospeso = state.receipts.find((r) =>
    r.customerId === customerId &&
    r.status === "pending" &&
    r.motivoSospensione === "codice_banco_mancante"
  );

  if (!sospeso) {
    el.creditoSospesoArea.hidden = true;
    return;
  }

  el.creditoSospesoArea.hidden = false;
  el.creditoSospesoScadenza.textContent = sospeso.sospesoScadutoIl
    ? `scade il ${new Date(sospeso.sospesoScadutoIl).toLocaleDateString("it-IT")}`
    : "scadenza non disponibile";
  if (el.attivaCodiceBtn) el.attivaCodiceBtn.dataset.scontrinoId = sospeso.id;
}
```

Aggiungi i due nuovi campi a `mapSupabaseReceipt` (circa riga 667) perché lo storico locale li conosca:
```javascript
  return {
    id: receipt.id,
    customerId: receipt.cliente_id,
    barName: BAR_NAME,
    receiptDate: receipt.data_scontrino || "",
    receiptTime: receipt.ora_scontrino || "",
    documentNumber: receipt.numero_documento || "",
    amount: Number(receipt.importo_dichiarato || 0),
    credit: Number(receipt.credito_generato || 0),
    status: mapSupabaseReceiptStatus(receipt.stato),
    motivoSospensione: receipt.motivo_sospensione || null,
    sospesoScadutoIl: receipt.sospeso_scaduto_il || null,
    note: receipt.motivo_rifiuto || (receipt.avviso_duplicato ? "Possibile duplicato." : ""),
    ocr: text ? createOcrSnapshot(text, fields, 0) : null,
    imageData: "",
    createdAt: receipt.created_at
  };
```

Chiama `aggiornaAreaCreditoSospeso()` alla fine di `render()`.

- [ ] **Step 9: `app.js` — nuova label di stato per "scaduto"**

```javascript
function mapSupabaseReceiptStatus(status) {
  const statuses = {
    confermato: "confirmed",
    in_verifica: "pending",
    rifiutato: "rejected",
    scaduto: "expired"
  };

  return statuses[status] || "pending";
}
```

```javascript
function statusLabel(status) {
  const labels = {
    pending: "In verifica",
    confirmed: "Confermato",
    rejected: "Rifiutato",
    expired: "Scaduto"
  };
  return labels[status] || status;
}
```

- [ ] **Step 10: `styles.css` — badge stato scaduto e area credito sospeso**

Cerca la regola esistente `.status-rejected` (o simile) e aggiungi subito dopo:
```css
.status-expired {
  background: var(--surface-soft);
  color: var(--muted);
}

.credito-sospeso-area {
  border: 1px solid var(--line-strong);
  border-radius: 10px;
  padding: 14px;
  margin-top: 12px;
  background: var(--surface-soft);
}
```

- [ ] **Step 11: Verifica manuale end-to-end**

Apri `banco.html` sul dispositivo di test con un token valido, annota il codice mostrato. Come cliente sull'app principale, carica uno scontrino digitando quel codice: deve risultare "Credito accreditato automaticamente." Carica un secondo scontrino **senza** inserire il codice: deve comparire "Credito in sospeso: passa dal bar per attivarlo entro il [data]" e l'area "Credito in sospeso" deve apparire nella scheda cliente con un campo per attivare. Prendi il codice attuale da `banco.html` e usalo in quel campo: deve confermare "Credito attivato. Ora e' spendibile." e il saldo disponibile deve aumentare dell'importo di quello scontrino.

- [ ] **Step 12: Commit**

```bash
git add index.html app.js styles.css
git commit -m "v54: inversione QR — cliente inquadra il codice del banco, non piu' il bar che scansiona"
```

---

### Task 8: Decadimento automatico dei crediti sospesi

**Files:**
- Create: `docs/supabase-cron-decadimento-sospesi.sql`

**Interfaces:**
- Consuma: `scadi_scontrini_sospesi_pilot()` (Task 5).

- [ ] **Step 1: Scrivere il file SQL**

```sql
-- docs/supabase-cron-decadimento-sospesi.sql
-- Programma l'esecuzione giornaliera di scadi_scontrini_sospesi_pilot() via pg_cron.
-- Se pg_cron non e' disponibile sul tuo piano Supabase, questo file fallisce alla prima
-- riga: in quel caso usa il fallback manuale descritto nello Step 3 di questo task.

CREATE EXTENSION IF NOT EXISTS pg_cron;

SELECT cron.schedule(
  'decadimento-scontrini-sospesi',
  '0 4 * * *',  -- ogni giorno alle 04:00 UTC
  $$SELECT public.scadi_scontrini_sospesi_pilot();$$
);
```

- [ ] **Step 2: Angelo applica il file su Supabase**

Prova a eseguire `docs/supabase-cron-decadimento-sospesi.sql` nell'SQL Editor. Se ottieni un errore su `CREATE EXTENSION pg_cron` (permesso negato o estensione non disponibile), passa allo Step 3 e non insistere: significa che il tuo piano Supabase non lo consente dall'SQL Editor — va abilitato da Dashboard → Database → Extensions cercando "pg_cron" e attivandolo da lì, poi rilancia solo la parte `SELECT cron.schedule(...)`.

- [ ] **Step 3: Fallback manuale (usalo se pg_cron non è disponibile)**

Una volta ogni pochi giorni, esegui a mano nell'SQL Editor:
```sql
SELECT public.scadi_scontrini_sospesi_pilot();
```
Restituisce il numero di scontrini appena decaduti. Non c'è urgenza: un cliente con credito sospeso resta comunque non-spendibile finché non lo attiva, il decadimento serve solo a "chiudere" formalmente le pratiche vecchie — farlo con qualche giorno di ritardo non causa danni.

- [ ] **Step 4: Verifica manuale**

```sql
SELECT jobid, schedule, command FROM cron.job WHERE jobname = 'decadimento-scontrini-sospesi';
```
Atteso (se pg_cron è attivo): una riga con lo schedule `0 4 * * *`.

- [ ] **Step 5: Commit**

```bash
git add docs/supabase-cron-decadimento-sospesi.sql
git commit -m "v54: decadimento automatico crediti sospesi via pg_cron"
```

---

### Task 9: Disattivare il vecchio meccanismo QR dal frontend

**Rischio:** questo task rimuove codice frontend che il pilot usa oggi. Va eseguito **solo dopo** che il Task 7 è verificato e funzionante, altrimenti i clienti restano senza nessun modo di validare lo scontrino nell'intervallo. **Rollback:** `git revert` di questo commit ripristina l'area QR-al-barista e lo scanner lato bar — ma a quel punto il Task 5 avrebbe già cambiato `registra_scontrino_pilot` per non considerare più `p_stato` come prima, quindi un rollback pulito richiede anche di tornare al Task 3 lato database. Preferisci non arrivare a questo punto: verifica bene il Task 7 prima.

**Files:**
- Nessuna modifica di codice aggiuntiva: gli Step 1-2 e 4 del Task 7 hanno già rimosso l'HTML e il JS del vecchio meccanismo. Questo task è la dichiarazione esplicita di cosa resta orfano in database, richiesta dal brief, non un task di codice.

- [ ] **Step 1: Verifica che nessun riferimento al vecchio meccanismo sia rimasto**

```bash
grep -n "genera_qr_scontrino_pilot\|conferma_qr_scontrino_pilot\|qrScanArea\|qrScontrinoArea" index.html app.js
```
Atteso: nessun risultato.

- [ ] **Step 2: Documentare cosa resta orfano (nessuna azione, solo lettura per verifica)**

Questi oggetti restano in database, intatti, con i dati storici del pilot, ma senza più nessun codice frontend che li richiami:
- Funzioni `genera_qr_scontrino_pilot(uuid)`, `conferma_qr_scontrino_pilot(uuid, text)`.
- Tabella `verifiche_scontrini` (mai stata popolata da queste funzioni, che scrivono solo su `scontrini.qr_*` — resta con le eventuali righe storiche di verifiche titolare-bar del design V2 originale, se ce ne sono).
- Colonne `scontrini.qr_token`, `qr_generated_at`, `qr_scanned_at`, `qr_scanned_by`.
- Tabella `operatori_bar` e vista `scontrini_bar_verifica`: **non** diventano orfane da questo piano — `operatori_bar` è ancora usata da `report_bar_corrente_pilot()` (tab "Report Bar" del titolare) per trovare il bar collegato al profilo, quindi resta viva. `scontrini_bar_verifica` non risulta richiamata da nessun punto del frontend attuale (verificato con grep prima di scrivere questo piano): era probabilmente un residuo del disegno V2 originale (titolare bar conferma da dashboard) mai collegato all'app dopo l'introduzione del QR — è orfana da prima di questo piano, non per effetto di questo piano.

Nessuna query da eseguire: è solo la dichiarazione richiesta dal brief.

- [ ] **Step 3: Commit**

Non c'è nulla da committare in questo task (nessun file cambia) — salta il commit.

---

### Task 10: Migrazione a caldo — scontrini in transito col vecchio QR

**Rischio:** tocca dati di scontrini reali, in produzione, caricati da clienti prima del deploy di questo piano. Esegui questo task **una sola volta**, subito dopo il Task 9, prima di comunicare il cambiamento ai clienti (Task 11).

**Files:**
- Create: `docs/supabase-migrazione-qr-a-caldo.sql`

- [ ] **Step 1: Scrivere lo script con anteprima prima della modifica**

```sql
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
```

- [ ] **Step 2: Angelo esegue l'anteprima, valuta, poi esegue la UPDATE**

Esegui prima solo la `SELECT` di anteprima. Se il numero di righe è quello che ti aspetti (probabilmente 0-2, dato il volume attuale del pilot), esegui la `UPDATE`.

- [ ] **Step 3: Verifica manuale**

Per ciascun cliente coinvolto (se ce ne sono), apri l'app come quel cliente (o chiedi conferma al cliente stesso): deve comparire l'area "Credito in sospeso: passa dal bar per attivarlo" nella scheda cliente, con la nuova scadenza.

- [ ] **Step 4: Commit**

```bash
git add docs/supabase-migrazione-qr-a-caldo.sql
git commit -m "v54: migrazione a caldo scontrini in transito col vecchio QR"
```

---

### Task 11: Comunicazione ai clienti del pilot

**Files:** nessuno — task operativo, non di codice.

- [ ] **Step 1: Bozza messaggio WhatsApp (Domanda aperta 3 — rivedila prima di inviarla)**

```text
Ciao! Una piccola novità per il credito SQ al bar 🙂

Da oggi, quando carichi lo scontrino sull'app, al banco del bar trovi uno schermo con un
codice a 6 cifre che cambia ogni minuto e mezzo. Basta digitarlo (o inquadrare il QR) mentre
carichi lo scontrino: serve solo a dimostrare che eri fisicamente al bar, non devi più
aspettare che qualcuno del bar scansioni il tuo QR.

Se per qualche motivo carichi lo scontrino senza avere il codice sottomano (es. da casa),
nessun problema: il credito resta visibile ma non lo puoi ancora usare. Basta che torni al
bar entro qualche giorno e lo attivi con il codice del momento — trovi il bottone "Attiva
ora" nella tua scheda dell'app.

Qualsiasi dubbio, scrivici pure qui.
```

- [ ] **Step 2: Angelo decide quando inviarlo**

Invialo (o modificalo prima) solo dopo aver verificato il Task 10 e aver controllato che almeno un caricamento reale di prova sia andato a buon fine con `banco.html` acceso al bar.

- [ ] **Step 3: Nessun commit**

Task operativo, nessun file da versionare.

---

### Task 12: Bump versione e verifica finale

**Files:**
- Modify: `app.js` (`APP_VERSION`)
- Modify: `index.html` (query-string cache-busting)

- [ ] **Step 1: Bump versione**

In `app.js`:
```javascript
const APP_VERSION = "v54";
```

In `index.html`:
```html
    <link rel="stylesheet" href="styles.css?v=56">
```
```html
    <script src="app.js?v=54"></script>
```

- [ ] **Step 2: `node --check app.js`**

Esegui: `node --check app.js`
Atteso: nessun output, exit code 0.

- [ ] **Step 3: Verifica manuale completa**

Ripeti l'intero flusso: caricamento scontrino con matricola e codice banco validi (confermato subito), caricamento senza codice (sospeso, poi attivato dal bottone "Attiva ora"), caricamento duplicato (rifiutato con messaggio chiaro), caricamento oltre soglia (finisce in coda di revisione manuale, confermabile/rifiutabile da Salute Quotidiana), caricamento oltre il tetto giornaliero (rifiutato con messaggio chiaro). Verifica anche che i flussi esistenti non toccati da questo piano — richieste utilizzo credito, redemption prestazioni, Lista dei Silenziosi se già presente — continuino a funzionare senza errori in console.

- [ ] **Step 4: Commit**

```bash
git add app.js index.html
git commit -m "v54: bump versione e chiusura modulo validazione scontrini"
```

---

## Anomalie rilevate — da segnalare, non da risolvere in questa versione

1. **`e_cliente` compare due volte** nell'elenco delle funzioni fornito nel brief. Sono quasi certamente due overload con firme diverse (il file `docs/supabase-rls-pilot-salute-admin.sql` ne definisce una sola, `e_cliente()` senza argomenti — l'altra firma non è in nessun file del repository, quindi è stata creata direttamente su Supabase). È una fonte concreta di ambiguità: PostgREST/Postgres risolvono l'overload in base agli argomenti passati, ma se qualcuno chiama `e_cliente()` da SQL Editor senza sapere quale firma esiste può ottenere un errore di ambiguità o richiamare quella sbagliata. **Raccomandazione:** far girare `SELECT proname, pg_get_function_arguments(oid) FROM pg_proc WHERE proname = 'e_cliente'` su Supabase per vedere le due firme reali, capire quale delle due è quella viva usata dalle RLS, ed eliminare l'altra con `DROP FUNCTION`.

2. **`log_operativi` e `log_operazioni` coesistono** con nomi quasi identici. `log_operativi` è quella definita in `docs/supabase-schema-v2.sql` e con RLS in `docs/supabase-rls-pilot-salute-admin.sql` — verosimilmente quella viva. `log_operazioni` non compare in nessun file del repository: è stata creata direttamente su Supabase, probabilmente il residuo di una rinomina mai completata o di un doppione creato per errore. **Raccomandazione:** controllare `SELECT count(*) FROM log_operazioni` — se è vuota o quasi, è sicuramente il residuo da eliminare; se contiene dati, va capito da quale parte del codice (non presente in questo repository — forse uno script esterno o una funzione creata solo su Supabase) scrive lì, prima di decidere se unificarla con `log_operativi`.

3. **Trovata durante questo piano, non nel brief:** la funzione `registra_scontrino_pilot`, prima di questo piano, era eseguibile da `anon` senza controllo `auth.uid()` — regressione introdotta da `docs/supabase-operatore-label.sql` (2026-07-25) rispetto a `docs/supabase-hardening-sicurezza-pilot.sql` (2026-07-19). Questo piano la corregge nel Task 1 (vedi nota in testa al piano), ma vale la pena controllare se lo stesso pattern — un file successivo che ricrea una funzione perdendo per strada un controllo di sicurezza di un file precedente — si è ripetuto su altre funzioni non toccate da questo piano. **Raccomandazione:** far girare `SELECT proname FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace WHERE n.nspname = 'public' AND has_function_privilege('anon', p.oid, 'execute') AND p.prosecdef` per vedere quali funzioni `SECURITY DEFINER` sono oggi eseguibili da `anon`, e verificare per ciascuna se è voluto.
