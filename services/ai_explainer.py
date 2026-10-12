from detection.explainability import explain_finding as explain_rule_based_finding


def explain_finding(finding):
    """Provide the best available explanation and indicate whether AI supplied it."""
    if (
        finding.ai_status == "completed"
        and finding.ai_summary
    ):
        return {
            "source": "ai",
            "summary": finding.ai_summary,
            "recommendation": finding.ai_recommendation,
        }

    recommendation = (
        "Verify the account or app through the brand's official channels before taking action."
        if finding.signals
        else "No action is suggested unless new evidence appears."
    )
    return {
        "source": "rules",
        "summary": explain_rule_based_finding(finding),
        "recommendation": recommendation,
    }
