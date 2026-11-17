// Authentication and session: the JWT, the role it carries, and expiry.
import { createAsyncThunk, createSlice } from "@reduxjs/toolkit";
import * as api from "../../services/api.js";

function decode(token) {
  try {
    return JSON.parse(atob(token.split(".")[1].replace(/-/g, "+").replace(/_/g, "/")));
  } catch {
    return null;
  }
}

// The stored token, or null (and cleared) once it has expired.
function storedToken() {
  const token = localStorage.getItem("access_token");
  const payload = token && decode(token);
  if (!payload || (payload.exp && payload.exp * 1000 < Date.now())) {
    localStorage.removeItem("access_token");
    return null;
  }
  return token;
}

function sessionFrom(token) {
  const payload = token ? decode(token) : null;
  return {
    token,
    userRole: payload?.role || null,
    userId: payload?.sub ? Number(payload.sub) : null,
    expiresAt: payload?.exp ? payload.exp * 1000 : null,
  };
}

export const login = createAsyncThunk("auth/login", async (credentials, { rejectWithValue }) => {
  try {
    const data = await api.login(credentials);
    localStorage.setItem("access_token", data.access_token);
    return data.access_token;
  } catch (error) {
    return rejectWithValue(error.message);
  }
});

// Ends the server-side session too, so the token stops working at once.
export const logout = createAsyncThunk("auth/logout", async () => {
  try {
    await api.logout();
  } catch {
    // Already expired or offline: clearing the client is enough.
  }
  localStorage.removeItem("access_token");
});

const authSlice = createSlice({
  name: "auth",
  initialState: { ...sessionFrom(storedToken()), status: "idle", error: null },
  reducers: {
    sessionExpired(state) {
      Object.assign(state, sessionFrom(null), { error: "Your session expired. Please sign in again." });
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(login.pending, (state) => {
        state.status = "loading";
        state.error = null;
      })
      .addCase(login.fulfilled, (state, action) => {
        Object.assign(state, sessionFrom(action.payload), { status: "idle" });
      })
      .addCase(login.rejected, (state, action) => {
        state.status = "idle";
        state.error = action.payload || "Sign-in failed.";
      })
      .addCase(logout.fulfilled, (state) => {
        Object.assign(state, sessionFrom(null), { status: "idle", error: null });
      });
  },
});

export const { sessionExpired } = authSlice.actions;

export const selectToken = (state) => state.auth.token;
export const selectUserRole = (state) => state.auth.userRole;
export const selectIsAuthenticated = (state) => Boolean(state.auth.token);
export const selectIsStudent = (state) => state.auth.userRole === "student";
export const selectIsCompany = (state) => state.auth.userRole === "company";

export default authSlice.reducer;
