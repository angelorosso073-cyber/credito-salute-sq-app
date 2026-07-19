# Credito Salute SQ
## Manuale operativo interno
### Riservato agli operatori Salute Quotidiana

---

## 1. Parametri del programma

| Parametro | Valore |
|---|---|
| Formula credito | 15% della spesa valida |
| Equivalenza | 1 euro SQ = 1 euro di sconto |
| Fondo tipico per ciclo | 1.000 euro |
| Tetto per cliente | 50 euro SQ |
| Clienti massimi per ciclo | 20 |
| Durata ciclo standard | 30 giorni |

---

## 2. Gestione iscrizioni

Il cliente si iscrive in autonomia tramite l'applicazione. L'operatore non iscrive i clienti manualmente, salvo casi di assistenza esplicita.

**Dati richiesti all'iscrizione:** nome, cognome, email, consenso al trattamento dei dati.

**Associazione profilo:** l'applicazione collega automaticamente il profilo di autenticazione al record cliente. Se l'associazione non avviene, eseguire manualmente la RPC `collega_cliente_corrente_pilot` dal pannello Supabase.

**Doppie iscrizioni:** il sistema blocca la creazione di un secondo profilo sulla stessa email. In caso di segnalazione, verificare in Supabase l'esistenza del record. Non creare duplicati.

**Limite iscrizioni:** al raggiungimento del numero massimo di clienti previsto per il ciclo, sospendere le nuove iscrizioni. Aggiornare lo stato nel pannello di controllo.

---

## 3. Verifica scontrini

### Flusso

Lo scontrino caricato dal cliente entra in stato **in attesa**. L'operatore accede al pannello, verifica manualmente ogni scontrino e aggiorna lo stato.

- Scontrino valido → stato **verificato** → credito confermato automaticamente.
- Scontrino non valido → stato **rifiutato** → credito non confermato.

### Criteri di validità

Uno scontrino è valido se:
- è uno scontrino fiscale leggibile;
- è riferito all'esercizio commerciale aderente al programma;
- la data rientra nel periodo attivo del ciclo;
- l'importo è leggibile e corrisponde alla foto;
- non è già stato caricato in precedenza.

### Criteri di rifiuto

Rifiutare se:
- data fuori periodo;
- esercizio non corrispondente;
- immagine illeggibile o parziale;
- scontrino duplicato;
- importo OCR non corrispondente e non corretto manualmente dal cliente.

### Comunicazione al cliente in caso di rifiuto

Comunicare con tono neutro e non sanzionatorio. Esempio: *"Lo scontrino che hai caricato non è leggibile nella parte dell'importo. Puoi riprovare con una foto più nitida?"*

---

## 4. Gestione del fondo

**Monitoraggio:** l'operatore monitora in ogni momento il fondo residuo.

- Fondo stanziato: importo versato dall'esercizio commerciale.
- Credito confermato: somma del credito verificato di tutti i clienti (non riduce il fondo).
- Credito utilizzato: somma degli utilizzi confermati (riduce il fondo).
- **Fondo residuo = fondo stanziato − credito utilizzato.**

**Soglia di allerta:** quando il fondo residuo scende sotto il 20% dell'importo iniziale, avvisare il responsabile di progetto prima di confermare nuovi utilizzi.

**Esaurimento fondo:** se il fondo si esaurisce prima della fine del ciclo, sospendere immediatamente i nuovi utilizzi e comunicarlo ai clienti con credito disponibile. Non generare esposizioni oltre il fondo.

---

## 5. Gestione richieste di utilizzo credito

### Flusso

1. Il cliente contatta Salute Quotidiana per prenotare una prestazione.
2. L'operatore verifica il saldo del cliente e il fondo residuo.
3. L'operatore conferma la prenotazione con: prestazione richiesta, costo, credito applicato, eventuale differenza a carico del cliente.
4. L'infermiere esegue la prestazione.
5. L'operatore registra l'utilizzo e aggiorna il saldo del cliente.

### Utilizzo per familiare convivente

Il cliente può richiedere la prestazione per un familiare convivente. Annotare nome del destinatario nella registrazione dell'utilizzo. Non è richiesta documentazione del rapporto di convivenza.

### Prestazioni con prescrizione

Le seguenti prestazioni richiedono prescrizione medica valida prima della conferma della prenotazione:
- Iniezione intramuscolare I.M.
- Catetere vescicale a permanenza / cateterismo estemporaneo
- Posizionamento e gestione sondino naso gastrico

Se la prescrizione non è disponibile al momento della richiesta, la prenotazione non viene confermata e il credito non viene scalato.

---

## 6. Privacy e separazione dei dati

L'esercizio commerciale aderente riceve esclusivamente il report aggregato anonimo. Non ha accesso a:
- dati nominativi dei clienti;
- saldi individuali;
- prestazioni utilizzate;
- qualsiasi informazione sanitaria.

Salute Quotidiana gestisce e conserva: profili clienti, scontrini, utilizzi credito, fondo. I dati dei clienti sono usati esclusivamente per la gestione del programma. In caso di richiesta di cancellazione, eliminare il profilo e segnalare al responsabile privacy.

---

## 7. Report finale

A chiusura del ciclo, il report da consegnare all'esercizio commerciale include:

- numero totale clienti iscritti
- numero scontrini caricati / verificati / rifiutati
- credito totale confermato
- credito totale utilizzato
- fondo residuo
- numero prestazioni erogate per tipologia (non per beneficiario)

Il report non contiene dati nominativi, prestazioni associate a singole persone, o qualsiasi dato che consenta di risalire a un individuo specifico.

---

## 8. Gestione anomalie

| Anomalia | Azione |
|---|---|
| Cliente non riesce a iscriversi | Assistenza manuale, verifica profilo Supabase, RPC di collegamento |
| Importo OCR errato | Correzione manuale prima della verifica, nota interna |
| Cliente supera il tetto credito | Blocco utilizzo ulteriore; comunicare il limite raggiunto |
| Richiesta di prestazione urgente | Non accettare; indicare 112/118 o Pronto Soccorso |
| Fondo esaurito | Blocco nuovi utilizzi; comunicazione ai clienti con credito in attesa |
| Scontrino duplicato | Rifiuto; comunicazione al cliente |
| Cliente non trovato nel sistema | Verificare associazione profilo-cliente; non creare duplicati |

---

## 9. Messaggi operativi standard

**In caso di richiesta urgente da parte del cliente:**

> "Per qualsiasi sintomo urgente — dolore toracico, difficoltà respiratoria, svenimento o peggioramento improvviso — chiama subito il 112/118 o vai al Pronto Soccorso. Il servizio Salute Quotidiana gestisce prestazioni programmate e non risponde a emergenze."

**In caso di richiesta di diagnosi o interpretazione referti:**

> "Questa è una valutazione che spetta al medico di base. Salute Quotidiana si occupa di prestazioni infermieristiche programmate. Per tutto il resto, il riferimento giusto è il tuo medico."

Questi messaggi vanno comunicati con chiarezza e senza esitazione in qualsiasi contesto.
