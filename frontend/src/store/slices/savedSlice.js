// Jobs and events the student saved (from the Jobs page or the assistant).
import { createAsyncThunk, createSlice } from "@reduxjs/toolkit";
import * as api from "../../services/api.js";

export const fetchSavedItems = createAsyncThunk("saved/fetch", async (_, { rejectWithValue }) => {
  try {
    return await api.getSavedItems();
  } catch (error) {
    return rejectWithValue(error.message);
  }
});

export const saveItem = createAsyncThunk("saved/save", async ({ itemType, itemId }, { dispatch, rejectWithValue }) => {
  try {
    const result = await api.saveItem(itemType, itemId);
    dispatch(fetchSavedItems());
    return result;
  } catch (error) {
    return rejectWithValue(error.message);
  }
});

export const removeSavedItem = createAsyncThunk("saved/remove", async (savedId, { rejectWithValue }) => {
  try {
    await api.removeSavedItem(savedId);
    return savedId;
  } catch (error) {
    return rejectWithValue(error.message);
  }
});

const savedSlice = createSlice({
  name: "saved",
  initialState: { items: [], status: "idle", error: null },
  reducers: {},
  extraReducers: (builder) => {
    builder
      .addCase(fetchSavedItems.pending, (state) => {
        state.status = "loading";
      })
      .addCase(fetchSavedItems.fulfilled, (state, action) => {
        state.status = "idle";
        state.items = Array.isArray(action.payload) ? action.payload : [];
      })
      .addCase(fetchSavedItems.rejected, (state, action) => {
        state.status = "idle";
        state.error = action.payload;
      })
      .addCase(saveItem.rejected, (state, action) => {
        state.error = action.payload;
      })
      .addCase(removeSavedItem.fulfilled, (state, action) => {
        state.items = state.items.filter((item) => item.id !== action.payload);
      });
  },
});

export const selectSavedItems = (state) => state.saved.items;
export const selectSavedJobs = (state) => state.saved.items.filter((item) => item.item_type === "job");
export const selectSavedEvents = (state) => state.saved.items.filter((item) => item.item_type === "event");
export const selectIsSaved = (itemType, itemId) => (state) =>
  state.saved.items.some((item) => item.item_type === itemType && item.item_id === itemId);

export default savedSlice.reducer;
