"""
Chat with the assistant in the terminal.

Every tool call is printed as one line, and the number of tool calls is
printed after each run. save_job_or_event asks for y/N confirmation.

    backend/.venv/bin/python backend/scripts/assistant_cli.py
    backend/.venv/bin/python backend/scripts/assistant_cli.py --email noprefs.student@example.edu --no-defense
"""

import argparse

from _common import SessionLocal, student_id_for

from app.assistant import AssistantSettings, OllamaModelClient, ToolContext, run_assistant


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--email", default="demo.student@example.edu", help="student to act as")
    parser.add_argument("--model", default=None, help="Ollama model (default: OLLAMA_MODEL or qwen3:8b)")
    parser.add_argument("--no-defense", action="store_true", help="turn off the untrusted-data defense")
    parser.add_argument("--no-repair", action="store_true", help="turn off the tool-call repair path")
    parser.add_argument("--no-think", action="store_true", help="turn off qwen3 reasoning (faster, less reliable)")
    args = parser.parse_args()

    db = SessionLocal()
    ctx = ToolContext(db=db, student_id=student_id_for(db, args.email), defended=not args.no_defense)
    client = OllamaModelClient(model=args.model, think=not args.no_think)
    settings = AssistantSettings(defended=not args.no_defense, repair=not args.no_repair)
    conversation: list[dict] = []

    print(f"Assistant ({client.model}) for {args.email}. Type 'new' to reset, 'quit' to exit.")

    while True:
        try:
            message = input("\nyou> ").strip()
        except (EOFError, KeyboardInterrupt):
            break

        if message.lower() in {"quit", "exit"}:
            break
        if message.lower() == "new":
            conversation.clear()
            print("(new conversation)")
            continue
        if not message:
            continue

        run = run_assistant(message, conversation, ctx=ctx, client=client, settings=settings)
        print(f"\nassistant> {run.answer}")

    db.close()


if __name__ == "__main__":
    main()
