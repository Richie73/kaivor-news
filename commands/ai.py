"""
Kaivor AI Shell
"""

from core.ai.engine import AIEngine


def run():

    ai = AIEngine()

    print("\nKaivor AI Shell")
    print("Type 'exit' to quit.")
    print("Type 'clear' to reset conversation.\n")

    while True:

        prompt = input("> ").strip()

        if prompt.lower() in ("exit", "quit", "q"):
            print("\nLeaving Kaivor AI Shell...\n")
            break

        if prompt.lower() == "clear":
            ai.conversation.clear()
            print("\nConversation cleared.\n")
            continue

        reply = ai.ask(
            "chat",
            prompt,
        )

        print()
        print(reply)
        print()
