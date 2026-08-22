import { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import styles from './HomePage.module.css';

const NAV_LINKS = ['Features', 'How It Works', 'Subjects', 'Contact'];

const STATS = [
  { icon: '⚡', value: '10x', label: 'Faster Grading' },
  { icon: '🧠', value: '95%', label: 'AI Accuracy' },
  { icon: '✉️', value: '100%', label: 'Auto Email' },
  { icon: '📚', value: '5+', label: 'Subjects' },
];

const FEATURES = [
  { icon: '🔍', title: 'OCR Text Extraction', desc: 'Automatically extract handwritten and scanned answer sheets using advanced OCR technology.' },
  { icon: '🧠', title: 'NLP Semantic Analysis', desc: 'Goes beyond keywords — understands the context and meaning behind student answers.' },
  { icon: '⚖️', title: 'FAIR Scoring Engine', desc: 'Multi-dimensional scoring: Semantic, Keywords, Structure, and Length for fair evaluation.' },
  { icon: '📊', title: 'Detailed Analytics', desc: 'Visualize performance with radar charts, grade distributions, and per-subject breakdowns.' },
  { icon: '✉️', title: 'Auto Email Reports', desc: 'Send individual PDF score reports to students via Gmail instantly after evaluation.' },
  { icon: '📚', title: 'Multi-Subject Support', desc: 'Evaluate SE, Cyber Security, AI, Blockchain, Law and more in a single batch run.' },
];

const HOW_IT_WORKS = [
  { step: '01', title: 'Upload Subjects', desc: 'Add master answer sheets and student PDF submissions.' },
  { step: '02', title: 'Configure Engine', desc: 'Select OCR, NLP models and email automation settings.' },
  { step: '03', title: 'Run Evaluation', desc: 'The FAIR engine scores all students across all subjects automatically.' },
  { step: '04', title: 'Review & Send', desc: 'View analytics, download CSVs and email results instantly.' },
];

const SUBJECTS = [
  { name: 'Software Engineering', icon: '💻' },
  { name: 'Cyber Security', icon: '🔐' },
  { name: 'Artificial Intelligence', icon: '🤖' },
  { name: 'Blockchain', icon: '⛓️' },
  { name: 'Constitutional Law', icon: '⚖️' },
  { name: 'Data Structures', icon: '🌳' },
];

const CONTACT_INFO = [
  { icon: '✉️', label: 'Email', value: 'support@evalai.edu', href: 'mailto:support@evalai.edu' },
  { icon: '📞', label: 'Phone', value: '+91 98765 43210', href: 'tel:+919876543210' },
  { icon: '📍', label: 'Location', value: 'Pune, Maharashtra, India', href: null },
  { icon: '🕐', label: 'Support Hours', value: 'Mon–Fri, 9AM – 6PM IST', href: null },
];

// 3D Tilt hook
const useTilt = () => {
  const ref = useRef(null);
  const [transform, setTransform] = useState('');
  useEffect(() => {
    const move = (e) => {
      if (!ref.current) return;
      const rect = ref.current.getBoundingClientRect();
      const rx = (((e.clientY - rect.top) / rect.height) - 0.5) * -10;
      const ry = (((e.clientX - rect.left) / rect.width) - 0.5) * 10;
      setTransform(`perspective(1000px) rotateX(${rx}deg) rotateY(${ry}deg) scale(1.02)`);
    };
    const leave = () => setTransform('perspective(1000px) rotateX(0) rotateY(0) scale(1)');
    const el = ref.current;
    if (el) { el.addEventListener('mousemove', move); el.addEventListener('mouseleave', leave); }
    return () => { if (el) { el.removeEventListener('mousemove', move); el.removeEventListener('mouseleave', leave); } };
  }, []);
  return { ref, style: { transform } };
};

// ── Contact Form Component ──────────────────────────────────────────
function ContactSection() {
  const [form, setForm] = useState({ name: '', email: '', subject: '', message: '' });
  const [status, setStatus] = useState('idle');
  const [touched, setTouched] = useState({});

  const errors = {
    name: !form.name.trim() ? 'Name is required' : '',
    email: !form.email.trim() ? 'Email is required' : !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email) ? 'Enter a valid email' : '',
    subject: !form.subject ? 'Please select a topic' : '',
    message: form.message.trim().length < 20 ? 'Message must be at least 20 characters' : '',
  };
  const isValid = Object.values(errors).every(e => !e);

  const blur = (f) => setTouched(t => ({ ...t, [f]: true }));
  const change = (f, v) => setForm(p => ({ ...p, [f]: v }));

  function submit(e) {
    e.preventDefault();
    setTouched({ name: true, email: true, subject: true, message: true });
    if (!isValid) return;
    setStatus('sending');
    setTimeout(() => {
      setStatus('success');
      setForm({ name: '', email: '', subject: '', message: '' });
      setTouched({});
    }, 1800);
  }

  if (status === 'success') {
    return (
      <section className={styles.contactSection} id="contact">
        <div className={styles.sectionInner}>
          <div className={styles.successState}>
            <div className={styles.successIcon}>🎉</div>
            <h3 className={styles.successTitle}>Message Sent Successfully!</h3>
            <p className={styles.successDesc}>Thank you for reaching out. We'll get back to you within 24 hours.</p>
            <button className={styles.successResetBtn} onClick={() => setStatus('idle')}>
              ✉️ Send Another Message
            </button>
          </div>
        </div>
      </section>
    );
  }

  return (
    <section className={styles.contactSection} id="contact">
      <div className={styles.sectionInner}>
        <div className={styles.sectionHead}>
          <span className={styles.sectionTag}>Contact</span>
          <h2 className={styles.sectionTitle}>Get in Touch</h2>
          <p className={styles.sectionSub}>Have questions about EvalAI? We'd love to hear from you.</p>
        </div>
        <div className={styles.contactLayout}>
          <div className={styles.contactInfoCard}>
            <h3 className={styles.contactInfoTitle}>Let's talk 👋</h3>
            <p className={styles.contactInfoDesc}>
              Whether you're an educator, institution, or researcher — we're here
              to help you set up AI-powered grading for your students.
            </p>
            <div className={styles.contactInfoList}>
              {CONTACT_INFO.map(item => (
                <div key={item.label} className={styles.contactInfoItem}>
                  <div className={styles.contactInfoIconBox}>{item.icon}</div>
                  <div>
                    <div className={styles.contactInfoLabel}>{item.label}</div>
                    {item.href
                      ? <a href={item.href} className={styles.contactInfoValue}>{item.value}</a>
                      : <span className={styles.contactInfoValue}>{item.value}</span>}
                  </div>
                </div>
              ))}
            </div>
            <div className={styles.socialLinks}>
              <a href="https://github.com" target="_blank" rel="noreferrer" className={styles.socialLink}>⬛ GitHub</a>
              <a href="https://linkedin.com" target="_blank" rel="noreferrer" className={styles.socialLink}>🔵 LinkedIn</a>
              <a href="https://twitter.com" target="_blank" rel="noreferrer" className={styles.socialLink}>🐦 Twitter</a>
            </div>
          </div>

          <form className={styles.contactForm} onSubmit={submit} noValidate>
            <div className={styles.contactFormRow}>
              <div className={styles.contactField}>
                <label className={styles.contactLabel}>Full Name <span className={styles.req}>*</span></label>
                <div className={`${styles.contactInputWrap} ${touched.name && errors.name ? styles.inputErr : ''}`}>
                  <span className={styles.contactInputIcon}>👤</span>
                  <input className={styles.contactInput} type="text" placeholder="Dr. / Prof. / Your Name"
                    value={form.name} onChange={e => change('name', e.target.value)} onBlur={() => blur('name')} />
                </div>
                {touched.name && errors.name && <span className={styles.contactErrMsg}>⚠ {errors.name}</span>}
              </div>
              <div className={styles.contactField}>
                <label className={styles.contactLabel}>Email <span className={styles.req}>*</span></label>
                <div className={`${styles.contactInputWrap} ${touched.email && errors.email ? styles.inputErr : ''}`}>
                  <span className={styles.contactInputIcon}>✉️</span>
                  <input className={styles.contactInput} type="email" placeholder="you@institution.edu"
                    value={form.email} onChange={e => change('email', e.target.value)} onBlur={() => blur('email')} />
                </div>
                {touched.email && errors.email && <span className={styles.contactErrMsg}>⚠ {errors.email}</span>}
              </div>
            </div>
            <div className={styles.contactField}>
              <label className={styles.contactLabel}>Topic <span className={styles.req}>*</span></label>
              <div className={`${styles.contactInputWrap} ${touched.subject && errors.subject ? styles.inputErr : ''}`}>
                <span className={styles.contactInputIcon}>📋</span>
                <select className={`${styles.contactInput} ${styles.contactSelect}`}
                  value={form.subject} onChange={e => change('subject', e.target.value)} onBlur={() => blur('subject')}>
                  <option value="">Select a topic</option>
                  <option value="demo">Request a Demo</option>
                  <option value="pricing">Pricing Inquiry</option>
                  <option value="support">Technical Support</option>
                  <option value="partnership">Partnership</option>
                  <option value="other">Other</option>
                </select>
              </div>
              {touched.subject && errors.subject && <span className={styles.contactErrMsg}>⚠ {errors.subject}</span>}
            </div>
            <div className={styles.contactField}>
              <label className={styles.contactLabel}>Message <span className={styles.req}>*</span></label>
              <div className={`${styles.contactInputWrap} ${touched.message && errors.message ? styles.inputErr : ''}`}>
                <textarea className={`${styles.contactInput} ${styles.contactTextarea}`} placeholder="Write your message here (min. 20 characters)..."
                  value={form.message} onChange={e => change('message', e.target.value)} onBlur={() => blur('message')} rows={4} />
              </div>
              {touched.message && errors.message && <span className={styles.contactErrMsg}>⚠ {errors.message}</span>}
            </div>
            <button className={`${styles.contactSubmitBtn} ${status === 'sending' ? styles.contactSubmitSending : ''}`} type="submit" disabled={status === 'sending'}>
              {status === 'sending' ? <><span className={styles.spinner} /> Sending...</> : '📨 Send Message'}
            </button>
          </form>
        </div>
      </div>
    </section>
  );
}

// ── Main HomePage Component ───────────────────────────────────────────────────
export default function HomePage() {
  const navigate = useNavigate();  // ← React Router hook
  const [menuOpen, setMenuOpen] = useState(false);
  const { ref: heroCardRef, style: heroCardStyle } = useTilt();

  return (
    <div className={styles.page}>
    {/* ── NAVBAR ── */}
<header className={styles.nav}>
  <div className={styles.navInner}>

    {/* Brand */}
    <div className={styles.brand}>
      <span className={styles.brandIcon}>🎓</span>
      <span className={styles.brandName}>
        EvalAI <span className={styles.brandSub}>Grader</span>
      </span>
    </div>

    {/* Navigation Links */}
    <nav className={styles.navLinks}>
      {NAV_LINKS.map(l => (
        <a
          key={l}
          href={`#${l.toLowerCase().replaceAll(' ', '-')}`}
          className={styles.navLink}
          onClick={() => setMenuOpen(false)}
        >
          {l}
        </a>
      ))}
    </nav>

    {/* CTA Buttons */}
    <div className={styles.navCtas}>
      <button
        className={styles.navLogin}
        onClick={() => navigate('/login')}
      >
        Sign In
      </button>

      <button
        className={styles.navRegister}
        onClick={() => navigate('/register')}
      >
        Get Started →
      </button>
    </div>

    {/* Mobile Hamburger */}
    <button
      className={`${styles.hamburger} ${menuOpen ? styles.hamburgerActive : ''}`}
      onClick={() => setMenuOpen(!menuOpen)}
      aria-label="Toggle menu"
    >
      <span></span>
      <span></span>
      <span></span>
    </button>

  </div>
</header> 

      {/* ── HERO ── */}
      <section className={styles.hero}>
        <div className={styles.heroBg}>
          <div className={styles.heroBlobA} />
          <div className={styles.heroBlobB} />
          <div className={styles.gridPattern} />
        </div>
        <div className={styles.heroContainer}>
          <div className={styles.heroContent}>
            <div className={styles.heroBadge}>
              <span className={styles.heroBadgeDot} />
              AI-Powered · FAIR Evaluation Engine
            </div>
            <h1 className={styles.heroTitle}>
              Automated <span className={styles.heroAccent}>Answer Sheet</span><br />Grading System
            </h1>
            <p className={styles.heroDesc}>
              Upload PDF answer sheets and get instant AI-powered evaluation. Leverage NLP semantic analysis,
              detailed analytics, and automated email reports to save hours of work.
            </p>
            <div className={styles.heroStats}>
              {STATS.map(s => (
                <div key={s.label} className={styles.heroStat}>
                  <span className={styles.heroStatIcon}>{s.icon}</span>
                  <span className={styles.heroStatVal}>{s.value}</span>
                  <span className={styles.heroStatLabel}>{s.label}</span>
                </div>
              ))}
            </div>
            <div className={styles.heroCtas}>
              <button className={styles.ctaPrimary} onClick={() => navigate('/register')}>🚀 Start Grading Now</button>
              <a href="#how-it-works" className={styles.ctaSecondary}>See How It Works ↓</a>
            </div>
          </div>

          <div className={styles.heroVisual} ref={heroCardRef} style={heroCardStyle}>
            <div className={styles.heroCard}>
              <div className={styles.heroCardHeader}>
                <div className={styles.heroCardDots}>
                  <span className={styles.heroCardDot} style={{ background: '#ef4444' }} />
                  <span className={styles.heroCardDot} style={{ background: '#f59e0b' }} />
                  <span className={styles.heroCardDot} style={{ background: '#22c55e' }} />
                </div>
                <span className={styles.heroCardTitle}>Live Evaluation Process</span>
              </div>
              <div className={styles.heroCardBody}>
                {['Student_01.pdf', 'Student_02.pdf', 'Student_03.pdf'].map((name, i) => (
                  <div key={name} className={styles.heroCardRow} style={{ animationDelay: `${i * 0.4}s` }}>
                    <div className={styles.fileIcon}>📄</div>
                    <div className={styles.fileInfo}>
                      <span className={styles.heroCardName}>{name}</span>
                      <div className={styles.heroCardBar}>
                        <div className={styles.heroCardBarFill} style={{ width: `${[78, 65, 92][i]}%`, animationDelay: `${i * 0.4 + 0.3}s` }} />
                      </div>
                    </div>
                    <span className={styles.heroCardScore}>{[78, 65, 92][i]}%</span>
                  </div>
                ))}
              </div>
              <div className={styles.heroCardFooter}>
                <span className={styles.heroCardBadge}>✅ Evaluation Complete</span>
                <span className={styles.heroCardTime}>2.3s</span>
              </div>
              <div className={styles.scanLine} />
            </div>
            <div className={styles.heroFloatA}><span>🧠</span> NLP Active</div>
            <div className={styles.heroFloatB}><span>📊</span> Analytics Ready</div>
          </div>
        </div>
      </section>

      {/* ── FEATURES ── */}
      <section className={styles.section} id="features">
        <div className={styles.sectionInner}>
          <div className={styles.sectionHead}>
            <span className={styles.sectionTag}>Features</span>
            <h2 className={styles.sectionTitle}>Everything you need to grade smarter</h2>
            <p className={styles.sectionSub}>Powered by cutting-edge NLP and OCR — built for educators</p>
          </div>
          <div className={styles.featuresGrid}>
            {FEATURES.map((f, i) => (
              <div key={f.title} className={styles.featureCard} style={{ animationDelay: `${i * 0.1}s` }}>
                <div className={styles.featureIconWrapper}>{f.icon}</div>
                <h3 className={styles.featureTitle}>{f.title}</h3>
                <p className={styles.featureDesc}>{f.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── HOW IT WORKS ── */}
      <section className={styles.howSection} id="how-it-works">
        <div className={styles.sectionInner}>
          <div className={styles.sectionHead}>
            <span className={styles.sectionTag}>Process</span>
            <h2 className={styles.sectionTitle}>How It Works</h2>
            <p className={styles.sectionSub}>Four simple steps from upload to results</p>
          </div>
          <div className={styles.stepsRow}>
            {HOW_IT_WORKS.map((step, i) => (
              <div key={step.step} className={styles.stepCard}>
                <div className={styles.stepNum}>{step.step}</div>
                {i < HOW_IT_WORKS.length - 1 && <div className={styles.stepConnector} />}
                <h3 className={styles.stepTitle}>{step.title}</h3>
                <p className={styles.stepDesc}>{step.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── SUBJECTS ── */}
      <section className={styles.section} id="subjects">
        <div className={styles.sectionInner}>
          <div className={styles.sectionHead}>
            <span className={styles.sectionTag}>Subjects</span>
            <h2 className={styles.sectionTitle}>Multi-Subject Evaluation</h2>
            <p className={styles.sectionSub}>Pre-trained on subject-specific technical vocabularies</p>
          </div>
          <div className={styles.subjectsGrid}>
            {SUBJECTS.map(s => (
              <div key={s.name} className={styles.subjectPill}>
                <span className={styles.subjectPillIcon}>{s.icon}</span>
                <span>{s.name}</span>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── CONTACT ── */}
      <ContactSection />

      {/* ── CTA BANNER ── */}
      <section className={styles.ctaBanner}>
        <div className={styles.ctaBannerInner}>
          <h2 className={styles.ctaBannerTitle}>Ready to modernize your grading?</h2>
          <p className={styles.ctaBannerSub}>Join educators using AI to evaluate faster, fairer, and smarter.</p>
          <button className={styles.ctaBannerBtn} onClick={() => navigate('/register')}>🎓 Create Free Account</button>
        </div>
      </section>

      {/* ── FOOTER ── */}
      <footer className={styles.footer}>
        <div className={styles.footerInner}>
          <div className={styles.footerBrand}>
            <span className={styles.brandIcon}>🎓</span>
            <span className={styles.brandName}>EvalAI <span className={styles.brandSub}>Grader</span></span>
          </div>
          <nav className={styles.footerNav}>
            {NAV_LINKS.map(l => (
              <a key={l} href={`#${l.toLowerCase().replace(' ', '-')}`} className={styles.footerNavLink}>{l}</a>
            ))}
          </nav>
          <p className={styles.footerCopy}>© 2026 EvalAI Grader · Built with ❤️ for educators</p>
        </div>
      </footer>
    </div>
  );
}