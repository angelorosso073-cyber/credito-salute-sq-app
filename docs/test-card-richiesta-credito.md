# Test card richiesta credito

Obiettivo: simulare credito SQ confermato per verificare card, form richiesta e coda Salute Quotidiana.

## 1. Attiva funzioni test

In Supabase SQL Editor eseguire:

```text
docs/supabase-test-simula-credito-sq.sql
```

## 2. Trova ID cliente

Sostituisci l'email con quella del cliente test:

```sql
select
  c.id,
  c.codice_cliente,
  c.nome,
  c.cognome,
  c.email
from public.clienti c
where lower(c.email) = lower('EMAIL-CLIENTE-TEST');
```

Se la colonna `email` non e' valorizzata, cerca per telefono:

```sql
select
  c.id,
  c.codice_cliente,
  c.nome,
  c.cognome,
  c.telefono
from public.clienti c
where c.telefono ilike '%3330000001%';
```

## 3. Simula credito

Sostituisci `ID-CLIENTE` con l'id copiato dalla query precedente.

Per testare credito parziale, ad esempio 5 euro SQ su una prestazione da 20 euro:

```sql
select public.test_simula_credito_sq('ID-CLIENTE', 5);
```

Per testare copertura completa della prima prestazione:

```sql
select public.test_simula_credito_sq('ID-CLIENTE', 20);
```

Per testare saldo maggiore:

```sql
select public.test_simula_credito_sq('ID-CLIENTE', 25);
```

Per testare tutte le differenze basse o nulle:

```sql
select public.test_simula_credito_sq('ID-CLIENTE', 30);
```

Nota: se aggiungi piu' simulazioni, il saldo cresce. Per esempio 20 + 25 = 45 euro SQ.

## 4. Test web app

1. Ricarica la web app con `Ctrl + F5`.
2. Accedi come cliente.
3. Verifica che nel saldo appaia la card `Credito SQ disponibile` anche con credito inferiore al costo pieno della prestazione.
4. Clicca `Richiedi utilizzo credito`.
5. Controlla che il form mostri credito applicabile e differenza stimata.
6. Invia una richiesta.
7. Accedi come Salute Quotidiana.
8. Verifica che la richiesta appaia nella coda.

## 5. Ripulisci dati test

Per rimuovere solo gli scontrini test di un cliente:

```sql
select public.test_rimuovi_credito_sq('ID-CLIENTE');
```

Per rimuovere tutti gli scontrini test:

```sql
select public.test_rimuovi_credito_sq(null);
```

Gli scontrini test hanno numero documento che inizia con:

```text
TEST-SQ-
```
