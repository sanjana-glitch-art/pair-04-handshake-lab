import { useState } from "react";
import { chatWithAssistant } from "../services/api.js";

function Assistant() {
  const [messages, setMessages] = useState([
    {
      role: "assistant",
      content:
        "Hi! I can help you find jobs, discover events, review your preferences, and save opportunities.",
    },
  ]);

  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(event) {
    event.preventDefault();

    const userMessage = input.trim();

    if (!userMessage || loading) {
      return;
    }

    const previousMessages = messages.map((message) => ({
      role: message.role,
      content: message.content,
    }));

    const updatedMessages = [
      ...messages,
      {
        role: "user",
        content: userMessage,
      },
    ];

    setMessages(updatedMessages);
    setInput("");
    setError("");
    setLoading(true);

    try {
      const response = await chatWithAssistant(
        userMessage,
        previousMessages
      );

      setMessages((currentMessages) => [
        ...currentMessages,
        {
          role: "assistant",
          content: response.answer,
        },
      ]);
    } catch (err) {
      setError(
        err.message || "The assistant could not respond."
      );
    } finally {
      setLoading(false);
    }
  }

  function useSuggestion(text) {
    setInput(text);
  }

  return (
    <div className="assistant-page">
      <div className="assistant-header">
        <div className="assistant-icon">✦</div>

        <div>
          <h1>Career Assistant</h1>

          <p>
            Ask me about jobs, events, and your saved preferences.
          </p>
        </div>
      </div>

      <div className="assistant-suggestions">
        <button
          type="button"
          onClick={() =>
            useSuggestion(
              "Find internship opportunities near San Jose."
            )
          }
        >
          Find internships near me
        </button>

        <button
          type="button"
          onClick={() =>
            useSuggestion(
              "Show me upcoming career events."
            )
          }
        >
          Show upcoming events
        </button>

        <button
          type="button"
          onClick={() =>
            useSuggestion(
              "What are my saved preferences?"
            )
          }
        >
          Review my preferences
        </button>
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
              {message.content}
            </div>
          ))}

          {loading && (
            <div className="assistant-message bot-message">
              Thinking...
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
            placeholder="Ask about jobs or events..."
            value={input}
            onChange={(event) =>
              setInput(event.target.value)
            }
            disabled={loading}
          />

          <button
            type="submit"
            disabled={loading || !input.trim()}
          >
            Send
          </button>
        </form>
      </div>
    </div>
  );
}

export default Assistant;