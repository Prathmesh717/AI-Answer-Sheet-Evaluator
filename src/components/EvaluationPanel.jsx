import { useState, useRef } from 'react';
import { useApp } from '../context/AppContext';
import { evaluationAPI, evaluationsAPI } from '../services/api';
import styles from './EvaluationPanel.module.css';

const SCORE_WEIGHTS = [
  { label: 'Semantic Understanding',   weight: 60, color: '#16A34A' },
  { label: 'Keyword Coverage',         weight: 25, color: '#3B82F6' },
  { label: 'Structure & Completeness', weight: 10, color: '#0D9488' },
  { label: 'Length Appropriateness',   weight: 5,  color: '#06B6D4' },
];

function WeightBar({ label, weight, color }) {
  return (
    <div className={styles.weightRow}>
      <span className={styles.weightLabel}>{label}</span>
      <div className={styles.weightBarWrap}>
        <div
          className={styles.weightBarFill}
          style={{ width: `${weight}%`, background: color, boxShadow: `0 0 10px ${color}66` }}
        />
      </div>
      <span className={styles.weightPct} style={{ color }}>{weight}%</span>
    </div>
  );
}

function LogEntry({ entry }) {
  const isSuccess = entry.text.includes('✅') || entry.text.includes('📊') || entry.text.includes('🎯');
  const isError   = entry.text.includes('❌') || entry.text.includes('⚠️');
  const isHeader  = entry.text.startsWith('=') || entry.text.startsWith('━') || entry.text.startsWith('─');

  return (
    <div
      className={[
        styles.logEntry,
        isSuccess ? styles.logSuccess : '',
        isError   ? styles.logError   : '',
        isHeader  ? styles.logHeader  : '',
      ].join(' ')}
    >
      <span className={styles.logTs}>{entry.time}</span>
      <span className={styles.logText}>{entry.text}</span>
    </div>
  );
}

export default function EvaluationPanel() {
  const { state, dispatch } = useApp();

  const [running,  setRunning]  = useState(false);
  const [progress, setProgress] = useState(0);
  const [results,  setResults]  = useState([]);   // latest batch results
  const [error,    setError]    = useState('');
  const abortRef = useRef(false);

  // ── Utility: push a log line ───────────────────────────────────────────────
  function addLog(text) {
    dispatch({
      type: 'ADD_LOG',
      payload: { text, time: new Date().toLocaleTimeString() },
    });
  }

  // ── Main evaluate handler ──────────────────────────────────────────────────
  async function handleEvaluate() {
    if (!state.subjects.length) {
      return alert('Please add at least one subject in Subject Manager.');
    }

    // Validate that all subjects have actual File objects
    for (const s of state.subjects) {
      if (!(s.masterPdf instanceof File)) {
        return alert(`Subject "${s.name}": Please re-upload the master PDF in Subject Manager (page reload clears file objects).`);
      }
      if (!s.studentPdfs?.length || !(s.studentPdfs[0] instanceof File)) {
        return alert(`Subject "${s.name}": Please re-upload student PDFs in Subject Manager.`);
      }
    }

    setRunning(true);
    setProgress(0);
    setError('');
    setResults([]);
    abortRef.current = false;
    dispatch({ type: 'CLEAR_LOGS' });

    addLog('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
    addLog('🚀 Connecting to FastAPI backend: http://127.0.0.1:8000');
    addLog(`📚 Subjects queued: ${state.subjects.length}`);
    addLog(`⚙️  Send emails after: ${state.settings.sendEmails ? 'YES' : 'NO'}`);
    addLog('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');

    try {
      let allResults = [];
      let consolidatedFile = null;

      if (state.subjects.length === 1) {
        // ── Single subject ──────────────────────────────────────────────────
        const s = state.subjects[0];
        addLog(`\n📖 Processing: ${s.name}`);
        addLog(`   Master: ${s.masterPdf.name}`);
        addLog(`   Students: ${s.studentPdfs.length} file(s)`);
        addLog('   📡 Uploading to FastAPI...');

        const data = await evaluationAPI.evaluateSubject(
          s.name,
          s.masterPdf,
          s.studentPdfs,
          state.settings.sendEmails,
          (line) => addLog(`   ${line}`),
        );

        setProgress(80);
        allResults = data.results || [];
        consolidatedFile = data.results_file;

        addLog(`\n✅ Evaluation complete — ${allResults.length} student(s) graded`);
        if (data.results_file) {
          addLog(`💾 Results saved: ${data.results_file}`);
        }
        if (data.email_status === 'queued') {
          addLog('📧 Emails queued for dispatch');
        }

      } else {
        // ── Batch (up to 3 subjects) ────────────────────────────────────────
        addLog('📡 Uploading batch to FastAPI /evaluation/evaluate-batch...');

        const batchData = await evaluationAPI.evaluateBatch(
          state.subjects,
          state.settings.sendEmails,
          (line) => addLog(`   ${line}`),
        );

        setProgress(80);
        allResults = batchData.results || [];
        consolidatedFile = batchData.consolidated_file;

        addLog(`\n✅ Batch complete — ${batchData.subjects_evaluated?.length || 0} subject(s), ${batchData.total_students || 0} student(s)`);
        if (batchData.consolidated_file) {
          addLog(`💾 Consolidated: ${batchData.consolidated_file}`);
        }
        if (batchData.email_status === 'queued') {
          addLog('📧 Emails queued for dispatch');
        }
      }

      // ── Print per-student summary ─────────────────────────────────────────
      if (allResults.length) {
        addLog('\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
        addLog('📊 RESULTS SUMMARY');
        addLog('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
        allResults.forEach(r => {
          const emoji = r.Grade === 'A+' || r.Grade === 'A' ? '🌟' :
                        r.Grade === 'B+' || r.Grade === 'B' ? '👍' :
                        r.Grade === 'F' ? '❌' : '📘';
          addLog(
            `${emoji} ${r.Name} (${r['Roll No']}) — ` +
            `${r['Total Marks']}/${r['Max Possible']} (${r.Percentage}%) — Grade: ${r.Grade}`
          );
        });

        // Store consolidated file path for downloads
        if (consolidatedFile) {
          dispatch({ type: 'SET_RESULTS_FILE', payload: consolidatedFile });
        }
        setResults(allResults);

        // ── Persist each graded result to MongoDB so it shows up in Analytics ──
        addLog('\n💾 Saving results to database...');
        let savedCount = 0;
        for (const r of allResults) {
          try {
            await evaluationsAPI.save({
              subject_name:    r.Subject,
              student_name:    r.Name,
              student_roll_no: r['Roll No'],
              student_email:   r.Email || null,
              total_marks:     r['Total Marks'],
              max_marks:       r['Max Possible'],
              percentage:      r.Percentage,
              grade:           r.Grade,
              question_results: [],
              metadata: {},
            });
            savedCount++;
          } catch (saveErr) {
            addLog(`   ⚠️  Failed to save record for ${r.Name}: ${saveErr.message}`);
          }
        }
        addLog(`✅ Saved ${savedCount}/${allResults.length} record(s) to database`);
      }

      addLog('\n🎉 Evaluation Complete!');
      setProgress(100);

    } catch (err) {
      setError(err.message);
      addLog(`\n❌ Error: ${err.message}`);
      addLog('💡 Tip: Make sure the backend is running at http://127.0.0.1:8000');
    } finally {
      setRunning(false);
    }
  }

  // ── Download last results file ─────────────────────────────────────────────
  async function handleDownload() {
    if (!state.resultsFile) return alert('No results file available yet. Run evaluation first.');
    try {
      const filename = state.resultsFile.split(/[\\/]/).pop();
      await evaluationAPI.downloadFile(filename);
    } catch (err) {
      alert(`Download failed: ${err.message}`);
    }
  }

  // ── Save log as .txt ───────────────────────────────────────────────────────
  function saveLog() {
    const text = state.evaluationLogs.map(l => `[${l.time}] ${l.text}`).join('\n');
    const blob = new Blob([text], { type: 'text/plain' });
    const url  = URL.createObjectURL(blob);
    const a    = document.createElement('a');
    a.href = url;
    a.download = `evaluation_log_${Date.now()}.txt`;
    a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div className={styles.page}>
      <div className={styles.header}>
        <div>
          <h1 className={styles.title}>Evaluation Engine</h1>
          <p className={styles.subtitle}>FAIR multi-subject scoring via FastAPI + NVIDIA NIM OCR</p>
        </div>
        <div className={styles.nlpBadge}>
          <span className={styles.nlpDot} />
          <span>FastAPI Connected</span>
        </div>
      </div>

      <div className={styles.layout}>
        {/* ── Left sidebar ─────────────────────────────────────────────── */}
        <div className={styles.sidebar}>
          {/* Scoring Weights */}
          <div className={styles.card}>
            <div className={styles.cardTitle}>⚖️ Scoring Weights</div>
            <div className={styles.weightList}>
              {SCORE_WEIGHTS.map(w => <WeightBar key={w.label} {...w} />)}
            </div>
            <div className={styles.markScheme}>
              <div className={styles.markItem}>
                <span>Main Questions (Q1, Q2…)</span>
                <span className={styles.markVal}>10 marks</span>
              </div>
              <div className={styles.markItem}>
                <span>Sub-Questions (Q1a, Q2b…)</span>
                <span className={styles.markVal}>5 marks</span>
              </div>
            </div>
          </div>

          {/* Options */}
          <div className={styles.card}>
            <div className={styles.cardTitle}>⚙️ Options</div>
            <div className={styles.optionList}>
              {[
                { key: 'useOCR',      label: 'Use OCR for handwritten sheets', hint: 'NVIDIA NIM llama-3.2-11b-vision' },
                { key: 'useSemantic', label: 'Semantic NLP Analysis',           hint: 'sentence-transformers (all-MiniLM-L6-v2)' },
                { key: 'sendEmails',  label: 'Send results via Email',          hint: 'Gmail SMTP / App Password' },
              ].map(opt => (
                <label key={opt.key} className={styles.optionRow}>
                  <div className={styles.toggle}>
                    <input
                      type="checkbox"
                      checked={state.settings[opt.key]}
                      onChange={(e) =>
                        dispatch({ type: 'UPDATE_SETTINGS', payload: { [opt.key]: e.target.checked } })
                      }
                    />
                    <span className={styles.toggleSlider} />
                  </div>
                  <div className={styles.optionText}>
                    <span className={styles.optionLabel}>{opt.label}</span>
                    <span className={styles.optionHint}>{opt.hint}</span>
                  </div>
                </label>
              ))}
            </div>
          </div>

          {/* Queued Subjects */}
          <div className={styles.card}>
            <div className={styles.cardTitle}>📋 Queued Subjects</div>
            {state.subjects.length === 0
              ? <p className={styles.emptySub}>No subjects configured. Go to Subject Manager.</p>
              : state.subjects.map((s, i) => (
                <div key={i} className={styles.queueItem}>
                  <span className={styles.queueNum}>{i + 1}</span>
                  <div>
                    <div className={styles.queueName}>{s.name}</div>
                    <div className={styles.queueMeta}>
                      {(s.studentPdfs?.length || 0)} student(s)
                      {s.masterPdf instanceof File ? '' : ' ⚠️ re-upload needed'}
                    </div>
                  </div>
                </div>
              ))
            }
          </div>

          {/* Run Button */}
          <button
            className={`${styles.runBtn} ${running ? styles.running : ''}`}
            onClick={handleEvaluate}
            disabled={running}
          >
            {running
              ? <><span className={styles.spinner} />Evaluating...</>
              : <>🚀 Start Evaluation</>
            }
          </button>

          {/* Download Results */}
          {state.resultsFile && !running && (
            <button className={styles.downloadBtn} onClick={handleDownload}>
              📥 Download Results (.xlsx)
            </button>
          )}

          {/* Progress */}
          {(running || state.evaluationLogs.length > 0) && (
            <div className={styles.progressWrap}>
              <div className={styles.progressTrack}>
                <div className={styles.progressFill} style={{ width: `${progress}%` }} />
              </div>
              <span className={styles.progressPct}>{progress}%</span>
            </div>
          )}

          {/* Error */}
          {error && (
            <div className={styles.errorBox}>
              <strong>❌ Error</strong>
              <p>{error}</p>
              <small>Is the backend running? <code>uvicorn main:app --reload</code></small>
            </div>
          )}

          {/* Quick results table */}
          {results.length > 0 && (
            <div className={styles.card} style={{ marginTop: 12 }}>
              <div className={styles.cardTitle}>📊 Quick Results</div>
              <div style={{ overflowX: 'auto' }}>
                <table style={{ width: '100%', fontSize: 11, borderCollapse: 'collapse' }}>
                  <thead>
                    <tr style={{ borderBottom: '1px solid #E5E7EB' }}>
                      <th style={{ textAlign: 'left', padding: '4px 6px', color: '#6B7280' }}>Name</th>
                      <th style={{ textAlign: 'right', padding: '4px 6px', color: '#6B7280' }}>%</th>
                      <th style={{ textAlign: 'right', padding: '4px 6px', color: '#6B7280' }}>Grade</th>
                    </tr>
                  </thead>
                  <tbody>
                    {results.map((r, i) => (
                      <tr key={i} style={{ borderBottom: '1px solid #F3F4F6' }}>
                        <td style={{ padding: '4px 6px' }}>{r.Name}</td>
                        <td style={{ padding: '4px 6px', textAlign: 'right' }}>{r.Percentage}%</td>
                        <td style={{
                          padding: '4px 6px', textAlign: 'right', fontWeight: 700,
                          color: r.Grade === 'A+' || r.Grade === 'A' ? '#16A34A' :
                                 r.Grade === 'F' ? '#EF4444' : '#3B82F6',
                        }}>{r.Grade}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>

        {/* ── Right: Log Panel ──────────────────────────────────────────── */}
        <div className={styles.logPanel}>
          <div className={styles.logHeader}>
            <span className={styles.logTitle}>📜 Evaluation Log</span>
            <div className={styles.logActions}>
              <button className={styles.logActionBtn} onClick={() => dispatch({ type: 'CLEAR_LOGS' })}>
                Clear
              </button>
              <button className={styles.logActionBtn} onClick={saveLog} disabled={!state.evaluationLogs.length}>
                💾 Save Log
              </button>
            </div>
          </div>
          <div className={styles.logBody}>
            {state.evaluationLogs.length === 0
              ? <div className={styles.logEmpty}>
                  <span>▶</span>
                  <p>Evaluation log will appear here once started</p>
                  <small style={{ color: '#9CA3AF', marginTop: 8 }}>
                    Backend: <code>http://127.0.0.1:8000</code>
                  </small>
                </div>
              : state.evaluationLogs.map((entry, i) => (
                  <LogEntry key={i} entry={entry} />
                ))
            }
          </div>
        </div>
      </div>
    </div>
  );
}