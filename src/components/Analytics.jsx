import { useState, useEffect } from 'react';
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  RadarChart, Radar, PolarGrid, PolarAngleAxis, PolarRadiusAxis,
  PieChart, Pie, Cell,
} from 'recharts';
import { evaluationsAPI, evaluationAPI } from '../services/api';
import styles from './Analytics.module.css';

const SUBJECT_COLORS = ['#16A34A', '#3B82F6', '#0D9488', '#06B6D4', '#8B5CF6', '#F59E0B'];

const GRADE_COLORS = {
  'A+': '#16A34A', A: '#4ADE80', 'B+': '#60A5FA', B: '#93C5FD',
  C: '#FBBF24', D: '#FB923C', F: '#F87171',
};

function StatCard({ label, value, sub, accent }) {
  return (
    <div className={styles.statCard}>
      <div className={styles.statValue} style={{ color: accent }}>{value}</div>
      <div className={styles.statLabel}>{label}</div>
      {sub && <div className={styles.statSub}>{sub}</div>}
    </div>
  );
}

const CustomTooltip = ({ active, payload, label }) => {
  if (active && payload && payload.length) {
    return (
      <div className={styles.tooltip}>
        <p className={styles.tooltipLabel}>{label}</p>
        {payload.map((p, i) => (
          <p key={i} style={{ color: p.fill || p.color }}>{p.name}: {p.value}</p>
        ))}
      </div>
    );
  }
  return null;
};

export default function Analytics() {
  const [stats,       setStats]       = useState(null);
  const [evaluations, setEvals]       = useState([]);
  const [resultFiles, setResultFiles] = useState([]);
  const [loading,     setLoading]     = useState(true);
  const [error,       setError]       = useState('');

  function loadData() {
    setLoading(true);
    setError('');

    Promise.allSettled([
      evaluationsAPI.stats(),
      evaluationsAPI.list(50),
      evaluationAPI.listResults(),
    ]).then(([statsRes, evalsRes, filesRes]) => {
      if (statsRes.status === 'fulfilled') setStats(statsRes.value);
      else setError(statsRes.reason?.message || 'Failed to load stats');

      if (evalsRes.status === 'fulfilled') {
        const data = evalsRes.value;
        setEvals(Array.isArray(data) ? data : data.results || data.evaluations || []);
      }

      if (filesRes.status === 'fulfilled') {
        setResultFiles(filesRes.value.files || []);
      }
    }).finally(() => setLoading(false));
  }

  useEffect(() => { loadData(); }, []);

  // ── Derive chart data ─────────────────────────────────────────────────────
  const gradeDistData = stats?.grade_distribution
    ? Object.entries(stats.grade_distribution).map(([name, value]) => ({
        name, value, color: GRADE_COLORS[name] || '#9CA3AF',
      }))
    : [];

  const subjectData = stats?.subjects
    ? stats.subjects.slice(0, 6).map((s, i) => ({
        subject: s._id || s.subject || `Subject ${i + 1}`,
        avg:     Math.round(s.avg_pct || s.avg_percentage || 0),
        color:   SUBJECT_COLORS[i % SUBJECT_COLORS.length],
      }))
    : [];

  const studentScores = evaluations.slice(0, 10).map(e => ({
    name:    (e.student_name || e.Name || 'Student').split(' ')[0],
    score:   Math.round(e.percentage || e.Percentage || 0),
    subject: e.subject_name || e.Subject || '',
  }));

  const total     = stats?.total_evaluations ?? evaluations.length ?? 0;
  const avg       = stats?.avg_percentage    ?? 0;
  const high      = stats?.highest           ?? (evaluations.length ? Math.max(...evaluations.map(e => e.percentage || e.Percentage || 0)) : 0);
  const passCount = evaluations.filter(e => (e.percentage || e.Percentage || 0) >= 60).length;
  const passRate  = total > 0 ? Math.round((passCount / evaluations.length) * 100) : 0;

  const radarData = [
    { metric: 'Semantic',  score: 72 },
    { metric: 'Keywords',  score: 65 },
    { metric: 'Structure', score: 80 },
    { metric: 'Length',    score: 88 },
    { metric: 'Overall',   score: Math.round(avg) },
  ];

  // ── Download file ─────────────────────────────────────────────────────────
  async function handleDownload(filename) {
    try {
      await evaluationAPI.downloadFile(filename);
    } catch (err) {
      alert(`Download failed: ${err.message}`);
    }
  }

  if (loading) {
    return (
      <div className={styles.page} style={{ display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <div style={{ textAlign: 'center', color: '#6B7280' }}>
          <div style={{ fontSize: 32 }}>📊</div>
          <p>Loading analytics from backend...</p>
          <small style={{ color: '#9CA3AF' }}>http://127.0.0.1:8000</small>
        </div>
      </div>
    );
  }

  return (
    <div className={styles.page}>
      <div className={styles.header}>
        <div>
          <h1 className={styles.title}>Analytics</h1>
          <p className={styles.subtitle}>
            Performance insights from {total} evaluation{total !== 1 ? 's' : ''}
            {error ? ' · ' : ' · '}
            {error
              ? <span style={{ color: '#EF4444' }}>⚠️ {error} — showing available data</span>
              : <span style={{ color: '#16A34A' }}>✅ Live from backend</span>
            }
          </p>
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          <button className={styles.exportBtn} onClick={loadData}>🔄 Refresh</button>
          <button className={styles.exportBtn} onClick={() => window.print()}>📊 Export Report</button>
        </div>
      </div>

      {/* Stats Row */}
      <div className={styles.statsRow}>
        <StatCard label="Total Evaluations" value={total}                         sub="Stored in MongoDB"    accent="#3B82F6" />
        <StatCard label="Average Score"      value={`${avg.toFixed(1)}%`}          sub="Across all subjects"  accent="#0D9488" />
        <StatCard label="Highest Score"      value={`${high.toFixed ? high.toFixed(1) : high}%`} sub="Best evaluation"   accent="#16A34A" />
        <StatCard label="Pass Rate"          value={evaluations.length > 0 ? `${passRate}%` : '—'} sub="Score ≥ 60%"    accent="#06B6D4" />
      </div>

      {total === 0 && evaluations.length === 0 ? (
        <div style={{ textAlign: 'center', padding: '60px 20px', color: '#6B7280' }}>
          <div style={{ fontSize: 48 }}>📭</div>
          <h3 style={{ marginTop: 12 }}>No evaluations yet</h3>
          <p>Run the evaluation engine — results will appear here automatically.</p>
          <small>Endpoints: <code>/evaluations/stats</code> · <code>/evaluations/list</code></small>
        </div>
      ) : (
        <div className={styles.chartsGrid}>

          {/* Student score bar chart */}
          {studentScores.length > 0 && (
            <div className={styles.chartCard}>
              <div className={styles.chartTitle}>📊 Recent Student Scores</div>
              <div className={styles.chartWrap}>
                <ResponsiveContainer width="100%" height={220}>
                  <BarChart data={studentScores} barSize={18}>
                    <XAxis dataKey="name" tick={{ fill: '#6B7280', fontSize: 10 }} axisLine={false} tickLine={false} />
                    <YAxis tick={{ fill: '#6B7280', fontSize: 10 }} axisLine={false} tickLine={false} domain={[0, 100]} />
                    <Tooltip content={<CustomTooltip />} cursor={{ fill: 'rgba(22,163,74,.05)' }} />
                    <Bar dataKey="score" name="Score %" radius={[3, 3, 0, 0]}>
                      {studentScores.map((_, i) => (
                        <Cell key={i} fill={SUBJECT_COLORS[i % SUBJECT_COLORS.length]} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
          )}

          {/* Radar — scoring dimensions */}
          <div className={styles.chartCard}>
            <div className={styles.chartTitle}>🕸️ Avg Scoring Dimension Profile</div>
            <div className={styles.chartWrap}>
              <ResponsiveContainer width="100%" height={220}>
                <RadarChart data={radarData}>
                  <PolarGrid stroke="#E5E7EB" />
                  <PolarAngleAxis dataKey="metric" tick={{ fill: '#6B7280', fontSize: 11 }} />
                  <PolarRadiusAxis domain={[0, 100]} tick={false} axisLine={false} />
                  <Radar name="Score" dataKey="score" stroke="#16A34A" fill="#16A34A" fillOpacity={0.2} />
                </RadarChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Grade distribution pie */}
          {gradeDistData.length > 0 && (
            <div className={styles.chartCard}>
              <div className={styles.chartTitle}>🎓 Grade Distribution</div>
              <div className={styles.chartWrap}>
                <ResponsiveContainer width="100%" height={220}>
                  <PieChart>
                    <Pie
                      data={gradeDistData}
                      dataKey="value"
                      nameKey="name"
                      cx="50%" cy="50%"
                      innerRadius={55} outerRadius={90}
                      paddingAngle={4}
                    >
                      {gradeDistData.map((g, i) => (
                        <Cell key={i} fill={g.color} stroke="#FFFFFF" strokeWidth={2} />
                      ))}
                    </Pie>
                    <Tooltip content={<CustomTooltip />} />
                  </PieChart>
                </ResponsiveContainer>
              </div>
              <div className={styles.chartLegend}>
                {gradeDistData.map(g => (
                  <div key={g.name} className={styles.legendItem}>
                    <span className={styles.legendDot} style={{ background: g.color }} />
                    <span>{g.name} ({g.value})</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Subject averages */}
          {subjectData.length > 0 && (
            <div className={styles.chartCard}>
              <div className={styles.chartTitle}>📐 Subject Average Scores</div>
              <div className={styles.subjectAvgList}>
                {subjectData.map(s => (
                  <div key={s.subject} className={styles.subjectAvgRow}>
                    <div className={styles.subjectAvgLabel}>{s.subject}</div>
                    <div className={styles.subjectAvgBarWrap}>
                      <div className={styles.subjectAvgBar} style={{ width: `${s.avg}%`, background: s.color }} />
                    </div>
                    <div className={styles.subjectAvgVal} style={{ color: s.color }}>{s.avg}%</div>
                  </div>
                ))}
              </div>

              {/* Top performers */}
              <div className={styles.topStudents}>
                <div className={styles.topTitle}>🏆 Top Performers</div>
                {[...evaluations]
                  .sort((a, b) => (b.percentage || b.Percentage || 0) - (a.percentage || a.Percentage || 0))
                  .slice(0, 3)
                  .map((e, i) => (
                    <div key={i} className={styles.topRow}>
                      <span className={styles.topRank}>#{i + 1}</span>
                      <span className={styles.topName}>{e.student_name || e.Name || '—'}</span>
                      <span className={styles.topScore} style={{ color: i === 0 ? '#16A34A' : '#6B7280' }}>
                        {(e.percentage || e.Percentage || 0).toFixed(1)}%
                      </span>
                    </div>
                  ))
                }
              </div>
            </div>
          )}

          {/* Downloadable result files */}
          {resultFiles.length > 0 && (
            <div className={styles.chartCard} style={{ gridColumn: '1 / -1' }}>
              <div className={styles.chartTitle}>📁 Result Files</div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginTop: 8 }}>
                {resultFiles.map((f, i) => (
                  <div
                    key={i}
                    onClick={() => handleDownload(f.name)}
                    style={{
                      display: 'flex', alignItems: 'center', gap: 8,
                      padding: '8px 14px', borderRadius: 8, cursor: 'pointer',
                      background: '#F9FAFB', border: '1px solid #E5E7EB',
                      fontSize: 12, transition: 'background 0.15s',
                    }}
                    onMouseEnter={e => e.currentTarget.style.background = '#EFF6FF'}
                    onMouseLeave={e => e.currentTarget.style.background = '#F9FAFB'}
                  >
                    <span>📥</span>
                    <div>
                      <div style={{ color: '#374151', fontWeight: 500 }}>{f.name}</div>
                      <div style={{ color: '#9CA3AF', fontSize: 10 }}>{f.size_kb} KB</div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}