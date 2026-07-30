-- supabase-lista-silenziosi-rls.sql
-- RLS per le 3 tabelle Lista dei Silenziosi.
-- Le RPC sono SECURITY DEFINER e bypassano RLS: non servono policy INSERT.
-- Solo salute_quotidiana e admin possono leggere i dati (viste incluse).

ALTER TABLE valutazioni_bisogno_silenziosi ENABLE ROW LEVEL SECURITY;
ALTER TABLE fondo_silenziosi_donazioni     ENABLE ROW LEVEL SECURITY;
ALTER TABLE fondo_silenziosi_erogazioni    ENABLE ROW LEVEL SECURITY;

CREATE POLICY "silenziosi_valutazioni_select" ON valutazioni_bisogno_silenziosi
  FOR SELECT USING (
    EXISTS (
      SELECT 1 FROM profili
      WHERE profili.id = auth.uid()
        AND profili.ruolo IN ('salute_quotidiana', 'controllo_sq', 'admin')
    )
  );

CREATE POLICY "silenziosi_donazioni_select" ON fondo_silenziosi_donazioni
  FOR SELECT USING (
    EXISTS (
      SELECT 1 FROM profili
      WHERE profili.id = auth.uid()
        AND profili.ruolo IN ('salute_quotidiana', 'controllo_sq', 'admin')
    )
  );

CREATE POLICY "silenziosi_erogazioni_select" ON fondo_silenziosi_erogazioni
  FOR SELECT USING (
    EXISTS (
      SELECT 1 FROM profili
      WHERE profili.id = auth.uid()
        AND profili.ruolo IN ('salute_quotidiana', 'controllo_sq', 'admin')
    )
  );
