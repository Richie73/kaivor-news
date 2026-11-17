"""
Kaivor auto-remembering (FP115).

After a chat reply, a second provider call asks what (if anything)
in the exchange is worth remembering long-term. Candidates are
checked against existing memories so the same fact is never saved
twice, then stored with source "auto". Everything here is best
effort: a failure returns (0, 0) and never breaks chat.

distinctive_words() also serves FP112's recall (main.py's
memory_context_for_chat): the stopword list lives here so both
features match memories on the same words.
"""

import json
import re

from core.ai.request import AIRequest
from core.memory.models import Memory
from core.providers.manager import ProviderManager

AUTO_REMEMBER_MIN_USER_CHARS = 20
AUTO_REMEMBER_MAX_MEMORIES = 3
AUTO_REMEMBER_MAX_TITLE_CHARS = 200
AUTO_REMEMBER_MAX_CONTENT_CHARS = 4000
AUTO_REMEMBER_MAX_TRANSCRIPT_CHARS = 2000
# A candidate is a duplicate when its title matches an existing
# memory, or it shares this many distinctive words with one.
AUTO_REMEMBER_DUPLICATE_WORDS = 3

AUTO_REMEMBER_PROMPT = (
    "You extract durable facts worth remembering about the user from a chat exchange. "
    'Reply with ONLY this JSON, no other text: {"memories": [{"title": "...", "content": "...", "category": "..."}]}. '
    'Use "general" as the category unless the fact clearly fits "work", "home", "health", "finance" or "travel". '
    "Save only facts that will still be true and useful in a month: the user's preferences, their situation, "
    "decisions they made, things they own or do regularly. "
    "Do NOT save: questions with no durable answer, prices or news (they change), one-off small talk, "
    "anything about the assistant itself, or anything secret (passwords, codes, account numbers). "
    'If nothing is worth remembering, reply {"memories": []}.'
)

# FP112: words too common to match a memory on. Anything shorter
# than four letters is skipped as well, so "the", "what", "when"
# and "does" never trigger a recall or count as a duplicate.
_STOPWORDS = frozenset({
    "about", "after", "again", "before", "could", "does", "doing",
    "dont", "from", "have", "here", "how", "just", "know", "like",
    "much", "many", "more", "most", "need", "only", "other", "over",
    "please", "really", "right", "should", "some", "tell", "than",
    "that", "them", "then", "there", "these", "thing", "think",
    "this", "those", "very", "want", "was", "were", "what", "when",
    "where", "which", "while", "who", "will", "with", "would", "you",
    "your",
})


def distinctive_words(text, limit=8):
    """Distinctive words in text: 4+ letters, not a stopword, in order, deduped.

    limit caps the result (8 for recall); None returns every match.
    """
    words = []
    for raw in (text or "").lower().split():
        word = "".join(ch for ch in raw if ch.isalnum()).lower()
        if len(word) < 4 or word in _STOPWORDS or word in words:
            continue
        words.append(word)
        if limit is not None and len(words) >= limit:
            break
    return words


def parse_extracted_memories(text):
    """Parse the extraction model's reply into validated candidates.

    Returns a list of (title, content, category) — at most three,
    titles capped at 200 chars, content at 4000. Anything
    unparseable yields an empty list.
    """
    if not text:
        return []
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        data = json.loads(cleaned)
    except (ValueError, TypeError):
        return []
    if not isinstance(data, dict):
        return []
    memories = data.get("memories")
    if not isinstance(memories, list):
        return []
    parsed = []
    for item in memories:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title") or "").strip()
        content = str(item.get("content") or "").strip()
        if not title or not content:
            continue
        category = str(item.get("category") or "general").strip()[:50] or "general"
        parsed.append((
            title[:AUTO_REMEMBER_MAX_TITLE_CHARS],
            content[:AUTO_REMEMBER_MAX_CONTENT_CHARS],
            category,
        ))
        if len(parsed) >= AUTO_REMEMBER_MAX_MEMORIES:
            break
    return parsed


def memory_already_saved(candidate_title, candidate_content, existing):
    """True when a candidate duplicates an existing memory."""
    title = (candidate_title or "").strip().lower()
    candidate_words = set(distinctive_words(
        f"{candidate_title} {candidate_content}", limit=None
    ))
    for memory in existing:
        if title and title == (memory.title or "").strip().lower():
            return True
        existing_words = set(distinctive_words(
            f"{memory.title} {memory.content}", limit=None
        ))
        if len(candidate_words & existing_words) >= AUTO_REMEMBER_DUPLICATE_WORDS:
            return True
    return False


def extract_and_save_memories(user_text, assistant_text, manager=None, remember=None, recall=None):
    """Extract durable facts from one chat exchange and save the new ones.

    Returns (saved, skipped): saved is the number of memories
    stored, skipped the number of candidates dropped as duplicates.
    Any failure returns (0, 0) — auto-remembering never breaks chat.
    """
    user_text = user_text or ""
    if len(user_text.strip()) < AUTO_REMEMBER_MIN_USER_CHARS:
        return (0, 0)
    try:
        if manager is None:
            manager = ProviderManager()
        transcript = (
            f"User: {user_text[:AUTO_REMEMBER_MAX_TRANSCRIPT_CHARS]}\n\n"
            f"Assistant: {(assistant_text or '')[:AUTO_REMEMBER_MAX_TRANSCRIPT_CHARS]}"
        )
        _, reply = manager.generate_with_fallback(
            AIRequest(
                system=AUTO_REMEMBER_PROMPT,
                user=transcript,
                temperature=0.1,
                max_tokens=500,
            )
        )
        candidates = parse_extracted_memories(reply)
        if not candidates:
            return (0, 0)
        if recall is None:
            from core.memory.api import recall as recall_memories

            recall = recall_memories
        if remember is None:
            from core.memory.api import remember as remember_memory

            remember = remember_memory
        existing = list(recall())
        saved = 0
        skipped = 0
        for title, content, category in candidates:
            if memory_already_saved(title, content, existing):
                skipped += 1
                continue
            remember(category, title, content, source="auto")
            saved += 1
            # Newly saved candidates count for the rest of this batch,
            # so two near-duplicates in one reply don't both land.
            existing.append(Memory(id=None, category=category, title=title, content=content))
        return (saved, skipped)
    except Exception:
        return (0, 0)
