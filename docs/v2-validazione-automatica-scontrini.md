# Credito Salute SQ - Validazione automatica scontrini

Obiettivo: aiutare Salute Quotidiana a capire quali scontrini sono piu' puliti e quali richiedono attenzione.

La V2 usa una validazione automatica a regole, ma dopo l'hardening di sicurezza non conferma piu' credito in automatico.

## 1. Esiti

Uno scontrino puo' finire in due esiti operativi:

1. `in_verifica`: stato iniziale obbligatorio per ogni nuovo scontrino.
2. `confermato`: stato assegnato solo dopo controllo Salute Quotidiana o admin.

Il titolare del bar non deve fare controllo quotidiano.

## 2. Controlli automatici attuali

Lo scontrino viene marcato come "controlli automatici superati" solo se:

1. data presente;
2. ora presente;
3. numero documento presente;
4. importo valido;
5. importo non superiore a 30 euro;
6. data non futura;
7. data non piu' vecchia di 14 giorni;
8. nessun duplicato rilevato;
9. testo OCR presente;
10. confidenza OCR almeno 45%;
11. nessuna parola esclusa rilevata.

## 3. Parole escluse

Il sistema manda in controllo gli scontrini che contengono parole collegate a:

1. scommesse;
2. lotto;
3. gratta e vinci;
4. vincite;
5. ricariche;
6. tabacchi;
7. sigarette;
8. bollettini;
9. servizi esterni.

## 4. Riconoscimento bar

Per ora il sistema prova a riconoscere il bar dal testo OCR usando parole chiave come:

```text
francofonte
```

Se non riconosce il bar, lo considera un avviso, non un blocco automatico.

## 5. Limite della soluzione

Questa validazione riduce il lavoro manuale, ma non certifica al 100% che lo scontrino sia reale e non rende il credito subito disponibile.

La versione piu' robusta e' la riconciliazione con export vendite del bar:

1. il bar esporta le vendite dal registratore/POS;
2. il sistema confronta automaticamente data, ora, documento e importo;
3. solo le mancate corrispondenze vengono evidenziate come casi sospetti.

## 6. Regola operativa consigliata

Nel pilot:

1. credito disponibile solo dopo conferma Salute Quotidiana o admin;
2. anomalie visibili solo a Salute Quotidiana;
3. nessuna verifica ordinaria richiesta al titolare del bar;
4. controllo manuale SQ prima che il credito diventi utilizzabile.
