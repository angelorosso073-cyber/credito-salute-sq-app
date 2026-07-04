# Credito Salute SQ - Ruoli e permessi V2

Aggiornato al 2 luglio 2026.

Questo documento descrive i permessi operativi della V2 con Supabase.

La regola principale e': ogni ruolo deve vedere solo cio' che gli serve davvero.

## 1. Concetto chiave: RLS

`RLS` significa `Row Level Security`.

In pratica: Supabase controlla ogni riga del database e decide se l'utente collegato puo' leggerla, crearla o modificarla.

Esempio semplice:

1. Mario cliente vede solo i suoi scontrini.
2. Il titolare del bar vede solo gli scontrini del suo bar.
3. Salute Quotidiana vede tutto.

## 2. Ruoli

I ruoli sono salvati nella tabella `profili`, campo `ruolo`.

Valori ammessi:

1. `cliente`
2. `titolare_bar`
3. `salute_quotidiana`

Nel frontend attuale alcuni valori vengono normalizzati:

1. `titolare_bar` diventa `bar`;
2. `controllo_sq` diventa `salute_quotidiana`;
3. `salute` diventa `salute_quotidiana`.

La registrazione pubblica deve creare solo utenti con ruolo `cliente`.

Ruoli come `bar`, `titolare_bar`, `salute_quotidiana` e `admin` devono essere creati o assegnati da Salute Quotidiana/amministrazione, non dall'utente pubblico.

## 3. Permessi per tabella

### `profili`

Cliente:

1. vede il proprio profilo;
2. puo' creare il proprio profilo cliente dopo la registrazione.
3. non puo' modificare il proprio ruolo.

Titolare bar:

1. vede il proprio profilo.

Salute Quotidiana:

1. vede tutti i profili;
2. puo' modificare profili e ruoli.

### `bar`

Cliente:

1. vede i bar attivi per scegliere dove ha fatto lo scontrino.

Titolare bar:

1. vede il proprio bar.

Salute Quotidiana:

1. vede e gestisce tutti i bar.

### `operatori_bar`

Cliente:

1. non vede questa tabella.

Titolare bar:

1. vede solo il proprio collegamento al bar.

Salute Quotidiana:

1. gestisce tutti i collegamenti tra operatori e bar.

### `clienti`

Cliente:

1. vede solo la propria scheda cliente.
2. se la scheda cliente esiste gia', la web app deve caricarla automaticamente dopo login.
3. se la scheda cliente esiste gia', la web app non deve mostrare di nuovo il form iscrizione.

Titolare bar:

1. non accede direttamente alla tabella completa dei clienti.
2. puo' vedere solo conteggi o viste minime collegate al proprio bar, se servono al report bar.

Salute Quotidiana:

1. vede e gestisce tutti i clienti.
2. puo' creare o correggere schede cliente in caso di errore operativo o cliente assistito.

Nota privacy: il titolare bar non deve vedere dati inutili del cliente. Per il bar conviene usare una vista o query dedicata con solo dati minimi.

### `scontrini`

Cliente:

1. vede solo i propri scontrini;
2. crea nuovi scontrini in stato `in_verifica`.

Titolare bar:

1. vede solo gli scontrini del proprio bar;
2. puo' confermare, correggere o rifiutare.
3. puo' avere un riepilogo aggregato sugli scontrini del proprio bar.

Salute Quotidiana:

1. vede tutto;
2. puo' intervenire su tutto in caso di errore operativo.

### `verifiche_scontrini`

Cliente:

1. non accede direttamente allo storico tecnico delle verifiche.

Titolare bar:

1. vede e registra verifiche sugli scontrini del proprio bar.

Salute Quotidiana:

1. vede tutto lo storico verifiche.

### `utilizzi_credito`

Cliente:

1. vede solo i propri utilizzi credito.

Titolare bar:

1. non vede questa tabella.
2. non deve vedere quali prestazioni sanitarie sono state usate, da chi o per quale beneficiario.

Salute Quotidiana:

1. registra e consulta tutti gli utilizzi credito.

### `log_operativi`

Cliente:

1. puo' generare log collegati alle proprie azioni;
2. non usa questa tabella dall'interfaccia.

Titolare bar:

1. puo' generare log collegati alle proprie azioni;
2. non usa questa tabella dall'interfaccia.

Salute Quotidiana:

1. puo' leggere i log operativi.

## 4. Report per ruolo

### Cliente

Il cliente vede:

1. saldo confermato;
2. saldo in verifica;
3. storico dei propri scontrini;
4. storico dei propri utilizzi credito, se presente.

Il cliente non deve vedere:

1. tendina con altri clienti;
2. report generale;
3. dati di altri clienti;
4. funzioni di verifica.

### Titolare bar

E' coerente dare al titolare un report generale, ma limitato.

Il titolare puo' vedere:

1. clienti iscritti collegati al proprio bar;
2. scontrini caricati;
3. scontrini in verifica;
4. scontrini confermati;
5. totale consumazioni confermate;
6. credito SQ generato nel bar;
7. andamento generale del pilot.

Il titolare non deve vedere:

1. prestazioni sanitarie usate;
2. beneficiari;
3. note sanitarie;
4. note interne Salute Quotidiana;
5. dati di altri bar futuri.

### Salute Quotidiana

Salute Quotidiana vede:

1. report completo;
2. clienti;
3. scontrini;
4. utilizzi credito;
5. anomalie;
6. dati aggregati del pilot.

## 5. Limite importante della prima versione

Le policy RLS proteggono le righe, ma non sono sempre ideali per proteggere singole colonne.

Esempio: se il titolare bar puo' aggiornare uno scontrino, tecnicamente la policy consente l'aggiornamento della riga.

Per una versione piu' robusta, le azioni importanti dovrebbero diventare funzioni Supabase dedicate:

1. `conferma_scontrino`
2. `correggi_scontrino`
3. `rifiuta_scontrino`
4. `registra_utilizzo_credito`

In questo modo il frontend non modifica liberamente le righe, ma chiama azioni controllate.

## 6. Scelta pratica per la V2

Per la prima V2 facciamo cosi':

1. creiamo subito le policy RLS;
2. manteniamo il frontend semplice;
3. in seguito spostiamo le azioni critiche in funzioni dedicate.

Questa e' la strada migliore per partire senza complicare troppo il prototipo.

## 7. Prossime correzioni necessarie

1. Dopo login cliente, collegare automaticamente `profili.auth_user_id` al record in `clienti`.
2. Nascondere il form `Nuovo cliente SQ` se il cliente ha gia' una scheda cliente.
3. Rimuovere o disabilitare la tendina cliente per il ruolo `cliente`.
4. Lasciare ricerca/tendina cliente solo a Salute Quotidiana.
5. Creare un report bar separato, basato su dati aggregati e non sanitari.
