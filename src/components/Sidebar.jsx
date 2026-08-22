import { useNavigate } from 'react-router-dom';
import { useApp } from '../context/AppContext';
import { useSubscription } from '../subscription/SubscriptionContext';
import { PLANS, canAccess } from '../subscription/plans';
import styles from './Sidebar.module.css';

const NAV_ITEMS = [
  { id: 'subjects',   icon: '📚', label: 'Subjects' },
  { id: 'evaluation', icon: '🎯', label: 'Evaluation' },
  { id: 'pdf',        icon: '📄', label: 'PDF Tools' },
  { id: 'analytics',  icon: '📊', label: 'Analytics' },
  { id: 'settings',   icon: '⚙️', label: 'Settings' },
];

export default function Sidebar({ onOpenPricing }) {
  const navigate = useNavigate();
  const { state, dispatch, logout } = useApp();

  const { state: subState, isActive, daysLeft } = useSubscription();
  const plan = subState.planId ? PLANS[subState.planId] : null;
  const user = state.authUser;

  function handleLogout() {
    if (window.confirm('Sign out of EvalAI?')) {
      // NOTE: we don't clear the subscription here — plan status now lives in
      // the database and is re-fetched fresh on next login, so it's always correct.
      logout();  // clear token + user
      navigate('/', { replace: true });
    }
  }

  function handleTabClick(tabId) {
    dispatch({ type: 'SET_TAB', payload: tabId });
    navigate(`/dashboard/${tabId}`);
  }

  return (
    <aside className={styles.sidebar}>
      {/* Brand */}
      <div className={styles.brand}>
        <div className={styles.brandIcon}><span>∑</span></div>
        <div className={styles.brandText}>
          <span className={styles.brandName}>EvalAI</span>
          <span className={styles.brandSub}>Exam Evaluator</span>
        </div>
      </div>

      <div className={styles.divider} />

      {/* Logged-in user info */}
      {user && (
        <div className={styles.userCard}>
          <div className={styles.userAvatar}>
            {user.name?.[0]?.toUpperCase() || '?'}
          </div>
          <div className={styles.userInfo}>
            <span className={styles.userName}>{user.name}</span>
            <span className={styles.userEmail}>{user.email}</span>
          </div>
          {/* Logout button removed from here */}
        </div>
      )}

      <div className={styles.divider} />

      {/* Plan badge */}
      {plan ? (
        <div className={styles.planBadge} style={{ borderColor: plan.color + '44', background: plan.bgGradient }}>
          <span className={styles.planBadgeIcon}>{plan.badge}</span>
          <div className={styles.planBadgeInfo}>
            <span className={styles.planBadgeName} style={{ color: plan.color }}>{plan.name} Plan</span>
            {daysLeft !== null && (
              <span className={styles.planBadgeDays}>
                {daysLeft > 0 ? `⏱️ ${daysLeft} day${daysLeft !== 1 ? 's' : ''} left` : '⚠️ Expired'}
              </span>
            )}
          </div>
        </div>
      ) : (
        <button className={styles.noPlanBtn} onClick={onOpenPricing}>⚡ Choose a Plan</button>
      )}

      <div className={styles.divider} />

      {/* Navigation */}
      <nav className={styles.nav}>
        {NAV_ITEMS.map((item) => {
          const locked = plan ? !canAccess(plan.id, item.id) : true;
          const active = state.activeTab === item.id;
          return (
            <button
              key={item.id}
              className={`${styles.navItem} ${active ? styles.active : ''} ${locked ? styles.locked : ''}`}
              onClick={() => handleTabClick(item.id)}
            >
              <span className={styles.navIcon}>{item.icon}</span>
              <span className={styles.navLabel}>{item.label}</span>
              {locked
                ? <span className={styles.lockIcon}>🔒</span>
                : active ? <span className={styles.navIndicator} /> : null}
            </button>
          );
        })}
      </nav>

      {plan && plan.id === 'silver' && (
        <div className={styles.upgradeCta}>
          <div className={styles.upgradeCtaText}>
            <strong>Unlock All Features</strong>
            <span>Upgrade to Gold</span>
          </div>
          <button className={styles.upgradeCtaBtn} onClick={onOpenPricing}>🥇 Upgrade</button>
        </div>
      )}

      <div className={styles.sidebarFooter}>
      {/* 1. Text Link */}
      <button className={styles.pricingLink} onClick={onOpenPricing}>
        💳 Manage Subscription
      </button>
      
      {/* 2. Boxed Button */}
      <button className={styles.logoutBtn} onClick={handleLogout}>
        ⏻ Logout
      </button>

      {/* 3. Version Tag */}
      <p className={styles.versionTag}>v2.0 — FAIR Eval</p>
    </div>
    </aside>
  );
}