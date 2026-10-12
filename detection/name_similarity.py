from difflib import SequenceMatcher
import unicodedata


CONFUSABLES = str.maketrans({
    "0": "o",
    "1": "l",
    "3": "e",
    "5": "s",
    "а": "a",
    "е": "e",
    "о": "o",
    "р": "p",
    "с": "c",
    "х": "x",
    "і": "i",
})


def _normalize(value):
    normalized = unicodedata.normalize("NFKD", value.casefold()).translate(CONFUSABLES)
    return "".join(
        character
        for character in normalized
        if character.isalnum() and not unicodedata.combining(character)
    )


def name_similarity(candidate, brand_name):
    """Return a normalized name similarity score between 0.0 and 1.0."""
    left = _normalize(candidate)
    right = _normalize(brand_name)
    if not left or not right:
        return 0.0
    return SequenceMatcher(None, left, right, autojunk=False).ratio()
