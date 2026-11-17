// Redux store: one slice per area of the app. Redux DevTools picks it up
// automatically in development builds (configureStore enables it).
import { configureStore } from "@reduxjs/toolkit";
import applications from "./slices/applicationsSlice.js";
import assistant from "./slices/assistantSlice.js";
import auth, { logout } from "./slices/authSlice.js";
import events from "./slices/eventsSlice.js";
import jobs from "./slices/jobsSlice.js";
import saved from "./slices/savedSlice.js";

const ASSISTANT_KEY = "p4_assistant_thread";

function loadAssistant() {
  try {
    const stored = JSON.parse(sessionStorage.getItem(ASSISTANT_KEY));
    return stored ? { ...stored, loading: false, error: "" } : undefined;
  } catch {
    return undefined;
  }
}

const reducers = { auth, jobs, applications, events, saved, assistant };

// Signing out clears every user-specific slice.
function rootReducer(state, action) {
  if (action.type === logout.fulfilled.type) {
    sessionStorage.removeItem(ASSISTANT_KEY);
    state = { auth: state?.auth };
  }
  const next = {};
  for (const [key, reducer] of Object.entries(reducers)) {
    next[key] = reducer(state?.[key], action);
  }
  return next;
}

const assistantState = loadAssistant();

export const store = configureStore({
  reducer: rootReducer,
  preloadedState: assistantState ? { assistant: assistantState } : undefined,
  devTools: { name: "Pair 4 Handshake" },
});

// The conversation also survives a page reload in the same tab.
store.subscribe(() => {
  try {
    sessionStorage.setItem(ASSISTANT_KEY, JSON.stringify(store.getState().assistant));
  } catch {
    // Storage full or blocked: the in-memory store still keeps the thread.
  }
});
