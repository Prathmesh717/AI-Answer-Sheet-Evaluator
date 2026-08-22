import { TAB_META, PLANS } from '../subscription/plans';
import { useSubscription } from '../subscription/SubscriptionContext';
import styles from './LockedOverlay.module.css';

export default function LockedOverlay({ tabId, onUpgrade }) {
  const { state } = useSubscription();
  const meta = TAB_META[tabId];
  const currentPlan = state.planId ? PLANS[state.planId] : null;

  // Which plan unlocks this tab?
  const unlockingPlan = Object.values(PLANS).find(
    p => p.allowedTabs.includes(tabId) && p.id !== 'free_trial'
  );

  return (
    <div className={styles.overlay}>
      <div className={styles.card}>
        <div className={styles.lockIcon}>🔒</div>
        <div className={styles.tabBadge}>
          {meta.icon} {meta.label}
        </div>
        <h2 className={styles.title}>This feature is locked</h2>
        <p className={styles.desc}>
          {meta.label} is not included in your{' '}
          <strong>{currentPlan ? currentPlan.name : 'current'}</strong> plan.
          {' '}Upgrade to <strong>Gold</strong> to unlock all services.
        </p>

        {/* Plan pills showing access */}
        <div className={styles.planPills}>
          {Object.values(PLANS).map(plan => {
            const allowed = plan.allowedTabs.includes(tabId);
            return (
              <div
                key={plan.id}
                className={`${styles.pill} ${allowed ? styles.pillAllowed : styles.pillLocked}`}
                style={allowed ? { borderColor: plan.color, color: plan.color, background: plan.bgGradient } : {}}
              >
                <span>{plan.badge}</span>
                <span>{plan.name}</span>
                <span>{allowed ? '✅' : '🔒'}</span>
              </div>
            );
          })}
        </div>

        <div className={styles.actions}>
          <button className={styles.upgradeBtn} onClick={onUpgrade}>
            🥇 Upgrade to Gold — ₹699/mo
          </button>
          <button className={styles.viewPlansBtn} onClick={onUpgrade}>
            View all plans →
          </button>
        </div>
      </div>
    </div>
  );
}