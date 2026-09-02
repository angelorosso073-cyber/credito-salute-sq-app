# Verifica provenienza scontrini — piano di esecuzione

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** impedire che uno scontrino estraneo all'esercizio aderente generi credito, verificando sul server che il testo letto dalla fotografia contenga le parole caratteristiche di quell'esercizio.

**Architecture:** ogni esercizio ha in tabella un elenco di parole con un peso. Una funzione sul server normalizza il testo OCR che l'app già invia e somma i pesi delle parole trovate. Sotto una soglia configurabile lo scontrino non viene confermato ma messo in revisione manuale. La catena decisionale di `registra_scontrino_pilot` passa da tre a cinque rami, con la provenienza verificata prima del codice banco. In più, due difetti trovati sui dati reali: l'importo esce dalla chiave anti-duplicato, e la matricola del registratore viene ricavata dal server quando il client non la manda.

**Tech Stack:** PostgreSQL/plpgsql su Supabase, JavaScript senza framework, test in Node senza dipendenze esterne.

**Spec:** `docs/superpowers/specs/2026-09-02-provenienza-scontrini-design.md`

## Global Constraints

- **I file SQL non sono applicabili da chi esegue il piano.** Vanno scritti, verificati per sintassi, committati, e poi applicati **da Angelo** nell'SQL Editor di Supabase. Ogni task che produce SQL termina con una consegna esplicita ad Angelo e attende conferma prima del task successivo.
- Tutti i file SQL vivono in `docs/`, come tutti gli altri del progetto.
- In una funzione `SECURITY DEFINER` non usare mai `current_user` per distinguere il chiamante: usare `session_user`. Regola già stabilita in questo progetto dopo una falla reale.
- Le funzioni che espongono informazioni utili a un imbroglione (codici attesi, elenco impronte) vanno revocate esplicitamente a `PUBLIC` e ad `anon`: PostgreSQL concede `EXECUTE` a `PUBLIC` per difetto sulle funzioni nuove.
- Il testo mostrato all'utente non deve mai accusarlo: la causa più probabile di un punteggio basso è una fotografia poco leggibile.
- `APP_VERSION` in `app.js` e la stringa `app.js?v=NN` in `index.html` vanno alzate insieme, altrimenti la PWA installata continua a servire la versione vecchia dalla cache.
- Nessun apostrofo tipografico né em dash nel testo mostrato all'utente.
- Valori del bar pilota, da usare nei dati di prova: `bar_id` = `ea2a9fbd-9d46-40d9-8992-182f61bcfe7a`, matricola = `2CISI000611`, soglia revisione = 30 euro, tetto giornaliero = 6, finestra codice banco = 90 secondi.

---

### Task 1: Impronte per esercizio, con verifica sui testi reali

Costruisce il meccanismo di punteggio senza collegarlo ancora al flusso degli scontrini. Alla fine di questo task nulla cambia nel comportamento dell'app: esiste solo una funzione nuova, verificabile da sola.

**Files:**
- Create: `docs/supabase-impronte-esercizio.sql`
- Create: `docs/supabase-test-impronte.sql`

**Interfaces:**
- Produces: `public.normalizza_testo_ocr(p_testo TEXT) RETURNS TEXT` — usata dal task 3 solo indirettamente.
- Produces: `public.punteggio_impronta_pilot(p_bar_id UUID, p_testo_ocr TEXT) RETURNS INTEGER` — chiamata dal task 3 dentro `registra_scontrino_pilot`.
- Produces: colonna `public.limiti_bar.soglia_impronta INTEGER NOT NULL DEFAULT 3` — letta dal task 3.

- [ ] **Step 1: Scrivere il file SQL delle impronte**

Creare `docs/supabase-impronte-esercizio.sql`:

```sql
-- docs/supabase-impronte-esercizio.sql
-- Verifica di provenienza: parole caratteristiche di ogni esercizio, cercate
-- nel testo OCR che l'app gia' invia insieme allo scontrino.
--
-- Eseguire in Supabase SQL Editor dopo docs/supabase-foto-scontrini-storage.sql.
-- Questo file NON modifica registra_scontrino_pilot: aggiunge solo il
-- meccanismo di punteggio, che il file successivo collega alla decisione.
--
-- Perche' basato su parole e non sulla matricola: su tre scontrini reali del
-- bar pilota l'OCR non ha letto la matricola correttamente nemmeno una volta
-- (2CISI000611 letto come AT 20181000611, RT 26151660611, RT 2C181600611),
-- mentre nome, titolare e via sono stati letti correttamente tutte e tre le
-- volte. L'OCR sbaglia i numeri e azzecca le parole.

-- 1. Elenco delle parole per esercizio.
CREATE TABLE IF NOT EXISTS public.impronte_esercizio (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  bar_id UUID NOT NULL REFERENCES public.bar(id) ON DELETE CASCADE,
  testo TEXT NOT NULL,
  peso INTEGER NOT NULL DEFAULT 1 CHECK (peso BETWEEN 1 AND 5),
  attivo BOOLEAN NOT NULL DEFAULT true,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (bar_id, testo)
);

ALTER TABLE public.impronte_esercizio ENABLE ROW LEVEL SECURITY;

-- Nessuna policy di lettura per i client: l'elenco delle impronte e'
-- esattamente cio' che servirebbe a un imbroglione per costruire un testo
-- falso capace di superare il controllo. Lo legge solo la funzione di
-- punteggio, che e' SECURITY DEFINER.
DROP POLICY IF EXISTS "impronte_gestione_admin_sq" ON public.impronte_esercizio;
CREATE POLICY "impronte_gestione_admin_sq"
ON public.impronte_esercizio
FOR ALL
TO authenticated
USING (public.e_admin() OR public.e_salute_quotidiana())
WITH CHECK (public.e_admin() OR public.e_salute_quotidiana());

REVOKE ALL ON public.impronte_esercizio FROM anon;

-- 2. Soglia per esercizio. 3 significa che una sola parola forte basta:
--    scelta voluta, una fotografia storta che lascia leggere solo il nome
--    dell'esercizio non deve finire in revisione manuale.
ALTER TABLE public.limiti_bar
  ADD COLUMN IF NOT EXISTS soglia_impronta INTEGER NOT NULL DEFAULT 3
  CHECK (soglia_impronta >= 0);

-- 3. Normalizzazione. Serve perche' l'OCR restituisce "TEL .095/7842471",
--    "NEW CHAT CAFE'" e simili: senza normalizzare nessun confronto reggerebbe.
CREATE OR REPLACE FUNCTION public.normalizza_testo_ocr(p_testo TEXT)
RETURNS TEXT
LANGUAGE sql
IMMUTABLE
AS $$
  SELECT TRIM(REGEXP_REPLACE(
    UPPER(TRANSLATE(
      COALESCE(p_testo, ''),
      'ÀÁÂÃÄÈÉÊËÌÍÎÏÒÓÔÕÖÙÚÛÜàáâãäèéêëìíîïòóôõöùúûü',
      'AAAAAEEEEIIIIOOOOOUUUUaaaaaeeeeiiiiooooouuuu'
    )),
    '[^A-Z0-9]+', ' ', 'g'
  ));
$$;

-- 4. Punteggio: somma dei pesi delle impronte attive presenti nel testo.
CREATE OR REPLACE FUNCTION public.punteggio_impronta_pilot(
  p_bar_id UUID,
  p_testo_ocr TEXT
)
RETURNS INTEGER
LANGUAGE plpgsql
STABLE
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  testo_normalizzato TEXT;
  totale INTEGER;
BEGIN
  testo_normalizzato := public.normalizza_testo_ocr(p_testo_ocr);

  IF testo_normalizzato = '' THEN
    RETURN 0;
  END IF;

  SELECT COALESCE(SUM(i.peso), 0)
  INTO totale
  FROM public.impronte_esercizio i
  WHERE i.bar_id = p_bar_id
    AND i.attivo = true
    AND POSITION(public.normalizza_testo_ocr(i.testo) IN testo_normalizzato) > 0;

  RETURN totale;
END;
$$;

-- Non richiamabile dai client: risponderebbe alle domande di chi vuole
-- indovinare le impronte. La chiama solo registra_scontrino_pilot, che gira
-- come proprietario.
REVOKE ALL ON FUNCTION public.punteggio_impronta_pilot(uuid, text) FROM PUBLIC, anon, authenticated;

-- 5. Impronte del bar pilota. Pesi alti alle parole, bassi ai numeri: sui tre
--    scontrini reali la partita IVA e' stata letta correttamente 2 volte su 3,
--    le parole 3 volte su 3.
--    FRANCOFONTE non compare di proposito: sta sullo scontrino di qualunque
--    negozio del paese e non distingue nulla.
INSERT INTO public.impronte_esercizio (bar_id, testo, peso)
SELECT b.id, v.testo, v.peso
FROM public.bar b
CROSS JOIN (VALUES
  ('NEW CHAT CAFE', 3),
  ('MERENDA MICHELE', 3),
  ('GAUDIOSO', 2),
  ('7842471', 1),
  ('01458000898', 1)
) AS v(testo, peso)
WHERE b.nome = 'Bar pilota Francofonte'
ON CONFLICT (bar_id, testo) DO NOTHING;

NOTIFY pgrst, 'reload schema';
```

- [ ] **Step 2: Scrivere il file di verifica**

Creare `docs/supabase-test-impronte.sql`. I primi tre casi sono testi OCR **reali**, copiati da `public.scontrini` del bar pilota; gli altri sono costruiti.

```sql
-- docs/supabase-test-impronte.sql
-- Verifica del punteggio impronta. Da lanciare dopo
-- docs/supabase-impronte-esercizio.sql. Non modifica nulla: solo SELECT.
--
-- Atteso: le prime quattro righe PASSA, le ultime tre FERMA.

WITH bar_pilota AS (
  SELECT id FROM public.bar WHERE nome = 'Bar pilota Francofonte'
),
casi(ordine, nome, testo, atteso_passa) AS (
  VALUES
  (1, 'reale 02/09 con OCR sporco', $t$SOS aa A Jr
NEW CHAT CAFE'
DI MERENDA MICHELE
PARTITA IVA 61468000898
VIA E.GAUDIOSO N 16
FRANCOFONTE (SR)
TEL.095/7842471
TOTALE COMPLESSIVO ~~ 1.28
02-09-2026 07:27
DOCUMENTO N. 2319-0004
AT 20181000611$t$, true),

  (2, 'reale 02/09 con molto rumore', $t$AR ar Aaah Ld
Sa NEW CHAT CAFE' Bia
Sa DI MERENDA MICHELE oP
a PARTITA IVA 01458000898 ij
o VIA E.GAUDIOSO N 10
O FRANCOFONTE (SR)
o TEL .095/7842471
TOTALE COMPLESSIVO 1,20
de 02-09-2026 07:27 i
i RT 26151660611$t$, true),

  (3, 'reale 01/09 pulito', $t$NEW CHAT CAFE'
' DI MERENDA MICHELE
PARTITA IVA 01458000898
VIA E.GAUDIOSO N 10
FRANCOFONTE (SR)
TEL.095/7842471
TOTALE COMPLESSIVO 1,2
i 01-09-2026 16:11
i RT 2C181600611$t$, true),

  (4, 'bar pilota, foto pessima, una parola sola', $t$ii1 |\ NEW CHAT CAFE ,,. ~~
sgv FRANCOFONTE (SR) ...
TOTALE 1,20$t$, true),

  (5, 'supermercato di Francofonte', $t$SUPERMERCATO CONAD
DI RUSSO GIUSEPPE
PARTITA IVA 01999000111
VIA ROMA N 45
FRANCOFONTE (SR)
TEL.095/1234567
TOTALE COMPLESSIVO 12,40$t$, false),

  (6, 'tabaccheria di Francofonte', $t$TABACCHERIA CENTRALE
DI LI CALZI ANTONIO
PARTITA IVA 01777000222
CORSO GARIBALDI N 3
FRANCOFONTE (SR)
TOTALE COMPLESSIVO 5,00$t$, false),

  (7, 'foto illeggibile', $t$~~~ ,,, || \ ... i i i
TOTALE 1 20$t$, false)
)
SELECT
  c.ordine,
  c.nome,
  public.punteggio_impronta_pilot(b.id, c.testo) AS punti,
  (SELECT soglia_impronta FROM public.limiti_bar WHERE bar_id = b.id) AS soglia,
  CASE
    WHEN public.punteggio_impronta_pilot(b.id, c.testo)
         >= (SELECT soglia_impronta FROM public.limiti_bar WHERE bar_id = b.id)
    THEN 'PASSA' ELSE 'FERMA'
  END AS esito,
  CASE
    WHEN (public.punteggio_impronta_pilot(b.id, c.testo)
          >= (SELECT soglia_impronta FROM public.limiti_bar WHERE bar_id = b.id))
         = c.atteso_passa
    THEN 'OK' ELSE 'FUORI ATTESA'
  END AS verifica
FROM casi c CROSS JOIN bar_pilota b
ORDER BY c.ordine;
```

- [ ] **Step 3: Consegnare ad Angelo e attendere l'esito**

Chiedere ad Angelo di lanciare nell'SQL Editor, in quest'ordine:
1. `docs/supabase-impronte-esercizio.sql`
2. `docs/supabase-test-impronte.sql`

Attendere il risultato incollato. Atteso: colonna `verifica` uguale a `OK` su tutte e sette le righe, con punteggi intorno a 9-10 per i casi 1-3, 3 per il caso 4, 0 per i casi 5-7.

**Se anche una sola riga risulta `FUORI ATTESA`, fermarsi**: significa che la normalizzazione o i pesi non si comportano come previsto sul database vero, e vanno corretti prima di collegare il meccanismo alla decisione sugli scontrini.

- [ ] **Step 4: Commit**

```bash
git add docs/supabase-impronte-esercizio.sql docs/supabase-test-impronte.sql
git commit -m "Impronte per esercizio: tabella, punteggio e verifica sui testi reali"
```

---

### Task 2: Bonifica dei doppioni già presenti

La nuova chiave anti-duplicato non tollera righe che la violano già. Nel database ce ne sono: lo stesso scontrino (documento `2319-0004` del 02/09, ore 07:27) è stato accettato due volte perché l'OCR ne ha letto il totale una volta `1,20` e una volta `1.28`. Questo task ripulisce, senza ancora cambiare regole.

**Files:**
- Create: `docs/supabase-bonifica-doppioni.sql`

**Interfaces:**
- Consumes: niente.
- Produces: un database in cui nessun gruppo `matricola_rt + numero_documento + data_scontrino` ha più di una riga non rifiutata. È la precondizione dell'indice creato nel task 3.

- [ ] **Step 1: Scrivere il file di bonifica**

Creare `docs/supabase-bonifica-doppioni.sql`:

```sql
-- docs/supabase-bonifica-doppioni.sql
-- Precondizione per la nuova chiave anti-duplicato senza importo.
--
-- Perche' serve: fino a oggi la chiave includeva l'importo, quindi due letture
-- diverse dello stesso totale (1,20 e 1.28 sullo stesso scontrino) risultavano
-- due scontrini distinti. Nel database ci sono righe cosi'. Il nuovo indice
-- unico le rifiuterebbe e non verrebbe creato.
--
-- LANCIARE PRIMA SOLO LA PARTE 1 E LEGGERE IL RISULTATO.
-- La parte 2 modifica dati: eseguirla solo dopo aver visto cosa tocca.

-- ---------------------------------------------------------------------------
-- PARTE 1 - Anteprima. Non modifica niente.
-- ---------------------------------------------------------------------------
SELECT
  s.matricola_rt,
  s.numero_documento,
  s.data_scontrino,
  count(*) AS righe_non_rifiutate,
  array_agg(s.importo_dichiarato ORDER BY s.created_at) AS importi,
  array_agg(s.stato ORDER BY s.created_at) AS stati,
  array_agg(s.created_at ORDER BY s.created_at) AS caricati_il
FROM public.scontrini s
WHERE s.matricola_rt IS NOT NULL
  AND s.stato <> 'rifiutato'
GROUP BY s.matricola_rt, s.numero_documento, s.data_scontrino
HAVING count(*) > 1
ORDER BY s.data_scontrino DESC;

-- ---------------------------------------------------------------------------
-- PARTE 2 - Bonifica. Tiene la riga piu' recente di ogni gruppo e rifiuta le
-- altre. Eseguire solo dopo aver letto l'anteprima.
-- ---------------------------------------------------------------------------
WITH ordinati AS (
  SELECT
    s.id,
    row_number() OVER (
      PARTITION BY s.matricola_rt, s.numero_documento, s.data_scontrino
      ORDER BY s.created_at DESC
    ) AS posizione
  FROM public.scontrini s
  WHERE s.matricola_rt IS NOT NULL
    AND s.stato <> 'rifiutato'
)
UPDATE public.scontrini s
SET stato = 'rifiutato',
    motivo_rifiuto = 'Doppione dello stesso scontrino: stesso registratore, stesso numero documento e stessa data. Rifiutato durante la bonifica del 02/09/2026.'
FROM ordinati o
WHERE s.id = o.id
  AND o.posizione > 1;

-- ---------------------------------------------------------------------------
-- PARTE 3 - Controllo. Deve restituire zero righe.
-- ---------------------------------------------------------------------------
SELECT
  s.matricola_rt, s.numero_documento, s.data_scontrino, count(*)
FROM public.scontrini s
WHERE s.matricola_rt IS NOT NULL
  AND s.stato <> 'rifiutato'
GROUP BY s.matricola_rt, s.numero_documento, s.data_scontrino
HAVING count(*) > 1;
```

- [ ] **Step 2: Consegnare ad Angelo, una parte alla volta**

Chiedere ad Angelo di lanciare **solo la parte 1** e incollare il risultato. Verificare insieme a lui che i gruppi elencati siano effettivamente doppioni e non scontrini distinti.

Solo dopo la sua conferma, chiedere di lanciare la parte 2 e poi la parte 3.

Atteso alla parte 3: nessuna riga.

- [ ] **Step 3: Commit**

```bash
git add docs/supabase-bonifica-doppioni.sql
git commit -m "Bonifica dei doppioni gia' presenti, precondizione della nuova chiave"
```

---

### Task 3: Nuova catena decisionale e nuova chiave anti-duplicato

Il cuore del lavoro. Riscrive `registra_scontrino_pilot` con cinque rami invece di tre, ricava la matricola quando manca, toglie l'importo dalla chiave dei doppioni e ricrea l'indice.

Le tre modifiche stanno in un unico task perché toccano tutte lo stesso percorso di scrittura: applicarne una senza le altre lascerebbe il sistema incoerente. In particolare, se l'indice diventasse più severo del controllo dentro la funzione, un inserimento riceverebbe un errore grezzo di PostgreSQL invece del messaggio comprensibile.

**Files:**
- Create: `docs/supabase-provenienza-e-chiave-duplicato.sql`

**Interfaces:**
- Consumes: `public.punteggio_impronta_pilot(uuid, text)` e `limiti_bar.soglia_impronta` dal task 1.
- Consumes: il database bonificato dal task 2.
- Produces: `registra_scontrino_pilot` con 18 parametri, firma invariata rispetto a oggi. L'app non cambia il modo in cui la chiama.
- Produces: nuovo valore `provenienza_da_verificare` in `scontrini.motivo_sospensione`, letto da `app.js` nel task 4.
- Produces: colonna `scontrini.punteggio_impronta INTEGER`.

- [ ] **Step 1: Scrivere il file**

Creare `docs/supabase-provenienza-e-chiave-duplicato.sql`:

```sql
-- docs/supabase-provenienza-e-chiave-duplicato.sql
-- Collega la verifica di provenienza alla decisione sullo scontrino, e
-- corregge due difetti emersi dai dati reali.
--
-- Eseguire dopo docs/supabase-impronte-esercizio.sql e dopo
-- docs/supabase-bonifica-doppioni.sql (l'indice unico fallirebbe se il
-- database contenesse ancora doppioni).

-- 1. Nuovo motivo di sospensione, senza togliere quelli esistenti.
ALTER TABLE public.scontrini
  DROP CONSTRAINT IF EXISTS scontrini_motivo_sospensione_check;
ALTER TABLE public.scontrini
  ADD CONSTRAINT scontrini_motivo_sospensione_check
  CHECK (motivo_sospensione IS NULL OR motivo_sospensione IN (
    'importo_oltre_soglia',
    'codice_banco_mancante',
    'provenienza_da_verificare'
  ));

-- 2. Punteggio ottenuto, salvato sulla riga: serve per tarare le soglie sui
--    dati veri invece che a intuito.
ALTER TABLE public.scontrini
  ADD COLUMN IF NOT EXISTS punteggio_impronta INTEGER;

-- 3. Nuova chiave anti-duplicato: senza importo.
--    Motivo: lo stesso scontrino e' stato accettato due volte perche' l'OCR
--    ne ha letto il totale una volta 1,20 e una volta 1.28. Con l'importo
--    nella chiave basta un errore di lettura di un centesimo, o una modifica
--    fatta apposta, per aggirare il controllo.
DROP INDEX IF EXISTS idx_scontrini_chiave_duplicato;
CREATE UNIQUE INDEX idx_scontrini_chiave_duplicato
  ON public.scontrini (matricola_rt, numero_documento, data_scontrino)
  WHERE matricola_rt IS NOT NULL AND stato <> 'rifiutato';

-- 4. La funzione completa.
CREATE OR REPLACE FUNCTION public.registra_scontrino_pilot(
  p_id                 UUID,
  p_cliente_id         UUID,
  p_bar_id             UUID,
  p_testo_ocr          TEXT,
  p_data_scontrino     DATE,
  p_ora_scontrino      TIME,
  p_numero_documento   TEXT,
  p_importo_dichiarato NUMERIC,
  p_importo_ocr        NUMERIC,
  p_importo_verificato NUMERIC,
  p_credito_generato   NUMERIC,
  p_stato              TEXT,
  p_avviso_duplicato   BOOLEAN,
  p_motivo_controllo   TEXT,
  p_operatore_label    TEXT DEFAULT NULL,
  p_matricola_rt       TEXT DEFAULT NULL,
  p_codice_banco       TEXT DEFAULT NULL,
  p_foto_path          TEXT DEFAULT NULL
)
RETURNS UUID
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  nuovo_id UUID;
  profilo_corrente_id UUID;
  documento_normalizzato TEXT;
  matricola_normalizzata TEXT;
  registratori_attivi INTEGER;
  limiti RECORD;
  scontrini_oggi INTEGER;
  punteggio INTEGER;
  caricato_dall_esercizio BOOLEAN;
  stato_finale TEXT;
  motivo_sospensione_finale TEXT;
  scadenza_sospensione TIMESTAMPTZ;
  PROGRAM_START_DATE CONSTANT DATE := '2026-07-04';
BEGIN
  IF auth.uid() IS NULL THEN
    RAISE EXCEPTION 'accesso richiesto';
  END IF;

  IF p_cliente_id IS NULL THEN
    RAISE EXCEPTION 'cliente mancante';
  END IF;

  IF p_bar_id IS NULL THEN
    RAISE EXCEPTION 'bar mancante';
  END IF;

  SELECT p.id
  INTO profilo_corrente_id
  FROM public.profili p
  WHERE p.auth_user_id = auth.uid()
  LIMIT 1;

  IF profilo_corrente_id IS NULL THEN
    RAISE EXCEPTION 'profilo non trovato';
  END IF;

  caricato_dall_esercizio := public.e_admin()
    OR public.e_salute_quotidiana()
    OR public.e_bar();

  IF NOT (
    caricato_dall_esercizio
    OR EXISTS (
      SELECT 1
      FROM public.clienti c
      WHERE c.id = p_cliente_id
        AND c.profilo_id = profilo_corrente_id
        AND c.stato = 'attivo'
    )
  ) THEN
    RAISE EXCEPTION 'cliente non autorizzato';
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM public.clienti c
    WHERE c.id = p_cliente_id AND c.stato = 'attivo'
  ) THEN
    RAISE EXCEPTION 'cliente non valido o non attivo';
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM public.bar b
    WHERE b.id = p_bar_id AND b.attivo = true
  ) THEN
    RAISE EXCEPTION 'bar non valido o non attivo';
  END IF;

  IF p_importo_dichiarato IS NULL OR p_importo_dichiarato <= 0 THEN
    RAISE EXCEPTION 'importo non valido';
  END IF;

  IF p_credito_generato IS NULL OR p_credito_generato < 0 THEN
    RAISE EXCEPTION 'credito non valido';
  END IF;

  IF p_stato NOT IN ('in_verifica', 'confermato') THEN
    RAISE EXCEPTION 'stato non ammesso';
  END IF;

  IF p_data_scontrino IS NULL THEN
    RAISE EXCEPTION 'data scontrino mancante';
  END IF;

  IF p_data_scontrino > CURRENT_DATE THEN
    RAISE EXCEPTION 'data scontrino futura';
  END IF;

  IF p_data_scontrino < PROGRAM_START_DATE THEN
    RAISE EXCEPTION 'data scontrino precedente all''avvio del programma';
  END IF;

  documento_normalizzato := NULLIF(TRIM(COALESCE(p_numero_documento, '')), '');
  IF documento_normalizzato IS NULL THEN
    RAISE EXCEPTION 'numero documento mancante';
  END IF;

  matricola_normalizzata := UPPER(NULLIF(TRIM(COALESCE(p_matricola_rt, '')), ''));

  -- Quando la matricola non arriva (flusso cassiere: nessuna fotografia,
  -- quindi nessun OCR e nessun campo), la ricava il server dal registro.
  -- Senza questo, il controllo sui doppioni piu' sotto non partirebbe
  -- affatto, e lo stesso scontrino potrebbe essere caricato due volte per
  -- distrazione.
  IF matricola_normalizzata IS NULL THEN
    SELECT count(*) INTO registratori_attivi
    FROM public.registratori_telematici rt
    WHERE rt.bar_id = p_bar_id AND rt.attivo = true;

    IF registratori_attivi = 1 THEN
      SELECT UPPER(rt.matricola) INTO matricola_normalizzata
      FROM public.registratori_telematici rt
      WHERE rt.bar_id = p_bar_id AND rt.attivo = true;
    END IF;
    -- Con zero o piu' di un registratore attivo non esiste un valore
    -- univoco da ricavare: la matricola resta nulla e il controllo sui
    -- doppioni resta inattivo per quell'esercizio, come oggi. Rinuncia
    -- consapevole, da riprendere quando arrivera' un esercizio con due casse.
  END IF;

  IF matricola_normalizzata IS NOT NULL THEN
    IF NOT EXISTS (
      SELECT 1 FROM public.registratori_telematici rt
      WHERE rt.bar_id = p_bar_id
        AND UPPER(rt.matricola) = matricola_normalizzata
        AND rt.attivo = true
    ) THEN
      RAISE EXCEPTION 'matricola registratore non riconosciuta per questo esercizio';
    END IF;

    -- Chiave senza importo: stesso registratore, stesso numero documento,
    -- stessa data significa stesso scontrino, qualunque cifra ne abbia
    -- letto l'OCR.
    IF EXISTS (
      SELECT 1 FROM public.scontrini s
      WHERE UPPER(s.matricola_rt) = matricola_normalizzata
        AND LOWER(TRIM(COALESCE(s.numero_documento, ''))) = LOWER(documento_normalizzato)
        AND s.data_scontrino = p_data_scontrino
        AND s.stato <> 'rifiutato'
    ) THEN
      RAISE EXCEPTION 'scontrino duplicato: stessa matricola, numero documento e data';
    END IF;
  END IF;

  SELECT * INTO limiti FROM public.limiti_bar WHERE bar_id = p_bar_id;
  IF NOT FOUND THEN
    limiti.tetto_giornaliero_scontrini := 3;
    limiti.soglia_revisione_manuale := 30;
    limiti.sospensione_giorni := 12;
    limiti.soglia_impronta := 3;
  END IF;

  SELECT count(*) INTO scontrini_oggi
  FROM public.scontrini s
  WHERE s.cliente_id = p_cliente_id
    AND s.bar_id = p_bar_id
    AND s.data_scontrino = p_data_scontrino
    AND s.stato <> 'rifiutato';

  IF scontrini_oggi >= limiti.tetto_giornaliero_scontrini THEN
    RAISE EXCEPTION 'tetto giornaliero di scontrini raggiunto per questo cliente';
  END IF;

  punteggio := public.punteggio_impronta_pilot(p_bar_id, p_testo_ocr);

  -- Catena a cinque rami. L'ordine conta.
  IF p_importo_dichiarato > limiti.soglia_revisione_manuale THEN
    -- Sopra soglia si guarda sempre, da chiunque arrivi: il controllo non
    -- riguarda la fiducia in chi carica ma la plausibilita' della cifra.
    stato_finale := 'in_verifica';
    motivo_sospensione_finale := 'importo_oltre_soglia';
    scadenza_sospensione := NULL;

  ELSIF caricato_dall_esercizio THEN
    -- Carica l'esercizio stesso, o Salute Quotidiana. Provenienza e presenza
    -- sono dimostrate per definizione: e' il titolare del registratore che
    -- attesta la consumazione, davanti al cliente. Chiedergli il codice che
    -- espone lui stesso, o l'OCR di una fotografia che non scatta, non
    -- dimostrerebbe nulla di piu'.
    -- Questo ramo corregge anche il credito dei clienti senza smartphone, che
    -- fino a oggi restava sospeso in attesa di un'attivazione impossibile e
    -- scadeva dopo 12 giorni.
    stato_finale := 'confermato';
    motivo_sospensione_finale := NULL;
    scadenza_sospensione := NULL;

  ELSIF punteggio < COALESCE(limiti.soglia_impronta, 3) THEN
    -- Il testo letto dalla fotografia non contiene abbastanza elementi
    -- dell'esercizio. Prima del codice banco: un codice valido non deve
    -- confermare uno scontrino estraneo.
    stato_finale := 'in_verifica';
    motivo_sospensione_finale := 'provenienza_da_verificare';
    scadenza_sospensione := NULL;

  ELSIF public.verifica_codice_banco_interna(p_bar_id, p_codice_banco) THEN
    stato_finale := 'confermato';
    motivo_sospensione_finale := NULL;
    scadenza_sospensione := NULL;

  ELSE
    stato_finale := 'in_verifica';
    motivo_sospensione_finale := 'codice_banco_mancante';
    scadenza_sospensione := NOW() + (COALESCE(limiti.sospensione_giorni, 12) || ' days')::INTERVAL;
  END IF;

  INSERT INTO public.scontrini (
    id, cliente_id, bar_id, testo_ocr,
    data_scontrino, ora_scontrino, numero_documento,
    importo_dichiarato, importo_ocr, importo_verificato,
    credito_generato, stato, avviso_duplicato,
    motivo_rifiuto, operatore_label, matricola_rt,
    motivo_sospensione, sospeso_scaduto_il, foto_path,
    punteggio_impronta
  )
  VALUES (
    COALESCE(p_id, gen_random_uuid()),
    p_cliente_id,
    p_bar_id,
    p_testo_ocr,
    p_data_scontrino,
    p_ora_scontrino,
    documento_normalizzato,
    p_importo_dichiarato,
    p_importo_ocr,
    p_importo_verificato,
    p_credito_generato,
    stato_finale,
    COALESCE(p_avviso_duplicato, false),
    NULLIF(TRIM(COALESCE(p_motivo_controllo, '')), ''),
    NULLIF(TRIM(COALESCE(p_operatore_label, '')), ''),
    matricola_normalizzata,
    motivo_sospensione_finale,
    scadenza_sospensione,
    NULLIF(TRIM(COALESCE(p_foto_path, '')), ''),
    punteggio
  )
  RETURNING id INTO nuovo_id;

  RETURN nuovo_id;
END;
$$;

REVOKE ALL ON FUNCTION public.registra_scontrino_pilot(
  uuid, uuid, uuid, text, date, time, text,
  numeric, numeric, numeric, numeric, text, boolean, text, text, text, text, text
) FROM anon;

GRANT EXECUTE ON FUNCTION public.registra_scontrino_pilot(
  uuid, uuid, uuid, text, date, time, text,
  numeric, numeric, numeric, numeric, text, boolean, text, text, text, text, text
) TO authenticated;

-- 5. La coda di revisione deve mostrare entrambi i motivi, con il punteggio e
--    la fotografia: la revisione si fa guardando la foto.
DROP VIEW IF EXISTS public.scontrini_revisione_manuale_pilot;
CREATE VIEW public.scontrini_revisione_manuale_pilot
WITH (security_invoker = true)
AS
SELECT
  s.id,
  s.cliente_id,
  c.codice_cliente,
  c.nome,
  c.cognome,
  s.data_scontrino,
  s.numero_documento,
  s.importo_dichiarato,
  s.credito_generato,
  s.motivo_sospensione,
  s.punteggio_impronta,
  s.foto_path,
  s.created_at
FROM public.scontrini s
JOIN public.clienti c ON c.id = s.cliente_id
WHERE s.stato = 'in_verifica'
  AND s.motivo_sospensione IN ('importo_oltre_soglia', 'provenienza_da_verificare')
ORDER BY s.created_at DESC;

GRANT SELECT ON public.scontrini_revisione_manuale_pilot TO authenticated;
REVOKE ALL ON public.scontrini_revisione_manuale_pilot FROM anon;

-- 6. La vista del cliente espone il nuovo motivo, per il messaggio in app.
DROP VIEW IF EXISTS public.scontrini_app_pilot;
CREATE VIEW public.scontrini_app_pilot
WITH (security_invoker = true)
AS
SELECT
  s.id,
  s.cliente_id,
  s.testo_ocr,
  s.data_scontrino,
  s.ora_scontrino,
  s.numero_documento,
  s.importo_dichiarato,
  s.importo_ocr,
  s.credito_generato,
  s.stato,
  s.avviso_duplicato,
  s.motivo_rifiuto,
  s.motivo_sospensione,
  s.sospeso_scaduto_il,
  s.foto_path,
  s.punteggio_impronta,
  s.created_at,
  s.updated_at
FROM public.scontrini s;

GRANT SELECT ON public.scontrini_app_pilot TO authenticated;
REVOKE ALL ON public.scontrini_app_pilot FROM anon;

NOTIFY pgrst, 'reload schema';
```

- [ ] **Step 2: Consegnare ad Angelo**

Chiedere di lanciare `docs/supabase-provenienza-e-chiave-duplicato.sql` nell'SQL Editor. Attendere conferma di esecuzione senza errori.

Se l'indice unico fallisce con `could not create unique index`, significa che il task 2 non è stato completato o sono nel frattempo arrivati nuovi doppioni: tornare alla parte 1 della bonifica.

- [ ] **Step 3: Verifica dal vivo dei rami**

Chiedere ad Angelo di eseguire questa verifica, che legge lo stato del sistema senza modificarlo:

```sql
SELECT
  s.created_at AT TIME ZONE 'Europe/Rome' AS caricato_il,
  s.importo_dichiarato,
  s.stato,
  s.motivo_sospensione,
  s.punteggio_impronta,
  s.matricola_rt
FROM public.scontrini s
ORDER BY s.created_at DESC
LIMIT 5;
```

Poi chiedergli di caricare **un vero scontrino del bar, da un account cliente** (non da `salute_quotidiana` né da `titolare_bar`: quei due entrano nel ramo dell'esercizio e verrebbe confermato senza passare dalla provenienza, provando un ramo diverso da quello che si crede di provare).

Atteso: `stato = confermato`, `motivo_sospensione` nullo, `punteggio_impronta` intorno a 9-10.

- [ ] **Step 4: Commit**

```bash
git add docs/supabase-provenienza-e-chiave-duplicato.sql
git commit -m "Provenienza verificata sul server e chiave anti-duplicato senza importo"
```

---

### Task 4: Allineamento dell'app

Il controllo sui doppioni dentro il browser deve usare la stessa chiave del server, altrimenti blocca caricamenti che il server accetterebbe. E il nuovo motivo di sospensione ha bisogno del suo messaggio.

**Files:**
- Modify: `app.js` (`findDuplicateReceipt`, il blocco messaggi in `submitReceipt`, `APP_VERSION`)
- Modify: `index.html` (stringa `app.js?v=NN`)
- Create: `test/test-duplicato-senza-importo.js`

**Interfaces:**
- Consumes: il valore `provenienza_da_verificare` in `motivo_sospensione`, prodotto dal task 3.

- [ ] **Step 1: Scrivere il test che fallisce**

Creare `test/test-duplicato-senza-importo.js`. Il test estrae la funzione vera da `app.js` invece di riscriverla, così non può divergere dal codice che va in produzione: metodo già usato in questo progetto.

```javascript
// Verifica che findDuplicateReceipt riconosca come doppione lo stesso
// scontrino anche quando l'OCR ne ha letto un importo diverso.
//
// Caso reale: documento 2319-0004 del 02/09/2026 e' stato accettato due volte
// perche' letto una volta 1,20 e una volta 1.28. Il server ora ignora
// l'importo nella chiave; il browser deve fare altrettanto, altrimenti i due
// controlli non concordano.

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
```

- [ ] **Step 2: Lanciare il test e verificare che fallisca**

Eseguire: `node test/test-duplicato-senza-importo.js`

Atteso: `FALLITO stesso scontrino, importo letto diverso (doppione=false, atteso=true)` e uscita con codice 1. Fallisce perché la funzione attuale confronta anche l'importo.

- [ ] **Step 3: Togliere l'importo dal confronto**

In `app.js`, sostituire il corpo di `findDuplicateReceipt` (oggi intorno alla riga 3020):

```javascript
function findDuplicateReceipt(receipt) {
  const documentNumber = cleanText(receipt.documentNumber).toLowerCase();

  // L'importo non fa parte della chiave, come sul server: lo stesso scontrino
  // e' stato accettato due volte perche' l'OCR ne aveva letto il totale una
  // volta 1,20 e una volta 1.28. Stesso esercizio, stesso numero documento e
  // stessa data significano stesso scontrino, qualunque cifra sia stata letta.
  return state.receipts.find((item) => (
    item.barName === receipt.barName &&
    item.receiptDate === receipt.receiptDate &&
    cleanText(item.documentNumber).toLowerCase() === documentNumber &&
    item.status !== "rejected"
  ));
}
```

- [ ] **Step 4: Lanciare il test e verificare che passi**

Eseguire: `node test/test-duplicato-senza-importo.js`

Atteso: tutti i casi `OK`, uscita con codice 0.

- [ ] **Step 5: Aggiornare il messaggio mostrato al cliente**

In `app.js`, nel blocco che oggi distingue i messaggi dopo l'invio (intorno alla riga 1908), aggiungere il ramo per il nuovo motivo **prima** di quello generico:

```javascript
  } else if (supabaseResult.motivoSospensione === "provenienza_da_verificare") {
    // Nessuna accusa: la causa piu' probabile e' una fotografia poco leggibile.
    setReceiptSubmitStatus(
      "Scontrino ricevuto. Prima di accreditare il credito controlliamo la foto: se e' tutto in ordine lo trovi accreditato a breve.",
      "success"
    );
    showToast("Scontrino ricevuto, in controllo.");
  } else if (supabaseResult.motivoSospensione === "codice_banco_mancante") {
```

Verificare che `saveReceiptToSupabase` restituisca già `motivoSospensione`: legge `scontrini_app_pilot` dopo l'inserimento e la vista espone quella colonna.

- [ ] **Step 6: Aggiornare il messaggio di errore del doppione**

In `app.js`, nella mappa `messaggiErrore` dentro `saveReceiptToSupabase`, la chiave deve corrispondere al nuovo testo sollevato dal server:

```javascript
      "scontrino duplicato: stessa matricola, numero documento e data":
        "Questo scontrino risulta gia' caricato (stesso registratore, numero documento e data).",
```

Togliere la voce vecchia, quella che finisce con "data e importo": non verra' piu' sollevata.

Inoltre, nel messaggio del controllo lato browser (oggi "Questo scontrino risulta gia' caricato: stessa data, numero documento e importo."), togliere il riferimento all'importo:

```javascript
    stopReceiptSubmit("Questo scontrino risulta gia' caricato: stesso esercizio, numero documento e data.");
```

- [ ] **Step 7: Alzare la versione**

In `app.js`: `const APP_VERSION = "v77";`
In `index.html`: `<script src="app.js?v=77"></script>`

- [ ] **Step 8: Verificare che non ci siano regressioni**

Eseguire, tutti devono passare:

```bash
node --check app.js
node test/test-campi-form-scontrino.js
node test/test-duplicato-senza-importo.js
```

- [ ] **Step 9: Commit**

```bash
git add app.js index.html test/test-duplicato-senza-importo.js
git commit -m "v77: doppioni riconosciuti senza l'importo, messaggio per la provenienza in controllo"
```

---

### Task 5: Pubblicazione e verifica dal vivo

**Files:** nessuna modifica.

- [ ] **Step 1: Pubblicare**

```bash
git push origin main
```

Se il push viene rifiutato con `denied to angelo-infermiere`, l'account attivo di `gh` è quello sbagliato:

```bash
gh auth switch --hostname github.com --user angelorosso073-cyber
```

- [ ] **Step 2: Attendere la pubblicazione e verificare i file serviti**

```bash
gh api repos/angelorosso073-cyber/credito-salute-sq-app/pages/builds/latest --jq '{status, commit: .commit[0:7], error: .error.message}'
```

Se lo stato risulta `errored` senza dettagli, chiedere una ricostruzione prima di cercare colpe nel commit: è già successo una volta e la ricostruzione è passata senza modifiche.

```bash
gh api --method POST repos/angelorosso073-cyber/credito-salute-sq-app/pages/builds
```

A pubblicazione avvenuta, verificare che il file servito sia quello nuovo:

```bash
curl -s "https://angelorosso073-cyber.github.io/credito-salute-sq-app/app.js?v=77" | grep APP_VERSION | head -1
```

Atteso: `const APP_VERSION = "v77";`

- [ ] **Step 3: Prova reale, con Angelo**

Chiedere ad Angelo, **da un account cliente**:

1. Aprire l'app e verificare che mostri `v77`. Se mostra v76, la PWA sta servendo la cache: aprire `https://angelorosso073-cyber.github.io/credito-salute-sq-app/index.html?fresh=1` in Chrome normale.
2. Caricare uno scontrino vero del bar con il codice del banco. Atteso: confermato, `punteggio_impronta` intorno a 9-10.
3. Caricare la fotografia di uno scontrino di un altro negozio. Atteso: **non confermato**, `motivo_sospensione = provenienza_da_verificare`, e il messaggio che parla di controllo della foto.
4. Provare a ricaricare uno scontrino già caricato. Atteso: messaggio di doppione.

Poi, **dall'account del bar**, caricare uno scontrino dal flusso cassiere per un cliente. Atteso: confermato subito, nessun motivo di sospensione, matricola valorizzata `2CISI000611` anche se il flusso non la manda.

- [ ] **Step 4: Chiudere gli strumenti di diagnosi**

Se il codice banco non dà più problemi, rimuovere la funzione di diagnosi temporanea creata durante il debug:

```sql
DROP FUNCTION IF EXISTS public.diagnostica_codice_banco_pilot(uuid, text);
```

---

## Cosa questo piano non fa

Elencato perché non venga scambiato per dimenticanza:

- **Nessuna interfaccia per gestire le impronte.** Con un solo esercizio si popolano via SQL. Servirà quando gli esercizi saranno più d'uno, insieme al resto della gestione multi-esercizio già segnalata come aperta.
- **Nessuna difesa contro un testo OCR falsificato.** `p_testo_ocr` lo manda il client: chi sa manipolare le richieste può costruirlo a tavolino. La difesa vera sarebbe un OCR eseguito sul server sulla fotografia già archiviata. Fuori portata oggi.
- **Nessuna modifica alla chiave anti-duplicato per gli scontrini senza matricola** in esercizi con più registratori: resta scoperto come oggi, e il codice lo dice esplicitamente.
- **`ora_scontrino` non entra nella chiave.** Era la richiesta di partenza del 01/09, ma i dati reali hanno mostrato che non avrebbe intercettato il doppione vero (le due letture avevano la stessa ora, 07:27): a intercettarlo è stato togliere l'importo. Se resta desiderata, va valutata a parte.
- **Nessuna guardia sugli anni implausibili letti dall'OCR** (il `2626`): difetto noto e separato, non riguarda la provenienza.
