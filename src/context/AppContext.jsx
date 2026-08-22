import { createContext, useContext, useReducer, useEffect } from 'react';
import {
  authAPI,
  getToken, getUser,
  setToken, setUser,
  removeToken, removeUser,
} from '../services/api';

// ── Initial state ─────────────────────────────────────────────────────────────
const initialState = {
  // ── Auth ─────────────────────────────────────────────────────────────────────
  authUser:    getUser(),           // re-hydrated from localStorage on page reload
  authLoading: !!getToken(),        // true only when there's a token to validate
  authChecked: !getToken(),         // skip backend check when no token exists

  // ── Navigation ───────────────────────────────────────────────────────────────
  activeTab: 'subjects',

  // ── Subjects  (each entry holds actual File objects for upload) ───────────────
  // Shape: { name, masterPdf: File, studentPdfs: File[],
  //          masterPdfName, studentPdfNames[], addedAt }
  subjects: [],

  // ── Evaluation logs ───────────────────────────────────────────────────────────
  evaluationLogs: [],  // { text, time }[]

  // ── PDF / OCR logs ────────────────────────────────────────────────────────────
  pdfLogs: [],         // { text, time }[]

  // ── Last consolidated results file path returned by backend ──────────────────
  resultsFile: null,

  // ── Analytics data (fetched from /evaluations/stats) ─────────────────────────
  analytics: null,

  // ── User settings ─────────────────────────────────────────────────────────────
  settings: {
    senderEmail:  '',
    appPassword:  '',
    nvidiaApiKey: '',
    outputDir:    'extracted_pdfs',
    useOCR:       true,
    useSemantic:  true,
    sendEmails:   false,
  },

  // ── Shared processing state (used by EvaluationPanel & PDFTools) ──────────────
  isProcessing: false,
  progress:     0,
};

// ── Reducer ───────────────────────────────────────────────────────────────────
function reducer(state, action) {
  switch (action.type) {
    // ── Auth ──────────────────────────────────────────────────────────────────
    case 'AUTH_LOGIN':
      return { ...state, authUser: action.payload, authLoading: false, authChecked: true };
    case 'AUTH_LOGOUT':
      return { ...state, authUser: null, authLoading: false, authChecked: true };
    case 'AUTH_CHECKED':
      return { ...state, authLoading: false, authChecked: true };

    // ── Navigation ────────────────────────────────────────────────────────────
    case 'SET_TAB':
      return { ...state, activeTab: action.payload };

    // ── Subjects ──────────────────────────────────────────────────────────────
    case 'ADD_SUBJECT':
      return { ...state, subjects: [...state.subjects, action.payload] };
    case 'REMOVE_SUBJECT':
      return { ...state, subjects: state.subjects.filter((_, i) => i !== action.payload) };
    case 'UPDATE_SUBJECT':
      return {
        ...state,
        subjects: state.subjects.map((s, i) =>
          i === action.payload.index ? action.payload.data : s
        ),
      };
    case 'CLEAR_SUBJECTS':
      return { ...state, subjects: [] };

    // ── Evaluation logs ───────────────────────────────────────────────────────
    case 'ADD_LOG':
      return { ...state, evaluationLogs: [...state.evaluationLogs, action.payload] };
    case 'CLEAR_LOGS':
      return { ...state, evaluationLogs: [] };

    // ── PDF / OCR logs ────────────────────────────────────────────────────────
    case 'ADD_PDF_LOG':
      return { ...state, pdfLogs: [...state.pdfLogs, action.payload] };
    case 'CLEAR_PDF_LOGS':
      return { ...state, pdfLogs: [] };

    // ── Results file (path returned by backend after evaluation) ──────────────
    case 'SET_RESULTS_FILE':
      return { ...state, resultsFile: action.payload };

    // ── Analytics ─────────────────────────────────────────────────────────────
    case 'SET_ANALYTICS':
      return { ...state, analytics: action.payload };

    // ── Settings ──────────────────────────────────────────────────────────────
    case 'UPDATE_SETTINGS':
      return { ...state, settings: { ...state.settings, ...action.payload } };

    // ── Processing / progress ─────────────────────────────────────────────────
    case 'SET_PROCESSING':
      return { ...state, isProcessing: action.payload };
    case 'SET_PROGRESS':
      return { ...state, progress: action.payload };

    default:
      return state;
  }
}

// ── Context ───────────────────────────────────────────────────────────────────
const AppContext = createContext(null);

export function AppProvider({ children }) {
  const [state, dispatch] = useReducer(reducer, initialState);

  // ── On mount: validate stored JWT with the backend ────────────────────────
  useEffect(() => {
    const token = getToken();
    if (!token) {
      dispatch({ type: 'AUTH_CHECKED' });
      return;
    }
    authAPI.me()
      .then((user) => {
        setUser(user);
        dispatch({ type: 'AUTH_LOGIN', payload: user });
      })
      .catch(() => {
        removeToken();
        removeUser();
        dispatch({ type: 'AUTH_LOGOUT' });
      });
  }, []);

  // ── Auth helpers (called by Login / Register pages) ───────────────────────

  async function login(email, password) {
    const data = await authAPI.login(email, password);
    setToken(data.access_token);
    setUser(data.user);
    dispatch({ type: 'AUTH_LOGIN', payload: data.user });
    return data.user;
  }

  async function register(name, email, password) {
    const data = await authAPI.register(name, email, password);
    setToken(data.access_token);
    setUser(data.user);
    dispatch({ type: 'AUTH_LOGIN', payload: data.user });
    return data.user;
  }

  function logout() {
    authAPI.logout();          // clears localStorage
    dispatch({ type: 'AUTH_LOGOUT' });
  }

  // ── Log helpers (convenience wrappers used by evaluation components) ───────

  function addLog(text) {
    dispatch({ type: 'ADD_LOG', payload: { text, time: new Date().toLocaleTimeString() } });
  }

  function addPdfLog(text) {
    dispatch({ type: 'ADD_PDF_LOG', payload: { text, time: new Date().toLocaleTimeString() } });
  }

  return (
    <AppContext.Provider value={{
      state,
      dispatch,
      // Auth
      login,
      register,
      logout,
      // Log helpers
      addLog,
      addPdfLog,
    }}>
      {children}
    </AppContext.Provider>
  );
}

export function useApp() {
  const ctx = useContext(AppContext);
  if (!ctx) throw new Error('useApp must be used inside <AppProvider>');
  return ctx;
}
