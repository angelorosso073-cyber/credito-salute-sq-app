// Verifica strutturale su index.html: ogni campo che submitReceipt legge via
// new FormData(receiptForm) deve stare DENTRO <form id="receiptForm">.
//
// Perche' esiste questo test: il campo del codice banco era finito fuori dal
// form (dopo </form>). L'app lo compilava correttamente a schermo, ma FormData
// non lo leggeva: al server arrivava p_codice_banco = null e ogni scontrino
// finiva in sospeso con motivo 'codice_banco_mancante', anche scansionando il
// QR del banco al momento giusto.

const fs = require("fs");
const path = require("path");

const html = fs.readFileSync(path.join(__dirname, "..", "index.html"), "utf8");

// Campi letti da form.get(...) dentro submitReceipt (app.js).
const CAMPI_ATTESI = [
  "receiptDate",
  "receiptTime",
  "documentNumber",
  "matricolaRt",
  "codiceBanco",
  "amount",
  "validConsumption",
  "receiptImage"
];

const aperturaForm = html.indexOf('<form id="receiptForm"');
if (aperturaForm === -1) {
  console.error('FALLITO: <form id="receiptForm"> non trovato in index.html');
  process.exit(1);
}

const chiusuraForm = html.indexOf("</form>", aperturaForm);
if (chiusuraForm === -1) {
  console.error("FALLITO: </form> di receiptForm non trovato");
  process.exit(1);
}

let falliti = 0;

for (const campo of CAMPI_ATTESI) {
  const posizione = html.indexOf(`name="${campo}"`);

  if (posizione === -1) {
    console.error(`FALLITO ${campo}: nessun input con name="${campo}" in index.html`);
    falliti += 1;
    continue;
  }

  const dentroIlForm = posizione > aperturaForm && posizione < chiusuraForm;
  const rigaCampo = html.slice(0, posizione).split("\n").length;
  const rigaChiusura = html.slice(0, chiusuraForm).split("\n").length;

  if (dentroIlForm) {
    console.log(`OK      ${campo} (riga ${rigaCampo}, dentro il form)`);
  } else {
    console.error(
      `FALLITO ${campo}: riga ${rigaCampo}, fuori dal form (</form> a riga ${rigaChiusura}). ` +
      "FormData non lo leggera' mai."
    );
    falliti += 1;
  }
}

if (falliti > 0) {
  console.error(`\n${falliti} campo/i fuori dal form.`);
  process.exit(1);
}

console.log(`\nTutti i ${CAMPI_ATTESI.length} campi sono dentro il form.`);
