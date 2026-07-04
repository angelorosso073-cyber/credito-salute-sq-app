# Credito Salute SQ - Setup Supabase V2

Questa guida spiega cosa fare per preparare Supabase prima di collegare la web app.

## 1. Creare il progetto Supabase

1. Vai su Supabase.
2. Crea un nuovo progetto.
3. Nome consigliato:

```text
credito-salute-sq
```

4. Scegli una password database sicura.
5. Scegli regione Europa, se disponibile.
6. Attendi la creazione del progetto.

## 2. Creare le tabelle

Nel pannello Supabase:

1. Apri `SQL Editor`.
2. Crea una nuova query.
3. Incolla il contenuto del file:

```text
docs/supabase-schema-v2.sql
```

4. Esegui la query.

Questo crea:

1. tabelle principali;
2. indici;
3. vista `saldi_clienti`;
4. primo bar pilota.

## 3. Attivare ruoli e permessi

Sempre in `SQL Editor`:

1. Crea una nuova query.
2. Incolla il contenuto del file:

```text
docs/supabase-rls-v2.sql
```

3. Esegui la query.

Questo crea:

1. funzioni helper per riconoscere il ruolo utente;
2. policy RLS;
3. bucket Storage `foto-scontrini`;
4. permessi per le foto scontrini;
5. vista `scontrini_bar_verifica`.

## 4. Recuperare le chiavi della web app

Nel pannello Supabase:

1. Vai su `Project Settings`.
2. Apri `API`.
3. Copia:
   - `Project URL`;
   - `anon public key`.

Attenzione: usa solo la chiave `anon public`.

Non usare mai nel frontend la chiave `service_role`, perche' ha permessi troppo alti.

## 5. Creare il file di configurazione

Nel progetto locale:

1. Duplica questo file:

```text
supabase-config.example.js
```

2. Rinominalo:

```text
supabase-config.js
```

3. Inserisci dentro:

```js
const SUPABASE_URL = "https://tuo-progetto.supabase.co";
const SUPABASE_ANON_KEY = "tua-chiave-anon-public";
```

## 6. Impostare autenticazione

Nel pannello Supabase:

1. Vai su `Authentication`.
2. Apri `Providers`.
3. Mantieni attivo `Email`.
4. Per il pilot iniziale, evita login social.

Scelta consigliata:

```text
Email + password
```

Motivo: e' semplice da capire, abbastanza robusto e compatibile con i ruoli.

## 7. Utenti iniziali da creare

Per testare servono almeno:

1. un utente cliente;
2. un utente titolare bar;
3. un utente Salute Quotidiana.

Dopo averli creati in Supabase Auth, bisogna inserire i rispettivi record nella tabella `profili`.

Esempio ruoli:

```text
cliente
titolare_bar
salute_quotidiana
```

## 8. Ordine corretto dei prossimi lavori

1. Creare progetto Supabase.
2. Eseguire `supabase-schema-v2.sql`.
3. Eseguire `supabase-rls-v2.sql`.
4. Creare `supabase-config.js`.
5. Collegare login alla web app.
6. Collegare iscrizione cliente.
7. Collegare caricamento scontrino.
8. Collegare verifica titolare bar.
9. Collegare pannello Salute Quotidiana.
10. Collegare report ed export.

## 9. Nota importante

Finche' la web app non e' collegata a Supabase, il prototipo attuale continua a usare `localStorage`.

Quindi questa fase prepara la V2, ma non cambia ancora il comportamento dell'app attuale.
