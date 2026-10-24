from brief_quality_validation import validate_brief


def good_brief():
    return (
        "WHAT IS REPORTED\nExample News reports a project is estimated to cost "
        "£20 million over three years. The estimate has not been independently verified.\n\n"
        "WHY IT MATTERS\nAnalysis: the scale may matter if the estimate is accurate.\n\n"
        "WHAT TO WATCH NEXT\nLook for official documents and independent corroboration."
    )


def test_accepts_brief_with_sections_attribution_uncertainty_and_figures():
    article = {
        "source": "Example News",
        "source_count": 1,
        "confidence_label": "Low",
        "evidence_status": "Single-source",
        "title": "Project cost £20 million",
        "description": "The project would cost £20 million over three years.",
    }
    result = validate_brief(good_brief(), article)
    assert result["valid"] is True
    assert result["issues"] == []


def test_rejects_missing_sections():
    result = validate_brief(
        "A short report without the required format.",
        {"source": "Example News"},
    )
    assert "missing_sections" in result["issues"]


def test_rejects_missing_source_attribution():
    brief = good_brief().replace(
        "Example News reports a project", "Reports say a project"
    )
    result = validate_brief(
        brief, {"source": "Example News", "source_count": 2}
    )
    assert "missing_source_attribution" in result["issues"]


def test_rejects_missing_uncertainty_for_low_confidence():
    brief = good_brief().replace(
        "The estimate has not been independently verified.",
        "The estimate is reported.",
    )
    result = validate_brief(
        brief,
        {
            "source": "Example News",
            "source_count": 1,
            "confidence_label": "Low",
        },
    )
    assert "missing_uncertainty" in result["issues"]


def test_rejects_dropped_source_figure():
    brief = good_brief().replace("£20 million", "£25 million")
    result = validate_brief(
        brief,
        {
            "source": "Example News",
            "source_count": 1,
            "title": "Project cost £20 million",
            "description": "Three years",
        },
    )
    assert "source_figures_not_preserved" in result["issues"]


def test_pasted_text_does_not_require_publisher_name():
    brief = good_brief().replace(
        "Example News reports a project",
        "The user-supplied text says a project",
    )
    result = validate_brief(
        brief, {"source_type": "pasted_text", "source_count": 1}
    )
    assert result["valid"] is True


def test_ignores_incidental_dates_and_counts():
    brief = good_brief()
    article = {
        "source": "Example News",
        "source_count": 2,
        "title": "Project announced on 24 October 2026",
        "description": "Three departments discussed the plan at 10:30.",
    }
    result = validate_brief(brief, article)
    assert "source_figures_not_preserved" not in result["issues"]


def test_fallback_brief_section_headings_are_recognised():
    brief = (
        "1) WHAT IS REPORTED: Example News reports a proposal. "
        "The claim has not been independently corroborated.\n\n"
        "2) WHY IT MATTERS: Analysis is limited by available evidence.\n\n"
        "3) WHAT TO WATCH NEXT: Look for official documents and confirmation."
    )
    result = validate_brief(
        brief,
        {
            "source": "Example News",
            "source_count": 1,
            "confidence_label": "Low",
        },
    )
    assert result["valid"] is True
