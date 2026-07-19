# Piano operativo progetto - Credito Salute SQ

Aggiornato al 2 luglio 2026.

## 1. Obiettivo del progetto

Credito Salute SQ e' una mini web app per il pilot locale nel bar pilota di Francofonte.

Obiettivo pratico:

1. Il cliente si registra in autonomia.
2. Il cliente carica lo scontrino.
3. Il sistema calcola il 15% come Credito SQ.
4. Lo scontrino viene verificato.
5. Salute Quotidiana usa il credito confermato su prestazioni semplici e non urgenti.

La web app deve restare semplice: frontend statico, Supabase come backend, nessun server Node separato.

## 2. Stato tecnico attuale

File principali:

1. `index.html`: struttura schermate, form, tab e caricamento script.
2. `styles.css`: stile responsive e layout.
3. `app.js`: logica completa dell'app.
4. `supabase-config.js`: collegamento a Supabase con chiave anonima/pubblica.
5. `docs/`: schema database, RLS, RPC e documentazione ruoli.

Versione frontend attuale:

```text
v33-report-bar
```

Controllo eseguito:

```text
node --check app.js
```

Risultato: nessun errore sintattico bloccante in `app.js`.

## 3. Ruoli da mantenere

### Cliente

Deve vedere solo:

1. `Cliente`;
2. `Regole`.

Non deve vedere:

1. altri clienti;
2. report generale;
3. verifica scontrini;
4. utilizzi credito di altri;
5. dati sanitari.

### Titolare bar

Deve vedere solo dati operativi del proprio bar.

Puo' vedere:

1. scontrini del bar;
2. conteggi aggregati;
3. andamento generale del pilot.

Non deve vedere:

1. prestazioni sanitarie usate;
2. beneficiari;
3. note sanitarie;
4. dati di altri bar futuri.

### Salute Quotidiana

Puo' vedere e gestire:

1. clienti;
2. scontrini;
3. verifiche;
4. utilizzi credito;
5. report completo;
6. correzioni operative.

## 4. Problema prioritario risolto

Il problema piu' importante era:

```text
dopo login cliente, se la scheda cliente esiste gia', la web app deve caricarla automaticamente,
nascondere il form Nuovo cliente SQ e mostrare saldo/storico senza tendina cliente.
```

Intervento completato nella versione:

```text
v33-report-bar
```

Risultato:

1. il ruolo `cliente` carica i dati da Supabase dopo il login;
2. i dati locali generici vengono svuotati al login cliente;
3. se Supabase restituisce una sola scheda cliente autorizzata, viene selezionata automaticamente;
4. se la scheda cliente esiste gia', il form `Nuovo cliente SQ` viene nascosto;
5. le tendine cliente vengono nascoste per il ruolo `cliente`;
6. scontrini, saldi e utilizzi credito vengono filtrati sul cliente corrente;
7. durante il caricamento dati Supabase, il form cliente non compare come nuova iscrizione;
8. il riconoscimento cliente usa `profilo_id` ed email quando la vista Supabase li espone;
9. se non viene trovata una scheda collegata, il cliente vede solo `Completa il tuo profilo`;
10. l'app prova a chiamare la RPC `collega_cliente_corrente_pilot` per collegare automaticamente un cliente esistente non ancora associato al profilo.

Perche' era prioritario:

1. evita doppie iscrizioni;
2. migliora molto l'esperienza cliente da telefono;
3. riduce errori al bar;
4. allinea frontend, documentazione e regole privacy.

## 5. Interventi consigliati in ordine

### Step 1 - Flusso cliente gia' registrato

Stato: completato e rifinito in `v32-riconoscimento-cliente-email-profilo`.

Obiettivo:

1. trovare il record `clienti` collegato al profilo Supabase;
2. selezionarlo automaticamente;
3. nascondere il form `Nuovo cliente SQ`;
4. nascondere o bloccare le tendine cliente per ruolo `cliente`;
5. lasciare saldo, storico e caricamento scontrino pronti per quel cliente.

Criterio di verifica:

1. login cliente nuovo: vede compilazione scheda se non esiste;
2. login cliente gia' censito: non vede il form nuova iscrizione;
3. il saldo mostra solo i suoi dati;
4. non puo' scegliere altri clienti.

### Step 2 - Allineamento ruolo bar

Stato: completato in `v33-report-bar`.

Obiettivo:

1. mantenere `titolare_bar` come ruolo database;
2. normalizzarlo a `bar` solo nel frontend;
3. aggiungere tab/report bar dedicato;
4. usare la RPC `report_bar_corrente_pilot` per non esporre dati sanitari.

Criterio di verifica:

1. un utente `titolare_bar` entra correttamente;
2. non vede dati sanitari;
3. vede solo aggregati e scontrini autorizzati.

### Step 3 - Report bar separato

Stato: completato in `v33-report-bar`, da attivare in Supabase eseguendo:

```text
docs/supabase-report-bar-corrente-pilot.sql
```

Obiettivo:

1. creare una vista o RPC Supabase con soli dati aggregati;
2. mostrare nel frontend una sezione separata dal report completo;
3. impedire accesso a utilizzi credito e beneficiari.

Criterio di verifica:

1. il bar vede conteggi e importi aggregati;
2. Salute Quotidiana continua a vedere il report completo;
3. il cliente non vede nessun report.

### Step 4 - Verifica sicurezza Supabase

Obiettivo:

1. controllare RLS su `profili`, `clienti`, `scontrini`, `utilizzi_credito`;
2. verificare che il frontend non sia l'unica barriera di sicurezza;
3. spostare azioni critiche in RPC quando serve.

Criterio di verifica:

1. cliente non legge altri clienti;
2. bar non legge utilizzi credito;
3. utente non autenticato non accede a dati operativi;
4. ruoli privilegiati non possono essere scelti in registrazione pubblica.

## 6. Rischi attuali

1. La repository Git rilevata parte da `C:/Users/angel`, non dalla cartella del progetto. Quindi `git status` mostra moltissimi file esterni e non e' affidabile per questo progetto.
2. Il frontend nasconde le sezioni, ma la sicurezza vera deve restare nelle policy RLS di Supabase.
3. OCR puo' sbagliare importo, data o numero documento: il controllo manuale resta necessario.
4. Il ruolo `titolare_bar` e il ruolo frontend `bar` vanno tenuti allineati per evitare accessi sbagliati.
5. `localStorage` resta un fallback utile, ma non deve diventare la fonte principale dei dati reali.

## 7. Regola sanitaria e privacy

La web app non deve diventare uno strumento clinico.

Non deve gestire:

1. diagnosi;
2. referti;
3. urgenze;
4. terapie;
5. valutazioni cliniche.

Messaggio operativo da mantenere:

```text
Per sintomi importanti, dolore toracico, difficolta' respiratoria, svenimento o peggioramento clinico,
contattare medico, guardia medica, 112/118 o Pronto Soccorso.
```

## 8. Metodo di lavoro consigliato

Per ogni modifica:

1. fare un intervento piccolo;
2. verificare il flusso interessato;
3. aggiornare README o documento tecnico se cambia il comportamento;
4. non mescolare refactor estetici con correzioni funzionali;
5. testare almeno cliente, titolare bar e Salute Quotidiana.

## 9. Prossima azione consigliata

La prossima azione migliore e':

```text
testare Step 1 con un account cliente reale gia' collegato a un record clienti.
```

E' la scelta migliore perche' conferma che le policy RLS di Supabase restituiscono davvero solo la scheda del cliente autenticato.

Se il cliente esiste ma non viene caricato, eseguire prima in Supabase:

```text
docs/supabase-collega-cliente-corrente-pilot.sql
```
