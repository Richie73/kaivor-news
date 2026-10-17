from confidence_aware_ai import build_ai_brief_fallback, build_ai_brief_messages, confidence_context


def test_single_source_brief_prompt_requires_attribution_and_uncertainty():
    article = {
        "title": "President waives several sanctions",
        "description": "A report says several restrictions were temporarily ended.",
        "source": "BBC News",
        "source_count": 1,
        "report_count": 1,
        "confidence_label": "Low",
        "evidence_status": "Single-source",
    }
    messages = build_ai_brief_messages(article)
    system = messages[0]["content"].lower()
    user = messages[1]["content"]
    assert "attribute the event" in system
    assert "not been independently corroborated" in system
    assert "bbc news" in user.lower()
    assert "single-source" in user.lower()


def test_multiple_reports_from_one_source_remain_low_confidence():
    article = {
        "title": "A developing report",
        "source": "BBC News",
        "source_count": 1,
        "report_count": 4,
        "confidence_label": "Low",
        "evidence_status": "Single-source — multiple reports",
    }
    evidence = confidence_context(article)
    assert evidence["low_confidence"] is True
    assert evidence["source_count"] == 1
    assert evidence["report_count"] == 4


def test_independent_source_metadata_does_not_claim_every_detail_is_verified():
    article = {
        "title": "Two publishers report a development",
        "source": "BBC News",
        "story_sources": ["BBC News", "Reuters"],
        "source_count": 2,
        "report_count": 3,
        "confidence_label": "Medium",
        "evidence_status": "Corroborated — 2 independent sources",
    }
    system = build_ai_brief_messages(article)[0]["content"].lower()
    assert "does not prove every detail" in system
    assert "bbc news, reuters" in build_ai_brief_messages(article)[1]["content"].lower()


def test_fallback_attributes_low_confidence_claim_and_recommends_verification():
    fallback = build_ai_brief_fallback({
        "title": "President waives several sanctions",
        "source": "BBC News",
        "source_count": 1,
        "report_count": 1,
        "confidence_label": "Low",
        "evidence_status": "Single-source",
    }).lower()
    assert "bbc news reports" in fallback
    assert "not been independently corroborated" in fallback
    assert "independent reporting" in fallback
