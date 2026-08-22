import { createContext, useContext, useReducer, useEffect, useRef } from 'react';
import { canAccess, isTrialExpired, trialDaysRemaining } from './plans';
import { paymentsAPI } from '../services/api';
import { useApp } from '../context/AppContext';

function storageKey(userId) {
  return `evalai_subscription_${userId || 'anon'}`;
}

function loadFromStorage(userId) {
  try {
    const raw = localStorage.getItem(storageKey(userId));
    if (!raw) return null;
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

function saveToStorage(userId, planId, activatedAt) {
  try {
    localStorage.setItem(storageKey(userId), JSON.stringify({ planId, activatedAt }));
  } catch {}
}

function clearStorage(userId) {
  try {
    localStorage.removeItem(storageKey(userId));
  } catch {}
}

const initialState = {
  planId:      null,
  activatedAt: null,
  planLoading: true,
  showPricing: false,
  lockedTab:   null,
};

function reducer(state, action) {
  switch (action.type) {
    case 'HYDRATE_PLAN':
      return {
        ...state,
        planId:      action.payload.planId,
        activatedAt: action.payload.activatedAt,
        planLoading: false,
      };
    case 'ACTIVATE_PLAN': {
      const { planId } = action.payload;
      const activatedAt = Date.now();
      return { ...state, planId, activatedAt, showPricing: false, lockedTab: null };
    }
    case 'OPEN_PRICING':
      return { ...state, showPricing: true, lockedTab: action.payload?.lockedTab || null };
    case 'CLOSE_PRICING':
      return { ...state, showPricing: false, lockedTab: null };
    case 'CANCEL_PLAN':
      return { ...state, planId: null, activatedAt: null };
    case 'RESET_FOR_LOGOUT':
      return { ...initialState, planLoading: false };
    default:
      return state;
  }
}

const SubscriptionContext = createContext(null);

export function SubscriptionProvider({ children }) {
  const [state, dispatch] = useReducer(reducer, initialState);
  const { state: appState } = useApp();
  const authUser = appState.authUser;
  const authChecked = appState.authChecked;
  const userId = authUser?.id || authUser?._id || authUser?.email || null;

  const lastFetchedUserId = useRef(null);

  useEffect(() => {
    if (!authChecked) return;

    if (!authUser) {
      lastFetchedUserId.current = null;
      dispatch({ type: 'RESET_FOR_LOGOUT' });
      return;
    }

    if (lastFetchedUserId.current === userId) return;
    lastFetchedUserId.current = userId;

    const cached = loadFromStorage(userId);
    if (cached?.planId) {
      dispatch({ type: 'ACTIVATE_PLAN', payload: { planId: cached.planId } });
    }

    paymentsAPI
      .status()
      .then((res) => {
        const planId = res?.planId ?? null;
        const activatedAt = res?.activatedAt ?? null;
        dispatch({ type: 'HYDRATE_PLAN', payload: { planId, activatedAt } });
        if (planId) {
          saveToStorage(userId, planId, activatedAt);
        } else {
          clearStorage(userId);
        }
      })
      .catch(() => {
        dispatch({
          type: 'HYDRATE_PLAN',
          payload: { planId: cached?.planId ?? null, activatedAt: cached?.activatedAt ?? null },
        });
      });
  }, [authUser, authChecked, userId]);

  const isActive =
    state.planId !== null &&
    !(state.planId === 'free_trial' && isTrialExpired(state.activatedAt));

  const daysLeft =
    state.planId === 'free_trial'
      ? trialDaysRemaining(state.activatedAt)
      : null;

  function checkAccess(tabId) {
    if (!isActive) {
      dispatch({ type: 'OPEN_PRICING', payload: { lockedTab: tabId } });
      return false;
    }
    if (!canAccess(state.planId, tabId)) {
      dispatch({ type: 'OPEN_PRICING', payload: { lockedTab: tabId } });
      return false;
    }
    return true;
  }

  function activatePlan(planId) {
    saveToStorage(userId, planId, Date.now());
    dispatch({ type: 'ACTIVATE_PLAN', payload: { planId } });
  }

  function cancelPlan() {
    clearStorage(userId);
    dispatch({ type: 'CANCEL_PLAN' });
  }

  return (
    <SubscriptionContext.Provider
      value={{ state, dispatch, isActive, daysLeft, checkAccess, activatePlan, cancelPlan }}
    >
      {children}
    </SubscriptionContext.Provider>
  );
}

export function useSubscription() {
  return useContext(SubscriptionContext);
}