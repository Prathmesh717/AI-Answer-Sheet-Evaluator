import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { PLANS, TAB_META } from '../subscription/plans';
import { useSubscription } from '../subscription/SubscriptionContext';
import { paymentsAPI } from '../services/api';
import styles from './PricingPage.module.css';

// ── Load Razorpay script dynamically ─────────────────────────────────────────
function loadRazorpayScript() {
  return new Promise((resolve) => {
    if (window.Razorpay) { resolve(true); return; }
    const script = document.createElement('script');
    script.src    = 'https://checkout.razorpay.com/v1/checkout.js';
    script.onload  = () => resolve(true);
    script.onerror = () => resolve(false);
    document.body.appendChild(script);
  });
}

// ── Plan Card ─────────────────────────────────────────────────────────────────
function PlanCard({ plan, isCurrentPlan, onSelect, loadingPlan, animDelay }) {
  const isLoading = loadingPlan === plan.id;

  return (
    <div
      className={`${styles.card} ${plan.popular ? styles.cardPopular : ''} ${isCurrentPlan ? styles.cardActive : ''}`}
      style={{ animationDelay: `${animDelay}s`, borderColor: isCurrentPlan ? plan.color : '' }}
    >
      {plan.popular && (
        <div className={styles.popularBadge} style={{ background: plan.color }}>🥇 Most Popular</div>
      )}
      {isCurrentPlan && (
        <div className={styles.activeBadge} style={{ background: plan.color }}>✅ Current Plan</div>
      )}

      <div className={styles.cardHeader} style={{ background: plan.bgGradient }}>
        <div className={styles.planBadge}>{plan.badge}</div>
        <h3 className={styles.planName} style={{ color: plan.color }}>{plan.name}</h3>
        <p className={styles.planTagline}>{plan.tagline}</p>
        <div className={styles.priceRow}>
          <span className={styles.price} style={{ color: plan.color }}>{plan.priceLabel}</span>
          {plan.durationDays
            ? <span className={styles.pricePer}>/ {plan.durationDays} days</span>
            : plan.price > 0
            ? <span className={styles.pricePer}>/ month</span>
            : null}
        </div>
        {plan.id === 'free_trial' && (
          <div className={styles.trialChip}>⏱️ 5 days · No credit card</div>
        )}
      </div>

      <div className={styles.cardBody}>
        <div className={styles.accessTitle}>Services Included</div>
        <div className={styles.accessGrid}>
          {Object.entries(TAB_META).map(([tabId, meta]) => {
            const allowed = plan.allowedTabs.includes(tabId);
            return (
              <div key={tabId} className={`${styles.accessItem} ${allowed ? styles.accessAllowed : styles.accessLocked}`}>
                <span className={styles.accessIcon}>{meta.icon}</span>
                <span className={styles.accessLabel}>{meta.label}</span>
                <span className={styles.accessCheck}>{allowed ? '✅' : '🔒'}</span>
              </div>
            );
          })}
        </div>
        <div className={styles.featureList}>
          {plan.features.map(f => (
            <div key={f.text} className={`${styles.featureItem} ${!f.included ? styles.featureDisabled : ''}`}>
              <span className={styles.featureDot} style={{ color: f.included ? plan.color : '#D1D5DB' }}>
                {f.included ? '✓' : '✗'}
              </span>
              <span>{f.text}</span>
            </div>
          ))}
        </div>
      </div>

      <div className={styles.cardFooter}>
        <button
          className={styles.selectBtn}
          style={isCurrentPlan
            ? { background: plan.color, color: 'white' }
            : {
                background: plan.popular ? plan.color : 'transparent',
                color:      plan.popular ? 'white' : plan.color,
                border:     `2px solid ${plan.color}`,
              }}
          onClick={() => onSelect(plan.id)}
          disabled={isCurrentPlan || !!loadingPlan}
        >
          {isLoading
            ? <><span className={styles.btnSpinner} /> Processing...</>
            : isCurrentPlan
            ? '✅ Active Plan'
            : plan.id === 'free_trial'
            ? '⚡ Start Free Trial'
            : `Choose ${plan.name}`}
        </button>
      </div>
    </div>
  );
}

// ── Main Page ─────────────────────────────────────────────────────────────────
export default function PricingPage() {
  const navigate = useNavigate();
  const { state, dispatch, isActive, activatePlan } = useSubscription();

  const [loadingPlan, setLoadingPlan]   = useState(null);
  const [paymentError, setPaymentError] = useState('');
  const [successInfo, setSuccessInfo]   = useState(null);

  // ── Select / pay for a plan ───────────────────────────────────────────────
  async function handleSelect(planId) {
    setPaymentError('');

    // Free trial — no payment, activate immediately
    if (planId === 'free_trial') {
      activatePlan(planId);
      navigate('/dashboard', { replace: true });
      return;
    }

    setLoadingPlan(planId);

    try {
      // 1. Load Razorpay script
      const loaded = await loadRazorpayScript();
      if (!loaded) throw new Error('Failed to load Razorpay. Check your internet connection.');

      // 2. Create order on backend
      const order = await paymentsAPI.createOrder(planId);

      // 3. Open Razorpay checkout
      await new Promise((resolve, reject) => {
        const rzp = new window.Razorpay({
          key:         order.key_id,
          amount:      order.amount,
          currency:    order.currency,
          name:        'EvalAI Grader',
          description: `${order.plan_name} Plan Subscription`,
          order_id:    order.order_id,
          theme:       { color: planId === 'gold' ? '#D97706' : '#64748B' },
          handler: async (response) => {
            try {
              // 4. Verify payment + save to MongoDB
              const result = await paymentsAPI.verifyPayment(
                response.razorpay_order_id,
                response.razorpay_payment_id,
                response.razorpay_signature,
                planId,
              );

              // inside the Razorpay handler, after paymentsAPI.verifyPayment succeeds
              // 5. Activate plan in context (also persists per-user to localStorage)
              activatePlan(planId);

              setSuccessInfo({
                planName:  result.plan_name,
                amount:    result.amount_display,
                paymentId: result.payment_id,
                planId,
              });
              resolve();
            } catch (err) {
              reject(new Error(err.message || 'Payment verification failed'));
            }
          },
          modal: { ondismiss: () => reject(new Error('DISMISSED')) },
        });

        rzp.on('payment.failed', (resp) => {
          reject(new Error(resp.error?.description || 'Payment failed'));
        });
        rzp.open();
      });

    } catch (err) {
      if (err.message !== 'DISMISSED') {
        setPaymentError(err.message || 'Payment failed. Please try again.');
      }
    } finally {
      setLoadingPlan(null);
    }
  }

  // After success modal → go to dashboard
  function handleContinue() {
    navigate('/dashboard', { replace: true });
  }

  return (
    <div className={styles.page}>
      {/* Background */}
      <div className={styles.bg}>
        <div className={styles.bgBlob1} />
        <div className={styles.bgBlob2} />
        <div className={styles.bgGrid} />
      </div>

      <div className={styles.inner}>
        {/* Header */}
        <div className={styles.pageHeader}>
          {isActive && (
            <button className={styles.backBtn} onClick={() => navigate('/dashboard')}>
              ← Back to Dashboard
            </button>
          )}

          <div className={styles.headerTag}>💳 Subscription Plans</div>
          <h1 className={styles.pageTitle}>
            Choose your <span className={styles.titleAccent}>learning plan</span>
          </h1>
          <p className={styles.pageSub}>
            Start free for 5 days, then pick the plan that fits your institution's needs.
          </p>

          <div className={styles.comparisonChips}>
            <div className={styles.chip} style={{ borderColor: '#9CA3AF', color: '#6B7280' }}>
              ⏱️ Free Trial — All features · 5 days
            </div>
            <div className={styles.chipArrow}>→</div>
            <div className={styles.chip} style={{ borderColor: '#94A3B8', color: '#64748B' }}>
              🥈 Silver — Subjects + Evaluation
            </div>
            <div className={styles.chipArrow}>→</div>
            <div className={styles.chip} style={{ borderColor: '#F59E0B', color: '#D97706', background: '#FFFBEB' }}>
              🥇 Gold — Everything Unlocked
            </div>
          </div>
        </div>

        {/* Error banner */}
        {paymentError && (
          <div className={styles.errorBanner}>
            ⚠️ {paymentError}
            <button className={styles.errorClose} onClick={() => setPaymentError('')}>✕</button>
          </div>
        )}

        {/* Plan Cards */}
        <div className={styles.cardsRow}>
          {Object.values(PLANS).map((plan, i) => (
            <PlanCard
              key={plan.id}
              plan={plan}
              isCurrentPlan={state.planId === plan.id}
              onSelect={handleSelect}
              loadingPlan={loadingPlan}
              animDelay={i * 0.12}
            />
          ))}
        </div>

        {/* Feature Comparison Table */}
        <div className={styles.compareSection}>
          <h2 className={styles.compareTitle}>Full Feature Comparison</h2>
          <div className={styles.compareTable}>
            <div className={styles.compareHeader}>
              <div className={styles.compareFeatureCol}>Feature</div>
              {Object.values(PLANS).map(p => (
                <div key={p.id} className={styles.comparePlanCol} style={{ color: p.color }}>
                  {p.badge} {p.name}
                </div>
              ))}
            </div>
            {[
              { label: '📚 Subject Manager',   key: 'subjects' },
              { label: '🎯 Evaluation Engine',  key: 'evaluation' },
              { label: '📄 PDF OCR Tools',      key: 'pdf' },
              { label: '📊 Analytics',          key: 'analytics' },
              { label: '⚙️ Settings',           key: 'settings' },
              { label: '✉️ Email Reports',      vals: [true, false, true] },
              { label: '🎓 Priority Support',   vals: [false, false, true] },
              { label: '👥 Unlimited Students', vals: [false, false, true] },
            ].map((row, i) => (
              <div key={i} className={`${styles.compareRow} ${i % 2 === 0 ? styles.compareRowAlt : ''}`}>
                <div className={styles.compareFeatureCol}>{row.label}</div>
                {Object.values(PLANS).map((p, j) => {
                  const has = row.key ? p.allowedTabs.includes(row.key) : row.vals[j];
                  return (
                    <div key={p.id} className={styles.comparePlanCol}>
                      <span className={has ? styles.checkYes : styles.checkNo}>{has ? '✅' : '—'}</span>
                    </div>
                  );
                })}
              </div>
            ))}
          </div>
        </div>

        {/* FAQ */}
        <div className={styles.faqStrip}>
          {[
            { q: 'No credit card for trial?', a: 'Correct — start free, no card needed.' },
            { q: 'Can I upgrade anytime?',    a: 'Yes, upgrade instantly from Silver to Gold.' },
            { q: 'What happens after trial?', a: 'Access is paused until you pick a plan.' },
          ].map(f => (
            <div key={f.q} className={styles.faqItem}>
              <span className={styles.faqQ}>{f.q}</span>
              <span className={styles.faqA}>{f.a}</span>
            </div>
          ))}
        </div>
      </div>

      {/* ── Payment Success Modal ───────────────────────────────────────────── */}
      {successInfo && (
        <div className={styles.modalOverlay}>
          <div className={styles.modal}>
            <div className={styles.successIcon}>🎉</div>
            <h3 className={styles.modalTitle}>Payment Successful!</h3>
            <p className={styles.modalSub}>
              Your <strong>{successInfo.planName}</strong> plan is now active.
            </p>

            <div className={styles.paymentReceipt}>
              <div className={styles.receiptRow}>
                <span className={styles.receiptLabel}>Plan</span>
                <span className={styles.receiptVal}>
                  {PLANS[successInfo.planId].badge} {successInfo.planName}
                </span>
              </div>
              <div className={styles.receiptRow}>
                <span className={styles.receiptLabel}>Amount Paid</span>
                <span className={styles.receiptVal} style={{ color: '#16A34A', fontWeight: 700 }}>
                  {successInfo.amount}
                </span>
              </div>
              <div className={styles.receiptRow}>
                <span className={styles.receiptLabel}>Payment ID</span>
                <span className={styles.receiptVal} style={{ fontFamily: 'monospace', fontSize: 11 }}>
                  {successInfo.paymentId}
                </span>
              </div>
              <div className={styles.receiptRow}>
                <span className={styles.receiptLabel}>Status</span>
                <span className={styles.receiptVal} style={{ color: '#16A34A' }}>✅ Confirmed & Saved</span>
              </div>
            </div>

            <div className={styles.modalAccessList}>
              {PLANS[successInfo.planId].allowedTabs.map(tabId => (
                <span key={tabId} className={`${styles.modalAccessChip} ${styles.chipAllowed}`}>
                  {TAB_META[tabId].icon} {TAB_META[tabId].label}
                </span>
              ))}
            </div>

            <div className={styles.modalActions}>
              <button
                className={styles.modalConfirm}
                style={{ background: PLANS[successInfo.planId].color }}
                onClick={handleContinue}
              >
                🚀 Go to Dashboard
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}