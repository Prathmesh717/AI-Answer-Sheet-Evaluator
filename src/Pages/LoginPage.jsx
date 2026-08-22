import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import styles from './AuthPage.module.css';

// onLogin is still passed from App.js (calls AppContext login)
export default function LoginPage({ onLogin }) {
  const navigate = useNavigate();
  const [form, setForm] = useState({ email: '', password: '' });
  const [showPass, setShowPass] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  async function handleSubmit(e) {
    e.preventDefault();
    if (!form.email || !form.password) {
      setError('Please fill in all fields.');
      return;
    }
    setError('');
    setLoading(true);
    try {
      await onLogin(form.email, form.password);
      // AppContext sets authUser → App.js navigates to /dashboard automatically
      navigate('/dashboard', { replace: true });
    } catch (err) {
      if (err.message === 'SESSION_EXPIRED') {
        setError('Session expired. Please log in again.');
      } else {
        setError(err.message || 'Invalid email or password.');
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className={styles.page}>
      {/* Left Panel */}
      <div className={styles.leftPanel}>
        <div className={styles.leftContent}>
          {/* ← Use Link instead of onNavigate button */}
          <Link to="/" className={styles.backBtn}>← Back to Home</Link>

          <div className={styles.leftBrand}>
            <span className={styles.leftBrandIcon}>🎓</span>
            <span className={styles.leftBrandName}>EvalAI Grader</span>
          </div>
          <h2 className={styles.leftTitle}>
            Grade smarter.<br />
            <span className={styles.leftAccent}>Not harder.</span>
          </h2>
          <p className={styles.leftDesc}>
            AI-powered evaluation for educators — evaluate hundreds of answer sheets in seconds with FAIR scoring.
          </p>
          <div className={styles.leftFeatures}>
            {[
              { icon: '🧠', text: 'NLP Semantic Understanding' },
              { icon: '⚡', text: '10x Faster than Manual Grading' },
              { icon: '📊', text: 'Detailed Analytics & Reports' },
              { icon: '✉️', text: 'Automated Email to Students' },
            ].map(f => (
              <div key={f.text} className={styles.leftFeature}>
                <span className={styles.leftFeatureIcon}>{f.icon}</span>
                <span>{f.text}</span>
              </div>
            ))}
          </div>
          <div className={styles.leftCard}>
            <div className={styles.leftCardTop}>
              <div className={styles.leftAvatars}>
                {['👩‍🏫', '👨‍🏫', '👩‍💻'].map((a, i) => (
                  <span key={i} className={styles.leftAvatar} style={{ marginLeft: i > 0 ? '-12px' : 0 }}>{a}</span>
                ))}
              </div>
              <div className={styles.leftCardStat}>
                <strong>500+</strong> educators trust EvalAI
              </div>
            </div>
          </div>
        </div>
        <div className={styles.leftBlob} />
        <div className={styles.leftBlobB} />
      </div>

      {/* Right Panel — Form */}
      <div className={styles.rightPanel}>
        <div className={styles.formWrap}>
          <div className={styles.formHeader}>
            <h1 className={styles.formTitle}>Welcome back</h1>
            <p className={styles.formSub}>Sign in to your EvalAI account</p>
          </div>

          {error && <div className={styles.errorBox}>⚠️ {error}</div>}

          <form className={styles.form} onSubmit={handleSubmit}>
            <div className={styles.field}>
              <label className={styles.label}>Email Address</label>
              <div className={styles.inputWrap}>
                <span className={styles.inputIcon}>✉️</span>
                <input
                  className={styles.input}
                  type="email"
                  placeholder="you@institution.edu"
                  value={form.email}
                  onChange={e => setForm(f => ({ ...f, email: e.target.value }))}
                  autoComplete="email"
                />
              </div>
            </div>

            <div className={styles.field}>
              <div className={styles.labelRow}>
                <label className={styles.label}>Password</label>
                <button type="button" className={styles.forgotBtn} onClick={() => alert('Reset link sent!')}>Forgot password?</button>
              </div>
              <div className={styles.inputWrap}>
                <span className={styles.inputIcon}>🔒</span>
                <input
                  className={styles.input}
                  type={showPass ? 'text' : 'password'}
                  placeholder="Enter your password"
                  value={form.password}
                  onChange={e => setForm(f => ({ ...f, password: e.target.value }))}
                  autoComplete="current-password"
                />
                <button type="button" className={styles.showPassBtn} onClick={() => setShowPass(p => !p)}>
                  {showPass ? '🙈' : '👁️'}
                </button>
              </div>
            </div>

            <label className={styles.rememberRow}>
              <input type="checkbox" className={styles.checkbox} />
              <span>Keep me signed in</span>
            </label>

            <button className={`${styles.submitBtn} ${loading ? styles.submitting : ''}`} type="submit" disabled={loading}>
              {loading ? <><span className={styles.spinner} /> Signing in...</> : '🚀 Sign In'}
            </button>
          </form>

          <div className={styles.dividerRow}>
            <div className={styles.dividerLine} />
            <span className={styles.dividerText}>or continue with</span>
            <div className={styles.dividerLine} />
          </div>

          <div className={styles.socialRow}>
            <button className={styles.socialBtn}><span style={{ fontSize: '16px' }}>G</span> Google</button>
            <button className={styles.socialBtn}><span style={{ fontSize: '16px' }}>M</span> Microsoft</button>
          </div>

          <p className={styles.switchText}>
            Don't have an account?{' '}
            {/* ← Link to /register instead of onNavigate('register') */}
            <Link to="/register" className={styles.switchLink}>Create one free →</Link>
          </p>
        </div>
      </div>
    </div>
  );
}