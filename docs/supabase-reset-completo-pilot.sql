-- Credito Salute SQ — Reset completo dati pilot
-- Elimina TUTTI i dati. Schema, tabelle, RPC e RLS restano intatti.
-- DA APPLICARE in Supabase SQL Editor.
-- ATTENZIONE: azione irreversibile. Fare solo prima del pilot reale.

-- Gli auth.users vanno eliminati SEPARATAMENTE dal dashboard
-- Supabase → Authentication → Users → elimina manualmente.

TRUNCATE TABLE
  public.richieste_utilizzo_credito,
  public.utilizzi_credito,
  public.scontrini,
  public.clienti,
  public.profili,
  public.bar
CASCADE;
