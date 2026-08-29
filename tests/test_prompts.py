import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.prompts import build_restoration_prompt, build_dynasty_prompt

def test_build_dynasty_prompt():
    examples = [
        {"text": "svasti śrî Gangavâḍi 96000", "dynasty": "Western Ganga", "date": "c. 950 CE"},
        {"text": "śrîmad-râjâdhirâja Chôḷa", "dynasty": "Chola", "date": "c. 1020 CE"}
    ]
    target_text = "svasti śrî-Permmânaḍi râjyaṁ geye"
    
    prompt = build_dynasty_prompt(target_text, examples)
    
    # Assertions
    assert "Western Ganga" in prompt
    assert "Chola" in prompt
    assert "svasti śrî-Permmânaḍi râjyaṁ geye" in prompt
    assert '{"dynasty": "...", "date_range": "...", "reasoning": "..."}' in prompt

if __name__ == "__main__":
    test_build_dynasty_prompt()
    print("All prompt tests passed!")
