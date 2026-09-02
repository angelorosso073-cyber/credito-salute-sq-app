# Provenienza degli scontrini — progetto

Data: 02/09/2026
Stato: approvato nella direzione, da eseguire

## Il problema

Oggi il sistema non verifica in alcun modo che uno scontrino venga davvero
dall'esercizio aderente. Uno scontrino di qualunque negozio, datato oggi e
sotto i 30 euro, viene confermato e genera credito.

Le tre cose che sembravano dimostrare la provenienza non la dimostrano:

- **La matricola RT non viene letta dallo scontrino.** Da v55 la compila l'app
  leggendola da `registratori_telematici` e il campo e' in sola lettura: qualunque
  foto si carichi, l'app ci attacca sopra la matricola dell'esercizio scelto.
- **Il controllo incrociato OCR non blocca.** `validateReceiptAutomatically`
  (app.js ~2154) aggiunge una nota testuale che finisce in `motivo_rifiuto`.
  Lo stato lo decide il server guardando solo importo e codice banco, senza
  leggere quella nota.
- **Il codice banco dimostra la presenza, non la provenienza.** Dimostra che il
  cliente e' nel locale in quel momento, non che lo scontrino sia di quel locale.

Gli argini attuali (tetto di 6 scontrini al giorno, soglia dei 30 euro) limitano
il danno, non lo impediscono: con scontrino medio da 3 euro valgono circa 2,70
euro di credito indebito al giorno per cliente.

## Le prove su cui e' costruito il progetto

Estratti tre `testo_ocr` reali di scontrini del bar pilota dal database. Confronto
con i valori veri stampati:

| Dato | Reale | Letture ottenute su 3 |
|---|---|---|
| Nome esercizio | NEW CHAT CAFE' | corretto 3 volte |
| Titolare | DI MERENDA MICHELE | corretto 3 volte |
| Via | VIA E.GAUDIOSO | corretto 3 volte |
| Telefono | 095/7842471 | corretto 3 volte |
| Partita IVA | 01458000898 | corretto 2 volte, una volta `61468000898` |
| Civico | N 10 | corretto 2 volte, una volta `N 16` |
| Matricola RT | 2CISI000611 | **mai corretta**: `AT 20181000611`, `RT 26151660611`, `RT 2C181600611` |

**Regola che ne deriva: l'OCR sbaglia i numeri e azzecca le parole.** Il controllo
va costruito su parole, non su codici numerici.

**Trappola da evitare:** `FRANCOFONTE (SR)` compare su qualunque scontrino di
qualunque negozio del paese. Come elemento identificativo vale zero.

**Difetto scoperto durante l'analisi:** due delle tre righe erano **lo stesso
scontrino fotografato due volte** (stesso `DOCUMENTO N. 2319-0004`, stessa ora
`07:27`, stessa data). Sono passate entrambe perche' l'OCR ha letto il totale una
volta `1,20` e una volta `1.28`, e l'importo fa parte della chiave anti-duplicato.
Oggi basta un errore di lettura dell'importo — o una modifica di un centesimo
fatta apposta — per caricare due volte lo stesso scontrino.

**Secondo difetto scoperto:** il flusso cassiere (`handleCassiereReceiptSubmit`)
non manda foto, OCR, matricola ne' codice banco. Ogni scontrino caricato dal
barista per un cliente anziano finisce quindi `codice_banco_mancante`, con
l'invito ad "attivarlo al bar" rivolto a chi non ha smartphone ed era gia' al
bar. Quel credito scade dopo 12 giorni senza che nessuno possa attivarlo.

**Terzo difetto scoperto:** nella funzione `registra_scontrino_pilot` sia la
convalida della matricola sia il controllo anti-duplicato si trovano dentro un
unico `IF matricola_normalizzata IS NOT NULL`. Quando la matricola non arriva,
il controllo sui doppioni non viene eseguito affatto. Poiche' il flusso cassiere
non trasmette mai la matricola, oggi **nessuno scontrino caricato dal banco e'
protetto dai doppioni**: lo stesso scontrino puo' essere inserito due volte per
semplice distrazione, e l'unico limite che interviene e' il tetto di sei
scontrini al giorno.

## Decisioni prese

- **Modello di minaccia**: furbizia deliberata, gia' in questa fase del pilot.
  Si accetta piu' attrito pur di avere controlli veri.
- **Approccio scelto**: impronta testuale per esercizio, verificata sul server.
  Scartate: la conferma del cassiere a ogni consumazione (troppo peso sul banco
  per importi da 1,20 euro) e la sola revisione a campione (non regge oltre i
  primi esercizi).
- **La chiave anti-duplicato perde l'importo** e diventa
  `matricola + numero documento + data`.

## Il progetto

### 1. Modello dati

Nuova tabella: le parole che identificano un esercizio, con un peso.

```sql
CREATE TABLE public.impronte_esercizio (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  bar_id UUID NOT NULL REFERENCES public.bar(id) ON DELETE CASCADE,
  testo TEXT NOT NULL,
  peso INTEGER NOT NULL DEFAULT 1 CHECK (peso BETWEEN 1 AND 5),
  attivo BOOLEAN NOT NULL DEFAULT true,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (bar_id, testo)
);
```

RLS: lettura ai soli `authenticated`, scrittura ad admin/salute_quotidiana,
nessun accesso ad `anon` (l'elenco delle impronte e' cio' che un imbroglione
vorrebbe conoscere per costruire un testo falso).

Soglia per esercizio, in `limiti_bar`:

```sql
ALTER TABLE public.limiti_bar
  ADD COLUMN IF NOT EXISTS soglia_impronta INTEGER NOT NULL DEFAULT 3
  CHECK (soglia_impronta >= 0);
```

Valori iniziali per il bar pilota:

| testo | peso | perche' |
|---|---|---|
| NEW CHAT CAFE | 3 | nome, letto sempre correttamente |
| MERENDA MICHELE | 3 | titolare, letto sempre correttamente |
| GAUDIOSO | 2 | via, parola non numerica |
| 7842471 | 1 | telefono, numerico quindi meno affidabile |
| 01458000898 | 1 | partita IVA, numerica |

Soglia 3: **una sola parola forte basta**. Scelta voluta — una foto storta che
lascia leggere solo il nome del bar non deve finire in revisione manuale.

### 2. Normalizzazione e punteggio

Due funzioni plpgsql.

`normalizza_testo_ocr(text)`: maiuscolo, accenti ridotti alla lettera base,
qualunque carattere non alfanumerico sostituito da spazio, spazi multipli
compattati. Serve perche' l'OCR restituisce `TEL .095/7842471`, `NEW CHAT CAFE'`
e simili: senza normalizzazione nessun confronto reggerebbe.

`punteggio_impronta_pilot(p_bar_id uuid, p_testo_ocr text) RETURNS INTEGER`:
normalizza il testo, somma i pesi delle impronte attive dell'esercizio che vi
compaiono. Testo nullo o vuoto -> 0.

### 3. La nuova catena decisionale

Dentro `registra_scontrino_pilot`, il ramo che oggi ha tre esiti ne avra' cinque.
**L'ordine conta**: la provenienza deve venire prima del codice banco, altrimenti
un codice banco valido confermerebbe uno scontrino estraneo.

```
1. importo > soglia_revisione_manuale    -> in_verifica, importo_oltre_soglia
2. caricato dal bar, da SQ o da admin    -> confermato
3. punteggio impronta < soglia_impronta  -> in_verifica, provenienza_da_verificare
4. codice banco valido                   -> confermato
5. altrimenti                            -> in_verifica, codice_banco_mancante
```

La soglia importo resta **in cima a tutto**, anche sopra il ramo del bar: un
importo implausibile va guardato da chiunque arrivi, perche' quel controllo non
riguarda la fiducia in chi carica ma la plausibilita' della cifra.

Il ramo 2 vale per `e_bar() OR e_salute_quotidiana() OR e_admin()`: sono gli
stessi ruoli che gia' oggi possono caricare per conto di un cliente.

**Il ramo 2 e' la correzione del flusso cassiere.** Quando a caricare e' l'account
del bar, provenienza e presenza sono dimostrate per definizione: e' l'esercizio
stesso che sta attestando la consumazione, sul proprio registratore, davanti al
cliente. Chiedergli in piu' un codice che espone lui stesso, o un OCR di una foto
che non scatta, non dimostrerebbe niente di piu'. Risolve anche il credito che
oggi scade inutilizzabile per i clienti anziani.

**Conseguenza sul collaudo, da tenere presente:** Angelo possiede due account,
`salute_quotidiana` e `titolare_bar`. Con questa modifica, qualunque scontrino
caricato da uno di quei due entra nel ramo 2 e viene confermato senza passare
per impronta e codice banco. Per collaudare il percorso del cliente servira'
quindi un account cliente vero, altrimenti si finisce per provare un ramo diverso
da quello che si crede di provare — lo stesso equivoco che ha fatto perdere una
giornata sul bug del codice banco.

Rischio accettato sul ramo 2: il bar potrebbe gonfiare gli importi. Non ha
interesse a farlo — e' lui che alimenta il fondo — e ogni scontrino porta gia'
`operatore_label` per l'attribuzione. Resta sotto il controllo dei report mensili.

Nuovo valore ammesso in `motivo_sospensione`, con estensione del CHECK esistente:

```sql
CHECK (motivo_sospensione IS NULL OR motivo_sospensione IN (
  'importo_oltre_soglia', 'codice_banco_mancante', 'provenienza_da_verificare'
))
```

Va anche salvato il punteggio ottenuto, per poter tarare le soglie con i dati
veri invece che a intuito:

```sql
ALTER TABLE public.scontrini
  ADD COLUMN IF NOT EXISTS punteggio_impronta INTEGER;
```

### 4. Correzione della chiave anti-duplicato

L'importo esce dalla chiave, in tutti e tre i punti dove compare:

- indice unico `idx_scontrini_chiave_duplicato`
- controllo esplicito dentro `registra_scontrino_pilot`
- `findDuplicateReceipt` in app.js (deve restare allineato al server)

Nuova chiave: `matricola_rt + numero_documento + data_scontrino`, sempre
escludendo `stato = 'rifiutato'`.

### 4-bis. La matricola viene ricavata dal server quando non arriva

Il controllo anti-duplicato si basa sulla matricola del registratore. Se la
matricola manca, oggi il controllo viene saltato del tutto, e questo lascia
scoperti tutti gli scontrini caricati dal banco (vedi il terzo difetto
scoperto).

La matricola pero' e' gia' registrata nel database, nella tabella
`registratori_telematici`, associata a ciascun esercizio. Il server non ha
alcun bisogno di riceverla dal client: puo' leggerla da li'.

La correzione consiste quindi nel ricavarla quando non viene trasmessa:

```sql
IF matricola_normalizzata IS NULL THEN
  SELECT UPPER(rt.matricola) INTO matricola_normalizzata
  FROM public.registratori_telematici rt
  WHERE rt.bar_id = p_bar_id AND rt.attivo = true;
  -- Nessun LIMIT 1: con piu' registratori attivi la SELECT INTO lascia
  -- comunque un solo valore, quindi il caso va reso esplicito.
END IF;
```

Con un solo registratore attivo per esercizio, che e' la situazione del bar
pilota, il valore e' univoco e il controllo sui doppioni torna a funzionare
anche per i caricamenti fatti dal banco, senza che il barista debba fare niente
di diverso.

Se un esercizio avesse piu' registratori attivi non esisterebbe un valore
univoco da ricavare. In quel caso la matricola resta vuota e il controllo sui
doppioni resta inattivo per quell'esercizio, esattamente come oggi. Va scritto
nel codice in modo esplicito, con un commento, perche' e' una rinuncia
consapevole e non una dimenticanza: quando arrivera' un esercizio con due
casse, la scelta andra' ripresa in mano.

Nota: la matricola cosi' ricavata viene salvata sulla riga dello scontrino. Non
e' una dichiarazione di aver letto quel numero dalla fotografia, ma
l'indicazione dell'esercizio da cui lo scontrino proviene. Il campo aveva gia'
questo significato dopo v55, quando la compilazione automatica lato client ha
smesso di leggerlo dallo scontrino.

**La migrazione non e' indolore**: esistono gia' righe che violano la nuova chiave
(le due letture dello stesso scontrino). L'indice unico fallirebbe. Quindi il file
SQL deve, in quest'ordine:

1. una `SELECT` di anteprima che elenca i gruppi in collisione — da lanciare da
   sola e leggere prima di proseguire;
2. una `UPDATE` che porta a `rifiutato` tutte le righe di ogni gruppo tranne la
   piu' recente, con `motivo_rifiuto` esplicito;
3. il `DROP INDEX` e la ricreazione senza importo.

### 5. Viste e interfaccia

- `scontrini_revisione_manuale_pilot` oggi filtra solo `importo_oltre_soglia`:
  deve includere anche `provenienza_da_verificare`, ed esporre
  `punteggio_impronta` e `foto_path` perche' la revisione si fa guardando la foto.
- app.js: messaggio dedicato per il nuovo motivo. Non deve accusare il cliente —
  la causa piu' probabile e' una foto poco leggibile, non un imbroglio. Testo
  proposto: "Scontrino ricevuto. Prima di accreditare il credito controlliamo la
  foto: se e' tutto in ordine lo trovi accreditato entro poco."
- Nessuna interfaccia di gestione delle impronte: per il pilot si popolano via
  SQL. Servira' quando gli esercizi saranno piu' d'uno.

## Cosa questo NON copre

Da dire chiaramente, perche' non venga scambiato per piu' di quel che e':

- **`p_testo_ocr` lo manda il client.** Chi sa manipolare le richieste dell'app
  puo' inviare un testo costruito a tavolino e superare il controllo. Ferma chi
  fotografa lo scontrino del supermercato, non ferma chi sa usare gli strumenti
  per sviluppatori del browser. Per il modello di minaccia scelto (clienti di
  paese) e' proporzionato; la difesa vera sarebbe un OCR eseguito sul server a
  partire dalla foto gia' archiviata, che oggi il piano gratuito di Supabase non
  consente senza una funzione dedicata.
- **Non verifica che la consumazione sia avvenuta davvero**, solo che lo scontrino
  sembri di quell'esercizio.
- **Non copre uno scontrino vero del bar pilota trovato per terra** o passato da
  un altro cliente. Contro quello agiscono il codice banco e il tetto giornaliero.

## Come si verifica

Il meccanismo e' gia' stato tarato sui dati veri prima di scrivere questo
progetto, con un prototipo sui tre `testo_ocr` reali piu' casi costruiti:

| Caso | Punti | Esito |
|---|---|---|
| Scontrino reale 02/09 (OCR sporco) | 9 | passa |
| Scontrino reale 02/09 (molto rumore) | 10 | passa |
| Scontrino reale 01/09 (pulito) | 10 | passa |
| Bar pilota, foto pessima, una sola parola leggibile | 3 | passa |
| Supermercato di Francofonte | 0 | fermato |
| Tabaccheria di Francofonte | 0 | fermato |
| Foto illeggibile | 0 | fermato |

Separazione netta: gli scontrini veri stanno tra 9 e 10, quelli estranei a 0, la
soglia e' a 3. Nessun caso al limite.

In fase di esecuzione questi stessi casi vanno rifatti **in SQL** contro le
funzioni vere, non solo nel prototipo: un blocco di test con i tre testi reali
come dati di prova, che stampa punteggio ed esito atteso per ciascuno.

## File previsti

| File | Contenuto |
|---|---|
| `docs/supabase-impronte-esercizio.sql` | tabella, RLS, soglia in `limiti_bar`, funzioni di normalizzazione e punteggio, impronte del bar pilota, nuovo CHECK, colonna `punteggio_impronta`, `registra_scontrino_pilot` aggiornata, viste |
| `docs/supabase-chiave-duplicato-senza-importo.sql` | anteprima collisioni, bonifica, nuovo indice |
| `docs/supabase-test-impronte.sql` | blocco di verifica con i tre testi reali |
| `app.js` | messaggio per il nuovo motivo, `findDuplicateReceipt` senza importo |
| `index.html` | nessuna modifica prevista |

Ordine di applicazione: prima `impronte`, poi `chiave-duplicato`, infine `test`.
Le due modifiche SQL toccano entrambe `registra_scontrino_pilot`: vanno scritte
in modo che la seconda parta dalla versione lasciata dalla prima.

## Rischi

- **Falsi positivi su foto pessime.** Mitigati dalla soglia bassa e dal fatto che
  l'esito non e' un rifiuto ma una revisione, con la foto gia' disponibile.
- **Le impronte vanno tenute aggiornate**: se il bar cambia insegna o indirizzo,
  gli scontrini iniziano a finire in revisione. Da ricordare all'ingresso di ogni
  nuovo esercizio.
- **Il ramo 2 (caricato dal bar) sposta fiducia sull'esercizio.** Consapevole:
  e' l'unico attore che non ha interesse a gonfiare, ed e' gia' oggi l'unico modo
  in cui un cliente senza smartphone puo' partecipare.
