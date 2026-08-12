# Certificato di Cura Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ad ogni prestazione confermata, generare automaticamente un messaggio (WhatsApp + versione stampabile) che accredita collettivamente "l'ecosistema Salute Quotidiana" (tutti gli esercizi aderenti attivi in quel momento) invece di un singolo donatore, e — se il beneficiario non è ancora cliente di nessun esercizio aderente — include un invito senza obbligo a provarne uno, con un piccolo sconto a tempo.

**Architecture:** Nessuna nuova tabella. Si aggancia al punto in cui `handleRedemptionSubmit` in `app.js` già genera il messaggio WhatsApp per il bar (`buildWhatsAppMessageBar`), aggiungendo un secondo messaggio parallelo per il beneficiario della prestazione, più un pulsante per aprirne una versione stampabile in una nuova scheda del browser.

**Tech Stack:** Vanilla JS (`app.js`), HTML statico (`index.html`), CSS (`styles.css`), Supabase JS client (query dirette su `bar`, `clienti`, `scontrini` — nessuna nuova RPC).

## Global Constraints

- Stack: vanilla JS senza build step e senza framework di test. Non esiste `package.json`/jest/vitest in questo repo — `node --check app.js` verifica solo la sintassi.
- `app.js` è uno script browser classico (non un modulo): non ha `module.exports`, usa `document.querySelector` a livello top. Non è "require-abile" in Node. Per le funzioni di puro calcolo/testo (nessun accesso a `document`/`supabaseClient`), verificarle PRIMA con uno script Node standalone che duplica temporaneamente la funzione, poi incollare la versione verificata in `app.js`. Per tutto il resto (wiring UI, chiamate Supabase) la verifica è manuale nel browser — non esiste automazione disponibile in questo progetto.
- Versione app: bump `APP_VERSION` in `app.js` (attualmente `"v52"` → diventa `"v53"`) e i query-string di cache-busting in `index.html` (`styles.css?v=55` → `?v=56`, `app.js?v=52` → `?v=53`) all'ultimo task.
- Non rompere nulla del pilot in corso (v52 QR anti-imbroglio, commit `017c426`) — solo addizioni. Non toccare `buildWhatsAppMessageBar`, `saveRedemptionToSupabase`, `registra_utilizzo_credito_pilot`, la logica QR o l'auto-approvazione scontrini.
- Linguaggio nei testi rivolti a pazienti/famiglie: semplice, umano, mai burocratico — niente gergo da programma fedeltà.
- Il tetto di 50€ SQ per cliente non è toccato da questo modulo (il Certificato non modifica saldi, è solo testo generato dopo una prestazione già registrata).
- Sconto invito ecosistema: finanziato dal singolo esercizio aderente (non dal fondo SQ) — il Certificato si limita a proporlo in un messaggio, non esiste enforcement automatico nell'app (l'esercizio lo applica manualmente quando la persona si presenta).

---

## File Structure

- **Modify `index.html`**
  - `redemptionForm` (sezione `id="salute"`, blocco beneficiario): aggiungere campo opzionale `beneficiaryPhone`, usato solo per verificare se il beneficiario è già cliente di un esercizio aderente.
  - Dopo `redemptionMessageArea` (circa riga 450 nell'attuale `index.html`): nuovo blocco `certificatoCuraArea` con textarea messaggio, pulsante copia, pulsante "Apri versione stampabile".
- **Modify `app.js`**
  - Nuove costanti: `ECOSISTEMA_INVITO_SCONTO_PERCENT`, `ECOSISTEMA_INVITO_GIORNI_VALIDITA`.
  - Nuovi `el` refs: `certificatoCuraArea`, `certificatoCuraText`, `copyCertificatoCuraBtn`, `openCertificatoStampabileBtn`.
  - Nuove funzioni: `loadEcosistemaAderenti()`, `isBeneficiarioNuovoNelEcosistema(phone)`, `buildCertificatoDiCuraMessage(...)`, `buildCertificatoStampabileHtml(...)`, `openCertificatoStampabile(...)`, `copyCertificatoCura()`.
  - Wiring: chiamata dentro `handleRedemptionSubmit`, subito dopo il blocco che popola `redemptionBarText`/`redemptionMessageArea`.
- **Modify `styles.css`**
  - Stile `.certificato-cura-area` (riuso pattern esistente `.whatsapp-message-area`/`.whatsapp-message-box`, nessuna nuova classe base da inventare dove non serve).

---

### Task 1: Campo telefono beneficiario + costanti configurazione invito

**Files:**
- Modify: `index.html:439-442` (blocco `<label>Beneficiario<select name="beneficiary">...` dentro `redemptionForm`)
- Modify: `app.js:3` (area costanti in cima al file, vicino a `CREDIT_RATE`/`BAR_NAME`)

**Interfaces:**
- Produce: nuova costante `ECOSISTEMA_INVITO_SCONTO_PERCENT = 10` e `ECOSISTEMA_INVITO_GIORNI_VALIDITA = 30`, usate da Task 4.
- Produce: `redemptionForm.beneficiaryPhone` (input opzionale, `form.get("beneficiaryPhone")`), usato da Task 3.

- [ ] **Step 1: Aggiungere il campo nel form**

In `index.html`, subito dopo il blocco "Nota beneficiario" dentro `redemptionForm` (circa riga 439-442):

```html
              <label>
                Nota beneficiario
                <input name="beneficiaryNote" placeholder="Es. madre, padre, persona indicata">
              </label>
              <label>
                Telefono beneficiario (facoltativo)
                <input name="beneficiaryPhone" inputmode="tel" placeholder="Solo se diverso dal cliente selezionato">
              </label>
```

- [ ] **Step 2: Aggiungere le costanti in app.js**

In `app.js`, subito dopo la riga `const BAR_NAME = "Bar pilota Francofonte";` (riga 5):

```javascript
const ECOSISTEMA_INVITO_SCONTO_PERCENT = 10;
const ECOSISTEMA_INVITO_GIORNI_VALIDITA = 30;
```

- [ ] **Step 3: Verifica manuale**

Apri `index.html` nel browser (o ricarica se già aperto), vai al tab "Salute Quotidiana" → "Registra prestazione": il nuovo campo "Telefono beneficiario (facoltativo)" deve comparire dopo "Nota beneficiario". Nessun errore in console.

- [ ] **Step 4: Commit**

```bash
git add index.html app.js
git commit -m "certificato-cura: campo telefono beneficiario + costanti invito ecosistema"
```

---

### Task 2: Elenco esercizi aderenti (ecosistema)

**Files:**
- Modify: `app.js` — aggiungere dopo la funzione `checkSupabaseDatabase` (circa riga 411)

**Interfaces:**
- Consuma: `supabaseClient` (già inizializzato da `initSupabase`), tabella `bar` (colonne note: `id`, `nome`).
- Produce: `let ecosistemaBarNomi = []` (variabile module-level), funzione `async function loadEcosistemaAderenti()` che la popola. Task 4 la userà leggendo direttamente `ecosistemaBarNomi`.

- [ ] **Step 1: Verifica standalone della query (manuale, non automatizzabile in Node)**

Non esiste modo di testare questa query senza un client Supabase reale: verifica diretta nel browser al Task 3 (nessuno step Node qui, la funzione dipende interamente da `supabaseClient`).

- [ ] **Step 2: Aggiungere la variabile module-level**

In `app.js`, vicino alle altre `let` di stato globale (riga 91-99, dopo `let activeBar = null;`):

```javascript
let ecosistemaBarNomi = [];
```

- [ ] **Step 3: Implementare `loadEcosistemaAderenti`**

Subito dopo la funzione `checkSupabaseDatabase` (dopo la riga 411, prima di `async function loadPilotCustomersFromSupabase`):

```javascript
async function loadEcosistemaAderenti() {
  if (!supabaseClient) return;

  const { data, error } = await supabaseClient
    .from("bar")
    .select("nome")
    .order("nome", { ascending: true });

  if (error) {
    console.error("Errore caricamento ecosistema esercizi aderenti:", error);
    return;
  }

  ecosistemaBarNomi = (data || []).map((row) => row.nome).filter(Boolean);
}
```

- [ ] **Step 4: Richiamarla all'avvio, subito dopo `checkSupabaseDatabase()`**

Cerca in `app.js` il punto in cui `checkSupabaseDatabase()` viene chiamata dentro `DOMContentLoaded` (vicino a `initSupabase()`). Subito dopo quella chiamata, aggiungi:

```javascript
  await loadEcosistemaAderenti();
```

- [ ] **Step 5: Verifica manuale**

Apri l'app nel browser con Supabase configurato, apri la console, digita `ecosistemaBarNomi` dopo il caricamento: deve restituire `["Bar pilota Francofonte"]` (l'unico esercizio attivo nel pilot). Nessun errore in console.

- [ ] **Step 6: Commit**

```bash
git add app.js
git commit -m "certificato-cura: carica elenco esercizi aderenti (ecosistema)"
```

---

### Task 3: Verifica "beneficiario nuovo nell'ecosistema"

**Files:**
- Modify: `app.js` — aggiungere subito dopo `loadEcosistemaAderenti` (Task 2)

**Interfaces:**
- Consuma: `supabaseClient`, tabelle `clienti` (colonna `telefono`, `id`) e `scontrini` (colonna `cliente_id`), funzione `normalizePhone` (già esistente, riga 3551).
- Produce: `async function isBeneficiarioNuovoNelEcosistema(phone)` → `Promise<boolean>`. `true` = la persona non è cliente di nessun esercizio aderente (nessuna riga in `scontrini` collegata al suo numero) o il numero non è fornito. Usata da Task 4.

- [ ] **Step 1: Implementare la funzione**

```javascript
async function isBeneficiarioNuovoNelEcosistema(phone) {
  const normalized = normalizePhone(phone || "");
  if (!normalized || !supabaseClient) return false;

  const { data: clienteRows, error: clienteError } = await supabaseClient
    .from("clienti")
    .select("id,telefono");

  if (clienteError) {
    console.error("Errore verifica cliente esistente (certificato):", clienteError);
    return false;
  }

  const match = (clienteRows || []).find((row) => normalizePhone(row.telefono) === normalized);
  if (!match) return true;

  const { count, error: scontriniError } = await supabaseClient
    .from("scontrini")
    .select("id", { count: "exact", head: true })
    .eq("cliente_id", match.id);

  if (scontriniError) {
    console.error("Errore verifica scontrini beneficiario (certificato):", scontriniError);
    return false;
  }

  return (count || 0) === 0;
}
```

**Nota per chi esegue:** se la lettura di `clienti`/`scontrini` con queste colonne fallisce per permessi RLS (l'app finora ha sempre letto tramite le viste `clienti_app_pilot` / `scontrini_app_pilot` per il ruolo `salute_quotidiana`), sostituisci `"clienti"` con `"clienti_app_pilot"` e `"scontrini"` con `"scontrini_app_pilot"` in questa funzione — sono le viste già usate altrove in `app.js` (righe 417, ~perimetro `loadPilotReceiptsFromSupabase`). Verifica quale delle due funziona nel passo di test qui sotto.

- [ ] **Step 2: Verifica manuale**

Nel tab "Salute Quotidiana", registra una prestazione con beneficiario "familiare" e un numero di telefono che NON esiste in nessun record cliente. In console del browser, dopo l'invio, controlla che `isBeneficiarioNuovoNelEcosistema("quel numero")` (richiamabile a mano in console se esposta, altrimenti verificalo indirettamente al Task 5 quando il messaggio la userà) restituisca `true`. Ripeti con il numero di un cliente esistente che ha già almeno uno scontrino: deve restituire `false`.

- [ ] **Step 3: Commit**

```bash
git add app.js
git commit -m "certificato-cura: verifica se il beneficiario e' gia' cliente di un esercizio aderente"
```

---

### Task 4: Testo del Certificato di Cura (WhatsApp)

**Files:**
- Modify: `app.js` — aggiungere subito dopo `buildWhatsAppMessageBar` (circa riga 3690)

**Interfaces:**
- Consuma: `formatMoney`, `formatDate` (esistenti), `ecosistemaBarNomi` (Task 2), `ECOSISTEMA_INVITO_SCONTO_PERCENT`/`ECOSISTEMA_INVITO_GIORNI_VALIDITA` (Task 1).
- Produce: `function buildCertificatoDiCuraMessage(customer, redemption, ecosistemaNomi, beneficiarioNuovo)` → stringa. Usata da Task 5.

- [ ] **Step 1: Verificare il testo con uno script Node standalone (funzione pura, nessun accesso a `document`/`supabaseClient`)**

Crea `$CLAUDE_JOB_DIR/tmp/test-certificato-testo.js`:

```javascript
function formatMoneyStub(v) { return Number(v).toFixed(2).replace(".", ","); }
function formatDateStub(v) { return new Date(v).toLocaleDateString("it-IT"); }

function buildCertificatoDiCuraMessage(customer, redemption, ecosistemaNomi, beneficiarioNuovo, opts) {
  const formatMoney = opts.formatMoney;
  const formatDate = opts.formatDate;
  const nomiEcosistema = ecosistemaNomi.length ? ecosistemaNomi.join(", ") : "gli esercizi aderenti a Salute Quotidiana";

  const lines = [
    `Certificato di Cura — ${formatDate(redemption.createdAt)}`,
    "",
    `${redemption.service} per ${customer.firstName} ${customer.lastName}.`,
    `Valore della prestazione: ${formatMoney(redemption.servicePrice)} euro.`,
    `Credito Salute SQ applicato: ${formatMoney(redemption.creditUsed)} euro.`,
    "",
    `Questa prestazione e' stata resa possibile dalla generosita' dell'ecosistema Salute Quotidiana: ${nomiEcosistema}.`,
    "Ogni consumazione fatta in questi esercizi da chi partecipa al progetto diventa cura per qualcun altro in paese.",
  ];

  if (beneficiarioNuovo) {
    lines.push(
      "",
      `Se vuoi conoscere l'ecosistema Salute Quotidiana, sei invitato — senza alcun obbligo — a fare una consumazione o un acquisto presso ${nomiEcosistema}.`,
      `Per i prossimi ${opts.giorni} giorni avrai un piccolo sconto (${opts.sconto}%) sul tuo primo acquisto.`
    );
  }

  lines.push("", "Grazie di cuore — Salute Quotidiana");
  return lines.join("\n");
}

const customer = { firstName: "Maria", lastName: "Rossi" };
const redemption = { service: "Prelievo ematico periferico", servicePrice: 10, creditUsed: 10, createdAt: new Date().toISOString() };
const opts = { formatMoney: formatMoneyStub, formatDate: formatDateStub, giorni: 30, sconto: 10 };

const withInvito = buildCertificatoDiCuraMessage(customer, redemption, ["Bar pilota Francofonte"], true, opts);
console.assert(withInvito.includes("sei invitato"), "FAIL: deve contenere invito quando beneficiarioNuovo=true");
console.assert(withInvito.includes("Bar pilota Francofonte"), "FAIL: deve nominare l'ecosistema");
console.assert(!withInvito.includes("undefined"), "FAIL: nessun campo undefined nel testo");

const senzaInvito = buildCertificatoDiCuraMessage(customer, redemption, ["Bar pilota Francofonte"], false, opts);
console.assert(!senzaInvito.includes("sei invitato"), "FAIL: NON deve contenere invito quando beneficiarioNuovo=false");

console.log("OK: tutti gli assert passati");
```

Esegui: `node "$CLAUDE_JOB_DIR/tmp/test-certificato-testo.js"`
Atteso: stampa `OK: tutti gli assert passati`, nessun output `FAIL`.

- [ ] **Step 2: Incollare la versione definitiva in `app.js`**

Subito dopo `buildWhatsAppMessageBar` (dopo la riga 3690, prima di `function copyToClipboard`):

```javascript
function buildCertificatoDiCuraMessage(customer, redemption, ecosistemaNomi, beneficiarioNuovo) {
  const nomiEcosistema = ecosistemaNomi.length
    ? ecosistemaNomi.join(", ")
    : "gli esercizi aderenti a Salute Quotidiana";

  const lines = [
    `Certificato di Cura — ${formatDate(redemption.createdAt)}`,
    "",
    `${redemption.service} per ${customer.firstName} ${customer.lastName}.`,
    `Valore della prestazione: ${formatMoney(redemption.servicePrice)} euro.`,
    `Credito Salute SQ applicato: ${formatMoney(redemption.creditUsed)} euro.`,
    "",
    `Questa prestazione e' stata resa possibile dalla generosita' dell'ecosistema Salute Quotidiana: ${nomiEcosistema}.`,
    "Ogni consumazione fatta in questi esercizi da chi partecipa al progetto diventa cura per qualcun altro in paese."
  ];

  if (beneficiarioNuovo) {
    lines.push(
      "",
      `Se vuoi conoscere l'ecosistema Salute Quotidiana, sei invitato — senza alcun obbligo — a fare una consumazione o un acquisto presso ${nomiEcosistema}.`,
      `Per i prossimi ${ECOSISTEMA_INVITO_GIORNI_VALIDITA} giorni avrai un piccolo sconto (${ECOSISTEMA_INVITO_SCONTO_PERCENT}%) sul tuo primo acquisto.`
    );
  }

  lines.push("", "Grazie di cuore — Salute Quotidiana");
  return lines.join("\n");
}
```

- [ ] **Step 3: Commit**

```bash
git add app.js
git commit -m "certificato-cura: testo messaggio WhatsApp certificato di cura"
```

---

### Task 5: Area UI digitale + wiring in `handleRedemptionSubmit`

**Files:**
- Modify: `index.html` — dopo il blocco `redemptionMessageArea` (circa riga 450-454)
- Modify: `app.js` — `el` object (riga 101-180), `handleRedemptionSubmit` (righe 2044-2126), event wiring (riga ~885)
- Modify: `styles.css` — dopo lo stile `.whatsapp-message-area`/`.whatsapp-message-box` esistente

**Interfaces:**
- Consuma: `buildCertificatoDiCuraMessage` (Task 4), `isBeneficiarioNuovoNelEcosistema` (Task 3), `ecosistemaBarNomi` (Task 2), `copyToClipboard` (esistente).
- Produce: `el.certificatoCuraArea`, `el.certificatoCuraText`, `el.copyCertificatoCuraBtn`; funzione `function copyCertificatoCura()`, usata anche da Task 6.

- [ ] **Step 1: HTML — nuova area sotto il messaggio bar**

In `index.html`, subito dopo il blocco che chiude `redemptionMessageArea` (dopo `</div>` che segue `copyBarPaymentBtn`, circa riga 454, prima di `<div class="mini-list" id="redemptionHistory"></div>`):

```html
            <div id="certificatoCuraArea" hidden class="whatsapp-message-area">
              <p class="form-label">Certificato di Cura — messaggio per il beneficiario:</p>
              <textarea id="certificatoCuraText" class="whatsapp-message-box" readonly rows="8"></textarea>
              <div class="camera-tool__actions">
                <button class="secondary" type="button" id="copyCertificatoCuraBtn">Copia messaggio</button>
                <button class="secondary" type="button" id="openCertificatoStampabileBtn">Apri versione stampabile</button>
              </div>
            </div>
```

- [ ] **Step 2: `app.js` — nuovi `el` refs**

In `app.js`, dentro l'oggetto `el` (subito dopo `copyBarPaymentBtn: document.querySelector("#copyBarPaymentBtn"),` circa riga 179, prima delle chiavi `qrScontrinoArea`):

```javascript
  certificatoCuraArea: document.querySelector("#certificatoCuraArea"),
  certificatoCuraText: document.querySelector("#certificatoCuraText"),
  copyCertificatoCuraBtn: document.querySelector("#copyCertificatoCuraBtn"),
  openCertificatoStampabileBtn: document.querySelector("#openCertificatoStampabileBtn"),
```

- [ ] **Step 3: `app.js` — funzione `copyCertificatoCura` e variabile di stato**

Vicino a `let lastRedemptionId = null;` (riga 3378), aggiungi:

```javascript
let lastCertificatoCuraText = "";
```

Subito dopo `copyBarPaymentMessage` (dopo riga 3859, prima di `// --- end v45 ---`):

```javascript
function copyCertificatoCura() {
  if (!lastCertificatoCuraText) return;
  copyToClipboard(lastCertificatoCuraText, "Certificato di Cura copiato!");
}
```

- [ ] **Step 4: `app.js` — wiring eventi**

Vicino alla riga `if (el.copyBarPaymentBtn) el.copyBarPaymentBtn.addEventListener(...)` (circa riga 886), aggiungi:

```javascript
  if (el.copyCertificatoCuraBtn) el.copyCertificatoCuraBtn.addEventListener("click", copyCertificatoCura);
  if (el.openCertificatoStampabileBtn) el.openCertificatoStampabileBtn.addEventListener("click", () => {
    if (lastCertificatoCuraText && lastCertificatoCuraContext) {
      openCertificatoStampabile(lastCertificatoCuraContext.customer, lastCertificatoCuraContext.redemption, lastCertificatoCuraText);
    }
  });
```

(`openCertificatoStampabile` e `lastCertificatoCuraContext` vengono creati nel Task 6 — questo passo lascia il riferimento pronto, l'app funziona comunque perche' la funzione viene chiamata solo al click, non al caricamento pagina.)

- [ ] **Step 5: `app.js` — generare il certificato dentro `handleRedemptionSubmit`**

In `handleRedemptionSubmit` (righe 2044-2126), subito dopo il blocco esistente:

```javascript
  lastRedemptionId = supabaseResult.id || redemption.id;
  const barMsg = buildWhatsAppMessageBar(customer, { ...redemption, id: lastRedemptionId });
  if (el.redemptionBarText) el.redemptionBarText.value = barMsg;
  if (el.redemptionMessageArea) el.redemptionMessageArea.hidden = false;
```

aggiungi:

```javascript
  const beneficiaryPhone = cleanText(form.get("beneficiaryPhone"));
  const beneficiarioNuovo = await isBeneficiarioNuovoNelEcosistema(beneficiaryPhone);
  const certificatoMsg = buildCertificatoDiCuraMessage(customer, { ...redemption, id: lastRedemptionId }, ecosistemaBarNomi, beneficiarioNuovo);
  lastCertificatoCuraText = certificatoMsg;
  lastCertificatoCuraContext = { customer, redemption: { ...redemption, id: lastRedemptionId } };
  if (el.certificatoCuraText) el.certificatoCuraText.value = certificatoMsg;
  if (el.certificatoCuraArea) el.certificatoCuraArea.hidden = false;
```

Aggiungi anche la dichiarazione della variabile di contesto vicino a `let lastCertificatoCuraText = "";` (Step 3):

```javascript
let lastCertificatoCuraContext = null;
```

- [ ] **Step 6: `styles.css` — riuso pattern esistente**

Verifica che `.whatsapp-message-area` e `.whatsapp-message-box` esistano già (usate da `cassiereMessageArea`/`redemptionMessageArea`). Se esistono (atteso, dato che l'HTML del Task 1/5 le riusa), **nessuna nuova classe CSS è necessaria** — salta questo step. Se durante la verifica manuale il blocco appare senza stile, aggiungi in `styles.css` dopo la definizione di `.whatsapp-message-box`:

```css
#certificatoCuraArea .camera-tool__actions {
  margin-top: 10px;
}
```

- [ ] **Step 7: Verifica manuale end-to-end**

Nel tab "Salute Quotidiana", registra una prestazione per un cliente con credito disponibile, beneficiario "se stesso". Dopo l'invio: deve comparire — sotto il messaggio bar esistente — la nuova area "Certificato di Cura" con il testo generato, SENZA la frase di invito ecosistema (beneficiario e' il cliente stesso, gia' presente nel sistema). Ripeti con beneficiario "familiare" + telefono di una persona non registrata: il testo deve includere la frase di invito con lo sconto. Verifica che il pulsante "Copia messaggio" copi il testo negli appunti (controlla `Ctrl+V` in un editor).

- [ ] **Step 8: Commit**

```bash
git add index.html app.js styles.css
git commit -m "certificato-cura: area digitale WhatsApp e wiring in registrazione prestazione"
```

---

### Task 6: Versione stampabile

**Files:**
- Modify: `app.js` — aggiungere subito dopo `copyCertificatoCura` (Task 5, Step 3)

**Interfaces:**
- Consuma: `escapeHtml`, `formatMoney`, `formatDate` (esistenti).
- Produce: `function buildCertificatoStampabileHtml(customer, redemption, message)` → stringa HTML completa; `function openCertificatoStampabile(customer, redemption, message)` — apre una nuova scheda con `window.open` e stampa. Usata dal wiring del Task 5, Step 4.

- [ ] **Step 1: Implementare `buildCertificatoStampabileHtml` e `openCertificatoStampabile`**

```javascript
function buildCertificatoStampabileHtml(customer, redemption, message) {
  const safeMessage = escapeHtml(message).replace(/\n/g, "<br>");
  return `<!doctype html>
<html lang="it">
<head>
<meta charset="utf-8">
<title>Certificato di Cura</title>
<style>
  body { font-family: Georgia, serif; max-width: 640px; margin: 40px auto; padding: 24px; border: 2px solid #1d6ab5; border-radius: 12px; color: #1c2b1f; }
  h1 { font-size: 22px; color: #1d6ab5; text-align: center; margin-bottom: 24px; }
  p { font-size: 15px; line-height: 1.6; }
  .firma { margin-top: 40px; font-style: italic; text-align: right; }
  @media print { body { border: none; } }
</style>
</head>
<body>
  <h1>Certificato di Cura</h1>
  <p>${safeMessage}</p>
  <p class="firma">Salute Quotidiana — ${escapeHtml(customer.firstName)} ${escapeHtml(customer.lastName)}</p>
</body>
</html>`;
}

function openCertificatoStampabile(customer, redemption, message) {
  const html = buildCertificatoStampabileHtml(customer, redemption, message);
  const win = window.open("", "_blank");
  if (!win) {
    showToast("Il browser ha bloccato l'apertura della nuova scheda. Consenti i popup per stampare il certificato.");
    return;
  }
  win.document.write(html);
  win.document.close();
  win.focus();
  win.print();
}
```

- [ ] **Step 2: Verifica manuale**

Dopo aver registrato una prestazione (Task 5, Step 7), clicca "Apri versione stampabile": deve aprirsi una nuova scheda con il certificato formattato e la finestra di stampa del browser deve attivarsi automaticamente. Se il browser blocca il popup, deve comparire il messaggio toast di avviso invece di un errore silenzioso.

- [ ] **Step 3: Commit**

```bash
git add app.js
git commit -m "certificato-cura: versione stampabile del certificato"
```

---

### Task 7: Bump versione e verifica finale

**Files:**
- Modify: `app.js:2` (`APP_VERSION`)
- Modify: `index.html:13,506` (query string cache-busting)

**Interfaces:** Nessuna — task di chiusura.

- [ ] **Step 1: Bump versione**

In `app.js`:
```javascript
const APP_VERSION = "v53";
```

In `index.html`:
```html
    <link rel="stylesheet" href="styles.css?v=56">
```
```html
    <script src="app.js?v=53"></script>
```

- [ ] **Step 2: `node --check app.js`**

Esegui: `node --check app.js`
Atteso: nessun output, exit code 0.

- [ ] **Step 3: Verifica manuale completa nel browser**

Ricarica l'app, verifica in alto a destra che appaia `(v53)`. Ripeti il flusso end-to-end del Task 5 Step 7 e Task 6 Step 2 per confermare che tutto funzioni con la versione bumpata. Verifica che il flusso QR (v52, invariato) funzioni ancora: carica uno scontrino cliente, controlla che il QR compaia normalmente.

- [ ] **Step 4: Commit**

```bash
git add app.js index.html
git commit -m "v53: certificato di cura per ogni prestazione confermata"
```

---

## Self-Review Note (svolta durante la stesura di questo piano)

- **Copertura spec:** trigger ad ogni prestazione (Task 5) ✓, accredito collettivo ecosistema (Task 2+4) ✓, invito se beneficiario nuovo con sconto a tempo (Task 1+3+4) ✓, formato WhatsApp (Task 5) ✓, formato stampabile (Task 6) ✓.
- **Placeholder scan:** nessun "TBD"/"gestisci errori appropriati" — ogni step ha codice completo.
- **Coerenza tipi/nomi:** `buildCertificatoDiCuraMessage(customer, redemption, ecosistemaNomi, beneficiarioNuovo)` usato identico in Task 4 e Task 5; `lastCertificatoCuraText`/`lastCertificatoCuraContext` dichiarate in Task 5 Step 3 e usate in Task 5 Step 4 e Task 6.
