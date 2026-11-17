// The assistant conversation. It lives in the store (and sessionStorage),
// not in the Assistant page, so leaving the page and coming back keeps
// the thread; the conversation_id ties it to the server-side session.
import { createAsyncThunk, createSlice } from "@reduxjs/toolkit";
import * as api from "../../services/api.js";
import { fetchSavedItems } from "./savedSlice.js";

export const GREETING = {
  role: "assistant",
  content: "Hi! I can help you find jobs, discover events, review your preferences, and save opportunities. Type /memory to see what I remember, or /compact to shorten a long chat.",
};

export const sendMessage = createAsyncThunk("assistant/send", async (text, { getState, rejectWithValue }) => {
  try {
    return await api.chatWithAssistant(text, getState().assistant.conversationId);
  } catch (error) {
    return rejectWithValue(error.message);
  }
});

export const answerConfirmation = createAsyncThunk(
  "assistant/confirm",
  async (approved, { getState, dispatch, rejectWithValue }) => {
    try {
      const response = await api.confirmAssistantAction(getState().assistant.conversationId, approved);
      if (approved) dispatch(fetchSavedItems());
      return response;
    } catch (error) {
      return rejectWithValue(error.message);
    }
  }
);

// Ends the server session (memory layer 3 is discarded) and starts over.
export const startNewChat = createAsyncThunk("assistant/newChat", async (_, { getState }) => {
  const { conversationId } = getState().assistant;
  if (conversationId) {
    try {
      await api.endAssistantConversation(conversationId);
    } catch {
      // Already expired on the server.
    }
  }
});

const initialState = {
  conversationId: null,
  messages: [GREETING],
  pending: null,
  usage: null,
  lastTraceId: null,
  compactions: 0,
  loading: false,
  error: "",
};

function addReply(state, response) {
  state.loading = false;
  state.conversationId = response.conversation_id;
  state.pending = response.pending_action;
  state.usage = response.usage || state.usage;
  state.lastTraceId = response.trace_id;
  if (response.compaction) state.compactions += 1;
  state.messages.push({
    role: "assistant",
    content: response.answer,
    toolCalls: response.tool_calls,
    status: response.status,
    usage: response.usage,
    traceId: response.trace_id,
    compaction: response.compaction,
  });
}

const assistantSlice = createSlice({
  name: "assistant",
  initialState,
  reducers: {
    errorCleared(state) {
      state.error = "";
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(sendMessage.pending, (state, action) => {
        state.messages.push({ role: "user", content: action.meta.arg });
        state.loading = true;
        state.error = "";
      })
      .addCase(sendMessage.fulfilled, (state, action) => addReply(state, action.payload))
      .addCase(sendMessage.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload || "The assistant could not respond.";
        if ((action.payload || "").includes("Conversation not found")) state.conversationId = null;
      })
      .addCase(answerConfirmation.pending, (state, action) => {
        state.messages.push({ role: "user", content: action.meta.arg ? "Yes, save it." : "No, don't save it." });
        state.pending = null;
        state.loading = true;
        state.error = "";
      })
      .addCase(answerConfirmation.fulfilled, (state, action) => addReply(state, action.payload))
      .addCase(answerConfirmation.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload || "The assistant could not respond.";
      })
      .addCase(startNewChat.fulfilled, () => initialState);
  },
});

export const { errorCleared } = assistantSlice.actions;

export const selectConversation = (state) => state.assistant.messages;
export const selectConversationId = (state) => state.assistant.conversationId;
export const selectPendingAction = (state) => state.assistant.pending;
export const selectAssistantLoading = (state) => state.assistant.loading;
export const selectAssistantError = (state) => state.assistant.error;
export const selectTokenUsage = (state) => state.assistant.usage;
export const selectContextWarning = (state) => Boolean(state.assistant.usage?.warning);

export default assistantSlice.reducer;
