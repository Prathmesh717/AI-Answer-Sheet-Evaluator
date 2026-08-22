import { useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useApp } from '../context/AppContext';
import { useSubscription } from '../subscription/SubscriptionContext';
import { canAccess } from '../subscription/plans';

import Sidebar from '../components/Sidebar';
import SubjectManager from '../components/SubjectManager';
import EvaluationPanel from '../components/EvaluationPanel';
import PDFTools from '../components/PDFTools';
import Analytics from '../components/Analytics';
import Settings from '../components/Settings';
import LockedOverlay from '../components/LockedOverlay';

import appStyles from '../App.module.css';

const VALID_TABS = ['subjects', 'evaluation', 'pdf', 'analytics', 'settings'];

const PANELS = {
  subjects:   <SubjectManager />,
  evaluation: <EvaluationPanel />,
  pdf:        <PDFTools />,
  analytics:  <Analytics />,
  settings:   <Settings />,
};

export default function Dashboard() {
  const { tab } = useParams();           // reads /dashboard/:tab from the URL
  const navigate = useNavigate();
  const { state, dispatch } = useApp();
  const { state: subState, isActive } = useSubscription();

  // Sync URL ↔ AppContext activeTab
  useEffect(() => {
    if (tab && VALID_TABS.includes(tab)) {
      // URL has a valid tab — sync into context
      if (state.activeTab !== tab) {
        dispatch({ type: 'SET_TAB', payload: tab });
      }
    } else {
      // No tab or invalid tab → redirect to /dashboard/subjects
      navigate(`/dashboard/${state.activeTab || 'subjects'}`, { replace: true });
    }
  }, [tab]);                        // eslint-disable-line react-hooks/exhaustive-deps

  // When context activeTab changes (e.g. Sidebar click), update the URL
  useEffect(() => {
    const currentTab = state.activeTab || 'subjects';
    if (tab !== currentTab) {
      navigate(`/dashboard/${currentTab}`, { replace: true });
    }
  }, [state.activeTab]);            // eslint-disable-line react-hooks/exhaustive-deps

  const activeTab = state.activeTab || 'subjects';
  const planId    = subState.planId;
  const isLocked  = !isActive || (planId && !canAccess(planId, activeTab));

  function handleOpenPricing() {
    navigate('/pricing');
  }

  return (
    <div className={appStyles.app}>
      <Sidebar onOpenPricing={handleOpenPricing} />
      <main className={appStyles.content}>
        {PANELS[activeTab]}
        {isLocked && (
          <LockedOverlay tabId={activeTab} onUpgrade={handleOpenPricing} />
        )}
      </main>
    </div>
  );
}