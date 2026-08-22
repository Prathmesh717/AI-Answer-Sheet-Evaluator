import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import styles from './AuthPage.module.css';

const ROLES = ['Teacher / Educator', 'Professor', 'Institution Admin', 'Researcher'];

export default function RegisterPage({ onRegister }) {
  const navigate = useNavigate();
  const [form, setForm] = useState({
    fullName: '', email: '', role: '', password: '', confirm: '', agree: false
  });
  const [showPass, setShowPass] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const strength = (() => {
    const p = form.password;
    if (!p) return 0;
    let s = 0;
    if (p.length >= 8) s++;
    if (/[A-Z]/.test(p)) s++;
    if (/[0-9]/.test(p)) s++;
    if (/[^A-Za-z0-9]/.test(p)) s++;
    return s;
  })();

  const strengthLabel = ['', 'Weak', 'Fair', 'Good', 'Strong'];
  const strengthColor = ['', '#ef4444', '#f59e0b', '#3b82f6', '#16A34A'];

  async function handleSubmit(e) {
    e.preventDefault();
    if (!form.fullName || !form.email || !form.password) {
      setError('Please fill in all required fields.');
      return;
    }
    if (form.password !== form.confirm) {
      setError('Passwords do not match.');
      return;
    }
    if (form.password.length < 6) {
      setError('Password must be at least 6 characters.');
      return;
    }
    if (!form.agree) {
      setError('Please accept the terms to continue.');
      return;
    }
    setError('');
    setLoading(true);
    try {
      await onRegister(form.fullName.trim(), form.email.trim(), form.password);
      // Navigate to pricing so the new user can pick a plan
      navigate('/pricing', { replace: true });
    } catch (err) {
      if (err.message.includes('already registered') || err.message.includes('duplicate')) {
        setError('This email is already registered. Try signing in.');
      } else {
        setError(err.message || 'Registration failed. Please try again.');
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
          <Link to="/" className={styles.backBtn}>← Back to Home</Link>

          <div className={styles.leftBrand}>
            <span className={styles.leftBrandIcon}>🎓</span>
            <span className={styles.leftBrandName}>EvalAI Grader</span>
          </div>
          <h2 className={styles.leftTitle}>
            Join thousands of<br />
            <span className={styles.leftAccent}>smart educators.</span>
          </h2>
          <p className={styles.leftDesc}>
            Create your free account and start evaluating answer sheets with AI-powered FAIR scoring today.
          </p>

          <div className={styles.stepIndicators}>
            <div className={styles.stepIndicatorRow}>
              <div className={`${styles.stepDot} ${styles.stepDotDone}`}>✓</div>
              <div className={styles.stepDotLine} />
              <div className={`${styles.stepDot} ${styles.stepDotDone}`}>✓</div>
              <div className={styles.stepDotLine} />
              <div className={`${styles.stepDot} ${styles.stepDotActive}`}>3</div>
            </div>
            <div className={styles.stepIndicatorLabels}>
              <span>Account</span>
              <span>Details</span>
              <span>Done</span>
            </div>
          </div>

          <div className={styles.leftCard}>
            <div className={styles.leftCardQuote}>
              "EvalAI saved us 80% of grading time. The NLP scoring is incredibly fair."
            </div>
            <div className={styles.leftCardAuthor}>
              <span className={styles.leftAvatar}>👩‍🏫</span>
              <div>
                <div style={{ fontWeight: 600, fontSize: 13 }}>Dr. Priya Sharma</div>
                <div style={{ fontSize: 11, color: '#6B7280' }}>Prof. of CS, MIT Pune</div>
              </div>
            </div>
          </div>
        </div>
        <div className={styles.leftBlob} />
        <div className={styles.leftBlobB} />
      </div>

      {/* Right Panel — Register Form */}
      <div className={styles.rightPanel}>
        <div className={styles.formWrap}>
          <div className={styles.formHeader}>
            <h1 className={styles.formTitle}>Create your account</h1>
            <p className={styles.formSub}>Free forever · No credit card required</p>
          </div>

          {error && <div className={styles.errorBox}>⚠️ {error}</div>}

          <form className={styles.form} onSubmit={handleSubmit}>
            <div className={styles.fieldRow}>
              <div className={styles.field}>
                <label className={styles.label}>Full Name <span className={styles.req}>*</span></label>
                <div className={styles.inputWrap}>
                  <span className={styles.inputIcon}>👤</span>
                  <input
                    className={styles.input}
                    type="text"
                    placeholder="Dr. / Prof. / Mr. / Ms."
                    value={form.fullName}
                    onChange={e => setForm(f => ({ ...f, fullName: e.target.value }))}
                  />
                </div>
              </div>
              <div className={styles.field}>
                <label className={styles.label}>Role</label>
                <div className={styles.inputWrap}>
                  <span className={styles.inputIcon}>🏫</span>
                  <select
                    className={`${styles.input} ${styles.select}`}
                    value={form.role}
                    onChange={e => setForm(f => ({ ...f, role: e.target.value }))}
                  >
                    <option value="">Select role</option>
                    {ROLES.map(r => <option key={r} value={r}>{r}</option>)}
                  </select>
                </div>
              </div>
            </div>

            <div className={styles.field}>
              <label className={styles.label}>Email Address <span className={styles.req}>*</span></label>
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
              <label className={styles.label}>Password <span className={styles.req}>*</span></label>
              <div className={styles.inputWrap}>
                <span className={styles.inputIcon}>🔒</span>
                <input
                  className={styles.input}
                  type={showPass ? 'text' : 'password'}
                  placeholder="Min. 6 characters"
                  value={form.password}
                  onChange={e => setForm(f => ({ ...f, password: e.target.value }))}
                  autoComplete="new-password"
                />
                <button type="button" className={styles.showPassBtn} onClick={() => setShowPass(p => !p)}>
                  {showPass ? '🙈' : '👁️'}
                </button>
              </div>
              {form.password && (
                <div className={styles.strengthRow}>
                  <div className={styles.strengthBars}>
                    {[1, 2, 3, 4].map(i => (
                      <div key={i} className={styles.strengthBar}
                        style={{ background: i <= strength ? strengthColor[strength] : '#E5E7EB' }} />
                    ))}
                  </div>
                  <span className={styles.strengthLabel} style={{ color: strengthColor[strength] }}>
                    {strengthLabel[strength]}
                  </span>
                </div>
              )}
            </div>

            <div className={styles.field}>
              <label className={styles.label}>Confirm Password <span className={styles.req}>*</span></label>
              <div className={styles.inputWrap}>
                <span className={styles.inputIcon}>🔐</span>
                <input
                  className={`${styles.input} ${form.confirm && form.confirm !== form.password ? styles.inputError : ''}`}
                  type={showPass ? 'text' : 'password'}
                  placeholder="Repeat your password"
                  value={form.confirm}
                  onChange={e => setForm(f => ({ ...f, confirm: e.target.value }))}
                  autoComplete="new-password"
                />
                {form.confirm && form.confirm === form.password && (
                  <span className={styles.inputCheck}>✅</span>
                )}
              </div>
            </div>

            <label className={styles.rememberRow}>
              <input
                type="checkbox"
                className={styles.checkbox}
                checked={form.agree}
                onChange={e => setForm(f => ({ ...f, agree: e.target.checked }))}
              />
              <span>I agree to the <button type="button" className={styles.switchLink}>Terms</button> & <button type="button" className={styles.switchLink}>Privacy</button></span>
            </label>

            <button className={`${styles.submitBtn} ${loading ? styles.submitting : ''}`} type="submit" disabled={loading}>
              {loading ? <><span className={styles.spinner} /> Creating account...</> : '🎓 Create Free Account'}
            </button>
          </form>

          <p className={styles.switchText}>
            Already have an account?{' '}
            {/* ← Link to /login */}
            <Link to="/login" className={styles.switchLink}>Sign in →</Link>
          </p>
        </div>
      </div>
    </div>
  );
}