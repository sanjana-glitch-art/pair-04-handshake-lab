// Events and registrations.
import { createAsyncThunk, createSlice } from "@reduxjs/toolkit";
import * as api from "../../services/api.js";

export const emptyEventFilters = { search: "", city: "" };

export const fetchEvents = createAsyncThunk("events/fetch", async (filters, { rejectWithValue }) => {
  try {
    return await api.getEvents(filters || {});
  } catch (error) {
    return rejectWithValue(error.message);
  }
});

export const fetchRegisteredEvents = createAsyncThunk("events/fetchRegistered", async (_, { rejectWithValue }) => {
  try {
    return await api.getRegisteredEvents();
  } catch (error) {
    return rejectWithValue(error.message);
  }
});

export const registerForEvent = createAsyncThunk("events/register", async (eventId, { rejectWithValue }) => {
  try {
    return { eventId, ...(await api.registerForEvent(eventId)) };
  } catch (error) {
    return rejectWithValue(error.message);
  }
});

const eventsSlice = createSlice({
  name: "events",
  initialState: {
    filters: emptyEventFilters,
    items: [],
    registrations: [],
    status: "idle",
    registeredStatus: "idle",
    message: "",
    error: null,
  },
  reducers: {
    eventFiltersChanged(state, action) {
      state.filters = { ...state.filters, ...action.payload };
    },
    eventFiltersReset(state) {
      state.filters = emptyEventFilters;
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(fetchEvents.pending, (state) => {
        state.status = "loading";
        state.error = null;
      })
      .addCase(fetchEvents.fulfilled, (state, action) => {
        state.status = "idle";
        state.items = Array.isArray(action.payload) ? action.payload : [];
      })
      .addCase(fetchEvents.rejected, (state, action) => {
        state.status = "idle";
        state.items = [];
        state.error = action.payload || "Unable to load events.";
      })
      .addCase(fetchRegisteredEvents.pending, (state) => {
        state.registeredStatus = "loading";
      })
      .addCase(fetchRegisteredEvents.fulfilled, (state, action) => {
        state.registeredStatus = "idle";
        state.registrations = Array.isArray(action.payload) ? action.payload : [];
      })
      .addCase(fetchRegisteredEvents.rejected, (state, action) => {
        state.registeredStatus = "idle";
        state.error = action.payload || "Unable to load registered events.";
      })
      .addCase(registerForEvent.pending, (state) => {
        state.message = "";
        state.error = null;
      })
      .addCase(registerForEvent.fulfilled, (state, action) => {
        state.message = action.payload.message || "Successfully registered for the event.";
        const event = state.items.find((item) => item.id === action.payload.eventId);
        if (event) event.is_registered = true;
      })
      .addCase(registerForEvent.rejected, (state, action) => {
        state.error = action.payload || "Unable to register for the event.";
      });
  },
});

export const { eventFiltersChanged, eventFiltersReset } = eventsSlice.actions;

export const selectEventFilters = (state) => state.events.filters;
export const selectEvents = (state) => state.events.items;
export const selectEventsLoading = (state) => state.events.status === "loading";
export const selectEventsError = (state) => state.events.error;
export const selectEventsMessage = (state) => state.events.message;
export const selectRegistrations = (state) => state.events.registrations;
export const selectRegistrationsLoading = (state) => state.events.registeredStatus === "loading";

export default eventsSlice.reducer;
