"""
Kaivor Knowledge Prompt Builder
"""

from core.debug import Debug

class KnowledgePrompt:
    """Build prompts using retrieved knowledge."""

    @staticmethod
    def build(question, context):
        """Build an AI prompt."""

        if not context.strip():
            prompt = question
        else:
            prompt = f"""
You are answering questions using the user's personal knowledge library.

Answer ONLY from the supplied knowledge.

If the answer is not contained in the supplied knowledge, clearly state that.

====================
KNOWLEDGE
====================

{context}

====================
QUESTION
====================

{question}
""".strip()

        if Debug.rag:

            print()
            print("=" * 60)
            print("KAIVOR RAG DEBUG")
            print("=" * 60)
            print()
            print(prompt if context.strip() else "NO KNOWLEDGE RETRIEVED")
            print()
            print("=" * 60)
            print()

        return prompt
