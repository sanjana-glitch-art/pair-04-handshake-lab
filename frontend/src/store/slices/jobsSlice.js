// Jobs and companies: search filters and results, the selected posting,
// and company details collected from postings the student opened.
import { createAsyncThunk, createSlice } from "@reduxjs/toolkit";
import * as api from "../../services/api.js";

export const emptyJobFilters = { search: "", category: "", city: "", remote: "", min_salary: "" };

export const searchJobs = createAsyncThunk("jobs/search", async (filters, { rejectWithValue }) => {
  try {
    return await api.searchJobs(filters);
  } catch (error) {
    return rejectWithValue(error.message);
  }
});

export const fetchJobDetails = createAsyncThunk("jobs/fetchDetails", async (jobId, { rejectWithValue }) => {
  try {
    return await api.getJobDetails(jobId);
  } catch (error) {
    return rejectWithValue(error.message);
  }
});

const jobsSlice = createSlice({
  name: "jobs",
  initialState: {
    filters: emptyJobFilters,
    results: [],
    selectedJobId: null,
    detailsById: {},
    companiesByName: {},
    status: "idle",
    detailsStatus: "idle",
    error: null,
    lastSearchedAt: null,
  },
  reducers: {
    filtersChanged(state, action) {
      state.filters = { ...state.filters, ...action.payload };
    },
    filtersReset(state) {
      state.filters = emptyJobFilters;
    },
    jobSelected(state, action) {
      state.selectedJobId = action.payload;
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(searchJobs.pending, (state) => {
        state.status = "loading";
        state.error = null;
      })
      .addCase(searchJobs.fulfilled, (state, action) => {
        state.status = "idle";
        state.results = action.payload;
        state.lastSearchedAt = Date.now();
        if (!action.payload.some((job) => job.id === state.selectedJobId)) {
          state.selectedJobId = action.payload[0]?.id ?? null;
        }
      })
      .addCase(searchJobs.rejected, (state, action) => {
        state.status = "idle";
        state.results = [];
        state.error = action.payload || "Unable to load jobs.";
      })
      .addCase(fetchJobDetails.pending, (state) => {
        state.detailsStatus = "loading";
      })
      .addCase(fetchJobDetails.fulfilled, (state, action) => {
        const job = action.payload;
        state.detailsStatus = "idle";
        state.detailsById[job.id] = job;
        state.companiesByName[job.company_name] = {
          name: job.company_name,
          location: job.company_location,
          description: job.company_description,
          contact_email: job.contact_email,
          contact_phone: job.contact_phone,
        };
      })
      .addCase(fetchJobDetails.rejected, (state, action) => {
        state.detailsStatus = "idle";
        state.error = action.payload || "Unable to load job details.";
      });
  },
});

export const { filtersChanged, filtersReset, jobSelected } = jobsSlice.actions;

export const selectJobFilters = (state) => state.jobs.filters;
export const selectJobResults = (state) => state.jobs.results;
export const selectJobsLoading = (state) => state.jobs.status === "loading";
export const selectJobsError = (state) => state.jobs.error;
export const selectSelectedJobId = (state) => state.jobs.selectedJobId;
export const selectSelectedJob = (state) => state.jobs.detailsById[state.jobs.selectedJobId] || null;
export const selectJobById = (jobId) => (state) => state.jobs.detailsById[jobId] || null;
export const selectDetailsLoading = (state) => state.jobs.detailsStatus === "loading";
export const selectCompanies = (state) => state.jobs.companiesByName;

export default jobsSlice.reducer;
