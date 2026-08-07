const STORAGE_KEY = "creditoSaluteSqPilot";
const APP_VERSION = "v54";
const CREDIT_RATE = 0.15;
const AUTH_REQUEST_TIMEOUT_MS = 25000;
const BAR_NAME = "Bar pilota Francofonte";
const MAX_PILOT_CUSTOMERS = 20;
const AUTO_APPROVE_MAX_AMOUNT = 30;
const MIN_OCR_CONFIDENCE = 45;
const MAX_RECEIPT_AGE_DAYS = 14;
const EXCLUDED_RECEIPT_TERMS = [
  "scommess",
  "lotto",
  "superenalotto",
  "gratta",
  "vincita",
  "ricarica",
  "tabac",
  "sigarette",
  "pagamento bollett",
  "servizi lis"
];
const BAR_VALIDATION_KEYWORDS = [
  "francofonte"
];
const ROLE_LABELS = {
  guest: "Accesso pubblico",
  cliente: "Cliente",
  bar: "Bar",
  salute_quotidiana: "Salute Quotidiana",
  admin: "Admin"
};

const ROLE_TAB_ACCESS = {
  guest: [],
  cliente: ["cliente", "regole"],
  bar: ["bar_report", "regole"],
  salute_quotidiana: ["cliente", "bar", "salute", "report", "regole"],
  admin: ["cliente", "bar", "salute", "report", "regole"]
};

const AUTH_ROLE_MAP = {
  cliente: "cliente",
  bar: "bar",
  titolare_bar: "bar",
  salute: "salute_quotidiana",
  salute_quotidiana: "salute_quotidiana",
  controllo_sq: "salute_quotidiana",
  admin: "admin"
};

const services = {
  "Iniezione intramuscolare I.M. (su prescrizione)": { price: 8 },
  "Prelievo ematico periferico": { price: 10 },
  "Medicazione semplice": { price: 13 },
  "Controllo parametri di base + educazione sanitaria": { price: 16 },
  "Prelievo arterioso": { price: 20 },
  "Medicazioni complesse": { price: 20 },
  "Ulcere ipertrofiche e piede diabetico": { price: 20 },
  "Gestione medicazione tracheostomia": { price: 30 },
  "Catetere vescicale a permanenza / cateterismo estemporaneo": { price: 35 },
  "Gestione PICC (cateteri venosi centrali)": { price: 35 },
  "Posizionamento e gestione sondino naso gastrico": { price: 40 },
  "Posizionamento ago di Huber": { price: 45 },
  "ECG": { price: 30, available: false },
  "Holter ECG 24h": { price: 48, available: false },
  "Holter pressorio 24h": { price: 42, available: false },
  "Spirometria semplice": { price: 30, available: false }
};

const REQUEST_STATUSES = {
  inviata: "Inviata",
  in_contatto: "In contatto",
  confermata: "Confermata",
  rifiutata: "Rifiutata",
  annullata: "Annullata"
};

const initialState = {
  customers: [],
  receipts: [],
  redemptions: [],
  creditRequests: [],
  balances: {},
  barReport: null,
  nextCustomerNumber: 1
};

let state = loadState();
let currentOcrResult = null;
let supabaseClient = null;
let activeBar = null;
let cameraStream = null;
let cameraReceiptFile = null;
let authSession = null;
let authProfile = null;
let authRole = "guest";
let authReady = false;
let pilotDataLoading = false;
let suppressLocalPersistence = false;

const el = {
  tabs: document.querySelectorAll(".tab-button"),
  panels: document.querySelectorAll(".tab-panel"),
  appTabs: document.querySelector("#appTabs"),
  appMain: document.querySelector("#appMain"),
  authForm: document.querySelector("#authForm"),
  signupForm: document.querySelector("#signupForm"),
  authEmail: document.querySelector("#authForm input[name='email']"),
  authPassword: document.querySelector("#authForm input[name='password']"),
  authSubmit: document.querySelector("#authSubmit"),
  signupSubmit: document.querySelector("#signupSubmit"),
  authLogout: document.querySelector("#authLogout"),
  authStatus: document.querySelector("#authStatus"),
  signupStatus: document.querySelector("#signupStatus"),
  authRole: document.querySelector("#authRole"),
  customerForm: document.querySelector("#customerForm"),
  receiptForm: document.querySelector("#receiptForm"),
  redemptionForm: document.querySelector("#redemptionForm"),
  customerSelect: document.querySelector("#customerSelect"),
  receiptCustomerSelect: document.querySelector("#receiptCustomerSelect"),
  redemptionCustomerSelect: document.querySelector("#redemptionCustomerSelect"),
  balanceCards: document.querySelector("#balanceCards"),
  creditRequestArea: document.querySelector("#creditRequestArea"),
  creditRequestForm: document.querySelector("#creditRequestForm"),
  creditRequestService: document.querySelector("#creditRequestService"),
  creditRequestBeneficiaryType: document.querySelector("#creditRequestBeneficiaryType"),
  creditRequestStatus: document.querySelector("#creditRequestStatus"),
  donazioneSilenziosiForm: document.querySelector("#donazioneSilenziosiForm"),
  donazioneSilenziosiStatus: document.querySelector("#donazioneSilenziosiStatus"),
  valutazioneBisogniForm: document.querySelector("#valutazioneBisogniForm"),
  valutazioneBisogniStatus: document.querySelector("#valutazioneBisogniStatus"),
  silenziosiFondoMetrics: document.querySelector("#silenziosiFondoMetrics"),
  silenziosiBeneficiariList: document.querySelector("#silenziosiBeneficiariList"),
  erogazioneSilenziosiForm: document.querySelector("#erogazioneSilenziosiForm"),
  erogazioneSilenziosiBeneficiario: document.querySelector("#erogazioneSilenziosiBeneficiario"),
  erogazioneSilenziosiPrestazione: document.querySelector("#erogazioneSilenziosiPrestazione"),
  erogazioneSilenziosiStatus: document.querySelector("#erogazioneSilenziosiStatus"),
  revisioneManualeList: document.querySelector("#revisioneManualeList"),
  revisioneManualeDetails: document.querySelector("#revisioneManualeDetails"),
  richiesteCreditoDetails: document.querySelector("#richiesteCreditoDetails"),
  customerCreditRequests: document.querySelector("#customerCreditRequests"),
  customerCreditRequestsDetails: document.querySelector("#customerCreditRequestsDetails"),
  creditRequestAlert: document.querySelector("#creditRequestAlert"),
  customerHistory: document.querySelector("#customerHistory"),
  customerRedemptionHistory: document.querySelector("#customerRedemptionHistory"),
  receiptCalculation: document.querySelector("#receiptCalculation"),
  receiptSubmitStatus: document.querySelector("#receiptSubmitStatus"),
  receiptOcrStatus: document.querySelector("#receiptOcrStatus"),
  receiptOcrText: document.querySelector("#receiptOcrText"),
  receiptOcrDetails: document.querySelector("#receiptOcrDetails"),
  rerunOcr: document.querySelector("#rerunOcr"),
  openCamera: document.querySelector("#openCamera"),
  captureReceipt: document.querySelector("#captureReceipt"),
  closeCamera: document.querySelector("#closeCamera"),
  cameraPreview: document.querySelector("#cameraPreview"),
  cameraVideo: document.querySelector("#cameraVideo"),
  cameraCanvas: document.querySelector("#cameraCanvas"),
  cameraStatus: document.querySelector("#cameraStatus"),
  receiptList: document.querySelector("#receiptList"),
  statusFilter: document.querySelector("#statusFilter"),
  barReportMetrics: document.querySelector("#barReportMetrics"),
  barReportReceipts: document.querySelector("#barReportReceipts"),
  barReportStatus: document.querySelector("#barReportStatus"),
  reportMetrics: document.querySelector("#reportMetrics"),
  redemptionHistory: document.querySelector("#redemptionHistory"),
  redemptionStatus: document.querySelector("#redemptionStatus"),
  creditRequestQueue: document.querySelector("#creditRequestQueue"),
  headerClients: document.querySelector("#headerClients"),
  headerConfirmed: document.querySelector("#headerConfirmed"),
  supabaseStatus: document.querySelector("#supabaseStatus"),
  exportJson: document.querySelector("#exportJson"),
  exportCsv: document.querySelector("#exportCsv"),
  exportOutput: document.querySelector("#exportOutput"),
  clearDemo: document.querySelector("#clearDemo"),
  toast: document.querySelector("#toast"),
  saldoPublicPage: document.querySelector("#saldoPublicPage"),
  cassiereSearchInput: document.querySelector("#cassiereSearchInput"),
  cassiereSearchBtn: document.querySelector("#cassiereSearchBtn"),
  cassiereResults: document.querySelector("#cassiereResults"),
  cassiereSelectedCustomer: document.querySelector("#cassiereSelectedCustomer"),
  cassiereCustomerLabel: document.querySelector("#cassiereCustomerLabel"),
  cassiereReceiptForm: document.querySelector("#cassiereReceiptForm"),
  cassiereReceiptStatus: document.querySelector("#cassiereReceiptStatus"),
  cassiereMessageArea: document.querySelector("#cassiereMessageArea"),
  cassiereWhatsAppText: document.querySelector("#cassiereWhatsAppText"),
  cassiereRegisterStatus: document.querySelector("#cassiereRegisterStatus"),
  cassiereQuickRegisterForm: document.querySelector("#cassiereQuickRegisterForm"),
  cassiereOperatorePanel: document.querySelector("#cassiereOperatorePanel"),
  cassiereOperatoreActive: document.querySelector("#cassiereOperatoreActive"),
  cassiereOperatoreLabel: document.querySelector("#cassiereOperatoreLabel"),
  redemptionMessageArea: document.querySelector("#redemptionMessageArea"),
  redemptionBarText: document.querySelector("#redemptionBarText"),
  copyBarPaymentBtn: document.querySelector("#copyBarPaymentBtn"),
  codiceBancoInput: document.querySelector("#codiceBancoInput"),
  openCodiceBancoScan: document.querySelector("#openCodiceBancoScan"),
  closeCodiceBancoScan: document.querySelector("#closeCodiceBancoScan"),
  codiceBancoScanPreview: document.querySelector("#codiceBancoScanPreview"),
  codiceBancoScanVideo: document.querySelector("#codiceBancoScanVideo"),
  codiceBancoScanCanvas: document.querySelector("#codiceBancoScanCanvas"),
  codiceBancoStatus: document.querySelector("#codiceBancoStatus"),
  creditoSospesoArea: document.querySelector("#creditoSospesoArea"),
  creditoSospesoScadenza: document.querySelector("#creditoSospesoScadenza"),
  attivaCodiceInput: document.querySelector("#attivaCodiceInput"),
  attivaCodiceBtn: document.querySelector("#attivaCodiceBtn"),
  attivaCodiceStatus: document.querySelector("#attivaCodiceStatus"),
};

document.addEventListener("DOMContentLoaded", async () => {
  const splashMin = new Promise(r => setTimeout(r, 1800));
  if (initPublicSaldo()) { hideSplash(); return; }
  initSupabase();
  wireEvents();
  renderRedemptionServiceOptions();
  setTodayDefaults();
  await bootstrapAuth();
  render();
  await splashMin;
  hideSplash();
  checkSupabaseDatabase();
  await syncDataForCurrentRole();
});

function hideSplash() {
  const splash = document.getElementById("splash");
  if (!splash) return;
  splash.classList.add("splash--hidden");
  splash.addEventListener("transitionend", () => splash.remove(), { once: true });
}

function initSupabase() {
  if (!window.supabase) {
    setSupabaseStatus(`Libreria Supabase non caricata (${APP_VERSION})`, "offline");
    return;
  }

  const hasConfig = typeof SUPABASE_URL === "string"
    && typeof SUPABASE_ANON_KEY === "string"
    && SUPABASE_URL.startsWith("https://")
    && SUPABASE_ANON_KEY.length > 20;

  if (!hasConfig) {
    setSupabaseStatus(`Configurazione Supabase mancante (${APP_VERSION})`, "offline");
    return;
  }

  supabaseClient = window.supabase.createClient(SUPABASE_URL, SUPABASE_ANON_KEY, {
    auth: {
      persistSession: false,
      autoRefreshToken: false
    }
  });
  setSupabaseStatus(`Supabase configurato (${APP_VERSION})`, "online");
}

async function bootstrapAuth() {
  authReady = false;
  if (!supabaseClient?.auth) {
    setAuthState(null, null);
    authReady = true;
    return;
  }

  const { data, error } = await supabaseClient.auth.getSession();
  if (error) {
    console.error("Errore lettura sessione auth:", error);
  }

  await setAuthState(data?.session || null);

  supabaseClient.auth.onAuthStateChange(async (_event, session) => {
    await setAuthState(session || null);
  });

  authReady = true;
}

async function setAuthState(session) {
  authSession = session || null;
  authProfile = null;
  authRole = "guest";

  if (authSession?.user) {
    authProfile = await loadProfileForUser(authSession.user);
    if (!authProfile && getUserMetadataRole(authSession.user) === "cliente") {
      authProfile = await createCustomerProfileForUser(authSession.user);
    }
    authRole = resolveAuthRole(authProfile, authSession.user);
    if (authRole === "cliente" || authRole === "bar") {
      resetPilotData();
    }
  } else {
    state = loadState();
    currentOcrResult = null;
  }

  renderAuthState();
  syncTabVisibility();
  if (shouldLoadRemoteData()) {
    await refreshPilotDataFromSupabase();
  }
  render();
  prefillCustomerFormFromAuth();
}

function resolveAuthRole(profile, user) {
  const rawRole = cleanText(
    profile?.ruolo ||
    profile?.role ||
    profile?.ruolo_operativo ||
    user?.user_metadata?.ruolo ||
    user?.user_metadata?.role
  ).toLowerCase();

  return AUTH_ROLE_MAP[rawRole] || "guest";
}

function getUserMetadataRole(user) {
  const rawRole = cleanText(
    user?.user_metadata?.ruolo ||
    user?.user_metadata?.role
  ).toLowerCase();

  return AUTH_ROLE_MAP[rawRole] || "";
}

async function loadProfileForUser(user) {
  if (!supabaseClient || !user) return null;

  try {
    const query = supabaseClient
      .from("profili")
      .select("id, auth_user_id, ruolo, email, nome_completo, telefono, created_at, updated_at")
      .eq("auth_user_id", user.id)
      .maybeSingle();

    const { data, error } = await query;
    if (!error) {
      if (data) return data;
    } else if (!looksLikeMissingColumnError(error)) {
      console.warn("Errore caricamento profilo via auth_user_id:", error);
    }
  } catch (error) {
    console.warn("Errore caricamento profilo via auth_user_id:", error);
  }

  try {
    const { data, error } = await supabaseClient
      .from("profili")
      .select("id, auth_user_id, ruolo, email, nome_completo, telefono, created_at, updated_at");

    if (error) {
      console.warn("Errore caricamento profili:", error);
      return null;
    }

    const profiles = Array.isArray(data) ? data : [];
    return profiles.find((profile) => matchesProfileToUser(profile, user)) || null;
  } catch (error) {
    console.warn("Errore caricamento profili:", error);
    return null;
  }
}

function matchesProfileToUser(profile, user) {
  if (!profile || !user) return false;

  const profileEmail = cleanText(profile.email || profile.user_email || profile.indirizzo_email).toLowerCase();
  return [
    profile.auth_user_id,
    profile.user_id,
    profile.profilo_id,
    profile.id
  ].some((value) => cleanText(value) === user.id)
    || (profileEmail && profileEmail === cleanText(user.email).toLowerCase());
}

function looksLikeMissingColumnError(error) {
  const message = cleanText(error?.message || error?.details || error?.hint).toLowerCase();
  return message.includes("does not exist") || message.includes("column") && message.includes("does not exist");
}

async function syncDataForCurrentRole() {
  if (!shouldLoadRemoteData()) {
    return;
  }

  await refreshPilotDataFromSupabase();
}

function shouldLoadRemoteData() {
  return authRole === "cliente" || authRole === "bar" || authRole === "salute_quotidiana" || authRole === "admin";
}

function resetPilotData() {
  state = structuredClone(initialState);
  currentOcrResult = null;
}

function setSupabaseStatus(message, status) {
  if (!el.supabaseStatus) return;

  el.supabaseStatus.textContent = message;
  el.supabaseStatus.dataset.status = status;
}

async function checkSupabaseDatabase() {
  if (!supabaseClient) return;

  const { data, error } = await supabaseClient
    .from("bar")
    .select("id,nome")
    .limit(1);

  if (error) {
    console.error("Errore connessione Supabase:", error);
    setSupabaseStatus("Database Supabase non leggibile", "offline");
    return;
  }

  const barName = data?.[0]?.nome || "database vuoto";
  activeBar = data?.[0] || null;
  setSupabaseStatus(`Database collegato: ${barName} (${APP_VERSION})`, "online");
}

async function loadPilotCustomersFromSupabase() {
  if (!supabaseClient) return;

  let { data, error } = await supabaseClient
    .from("clienti_app_pilot")
    .select("id,codice_cliente,nome,cognome,telefono,email,profilo_id,citta,saldo_token,created_at")
    .order("created_at", { ascending: false })
    .limit(MAX_PILOT_CUSTOMERS);

  if (error && looksLikeMissingColumnError(error)) {
    const fallback = await supabaseClient
      .from("clienti_app_pilot")
      .select("id,codice_cliente,nome,cognome,telefono,citta,saldo_token,created_at")
      .order("created_at", { ascending: false })
      .limit(MAX_PILOT_CUSTOMERS);
    data = fallback.data;
    error = fallback.error;
  }

  if (error) {
    console.error("Errore caricamento clienti Supabase:", error);
    return;
  }

  const customers = filterCustomersForCurrentRole(data.map(mapSupabaseCustomer));
  if (authRole === "cliente") {
    state.customers = customers;
    if (!customers.length) {
      setReceiptSubmitStatus("Scheda cliente non trovata. Completa il tuo profilo oppure fai collegare il record cliente da Salute Quotidiana.", "error");
    }
  } else {
    customers.forEach((customer) => upsertCustomer(customer));
  }

  saveState();
  render();
}

async function loadPilotReceiptsFromSupabase() {
  if (!supabaseClient) return;

  const { data, error } = await supabaseClient
    .from("scontrini_app_pilot")
    .select("id,cliente_id,testo_ocr,data_scontrino,ora_scontrino,numero_documento,importo_dichiarato,importo_ocr,credito_generato,stato,avviso_duplicato,motivo_rifiuto,motivo_sospensione,sospeso_scaduto_il,foto_path,created_at")
    .order("created_at", { ascending: false })
    .limit(100);

  if (error) {
    console.error("Errore caricamento scontrini Supabase:", error);
    return;
  }

  const receipts = filterItemsForCurrentCustomer(data.map(mapSupabaseReceipt));
  if (authRole === "cliente") {
    state.receipts = receipts;
  } else {
    receipts.forEach((receipt) => upsertReceipt(receipt));
  }
  saveState();
  render();
}

async function refreshPilotDataFromSupabase() {
  if (!shouldLoadRemoteData()) return;

  pilotDataLoading = true;
  render();
  suppressLocalPersistence = true;
  try {
    if (authRole === "bar") {
      await loadBarReportFromSupabase();
      return;
    }

    if (authRole === "cliente") {
      await linkCurrentCustomerToProfile();
    }
    await loadPilotCustomersFromSupabase();
    await loadPilotReceiptsFromSupabase();
    await loadPilotRedemptionsFromSupabase();
    await loadPilotBalancesFromSupabase();
    await loadCreditRequestsFromSupabase();
    if (authRole === "salute_quotidiana" || authRole === "admin") {
      await loadFondoSilenziosi();
      await loadRevisioneManuale();
    }
  } finally {
    suppressLocalPersistence = false;
    pilotDataLoading = false;
    render();
  }
}

async function loadBarReportFromSupabase() {
  if (!supabaseClient) return;

  setBarReportStatus("Caricamento report bar in corso.", "loading");
  const { data, error } = await supabaseClient.rpc("report_bar_corrente_pilot");

  if (error) {
    console.error("Errore caricamento report bar:", error);
    state.barReport = null;
    setBarReportStatus(`Report bar non disponibile: ${error.message}`, "error");
    return;
  }

  state.barReport = normalizeBarReport(data);
  setBarReportStatus("Report bar aggiornato.", "success");
  saveState();
  render();
}

function normalizeBarReport(data) {
  const report = Array.isArray(data) ? data[0] : data;
  const metrics = report?.metrics || report || {};
  const receipts = report?.recent_receipts || report?.scontrini_recenti || [];

  return {
    barName: cleanText(report?.bar_name || metrics.bar_name || BAR_NAME),
    updatedAt: report?.updated_at || new Date().toISOString(),
    metrics: {
      customers: Number(metrics.customers || metrics.clienti_iscritti || 0),
      receipts: Number(metrics.receipts || metrics.scontrini_caricati || 0),
      pending: Number(metrics.pending || metrics.scontrini_in_verifica || 0),
      confirmed: Number(metrics.confirmed || metrics.scontrini_confermati || 0),
      rejected: Number(metrics.rejected || metrics.scontrini_rifiutati || 0),
      confirmedAmount: Number(metrics.confirmed_amount || metrics.consumazioni_confermate || 0),
      generatedCredit: Number(metrics.generated_credit || metrics.credito_generato || 0),
      anomalies: Number(metrics.anomalies || metrics.anomalie || 0)
    },
    receipts: receipts.map((receipt) => ({
      id: receipt.id,
      code: cleanText(receipt.codice_cliente || receipt.customer_code || "Cliente"),
      date: receipt.data_scontrino || receipt.receipt_date || "",
      time: receipt.ora_scontrino || receipt.receipt_time || "",
      documentNumber: receipt.numero_documento || receipt.document_number || "",
      amount: Number(receipt.importo_dichiarato || receipt.amount || 0),
      credit: Number(receipt.credito_generato || receipt.credit || 0),
      status: mapSupabaseReceiptStatus(receipt.stato || receipt.status),
      duplicate: Boolean(receipt.avviso_duplicato || receipt.duplicate)
    }))
  };
}

function setBarReportStatus(message, status) {
  if (!el.barReportStatus) return;
  el.barReportStatus.textContent = message;
  if (status) {
    el.barReportStatus.dataset.status = status;
  } else {
    delete el.barReportStatus.dataset.status;
  }
}

async function linkCurrentCustomerToProfile() {
  if (!supabaseClient || authRole !== "cliente" || !authProfile?.id) {
    return;
  }

  const { error } = await supabaseClient.rpc("collega_cliente_corrente_pilot");
  if (error) {
    const message = cleanText(error.message).toLowerCase();
    if (!message.includes("collega_cliente_corrente_pilot")) {
      console.warn("Collegamento automatico cliente non riuscito:", error);
    }
  }
}

function mapSupabaseCustomer(customer) {
  return {
    id: customer.id,
    code: customer.codice_cliente,
    firstName: customer.nome,
    lastName: customer.cognome,
    email: cleanText(customer.email),
    profileId: customer.profilo_id || "",
    phone: cleanText(customer.telefono),
    city: customer.citta || "",
    saldoToken: customer.saldo_token || "",
    barName: BAR_NAME,
    createdAt: customer.created_at
  };
}

function filterCustomersForCurrentRole(customers) {
  if (authRole !== "cliente") {
    return customers;
  }

  const matchingCustomers = customers.filter((customer) => customerMatchesAuthenticatedUser(customer));
  if (matchingCustomers.length) {
    return matchingCustomers.slice(0, 1);
  }

  if (customers.length === 1) {
    return customers;
  }

  console.warn("Cliente autenticato: la vista clienti ha restituito piu' record non riconoscibili. Dati non mostrati per sicurezza.");
  return [];
}

function customerMatchesAuthenticatedUser(customer) {
  if (!customer || !authSession?.user) return false;

  const metadata = authSession.user.user_metadata || {};
  const userEmail = cleanText(authSession.user.email).toLowerCase();
  const profileId = cleanText(authProfile?.id);
  const customerProfileId = cleanText(customer.profileId);
  const customerEmail = cleanText(customer.email).toLowerCase();
  const profilePhone = normalizePhone(authProfile?.telefono || authProfile?.phone || metadata.telefono || metadata.phone);
  const customerPhone = normalizePhone(customer.phone);
  const firstName = cleanText(metadata.nome || metadata.firstName).toLowerCase();
  const lastName = cleanText(metadata.cognome || metadata.lastName).toLowerCase();
  const customerFirstName = cleanText(customer.firstName).toLowerCase();
  const customerLastName = cleanText(customer.lastName).toLowerCase();

  if (profileId && customerProfileId && profileId === customerProfileId) {
    return true;
  }

  if (userEmail && customerEmail && userEmail === customerEmail) {
    return true;
  }

  if (profilePhone && customerPhone && profilePhone === customerPhone) {
    return true;
  }

  return Boolean(firstName && lastName && firstName === customerFirstName && lastName === customerLastName);
}

function filterItemsForCurrentCustomer(items) {
  if (authRole !== "cliente") {
    return items;
  }

  const allowedCustomerIds = new Set(state.customers.map((customer) => customer.id));
  if (!allowedCustomerIds.size) {
    return [];
  }

  return items.filter((item) => allowedCustomerIds.has(item.customerId));
}

function mapSupabaseReceipt(receipt) {
  const text = receipt.testo_ocr || "";
  const fields = {
    receiptDate: receipt.data_scontrino || "",
    receiptTime: receipt.ora_scontrino || "",
    documentNumber: receipt.numero_documento || "",
    amount: Number(receipt.importo_ocr || receipt.importo_dichiarato || 0)
  };

  return {
    id: receipt.id,
    customerId: receipt.cliente_id,
    barName: BAR_NAME,
    receiptDate: receipt.data_scontrino || "",
    receiptTime: receipt.ora_scontrino || "",
    documentNumber: receipt.numero_documento || "",
    amount: Number(receipt.importo_dichiarato || 0),
    credit: Number(receipt.credito_generato || 0),
    status: mapSupabaseReceiptStatus(receipt.stato),
    motivoSospensione: receipt.motivo_sospensione || null,
    sospesoScadutoIl: receipt.sospeso_scaduto_il || null,
    fotoPath: receipt.foto_path || null,
    note: receipt.motivo_rifiuto || (receipt.avviso_duplicato ? "Possibile duplicato." : ""),
    ocr: text ? createOcrSnapshot(text, fields, 0) : null,
    imageData: "",
    createdAt: receipt.created_at
  };
}

function mapSupabaseReceiptStatus(status) {
  const statuses = {
    confermato: "confirmed",
    in_verifica: "pending",
    rifiutato: "rejected",
    scaduto: "expired"
  };

  return statuses[status] || "pending";
}

async function loadRevisioneManuale() {
  if (!supabaseClient) return;

  const { data, error } = await supabaseClient
    .from("scontrini_revisione_manuale_pilot")
    .select("id,cliente_id,codice_cliente,nome,cognome,data_scontrino,numero_documento,importo_dichiarato,credito_generato,foto_path,created_at");

  if (error) {
    console.error("Errore caricamento revisione manuale:", error);
    return;
  }

  renderRevisioneManuale(data || []);
}

function renderRevisioneManuale(righe) {
  if (!el.revisioneManualeList) return;

  el.revisioneManualeList.innerHTML = righe.length
    ? righe.map((r) => `
        <div class="mini-list__row">
          <span>${escapeHtml(r.nome)} ${escapeHtml(r.cognome)} (${escapeHtml(r.codice_cliente)}) — ${r.data_scontrino} — doc. ${escapeHtml(r.numero_documento || "-")}</span>
          <strong>${formatMoney(r.importo_dichiarato)} euro — credito ${formatMoney(r.credito_generato)} euro SQ</strong>
          <div class="mini-list__actions">
            ${r.foto_path ? `<button type="button" class="secondary small" onclick="vediFotoScontrino('${r.foto_path}')">Vedi foto</button>` : ""}
            <button type="button" class="secondary small" data-revisione-conferma="${r.id}" data-revisione-importo="${r.importo_dichiarato}" data-revisione-credito="${r.credito_generato}">Conferma</button>
            <button type="button" class="secondary small" data-revisione-rifiuta="${r.id}">Rifiuta</button>
          </div>
        </div>
      `).join("")
    : `<p class="form-status">Nessuno scontrino in revisione manuale.</p>`;

  if (el.revisioneManualeDetails) el.revisioneManualeDetails.open = righe.length > 0;
}

async function handleRevisioneManualeClick(event) {
  const confermaId = event.target.dataset.revisioneConferma;
  const rifiutaId = event.target.dataset.revisioneRifiuta;
  if (!confermaId && !rifiutaId) return;

  if (!supabaseClient) return;

  if (confermaId) {
    const importo = Number(event.target.dataset.revisioneImporto);
    const credito = Number(event.target.dataset.revisioneCredito);
    const { error } = await supabaseClient.rpc("aggiorna_scontrino_pilot", {
      p_id: confermaId,
      p_stato: "confermato",
      p_importo_dichiarato: importo,
      p_importo_verificato: importo,
      p_credito_generato: credito,
      p_motivo_controllo: "Confermato manualmente dopo revisione importo elevato."
    });
    if (error) {
      console.error("Errore conferma revisione manuale:", error);
      showToast(`Errore: ${error.message}`);
      return;
    }
    showToast("Scontrino confermato.");
  }

  if (rifiutaId) {
    const { error } = await supabaseClient.rpc("aggiorna_scontrino_pilot", {
      p_id: rifiutaId,
      p_stato: "rifiutato",
      p_importo_dichiarato: null,
      p_importo_verificato: null,
      p_credito_generato: 0,
      p_motivo_controllo: "Rifiutato dopo revisione manuale importo elevato."
    });
    if (error) {
      console.error("Errore rifiuto revisione manuale:", error);
      showToast(`Errore: ${error.message}`);
      return;
    }
    showToast("Scontrino rifiutato.");
  }

  loadRevisioneManuale();
  loadPilotReceiptsFromSupabase();
  loadPilotBalancesFromSupabase();
}

async function loadPilotBalancesFromSupabase() {
  if (!supabaseClient) return;

  const { data, error } = await supabaseClient
    .from("saldi_clienti_app_pilot")
    .select("cliente_id,credito_confermato,credito_in_verifica,credito_usato,credito_totale_generato,saldo_disponibile");

  if (error) {
    console.error("Errore caricamento saldi Supabase:", error);
    return;
  }

  state.balances = {};
  const allowedCustomerIds = getAllowedCustomerIdsForCurrentRole();
  data.forEach((balance) => {
    if (allowedCustomerIds && !allowedCustomerIds.has(balance.cliente_id)) {
      return;
    }

    state.balances[balance.cliente_id] = {
      confirmed: Number(balance.saldo_disponibile || 0),
      pending: Number(balance.credito_in_verifica || 0),
      used: Number(balance.credito_usato || 0),
      totalGenerated: Number(balance.credito_totale_generato || 0),
      confirmedGenerated: Number(balance.credito_confermato || 0)
    };
  });

  saveState();
  render();
}

async function loadPilotRedemptionsFromSupabase() {
  if (!supabaseClient) return;

  const { data, error } = await supabaseClient
    .from("utilizzi_credito_app_pilot")
    .select("id,cliente_id,tipo_prestazione,prezzo_prestazione,credito_usato,importo_pagato,beneficiario,note,conferma_sq,conferma_cliente,stato_pagamento,incassato_at,created_at")
    .order("created_at", { ascending: false })
    .limit(100);

  if (error) {
    console.error("Errore caricamento utilizzi credito Supabase:", error);
    return;
  }

  const redemptions = filterItemsForCurrentCustomer(data.map(mapSupabaseRedemption));
  if (authRole === "cliente") {
    state.redemptions = redemptions;
  } else {
    redemptions.forEach((redemption) => upsertRedemption(redemption));
  }
  saveState();
  render();
}

let silenziosiBeneficiariCache = [];

async function loadFondoSilenziosi() {
  if (!supabaseClient) return;

  const { data: saldoRows, error: saldoError } = await supabaseClient
    .from("fondo_silenziosi_saldo_v")
    .select("saldo_disponibile");

  const { data: beneficiariRows, error: beneficiariError } = await supabaseClient
    .from("fondo_silenziosi_beneficiari_v")
    .select("cliente_id,punteggio,valutato_il,quota_disponibile")
    .order("quota_disponibile", { ascending: false });

  if (saldoError || beneficiariError) {
    console.error("Errore caricamento Lista dei Silenziosi:", saldoError || beneficiariError);
    return;
  }

  const saldoDisponibile = Number(saldoRows?.[0]?.saldo_disponibile || 0);
  silenziosiBeneficiariCache = beneficiariRows || [];
  renderFondoSilenziosi(saldoDisponibile, silenziosiBeneficiariCache);
}

function renderFondoSilenziosi(saldoDisponibile, beneficiari) {
  if (el.silenziosiFondoMetrics) {
    el.silenziosiFondoMetrics.innerHTML = `
      <article><span>Saldo fondo disponibile</span><strong>${formatMoney(saldoDisponibile)} euro SQ</strong></article>
      <article><span>Beneficiari ammessi</span><strong>${beneficiari.length}</strong></article>
    `;
  }

  if (el.silenziosiBeneficiariList) {
    el.silenziosiBeneficiariList.innerHTML = beneficiari.length
      ? beneficiari.map((b) => {
          const customer = getCustomer(b.cliente_id);
          const nome = customer ? `${customer.firstName} ${customer.lastName}` : b.cliente_id;
          return `<div class="mini-list__row"><span>${escapeHtml(nome)} — punteggio ${b.punteggio}</span><strong>${formatMoney(b.quota_disponibile)} euro SQ</strong></div>`;
        }).join("")
      : `<p class="form-status">Nessun beneficiario ammesso al momento.</p>`;
  }

  if (el.erogazioneSilenziosiBeneficiario) {
    el.erogazioneSilenziosiBeneficiario.innerHTML = beneficiari.map((b) => {
      const customer = getCustomer(b.cliente_id);
      const nome = customer ? `${customer.firstName} ${customer.lastName}` : b.cliente_id;
      return `<option value="${b.cliente_id}">${escapeHtml(nome)} — quota ${formatMoney(b.quota_disponibile)} euro</option>`;
    }).join("");
  }

  if (el.erogazioneSilenziosiPrestazione && !el.erogazioneSilenziosiPrestazione.options.length) {
    el.erogazioneSilenziosiPrestazione.innerHTML = Object.entries(services)
      .filter(([, config]) => config.available !== false)
      .map(([name, config]) => `<option value="${escapeHtml(name)}">${escapeHtml(name)} — ${formatMoney(config.price)} euro</option>`)
      .join("");
  }
}

function mapSupabaseRedemption(redemption) {
  return {
    id: redemption.id,
    customerId: redemption.cliente_id,
    service: redemption.tipo_prestazione,
    servicePrice: Number(redemption.prezzo_prestazione || 0),
    creditUsed: Number(redemption.credito_usato || 0),
    differenceDue: Number(redemption.importo_pagato || 0),
    beneficiary: redemption.beneficiario || "se",
    beneficiaryNote: redemption.note || "",
    confirmSq: !!redemption.conferma_sq,
    confirmCliente: !!redemption.conferma_cliente,
    paymentStatus: redemption.stato_pagamento || "da_incassare",
    incassatoAt: redemption.incassato_at || null,
    createdAt: redemption.created_at
  };
}

async function loadCreditRequestsFromSupabase() {
  if (!supabaseClient) return;

  const { data, error } = await supabaseClient
    .from("richieste_utilizzo_credito_app_pilot")
    .select("id,cliente_id,codice_cliente,cliente_nome,cliente_cognome,prestazione,prezzo_prestazione,credito_richiesto,beneficiario_tipo,beneficiario_nome,beneficiario_telefono,giorno_preferito,fascia_oraria_preferita,consenso_contatto,note_cliente,stato,note_interne_sq,created_at,updated_at")
    .order("created_at", { ascending: false })
    .limit(100);

  if (error) {
    console.warn("Richieste utilizzo credito non disponibili:", error);
    return;
  }

  const requests = filterItemsForCurrentCustomer(data.map(mapSupabaseCreditRequest));
  if (authRole === "cliente") {
    state.creditRequests = requests;
  } else {
    requests.forEach((request) => upsertCreditRequest(request));
  }
  saveState();
  render();
}

function mapSupabaseCreditRequest(request) {
  return {
    id: request.id,
    customerId: request.cliente_id,
    customerCode: request.codice_cliente || "",
    customerName: cleanText(`${request.cliente_nome || ""} ${request.cliente_cognome || ""}`),
    service: request.prestazione,
    servicePrice: Number(request.prezzo_prestazione || 0),
    creditRequested: Number(request.credito_richiesto || 0),
    beneficiaryType: request.beneficiario_tipo || "se",
    beneficiaryName: request.beneficiario_nome || "",
    beneficiaryPhone: request.beneficiario_telefono || "",
    preferredDate: request.giorno_preferito || "",
    preferredTime: request.fascia_oraria_preferita || "",
    contactConsent: Boolean(request.consenso_contatto),
    note: request.note_cliente || "",
    status: request.stato || "inviata",
    internalNote: request.note_interne_sq || "",
    createdAt: request.created_at,
    updatedAt: request.updated_at
  };
}

function upsertCustomer(customer) {
  const index = state.customers.findIndex((item) => item.id === customer.id || item.phone === customer.phone);
  if (index >= 0) {
    state.customers[index] = { ...state.customers[index], ...customer };
  } else {
    state.customers.unshift(customer);
  }
}

function upsertReceipt(receipt) {
  const index = state.receipts.findIndex((item) => item.id === receipt.id);
  if (index >= 0) {
    state.receipts[index] = {
      ...receipt,
      imageData: state.receipts[index].imageData || receipt.imageData,
      ocr: state.receipts[index].ocr || receipt.ocr
    };
  } else {
    state.receipts.unshift(receipt);
  }
}

function upsertCreditRequest(request) {
  const index = state.creditRequests.findIndex((item) => item.id === request.id);
  if (index >= 0) {
    state.creditRequests[index] = { ...state.creditRequests[index], ...request };
  } else {
    state.creditRequests.unshift(request);
  }
}

function upsertRedemption(redemption) {
  const index = state.redemptions.findIndex((item) => item.id === redemption.id);
  if (index >= 0) {
    state.redemptions[index] = { ...state.redemptions[index], ...redemption };
  } else {
    state.redemptions.unshift(redemption);
  }
}

function getAllowedCustomerIdsForCurrentRole() {
  if (authRole !== "cliente") {
    return null;
  }

  return new Set(state.customers.map((customer) => customer.id));
}

function wireEvents() {
  el.authForm.addEventListener("submit", handleAuthSubmit);
  el.signupForm.addEventListener("submit", handleSignupSubmit);
  el.authLogout.addEventListener("click", handleAuthLogout);

  el.tabs.forEach((button) => {
    button.addEventListener("click", () => switchTab(button.dataset.tab));
  });

  el.customerForm.addEventListener("submit", handleCustomerSubmit);
  el.receiptForm.addEventListener("submit", handleReceiptSubmit);
  el.redemptionForm.addEventListener("submit", handleRedemptionSubmit);
  el.creditRequestForm.addEventListener("submit", handleCreditRequestSubmit);

  el.receiptForm.amount.addEventListener("input", updateReceiptCalculation);
  el.receiptForm.receiptImage.addEventListener("change", handleReceiptImageChange);
  el.rerunOcr.addEventListener("click", handleManualOcrRequest);
  el.openCamera.addEventListener("click", openGuidedCamera);
  el.captureReceipt.addEventListener("click", captureGuidedReceipt);
  el.closeCamera.addEventListener("click", closeGuidedCamera);
  el.customerSelect.addEventListener("change", renderCustomerDetail);
  el.creditRequestService.addEventListener("change", updateCreditRequestStatusText);
  el.creditRequestBeneficiaryType.addEventListener("change", syncCreditRequestBeneficiaryFields);
  el.redemptionCustomerSelect.addEventListener("change", updateRedemptionStatusText);
  el.redemptionForm.service.addEventListener("change", updateRedemptionStatusText);
  el.statusFilter.addEventListener("change", renderReceiptList);

  el.exportJson.addEventListener("click", exportJson);
  el.exportCsv.addEventListener("click", exportCsv);
  el.clearDemo.addEventListener("click", clearAllData);

  if (el.cassiereSearchBtn) el.cassiereSearchBtn.addEventListener("click", handleCassiereSearch);
  if (el.cassiereSearchInput) el.cassiereSearchInput.addEventListener("keydown", (e) => { if (e.key === "Enter") { e.preventDefault(); handleCassiereSearch(e); } });
  if (el.cassiereReceiptForm) el.cassiereReceiptForm.addEventListener("submit", handleCassiereReceiptSubmit);
  if (el.cassiereQuickRegisterForm) el.cassiereQuickRegisterForm.addEventListener("submit", handleCassiereQuickRegister);
  document.querySelectorAll(".cassiere-operatore-btn").forEach((btn) => {
    btn.addEventListener("click", () => setCassiereOperatore(btn.dataset.operatore));
  });
  const cambiaBtnOp = document.querySelector("#cassiereOperatoreCambia");
  if (cambiaBtnOp) cambiaBtnOp.addEventListener("click", () => { localStorage.removeItem("sq_operatore"); initCassiereOperatore(); });
  if (el.copyBarPaymentBtn) el.copyBarPaymentBtn.addEventListener("click", () => { if (lastRedemptionId) copyBarPaymentMessage(lastRedemptionId); });

  if (el.openCodiceBancoScan) el.openCodiceBancoScan.addEventListener("click", openCodiceBancoScanner);
  if (el.closeCodiceBancoScan) el.closeCodiceBancoScan.addEventListener("click", closeCodiceBancoScanner);
  if (el.attivaCodiceBtn) el.attivaCodiceBtn.addEventListener("click", handleAttivaCodiceBanco);
  if (el.donazioneSilenziosiForm) el.donazioneSilenziosiForm.addEventListener("submit", handleDonazioneSilenziosiSubmit);
  if (el.valutazioneBisogniForm) el.valutazioneBisogniForm.addEventListener("submit", handleValutazioneBisogniSubmit);
  if (el.erogazioneSilenziosiForm) el.erogazioneSilenziosiForm.addEventListener("submit", handleErogazioneSilenziosiSubmit);
  if (el.revisioneManualeList) el.revisioneManualeList.addEventListener("click", handleRevisioneManualeClick);
}

function setTodayDefaults() {
  const today = new Date();
  const date = today.toISOString().slice(0, 10);
  const time = today.toTimeString().slice(0, 5);
  el.receiptForm.receiptDate.value = date;
  el.receiptForm.receiptTime.value = time;
}

async function handleAuthSubmit(event) {
  event.preventDefault();

  if (!supabaseClient?.auth) {
    showToast("Supabase Auth non e' disponibile.");
    return;
  }

  const form = new FormData(event.currentTarget);
  const email = cleanText(form.get("email")).toLowerCase();
  const password = String(form.get("password") || "");

  if (!email || !password) {
    showToast("Inserisci email e password.");
    return;
  }

  setAuthMessage("Accesso in corso...", "loading");

  const { data, error } = await supabaseClient.auth.signInWithPassword({ email, password });
  if (error) {
    console.error("Errore login Supabase:", error);
    setAuthMessage(`Accesso non riuscito: ${error.message}`, "error");
    showToast("Accesso non riuscito.");
    return;
  }

  event.currentTarget.password.value = "";
  await setAuthState(data?.session || null);
  setAuthMessage(`Accesso completato. Ruolo: ${ROLE_LABELS[authRole] || "Accesso pubblico"}.`, "success");
  showToast("Accesso completato.");
}

async function handleSignupSubmit(event) {
  event.preventDefault();
  const formEl = event.currentTarget;

  if (!supabaseClient?.auth) {
    setSignupMessage("Supabase Auth non e' disponibile.", "error");
    showToast("Registrazione non disponibile.");
    return;
  }

  const form = new FormData(formEl);
  const firstName = cleanText(form.get("firstName"));
  const lastName = cleanText(form.get("lastName"));
  const phone = cleanText(form.get("phone"));
  const city = cleanText(form.get("city")) || "Francofonte";
  const email = cleanText(form.get("email")).toLowerCase();
  const password = String(form.get("password") || "");
  const passwordConfirm = String(form.get("passwordConfirm") || "");

  if (!firstName || !lastName || !phone || !email || !password) {
    setSignupMessage("Compila tutti i campi obbligatori.", "error");
    return;
  }

  if (password.length < 8) {
    setSignupMessage("La password deve avere almeno 8 caratteri.", "error");
    return;
  }

  if (password !== passwordConfirm) {
    setSignupMessage("Le due password non coincidono.", "error");
    return;
  }

  setSignupMessage("Creazione account in corso...", "loading");
  if (el.signupSubmit) el.signupSubmit.disabled = true;

  const metadata = {
    ruolo: "cliente",
    role: "cliente",
    nome: firstName,
    cognome: lastName,
    nome_completo: `${firstName} ${lastName}`,
    telefono: phone,
    citta: city
  };

  let data = null;
  let error = null;
  try {
    const result = await withTimeout(
      supabaseClient.auth.signUp({
        email,
        password,
        options: {
          data: metadata
        }
      }),
      AUTH_REQUEST_TIMEOUT_MS,
      "Supabase non ha risposto in tempo. Controlla la connessione e riprova."
    );
    data = result.data;
    error = result.error;
  } catch (signupError) {
    console.error("Errore o timeout registrazione Supabase:", signupError);
    setSignupMessage(`Registrazione non completata: ${signupError.message}`, "error");
    showToast("Registrazione non completata.");
    return;
  } finally {
    if (el.signupSubmit) el.signupSubmit.disabled = false;
  }

  if (error) {
    console.error("Errore registrazione Supabase:", error);
    setSignupMessage(`Registrazione non riuscita: ${error.message}`, "error");
    showToast("Registrazione non riuscita.");
    return;
  }

  formEl.reset();
  formEl.city.value = "Francofonte";

  if (data?.session) {
    await setAuthState(data.session);

    const phoneNorm = normalizePhone(phone);
    const clienteEsiste = state.customers.some((c) => normalizePhone(c.phone) === phoneNorm);
    if (!clienteEsiste && state.customers.length < MAX_PILOT_CUSTOMERS) {
      const nuovoCliente = {
        id: crypto.randomUUID(),
        code: generateCustomerCode(),
        firstName,
        lastName,
        phone,
        city,
        barName: BAR_NAME,
        createdAt: new Date().toISOString()
      };
      const risultato = await saveCustomerToSupabase(nuovoCliente);
      if (risultato.ok) {
        state.nextCustomerNumber += 1;
        upsertCustomer(nuovoCliente);
        saveState();
        await loadPilotCustomersFromSupabase();
      }
    }

    setSignupMessage("Account cliente creato. Accesso effettuato.", "success");
    setAuthMessage("Account cliente creato. Ora puoi usare la web app.", "success");
    showToast("Account cliente creato.");
    return;
  }

  setSignupMessage("Account creato. Se Supabase richiede conferma email, apri l'email ricevuta e poi fai login.", "success");
  setAuthMessage("Account creato. Dopo la conferma email, accedi con email e password.", "success");
  showToast("Account creato: controlla eventuale email di conferma.");
}

async function handleAuthLogout() {
  if (!supabaseClient?.auth) {
    return;
  }

  const { error } = await supabaseClient.auth.signOut();
  if (error) {
    console.error("Errore logout Supabase:", error);
    setAuthMessage(`Logout non riuscito: ${error.message}`, "error");
    return;
  }

  await setAuthState(null);
  setAuthMessage("Accesso pubblico attivo.", "success");
  showToast("Uscita completata.");
}

function setAuthMessage(message, status) {
  if (!el.authStatus) return;
  el.authStatus.textContent = message;
  if (status) {
    el.authStatus.dataset.status = status;
  } else {
    delete el.authStatus.dataset.status;
  }
}

function setSignupMessage(message, status) {
  if (!el.signupStatus) return;
  el.signupStatus.textContent = message;
  if (status) {
    el.signupStatus.dataset.status = status;
  } else {
    delete el.signupStatus.dataset.status;
  }
}

function withTimeout(promise, timeoutMs, timeoutMessage) {
  let timeoutId;
  const timeout = new Promise((_, reject) => {
    timeoutId = window.setTimeout(() => reject(new Error(timeoutMessage)), timeoutMs);
  });

  return Promise.race([promise, timeout]).finally(() => {
    window.clearTimeout(timeoutId);
  });
}

function prefillCustomerFormFromAuth() {
  if (!authSession?.user || authRole !== "cliente" || !el.customerForm) return;

  const metadata = authSession.user.user_metadata || {};
  const fields = el.customerForm.elements;
  if (fields.firstName && !fields.firstName.value) {
    fields.firstName.value = cleanText(metadata.nome || metadata.firstName);
  }
  if (fields.lastName && !fields.lastName.value) {
    fields.lastName.value = cleanText(metadata.cognome || metadata.lastName);
  }
  if (fields.phone && !fields.phone.value) {
    fields.phone.value = cleanText(metadata.telefono || metadata.phone);
  }
  if (fields.city && !fields.city.value) {
    fields.city.value = cleanText(metadata.citta || metadata.city) || "Francofonte";
  }
}

async function createCustomerProfileForUser(user) {
  if (!supabaseClient || !user) return null;

  const metadata = user.user_metadata || {};
  const firstName = cleanText(metadata.nome || metadata.firstName);
  const lastName = cleanText(metadata.cognome || metadata.lastName);
  const fullName = cleanText(metadata.nome_completo || `${firstName} ${lastName}`) || cleanText(user.email);

  const profile = {
    auth_user_id: user.id,
    ruolo: "cliente",
    nome_completo: fullName,
    telefono: cleanText(metadata.telefono || metadata.phone),
    email: cleanText(user.email),
    attivo: true
  };

  const { data, error } = await supabaseClient
    .from("profili")
    .insert(profile)
    .select("*")
    .maybeSingle();

  if (error) {
    console.warn("Profilo cliente non creato automaticamente:", error);
    return null;
  }

  return data || profile;
}

function loadState() {
  const raw = localStorage.getItem(STORAGE_KEY);
  if (!raw) return structuredClone(initialState);

  try {
    return { ...structuredClone(initialState), ...JSON.parse(raw) };
  } catch {
    return structuredClone(initialState);
  }
}

function saveState() {
  if (suppressLocalPersistence) {
    return true;
  }

  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
    return true;
  } catch (error) {
    console.error("Errore salvataggio locale:", error);
    showToast("Cliente salvato su Supabase, ma il browser non ha salvato i dati locali.");
    return false;
  }
}

function switchTab(tabId) {
  if (!requireAccess(tabId)) return;

  el.tabs.forEach((button) => {
    button.classList.toggle("is-active", button.dataset.tab === tabId);
  });
  el.panels.forEach((panel) => {
    panel.classList.toggle("is-active", panel.id === tabId);
  });
  if (tabId === "bar_report") initCassiereOperatore();
}

function initCassiereOperatore() {
  const saved = localStorage.getItem("sq_operatore");
  if (el.cassiereOperatorePanel) el.cassiereOperatorePanel.hidden = !!saved;
  if (el.cassiereOperatoreActive) el.cassiereOperatoreActive.hidden = !saved;
  if (el.cassiereOperatoreLabel && saved) el.cassiereOperatoreLabel.textContent = saved;
}

function setCassiereOperatore(label) {
  localStorage.setItem("sq_operatore", label);
  initCassiereOperatore();
}

function requireAccess(tabId) {
  if (canAccessTab(tabId)) return true;

  if (!authSession?.user) {
    showToast("Accedi con un account autorizzato per aprire questa sezione.");
    return false;
  }

  showToast("Questa sezione non e' disponibile per il tuo ruolo.");
  return false;
}

async function handleCustomerSubmit(event) {
  event.preventDefault();
  const customerForm = event.currentTarget;
  const form = new FormData(customerForm);
  const phone = cleanText(form.get("phone"));

  if (authRole === "cliente" && getCurrentCustomerIdForRole()) {
    showToast("La tua scheda cliente e' gia' presente.");
    return;
  }

  if (state.customers.length >= MAX_PILOT_CUSTOMERS) {
    showToast(`Limite pilot raggiunto: massimo ${MAX_PILOT_CUSTOMERS} clienti.`);
    return;
  }

  if (state.customers.some((customer) => customer.phone === phone)) {
    showToast("Telefono gia' registrato.");
    return;
  }

  const customer = {
    id: crypto.randomUUID(),
    code: generateCustomerCode(),
    firstName: cleanText(form.get("firstName")),
    lastName: cleanText(form.get("lastName")),
    phone,
    city: cleanText(form.get("city")),
    barName: BAR_NAME,
    createdAt: new Date().toISOString()
  };

  const supabaseResult = await saveCustomerToSupabase(customer);
  if (!supabaseResult.ok) {
    showToast(`Cliente non salvato su Supabase: ${supabaseResult.message}`);
    return;
  }

  if (supabaseResult.id) {
    customer.supabaseId = supabaseResult.id;
  }

  state.nextCustomerNumber += 1;
  upsertCustomer(customer);
  customerForm.reset();
  customerForm.city.value = "Francofonte";
  render();
  selectCustomerForCurrentFlow(customer.id);
  saveState();
  showToast(authRole === "cliente" ? "Profilo cliente salvato." : `Cliente registrato e selezionato: ${customer.code}`);
  loadPilotCustomersFromSupabase();
}

function selectCustomerForCurrentFlow(customerId) {
  if (!customerId) return;

  el.customerSelect.value = customerId;
  el.receiptCustomerSelect.value = customerId;
  el.redemptionCustomerSelect.value = customerId;
  renderCustomerDetail();
}

function generateCustomerCode() {
  const datePart = new Date().toISOString().slice(2, 10).replaceAll("-", "");
  const randomPart = crypto.randomUUID().slice(0, 4).toUpperCase();
  return `SQ${datePart}${randomPart}`;
}

async function saveCustomerToSupabase(customer) {
  if (!supabaseClient) {
    return { ok: true, id: null };
  }

  const { error } = await supabaseClient
    .from("clienti")
    .insert({
      id: customer.id,
      profilo_id: authProfile?.id || null,
      codice_cliente: customer.code,
      nome: customer.firstName,
      cognome: customer.lastName,
      telefono: customer.phone,
      email: authSession?.user?.email || null,
      citta: customer.city,
      consenso_programma: true,
      privacy_accettata_at: new Date().toISOString(),
      stato: "attivo"
    });

  if (error) {
    console.error("Errore salvataggio cliente Supabase:", error);
    return { ok: false, message: error.message };
  }

  return { ok: true, id: null };
}

async function handleReceiptSubmit(event) {
  event.preventDefault();
  try {
    await submitReceipt(event);
  } catch (error) {
    console.error("Errore imprevisto invio scontrino:", error);
    stopReceiptSubmit(`Errore imprevisto durante l'invio: ${error.message || "dettaglio non disponibile"}`);
  }
}

async function submitReceipt(event) {
  const receiptForm = event.currentTarget;
  setReceiptSubmitStatus("Controllo dati scontrino in corso.", "loading");

  if (!state.customers.length) {
    stopReceiptSubmit("Registra prima almeno un cliente.");
    return;
  }

  const form = new FormData(receiptForm);
  const selectedCustomerId = getCurrentCustomerIdForRole() || form.get("customerId");
  const amount = parseMoney(form.get("amount"));
  const imageFile = cameraReceiptFile || form.get("receiptImage");

  if (!selectedCustomerId || !getCustomer(selectedCustomerId)) {
    stopReceiptSubmit("Seleziona il cliente corretto prima di inviare lo scontrino.");
    return;
  }

  if (!form.get("receiptDate")) {
    stopReceiptSubmit("Inserisci la data dello scontrino.");
    return;
  }

  if (!form.get("receiptTime")) {
    stopReceiptSubmit("Inserisci l'ora dello scontrino.");
    return;
  }

  if (!cleanText(form.get("documentNumber"))) {
    stopReceiptSubmit("Inserisci il numero documento dello scontrino.");
    return;
  }

  if (!cleanText(form.get("matricolaRt"))) {
    stopReceiptSubmit("Inserisci la matricola del registratore telematico (la trovi sullo scontrino).");
    return;
  }

  if (!amount || amount <= 0) {
    stopReceiptSubmit("Inserisci un importo valido.");
    return;
  }

  if (!form.get("validConsumption")) {
    stopReceiptSubmit("Spunta la conferma che l'importo riguarda solo consumazioni valide del bar.");
    return;
  }

  if (!imageFile || !imageFile.size) {
    stopReceiptSubmit("Carica o scatta una foto dello scontrino.");
    return;
  }

  setReceiptSubmitStatus("Preparazione foto scontrino in corso.", "loading");
  const imageData = await readFileAsDataUrl(imageFile);

  const receipt = {
    id: crypto.randomUUID(),
    customerId: selectedCustomerId,
    barName: BAR_NAME,
    receiptDate: form.get("receiptDate"),
    receiptTime: form.get("receiptTime"),
    documentNumber: cleanText(form.get("documentNumber")),
    matricolaRt: cleanText(form.get("matricolaRt")),
    codiceBanco: cleanText(form.get("codiceBanco")),
    amount,
    credit: roundMoney(amount * CREDIT_RATE),
    status: "pending",
    note: "",
    ocr: currentOcrResult,
    imageData,
    createdAt: new Date().toISOString()
  };

  setReceiptSubmitStatus("Riepilogo dati pronto. Conferma per inviare.", "loading");
  if (!confirmReceiptData(receipt)) {
    stopReceiptSubmit("Invio annullato. Correggi i dati dello scontrino e riprova.");
    return;
  }

  const duplicate = findDuplicateReceipt(receipt);
  if (duplicate) {
    stopReceiptSubmit("Questo scontrino risulta gia' caricato: stessa data, numero documento e importo.");
    return;
  }

  const validation = validateReceiptAutomatically(receipt, duplicate);
  receipt.autoValidation = validation;
  receipt.status = "pending";
  receipt.note = validation.message;

  setReceiptSubmitStatus("Salvataggio foto per controllo in corso.", "loading");
  receipt.fotoPath = await uploadFotoScontrino(selectedCustomerId, receipt.id, imageFile);

  setReceiptSubmitStatus("Invio scontrino a Supabase in corso.", "loading");
  const supabaseResult = await saveReceiptToSupabase(receipt, duplicate, validation);
  if (!supabaseResult.ok) {
    stopReceiptSubmit(`Scontrino non salvato su Supabase: ${supabaseResult.message}`);
    return;
  }

  if (supabaseResult.autoApproved) {
    receipt.status = "confirmed";
    receipt.note = "Approvato automaticamente.";
  }
  state.receipts.unshift(receipt);
  saveState();
  receiptForm.reset();
  cameraReceiptFile = null;
  setTodayDefaults();
  resetOcrBox();
  updateReceiptCalculation();
  render();
  if (supabaseResult.autoApproved) {
    setReceiptSubmitStatus("Credito accreditato automaticamente.", "success");
    showToast("Credito accreditato.");
  } else if (supabaseResult.motivoSospensione === "codice_banco_mancante") {
    const scadenza = supabaseResult.sospesoScadutoIl
      ? new Date(supabaseResult.sospesoScadutoIl).toLocaleDateString("it-IT")
      : "";
    setReceiptSubmitStatus(
      `Scontrino inviato. Credito in sospeso: passa dal bar per attivarlo${scadenza ? ` entro il ${scadenza}` : ""}.`,
      "success"
    );
    showToast("Credito in sospeso: passa dal bar per attivarlo.");
  } else {
    setReceiptSubmitStatus("Scontrino inviato — in attesa di verifica SQ.", "success");
    showToast("Scontrino inviato. In attesa di verifica SQ.");
  }
  loadPilotReceiptsFromSupabase();
  loadPilotBalancesFromSupabase();
}

let codiceBancoScanStream = null;
let codiceBancoScanAnimFrame = null;

async function openCodiceBancoScanner() {
  if (!el.codiceBancoScanVideo || !el.codiceBancoScanCanvas) return;
  if (typeof jsQR === "undefined") {
    setCodiceBancoStatus("Libreria scanner QR non caricata. Digita il codice a mano.", "error");
    return;
  }

  try {
    codiceBancoScanStream = await navigator.mediaDevices.getUserMedia({
      video: { facingMode: "environment" }
    });
  } catch (err) {
    setCodiceBancoStatus("Impossibile accedere alla fotocamera. Digita il codice a mano.", "error");
    return;
  }

  el.codiceBancoScanVideo.srcObject = codiceBancoScanStream;
  el.codiceBancoScanPreview.hidden = false;
  el.openCodiceBancoScan.disabled = true;
  el.closeCodiceBancoScan.disabled = false;
  setCodiceBancoStatus("Inquadra il QR mostrato al banco.", "loading");

  await el.codiceBancoScanVideo.play();
  codiceBancoScanLoop();
}

function closeCodiceBancoScanner() {
  if (codiceBancoScanAnimFrame) {
    cancelAnimationFrame(codiceBancoScanAnimFrame);
    codiceBancoScanAnimFrame = null;
  }
  if (codiceBancoScanStream) {
    codiceBancoScanStream.getTracks().forEach((track) => track.stop());
    codiceBancoScanStream = null;
  }
  if (el.codiceBancoScanVideo) el.codiceBancoScanVideo.srcObject = null;
  if (el.codiceBancoScanPreview) el.codiceBancoScanPreview.hidden = true;
  if (el.openCodiceBancoScan) el.openCodiceBancoScan.disabled = false;
  if (el.closeCodiceBancoScan) el.closeCodiceBancoScan.disabled = true;
}

function codiceBancoScanLoop() {
  if (!codiceBancoScanStream || !el.codiceBancoScanVideo.videoWidth) {
    codiceBancoScanAnimFrame = requestAnimationFrame(codiceBancoScanLoop);
    return;
  }

  const canvas = el.codiceBancoScanCanvas;
  canvas.width = el.codiceBancoScanVideo.videoWidth;
  canvas.height = el.codiceBancoScanVideo.videoHeight;
  const ctx = canvas.getContext("2d");
  ctx.drawImage(el.codiceBancoScanVideo, 0, 0, canvas.width, canvas.height);
  const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
  const code = jsQR(imageData.data, canvas.width, canvas.height);

  if (code?.data && /^\d{6}$/.test(code.data.trim())) {
    if (el.codiceBancoInput) el.codiceBancoInput.value = code.data.trim();
    setCodiceBancoStatus("Codice letto dal QR del banco.", "success");
    closeCodiceBancoScanner();
    return;
  }

  codiceBancoScanAnimFrame = requestAnimationFrame(codiceBancoScanLoop);
}

function setCodiceBancoStatus(message, status) {
  if (!el.codiceBancoStatus) return;
  el.codiceBancoStatus.textContent = message;
  el.codiceBancoStatus.dataset.status = status;
}

async function handleAttivaCodiceBanco() {
  const scontrinoId = el.attivaCodiceBtn?.dataset.scontrinoId;
  const codice = cleanText(el.attivaCodiceInput?.value);

  if (!scontrinoId || !codice) {
    setAttivaCodiceStatus("Inserisci il codice mostrato al banco.", "error");
    return;
  }

  if (!supabaseClient) {
    setAttivaCodiceStatus("Database non collegato.", "error");
    return;
  }

  setAttivaCodiceStatus("Verifica in corso.", "loading");
  const { data, error } = await supabaseClient.rpc("attiva_scontrino_con_codice_banco_pilot", {
    p_scontrino_id: scontrinoId,
    p_codice: codice
  });

  if (error) {
    console.error("Errore attivazione codice banco:", error);
    setAttivaCodiceStatus(`Errore: ${error.message}`, "error");
    return;
  }

  if (!data?.ok) {
    const messaggi = {
      codice_non_valido: "Codice non valido: controlla che sia quello mostrato ora al banco.",
      scaduto: "Il periodo per attivare questo credito e' scaduto.",
      non_attivabile: "Questo scontrino non e' (piu') attivabile con un codice."
    };
    setAttivaCodiceStatus(messaggi[data?.errore] || "Attivazione non riuscita.", "error");
    return;
  }

  setAttivaCodiceStatus("Credito attivato. Ora e' spendibile.", "success");
  showToast("Credito attivato.");
  if (el.creditoSospesoArea) el.creditoSospesoArea.hidden = true;
  loadPilotReceiptsFromSupabase();
  loadPilotBalancesFromSupabase();
}

function setAttivaCodiceStatus(message, status) {
  if (!el.attivaCodiceStatus) return;
  el.attivaCodiceStatus.textContent = message;
  el.attivaCodiceStatus.dataset.status = status;
}

function aggiornaAreaCreditoSospeso() {
  if (!el.creditoSospesoArea) return;

  const customerId = getCurrentCustomerIdForRole();
  const sospeso = state.receipts.find((r) =>
    r.customerId === customerId &&
    r.status === "pending" &&
    r.motivoSospensione === "codice_banco_mancante"
  );

  if (!sospeso) {
    el.creditoSospesoArea.hidden = true;
    return;
  }

  el.creditoSospesoArea.hidden = false;
  el.creditoSospesoScadenza.textContent = sospeso.sospesoScadutoIl
    ? `scade il ${new Date(sospeso.sospesoScadutoIl).toLocaleDateString("it-IT")}`
    : "scadenza non disponibile";
  if (el.attivaCodiceBtn) el.attivaCodiceBtn.dataset.scontrinoId = sospeso.id;
}

function stopReceiptSubmit(message) {
  setReceiptSubmitStatus(message, "error");
  showToast(message);
}

function setReceiptSubmitStatus(message, status) {
  if (!el.receiptSubmitStatus) return;

  el.receiptSubmitStatus.textContent = message;
  el.receiptSubmitStatus.dataset.status = status;
}

function confirmReceiptData(receipt) {
  return window.confirm([
    "Controlla i dati dello scontrino prima di inviare:",
    "",
    `Data: ${receipt.receiptDate || "mancante"}`,
    `Ora: ${receipt.receiptTime || "mancante"}`,
    `Documento: ${receipt.documentNumber || "mancante"}`,
    `Matricola RT: ${receipt.matricolaRt || "mancante"}`,
    `Importo: ${formatMoney(receipt.amount)} euro`,
    `Credito SQ: ${formatMoney(receipt.credit)} euro`,
    "",
    "Se sono corretti, premi OK.",
    "Se sono sbagliati, premi Annulla e correggi i campi."
  ].join("\n"));
}

function validateReceiptAutomatically(receipt, duplicate) {
  const issues = [];
  const warnings = [];
  const ocrText = normalizeOcrText(receipt.ocr?.text || "");
  const confidence = Number(receipt.ocr?.confidence || 0);
  const amount = Number(receipt.amount || 0);
  const receiptDate = receipt.receiptDate ? new Date(`${receipt.receiptDate}T00:00:00`) : null;
  const today = new Date();
  today.setHours(0, 0, 0, 0);

  if (!receipt.receiptDate) issues.push("data scontrino mancante");
  if (!receipt.receiptTime) issues.push("ora scontrino mancante");
  if (!receipt.documentNumber) issues.push("numero documento mancante");
  if (!amount || amount <= 0) issues.push("importo non valido");

  if (receiptDate && receiptDate > today) {
    issues.push("data scontrino futura");
  }

  if (receiptDate) {
    const ageDays = Math.round((today - receiptDate) / (1000 * 60 * 60 * 24));
    if (ageDays > MAX_RECEIPT_AGE_DAYS) {
      issues.push(`scontrino piu' vecchio di ${MAX_RECEIPT_AGE_DAYS} giorni`);
    }
  }

  if (amount > AUTO_APPROVE_MAX_AMOUNT) {
    issues.push(`importo sopra soglia auto: ${formatMoney(AUTO_APPROVE_MAX_AMOUNT)} euro`);
  }

  if (duplicate) {
    issues.push("possibile duplicato");
  }

  if (!receipt.ocr?.text) {
    issues.push("testo OCR assente");
  } else if (confidence < MIN_OCR_CONFIDENCE) {
    issues.push(`confidenza OCR bassa: ${confidence}%`);
  }

  const excludedTerm = EXCLUDED_RECEIPT_TERMS.find((term) => ocrText.includes(term));
  if (excludedTerm) {
    issues.push(`termine escluso rilevato: ${excludedTerm}`);
  }

  const hasBarKeyword = BAR_VALIDATION_KEYWORDS.some((keyword) => ocrText.includes(keyword));
  if (!hasBarKeyword) {
    issues.push("esercizio non riconosciuto: scontrino non proviene da esercizio aderente al progetto");
  }

  const approved = issues.length === 0;
  const score = Math.max(0, 100 - (issues.length * 25) - (warnings.length * 8));

  return {
    approved,
    score,
    issues,
    warnings,
    status: approved ? "confermato" : "in_verifica",
    message: approved
      ? "Controlli automatici superati. Conferma finale richiesta a Salute Quotidiana."
      : `Verifica SQ richiesta: ${issues.join("; ")}.`
  };
}

async function uploadFotoScontrino(customerId, receiptId, file) {
  if (!supabaseClient || !file || !customerId || !receiptId) return null;

  const estensione = (file.type && file.type.split("/")[1]) || "jpg";
  const percorso = `${customerId}/${receiptId}.${estensione}`;

  const { error } = await supabaseClient.storage
    .from("foto-scontrini")
    .upload(percorso, file, { contentType: file.type || "image/jpeg", upsert: false });

  if (error) {
    console.error("Errore salvataggio foto scontrino:", error);
    return null;
  }

  return percorso;
}

async function vediFotoScontrino(fotoPath) {
  if (!fotoPath || !supabaseClient) {
    showToast("Foto non disponibile per questo scontrino.");
    return;
  }

  const { data, error } = await supabaseClient.storage
    .from("foto-scontrini")
    .createSignedUrl(fotoPath, 300);

  if (error || !data?.signedUrl) {
    console.error("Errore apertura foto scontrino:", error);
    showToast("Impossibile aprire la foto.");
    return;
  }

  window.open(data.signedUrl, "_blank");
}

async function saveReceiptToSupabase(receipt, duplicate, validation) {
  if (!supabaseClient) {
    return { ok: true };
  }

  if (!activeBar?.id) {
    return { ok: false, message: "bar pilota non trovato nel database" };
  }

  const { data, error } = await supabaseClient.rpc("registra_scontrino_pilot", {
    p_id: receipt.id,
    p_cliente_id: receipt.customerId,
    p_bar_id: activeBar.id,
    p_testo_ocr: receipt.ocr?.text || null,
    p_data_scontrino: receipt.receiptDate,
    p_ora_scontrino: receipt.receiptTime,
    p_numero_documento: receipt.documentNumber,
    p_importo_dichiarato: receipt.amount,
    p_importo_ocr: receipt.ocr?.fields?.amount || null,
    p_importo_verificato: null,
    p_credito_generato: receipt.credit,
    p_stato: "in_verifica",
    p_avviso_duplicato: Boolean(duplicate),
    p_motivo_controllo: validation.message,
    p_operatore_label: receipt.operatorLabel || null,
    p_matricola_rt: receipt.matricolaRt,
    p_codice_banco: receipt.codiceBanco || null,
    p_foto_path: receipt.fotoPath || null
  });

  if (error) {
    console.error("Errore salvataggio scontrino Supabase:", error);
    const messaggiErrore = {
      "scontrino duplicato: stessa matricola, numero documento, data e importo":
        "Questo scontrino risulta gia' caricato (stessa matricola, numero documento, data e importo).",
      "matricola registratore non riconosciuta per questo esercizio":
        "Matricola non riconosciuta: controlla di averla copiata correttamente dallo scontrino.",
      "data scontrino precedente all'avvio del programma":
        "La data dello scontrino e' precedente all'avvio del programma.",
      "tetto giornaliero di scontrini raggiunto per questo cliente":
        "Hai raggiunto il numero massimo di scontrini caricabili oggi. Riprova domani."
    };
    const messaggioLeggibile = messaggiErrore[error.message] || error.message;
    return { ok: false, message: messaggioLeggibile };
  }

  const { data: rigaInserita, error: erroreLettura } = await supabaseClient
    .from("scontrini_app_pilot")
    .select("stato,motivo_sospensione,sospeso_scaduto_il")
    .eq("id", data)
    .single();

  if (erroreLettura || !rigaInserita) {
    return { ok: true, id: data, autoApproved: false };
  }

  return {
    ok: true,
    id: data,
    autoApproved: rigaInserita.stato === "confermato",
    motivoSospensione: rigaInserita.motivo_sospensione,
    sospesoScadutoIl: rigaInserita.sospeso_scaduto_il
  };
}

async function handleReceiptImageChange() {
  const file = el.receiptForm.receiptImage.files[0];
  if (!file) {
    cameraReceiptFile = null;
    resetOcrBox();
    return;
  }

  cameraReceiptFile = null;
  await runReceiptOcr(file);
}

async function handleManualOcrRequest() {
  const file = el.receiptForm.receiptImage.files[0];
  if (!file) {
    showToast("Carica prima una foto dello scontrino.");
    return;
  }

  await runReceiptOcr(file);
}

async function openGuidedCamera() {
  if (!navigator.mediaDevices?.getUserMedia) {
    setCameraStatus("Fotocamera non disponibile in questo browser. Usa il caricamento foto normale.", "error");
    return;
  }

  closeGuidedCamera(false);
  setCameraStatus("Apertura fotocamera in corso.", "loading");

  try {
    cameraStream = await navigator.mediaDevices.getUserMedia({
      video: {
        facingMode: { ideal: "environment" },
        width: { ideal: 1920 },
        height: { ideal: 1080 }
      },
      audio: false
    });

    const [track] = cameraStream.getVideoTracks();
    await applyCameraFocus(track);

    el.cameraVideo.srcObject = cameraStream;
    el.cameraPreview.hidden = false;
    el.captureReceipt.disabled = false;
    el.closeCamera.disabled = false;
    el.openCamera.disabled = true;
    setCameraStatus("Inquadra tutto lo scontrino nella cornice. Attendi un secondo per la messa a fuoco, poi scatta.", "ready");
  } catch (error) {
    console.error("Errore apertura fotocamera:", error);
    setCameraStatus("Non riesco ad aprire la fotocamera. Controlla i permessi o usa il caricamento foto normale.", "error");
    closeGuidedCamera(false);
  }
}

async function applyCameraFocus(track) {
  if (!track?.getCapabilities || !track.applyConstraints) return;

  const capabilities = track.getCapabilities();
  const advanced = [];

  if (capabilities.focusMode?.includes("continuous")) {
    advanced.push({ focusMode: "continuous" });
  }

  if (capabilities.exposureMode?.includes("continuous")) {
    advanced.push({ exposureMode: "continuous" });
  }

  if (!advanced.length) return;

  try {
    await track.applyConstraints({ advanced });
  } catch (error) {
    console.info("Controllo focus non supportato dal dispositivo:", error);
  }
}

async function captureGuidedReceipt() {
  if (!cameraStream || !el.cameraVideo.videoWidth) {
    setCameraStatus("Fotocamera non pronta. Attendi un momento e riprova.", "error");
    return;
  }

  const canvas = el.cameraCanvas;
  const video = el.cameraVideo;
  const maxWidth = 1600;
  const scale = Math.min(1, maxWidth / video.videoWidth);
  canvas.width = Math.round(video.videoWidth * scale);
  canvas.height = Math.round(video.videoHeight * scale);

  const context = canvas.getContext("2d", { willReadFrequently: true });
  context.drawImage(video, 0, 0, canvas.width, canvas.height);

  const sharpness = scoreImageSharpness(context, canvas.width, canvas.height);
  if (sharpness < 5.5) {
    setCameraStatus("Foto probabilmente sfocata. Avvicina lo scontrino, tieni fermo il telefono e riprova.", "error");
    return;
  }

  const blob = await new Promise((resolve) => canvas.toBlob(resolve, "image/jpeg", 0.9));
  if (!blob) {
    setCameraStatus("Non riesco a creare la foto. Usa il caricamento foto normale.", "error");
    return;
  }

  cameraReceiptFile = new File([blob], `scontrino-${Date.now()}.jpg`, { type: "image/jpeg" });
  setReceiptImageFile(cameraReceiptFile);
  setCameraStatus(`Foto acquisita. Nitidezza: ${Math.round(sharpness)}. Avvio lettura OCR.`, "ready");
  closeGuidedCamera(false);
  await runReceiptOcr(cameraReceiptFile);
}

function scoreImageSharpness(context, width, height) {
  const sampleWidth = Math.min(320, width);
  const sampleHeight = Math.max(1, Math.round(height * (sampleWidth / width)));
  const sampleCanvas = document.createElement("canvas");
  sampleCanvas.width = sampleWidth;
  sampleCanvas.height = sampleHeight;
  const sampleContext = sampleCanvas.getContext("2d", { willReadFrequently: true });
  sampleContext.drawImage(context.canvas, 0, 0, sampleWidth, sampleHeight);

  const { data } = sampleContext.getImageData(0, 0, sampleWidth, sampleHeight);
  let totalDiff = 0;
  let count = 0;

  for (let y = 0; y < sampleHeight - 1; y += 1) {
    for (let x = 0; x < sampleWidth - 1; x += 1) {
      const i = (y * sampleWidth + x) * 4;
      const right = i + 4;
      const down = ((y + 1) * sampleWidth + x) * 4;
      const currentGray = (data[i] + data[i + 1] + data[i + 2]) / 3;
      const rightGray = (data[right] + data[right + 1] + data[right + 2]) / 3;
      const downGray = (data[down] + data[down + 1] + data[down + 2]) / 3;
      totalDiff += Math.abs(currentGray - rightGray) + Math.abs(currentGray - downGray);
      count += 2;
    }
  }

  return count ? totalDiff / count : 0;
}

function setReceiptImageFile(file) {
  try {
    const transfer = new DataTransfer();
    transfer.items.add(file);
    el.receiptForm.receiptImage.files = transfer.files;
  } catch (error) {
    console.info("Impostazione file input non supportata:", error);
  }
}

function closeGuidedCamera(resetStatus = true) {
  if (cameraStream) {
    cameraStream.getTracks().forEach((track) => track.stop());
    cameraStream = null;
  }

  if (el.cameraVideo) {
    el.cameraVideo.srcObject = null;
  }

  el.cameraPreview.hidden = true;
  el.captureReceipt.disabled = true;
  el.closeCamera.disabled = true;
  el.openCamera.disabled = false;

  if (resetStatus) {
    setCameraStatus("Fotocamera chiusa. Puoi riaprirla o usare il caricamento foto normale.", "idle");
  }
}

function setCameraStatus(message, status) {
  el.cameraStatus.textContent = message;
  el.cameraStatus.dataset.status = status;
}

async function runReceiptOcr(file) {
  currentOcrResult = null;

  if (!window.Tesseract) {
    setOcrStatus("OCR non disponibile: controlla la connessione internet e ricarica la pagina.", "error");
    return;
  }

  setOcrStatus("Lettura scontrino in corso. Attendi qualche secondo.", "loading");
  el.rerunOcr.disabled = true;

  try {
    const result = await Tesseract.recognize(file, "ita+eng", {
      logger: (progress) => {
        if (progress.status === "recognizing text") {
          const percent = Math.round((progress.progress || 0) * 100);
          setOcrStatus(`Lettura testo in corso: ${percent}%.`, "loading");
        }
      }
    });

    const text = result.data.text || "";
    const fields = extractReceiptFields(text);
    currentOcrResult = createOcrSnapshot(text, fields, result.data.confidence);
    applyOcrFields(fields);
    renderOcrResult(text, fields, currentOcrResult.confidence);
  } catch (error) {
    setOcrStatus("Non sono riuscito a leggere la foto. Inserisci i dati manualmente.", "error");
  } finally {
    el.rerunOcr.disabled = false;
  }
}

function extractReceiptFields(text) {
  const normalized = normalizeOcrText(text);
  return {
    receiptDate: extractReceiptDate(normalized),
    receiptTime: extractReceiptTime(normalized),
    documentNumber: extractDocumentNumber(normalized),
    amount: extractReceiptAmount(normalized)
  };
}

function applyOcrFields(fields) {
  if (fields.receiptDate) {
    el.receiptForm.receiptDate.value = fields.receiptDate;
  }

  if (fields.receiptTime) {
    el.receiptForm.receiptTime.value = fields.receiptTime;
  }

  if (fields.documentNumber) {
    el.receiptForm.documentNumber.value = fields.documentNumber;
  }

  if (fields.amount) {
    el.receiptForm.amount.value = fields.amount.toFixed(2);
    updateReceiptCalculation();
  }
}

function renderOcrResult(text, fields, confidence) {
  const found = [
    fields.receiptDate ? "data" : "",
    fields.receiptTime ? "ora" : "",
    fields.documentNumber ? "documento" : "",
    fields.amount ? "importo" : ""
  ].filter(Boolean);

  el.receiptOcrText.textContent = text.trim() || "Nessun testo leggibile.";
  el.receiptOcrDetails.open = false;

  if (!found.length) {
    setOcrStatus("Foto letta, ma non ho trovato dati sicuri. Compila i campi manualmente.", "warning");
    return;
  }

  const confidenceText = confidence ? ` Confidenza OCR: ${confidence}%.` : "";
  setOcrStatus(`Ho compilato: ${found.join(", ")}.${confidenceText} Controlla i dati prima di inviare.`, "success");
}

function resetOcrBox() {
  currentOcrResult = null;
  el.receiptOcrText.textContent = "";
  el.receiptOcrDetails.open = false;
  setOcrStatus("Carica una foto per provare a compilare automaticamente data, ora, documento e importo.", "");
}

function setOcrStatus(message, status) {
  el.receiptOcrStatus.textContent = message;
  el.receiptOcrStatus.dataset.status = status;
}

function createOcrSnapshot(text, fields, confidence) {
  return {
    text: text.trim(),
    fields: {
      receiptDate: fields.receiptDate || "",
      receiptTime: fields.receiptTime || "",
      documentNumber: fields.documentNumber || "",
      amount: fields.amount || 0
    },
    confidence: normalizeOcrConfidence(confidence),
    createdAt: new Date().toISOString()
  };
}

function normalizeOcrConfidence(confidence) {
  const value = Number(confidence);
  if (!Number.isFinite(value)) return 0;
  return Math.max(0, Math.min(100, Math.round(value)));
}

async function handleRedemptionSubmit(event) {
  event.preventDefault();

  if (!requireAccess("salute")) return;

  const form = new FormData(event.currentTarget);
  const customerId = form.get("customerId");
  const customer = getCustomer(customerId);

  if (!customer) {
    showToast("Seleziona un cliente valido.");
    return;
  }

  const service = form.get("service");
  const serviceConfig = services[service];
  const servicePrice = serviceConfig?.price || 0;
  const balance = getBalances(customerId).confirmed;
  const fieldCredit = parseMoney(form.get("creditUsed"));
  const creditUsed = roundMoney(Math.min(fieldCredit || balance, servicePrice));

  if (!serviceConfig) {
    setRedemptionMessage("Seleziona una prestazione valida.", "error");
    return;
  }

  if (!creditUsed || creditUsed <= 0) {
    setRedemptionMessage("Il cliente non ha credito SQ da scalare in questo utilizzo. Se vuoi erogare la prestazione senza credito, gestiscila fuori dal programma SQ.", "error");
    return;
  }

  if (balance > 0 && creditUsed > balance) {
    setRedemptionMessage(`Credito SQ insufficiente. Per questo cliente risultano disponibili ${formatMoney(balance)} euro SQ.`, "error");
    return;
  }

  if (creditUsed > servicePrice) {
    setRedemptionMessage(`Il credito SQ non puo' superare il prezzo della prestazione: ${formatMoney(servicePrice)} euro.`, "error");
    return;
  }

  const redemption = {
    id: crypto.randomUUID(),
    customerId,
    service,
    servicePrice,
    creditUsed: roundMoney(creditUsed),
    differenceDue: roundMoney(servicePrice - creditUsed),
    beneficiary: form.get("beneficiary"),
    beneficiaryNote: cleanText(form.get("beneficiaryNote")),
    createdAt: new Date().toISOString()
  };

  const supabaseResult = await saveRedemptionToSupabase(redemption);
  if (!supabaseResult.ok) {
    showToast(`Utilizzo credito non salvato su Supabase: ${supabaseResult.message}`);
    return;
  }

  const confermaCliente = !!form.get("confermaCliente");
  if (supabaseClient && supabaseResult.id) {
    await supabaseClient.rpc("conferma_prestazione_pilot", {
      p_id: supabaseResult.id,
      p_conferma_sq: true,
      p_conferma_cliente: confermaCliente
    });
  }

  upsertRedemption({ ...redemption, confirmSq: true, confirmCliente: confermaCliente, paymentStatus: "da_incassare" });
  saveState();
  event.currentTarget.reset();
  render();
  setRedemptionMessage("Utilizzo credito registrato. Il saldo cliente e' stato aggiornato.", "success");
  showToast("Utilizzo credito registrato.");

  lastRedemptionId = supabaseResult.id || redemption.id;
  const barMsg = buildWhatsAppMessageBar(customer, { ...redemption, id: lastRedemptionId });
  if (el.redemptionBarText) el.redemptionBarText.value = barMsg;
  if (el.redemptionMessageArea) el.redemptionMessageArea.hidden = false;

  loadPilotRedemptionsFromSupabase();
  loadPilotBalancesFromSupabase();
}

function updateRedemptionStatusText() {
  if (!el.redemptionStatus || !el.redemptionForm) return;

  const customerId = el.redemptionCustomerSelect?.value || "";
  const service = el.redemptionForm.service?.value || "";
  const servicePrice = services[service]?.price || 0;
  const balance = customerId ? getBalances(customerId).confirmed : 0;
  const preparedRequest = getPreparedRedemptionRequest();
  const preparedCredit = preparedRequest ? Number(preparedRequest.creditRequested || 0) : 0;
  const suggestedCredit = Math.min(balance > 0 ? balance : preparedCredit, servicePrice);
  const difference = Math.max(servicePrice - suggestedCredit, 0);

  if (!customerId || !servicePrice) {
    if (el.redemptionForm.creditUsed) {
      el.redemptionForm.creditUsed.value = "";
    }
    setRedemptionMessage("Seleziona cliente e prestazione: qui vedrai credito massimo utilizzabile e differenza stimata.", "");
    return;
  }

  if (el.redemptionForm.creditUsed) {
    el.redemptionForm.creditUsed.value = suggestedCredit > 0 ? suggestedCredit.toFixed(2) : "";
  }

  const source = preparedRequest && balance <= 0
    ? "credito indicato dalla richiesta"
    : "saldo SQ disponibile";
  setRedemptionMessage(`${source}: ${formatMoney(balance > 0 ? balance : preparedCredit)} euro. Credito SQ applicato: ${formatMoney(suggestedCredit)} euro. Differenza stimata da pagare: ${formatMoney(difference)} euro.`, "");
}

function setRedemptionMessage(message, status) {
  if (!el.redemptionStatus) return;
  el.redemptionStatus.textContent = message;
  if (status) {
    el.redemptionStatus.dataset.status = status;
  } else {
    delete el.redemptionStatus.dataset.status;
  }
}

async function saveRedemptionToSupabase(redemption) {
  if (!supabaseClient) {
    return { ok: true };
  }

  const { data, error } = await supabaseClient.rpc("registra_utilizzo_credito_pilot", {
    p_id: redemption.id,
    p_cliente_id: redemption.customerId,
    p_tipo_prestazione: redemption.service,
    p_prezzo_prestazione: redemption.servicePrice,
    p_credito_usato: redemption.creditUsed,
    p_importo_pagato: redemption.differenceDue,
    p_beneficiario: redemption.beneficiary,
    p_note: redemption.beneficiaryNote
  });

  if (error) {
    console.error("Errore salvataggio utilizzo credito Supabase:", error);
    return { ok: false, message: error.message };
  }

  return { ok: true, id: data };
}

async function handleCreditRequestSubmit(event) {
  event.preventDefault();

  if (authRole !== "cliente") {
    showToast("La richiesta credito e' disponibile solo per il cliente.");
    return;
  }

  const customerId = getCurrentCustomerIdForRole();
  if (!customerId) {
    setCreditRequestMessage("Prima completa il profilo cliente.", "error");
    return;
  }

  const form = new FormData(event.currentTarget);
  const service = cleanText(form.get("service"));
  const serviceConfig = services[service];
  const beneficiaryType = form.get("beneficiaryType") || "se";
  const beneficiaryName = cleanText(form.get("beneficiaryName"));
  const balance = getBalances(customerId).confirmed;
  const hasActiveRequest = state.creditRequests.some((request) => (
    request.customerId === customerId
    && ["inviata", "in_contatto", "confermata"].includes(request.status)
  ));

  if (hasActiveRequest) {
    setCreditRequestMessage("Hai gia' una richiesta attiva. Attendi il controllo di Salute Quotidiana.", "error");
    return;
  }

  if (!serviceConfig) {
    setCreditRequestMessage("Seleziona una prestazione valida.", "error");
    return;
  }

  if (balance <= 0) {
    setCreditRequestMessage("Serve almeno un credito SQ confermato per inviare una richiesta.", "error");
    return;
  }

  if (beneficiaryType === "altra_persona" && !beneficiaryName) {
    setCreditRequestMessage("Inserisci il nome del beneficiario.", "error");
    return;
  }

  if (!form.get("contactConsent")) {
    setCreditRequestMessage("Serve il consenso al contatto per inviare la richiesta.", "error");
    return;
  }

  const request = {
    id: crypto.randomUUID(),
    customerId,
    service,
    servicePrice: serviceConfig.price,
    creditRequested: roundMoney(Math.min(balance, serviceConfig.price)),
    beneficiaryType,
    beneficiaryName,
    beneficiaryPhone: cleanText(form.get("beneficiaryPhone")),
    preferredDate: form.get("preferredDate") || "",
    preferredTime: form.get("preferredTime") || "",
    contactConsent: true,
    note: cleanText(form.get("note")),
    status: "inviata",
    createdAt: new Date().toISOString()
  };

  setCreditRequestMessage("Invio richiesta in corso.", "loading");
  const supabaseResult = await saveCreditRequestToSupabase(request);
  if (!supabaseResult.ok) {
    setCreditRequestMessage(`Richiesta non inviata: ${supabaseResult.message}`, "error");
    return;
  }

  request.id = supabaseResult.id || request.id;
  upsertCreditRequest(request);
  saveState();
  event.currentTarget.reset();
  syncCreditRequestBeneficiaryFields();
  render();
  setCreditRequestMessage("Richiesta inviata. Salute Quotidiana ti ricontattera' dopo controllo.", "success");
  showToast("Richiesta utilizzo credito inviata.");
  loadCreditRequestsFromSupabase();
}

async function saveCreditRequestToSupabase(request) {
  if (!supabaseClient) {
    return { ok: true, id: request.id };
  }

  const { data, error } = await supabaseClient.rpc("crea_richiesta_utilizzo_credito_pilot", {
    p_cliente_id: request.customerId,
    p_prestazione: request.service,
    p_prezzo_prestazione: request.servicePrice,
    p_beneficiario_tipo: request.beneficiaryType,
    p_beneficiario_nome: request.beneficiaryName || null,
    p_beneficiario_telefono: request.beneficiaryPhone || null,
    p_giorno_preferito: request.preferredDate || null,
    p_fascia_oraria_preferita: request.preferredTime || null,
    p_consenso_contatto: request.contactConsent,
    p_note_cliente: request.note || null
  });

  if (error) {
    console.error("Errore richiesta utilizzo credito Supabase:", error);
    return { ok: false, message: error.message };
  }

  return { ok: true, id: data };
}

function setCreditRequestMessage(message, status) {
  if (!el.creditRequestStatus) return;
  el.creditRequestStatus.textContent = message;
  if (status) {
    el.creditRequestStatus.dataset.status = status;
  } else {
    delete el.creditRequestStatus.dataset.status;
  }
}

async function handleDonazioneSilenziosiSubmit(event) {
  event.preventDefault();

  const customerId = getCurrentCustomerIdForRole();
  if (!customerId) {
    setDonazioneSilenziosiMessage("Prima completa il profilo cliente.", "error");
    return;
  }

  const formEl = event.currentTarget;
  const form = new FormData(formEl);
  const importo = parseMoney(form.get("importo"));
  const balance = getBalances(customerId).confirmed;

  if (!importo || importo <= 0) {
    setDonazioneSilenziosiMessage("Inserisci un importo valido.", "error");
    return;
  }

  if (importo > balance) {
    setDonazioneSilenziosiMessage(`Puoi donare al massimo il tuo saldo disponibile: ${formatMoney(balance)} euro.`, "error");
    return;
  }

  if (!supabaseClient) {
    setDonazioneSilenziosiMessage("Database non collegato.", "error");
    return;
  }

  setDonazioneSilenziosiMessage("Donazione in corso.", "loading");
  const { error } = await supabaseClient.rpc("dona_a_lista_silenziosi_pilot", {
    p_cliente_id: customerId,
    p_importo: importo
  });

  if (error) {
    console.error("Errore donazione Lista Silenziosi:", error);
    setDonazioneSilenziosiMessage(`Donazione non riuscita: ${error.message}`, "error");
    return;
  }

  formEl.reset();
  setDonazioneSilenziosiMessage(`Grazie. Hai donato ${formatMoney(importo)} euro SQ alla Lista dei Silenziosi.`, "success");
  showToast("Donazione registrata. Grazie.");
  loadPilotBalancesFromSupabase();
}

function setDonazioneSilenziosiMessage(message, status) {
  if (!el.donazioneSilenziosiStatus) return;
  el.donazioneSilenziosiStatus.textContent = message;
  el.donazioneSilenziosiStatus.dataset.status = status;
}

async function handleValutazioneBisogniSubmit(event) {
  event.preventDefault();

  const customerId = getCurrentCustomerIdForRole();
  if (!customerId) {
    setValutazioneBisogniMessage("Prima completa il profilo cliente.", "error");
    return;
  }

  const formEl = event.currentTarget;
  const form = new FormData(formEl);
  const compilatoDa = form.get("compilatoDa");
  const risposte = {
    vive_solo: Number(form.get("q1")),
    difficolta_movimento: Number(form.get("q2")),
    rete_familiare_assente: Number(form.get("q3")),
    nessun_credito_recente: Number(form.get("q4")),
    reddito_insufficiente: Number(form.get("q5"))
  };
  const punteggio = Object.values(risposte).reduce((acc, v) => acc + v, 0);
  const consenso = !!form.get("consensoValutazione");

  if (!consenso) {
    setValutazioneBisogniMessage("Serve il consenso per inviare il questionario.", "error");
    return;
  }

  if (!supabaseClient) {
    setValutazioneBisogniMessage("Database non collegato.", "error");
    return;
  }

  setValutazioneBisogniMessage("Invio in corso.", "loading");
  const { error } = await supabaseClient.rpc("invia_valutazione_bisogno_pilot", {
    p_cliente_id: customerId,
    p_punteggio: punteggio,
    p_risposte: risposte,
    p_consenso: consenso,
    p_compilato_da: compilatoDa
  });

  if (error) {
    console.error("Errore invio valutazione bisogni:", error);
    setValutazioneBisogniMessage(`Invio non riuscito: ${error.message}`, "error");
    return;
  }

  formEl.reset();
  setValutazioneBisogniMessage("Richiesta inviata. Salute Quotidiana la considerera' per il fondo Lista dei Silenziosi.", "success");
  showToast("Questionario inviato.");
}

function setValutazioneBisogniMessage(message, status) {
  if (!el.valutazioneBisogniStatus) return;
  el.valutazioneBisogniStatus.textContent = message;
  el.valutazioneBisogniStatus.dataset.status = status;
}

async function handleErogazioneSilenziosiSubmit(event) {
  event.preventDefault();

  if (!requireAccess("salute")) return;

  const form = new FormData(event.currentTarget);
  const beneficiarioClienteId = form.get("beneficiarioClienteId");
  const tipoPrestazione = form.get("tipoPrestazione");
  const serviceConfig = services[tipoPrestazione];

  if (!beneficiarioClienteId || !serviceConfig) {
    setErogazioneSilenziosiMessage("Seleziona beneficiario e prestazione validi.", "error");
    return;
  }

  if (!supabaseClient) {
    setErogazioneSilenziosiMessage("Database non collegato.", "error");
    return;
  }

  setErogazioneSilenziosiMessage("Erogazione in corso.", "loading");
  const { data, error } = await supabaseClient.rpc("eroga_da_lista_silenziosi_pilot", {
    p_beneficiario_cliente_id: beneficiarioClienteId,
    p_tipo_prestazione: tipoPrestazione,
    p_prezzo_prestazione: serviceConfig.price,
    p_importo_pagato_extra: 0
  });

  if (error) {
    console.error("Errore erogazione Lista Silenziosi:", error);
    setErogazioneSilenziosiMessage(`Erogazione non riuscita: ${error.message}`, "error");
    return;
  }

  if (!data?.ok) {
    const messaggi = {
      beneficiario_non_ammesso: "Questo beneficiario non risulta piu' ammesso al fondo.",
      fondo_esaurito: "La quota disponibile per questo beneficiario e' esaurita."
    };
    setErogazioneSilenziosiMessage(messaggi[data?.errore] || "Erogazione non riuscita.", "error");
    return;
  }

  event.currentTarget.reset();
  setErogazioneSilenziosiMessage(
    `Erogati ${formatMoney(data.importo_erogato)} euro SQ dal fondo. Differenza da pagare: ${formatMoney(data.differenza_da_pagare)} euro.`,
    "success"
  );
  showToast("Prestazione erogata dal fondo Lista dei Silenziosi.");
  loadFondoSilenziosi();
}

function setErogazioneSilenziosiMessage(message, status) {
  if (!el.erogazioneSilenziosiStatus) return;
  el.erogazioneSilenziosiStatus.textContent = message;
  el.erogazioneSilenziosiStatus.dataset.status = status;
}

function findDuplicateReceipt(receipt) {
  const documentNumber = cleanText(receipt.documentNumber).toLowerCase();
  const amount = roundMoney(receipt.amount);

  return state.receipts.find((item) => (
    item.barName === receipt.barName &&
    item.receiptDate === receipt.receiptDate &&
    cleanText(item.documentNumber).toLowerCase() === documentNumber &&
    roundMoney(item.amount) === amount &&
    item.status !== "rejected"
  ));
}

function readFileAsDataUrl(file) {
  return new Promise((resolve, reject) => {
    if (!file || !file.size) {
      reject(new Error("foto scontrino mancante o vuota"));
      return;
    }

    const reader = new FileReader();
    reader.onload = () => resolve(reader.result);
    reader.onerror = () => reject(reader.error || new Error("foto non leggibile"));
    reader.readAsDataURL(file);
  });
}

function updateReceiptCalculation() {
  const amount = parseMoney(el.receiptForm.amount.value);
  const credit = amount ? roundMoney(amount * CREDIT_RATE) : 0;
  el.receiptCalculation.textContent = `Credito generato: ${formatMoney(credit)} euro SQ`;
}

function render() {
  renderAuthState();
  syncTabVisibility();
  syncCustomerRoleUi();
  renderCustomerOptions();
  renderCustomerDetail();
  renderReceiptList();
  renderBarReport();
  renderReport();
  renderRedemptionHistory();
  renderCreditRequestAlert();
  renderCreditRequestQueue();
  renderSaluteTabBadge();
  updateRedemptionStatusText();
  renderHeader();
  aggiornaAreaCreditoSospeso();
}

function renderAuthState() {
  if (!el.authStatus || !el.authRole || !el.authSubmit || !el.authLogout) {
    return;
  }

  const roleLabel = ROLE_LABELS[authRole] || ROLE_LABELS.guest;
  const email = authSession?.user?.email || "";

  el.authRole.textContent = roleLabel;
  el.authStatus.textContent = authSession
    ? `Connesso come ${email}. Ruolo attivo: ${roleLabel}.`
    : "Inserisci email e password per accedere alla web app.";
  el.authSubmit.textContent = authSession ? "Aggiorna accesso" : "Accedi";
  el.authLogout.disabled = !authSession;
}

function syncTabVisibility() {
  const allowedTabIds = getAllowedTabsForCurrentRole();
  const allowedTabs = new Set(allowedTabIds);
  let activeTab = null;

  if (!allowedTabIds.length) {
    if (el.appTabs) el.appTabs.hidden = true;
    if (el.appMain) el.appMain.hidden = true;
    el.tabs.forEach((button) => {
      button.hidden = true;
      button.classList.remove("is-active");
    });
    el.panels.forEach((panel) => {
      panel.hidden = true;
      panel.classList.remove("is-active");
    });
    return;
  }

  if (el.appTabs) el.appTabs.hidden = false;
  if (el.appMain) el.appMain.hidden = false;

  el.tabs.forEach((button) => {
    const visible = allowedTabs.has(button.dataset.tab);
    button.hidden = !visible;
    button.classList.toggle("is-active", visible && button.classList.contains("is-active"));
    if (visible && button.classList.contains("is-active")) {
      activeTab = button.dataset.tab;
    }
  });

  el.panels.forEach((panel) => {
    const visible = allowedTabs.has(panel.id);
    panel.classList.toggle("is-active", visible && panel.classList.contains("is-active"));
    panel.hidden = !visible;
    if (visible && panel.classList.contains("is-active")) {
      activeTab = panel.id;
    }
  });

  const currentActive = Array.from(el.tabs).find((button) => button.classList.contains("is-active") && !button.hidden);
  if (!currentActive) {
    const fallback = allowedTabIds[0];
    switchTab(fallback);
  } else if (!activeTab) {
    switchTab(currentActive.dataset.tab || "cliente");
  }
}

function getAllowedTabsForCurrentRole() {
  return ROLE_TAB_ACCESS[authRole] || ROLE_TAB_ACCESS.guest;
}

function canAccessTab(tabId) {
  return getAllowedTabsForCurrentRole().includes(tabId);
}

function renderHeader() {
  if (authRole === "bar" && state.barReport?.metrics) {
    const metrics = state.barReport.metrics;
    el.headerClients.textContent = `${metrics.customers} clienti collegati`;
    el.headerConfirmed.textContent = `${formatMoney(metrics.generatedCredit)} euro SQ generati`;
    return;
  }

  const confirmed = state.receipts
    .filter((receipt) => receipt.status === "confirmed")
    .reduce((sum, receipt) => sum + receipt.credit, 0);
  const used = state.redemptions.reduce((sum, item) => sum + item.creditUsed, 0);

  el.headerClients.textContent = `${state.customers.length} clienti`;
  el.headerConfirmed.textContent = `${formatMoney(Math.max(confirmed - used, 0))} euro SQ confermati`;
}

function renderCustomerOptions() {
  const forcedCustomerId = getCurrentCustomerIdForRole();
  const selectedCustomerId = forcedCustomerId || el.customerSelect.value;
  const selectedReceiptCustomerId = el.receiptCustomerSelect.value;
  const selectedRedemptionCustomerId = el.redemptionCustomerSelect.value;
  const options = state.customers.map((customer) => {
    return `<option value="${customer.id}">${customer.code} - ${escapeHtml(customer.firstName)} ${escapeHtml(customer.lastName)}</option>`;
  }).join("");

  const empty = `<option value="">Nessun cliente registrato</option>`;
  el.customerSelect.innerHTML = options || empty;
  el.receiptCustomerSelect.innerHTML = options || empty;
  el.redemptionCustomerSelect.innerHTML = options || empty;

  restoreSelectValue(el.customerSelect, selectedCustomerId);
  restoreSelectValue(el.receiptCustomerSelect, forcedCustomerId || selectedReceiptCustomerId || selectedCustomerId);
  restoreSelectValue(el.redemptionCustomerSelect, forcedCustomerId || selectedRedemptionCustomerId || selectedCustomerId);
}

function restoreSelectValue(select, value) {
  if (!value) return;
  const exists = Array.from(select.options || []).some((option) => option.value === value);
  if (exists) {
    select.value = value;
  }
}

function renderCustomerDetail() {
  const customerId = getCurrentCustomerIdForRole() || el.customerSelect.value || state.customers[0]?.id;
  if (customerId && el.customerSelect.value !== customerId) {
    el.customerSelect.value = customerId;
  }

  if (!customerId) {
    el.balanceCards.innerHTML = balanceMarkup(0, 0, 0);
    renderCreditRequestArea("", { confirmed: 0 });
    renderCustomerCreditRequests("");
    el.customerHistory.innerHTML = `<div class="empty">Nessun cliente registrato.</div>`;
    el.customerRedemptionHistory.innerHTML = "";
    return;
  }

  const balances = getBalances(customerId);
  el.balanceCards.innerHTML = balanceMarkup(balances.confirmed, balances.pending, balances.totalGenerated);
  renderCreditRequestArea(customerId, balances);
  renderCustomerCreditRequests(customerId);

  const history = state.receipts
    .filter((receipt) => receipt.customerId === customerId)
    .slice(0, 8)
    .map((receipt) => {
      return `
        <article class="history-card">
          <strong>${formatDate(receipt.receiptDate)} - ${formatMoney(receipt.amount)} euro</strong>
          <p>${formatMoney(receipt.credit)} euro SQ - ${statusLabel(receipt.status)}</p>
        </article>
      `;
    }).join("");

  el.customerHistory.innerHTML = history || `<div class="empty">Nessuno scontrino caricato per questo cliente.</div>`;

  const redemptions = state.redemptions
    .filter((item) => item.customerId === customerId)
    .slice(0, 8)
    .map((item) => {
      return `
        <article class="history-card">
          <strong>Utilizzo credito - ${formatDateTime(item.createdAt)}</strong>
          <p>${escapeHtml(item.service)}: ${formatMoney(item.creditUsed)} euro SQ usati, ${formatMoney(item.differenceDue)} euro da pagare.</p>
        </article>
      `;
    }).join("");

  el.customerRedemptionHistory.innerHTML = redemptions ? `
    <div class="history-title">Utilizzi credito</div>
    ${redemptions}
  ` : "";
}

function renderCreditRequestArea(customerId, balances) {
  if (!el.creditRequestArea || !el.creditRequestForm) return;

  if (authRole !== "cliente" || !customerId) {
    el.creditRequestArea.innerHTML = "";
    el.creditRequestForm.hidden = true;
    return;
  }

  const availableServices = getRequestableServices(balances.confirmed);
  const activeRequest = state.creditRequests.find((request) => (
    request.customerId === customerId
    && ["inviata", "in_contatto", "confermata"].includes(request.status)
  ));

  if (activeRequest) {
    el.creditRequestArea.innerHTML = `
      <article class="credit-request-card">
        <div>
          <span>Richiesta credito</span>
          <strong>Richiesta gia' presente: ${requestStatusLabel(activeRequest.status)}</strong>
          <p>Salute Quotidiana controllera' la richiesta e ti ricontattera'.</p>
        </div>
      </article>
    `;
    el.creditRequestForm.hidden = true;
    return;
  }

  if (!availableServices.length) {
    el.creditRequestArea.innerHTML = "";
    el.creditRequestForm.hidden = true;
    return;
  }

  el.creditRequestArea.innerHTML = `
    <article class="credit-request-card">
      <div>
        <span>Credito SQ disponibile</span>
        <strong>Puoi usare il credito come sconto su una prestazione</strong>
        <p>Se il credito non copre tutto il costo, potrai pagare la differenza. La richiesta non conferma automaticamente un appuntamento.</p>
      </div>
      <button type="button" class="primary" onclick="toggleCreditRequestForm()">Richiedi utilizzo credito</button>
    </article>
  `;

  renderCreditRequestServiceOptions(availableServices);
  syncCreditRequestBeneficiaryFields();
}

function renderRedemptionServiceOptions() {
  const select = el.redemptionForm?.service;
  if (!select) return;
  const current = select.value;
  select.innerHTML = Object.entries(services).map(([name, config]) => {
    const unavailable = config.available === false;
    const label = unavailable
      ? `${escapeHtml(name)} — ${formatMoney(config.price)} euro (non disponibile)`
      : `${escapeHtml(name)} — ${formatMoney(config.price)} euro`;
    return `<option value="${escapeHtml(name)}"${unavailable ? " disabled" : ""}>${label}</option>`;
  }).join("");
  if (current && Array.from(select.options).some(o => o.value === current)) {
    select.value = current;
  }
  updateRedemptionStatusText();
}

function renderCreditRequestServiceOptions(availableServices) {
  if (!el.creditRequestService) return;

  const currentValue = el.creditRequestService.value;
  el.creditRequestService.innerHTML = availableServices.map(([name, config]) => (
    `<option value="${escapeHtml(name)}">${escapeHtml(name)} - ${formatMoney(config.price)} euro SQ</option>`
  )).join("");

  restoreSelectValue(el.creditRequestService, currentValue);
  updateCreditRequestStatusText();
}

function getRequestableServices(confirmedBalance) {
  if (confirmedBalance <= 0) {
    return [];
  }

  return Object.entries(services).filter(([, config]) => config.available !== false);
}

function toggleCreditRequestForm() {
  if (!el.creditRequestForm) return;
  el.creditRequestForm.hidden = !el.creditRequestForm.hidden;
  if (!el.creditRequestForm.hidden) {
    updateCreditRequestStatusText();
  }
}

function updateCreditRequestStatusText() {
  const service = el.creditRequestService?.value;
  const price = services[service]?.price;
  const customerId = getCurrentCustomerIdForRole();
  const balance = customerId ? getBalances(customerId).confirmed : 0;
  const creditApplied = Math.min(balance, price || 0);
  const difference = Math.max((price || 0) - creditApplied, 0);

  if (!price) {
    setCreditRequestMessage("La richiesta sara' controllata e confermata da Salute Quotidiana.", "");
    return;
  }

  setCreditRequestMessage(`Costo: ${formatMoney(price)} euro. Credito SQ stimato: ${formatMoney(creditApplied)} euro. Differenza stimata: ${formatMoney(difference)} euro.`, "");
}

function syncCreditRequestBeneficiaryFields() {
  if (!el.creditRequestForm) return;
  const isOther = el.creditRequestBeneficiaryType?.value === "altra_persona";
  const beneficiaryName = el.creditRequestForm.elements.beneficiaryName;
  const beneficiaryPhone = el.creditRequestForm.elements.beneficiaryPhone;

  if (beneficiaryName) {
    beneficiaryName.required = isOther;
    beneficiaryName.closest("label").hidden = !isOther;
  }

  if (beneficiaryPhone) {
    beneficiaryPhone.closest("label").hidden = !isOther;
  }
}

function renderCustomerCreditRequests(customerId) {
  if (!el.customerCreditRequests) return;

  const requests = state.creditRequests
    .filter((request) => request.customerId === customerId)
    .slice(0, 5);

  if (!requests.length) {
    el.customerCreditRequests.innerHTML = "";
    if (el.customerCreditRequestsDetails) el.customerCreditRequestsDetails.open = false;
    return;
  }

  const haInAttesa = requests.some((request) => ["inviata", "in_contatto"].includes(request.status));
  if (el.customerCreditRequestsDetails) el.customerCreditRequestsDetails.open = haInAttesa;

  el.customerCreditRequests.innerHTML = `
    <div class="history-title">Richieste utilizzo credito</div>
    ${requests.map((request) => `
      <article class="history-card">
        <strong>${escapeHtml(request.service)} - ${requestStatusLabel(request.status)}</strong>
        <p>${formatMoney(request.creditRequested)} euro SQ richiesti, differenza stimata ${formatMoney(Math.max(request.servicePrice - request.creditRequested, 0))} euro${request.preferredDate ? `, giorno preferito ${formatDate(request.preferredDate)}` : ""}.</p>
      </article>
    `).join("")}
  `;
}

function syncCustomerRoleUi() {
  const isCustomer = authRole === "cliente";
  const hasCustomerRecord = isCustomer && Boolean(getCurrentCustomerIdForRole());
  const showCustomerCompletion = isCustomer && !pilotDataLoading && !hasCustomerRecord;
  const customerFormPanel = el.customerForm?.closest(".panel");
  const customerGrid = customerFormPanel?.parentElement;
  const customerSelectLabel = el.customerSelect?.closest("label");
  const receiptCustomerSelectLabel = el.receiptCustomerSelect?.closest("label");
  const customerFormTitle = customerFormPanel?.querySelector("h2");
  const customerFormEyebrow = customerFormPanel?.querySelector(".eyebrow");
  const customerFormButton = el.customerForm?.querySelector("button[type='submit']");

  if (customerFormPanel) {
    customerFormPanel.hidden = isCustomer ? !showCustomerCompletion : false;
  }

  if (customerFormTitle) {
    customerFormTitle.textContent = isCustomer ? "Completa il tuo profilo" : "Nuovo cliente SQ";
  }

  if (customerFormEyebrow) {
    customerFormEyebrow.textContent = isCustomer ? "Profilo cliente" : "Iscrizione";
  }

  if (customerFormButton) {
    customerFormButton.textContent = isCustomer ? "Salva il mio profilo" : "Registra cliente";
  }

  if (customerGrid?.classList) {
    customerGrid.classList.toggle("is-single", isCustomer && !showCustomerCompletion);
  }

  if (customerSelectLabel) {
    customerSelectLabel.hidden = isCustomer;
  }

  if (receiptCustomerSelectLabel) {
    receiptCustomerSelectLabel.hidden = isCustomer;
  }

  if (isCustomer && (pilotDataLoading || !hasCustomerRecord) && el.receiptForm) {
    el.receiptForm.querySelectorAll("input, select, button").forEach((field) => {
      if (!field.disabled) {
        field.dataset.disabledByMissingCustomer = "true";
      }
      field.disabled = true;
    });
    if (el.receiptSubmitStatus) {
      el.receiptSubmitStatus.textContent = pilotDataLoading
        ? "Sto caricando il tuo profilo cliente da Supabase."
        : "Prima serve una scheda cliente collegata al tuo account. Se sei gia' registrato, il record clienti probabilmente non e' collegato al tuo profilo Supabase.";
      el.receiptSubmitStatus.dataset.status = pilotDataLoading ? "loading" : "error";
    }
  } else if (el.receiptForm) {
    el.receiptForm.querySelectorAll("input, select, button").forEach((field) => {
      if (field.dataset.disabledByMissingCustomer === "true") {
        field.disabled = false;
        delete field.dataset.disabledByMissingCustomer;
      }
    });
  }
}

function getCurrentCustomerIdForRole() {
  if (authRole !== "cliente") {
    return "";
  }

  if (state.customers.length === 1) {
    return state.customers[0].id;
  }

  const matchingCustomer = state.customers.find((customer) => customerMatchesAuthenticatedUser(customer));
  return matchingCustomer?.id || "";
}

function balanceMarkup(confirmed, pending, totalGenerated) {
  return `
    <article>
      <span>Confermato</span>
      <strong>${formatMoney(confirmed)} euro SQ</strong>
    </article>
    <article>
      <span>In verifica</span>
      <strong>${formatMoney(pending)} euro SQ</strong>
    </article>
    <article>
      <span>Totale storico</span>
      <strong>${formatMoney(totalGenerated)} euro SQ</strong>
    </article>
  `;
}

function renderReceiptList() {
  const filter = el.statusFilter.value;
  const receipts = state.receipts.filter((receipt) => filter === "all" || receipt.status === filter);
  const canModerate = canAccessTab("salute");

  if (!receipts.length) {
    el.receiptList.innerHTML = `<div class="empty">Nessuno scontrino da mostrare.</div>`;
    return;
  }

  el.receiptList.innerHTML = receipts.map((receipt) => {
    const customer = getCustomer(receipt.customerId);
    const imageMarkup = receipt.imageData
      ? `<img src="${receipt.imageData}" alt="Foto scontrino">`
      : receipt.fotoPath
        ? `<button type="button" class="secondary" onclick="vediFotoScontrino('${receipt.fotoPath}')">Vedi foto scontrino</button>`
        : `<div class="receipt-image-placeholder">Nessuna foto salvata per questo scontrino.</div>`;

    return `
      <article class="receipt-card" data-id="${receipt.id}">
        <div class="receipt-card__head">
          <div>
            <strong>${customer ? `${escapeHtml(customer.code)} - ${escapeHtml(customer.firstName)} ${escapeHtml(customer.lastName)}` : "Cliente non trovato"}</strong>
            <p>${formatDate(receipt.receiptDate)} ${escapeHtml(receipt.receiptTime)} - Doc. ${escapeHtml(receipt.documentNumber)}</p>
          </div>
          <span class="status-pill status-${receipt.status}">${statusLabel(receipt.status)}</span>
        </div>
        ${imageMarkup}
        <div class="receipt-card__meta">
          <span>Importo: <strong>${formatMoney(receipt.amount)} euro</strong></span>
          <span>Credito: <strong>${formatMoney(receipt.credit)} euro SQ</strong></span>
        </div>
        ${receipt.note ? `<p class="status-pill status-pending">${escapeHtml(receipt.note)}</p>` : ""}
        ${ocrSummaryMarkup(receipt.ocr)}
        ${canModerate ? `
          <div class="receipt-card__actions">
            <button type="button" class="primary" onclick="confirmReceipt('${receipt.id}')">Conferma</button>
            <button type="button" class="secondary" onclick="correctReceipt('${receipt.id}')">Correggi</button>
            <button type="button" class="secondary" onclick="rejectReceipt('${receipt.id}')">Rifiuta</button>
          </div>
        ` : ""}
      </article>
    `;
  }).join("");
}

function renderBarReport() {
  if (!el.barReportMetrics || !el.barReportReceipts) {
    return;
  }

  if (!canAccessTab("bar_report")) {
    el.barReportMetrics.innerHTML = "";
    el.barReportReceipts.innerHTML = "";
    return;
  }

  const report = state.barReport;
  if (!report) {
    el.barReportMetrics.innerHTML = `
      <article>
        <span>Report bar</span>
        <strong>In attesa</strong>
      </article>
    `;
    el.barReportReceipts.innerHTML = `<div class="empty">Accedi come titolare bar collegato al bar pilota per vedere il riepilogo.</div>`;
    return;
  }

  const metrics = report.metrics || {};
  const metricRows = [
    ["Clienti collegati", metrics.customers],
    ["Scontrini caricati", metrics.receipts],
    ["In verifica", metrics.pending],
    ["Confermati", metrics.confirmed],
    ["Rifiutati", metrics.rejected],
    ["Consumazioni confermate", `${formatMoney(metrics.confirmedAmount)} euro`],
    ["Credito generato", `${formatMoney(metrics.generatedCredit)} euro SQ`],
    ["Anomalie", metrics.anomalies]
  ];

  el.barReportMetrics.innerHTML = metricRows.map(([label, value]) => `
    <article>
      <span>${label}</span>
      <strong>${value}</strong>
    </article>
  `).join("");

  const receipts = report.receipts || [];
  if (!receipts.length) {
    el.barReportReceipts.innerHTML = `<div class="empty">Nessuno scontrino del bar da mostrare.</div>`;
    return;
  }

  el.barReportReceipts.innerHTML = receipts.map((receipt) => `
    <article class="bar-receipt-row">
      <div>
        <strong>${escapeHtml(receipt.code || "Cliente")}</strong>
        <p>${formatDate(receipt.date)} ${escapeHtml(String(receipt.time || "").slice(0, 5))} - Doc. ${escapeHtml(receipt.documentNumber || "-")}</p>
      </div>
      <div class="bar-receipt-row__amount">
        <span>${formatMoney(receipt.amount)} euro</span>
        <span>${formatMoney(receipt.credit)} euro SQ</span>
      </div>
      <span class="status-pill status-${receipt.status}">${statusLabel(receipt.status)}</span>
      ${receipt.duplicate ? `<span class="status-pill status-pending">Possibile duplicato</span>` : ""}
    </article>
  `).join("");
}

async function confirmReceipt(id) {
  if (!requireAccess("salute")) return;

  const receipt = getReceipt(id);
  if (!receipt) return;

  const supabaseResult = await updateReceiptReviewOnSupabase({
    id,
    status: "confermato",
    amount: receipt.amount,
    credit: receipt.credit,
    note: null
  });
  if (!supabaseResult.ok) {
    showToast(`Scontrino non aggiornato su Supabase: ${supabaseResult.message}`);
    return;
  }

  receipt.status = "confirmed";
  receipt.note = "";
  receipt.verifiedByRole = "salute_quotidiana";
  receipt.verifiedAt = new Date().toISOString();
  saveState();
  render();
  showToast("Scontrino confermato su Supabase.");
  loadPilotReceiptsFromSupabase();
  loadPilotBalancesFromSupabase();
}

async function rejectReceipt(id) {
  if (!requireAccess("salute")) return;

  const receipt = getReceipt(id);
  if (!receipt) return;
  const reason = prompt("Motivo rifiuto:", receipt.note || "Scontrino non valido.");
  if (reason === null) return;

  const note = cleanText(reason);
  const supabaseResult = await updateReceiptReviewOnSupabase({
    id,
    status: "rifiutato",
    amount: receipt.amount,
    credit: 0,
    note
  });
  if (!supabaseResult.ok) {
    showToast(`Scontrino non aggiornato su Supabase: ${supabaseResult.message}`);
    return;
  }

  receipt.status = "rejected";
  receipt.note = note;
  receipt.credit = 0;
  receipt.verifiedByRole = "salute_quotidiana";
  receipt.verifiedAt = new Date().toISOString();
  saveState();
  render();
  showToast("Scontrino rifiutato su Supabase.");
  loadPilotReceiptsFromSupabase();
  loadPilotBalancesFromSupabase();
}

async function correctReceipt(id) {
  if (!requireAccess("salute")) return;

  const receipt = getReceipt(id);
  if (!receipt) return;
  const value = prompt("Nuovo importo valido:", String(receipt.amount).replace(".", ","));
  if (value === null) return;
  const amount = parseMoney(value);
  if (!amount || amount <= 0) {
    showToast("Importo non valido.");
    return;
  }

  const credit = roundMoney(amount * CREDIT_RATE);
  const note = "Importo corretto da Verifica SQ, da confermare.";
  const supabaseResult = await updateReceiptReviewOnSupabase({
    id,
    status: "in_verifica",
    amount,
    credit,
    note
  });
  if (!supabaseResult.ok) {
    showToast(`Scontrino non aggiornato su Supabase: ${supabaseResult.message}`);
    return;
  }

  receipt.amount = amount;
  receipt.credit = credit;
  receipt.status = "pending";
  receipt.note = note;
  receipt.verifiedByRole = "salute_quotidiana";
  receipt.verifiedAt = new Date().toISOString();
  saveState();
  render();
  showToast("Importo corretto su Supabase.");
  loadPilotReceiptsFromSupabase();
  loadPilotBalancesFromSupabase();
}

async function updateReceiptReviewOnSupabase({ id, status, amount, credit, note }) {
  if (!supabaseClient) {
    return { ok: true };
  }

  const { data, error } = await supabaseClient.rpc("aggiorna_scontrino_pilot", {
    p_id: id,
    p_stato: status,
    p_importo_dichiarato: amount,
    p_importo_verificato: status === "confermato" ? amount : null,
    p_credito_generato: credit,
    p_motivo_controllo: note
  });

  if (error) {
    console.error("Errore aggiornamento scontrino Supabase:", error);
    return { ok: false, message: error.message };
  }

  return { ok: true, id: data };
}

function renderReport() {
  if (!canAccessTab("report")) {
    el.reportMetrics.innerHTML = `<div class="empty">Accesso riservato a Salute Quotidiana e Admin.</div>`;
    return;
  }

  const confirmedReceipts = state.receipts.filter((receipt) => receipt.status === "confirmed");
  const pendingReceipts = state.receipts.filter((receipt) => receipt.status === "pending");
  const rejectedReceipts = state.receipts.filter((receipt) => receipt.status === "rejected");
  const totalAmount = confirmedReceipts.reduce((sum, receipt) => sum + receipt.amount, 0);
  const totalCredit = confirmedReceipts.reduce((sum, receipt) => sum + receipt.credit, 0);
  const totalUsed = state.redemptions.reduce((sum, item) => sum + item.creditUsed, 0);

  const metrics = [
    ["Clienti iscritti", state.customers.length],
    ["Scontrini caricati", state.receipts.length],
    ["Scontrini confermati", confirmedReceipts.length],
    ["Scontrini in verifica", pendingReceipts.length],
    ["Scontrini rifiutati", rejectedReceipts.length],
    ["Consumazioni confermate", `${formatMoney(totalAmount)} euro`],
    ["Credito generato", `${formatMoney(totalCredit)} euro SQ`],
    ["Credito usato", `${formatMoney(totalUsed)} euro SQ`],
    ["Saldo utilizzabile", `${formatMoney(Math.max(totalCredit - totalUsed, 0))} euro SQ`]
  ];

  el.reportMetrics.innerHTML = metrics.map(([label, value]) => `
    <article>
      <span>${label}</span>
      <strong>${value}</strong>
    </article>
  `).join("");
}

function renderRedemptionHistory() {
  if (!state.redemptions.length) {
    el.redemptionHistory.innerHTML = `<div class="empty">Nessun utilizzo credito registrato.</div>`;
    return;
  }

  el.redemptionHistory.innerHTML = state.redemptions.slice(0, 10).map((item) => {
    const customer = getCustomer(item.customerId);
    const isPaid = item.paymentStatus === "incassato";
    const paymentBadge = isPaid
      ? `<span class="status-pill status-green">Incassato</span>`
      : `<span class="status-pill status-yellow">Da incassare</span>`;
    const actionsBtns = !isPaid ? `
      <button type="button" class="secondary small" onclick="copyBarPaymentMessage('${item.id}')">Copia msg bar</button>
      <button type="button" class="secondary small" onclick="markPaymentReceived('${item.id}')">Segna incassato</button>
    ` : "";
    return `
      <article class="history-card">
        <div class="receipt-card__head">
          <strong>${customer ? `${escapeHtml(customer.code)} - ${escapeHtml(customer.firstName)} ${escapeHtml(customer.lastName)}` : "Cliente"}</strong>
          ${paymentBadge}
        </div>
        <p>${escapeHtml(item.service)}: usati ${formatMoney(item.creditUsed)} euro SQ, differenza ${formatMoney(item.differenceDue)} euro.</p>
        <p>Beneficiario: ${escapeHtml(item.beneficiary)} ${item.beneficiaryNote ? `- ${escapeHtml(item.beneficiaryNote)}` : ""}</p>
        ${actionsBtns ? `<div class="receipt-card__actions">${actionsBtns}</div>` : ""}
      </article>
    `;
  }).join("");
}

function renderCreditRequestQueue() {
  if (!el.creditRequestQueue) return;

  if (!canAccessTab("salute")) {
    el.creditRequestQueue.innerHTML = "";
    return;
  }

  if (!state.creditRequests.length) {
    el.creditRequestQueue.innerHTML = `<div class="empty">Nessuna richiesta utilizzo credito da gestire.</div>`;
    if (el.richiesteCreditoDetails) el.richiesteCreditoDetails.open = false;
    return;
  }

  if (el.richiesteCreditoDetails) el.richiesteCreditoDetails.open = true;

  el.creditRequestQueue.innerHTML = state.creditRequests.slice(0, 20).map((request) => {
    const customer = getCustomer(request.customerId);
    const customerLabel = customer
      ? `${escapeHtml(customer.code)} - ${escapeHtml(customer.firstName)} ${escapeHtml(customer.lastName)}`
      : escapeHtml(request.customerName || request.customerCode || "Cliente");
    const beneficiary = request.beneficiaryType === "altra_persona"
      ? `${escapeHtml(request.beneficiaryName || "Altra persona")}${request.beneficiaryPhone ? ` - ${escapeHtml(request.beneficiaryPhone)}` : ""}`
      : "Cliente stesso";

    return `
      <article class="history-card credit-request-row">
        <div class="receipt-card__head">
          <div>
            <strong>${customerLabel}</strong>
        <p>${escapeHtml(request.service)} - ${formatMoney(request.creditRequested)} euro SQ richiesti, differenza stimata ${formatMoney(Math.max(request.servicePrice - request.creditRequested, 0))} euro</p>
          </div>
          <span class="status-pill status-${requestStatusTone(request.status)}">${requestStatusLabel(request.status)}</span>
        </div>
        <p>Beneficiario: ${beneficiary}</p>
        <p>Preferenza: ${request.preferredDate ? formatDate(request.preferredDate) : "giorno da concordare"}${request.preferredTime ? `, ${escapeHtml(request.preferredTime)}` : ""}</p>
        ${request.note ? `<p>Nota cliente: ${escapeHtml(request.note)}</p>` : ""}
        ${request.internalNote ? `<p>Nota SQ: ${escapeHtml(request.internalNote)}</p>` : ""}
        <div class="receipt-card__actions">
          <button type="button" class="secondary" onclick="updateCreditRequestStatus('${request.id}', 'in_contatto')">Prendi in carico</button>
          <button type="button" class="primary" onclick="prepareRedemptionFromRequest('${request.id}')">Prepara utilizzo</button>
          <button type="button" class="secondary" onclick="updateCreditRequestStatus('${request.id}', 'rifiutata')">Rifiuta</button>
          <button type="button" class="secondary" onclick="updateCreditRequestStatus('${request.id}', 'annullata')">Annulla</button>
        </div>
      </article>
    `;
  }).join("");
}

function prepareRedemptionFromRequest(id) {
  if (!requireAccess("salute")) return;

  const request = state.creditRequests.find((item) => item.id === id);
  if (!request || !el.redemptionForm) return;

  const balance = getBalances(request.customerId).confirmed;
  const requestCredit = Number(request.creditRequested || 0);
  const availableCredit = balance > 0 ? Math.min(balance, requestCredit || request.servicePrice) : requestCredit;
  const creditToUse = Math.min(availableCredit, request.servicePrice);

  restoreSelectValue(el.redemptionCustomerSelect, request.customerId);
  el.redemptionForm.dataset.preparedRequestId = request.id;
  el.redemptionForm.service.value = request.service;
  el.redemptionForm.creditUsed.value = creditToUse ? creditToUse.toFixed(2) : "";
  el.redemptionForm.beneficiary.value = request.beneficiaryType === "altra_persona" ? "familiare" : "se";
  el.redemptionForm.beneficiaryNote.value = request.beneficiaryType === "altra_persona"
    ? cleanText(`${request.beneficiaryName || ""} ${request.beneficiaryPhone ? `- ${request.beneficiaryPhone}` : ""}`)
    : "";

  updateRedemptionStatusText();
  el.redemptionForm.scrollIntoView({ behavior: "smooth", block: "start" });
  showToast("Form utilizzo preparato. Controlla i dati e registra solo se la prestazione e' da applicare.");
}

function getPreparedRedemptionRequest() {
  const preparedRequestId = el.redemptionForm?.dataset?.preparedRequestId || "";
  if (!preparedRequestId) return null;
  return state.creditRequests.find((request) => request.id === preparedRequestId) || null;
}

function getOpenCreditRequests() {
  return state.creditRequests.filter((request) => ["inviata", "in_contatto"].includes(request.status));
}

function renderCreditRequestAlert() {
  if (!el.creditRequestAlert) return;

  if (!canAccessTab("salute")) {
    el.creditRequestAlert.innerHTML = "";
    el.creditRequestAlert.hidden = true;
    return;
  }

  const openRequests = getOpenCreditRequests();
  el.creditRequestAlert.hidden = false;

  if (!openRequests.length) {
    el.creditRequestAlert.className = "request-alert request-alert--empty";
    el.creditRequestAlert.innerHTML = `
      <strong>Nessuna nuova richiesta credito</strong>
      <span>Le richieste inviate dai clienti compariranno qui sopra il form di registrazione prestazione.</span>
    `;
    return;
  }

  el.creditRequestAlert.className = "request-alert request-alert--active";
  el.creditRequestAlert.innerHTML = `
    <strong>${openRequests.length} richiesta${openRequests.length === 1 ? "" : "e"} credito da gestire</strong>
    <span>Controlla la coda richieste prima di registrare eventuali utilizzi credito.</span>
  `;
}

function renderSaluteTabBadge() {
  const saluteTab = Array.from(el.tabs || []).find((button) => button.dataset.tab === "salute");
  if (!saluteTab) return;

  const count = canAccessTab("salute") ? getOpenCreditRequests().length : 0;
  saluteTab.textContent = count ? `Salute Quotidiana (${count})` : "Salute Quotidiana";
}

async function updateCreditRequestStatus(id, status) {
  if (!requireAccess("salute")) return;

  const request = state.creditRequests.find((item) => item.id === id);
  if (!request) return;

  const note = prompt("Nota interna Salute Quotidiana:", request.internalNote || "");
  if (note === null) return;

  const result = await updateCreditRequestStatusOnSupabase(id, status, cleanText(note));
  if (!result.ok) {
    showToast(`Richiesta non aggiornata: ${result.message}`);
    return;
  }

  request.status = status;
  request.internalNote = cleanText(note);
  request.updatedAt = new Date().toISOString();
  saveState();
  render();
  showToast(`Richiesta aggiornata: ${requestStatusLabel(status)}.`);
  loadCreditRequestsFromSupabase();
}

async function updateCreditRequestStatusOnSupabase(id, status, note) {
  if (!supabaseClient) {
    return { ok: true };
  }

  const { data, error } = await supabaseClient.rpc("aggiorna_richiesta_utilizzo_credito_pilot", {
    p_id: id,
    p_stato: status,
    p_note_interne_sq: note || null
  });

  if (error) {
    console.error("Errore aggiornamento richiesta credito Supabase:", error);
    return { ok: false, message: error.message };
  }

  return { ok: true, id: data };
}

function ocrSummaryMarkup(ocr) {
  if (!ocr || !ocr.text) return "";

  const fields = ocr.fields || {};

  return `
    <details class="ocr-snapshot">
      <summary>OCR salvato dalla foto</summary>
      <div class="ocr-snapshot__grid">
        <span>Confidenza: <strong>${Number(ocr.confidence) || 0}%</strong></span>
        <span>Data OCR: <strong>${escapeHtml(fields.receiptDate || "-")}</strong></span>
        <span>Ora OCR: <strong>${escapeHtml(fields.receiptTime || "-")}</strong></span>
        <span>Documento OCR: <strong>${escapeHtml(fields.documentNumber || "-")}</strong></span>
        <span>Importo OCR: <strong>${fields.amount ? `${formatMoney(fields.amount)} euro` : "-"}</strong></span>
      </div>
      <pre>${escapeHtml(ocr.text)}</pre>
    </details>
  `;
}

function getBalances(customerId) {
  const supabaseBalance = state.balances?.[customerId];
  if (supabaseBalance) {
    return {
      confirmed: roundMoney(supabaseBalance.confirmed),
      pending: roundMoney(supabaseBalance.pending),
      totalGenerated: roundMoney(supabaseBalance.totalGenerated)
    };
  }

  const confirmedGenerated = state.receipts
    .filter((receipt) => receipt.customerId === customerId && receipt.status === "confirmed")
    .reduce((sum, receipt) => sum + receipt.credit, 0);
  const pending = state.receipts
    .filter((receipt) => receipt.customerId === customerId && receipt.status === "pending")
    .reduce((sum, receipt) => sum + receipt.credit, 0);
  const used = state.redemptions
    .filter((item) => item.customerId === customerId)
    .reduce((sum, item) => sum + item.creditUsed, 0);
  const totalGenerated = state.receipts
    .filter((receipt) => receipt.customerId === customerId && receipt.status !== "rejected")
    .reduce((sum, receipt) => sum + receipt.credit, 0);

  return {
    confirmed: roundMoney(Math.max(confirmedGenerated - used, 0)),
    pending: roundMoney(pending),
    totalGenerated: roundMoney(totalGenerated)
  };
}

function exportJson() {
  if (!requireAccess("report")) return;

  el.exportOutput.value = JSON.stringify(state, null, 2);
  showToast("Export JSON generato.");
}

function exportCsv() {
  if (!requireAccess("report")) return;

  const rows = [
    [
      "cliente",
      "codice",
      "data",
      "ora",
      "documento",
      "importo",
      "credito",
      "stato",
      "nota",
      "ocr_confidenza",
      "ocr_data",
      "ocr_ora",
      "ocr_documento",
      "ocr_importo",
      "ocr_testo"
    ]
  ];

  state.receipts.forEach((receipt) => {
    const customer = getCustomer(receipt.customerId);
    const ocr = receipt.ocr || {};
    const ocrFields = ocr.fields || {};
    rows.push([
      customer ? `${customer.firstName} ${customer.lastName}` : "",
      customer ? customer.code : "",
      receipt.receiptDate,
      receipt.receiptTime,
      receipt.documentNumber,
      receipt.amount,
      receipt.credit,
      receipt.status,
      receipt.note,
      ocr.confidence || "",
      ocrFields.receiptDate || "",
      ocrFields.receiptTime || "",
      ocrFields.documentNumber || "",
      ocrFields.amount || "",
      ocr.text || ""
    ]);
  });

  el.exportOutput.value = rows.map((row) => row.map(csvCell).join(";")).join("\n");
  showToast("Export CSV generato.");
}

function clearAllData() {
  if (!requireAccess("report")) return;

  const ok = confirm("Vuoi svuotare tutti i dati locali del prototipo?");
  if (!ok) return;
  state = structuredClone(initialState);
  saveState();
  render();
  showToast("Dati locali svuotati.");
}

function getCustomer(id) {
  return state.customers.find((customer) => customer.id === id);
}

function getReceipt(id) {
  return state.receipts.find((receipt) => receipt.id === id);
}

function normalizeOcrText(text) {
  return String(text || "")
    .replace(/\r/g, "\n")
    .replace(/[ \t]+/g, " ")
    .replace(/\n{3,}/g, "\n\n")
    .trim();
}

function extractReceiptDate(text) {
  const europeanDate = text.match(/\b(\d{1,2})[./-](\d{1,2})[./-](\d{2,4})\b/);
  if (europeanDate) {
    return toInputDate(europeanDate[1], europeanDate[2], europeanDate[3]);
  }

  const inputDate = text.match(/\b(20\d{2})-(\d{1,2})-(\d{1,2})\b/);
  if (inputDate) {
    return toInputDate(inputDate[3], inputDate[2], inputDate[1]);
  }

  return "";
}

function toInputDate(day, month, year) {
  const fullYear = String(year).length === 2 ? `20${year}` : String(year);
  const date = new Date(Number(fullYear), Number(month) - 1, Number(day));

  if (
    date.getFullYear() !== Number(fullYear) ||
    date.getMonth() !== Number(month) - 1 ||
    date.getDate() !== Number(day)
  ) {
    return "";
  }

  return [
    fullYear.padStart(4, "0"),
    String(month).padStart(2, "0"),
    String(day).padStart(2, "0")
  ].join("-");
}

function extractReceiptTime(text) {
  const labeledTime = text.match(/\b(?:ora|ore|time)\D{0,8}([01]?\d|2[0-3])[:.]([0-5]\d)\b/i);
  if (labeledTime) {
    return `${labeledTime[1].padStart(2, "0")}:${labeledTime[2]}`;
  }

  const time = text.match(/\b([01]?\d|2[0-3]):([0-5]\d)(?::\d{2})?\b/);
  if (!time) return "";
  return `${time[1].padStart(2, "0")}:${time[2]}`;
}

function extractDocumentNumber(text) {
  const lines = text.split("\n").map((line) => line.trim()).filter(Boolean);
  const labelPattern = /\b(doc\.?|documento|numero|num\.?|n\.|nr\.?|scontrino|fiscale)\b/i;

  for (const line of lines) {
    if (!labelPattern.test(line)) continue;
    const value = line.match(/(?:doc\.?|documento|numero|num\.?|n\.|nr\.?|scontrino|fiscale)\D{0,12}([a-z0-9][a-z0-9./-]{1,20})/i);
    if (value && hasDigit(value[1])) {
      return cleanDocumentNumber(value[1]);
    }
  }

  const commercialDocument = text.match(/documento\s+commerciale[\s\S]{0,80}?\b(?:n\.?|numero)?\D{0,12}([a-z0-9][a-z0-9./-]{1,20})/i);
  if (commercialDocument && hasDigit(commercialDocument[1])) {
    return cleanDocumentNumber(commercialDocument[1]);
  }

  return "";
}

function extractReceiptAmount(text) {
  const lines = text.split("\n").map((line) => line.trim()).filter(Boolean);
  const candidates = [];

  lines.forEach((line, index) => {
    if (/\b(iva|aliquota|imponibile|resto|subtotale|sconto)\b/i.test(line)) return;

    const amounts = findMoneyValues(line);
    if (!amounts.length) return;

    let score = index / 100;
    if (/\b(totale|tot\.|total)\b/i.test(line)) score += 40;
    if (/\b(importo|euro|eur|contanti|pagato)\b/i.test(line)) score += 12;

    amounts.forEach((amount) => {
      if (amount > 0 && amount <= 500) {
        candidates.push({ amount, score });
      }
    });
  });

  if (candidates.length) {
    candidates.sort((a, b) => b.score - a.score || b.amount - a.amount);
    return roundMoney(candidates[0].amount);
  }

  const fallback = findMoneyValues(text)
    .filter((amount) => amount > 0 && amount <= 500)
    .sort((a, b) => b - a);

  return fallback[0] ? roundMoney(fallback[0]) : 0;
}

function findMoneyValues(text) {
  const matches = String(text || "").match(/\b\d{1,4}(?:[.,]\d{2})\b/g) || [];
  return matches.map(parseOcrMoney).filter((value) => Number.isFinite(value));
}

function parseOcrMoney(value) {
  const clean = String(value || "").replace(/\s/g, "");
  const commaIndex = clean.lastIndexOf(",");
  const dotIndex = clean.lastIndexOf(".");

  if (commaIndex > dotIndex) {
    return Number(clean.replace(/\./g, "").replace(",", "."));
  }

  return Number(clean.replace(/,/g, ""));
}

function cleanDocumentNumber(value) {
  return String(value || "")
    .replace(/^[^\da-z]+/i, "")
    .replace(/[^\da-z./-]+$/i, "")
    .trim();
}

function hasDigit(value) {
  return /\d/.test(String(value || ""));
}

function parseMoney(value) {
  if (typeof value !== "string") return Number(value) || 0;
  return Number(value.replace(",", "."));
}

function roundMoney(value) {
  return Math.round((Number(value) + Number.EPSILON) * 100) / 100;
}

function formatMoney(value) {
  return roundMoney(value).toLocaleString("it-IT", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
  });
}

function formatDate(value) {
  if (!value) return "";
  const [year, month, day] = value.split("-");
  return `${day}/${month}/${year}`;
}

function formatDateTime(value) {
  if (!value) return "";
  const date = new Date(value);
  return date.toLocaleString("it-IT", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit"
  });
}

function statusLabel(status) {
  const labels = {
    pending: "In verifica",
    confirmed: "Confermato",
    rejected: "Rifiutato",
    expired: "Scaduto"
  };
  return labels[status] || status;
}

function requestStatusLabel(status) {
  return REQUEST_STATUSES[status] || status;
}

function requestStatusTone(status) {
  const tones = {
    inviata: "pending",
    in_contatto: "pending",
    confermata: "confirmed",
    rifiutata: "rejected",
    annullata: "rejected"
  };
  return tones[status] || "pending";
}

function cleanText(value) {
  return String(value || "").trim();
}

function normalizePhone(value) {
  return cleanText(value).replace(/\D/g, "");
}

function escapeHtml(value) {
  return String(value || "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function csvCell(value) {
  return `"${String(value ?? "").replaceAll('"', '""')}"`;
}

// --- v45 cassiere-first ---

let cassiereSelectedCustomerId = null;
let cassiereCopiedMessageText = null;
let lastRedemptionId = null;

function initPublicSaldo() {
  const params = new URLSearchParams(window.location.search);
  const token = params.get("saldo");
  if (!token) return false;

  const publicPage = document.getElementById("saldoPublicPage");
  const appShell = document.querySelector(".app-shell");
  if (!publicPage || !appShell) return false;

  publicPage.hidden = false;
  appShell.hidden = true;
  document.title = "Saldo SQ — Credito Salute";
  initSupabase();
  loadPublicSaldo(token);
  return true;
}

async function loadPublicSaldo(token) {
  const content = document.getElementById("saldoPublicContent");
  if (!content) return;
  if (!supabaseClient) {
    content.innerHTML = `<p class="form-status" data-status="error">Servizio non disponibile. Riprova tra qualche istante.</p>`;
    return;
  }
  const { data, error } = await supabaseClient.rpc("saldo_pubblico_per_token", { p_token: token });
  if (error || !data) {
    renderPublicSaldoError(content, "Saldo non trovato. Verifica il link ricevuto dal bar.");
    return;
  }
  renderPublicSaldo(content, data);
}

function renderPublicSaldo(container, data) {
  container.innerHTML = `
    <div class="saldo-public__card">
      <p class="eyebrow">${escapeHtml(data.codice)}</p>
      <h2>${escapeHtml(data.nome)} ${escapeHtml(data.cognome)}</h2>
      <div class="saldo-public__balances">
        <div class="saldo-public__balance-item">
          <span>Saldo disponibile</span>
          <strong>${formatMoney(data.confermato)} euro SQ</strong>
        </div>
        ${data.in_verifica > 0 ? `
        <div class="saldo-public__balance-item">
          <span>In verifica SQ</span>
          <strong>${formatMoney(data.in_verifica)} euro SQ</strong>
        </div>` : ""}
      </div>
      ${renderAffordableServicesMarkup(Number(data.confermato))}
    </div>
  `;
}

function renderPublicSaldoError(container, msg) {
  container.innerHTML = `<p class="form-status" data-status="error">${escapeHtml(msg)}</p>`;
}

function getAffordableServices(balance) {
  return Object.entries(services)
    .map(([name, cfg]) => {
      const creditApplied = Math.min(balance, cfg.price);
      const difference = Math.max(cfg.price - creditApplied, 0);
      return { name, price: cfg.price, creditApplied, difference, fullyCovers: difference === 0 };
    })
    .filter((s) => s.creditApplied > 0);
}

function renderAffordableServicesMarkup(balance) {
  const affordable = getAffordableServices(balance);
  if (!affordable.length) return `<p class="affordable-services__empty">Continua ad accumulare per raggiungere una prestazione.</p>`;
  return `
    <div class="affordable-services">
      <p class="eyebrow">Con il tuo saldo puoi prenotare</p>
      ${affordable.map((s) => `
        <div class="affordable-service${s.fullyCovers ? " affordable-service--full" : ""}">
          <strong>${escapeHtml(s.name)}</strong>
          <span>${formatMoney(s.creditApplied)} euro SQ${s.difference > 0 ? ` + ${formatMoney(s.difference)} euro da pagare` : " — interamente coperta"}</span>
        </div>
      `).join("")}
    </div>
  `;
}

function buildSaldoUrl(token) {
  return `${window.location.origin}${window.location.pathname}?saldo=${token}`;
}

function buildWhatsAppMessageCustomer(customer, addedCredit, balance) {
  const affordable = getAffordableServices(balance);
  const serviceLines = affordable.length
    ? affordable.map((s) => `• ${s.name}: ${formatMoney(s.creditApplied)} SQ${s.difference > 0 ? ` + ${formatMoney(s.difference)}€ di differenza` : " (coperta)"}`).join("\n")
    : "Continua ad accumulare per raggiungere la prima prestazione.";
  const saldoUrl = customer.saldoToken ? buildSaldoUrl(customer.saldoToken) : "";
  return [
    `Ciao ${customer.firstName}!`,
    `Hai guadagnato ${formatMoney(addedCredit)} euro SQ oggi al ${BAR_NAME}.`,
    `Il tuo saldo e' ora ${formatMoney(balance)} euro SQ.`,
    "",
    "Con il tuo saldo puoi prenotare:",
    serviceLines,
    "",
    saldoUrl ? `Il tuo saldo aggiornato: ${saldoUrl}` : "",
    "— Salute Quotidiana"
  ].filter((l) => l !== undefined).join("\n").replace(/\n{3,}/g, "\n\n").trim();
}

function buildWhatsAppMessageBar(customer, redemption) {
  return [
    `Prestazione Credito SQ — ${formatDate(redemption.createdAt)}`,
    `Cliente: ${customer.firstName} ${customer.lastName} (${customer.code})`,
    `Prestazione: ${redemption.service} — ${formatMoney(redemption.servicePrice)} euro`,
    `Credito SQ applicato: ${formatMoney(redemption.creditUsed)} euro`,
    `Da versare al fondo SQ: ${formatMoney(redemption.creditUsed)} euro`,
    "",
    "Grazie — Salute Quotidiana"
  ].join("\n");
}

function copyToClipboard(text, successMsg) {
  navigator.clipboard.writeText(text).then(
    () => showToast(successMsg || "Copiato!"),
    () => showToast("Copia manuale: seleziona il testo e copia.")
  );
}

function handleCassiereSearch(event) {
  if (event && event.type !== "keydown") event.preventDefault?.();
  const query = (el.cassiereSearchInput?.value || "").trim().toLowerCase();
  if (!query) return;
  const matches = state.customers.filter((c) =>
    `${c.firstName} ${c.lastName}`.toLowerCase().includes(query) ||
    normalizePhone(c.phone).includes(normalizePhone(query))
  );
  renderCassiereResults(matches, query);
}

function renderCassiereResults(matches, query) {
  if (!el.cassiereResults) return;
  if (!matches.length) {
    el.cassiereResults.innerHTML = `<p class="form-status" data-status="error">Nessun cliente trovato per "${escapeHtml(query)}". Registralo qui sotto.</p>`;
    return;
  }
  el.cassiereResults.innerHTML = matches.map((c) => `
    <div class="cassiere-result-row">
      <span>${escapeHtml(c.code)} — ${escapeHtml(c.firstName)} ${escapeHtml(c.lastName)}${c.phone ? ` — ${escapeHtml(c.phone)}` : ""}</span>
      <button type="button" class="secondary small" onclick="selectCassiereCustomer('${c.id}')">Seleziona</button>
    </div>
  `).join("");
}

function selectCassiereCustomer(customerId) {
  const customer = getCustomer(customerId);
  if (!customer) return;
  cassiereSelectedCustomerId = customerId;
  if (el.cassiereResults) el.cassiereResults.innerHTML = "";
  if (el.cassiereCustomerLabel) el.cassiereCustomerLabel.textContent = `${customer.code} — ${customer.firstName} ${customer.lastName}`;
  if (el.cassiereSelectedCustomer) el.cassiereSelectedCustomer.hidden = false;
  if (el.cassiereMessageArea) el.cassiereMessageArea.hidden = true;
  if (el.cassiereReceiptStatus) el.cassiereReceiptStatus.textContent = "";
  if (el.cassiereReceiptForm) {
    el.cassiereReceiptForm.reset();
    el.cassiereReceiptForm.receiptDate.value = new Date().toISOString().slice(0, 10);
  }
}

function clearCassiereCustomer() {
  cassiereSelectedCustomerId = null;
  if (el.cassiereSelectedCustomer) el.cassiereSelectedCustomer.hidden = true;
  if (el.cassiereMessageArea) el.cassiereMessageArea.hidden = true;
  if (el.cassiereResults) el.cassiereResults.innerHTML = "";
  if (el.cassiereSearchInput) el.cassiereSearchInput.value = "";
}

async function handleCassiereQuickRegister(event) {
  event.preventDefault();
  const form = new FormData(event.currentTarget);
  const nome = cleanText(form.get("firstName"));
  const cognome = cleanText(form.get("lastName"));
  const telefono = cleanText(form.get("phone"));
  if (el.cassiereRegisterStatus) el.cassiereRegisterStatus.textContent = "Registrazione in corso...";
  if (!supabaseClient) {
    if (el.cassiereRegisterStatus) el.cassiereRegisterStatus.textContent = "Errore: Supabase non disponibile.";
    return;
  }
  const { data, error } = await supabaseClient.rpc("registra_cliente_rapido_pilot", {
    p_nome: nome, p_cognome: cognome, p_telefono: telefono
  });
  if (error) {
    if (el.cassiereRegisterStatus) el.cassiereRegisterStatus.textContent = `Errore: ${error.message}`;
    return;
  }
  const msg = data.exists ? "Cliente gia' presente — selezionato." : "Cliente registrato.";
  if (el.cassiereRegisterStatus) el.cassiereRegisterStatus.textContent = msg;
  showToast(msg);
  event.currentTarget.reset();
  await loadPilotCustomersFromSupabase();
  selectCassiereCustomer(data.id);
}

async function handleCassiereReceiptSubmit(event) {
  event.preventDefault();
  const customer = getCustomer(cassiereSelectedCustomerId);
  if (!customer) { showToast("Seleziona un cliente prima."); return; }
  const form = new FormData(event.currentTarget);
  const amount = parseMoney(form.get("amount"));
  const validConsumption = !!form.get("validConsumption");
  if (!amount || amount <= 0) {
    if (el.cassiereReceiptStatus) el.cassiereReceiptStatus.textContent = "Importo non valido.";
    return;
  }
  if (!validConsumption) {
    if (el.cassiereReceiptStatus) el.cassiereReceiptStatus.textContent = "Conferma che sia una consumazione valida.";
    return;
  }
  const receiptDate = cleanText(form.get("receiptDate")) || new Date().toISOString().slice(0, 10);
  const documentNumber = cleanText(form.get("documentNumber"));
  const credit = roundMoney(amount * CREDIT_RATE);
  const receipt = {
    id: crypto.randomUUID(),
    customerId: customer.id,
    customerCode: customer.code,
    receiptDate,
    receiptTime: new Date().toTimeString().slice(0, 5),
    amount,
    credit,
    documentNumber,
    operatorLabel: localStorage.getItem("sq_operatore") || null,
    status: "pending",
    note: "Caricato da cassiere bar",
    createdAt: new Date().toISOString()
  };
  if (el.cassiereReceiptStatus) el.cassiereReceiptStatus.textContent = "Salvataggio...";
  const result = await saveReceiptToSupabase(receipt, false, { autoApprove: amount <= AUTO_APPROVE_MAX_AMOUNT, message: "" });
  if (!result.ok) {
    if (el.cassiereReceiptStatus) el.cassiereReceiptStatus.textContent = `Errore: ${result.message}`;
    return;
  }
  upsertReceipt(receipt);
  saveState();
  const balances = getBalances(customer.id);
  const newBalance = balances.confirmed + credit;
  const msg = buildWhatsAppMessageCustomer(customer, credit, newBalance);
  cassiereCopiedMessageText = msg;
  if (el.cassiereWhatsAppText) el.cassiereWhatsAppText.value = msg;
  if (el.cassiereMessageArea) el.cassiereMessageArea.hidden = false;
  if (el.cassiereReceiptStatus) el.cassiereReceiptStatus.textContent = `Scontrino registrato. Credito: +${formatMoney(credit)} euro SQ.`;
  event.currentTarget.reset();
  event.currentTarget.receiptDate.value = new Date().toISOString().slice(0, 10);
  showToast(`Scontrino caricato per ${customer.firstName}.`);
  loadPilotReceiptsFromSupabase();
  loadPilotBalancesFromSupabase();
}

function copyCassiereWhatsApp() {
  if (!cassiereCopiedMessageText) return;
  copyToClipboard(cassiereCopiedMessageText, "Messaggio WhatsApp copiato!");
}

async function markPaymentReceived(redemptionId) {
  const ok = await markPaymentReceivedOnSupabase(redemptionId);
  if (!ok) return;
  const redemption = state.redemptions.find((r) => r.id === redemptionId);
  if (redemption) {
    redemption.paymentStatus = "incassato";
    redemption.incassatoAt = new Date().toISOString();
    saveState();
    renderRedemptionHistory();
  }
  showToast("Pagamento segnato come incassato.");
}

async function markPaymentReceivedOnSupabase(id) {
  if (!supabaseClient) return false;
  const { error } = await supabaseClient.rpc("segna_pagamento_incassato_pilot", { p_id: id });
  if (error) { showToast(`Errore: ${error.message}`); return false; }
  return true;
}

function copyBarPaymentMessage(redemptionId) {
  const redemption = state.redemptions.find((r) => r.id === redemptionId);
  if (!redemption) return;
  const customer = getCustomer(redemption.customerId);
  if (!customer) return;
  const msg = buildWhatsAppMessageBar(customer, redemption);
  copyToClipboard(msg, "Messaggio bar copiato!");
}

// --- end v45 ---

function showToast(message) {
  el.toast.textContent = message;
  el.toast.classList.add("is-visible");
  window.clearTimeout(showToast.timeout);
  showToast.timeout = window.setTimeout(() => {
    el.toast.classList.remove("is-visible");
  }, 2600);
}
