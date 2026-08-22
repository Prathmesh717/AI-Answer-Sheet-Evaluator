import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AppProvider, useApp } from './context/AppContext';
import { SubscriptionProvider, useSubscription } from './subscription/SubscriptionContext';
import styles from './App.module.css';

import HomePage     from './Pages/HomePage';
import LoginPage    from './Pages/LoginPage';
import RegisterPage from './Pages/RegisterPage';
import PricingPage  from './Pages/Pricingpage';
import Dashboard    from './Pages/Dashboard';

// ── Spinner ───────────────────────────────────────────────────────────────────
function FullPageSpinner() {
  return (
    <div style={{
      minHeight: '100vh', display: 'flex',
      alignItems: 'center', justifyContent: 'center', background: '#0a0c10',
    }}>
      <div style={{
        width: 32, height: 32,
        border: '2px solid rgba(56,189,248,.2)',
        borderTopColor: '#38bdf8', borderRadius: '50%',
        animation: 'spin .8s linear infinite',
      }} />
    </div>
  );
}

// ── Auth guard: not logged in → /login ───────────────────────────────────────
function RequireAuth({ children }) {
  const { state } = useApp();
  if (state.authLoading) return <FullPageSpinner />;
  if (!state.authUser)   return <Navigate to="/login" replace />;
  return children;
}

// ── Guest guard: already logged in → /dashboard ──────────────────────────────
function GuestOnly({ children }) {
  const { state } = useApp();
  if (state.authLoading) return <FullPageSpinner />;
  if (state.authUser)    return <Navigate to="/dashboard" replace />;
  return children;
}

// ── Pricing guard: already has active plan → skip pricing, go to /dashboard ──
function RequirePlan({ children }) {
  const { isActive, state } = useSubscription();
  if (state.planLoading) return <FullPageSpinner />;
  if (isActive) return <Navigate to="/dashboard" replace />;
  return children;
}

// ── Dashboard guard: no active plan → go choose one at /pricing ──────────────
function RequireActivePlan({ children }) {
  const { isActive, state } = useSubscription();
  if (state.planLoading) return <FullPageSpinner />;
  if (!isActive) return <Navigate to="/pricing" replace />;
  return children;
}

// ── Router ────────────────────────────────────────────────────────────────────
function AppRouter() {
  const { login, register } = useApp();

  return (
    <Routes>
      {/* Public */}
      <Route path="/"         element={<HomePage />} />
      <Route path="/login"    element={<GuestOnly><LoginPage    onLogin={login}       onNavigate={() => {}} /></GuestOnly>} />
      <Route path="/register" element={<GuestOnly><RegisterPage onRegister={register} onNavigate={() => {}} /></GuestOnly>} />

      {/* Pricing: must be logged in; if plan already active → skip to dashboard */}
      <Route
        path="/pricing"
        element={
          <RequireAuth>
            <RequirePlan>
              <PricingPage />
            </RequirePlan>
          </RequireAuth>
        }
      />

      {/* Dashboard: must be logged in AND have active plan */}
      <Route
        path="/dashboard"
        element={
          <RequireAuth>
            <RequireActivePlan>
              <Dashboard />
            </RequireActivePlan>
          </RequireAuth>
        }
      />
      <Route
        path="/dashboard/:tab"
        element={
          <RequireAuth>
            <RequireActivePlan>
              <Dashboard />
            </RequireActivePlan>
          </RequireAuth>
        }
      />

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

// ── Entry point ───────────────────────────────────────────────────────────────
export default function App() {
  return (
    <BrowserRouter>
      <AppProvider>
        {/* ONE SubscriptionProvider at the root so plan state is shared everywhere */}
        <SubscriptionProvider>
          <div className={styles.app}>
            <div className={styles.content}>
              <AppRouter />
            </div>
          </div>
        </SubscriptionProvider>
      </AppProvider>
    </BrowserRouter>
  );
}