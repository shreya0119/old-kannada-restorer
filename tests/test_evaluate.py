import json
import os
import sys
import unicodedata

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.evaluate import norm_word, extract_predictions_from_response

def test_norm_word():
    # Test unicodedata NFC normalization and case / punctuation stripping
    str1 = unicodedata.normalize("NFD", "Śiva-Bhîmaga")
    str2 = unicodedata.normalize("NFC", "śiva-bhîmaga")
    
    assert norm_word(str1) == norm_word(str2)
    assert norm_word("  Hêmâdri-kalaśâ!!  ") == "hêmâdri-kalaśâ"

def test_extract_predictions_from_response():
    # Test model prompt response structure parsing
    resp = {
        "candidates": [
            {"text": "Śiva-Bhîmaga", "reasoning": "Fits formula"},
            {"text": "Râchamalla", "reasoning": "Dynasty name"}
        ]
    }
    extracted = extract_predictions_from_response(resp)
    assert extracted == ["Śiva-Bhîmaga", "Râchamalla"]

if __name__ == "__main__":
    test_norm_word()
    test_extract_predictions_from_response()
    print("All unit tests passed!")
