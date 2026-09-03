// Verifica che findDuplicateReceipt riconosca come doppione lo stesso
// scontrino anche quando l'OCR ne ha letto un importo diverso.
//
// Caso reale: documento 2319-0004 del 02/09/2026 e' stato accettato due volte
// perche' letto una volta 1,20 e una volta 1.28. Il server ora ignora
// l'importo nella chiave; il browser deve fare altrettanto, altrimenti i due
// controlli non concordano e il browser blocca caricamenti che il server
// accetterebbe, o viceversa.
//
// La funzione viene estratta da app.js invece di essere riscritta qui: cosi'
// il test non puo' divergere dal codice che va in produzione.

const fs = require("fs");
const path = require("path");

const sorgente = fs.readFileSync(path.join(__dirname, "..", "app.js"), "utf8");

const inizio = sorgente.indexOf("function findDuplicateReceipt");
if (inizio === -1) {
  console.error("FALLITO: findDuplicateReceipt non trovata in app.js");
  process.exit(1);
}
const fine = sorgente.indexOf("\n}", inizio) + 2;
const corpoFunzione = sorgente.slice(inizio, fine);

// Dipendenze minime usate dalla funzione estratta.
const cleanText = (valore) => String(valore ?? "").trim();
const roundMoney = (valore) => Math.round(Number(valore) * 100) / 100;
const state = { receipts: [] };

const findDuplicateReceipt = new Function(
  "state", "cleanText", "roundMoney",
  `${corpoFunzione}; return findDuplicateReceipt;`
)(state, cleanText, roundMoney);

const giaCaricato = {
  barName: "Bar pilota Francofonte",
  receiptDate: "2026-09-02",
  documentNumber: "2319-0004",
  amount: 1.20,
  status: "pending"
};

const casi = [
  {
    nome: "stesso scontrino, importo letto diverso",
    nuovo: { barName: "Bar pilota Francofonte", receiptDate: "2026-09-02", documentNumber: "2319-0004", amount: 1.28 },
    atteso: true
  },
  {
    nome: "stesso scontrino, importo identico",
    nuovo: { barName: "Bar pilota Francofonte", receiptDate: "2026-09-02", documentNumber: "2319-0004", amount: 1.20 },
    atteso: true
  },
  {
    nome: "documento diverso, stesso giorno",
    nuovo: { barName: "Bar pilota Francofonte", receiptDate: "2026-09-02", documentNumber: "2319-0005", amount: 1.20 },
    atteso: false
  },
  {
    nome: "stesso documento, giorno diverso",
    nuovo: { barName: "Bar pilota Francofonte", receiptDate: "2026-09-03", documentNumber: "2319-0004", amount: 1.20 },
    atteso: false
  }
];

let falliti = 0;
for (const caso of casi) {
  state.receipts = [{ ...giaCaricato }];
  const trovato = Boolean(findDuplicateReceipt(caso.nuovo));
  const ok = trovato === caso.atteso;
  if (!ok) falliti += 1;
  console.log(`${ok ? "OK     " : "FALLITO"} ${caso.nome} (doppione=${trovato}, atteso=${caso.atteso})`);
}

// Uno scontrino rifiutato non deve piu' bloccare un nuovo caricamento.
state.receipts = [{ ...giaCaricato, status: "rejected" }];
const dopoRifiuto = Boolean(findDuplicateReceipt({
  barName: "Bar pilota Francofonte", receiptDate: "2026-09-02", documentNumber: "2319-0004", amount: 1.20
}));
if (dopoRifiuto) {
  console.error("FALLITO uno scontrino rifiutato blocca ancora il ricaricamento");
  falliti += 1;
} else {
  console.log("OK      uno scontrino rifiutato non blocca il ricaricamento");
}

if (falliti > 0) {
  console.error(`\n${falliti} casi falliti.`);
  process.exit(1);
}
console.log("\nTutti i casi come atteso.");
