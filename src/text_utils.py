import unicodedata

def normalize_for_comparison(text: str) -> str:
    """
    Normalizes transliterated text for comparison purposes:
    1. Lowercases the text
    2. Replaces circumflex vowels with macron equivalents:
       î -> ī
       ê -> ē
       â -> ā
       ô -> ō
       û -> ū
    3. Performs Unicode NFC normalization
    4. Strips leading/trailing whitespace and punctuation
    """
    if not text:
        return ""

    # Lowercase
    s = str(text).lower()

    # Circumflex to macron mapping
    vowel_map = {
        "î": "ī",
        "ê": "ē",
        "â": "ā",
        "ô": "ō",
        "û": "ū"
    }
    for circ, macr in vowel_map.items():
        s = s.replace(circ, macr)

    # Unicode NFC normalization
    s = unicodedata.normalize("NFC", s)

    # Strip leading/trailing whitespace & punctuation
    cleaned = s.strip(" .,|:;!?()[]{}*\"'")
    return cleaned
