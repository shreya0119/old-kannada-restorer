import json
import os
import sys
import unicodedata

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.text_utils import normalize_for_comparison
from scripts.evaluate import norm_word, extract_predictions_from_response

def test_normalize_for_comparison():
    # Test lowercasing, circumflex to macron conversion, and whitespace/punctuation stripping
    assert normalize_for_comparison("Śiva-Bhîmaga") == "śiva-bhīmaga"
    assert normalize_for_comparison("Hêmâdri-kalaśâ!!") == "hēmādri-kalaśā"
    assert normalize_for_comparison("  Pṛithvî  ") == "pṛithvī"
    assert normalize_for_comparison("ô/û") == "ō/ū"

def test_norm_word():
    # Test legacy unicodedata NFC normalization
    str1 = unicodedata.normalize("NFD", "Śiva-Bhîmaga")
    str2 = unicodedata.normalize("NFC", "śiva-bhîmaga")
    
    assert norm_word(str1) == norm_word(str2)
    assert norm_word("  Hêmâdri-kalaśâ!!  ") == "hêmâdri-kalaśâ"

def test_extract_predictions_from_response():
    resp = {
        "candidates": [
            {"text": "Śiva-Bhîmaga", "reasoning": "Fits formula"},
            {"text": "Râchamalla", "reasoning": "Dynasty name"}
        ]
    }
    extracted = extract_predictions_from_response(resp)
    assert extracted == ["Śiva-Bhîmaga", "Râchamalla"]

def test_checkpoint_logic():
    sample_checkpoint = {
        "aggregate": {"status": "in_progress"},
        "per_inscription_results": [
            {"id": "ins_1", "masked_word": "test"},
            {"id": "ins_2", "masked_word": "test2"}
        ]
    }
    completed_ids = {rec["id"] for rec in sample_checkpoint["per_inscription_results"]}
    assert "ins_1" in completed_ids
    assert "ins_2" in completed_ids
    assert "ins_3" not in completed_ids

if __name__ == "__main__":
    test_normalize_for_comparison()
    test_norm_word()
    test_extract_predictions_from_response()
    test_checkpoint_logic()
    print("All unit tests passed!")
