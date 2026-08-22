import { useState } from 'react';
import { useApp } from '../context/AppContext';
import { ocrAPI, evaluationAPI } from '../services/api';
import styles from './PDFTools.module.css';

export default function PDFTools() {
  const { state, dispatch } = useApp();

  const [processing,     setProcessing]     = useState(false);
  const [selectedFiles,  setSelectedFiles]  = useState([]);   // File[]
  const [dragging,       setDragging]       = useState(false);
  const [forceOcr,       setForceOcr]       = useState(false);
  const [results,        setResults]        = useState([]);   // OCR result objects
  const [resultFiles,    setResultFiles]    = useState([]);   // available downloads

  // ── Log helper ────────────────────────────────────────────────────────────
  function addLog(text) {
    dispatch({
      type: 'ADD_PDF_LOG',
      payload: { text, time: new Date().toLocaleTimeString() },
    });
  }

  // ── Process PDFs via real API ─────────────────────────────────────────────
  async function handleProcess() {
    if (!selectedFiles.length) return alert('Please select PDF files to process.');

    setProcessing(true);
    setResults([]);
    dispatch({ type: 'CLEAR_PDF_LOGS' });

    addLog('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
    addLog('🔍 Starting NVIDIA NIM OCR Processing...');
    addLog(`📂 Files: ${selectedFiles.length}`);
    addLog(`🔑 Force OCR: ${forceOcr ? 'YES' : 'NO (auto-detect)'}`);
    addLog('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');

    try {
      const batchResults = [];

      if (selectedFiles.length === 1) {
        // ── Single file ───────────────────────────────────────────────────
        const f = selectedFiles[0];
        addLog(`\n📄 Processing: ${f.name}`);
        addLog('   📡 Uploading to FastAPI /ocr/extract-text...');

        const data = await ocrAPI.extractText(f, forceOcr, (line) => addLog(`   ${line}`));

        addLog(`   ✅ Method: ${data.method_used}`);
        addLog(`   📊 Extracted: ${data.char_count} characters`);
        batchResults.push({ filename: data.filename, method: data.method_used, chars: data.char_count, text: data.text });

      } else {
        // ── Batch ─────────────────────────────────────────────────────────
        addLog(`\n📡 Uploading ${selectedFiles.length} files to /ocr/extract-text-batch...`);
        const data = await ocrAPI.extractBatch(selectedFiles, forceOcr);

        data.results.forEach(r => {
          const icon = r.success ? '✅' : '❌';
          addLog(`${icon} ${r.filename} — ${r.char_count} chars via ${r.method_used}`);
          batchResults.push({ filename: r.filename, method: r.method_used, chars: r.char_count, text: r.text, success: r.success });
        });
      }

      setResults(batchResults);

      // Generate local .txt downloads from extracted text
      addLog('\n📝 Generating text file(s) for download...');
      generateTextFiles(batchResults);

      // Refresh downloadable result files list from server (best-effort)
      try {
        const listData = await evaluationAPI.listResults();
        // Merge server files with locally generated ones (keep local ones too)
        setResultFiles((prev) => {
          const serverFiles = (listData.files || []).map((f) => ({ ...f, isLocal: false }));
          const localFiles  = prev.filter((f) => f.isLocal);
          // Deduplicate by name, preferring local
          const localNames  = new Set(localFiles.map((f) => f.name));
          return [...localFiles, ...serverFiles.filter((f) => !localNames.has(f.name))];
        });
      } catch (_) {}

      addLog('\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
      addLog('🎉 OCR Processing Complete!');
      addLog(`✅ Processed: ${batchResults.length} file(s)`);
      addLog(`📁 Output directory: ${state.settings.outputDir || 'extracted_pdfs'}`);
      addLog('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');

    } catch (err) {
      addLog(`\n❌ Error: ${err.message}`);
      addLog('💡 Is the backend running? uvicorn main:app --reload');
    } finally {
      setProcessing(false);
    }
  }

  // ── Drag-and-drop ─────────────────────────────────────────────────────────
  function handleDrop(e) {
    e.preventDefault();
    setDragging(false);
    const files = Array.from(e.dataTransfer.files).filter(f => f.name.endsWith('.pdf'));
    setSelectedFiles(prev => [...prev, ...files]);
  }

  // ── Download result file ──────────────────────────────────────────────────
  async function handleDownload(file) {
    if (file.isLocal && file.url) {
      // Local blob — trigger browser download directly
      const a = document.createElement('a');
      a.href = file.url;
      a.download = file.name;
      a.click();
      return;
    }
    try {
      await evaluationAPI.downloadFile(file.name);
    } catch (err) {
      alert(`Download failed: ${err.message}`);
    }
  }

  // ── Copy extracted text to clipboard ─────────────────────────────────────
  function copyText(text) {
    navigator.clipboard.writeText(text).then(() => alert('Copied to clipboard!'));
  }

  // ── Generate .txt file(s) from extracted text and add to Result Files ─────
  function generateTextFiles(batchResults) {
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19);
    const isBatch = batchResults.length > 1;

    batchResults.forEach((r) => {
      const baseName = r.filename.replace(/\.pdf$/i, '');
      const fileName = isBatch
        ? `${baseName}_extracted_${timestamp}.txt`
        : `${baseName}_extracted.txt`;

      const header = [
        '═══════════════════════════════════════════════════',
        `FILE    : ${r.filename}`,
        `METHOD  : ${r.method}`,
        `CHARS   : ${r.chars}`,
        `EXPORTED: ${new Date().toLocaleString()}`,
        '═══════════════════════════════════════════════════',
        '',
      ].join('\n');

      const content = header + (r.text || '');
      const blob = new Blob([content], { type: 'text/plain;charset=utf-8' });
      const sizeKb = (blob.size / 1024).toFixed(1);
      const url = URL.createObjectURL(blob);

      setResultFiles((prev) => [
        // replace if same name already exists (re-run scenario)
        ...prev.filter((f) => f.name !== fileName),
        { name: fileName, size_kb: sizeKb, url, isLocal: true },
      ]);

      addLog(`   📝 Text file ready: ${fileName} (${sizeKb} KB)`);
    });
  }

  return (
    <div className={styles.page}>
      <div className={styles.header}>
        <div>
          <h1 className={styles.title}>PDF Tools</h1>
          <p className={styles.subtitle}>OCR extraction via NVIDIA NIM + text recognition</p>
        </div>
        <div className={styles.apiStatus}>
          <span className={styles.apiDot} />
          <span>NVIDIA NIM OCR</span>
        </div>
      </div>

      <div className={styles.layout}>
        {/* ── Upload Section ─────────────────────────────────────────────── */}
        <div className={styles.uploadSection}>
          <div className={styles.card}>
            <div className={styles.cardTitle}>📂 Upload PDFs for OCR</div>
            <div
              className={`${styles.dropZone} ${dragging ? styles.dragging : ''}`}
              onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
              onDragLeave={() => setDragging(false)}
              onDrop={handleDrop}
              onClick={() => document.getElementById('pdf-upload').click()}
            >
              <input
                id="pdf-upload"
                type="file"
                accept=".pdf"
                multiple
                style={{ display: 'none' }}
                onChange={(e) => setSelectedFiles(prev => [...prev, ...Array.from(e.target.files)])}
              />
              <div className={styles.dropContent}>
                <span className={styles.dropIcon}>📄</span>
                <p className={styles.dropMain}>Drop PDF files here</p>
                <p className={styles.dropSub}>or click to browse · Multiple files supported</p>
              </div>
            </div>

            {selectedFiles.length > 0 && (
              <div className={styles.fileList}>
                <div className={styles.fileListHeader}>
                  <span>{selectedFiles.length} file(s) selected</span>
                  <button className={styles.clearFilesBtn} onClick={() => setSelectedFiles([])}>
                    Clear All
                  </button>
                </div>
                {selectedFiles.map((f, i) => (
                  <div key={i} className={styles.fileItem}>
                    <span className={styles.fileIcon}>📄</span>
                    <div className={styles.fileInfo}>
                      <span className={styles.fileName}>{f.name}</span>
                      <span className={styles.fileSize}>{(f.size / 1024).toFixed(1)} KB</span>
                    </div>
                    <button
                      className={styles.removeFileBtn}
                      onClick={() => setSelectedFiles(prev => prev.filter((_, j) => j !== i))}
                    >×</button>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* OCR Settings */}
          <div className={styles.card}>
            <div className={styles.cardTitle}>🔧 OCR Settings</div>

            <div className={styles.settingRow}>
              <label className={styles.settingLabel}>Output Directory</label>
              <input
                className={styles.settingInput}
                type="text"
                value={state.settings.outputDir || 'extracted_pdfs'}
                onChange={(e) =>
                  dispatch({ type: 'UPDATE_SETTINGS', payload: { outputDir: e.target.value } })
                }
              />
            </div>

            <div className={styles.settingRow}>
              <label className={styles.settingLabel}>Force OCR</label>
              <label style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer' }}>
                <input
                  type="checkbox"
                  checked={forceOcr}
                  onChange={(e) => setForceOcr(e.target.checked)}
                />
                <span style={{ fontSize: 12, color: '#6B7280' }}>
                  Always use NVIDIA NIM (skip PyPDF2 fast-path)
                </span>
              </label>
            </div>

            <div style={{ marginTop: 8, padding: '8px 10px', background: '#F0FDF4', borderRadius: 6, fontSize: 11, color: '#166534' }}>
              <strong>Engine:</strong> NVIDIA NIM <code>llama-3.2-11b-vision-instruct</code>
              <br />
              <strong>Fallback:</strong> PyPDF2 (digital PDFs)
            </div>
          </div>

          <button
            className={`${styles.processBtn} ${processing ? styles.processing : ''}`}
            onClick={handleProcess}
            disabled={processing}
          >
            {processing
              ? <><span className={styles.spinner} /> Processing OCR...</>
              : '🔍 Process PDFs with OCR'
            }
          </button>

          {/* OCR Results Preview */}
          {results.length > 0 && (
            <div className={styles.card} style={{ marginTop: 12 }}>
              <div className={styles.cardTitle}>📋 Extraction Results</div>
              {results.map((r, i) => (
                <div key={i} style={{ marginBottom: 12, padding: '10px 12px', background: '#F9FAFB', borderRadius: 8, border: '1px solid #E5E7EB' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
                    <strong style={{ fontSize: 12 }}>📄 {r.filename}</strong>
                    <span style={{ fontSize: 11, color: '#6B7280' }}>{r.method} · {r.chars} chars</span>
                  </div>
                  <div style={{
                    fontSize: 11, color: '#374151', maxHeight: 80, overflowY: 'auto',
                    fontFamily: 'monospace', whiteSpace: 'pre-wrap', background: '#fff',
                    padding: 6, borderRadius: 4, border: '1px solid #E5E7EB',
                  }}>
                    {(r.text || '').slice(0, 400)}{r.text?.length > 400 ? '…' : ''}
                  </div>
                  <button
                    onClick={() => copyText(r.text)}
                    style={{ marginTop: 6, fontSize: 11, padding: '3px 10px', cursor: 'pointer', borderRadius: 4, border: '1px solid #D1D5DB', background: '#fff' }}
                  >
                    📋 Copy Text
                  </button>
                </div>
              ))}
            </div>
          )}

          {/* Downloadable files list */}
          {resultFiles.length > 0 && (
            <div className={styles.card} style={{ marginTop: 12 }}>
              <div className={styles.cardTitle}>📁 Result Files</div>
              {resultFiles.map((f, i) => (
                <div key={i} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '6px 0', borderBottom: '1px solid #F3F4F6' }}>
                  <div>
                    <div style={{ fontSize: 12, color: '#374151' }}>{f.name}</div>
                    <div style={{ fontSize: 11, color: '#9CA3AF' }}>{f.size_kb} KB</div>
                  </div>
                  <button
                    onClick={() => handleDownload(f)}
                    style={{ fontSize: 11, padding: '4px 10px', cursor: 'pointer', borderRadius: 4, border: '1px solid #16A34A', color: '#16A34A', background: '#F0FDF4' }}
                  >
                    📥 Download
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* ── Log Panel ─────────────────────────────────────────────────── */}
        <div className={styles.logPanel}>
          <div className={styles.logHeader}>
            <span className={styles.logTitle}>📜 OCR Processing Log</span>
            <button className={styles.logClearBtn} onClick={() => dispatch({ type: 'CLEAR_PDF_LOGS' })}>
              Clear
            </button>
          </div>
          <div className={styles.logBody}>
            {state.pdfLogs.length === 0 ? (
              <div className={styles.logEmpty}>
                <span>📄</span>
                <p>OCR log will appear here after processing starts</p>
                <small style={{ color: '#9CA3AF', marginTop: 8 }}>
                  API: <code>http://127.0.0.1:8000/ocr/extract-text</code>
                </small>
              </div>
            ) : (
              state.pdfLogs.map((entry, i) => {
                const isOk     = entry.text.includes('✅') || entry.text.includes('🎉');
                const isErr    = entry.text.includes('❌');
                const isBorder = entry.text.startsWith('━');
                return (
                  <div
                    key={i}
                    className={[
                      styles.logEntry,
                      isOk     ? styles.logOk     : '',
                      isErr    ? styles.logErr    : '',
                      isBorder ? styles.logBorder : '',
                    ].join(' ')}
                  >
                    <span className={styles.logTs}>{entry.time}</span>
                    <span className={styles.logText}>{entry.text}</span>
                  </div>
                );
              })
            )}
          </div>
        </div>
      </div>
    </div>
  );
}