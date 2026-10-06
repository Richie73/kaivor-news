"""Evidence-first story intelligence for Kaivor News.

FP012 improves on FP011 by separating:
- reports from unique sources;
- corroboration from same-source related coverage;
- deterministic evidence summaries from optional AI interpretation.

The deterministic layer never claims that a story is true merely because it
appears in multiple feeds. It reports what Kaivor currently has evidence for
and explicitly marks what remains unverified.
"""
from __future__ import annotations

import hashlib
import re
from difflib import SequenceMatcher
from typing import Any

from evidence_engine import build_evidence_model, evidence_sentence
from story_timeline import build_story_timeline
from importance_engine import build_importance_model
from personal_relevance import calculate_personal_relevance, load_profile

STOPWORDS = {
    "a","an","and","are","as","at","be","been","being","but","by","for",
    "from","had","has","have","he","her","his","in","into","is","it","its",
    "of","on","or","that","the","their","this","to","was","were","will","with",
    "after","before","about","over","under","new","says","said","how","what","why",
    "who","when","where","which","while","than","more","also","could","would","should",
    "first","latest","report","reports","watch","news","update","live","today",
}

IMPACT_RULES = [
    ("war", ("war", "strike", "strikes", "drone", "missile", "attack", "troops", "military", "ceasefire", "russia", "ukraine", "iran", "israel", "gaza", "houthi"),
     "This concerns an active conflict or security event. If confirmed, developments of this type can affect civilian safety, infrastructure, military operations and the wider course of the conflict."),
    ("infrastructure", ("bridge", "airport", "rail", "railway", "power", "grid", "pipeline", "port", "road", "station", "infrastructure"),
     "This concerns infrastructure that can affect movement, essential services or economic activity. If the reported damage is confirmed, disruption could extend beyond the immediate incident."),
    ("politics", ("government", "minister", "chancellor", "president", "prime minister", "election", "parliament", "vote", "law", "policy", "resign"),
     "This could affect government decisions, public policy or political stability. The practical impact depends on what action follows the reported development."),
    ("economy", ("inflation", "interest rate", "rates", "jobs", "employment", "recession", "gdp", "economy", "market", "markets", "bank", "tariff", "trade"),
     "This could affect prices, borrowing, employment, trade or financial markets. The scale of the impact depends on whether the development persists and how markets or policymakers respond."),
    ("technology", ("ai", "artificial intelligence", "chip", "semiconductor", "cyber", "hack", "software", "robot", "model", "data breach"),
     "This could affect technology capability, competition, security or how a product or service is used. The longer-term significance depends on adoption, verification and follow-up."),
    ("science", ("study", "research", "trial", "scientists", "discovery", "climate", "vaccine", "disease", "space", "nasa"),
     "The significance depends on the strength of the underlying evidence and whether the finding survives independent verification or further research."),
    ("sport", ("football", "goal", "match", "tournament", "world cup", "championship", "player", "manager", "transfer"),
     "The immediate significance is mainly sporting: it may affect results, qualification, selection, form or the wider competition picture."),
]

UNCERTAINTY_RULES = [
    (("casualt", "injur", "killed", "dead"), "The current feed does not independently verify the final casualty or injury figures."),
    (("damage", "destroy", "destroyed", "fire", "explosion", "bridge", "building"), "The full extent of physical damage and its operational consequences are not independently verified by Kaivor yet."),
    (("claim", "claims", "alleged", "alleges", "according to"), "The report contains claims or attributed information; independent confirmation may still be required."),
    (("future", "plan", "plans", "could", "may", "might", "expected"), "The future outcome remains uncertain and may change as events develop."),
]


def _normalise_token(word: str) -> str:
    aliases = {
        "bridges": "bridge", "strikes": "strike", "drones": "drone",
        "attacks": "attack", "missiles": "missile", "troops": "troop",
        "markets": "market", "governments": "government",
    }
    return aliases.get(word, word)


def _tokens(text: str) -> list[str]:
    words = re.findall(r"[a-z0-9]{3,}", (text or "").lower())
    return [_normalise_token(word) for word in words if word not in STOPWORDS]


def _token_set(article: dict[str, Any]) -> set[str]:
    return set(_tokens(f"{article.get('title', '')} {article.get('description', '')}"))


def _title_tokens(article: dict[str, Any]) -> set[str]:
    return set(_tokens(str(article.get("title", ""))))


def _jaccard(left: set[str], right: set[str]) -> float:
    union = left | right
    return len(left & right) / len(union) if union else 0.0


def _same_story(left: dict[str, Any], right: dict[str, Any]) -> bool:
    if left.get("category") != right.get("category"):
        return False
    lt = _title_tokens(left)
    rt = _title_tokens(right)
    if len(lt) < 2 or len(rt) < 2:
        return False
    shared = len(lt & rt)
    title_overlap = _jaccard(lt, rt)
    title_ratio = SequenceMatcher(None, str(left.get("title", "")).lower(), str(right.get("title", "")).lower()).ratio()
    content_overlap = _jaccard(_token_set(left), _token_set(right))

    # FP012 adds a named-event anchor requirement for looser matches. This
    # prevents unrelated stories in the same category being merged merely
    # because they share generic words such as "government" or "attack".
    anchors = {t for t in lt & rt if len(t) >= 5}
    if title_ratio >= 0.78 and shared >= 2:
        return True
    if title_overlap >= 0.50 and shared >= 2:
        return True
    if len(anchors) >= 3 and title_overlap >= 0.30 and content_overlap >= 0.25:
        return True
    return False


def _cluster_id(members: list[dict[str, Any]]) -> str:
    seed = "|".join(sorted(str(item.get("id", "")) for item in members))
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()[:16]


def _impact_hint(article: dict[str, Any]) -> str:
    text = f"{article.get('title', '')} {article.get('description', '')}".lower()
    category = str(article.get("category") or "news").lower()
    for _, keywords, message in IMPACT_RULES:
        if any(keyword in text for keyword in keywords):
            return message
    if category == "business":
        return "This may have implications for companies, consumers or markets; the scale depends on the follow-up evidence and response."
    return "The immediate significance depends on what is confirmed next and whether the development produces wider consequences."


def _uncertainty_hint(article: dict[str, Any], source_count: int) -> str:
    text = f"{article.get('title', '')} {article.get('description', '')}".lower()
    for keywords, message in UNCERTAINTY_RULES:
        if any(keyword in text for keyword in keywords):
            return message
    if source_count <= 1:
        return "This is currently a single-source report. Independent coverage or primary evidence could change the picture."
    return "The available reports do not establish every detail. Further primary evidence or independent reporting could change the picture."


def _status(source_count: int, report_count: int) -> str:
    if source_count >= 3:
        return "Corroborated — 3+ independent sources"
    if source_count == 2:
        return "Corroborated — 2 independent sources"
    if report_count >= 2:
        return "Single-source — multiple reports"
    return "Single-source"


def _confidence(source_count: int, report_count: int) -> str:
    if source_count >= 3:
        return "Higher confidence"
    if source_count == 2:
        return "Corroborated"
    if report_count >= 2:
        return "Related coverage"
    return "Uncorroborated"


def _what_we_know(article: dict[str, Any], evidence: dict[str, Any]) -> str:
    source = str(article.get("source") or "Unknown source")
    title = str(article.get("title") or "This report")
    return f"{title} is reported by {source}. {evidence_sentence(evidence)} This describes the current evidence available to Kaivor, not independent proof that every detail is correct."


def _relevance_metadata(representative: dict[str, Any], members: list[dict[str, Any]]) -> dict[str, Any]:
    # Personal relevance is assessed against the configured profile and the
    # representative story text. The story cluster itself does not become
    # more personally relevant merely because it has more reports.
    profile = load_profile()
    assessment = calculate_personal_relevance(representative, profile)
    return {
        "relevance_score": assessment["score"],
        "relevance_label": assessment["label"],
        "relevance_reasons": assessment["reasons"],
        "relevance_keywords": assessment["matched_keywords"],
        "relevance_regions": assessment["matched_regions"],
    }


def _cluster_summary(members: list[dict[str, Any]]) -> dict[str, Any]:
    evidence = build_evidence_model(members)
    timeline = build_story_timeline(members)
    representative = members[0]
    source_count = evidence["source_count"]
    report_count = evidence["report_count"]
    importance_model = build_importance_model(members, story_status=timeline["story_status"])
    return {
        **evidence,
        "developing": report_count >= 2,
        "story_status": timeline["story_status"],
        "timeline": timeline["timeline"],
        "change_summary": timeline["change_summary"],
        "first_published": timeline["first_published"],
        "latest_published": timeline["latest_published"],
        "latest_source": timeline["latest_source"],
        "based_on_current_reports": timeline["based_on_current_reports"],
        "what_we_know_hint": _what_we_know(representative, evidence),
        "evidence_detail": evidence_sentence(evidence),
        "impact_hint": _impact_hint(representative),
        "uncertainty_hint": _uncertainty_hint(representative, source_count),
        "importance_score": importance_model["importance"]["score"],
        "importance_label": importance_model["importance"]["label"],
        "importance_reasons": importance_model["importance"]["reasons"],
        "confidence_score": importance_model["confidence_assessment"]["score"],
        "confidence_label": importance_model["confidence_assessment"]["label"],
        "confidence_reasons": importance_model["confidence_assessment"]["reasons"],
        **_relevance_metadata(representative, members),
    }


def enrich_articles(articles: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Attach evidence-first story intelligence metadata to articles."""
    enriched = [dict(item) for item in articles]
    clusters: list[list[int]] = []
    for index, article in enumerate(enriched):
        for cluster in clusters:
            if any(_same_story(article, enriched[member_index]) for member_index in cluster):
                cluster.append(index)
                break
        else:
            clusters.append([index])

    for cluster in clusters:
        members = [enriched[index] for index in cluster]
        metadata = _cluster_summary(members)
        cluster_id = _cluster_id(members)
        related_ids = [str(item.get("id")) for item in members if item.get("id")]
        for index in cluster:
            enriched[index].update(metadata)
            enriched[index]["cluster_id"] = cluster_id
            enriched[index]["related_article_ids"] = related_ids
            enriched[index]["why_matters_hint"] = metadata["impact_hint"]
    return enriched
