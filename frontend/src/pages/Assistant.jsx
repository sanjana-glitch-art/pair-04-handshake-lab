import { useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import {
  answerConfirmation as answerConfirmationThunk,
  selectAssistantError,
  selectAssistantLoading,
  selectConversation,
  selectPendingAction,
  selectTokenUsage,
  sendMessage,
  startNewChat as startNewChatThunk,
} from "../store/slices/assistantSlice.js";

const SUGGESTIONS = [
  ["Find internships in my city", "Find an internship in my city."],
  ["Remote data science internships", "Find a remote data science internship that matches my Python and SQL skills."],
  ["CS events next month", "Find an event for computer science students next month."],
  ["Review my preferences", "What are my saved preferences?"],
  ["What do you remember?", "/memory"],
];

// Tokens used by the last model call and how full the context window is.
function TokenMeter({ usage }) {
  if (!usage) {
    return null;
  }

  const percent = Math.min(100, usage.context_percent);
  const barClass = usage.warning ? "bg-danger" : percent > 50 ? "bg-warning" : "bg-success";

  return (
    <div className="px-3 pt-2 small" data-testid="token-meter">
      <div className="d-flex justify-content-between text-muted">
        <span>
          Tokens: {usage.prompt_tokens.toLocaleString()} prompt + {usage.completion_tokens.toLocaleString()} completion
        </span>
        <span>
          {usage.context_percent}% of {usage.context_window.toLocaleString()}-token context
        </span>
      </div>
      <div className="progress" style={{ height: 6 }}>
        <div className={`progress-bar ${barClass}`} style={{ width: `${percent}%` }} />
      </div>
      {usage.warning && (
        <div className="alert alert-warning py-1 px-2 mt-2 mb-0">
          This conversation is using over 70% of the model's context window. Type /compact to summarize it,
          or start a new chat.
        </div>
      )}
    </div>
  );
}

// Shows the tool calls the agent loop made for one answer.
function ToolTrace({ calls }) {
  if (!calls?.length) {
    return null;
  }

  return (
    <details className="small mt-2">
      <summary className="text-muted">
        {calls.length} tool call{calls.length === 1 ? "" : "s"}
      </summary>
      <ol className="mb-0 ps-3">
        {calls.map((call, index) => (
          <li key={index} className={call.valid ? "" : "text-danger"}>
            <code>{call.name}</code>{" "}
            <code className="text-muted">
              {call.arguments ? JSON.stringify(call.arguments) : "(unparseable)"}
            </code>
            {!call.valid && " — rejected"}
          </li>
        ))}
      </ol>
    </details>
  );
}

function Assistant() {
  const dispatch = useDispatch();

  // The thread lives in the Redux assistant slice, so leaving this page
  // and coming back keeps it.
  const messages = useSelector(selectConversation);
  const pending = useSelector(selectPendingAction);
  const loading = useSelector(selectAssistantLoading);
  const error = useSelector(selectAssistantError);
  const usage = useSelector(selectTokenUsage);
  const [input, setInput] = useState("");

  function send(text) {
    const userMessage = text.trim();

    if (!userMessage || loading || pending) {
      return;
    }

    setInput("");
    dispatch(sendMessage(userMessage));
  }

  function answerConfirmation(approved) {
    dispatch(answerConfirmationThunk(approved));
  }

  function startNewChat() {
    dispatch(startNewChatThunk());
  }

  function handleSubmit(event) {
    event.preventDefault();
    send(input);
  }

  return (
    <div className="assistant-page">
      <div className="assistant-header">
        <div className="assistant-icon">✦</div>

        <div className="flex-grow-1">
          <h1>Career Assistant</h1>

          <p>
            Ask me about jobs, events, and your saved preferences.
          </p>
        </div>

        <button
          type="button"
          className="btn btn-outline-secondary btn-sm"
          onClick={startNewChat}
          disabled={loading}
        >
          New chat
        </button>
      </div>

      <div className="assistant-suggestions">
        {SUGGESTIONS.map(([label, text]) => (
          <button
            key={label}
            type="button"
            onClick={() => setInput(text)}
            disabled={loading || Boolean(pending)}
          >
            {label}
          </button>
        ))}
      </div>

      <div className="assistant-chat-card">
        <TokenMeter usage={usage} />

        <div className="assistant-messages">
          {messages.map((message, index) => (
            <div
              key={`${message.role}-${index}`}
              className={
                message.role === "user"
                  ? "assistant-message user-message"
                  : "assistant-message bot-message"
              }
            >
              <div style={{ whiteSpace: "pre-wrap" }}>{message.content}</div>
              <ToolTrace calls={message.toolCalls} />
            </div>
          ))}

          {pending && !loading && (
            <div className="assistant-message bot-message">
              <div className="fw-semibold mb-2">{pending.description}?</div>
              <div className="d-flex gap-2">
                <button
                  type="button"
                  className="btn btn-primary btn-sm"
                  onClick={() => answerConfirmation(true)}
                >
                  Yes, save
                </button>
                <button
                  type="button"
                  className="btn btn-outline-secondary btn-sm"
                  onClick={() => answerConfirmation(false)}
                >
                  No
                </button>
              </div>
            </div>
          )}

          {loading && (
            <div className="assistant-message bot-message">
              Thinking... (the local model can take up to a minute)
            </div>
          )}
        </div>

        {error && (
          <div className="alert alert-danger mx-3">
            {error}
          </div>
        )}

        <form
          className="assistant-input-row"
          onSubmit={handleSubmit}
        >
          <input
            type="text"
            placeholder={
              pending ? "Answer the confirmation above first" : "Ask about jobs or events..."
            }
            value={input}
            onChange={(event) =>
              setInput(event.target.value)
            }
            disabled={loading || Boolean(pending)}
          />

          <button
            type="submit"
            disabled={loading || Boolean(pending) || !input.trim()}
          >
            Send
          </button>
        </form>
      </div>
    </div>
  );
}

export default Assistant;
