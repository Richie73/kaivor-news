"""FP032: evidence safeguards must be present in WHAT IS REPORTED."""
from brief_quality_validation import validate_brief


def base_article():
    return {
        "source": "Example News",
        "source_count": 1,
        "confidence_label": "Low",
        "evidence_status": "Single-source",
        "title": "Project cost £20 million",
        "description": "Example News says the project is estimated to cost £20 million.",
    }


def valid_brief():
    return (
        "WHAT IS REPORTED\nExample News reports that the project is estimated to cost £20 million. "
        "The figure has not been independently verified.\n\n"
        "WHY IT MATTERS\nAnalysis: the amount may be significant if accurate.\n\n"
        "WHAT TO WATCH NEXT\nLook for official documents and independent confirmation."
    )


def test_accepts_evidence_anchored_in_reported_section():
    result = validate_brief(valid_brief(), base_article())
    assert result["valid"] is True
    assert result["issues"] == []


def test_rejects_source_attribution_only_in_analysis_section():
    brief = valid_brief().replace(
        "Example News reports that the project is estimated to cost £20 million.",
        "The project is estimated to cost £20 million.",
    ).replace("Analysis: the amount", "Example News analysis: the amount")
    result = validate_brief(brief, base_article())
    assert "missing_source_attribution" in result["issues"]


def test_rejects_uncertainty_only_outside_reported_section():
    brief = valid_brief().replace(
        "The figure has not been independently verified.",
        "The figure is stated in the report.",
    ).replace(
        "Analysis: the amount may be significant if accurate.",
        "Analysis: the amount has not been independently verified and may be significant.",
    )
    result = validate_brief(brief, base_article())
    assert "missing_uncertainty" in result["issues"]


def test_rejects_source_figure_only_in_watch_section():
    brief = valid_brief().replace("£20 million", "£25 million")
    brief = brief.replace(
        "Look for official documents and independent confirmation.",
        "Look for official documents confirming the £20 million figure.",
    )
    result = validate_brief(brief, base_article())
    assert "source_figures_not_preserved" in result["issues"]


def test_pasted_text_attribution_must_be_in_reported_section():
    brief = (
        "WHAT IS REPORTED\nThe text describes a research project and its possible impact; its accuracy is unverified.\n\n"
        "WHY IT MATTERS\nAnalysis: this is user-supplied text and is not independently verified.\n\n"
        "WHAT TO WATCH NEXT\nSeek independent confirmation and official documents."
    )
    result = validate_brief(brief, {"source_type": "pasted_text", "source_count": 1})
    assert "missing_pasted_text_attribution" in result["issues"]
