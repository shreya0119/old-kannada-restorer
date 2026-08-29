import json
import os
import re
import time
from typing import Any, Dict, List, Optional
from dotenv import load_dotenv

from src.prompts import build_restoration_prompt
from src.llm_client import call_llm

load_dotenv()


def restore_gap(
    masked_text: str,
    examples: List[Dict[str, Any]],
    api_key: Optional[str] = None
) -> Dict[str, Any]:
    """
    Restores missing text in masked_text using the LLM client.

    Args:
        masked_text: Inscription text with '[...]' marking a missing word.
        examples: Reference example inscriptions with text, dynasty, date.
        api_key: Optional API key override; if provided, temporarily sets GEMINI_API_KEY.

    Returns:
        Parsed dict response from model or dict with an 'error' key on failure.
    """
    if api_key:
        os.environ["GEMINI_API_KEY"] = api_key

    prompt = build_restoration_prompt(masked_text, examples)

    try:
        raw_text = call_llm(prompt)

        # Strip markdown code fences if present
        cleaned_text = re.sub(r"^```(?:json)?\s*", "", raw_text.strip(), flags=re.MULTILINE)
        cleaned_text = re.sub(r"\s*```$", "", cleaned_text, flags=re.MULTILINE).strip()

        try:
            parsed_data = json.loads(cleaned_text)
            return parsed_data
        except json.JSONDecodeError as parse_err:
            return {
                "error": f"Failed to parse model output as JSON: {str(parse_err)}",
                "raw_response": raw_text,
            }

    except Exception as exc:
        return {"error": f"LLM request failed: {str(exc)}"}


if __name__ == "__main__":
    sample_masked = "Srimat [...] mahamandalesvara..."
    sample_examples = [
        {"text": "Srimat Tribhuvanamalla mahamandalesvara", "dynasty": "Western Chalukya", "date": "1080 AD"}
    ]

    res = restore_gap(sample_masked, sample_examples)
    print("Result:", res)
