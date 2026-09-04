-- Credito Salute SQ - Fix RLS: il ruolo bar non poteva leggere la tabella clienti
--
-- Sintomo: nella sezione bar > Carica scontrino (cassiere), la ricerca cliente
-- per nome o telefono non trovava mai nessuno, nemmeno clienti gia' iscritti
-- con scontrini caricati.
--
-- Causa: la policy "clienti_select_proprio_o_sq" (da supabase-rls-pilot-salute-admin.sql)
-- permetteva SELECT su public.clienti solo a salute_quotidiana, admin o al
-- cliente sul proprio record. Mancava il ramo per il ruolo bar/titolare_bar,
-- nonostante la funzione public.e_bar() esistesse gia'. La vista
-- clienti_app_pilot (security_invoker = true) rispetta questa RLS, quindi
-- per l'account bar tornava sempre vuota.
--
-- Il pannello "Report bar" non ne risentiva perche' passa da una RPC
-- security definer (report_bar_corrente_pilot) che bypassa la RLS. Solo la
-- ricerca cliente diretta ne era colpita.
--
-- Applicato su Supabase il 04/09/2026.

drop policy if exists "clienti_select_proprio_o_sq" on public.clienti;
create policy "clienti_select_proprio_o_sq"
on public.clienti
for select
to authenticated
using (
  public.e_salute_quotidiana()
  or public.e_admin()
  or public.e_bar()
  or exists (
    select 1
    from public.profili p
    where p.id = clienti.profilo_id
      and p.auth_user_id = auth.uid()
  )
);

notify pgrst, 'reload schema';
