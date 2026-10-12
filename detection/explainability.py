def explain_finding(finding):
    if not finding.signals:
        return "No risk indicators were recorded for this finding."
    details = [
        f"{signal['signal'].replace('_', ' ').capitalize()} (+{signal['weight']})"
        for signal in finding.signals
    ]
    return f"Risk score {finding.risk_score}/100: " + "; ".join(details) + "."
