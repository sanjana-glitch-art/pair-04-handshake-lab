import { useState } from "react";
import {
  chatWithAssistant,
  confirmAssistantAction,
} from "../services/api.js";

const GREETING = {
  role: "assistant",
  content:
    "Hi! I can help you find jobs, discover events, review your preferences, and save opportunities.",
};

const SUGGESTIONS = [
  ["Find internships in my city", "Find an internship in my city."],
  ["Remote data science internships", "Find a remote data science internship that matches my Python and SQL skills."],
  ["CS events next month", "Find an event for computer science students next month."],
  ["Review my preferences", "What are my saved preferences?"],
];

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
  const [messages, setMessages] = useState([GREETING]);
  const [conversationId, setConversationId] = useState(null);
  const [pending, setPending] = useState(null);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  function addAssistantReply(response) {
    setConversationId(response.conversation_id);
    setPending(response.pending_action);
    setMessages((current) => [
      ...current,
      {
        role: "assistant",
        content: response.answer,
        toolCalls: response.tool_calls,
      },
    ]);
  }

  async function send(text) {
    const userMessage = text.trim();

    if (!userMessage || loading || pending) {
      return;
    }

    setMessages((current) => [...current, { role: "user", content: userMessage }]);
    setInput("");
    setError("");
    setLoading(true);

    try {
      addAssistantReply(await chatWithAssistant(userMessage, conversationId));
    } catch (err) {
      setError(err.message || "The assistant could not respond.");
    } finally {
      setLoading(false);
    }
  }

  async function answerConfirmation(approved) {
    setMessages((current) => [
      ...current,
      { role: "user", content: approved ? "Yes, save it." : "No, don't save it." },
    ]);
    setPending(null);
    setError("");
    setLoading(true);

    try {
      addAssistantReply(await confirmAssistantAction(conversationId, approved));
    } catch (err) {
      setError(err.message || "The assistant could not respond.");
    } finally {
      setLoading(false);
    }
  }

  function startNewChat() {
    setMessages([GREETING]);
    setConversationId(null);
    setPending(null);
    setError("");
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
