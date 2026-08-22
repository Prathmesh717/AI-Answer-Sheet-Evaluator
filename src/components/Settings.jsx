import { useState, useEffect } from 'react';
import { useApp } from '../context/AppContext';
import { evaluationAPI, healthAPI } from '../services/api';
import styles from './Settings.module.css';

function SettingSection({ title, children }) {
  return (
    <div className={styles.section}>
      <div className={styles.sectionTitle}>{title}</div>
      <div className={styles.sectionBody}>{children}</div>
    </div>
  );
}

function Field({ label, hint, children }) {
  return (
    <div className={styles.field}>
      <div className={styles.fieldMeta}>
        <label className={styles.fieldLabel}>{label}</label>
        {hint && <span className={styles.fieldHint}>{hint}</span>}
      </div>
      {children}
    </div>
  );
}

export default function Settings() {
  const { state, dispatch } = useApp();
  const [saved,       setSaved]      = useState(false);
  const [showPass,    setShowPass]   = useState(false);
  const [testingEmail, setTestEmail] = useState(false);
  const [emailStatus, setEmailStatus] = useState('');  // 'ok' | 'error' | ''
  const [emailMsg,    setEmailMsg]   = useState('');
  const [apiHealth,   setApiHealth]  = useState(null); // null | 'ok' | 'error'
  const [resultFiles, setResultFiles] = useState([]);

  // ── Check backend health on mount ────────────────────────────────────────
  useEffect(() => {
    healthAPI.ping()
      .then(() => setApiHealth('ok'))
      .catch(() => setApiHealth('error'));

    evaluationAPI.listResults()
      .then(d => setResultFiles(d.files || []))
      .catch(() => {});
  }, []);

  function update(key, value) {
    dispatch({ type: 'UPDATE_SETTINGS', payload: { [key]: value } });
  }

  // ── Save settings (local state + optionally persist to backend) ───────────
  async function save() {
    setSaved(true);
    // Future: call settingsAPI.save(state.settings) to persist on backend
    setTimeout(() => setSaved(false), 2500);
  }

  // ── Test email via real API ───────────────────────────────────────────────
  async function testEmailConnection() {
    setTestEmail(true);
    setEmailStatus('');
    setEmailMsg('');
    try {
      const res = await evaluationAPI.testEmail();
      setEmailStatus('ok');
      setEmailMsg(res.message || 'Connection successful!');
    } catch (err) {
      setEmailStatus('error');
      setEmailMsg(err.message || 'Connection failed');
    } finally {
      setTestEmail(false);
    }
  }

  // ── Download result file ──────────────────────────────────────────────────
  async function handleDownload(filename) {
    try {
      await evaluationAPI.downloadFile(filename);
    } catch (err) {
      alert(`Download failed: ${err.message}`);
    }
  }

  return (
    <div className={styles.page}>
      <div className={styles.header}>
        <div>
          <h1 className={styles.title}>Settings</h1>
          <p className={styles.subtitle}>Configure system preferences, API keys &amp; email credentials</p>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          {/* Backend health indicator */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 13, color: apiHealth === 'ok' ? '#16A34A' : apiHealth === 'error' ? '#EF4444' : '#9CA3AF' }}>
            <span style={{ width: 8, height: 8, borderRadius: '50%', background: 'currentColor', display: 'inline-block' }} />
            {apiHealth === 'ok' ? 'Backend Online' : apiHealth === 'error' ? 'Backend Offline' : 'Checking...'}
          </div>
          <button className={`${styles.saveBtn} ${saved ? styles.saved : ''}`} onClick={save}>
            {saved ? '✅ Saved!' : '💾 Save Settings'}
          </button>
        </div>
      </div>

      <div className={styles.layout}>
        {/* Backend Status */}
        <SettingSection title="🌐 Backend Connection">
          <div style={{ padding: '12px 14px', borderRadius: 8, background: apiHealth === 'ok' ? '#F0FDF4' : '#FEF2F2', border: `1px solid ${apiHealth === 'ok' ? '#BBF7D0' : '#FECACA'}` }}>
            <div style={{ fontWeight: 600, fontSize: 13, color: apiHealth === 'ok' ? '#166534' : '#991B1B' }}>
              {apiHealth === 'ok' ? '✅ FastAPI backend is reachable' : '❌ Cannot reach backend'}
            </div>
            <div style={{ fontSize: 12, color: '#6B7280', marginTop: 4 }}>
              URL: <code>http://127.0.0.1:8000</code>
            </div>
            {apiHealth === 'error' && (
              <div style={{ fontSize: 11, color: '#EF4444', marginTop: 6 }}>
                Run: <code>cd backend &amp;&amp; uvicorn main:app --reload</code>
              </div>
            )}
          </div>

          <Field label="API Docs" hint="Interactive Swagger UI">
            <a
              href="http://127.0.0.1:8000/docs"
              target="_blank"
              rel="noopener noreferrer"
              className={styles.input}
              style={{ display: 'block', textDecoration: 'none', color: '#3B82F6', textAlign: 'center', padding: '8px 12px' }}
            >
              Open Swagger UI →
            </a>
          </Field>
        </SettingSection>

        {/* Email Settings */}
        <SettingSection title="📧 Email Configuration">
          <Field label="Sender Email" hint="Gmail address used to send results">
            <input
              className={styles.input}
              type="email"
              placeholder="your@gmail.com"
              value={state.settings.senderEmail || ''}
              onChange={(e) => update('senderEmail', e.target.value)}
            />
          </Field>
          <Field label="App Password" hint="Gmail App Password (not your regular password)">
            <div className={styles.passRow}>
              <input
                className={styles.input}
                type={showPass ? 'text' : 'password'}
                placeholder="xxxx xxxx xxxx xxxx"
                value={state.settings.appPassword || ''}
                onChange={(e) => update('appPassword', e.target.value)}
              />
              <button className={styles.showPassBtn} onClick={() => setShowPass(p => !p)}>
                {showPass ? '🙈' : '👁️'}
              </button>
            </div>
          </Field>

          <button
            className={styles.testBtn}
            onClick={testEmailConnection}
            disabled={testingEmail}
          >
            {testingEmail ? '⏳ Testing...' : '🔌 Test Email Connection'}
          </button>

          {emailStatus && (
            <div style={{
              marginTop: 8, padding: '8px 12px', borderRadius: 6, fontSize: 12,
              background: emailStatus === 'ok' ? '#F0FDF4' : '#FEF2F2',
              color:      emailStatus === 'ok' ? '#166534' : '#991B1B',
              border:     `1px solid ${emailStatus === 'ok' ? '#BBF7D0' : '#FECACA'}`,
            }}>
              {emailStatus === 'ok' ? '✅' : '❌'} {emailMsg}
            </div>
          )}
        </SettingSection>

        {/* NVIDIA NIM Settings */}
        <SettingSection title="🤖 NVIDIA NIM OCR">
          <Field label="NVIDIA API Key" hint="From build.nvidia.com — used for handwritten PDF OCR">
            <input
              className={styles.input}
              type="password"
              placeholder="nvapi-..."
              value={state.settings.nvidiaApiKey || ''}
              onChange={(e) => update('nvidiaApiKey', e.target.value)}
            />
          </Field>
          <Field label="Output Directory" hint="Where result files (Excel, JSON) will be saved on the server">
            <input
              className={styles.input}
              type="text"
              value={state.settings.outputDir || 'extracted_pdfs'}
              onChange={(e) => update('outputDir', e.target.value)}
            />
          </Field>
          <div style={{ fontSize: 11, color: '#6B7280', padding: '6px 0' }}>
            Model: <code>meta/llama-3.2-11b-vision-instruct</code>
            &nbsp;·&nbsp;Fallback: PyPDF2 (digital PDFs)
          </div>
        </SettingSection>

        {/* Evaluation Preferences */}
        <SettingSection title="⚙️ Evaluation Preferences">
          {[
            { key: 'useOCR',      label: 'Enable OCR Processing',         hint: 'For handwritten / scanned answer sheets' },
            { key: 'useSemantic', label: 'Semantic NLP Analysis',          hint: 'sentence-transformers (all-MiniLM-L6-v2)' },
            { key: 'sendEmails',  label: 'Auto-send Results via Email',    hint: 'Sends result email to each student' },
          ].map(opt => (
            <div key={opt.key} className={styles.toggleField}>
              <div>
                <div className={styles.toggleLabel}>{opt.label}</div>
                <div className={styles.toggleHint}>{opt.hint}</div>
              </div>
              <label className={styles.toggle}>
                <input
                  type="checkbox"
                  checked={state.settings[opt.key] || false}
                  onChange={(e) => update(opt.key, e.target.checked)}
                />
                <span className={styles.toggleSlider} />
              </label>
            </div>
          ))}
        </SettingSection>

        {/* Scoring Weights — read only */}
        <SettingSection title="📐 Scoring Weights (Read-only)">
          <div className={styles.weightInfo}>
            {[
              { label: 'Semantic Understanding',   val: '60%', color: '#16A34A' },
              { label: 'Keyword Coverage',          val: '25%', color: '#3B82F6' },
              { label: 'Structure & Completeness',  val: '10%', color: '#0D9488' },
              { label: 'Length Appropriateness',    val: '5%',  color: '#06B6D4' },
            ].map(w => (
              <div key={w.label} className={styles.weightRow}>
                <span className={styles.weightDot} style={{ background: w.color }} />
                <span className={styles.weightLabel}>{w.label}</span>
                <span className={styles.weightVal} style={{ color: w.color }}>{w.val}</span>
              </div>
            ))}
          </div>
          <div className={styles.markNote}>
            Main Questions: <strong>10 marks</strong> each · Sub-Questions: <strong>5 marks</strong> each
          </div>
        </SettingSection>

        {/* Result Files */}
        {resultFiles.length > 0 && (
          <SettingSection title="📁 Result Files on Server">
            <div style={{ maxHeight: 200, overflowY: 'auto' }}>
              {resultFiles.map((f, i) => (
                <div key={i} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '6px 0', borderBottom: '1px solid #F3F4F6' }}>
                  <div>
                    <div style={{ fontSize: 12, color: '#374151' }}>{f.name}</div>
                    <div style={{ fontSize: 11, color: '#9CA3AF' }}>{f.size_kb} KB</div>
                  </div>
                  <button
                    onClick={() => handleDownload(f.name)}
                    style={{ fontSize: 11, padding: '4px 10px', cursor: 'pointer', borderRadius: 4, border: '1px solid #3B82F6', color: '#3B82F6', background: '#EFF6FF' }}
                  >
                    📥 Download
                  </button>
                </div>
              ))}
            </div>
          </SettingSection>
        )}

        {/* Danger Zone */}
        <SettingSection title="⚠️ Danger Zone">
          <div className={styles.dangerRow}>
            <div>
              <div className={styles.dangerLabel}>Clear All Subjects</div>
              <div className={styles.dangerHint}>Removes all configured subjects and student data</div>
            </div>
            <button className={styles.dangerBtn} onClick={() => dispatch({ type: 'CLEAR_SUBJECTS' })}>
              🗑️ Clear
            </button>
          </div>
          <div className={styles.dangerRow}>
            <div>
              <div className={styles.dangerLabel}>Clear Evaluation Logs</div>
              <div className={styles.dangerHint}>Removes all evaluation and PDF processing logs</div>
            </div>
            <button className={styles.dangerBtn} onClick={() => {
              dispatch({ type: 'CLEAR_LOGS' });
              dispatch({ type: 'CLEAR_PDF_LOGS' });
            }}>
              🗑️ Clear
            </button>
          </div>
        </SettingSection>
      </div>
    </div>
  );
}