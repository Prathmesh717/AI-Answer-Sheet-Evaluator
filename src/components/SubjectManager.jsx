import { useState } from 'react';
import { useApp } from '../context/AppContext';
import styles from './SubjectManager.module.css';

const SUBJECT_PRESETS = [
  'Software Engineering',
  'Cyber Security',
  'Artificial Intelligence',
  'Blockchain Technology',
  'Constitutional Law',
  'Data Structures',
  'Computer Networks',
  'Database Management',
];

function FileDropZone({ label, accept, multiple, value, onChange, placeholder }) {
  const [dragging, setDragging] = useState(false);

  function handleDrop(e) {
    e.preventDefault();
    setDragging(false);
    const files = Array.from(e.dataTransfer.files).filter(f => f.name.endsWith('.pdf'));
    if (files.length) onChange(multiple ? files : files[0]);
  }

  return (
    <div
      className={`${styles.dropZone} ${dragging ? styles.dragging : ''}`}
      onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
      onDragLeave={() => setDragging(false)}
      onDrop={handleDrop}
      onClick={() => document.getElementById(`fz-${label.replace(/\s/g, '-')}`).click()}
    >
      <input
        id={`fz-${label.replace(/\s/g, '-')}`}
        type="file"
        accept={accept || '.pdf'}
        multiple={multiple}
        style={{ display: 'none' }}
        onChange={(e) => {
          const files = Array.from(e.target.files);
          onChange(multiple ? files : files[0]);
        }}
      />
      <span className={styles.dropIcon}>📂</span>
      {value
        ? <span className={styles.dropValue}>
            {multiple
              ? `${value.length} PDF(s) selected`
              : (value.name || value)}
          </span>
        : <span className={styles.dropPlaceholder}>{placeholder || 'Drop PDF or click to browse'}</span>
      }
    </div>
  );
}

export default function SubjectManager() {
  const { state, dispatch } = useApp();

  const [form, setForm] = useState({
    name: '',
    masterPdf: null,       // File object
    studentPdfs: [],       // File[] objects
  });
  const [editIndex, setEditIndex]   = useState(null);
  const [showPresets, setShowPresets] = useState(false);

  // ── Add / Update subject (stores actual File objects) ────────────────────
  function handleAdd() {
    if (!form.name.trim())   return alert('Please enter a subject name.');
    if (!form.masterPdf)     return alert('Please upload a master answer sheet.');
    if (!form.studentPdfs.length) return alert('Please upload at least one student PDF.');

    const subject = {
      name:        form.name,
      masterPdf:   form.masterPdf,                    // File object — used by EvaluationPanel
      studentPdfs: form.studentPdfs,                  // File[] objects
      // Display-only copies:
      masterPdfName:   form.masterPdf.name,
      studentPdfNames: form.studentPdfs.map(f => f.name),
      addedAt: new Date().toLocaleTimeString(),
    };

    if (editIndex !== null) {
      dispatch({ type: 'UPDATE_SUBJECT', payload: { index: editIndex, data: subject } });
      setEditIndex(null);
    } else {
      dispatch({ type: 'ADD_SUBJECT', payload: subject });
    }

    setForm({ name: '', masterPdf: null, studentPdfs: [] });
  }

  function handleEdit(idx) {
    const s = state.subjects[idx];
    setForm({
      name:        s.name,
      masterPdf:   s.masterPdf,
      studentPdfs: s.studentPdfs,
    });
    setEditIndex(idx);
  }

  function handleRemove(idx) {
    dispatch({ type: 'REMOVE_SUBJECT', payload: idx });
  }

  function handlePreset(preset) {
    setForm(f => ({ ...f, name: preset }));
    setShowPresets(false);
  }

  // ── CSV import (reads CSV and pre-fills subject names) ──────────────────
  function handleImportCSV() {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = '.csv';
    input.onchange = (e) => {
      const file = e.target.files[0];
      if (!file) return;
      const reader = new FileReader();
      reader.onload = (ev) => {
        const lines = ev.target.result.split('\n').filter(Boolean);
        lines.slice(1).forEach(line => {      // skip header
          const cols = line.split(',');
          const name = cols[0]?.trim();
          if (name) {
            dispatch({
              type: 'ADD_SUBJECT',
              payload: {
                name,
                masterPdf: null,
                studentPdfs: [],
                masterPdfName: '(not uploaded)',
                studentPdfNames: [],
                addedAt: new Date().toLocaleTimeString(),
              },
            });
          }
        });
        alert(`Imported ${lines.length - 1} subject name(s) from CSV. Please upload PDFs for each.`);
      };
      reader.readAsText(file);
    };
    input.click();
  }

  // ── CSV export ────────────────────────────────────────────────────────────
  function handleExportCSV() {
    const rows = [['Subject_Name', 'Master_PDF', 'Student_Count']];
    state.subjects.forEach(s => {
      rows.push([s.name, s.masterPdfName || '', (s.studentPdfNames || []).length]);
    });
    const csv = rows.map(r => r.join(',')).join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url  = URL.createObjectURL(blob);
    const a    = document.createElement('a');
    a.href = url;
    a.download = 'subjects.csv';
    a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div className={styles.page}>
      {/* Page Header */}
      <div className={styles.header}>
        <div>
          <h1 className={styles.title}>Subject Manager</h1>
          <p className={styles.subtitle}>Configure subjects, upload master sheets &amp; manage student PDFs</p>
        </div>
        <div className={styles.headerStat}>
          <span className={styles.statNum}>{state.subjects.length}</span>
          <span className={styles.statLabel}>Subjects</span>
        </div>
      </div>

      <div className={styles.layout}>
        {/* Left: Subject List */}
        <div className={styles.listPanel}>
          <div className={styles.panelHeader}>
            <span className={styles.panelTitle}>📋 Subjects List</span>
            <button className={styles.clearBtn} onClick={() => dispatch({ type: 'CLEAR_SUBJECTS' })}>
              Clear All
            </button>
          </div>

          {state.subjects.length === 0 ? (
            <div className={styles.emptyState}>
              <span className={styles.emptyIcon}>📭</span>
              <p>No subjects added yet</p>
              <p className={styles.emptyHint}>Add your first subject using the form →</p>
            </div>
          ) : (
            <ul className={styles.subjectList}>
              {state.subjects.map((subject, idx) => (
                <li key={idx} className={styles.subjectCard}>
                  <div className={styles.subjectCardTop}>
                    <div className={styles.subjectIndex}>{String(idx + 1).padStart(2, '0')}</div>
                    <div className={styles.subjectInfo}>
                      <span className={styles.subjectName}>{subject.name}</span>
                      <span className={styles.subjectMeta}>
                        Master: {subject.masterPdfName || subject.masterPdf?.name || '—'}
                        &nbsp;·&nbsp;
                        {(subject.studentPdfNames || subject.studentPdfs || []).length} student(s)
                      </span>
                    </div>
                    <div className={styles.subjectActions}>
                      <button className={styles.editBtn}   onClick={() => handleEdit(idx)}>✏️</button>
                      <button className={styles.removeBtn} onClick={() => handleRemove(idx)}>🗑️</button>
                    </div>
                  </div>
                  <div className={styles.subjectTags}>
                    {(subject.studentPdfNames || subject.studentPdfs?.map(f => f.name) || [])
                      .slice(0, 3)
                      .map((name, i) => (
                        <span key={i} className={styles.pdfTag}>{name}</span>
                      ))}
                    {(subject.studentPdfNames || subject.studentPdfs || []).length > 3 && (
                      <span className={styles.pdfTagMore}>
                        +{(subject.studentPdfNames || subject.studentPdfs).length - 3} more
                      </span>
                    )}
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>

        {/* Right: Add / Edit Form */}
        <div className={styles.formPanel}>
          <div className={styles.panelHeader}>
            <span className={styles.panelTitle}>
              {editIndex !== null ? '✏️ Edit Subject' : '➕ Add New Subject'}
            </span>
            {editIndex !== null && (
              <button
                className={styles.cancelBtn}
                onClick={() => { setEditIndex(null); setForm({ name: '', masterPdf: null, studentPdfs: [] }); }}
              >
                Cancel
              </button>
            )}
          </div>

          <div className={styles.formBody}>
            {/* Subject Name */}
            <div className={styles.formGroup}>
              <label className={styles.label}>Subject Name</label>
              <div className={styles.nameRow}>
                <input
                  className={styles.input}
                  type="text"
                  placeholder="e.g. Software Engineering"
                  value={form.name}
                  onChange={(e) => setForm(f => ({ ...f, name: e.target.value }))}
                />
                <button className={styles.presetBtn} onClick={() => setShowPresets(p => !p)}>
                  Presets ▾
                </button>
              </div>
              {showPresets && (
                <div className={styles.presetDropdown}>
                  {SUBJECT_PRESETS.map(p => (
                    <button key={p} className={styles.presetItem} onClick={() => handlePreset(p)}>
                      {p}
                    </button>
                  ))}
                </div>
              )}
            </div>

            {/* Master PDF */}
            <div className={styles.formGroup}>
              <label className={styles.label}>Master Answer Sheet (PDF)</label>
              <FileDropZone
                label="master-pdf"
                value={form.masterPdf}
                onChange={(f) => setForm(prev => ({ ...prev, masterPdf: f }))}
                placeholder="Drop master answer sheet PDF here"
              />
            </div>

            {/* Student PDFs */}
            <div className={styles.formGroup}>
              <label className={styles.label}>
                Student Answer Sheets
                <span className={styles.labelMeta}> ({form.studentPdfs.length} files)</span>
              </label>
              <FileDropZone
                label="student-pdfs"
                multiple
                value={form.studentPdfs.length ? form.studentPdfs : null}
                onChange={(files) => setForm(prev => ({ ...prev, studentPdfs: [...prev.studentPdfs, ...files] }))}
                placeholder="Drop multiple student PDF files here"
              />
              {form.studentPdfs.length > 0 && (
                <div className={styles.studentPdfList}>
                  {form.studentPdfs.map((f, i) => (
                    <div key={i} className={styles.studentPdfItem}>
                      <span>📄 {f.name}</span>
                      <button
                        className={styles.removePdfBtn}
                        onClick={() => setForm(prev => ({
                          ...prev,
                          studentPdfs: prev.studentPdfs.filter((_, j) => j !== i),
                        }))}
                      >×</button>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Submit */}
            <div className={styles.formActions}>
              <button className={styles.primaryBtn} onClick={handleAdd}>
                {editIndex !== null ? '✅ Update Subject' : '➕ Add Subject'}
              </button>
              <button
                className={styles.secondaryBtn}
                onClick={() => setForm({ name: '', masterPdf: null, studentPdfs: [] })}
              >
                Reset
              </button>
            </div>

            {/* CSV Actions */}
            <div className={styles.csvActions}>
              <button className={styles.csvBtn} onClick={handleImportCSV}>📥 Import from CSV</button>
              <button className={styles.csvBtn} onClick={handleExportCSV}>📤 Export to CSV</button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}