import json
import os
import re
import time
from typing import Any, Dict, List, Optional
from dotenv import load_dotenv
from google import genai

from src.prompts import build_restoration_prompt

load_dotenv()


def restore_gap(
    masked_text: str,
    examples: List[Dict[str, Any]],
    api_key: Optional[str] = None
) -> Dict[str, Any]:
    """
    Restores missing text in masked_text using Gemini API.

    Args:
        masked_text: Inscription text with '[...]' marking a missing word.
        examples: Reference example inscriptions with text, dynasty, date.
        api_key: Optional API key override; defaults to GEMINI_API_KEY env var.

    Returns:
        Parsed dict response from model or dict with an 'error' key on failure.
    """
    key = api_key or os.getenv("GEMINI_API_KEY")
    if not key:
        return {"error": "GEMINI_API_KEY not found in environment or passed parameters."}

    prompt = build_restoration_prompt(masked_text, examples)

    try:
        client = genai.Client(api_key=key)
        
        # Simple retry for 429 rate limit
        for attempt in range(5):
            try:
                response = client.models.generate_content(
                    model="gemini-3.6-flash",
                    contents=prompt,
                )
                break
            except Exception as e:
                err_str = str(e)
                if "429" in err_str and attempt < 4:
                    # Parse retry delay if available or default to 30s
                    match = re.search(r"retryDelay':\s*'(\d+)s'", err_str)
                    sleep_time = int(match.group(1)) + 2 if match else 30
                    time.sleep(sleep_time)
                else:
                    raise e

        raw_text = response.text or ""

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
        return {"error": f"Gemini API request failed: {str(exc)}"}


if __name__ == "__main__":
    sample_masked = "Srimat [...] mahamandalesvara..."
    sample_examples = [
        {"text": "Srimat Tribhuvanamalla mahamandalesvara", "dynasty": "Western Chalukya", "date": "1080 AD"}
    ]

    res = restore_gap(sample_masked, sample_examples)
    print("Result:", res)
