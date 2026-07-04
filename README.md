# Credito Salute SQ - Mini Web App

Mini web app per il pilot Credito Salute SQ nel bar pilota di Francofonte.

Stato aggiornato: 2 luglio 2026.

## 1. Come aprirla

1. Aprire questo file nel browser:

```text
index.html
```

2. Premere:

```text
Ctrl + F5
```

Questo forza Chrome o Edge a caricare l'ultima versione dei file.

Non serve installare nulla. Il progetto non ha `package.json`.

## 2. Stato tecnico attuale

La web app usa:

1. HTML, CSS e JavaScript statici.
2. Supabase Auth per login e registrazione.
3. Supabase Database per profili, clienti, scontrini, saldi e utilizzi credito.
4. Tesseract.js da CDN per OCR, cioe' lettura automatica del testo da foto.

Serve connessione internet per:

1. login Supabase;
2. registrazione account;
3. lettura/scrittura dati su Supabase;
4. OCR tramite libreria caricata da CDN.

## 3. Versione frontend

La versione attuale dell'app e':

```text
v32-riconoscimento-cliente-email-profilo
```

In `index.html` viene caricato:

```html
<script src="app.js?v=32"></script>
```

Se il browser mostra comportamenti vecchi, premere `Ctrl + F5`.

## 4. Accesso obbligatorio

All'apertura la web app deve mostrare solo:

1. intestazione;
2. stato Supabase;
3. form login;
4. sezione apribile `Crea account cliente`.

Prima del login non devono comparire:

1. `Cliente`;
2. `Verifica SQ`;
3. `Salute Quotidiana`;
4. `Report`;
5. `Regole`.

## 5. Registrazione cliente

La registrazione pubblica e' prevista solo per il cliente.

Il cliente inserisce:

1. nome;
2. cognome;
3. telefono;
4. comune;
5. email;
6. password;
7. consenso contatto;
8. accettazione regolamento pilot.

La registrazione crea un account Supabase Auth con ruolo:

```text
cliente
```

Il cliente non puo' scegliere ruoli come:

1. `bar`;
2. `salute_quotidiana`;
3. `admin`.

Motivo: sarebbe un rischio di sicurezza e privacy.

## 6. Ruoli attuali

### Cliente

Il cliente deve vedere solo:

1. `Cliente`;
2. `Regole`.

Obiettivo corretto del flusso:

1. se il cliente non ha ancora una scheda cliente completa, puo' completarla;
2. se il cliente e' gia' registrato in Supabase, non dovrebbe vedere di nuovo la sezione iscrizione;
3. il saldo dovrebbe mostrare direttamente il suo profilo, senza tendina da scegliere.

Nota stato attuale:

1. login cliente funzionante;
2. profilo cliente trovato;
3. se Supabase/RLS restituisce la scheda cliente collegata, il saldo viene mostrato automaticamente;
4. se la scheda cliente esiste gia', la sezione `Nuovo cliente SQ` viene nascosta;
5. per il ruolo cliente le tendine cliente vengono nascoste e il cliente corrente viene selezionato automaticamente;
6. durante il caricamento dati Supabase, la scheda cliente non viene mostrata come nuova iscrizione;
7. il riconoscimento cliente usa, quando disponibili, `profilo_id`, email, telefono o nome/cognome;
8. se il cliente risulta registrato ma la scheda non viene caricata, viene mostrato solo `Completa il tuo profilo`, oppure bisogna eseguire in Supabase `docs/supabase-diagnosi-fix-cliente-test.sql`.

### Titolare bar

Decisione di prodotto:

1. il titolare non deve registrare clienti come flusso principale;
2. il titolare puo' avere un resoconto generale del pilot;
3. il resoconto deve essere limitato ai dati del bar e non deve includere dati sanitari.

Il titolare puo' vedere:

1. numero clienti iscritti collegati al bar;
2. numero scontrini caricati;
3. scontrini in verifica;
4. scontrini confermati;
5. totale consumazioni confermate;
6. credito SQ generato nel bar;
7. andamento generale del pilot.

Il titolare non deve vedere:

1. prestazioni sanitarie usate;
2. beneficiari delle prestazioni;
3. note sanitarie o interne Salute Quotidiana;
4. dati di altri bar futuri.

### Salute Quotidiana

Salute Quotidiana deve poter vedere:

1. `Cliente`;
2. `Verifica SQ`;
3. `Salute Quotidiana`;
4. `Report`;
5. `Regole`.

Salute Quotidiana puo':

1. controllare scontrini;
2. confermare, correggere o rifiutare scontrini;
3. registrare utilizzi credito;
4. monitorare saldi e report;
5. intervenire sui clienti in caso di errore operativo.

## 7. Cosa fa la web app

1. Blocca le sezioni operative prima del login.
2. Permette login con Supabase Auth.
3. Permette registrazione autonoma del cliente.
4. Mostra le sezioni in base al ruolo.
5. Registra clienti SQ.
6. Limita il pilot a 20 clienti.
7. Carica foto scontrino.
8. Prova a leggere automaticamente data, ora, numero documento e importo dalla foto.
9. Permette correzione manuale dei dati letti.
10. Calcola il 3% come Credito SQ.
11. Tiene il credito in verifica.
12. Permette verifica e gestione scontrini lato Salute Quotidiana.
13. Registra utilizzo del credito su prestazioni.
14. Esporta dati JSON o CSV per i ruoli autorizzati.

## 8. Regola credito

Formula:

```text
Credito SQ = importo consumazione valida x 0,03
```

Esempio:

```text
10 euro di consumazione = 0,30 euro SQ
```

Regola:

```text
1 euro SQ = 1 euro di sconto su prestazioni Salute Quotidiana.
```

## 9. Prestazioni del pilot

Per ora comunicare solo:

1. controllo parametri base a domicilio: 20 euro;
2. controllo parametri completo a domicilio: 25 euro;
3. parametri + breve educazione sanitaria: 30 euro.

Non comunicare come prima fase:

1. ECG;
2. Holter;
3. medicazioni;
4. iniezioni;
5. prestazioni urgenti.

## 10. Limiti importanti

1. La sicurezza vera deve stare su Supabase tramite RLS, cioe' regole che limitano quali righe ogni utente puo' leggere o modificare.
2. Il frontend nasconde le sezioni, ma non deve essere considerato da solo una protezione sufficiente.
3. OCR puo' sbagliare: i dati letti dalla foto vanno sempre controllati.
4. Non usare la web app per emergenze, diagnosi, referti o cure.
5. In caso di sintomi seri, dolore toracico, difficolta' respiratoria, svenimento o peggioramento clinico, indirizzare a medico, guardia medica, 112/118 o Pronto Soccorso.

## 11. Prossima correzione consigliata

Priorita' tecnica:

1. testare il flusso cliente con un account reale gia' collegato a `clienti`;
2. verificare che Supabase/RLS restituisca solo la scheda del cliente autenticato;
3. se il cliente non viene trovato, eseguire `docs/supabase-collega-cliente-corrente-pilot.sql`;
4. lasciare la creazione/correzione clienti a Salute Quotidiana come funzione separata;
5. aggiungere `Report Bar` limitato al titolare.
