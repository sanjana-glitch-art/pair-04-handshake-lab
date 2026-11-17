// The student's applications. Submitting is asynchronous on the server
// (Kafka); the slice tracks the 202 "queued" answer and refreshes.
import { createAsyncThunk, createSlice } from "@reduxjs/toolkit";
import * as api from "../../services/api.js";

export const fetchMyApplications = createAsyncThunk("applications/fetchMine", async (status, { rejectWithValue }) => {
  try {
    return await api.getMyApplications(status || "");
  } catch (error) {
    return rejectWithValue(error.message);
  }
});

export const submitApplication = createAsyncThunk(
  "applications/submit",
  async ({ jobId, resume }, { rejectWithValue }) => {
    try {
      return await api.submitApplication(jobId, resume);
    } catch (error) {
      return rejectWithValue(error.message);
    }
  }
);

export const withdrawApplication = createAsyncThunk("applications/withdraw", async (applicationId, { rejectWithValue }) => {
  try {
    return await api.withdrawApplication(applicationId);
  } catch (error) {
    return rejectWithValue(error.message);
  }
});

const applicationsSlice = createSlice({
  name: "applications",
  initialState: {
    items: [],
    statusFilter: "",
    status: "idle",
    submitting: false,
    lastSubmitted: null,
    error: null,
  },
  reducers: {
    statusFilterChanged(state, action) {
      state.statusFilter = action.payload;
    },
    submissionCleared(state) {
      state.lastSubmitted = null;
      state.error = null;
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(fetchMyApplications.pending, (state) => {
        state.status = "loading";
        state.error = null;
      })
      .addCase(fetchMyApplications.fulfilled, (state, action) => {
        state.status = "idle";
        state.items = Array.isArray(action.payload) ? action.payload : [];
      })
      .addCase(fetchMyApplications.rejected, (state, action) => {
        state.status = "idle";
        state.error = action.payload || "Unable to load applications.";
      })
      .addCase(submitApplication.pending, (state) => {
        state.submitting = true;
        state.error = null;
        state.lastSubmitted = null;
      })
      .addCase(submitApplication.fulfilled, (state, action) => {
        state.submitting = false;
        state.lastSubmitted = action.payload;
      })
      .addCase(submitApplication.rejected, (state, action) => {
        state.submitting = false;
        state.error = action.payload || "Unable to submit application.";
      })
      .addCase(withdrawApplication.fulfilled, (state, action) => {
        const item = state.items.find((a) => a.id === action.payload.application_id);
        if (item) item.status = "Withdrawn";
      });
  },
});

export const { statusFilterChanged, submissionCleared } = applicationsSlice.actions;

export const selectApplications = (state) => state.applications.items;
export const selectApplicationFilter = (state) => state.applications.statusFilter;
export const selectApplicationsLoading = (state) => state.applications.status === "loading";
export const selectApplicationsError = (state) => state.applications.error;
export const selectSubmitting = (state) => state.applications.submitting;
export const selectLastSubmitted = (state) => state.applications.lastSubmitted;
export const selectAppliedJobIds = (state) => new Set(state.applications.items.map((a) => a.job_id));

export default applicationsSlice.reducer;
