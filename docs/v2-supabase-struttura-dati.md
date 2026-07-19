# Credito Salute SQ - V2 Supabase

Questo documento definisce la prima struttura dati della V2.

Obiettivo: passare dal salvataggio locale con `localStorage` a un archivio centrale Supabase, mantenendo la web app semplice e gestibile.

## 1. Scelta tecnica

La V2 usa:

1. Frontend statico: `index.html`, `styles.css`, `app.js`.
2. Backend leggero: Supabase.
3. Database centrale: PostgreSQL gestito da Supabase.
4. Foto scontrini: Supabase Storage.
5. Login e ruoli: Supabase Auth + tabella `profili`.

Per ora non serve creare un server Node.js separato.

## 2. Ruoli

I ruoli iniziali sono tre:

1. `cliente`
2. `titolare_bar`
3. `salute_quotidiana`

### Cliente

Puo':

1. iscriversi;
2. caricare scontrini;
3. vedere il proprio credito;
4. vedere il proprio storico.

Non puo':

1. confermare scontrini;
2. vedere altri clienti;
3. modificare credito;
4. vedere dati operativi del bar o di Salute Quotidiana.

### Titolare bar

Puo':

1. vedere scontrini del proprio bar;
2. controllare foto, importo, data e numero documento;
3. confermare scontrini;
4. correggere importi;
5. rifiutare scontrini.

Non puo':

1. registrare clienti al posto loro;
2. vedere dati sanitari;
3. vedere prestazioni Salute Quotidiana;
4. esportare report completi.

### Salute Quotidiana

Puo':

1. vedere tutto il pilot;
2. monitorare clienti e scontrini;
3. registrare utilizzi credito;
4. controllare anomalie;
5. esportare dati;
6. valutare andamento del pilot.

## 3. Tabelle

### `profili`

Collega gli utenti Supabase ai ruoli del progetto.

Campi principali:

1. `id`
2. `auth_user_id`
3. `ruolo`
4. `nome_completo`
5. `telefono`
6. `email`
7. `attivo`
8. `created_at`

### `bar`

Contiene i bar aderenti.

Campi principali:

1. `id`
2. `nome`
3. `citta`
4. `indirizzo`
5. `attivo`
6. `created_at`

### `operatori_bar`

Collega titolari o operatori a uno specifico bar.

Campi principali:

1. `id`
2. `bar_id`
3. `profilo_id`
4. `ruolo_operativo`
5. `attivo`
6. `created_at`

### `clienti`

Contiene i clienti iscritti al programma credito.

Campi principali:

1. `id`
2. `profilo_id`
3. `codice_cliente`
4. `nome`
5. `cognome`
6. `telefono`
7. `email`
8. `citta`
9. `privacy_accettata_at`
10. `consenso_programma`
11. `consenso_marketing`
12. `stato`
13. `created_at`

Nota privacy: qui non vanno inseriti dati sanitari.

### `scontrini`

Contiene gli scontrini caricati dai clienti.

Campi principali:

1. `id`
2. `cliente_id`
3. `bar_id`
4. `caricato_da_profilo_id`
5. `percorso_foto`
6. `testo_ocr`
7. `data_scontrino`
8. `ora_scontrino`
9. `numero_documento`
10. `importo_dichiarato`
11. `importo_ocr`
12. `importo_verificato`
13. `credito_generato`
14. `stato`
15. `avviso_duplicato`
16. `motivo_rifiuto`
17. `verificato_da_profilo_id`
18. `verificato_at`
19. `created_at`
20. `updated_at`

Stati:

1. `in_verifica`
2. `confermato`
3. `rifiutato`

### `verifiche_scontrini`

Storico delle azioni del titolare bar sugli scontrini.

Campi principali:

1. `id`
2. `scontrino_id`
3. `verificato_da_profilo_id`
4. `stato_precedente`
5. `nuovo_stato`
6. `importo_precedente`
7. `nuovo_importo`
8. `nota`
9. `created_at`

### `utilizzi_credito`

Contiene gli utilizzi del credito su prestazioni Salute Quotidiana.

Campi principali:

1. `id`
2. `cliente_id`
3. `registrato_da_profilo_id`
4. `tipo_prestazione`
5. `data_prestazione`
6. `prezzo_prestazione`
7. `credito_usato`
8. `differenza_pagata`
9. `nota_interna`
10. `created_at`

Questa tabella non deve essere visibile al titolare del bar.

### `log_operativi`

Registro delle azioni importanti.

Campi principali:

1. `id`
2. `profilo_id`
3. `azione`
4. `tipo_entita`
5. `entita_id`
6. `dettagli`
7. `created_at`

## 4. Calcolo credito

Il credito non va modificato manualmente come saldo libero.

Regola:

```text
credito generato = importo verificato * 0.15
```

Saldo cliente:

```text
credito confermato = somma credito_generato degli scontrini confermati
credito usato = somma credito_usato degli utilizzi credito
saldo disponibile = credito confermato - credito usato
credito in verifica = somma credito_generato degli scontrini in verifica
```

Questa scelta e' piu' robusta perche' il saldo deriva sempre dai movimenti reali.

## 5. Anomalie iniziali

Le anomalie da gestire nella V2 base sono:

1. stesso bar, stessa data e stesso numero documento;
2. stesso cliente, stesso importo e stessa data;
3. importo molto alto;
4. cliente con molti scontrini rifiutati;
5. cliente iscritto ma senza scontrini;
6. scontrino in verifica da troppi giorni.

## 6. Prossimi passaggi

1. Creare progetto Supabase.
2. Eseguire lo script `docs/supabase-schema-v2.sql`.
3. Creare bucket Storage per le foto degli scontrini.
4. Definire le policy RLS.
5. Collegare la web app a Supabase.
6. Migrare gradualmente le funzioni da `localStorage` al database.
