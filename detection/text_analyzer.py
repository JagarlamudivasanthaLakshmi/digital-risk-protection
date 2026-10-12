from difflib import SequenceMatcher

SUSPICIOUS_TERMS = ("urgent", "verify your account", "password", "claim reward", "suspended")


def analyze_text(text, official_description=""):
    normalized = text.casefold()
    signals = [
        {"signal": "suspicious_language", "term": term, "weight": 15}
        for term in SUSPICIOUS_TERMS
        if term in normalized
    ]
    candidate_text = " ".join(normalized.split())
    brand_text = " ".join(official_description.casefold().split())
    if len(candidate_text) >= 80 and len(brand_text) >= 80:
        similarity = SequenceMatcher(
            None, candidate_text[:2000], brand_text[:2000], autojunk=False
        ).ratio()
        if similarity >= 0.82:
            signals.append({
                "signal": "brand_description_similarity",
                "similarity": round(similarity, 2),
                "weight": 20,
            })
    return signals
