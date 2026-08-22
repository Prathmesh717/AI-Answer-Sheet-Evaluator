// ── Config ────────────────────────────────────────────────────────────────────
// FastAPI runs at http://127.0.0.1:8000
// Routes: /auth/...  /evaluation/...  /ocr/...  /evaluations/...  /payments/...
// No /api prefix — set REACT_APP_API_URL in .env to override.
const BASE_URL = process.env.REACT_APP_API_URL || 'http://127.0.0.1:8000';

// ── Token / User helpers (localStorage) ──────────────────────────────────────
export const getToken    = ()  => localStorage.getItem('evalai_token');
export const setToken    = (t) => localStorage.setItem('evalai_token', t);
export const removeToken = ()  => localStorage.removeItem('evalai_token');
export const getUser     = ()  => {
  try { return JSON.parse(localStorage.getItem('evalai_user')); } catch { return null; }
};
export const setUser     = (u) => localStorage.setItem('evalai_user', JSON.stringify(u));
export const removeUser  = ()  => localStorage.removeItem('evalai_user');

// ── Auth header helper ────────────────────────────────────────────────────────
function authHeader() {
  const t = getToken();
  return t ? { Authorization: `Bearer ${t}` } : {};
}

// ─────────────────────────────────────────────────────────────────────────────
// Base fetch — JSON bodies
// ─────────────────────────────────────────────────────────────────────────────
async function apiFetch(path, options = {}) {
  const headers = {
    'Content-Type': 'application/json',
    ...authHeader(),
    ...options.headers,   // allow callers to override
  };

  const res = await fetch(`${BASE_URL}${path}`, { ...options, headers });

  // Auto-clear session on 401
  if (res.status === 401) {
    removeToken();
    removeUser();
    throw new Error('SESSION_EXPIRED');
  }

  if (res.status === 204) return null;  // No Content

  const ct = res.headers.get('content-type') || '';
  const data = ct.includes('application/json') ? await res.json() : await res.text();

  if (!res.ok) throw new Error(data?.detail || data || `HTTP ${res.status}`);
  return data;
}

// ─────────────────────────────────────────────────────────────────────────────
// Base fetch — multipart/FormData (file uploads)
// Browser sets Content-Type + boundary automatically — do NOT set it manually.
// ─────────────────────────────────────────────────────────────────────────────
async function apiFetchForm(path, formData) {
  const res = await fetch(`${BASE_URL}${path}`, {
    method:  'POST',
    headers: authHeader(),   // only Authorization — no Content-Type
    body:    formData,
  });

  if (res.status === 401) {
    removeToken();
    removeUser();
    throw new Error('SESSION_EXPIRED');
  }

  if (res.status === 204) return null;

  const ct = res.headers.get('content-type') || '';

  // File download response
  if (ct.includes('octet-stream') || ct.includes('spreadsheet') || ct.includes('vnd.ms-excel')) {
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.blob();
  }

  const data = ct.includes('application/json') ? await res.json() : await res.text();
  if (!res.ok) throw new Error(data?.detail || data || `HTTP ${res.status}`);
  return data;
}

// ─────────────────────────────────────────────────────────────────────────────
// AUTH
// FastAPI OAuth2: login expects form-encoded  { username, password }
//                 register expects JSON        { name, email, password }
//                 Both return { access_token, token_type, user }
// ─────────────────────────────────────────────────────────────────────────────
export const authAPI = {
  /**
   * Register a new user.
   * Returns { access_token, token_type, user }
   */
  register: (name, email, password) =>
    apiFetch('/api/auth/register', {
      method: 'POST',
      body:   JSON.stringify({ name, email, password }),
    }),

  /**
   * Login using FastAPI OAuth2PasswordRequestForm.
   * IMPORTANT: FastAPI expects "username" field (not "email") + form-encoded body.
   * Returns { access_token, token_type, user }
   */
login: async (email, password) => {
  const res = await fetch(`${BASE_URL}/api/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  });

  if (res.status === 401) throw new Error('Invalid email or password');

  const data = await res.json();
  if (!res.ok) throw new Error(data?.detail || 'Login failed');

  return {
    access_token: data.access_token,
    token_type: data.token_type || 'bearer',
    user: data.user || { email, name: data.name || email },
  };
},

  /** GET /auth/me — returns currently logged-in user */
  me: () => apiFetch('/api/auth/me'),

  logout: () => { removeToken(); removeUser(); },
};

// ─────────────────────────────────────────────────────────────────────────────
// EVALUATION ENGINE
// POST /evaluation/evaluate-subject   — single subject (multipart)
// POST /evaluation/evaluate-batch     — up to 3 subjects (multipart)
// POST /evaluation/send-emails        — JSON
// POST /evaluation/test-email         — no body
// GET  /evaluation/list-results       — list server result files
// GET  /evaluation/download/{file}    — download blob
// ─────────────────────────────────────────────────────────────────────────────
export const evaluationAPI = {
  /**
   * Evaluate a single subject.
   * @param {string}    subjectName
   * @param {File}      masterPdf       — actual File object
   * @param {File[]}    studentPdfs     — array of File objects
   * @param {boolean}   sendEmail
   * @param {function}  onLog           — optional(string) => void, called per log line
   */
  evaluateSubject: async (subjectName, masterPdf, studentPdfs, sendEmail = false, onLog = null) => {
    const fd = new FormData();
    fd.append('subject_name', subjectName);
    fd.append('master_pdf',   masterPdf);
    studentPdfs.forEach(f => fd.append('student_pdfs', f));
    fd.append('send_email', String(sendEmail));

    const data = await apiFetchForm('/evaluation/evaluate-subject', fd);
    if (onLog && Array.isArray(data?.logs)) data.logs.forEach(l => onLog(l));
    return data;
    // Returns: { subject, students_evaluated, results_file, results[], logs[], email_status? }
  },

  /**
   * Batch evaluate up to 3 subjects in one request.
   * @param {{ name, masterPdf: File, studentPdfs: File[] }[]} subjects
   */
  evaluateBatch: async (subjects, sendEmail = false, onLog = null) => {
    const fd = new FormData();
    subjects.slice(0, 3).forEach((s, i) => {
      fd.append(`subject_name_${i}`, s.name);
      fd.append(`master_${i}`,       s.masterPdf);
      s.studentPdfs.forEach(f => fd.append(`students_${i}`, f));
    });
    fd.append('send_email', String(sendEmail));

    const data = await apiFetchForm('/evaluation/evaluate-batch', fd);
    if (onLog && Array.isArray(data?.logs)) data.logs.forEach(l => onLog(l));
    return data;
    // Returns: { subjects_evaluated[], total_students, consolidated_file, results[], logs[] }
  },

  /** Re-dispatch emails for already-evaluated results */
  sendEmails: (results, detailedFeedback, consolidatedFile = null) =>
    apiFetch('/evaluation/send-emails', {
      method: 'POST',
      body:   JSON.stringify({
        results,
        detailed_feedback: detailedFeedback,
        consolidated_file: consolidatedFile,
      }),
    }),

  /** Test SMTP connection — returns { status, message } */
  testEmail: () => apiFetch('/evaluation/test-email', { method: 'POST' }),

  /** List downloadable result files on the server */
  listResults: () => apiFetch('/evaluation/list-results'),

  /** Download a result file — triggers browser save dialog */
  downloadFile: async (filename) => {
    const res = await fetch(
      `${BASE_URL}/evaluation/download/${encodeURIComponent(filename)}`,
      { headers: authHeader() }
    );
    if (!res.ok) throw new Error(`Download failed: HTTP ${res.status}`);
    const blob = await res.blob();
    const url  = URL.createObjectURL(blob);
    const a    = document.createElement('a');
    a.href     = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  },
};

// ─────────────────────────────────────────────────────────────────────────────
// OCR
// POST /ocr/extract-text        — single PDF
// POST /ocr/extract-text-batch  — multiple PDFs
// ─────────────────────────────────────────────────────────────────────────────
export const ocrAPI = {
  /**
   * Extract text from a single PDF.
   * @param {File}     pdfFile
   * @param {boolean}  forceOcr   — skip PyPDF2 fast-path, always use NVIDIA NIM
   * @param {function} onLog      — optional log callback
   */
  extractText: async (pdfFile, forceOcr = false, onLog = null) => {
    const fd = new FormData();
    fd.append('pdf_file',  pdfFile);
    fd.append('force_ocr', String(forceOcr));

    const data = await apiFetchForm('/ocr/extract-text', fd);
    if (onLog && Array.isArray(data?.logs)) data.logs.forEach(l => onLog(l));
    return data;
    // Returns: { filename, method_used, char_count, text, logs[] }
  },

  /** Batch OCR — multiple PDFs at once */
  extractBatch: async (pdfFiles, forceOcr = false) => {
    const fd = new FormData();
    pdfFiles.forEach(f => fd.append('pdf_files', f));
    fd.append('force_ocr', String(forceOcr));
    return apiFetchForm('/ocr/extract-text-batch', fd);
    // Returns: { results: [{ filename, method_used, char_count, text, success }], total }
  },
};

// ─────────────────────────────────────────────────────────────────────────────
// EVALUATIONS HISTORY  (MongoDB records)
// GET  /evaluations/stats         — aggregate stats
// GET  /evaluations/?skip&limit   — paginated list
// POST /evaluations/              — save a result record
// GET  /evaluations/{id}          — single record
// DELETE /evaluations/{id}        — delete record
// ─────────────────────────────────────────────────────────────────────────────
export const evaluationsAPI = {
  /**
   * Aggregate stats.
   * Returns: { total_evaluations, avg_percentage, highest, grade_distribution, subjects[] }
   */
  stats: () => apiFetch('/api/evaluations/stats'),

  /**
   * Paginated list of past evaluation records.
   * Returns array of evaluation objects.
   */
  list: (subject = '', skip = 0, limit = 100) => {
    const p = new URLSearchParams({ skip, limit });
    if (subject) p.set('subject', subject);
    return apiFetch(`/api/evaluations/?${p}`);
  },

  /** Persist a result record to MongoDB */
  save: (data) =>
    apiFetch('/api/evaluations/', { method: 'POST', body: JSON.stringify(data) }),

  /** Fetch a single record by id */
  get: (id) => apiFetch(`/api/evaluations/${id}`),

  /** Delete a record */
  delete: (id) => apiFetch(`/api/evaluations/${id}`, { method: 'DELETE' }),
};

// ─────────────────────────────────────────────────────────────────────────────
// PAYMENTS  (Razorpay)
// Mounted in backend/main.py with prefix "/api/payments"
// POST /api/payments/create-order  — returns { order_id, amount, currency, key_id }
// POST /api/payments/verify        — verifies signature, saves record
// GET  /api/payments/history       — payment history for current user
// ─────────────────────────────────────────────────────────────────────────────
export const paymentsAPI = {
  /** Step 1 — create a Razorpay order */
  createOrder: (planId) =>
    apiFetch('/api/payments/create-order', {
      method: 'POST',
      body:   JSON.stringify({ plan_id: planId }),
    }),

  /** Step 2 — verify payment signature and persist record */
  verifyPayment: (razorpay_order_id, razorpay_payment_id, razorpay_signature, plan_id) =>
    apiFetch('/api/payments/verify', {
      method: 'POST',
      body:   JSON.stringify({
        razorpay_order_id,
        razorpay_payment_id,
        razorpay_signature,
        plan_id,
      }),
    }),

  /** Payment history for the logged-in user */
  history: () => apiFetch('/api/payments/history'),

  /** Current subscription status (source of truth from DB), e.g. { planId, planName, activatedAt } */
  status: () => apiFetch('/api/payments/status'),
};

// ─────────────────────────────────────────────────────────────────────────────
// HEALTH
// ─────────────────────────────────────────────────────────────────────────────
export const healthAPI = {
  ping: () => apiFetch('/health'),
};
