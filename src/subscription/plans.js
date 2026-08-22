// ── Subscription Plans Configuration ──────────────────────────────
// Each plan defines which sidebar tabs / features are accessible.

export const PLANS = {
  free_trial: {
    id: 'free_trial',
    name: 'Free Trial',
    tagline: '5-day full access — no card needed',
    price: 0,
    priceLabel: 'Free',
    durationDays: 5,
    badge: '⏱️',
    color: '#6B7280',
    accentColor: '#9CA3AF',
    bgGradient: 'linear-gradient(135deg, #F9FAFB 0%, #F3F4F6 100%)',
    borderColor: '#E5E7EB',
    allowedTabs: ['subjects', 'evaluation', 'pdf', 'analytics', 'settings'],
    features: [
      { text: 'All features unlocked', included: true },
      { text: '5 days access only', included: true },
      { text: 'Subject Manager', included: true },
      { text: 'Evaluation Engine', included: true },
      { text: 'PDF OCR Tools', included: true },
      { text: 'Analytics Dashboard', included: true },
      { text: 'Email Reports', included: true },
      { text: 'Priority Support', included: false },
      { text: 'Unlimited Students', included: false },
    ],
  },

  silver: {
    id: 'silver',
    name: 'Silver',
    tagline: 'Core evaluation tools for educators',
    price: 9.99,
    priceLabel: '₹299',
    durationDays: null, // ongoing
    badge: '🥈',
    color: '#64748B',
    accentColor: '#94A3B8',
    bgGradient: 'linear-gradient(135deg, #F8FAFC 0%, #E2E8F0 100%)',
    borderColor: '#CBD5E1',
    allowedTabs: ['subjects', 'evaluation'],
    features: [
      { text: 'Subject Manager', included: true },
      { text: 'Evaluation Engine', included: true },
      { text: 'PDF OCR Tools', included: false },
      { text: 'Analytics Dashboard', included: false },
      { text: 'Email Reports', included: false },
      { text: 'Priority Support', included: false },
      { text: 'Unlimited Students', included: false },
    ],
  },

  gold: {
    id: 'gold',
    name: 'Gold',
    tagline: 'Full power — unlimited everything',
    price: 24.99,
    priceLabel: '₹699',
    durationDays: null,
    badge: '🥇',
    color: '#D97706',
    accentColor: '#F59E0B',
    bgGradient: 'linear-gradient(135deg, #FFFBEB 0%, #FEF3C7 100%)',
    borderColor: '#FCD34D',
    allowedTabs: ['subjects', 'evaluation', 'pdf', 'analytics', 'settings'],
    features: [
      { text: 'Subject Manager', included: true },
      { text: 'Evaluation Engine', included: true },
      { text: 'PDF OCR Tools', included: true },
      { text: 'Analytics Dashboard', included: true },
      { text: 'Email Reports', included: true },
      { text: 'Priority Support', included: true },
      { text: 'Unlimited Students', included: true },
    ],
    popular: true,
  },
};

// Tab access labels for display
export const TAB_META = {
  subjects:    { label: 'Subject Manager',   icon: '📚' },
  evaluation:  { label: 'Evaluation Engine', icon: '🎯' },
  pdf:         { label: 'PDF OCR Tools',     icon: '📄' },
  analytics:   { label: 'Analytics',         icon: '📊' },
  settings:    { label: 'Settings',          icon: '⚙️' },
};

// Check if a plan can access a given tab
export function canAccess(planId, tabId) {
  const plan = PLANS[planId];
  if (!plan) return false;
  return plan.allowedTabs.includes(tabId);
}

// Check if trial has expired
export function isTrialExpired(activatedAt) {
  if (!activatedAt) return false;
  const now = Date.now();
  const fiveDays = 5 * 24 * 60 * 60 * 1000;
  return now - activatedAt > fiveDays;
}

// Get days remaining for trial
export function trialDaysRemaining(activatedAt) {
  if (!activatedAt) return 5;
  const now = Date.now();
  const fiveDays = 5 * 24 * 60 * 60 * 1000;
  const elapsed = now - activatedAt;
  return Math.max(0, Math.ceil((fiveDays - elapsed) / (24 * 60 * 60 * 1000)));
}
