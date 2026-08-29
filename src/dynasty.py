import json
import os
import re
from typing import Any, Dict, List, Optional
from dotenv import load_dotenv

from src.prompts import build_dynasty_prompt
from src.llm_client import call_llm

load_dotenv()


def guess_dynasty(
    text: str,
    examples: List[Dict[str, Any]],
    api_key: Optional[str] = None
) -> Dict[str, Any]:
    """
    Estimates the dynasty and date range of an Old Kannada inscription using the LLM client.

    Args:
        text: Inscription text.
        examples: List of reference inscription dicts.
        api_key: Optional API key override; if provided, temporarily sets GROQ_API_KEY.

    Returns:
        Dict with keys "dynasty", "date_range", "reasoning", or "error".
    """
    if api_key:
        os.environ["GROQ_API_KEY"] = api_key

    prompt = build_dynasty_prompt(text, examples)

    try:
        response_text = call_llm(prompt)

        # Strip markdown code fences if present (e.g., ```json ... ```)
        cleaned_text = re.sub(r"^```(?:json)?\s*", "", response_text.strip(), flags=re.IGNORECASE | re.MULTILINE)
        cleaned_text = re.sub(r"\s*```$", "", cleaned_text, flags=re.MULTILINE).strip()

        # Parse JSON
        result = json.loads(cleaned_text)

        # Ensure required keys exist
        return {
            "dynasty": result.get("dynasty", "Unknown"),
            "date_range": result.get("date_range", "Unknown"),
            "reasoning": result.get("reasoning", "")
        }

    except json.JSONDecodeError as e:
        return {"error": f"Failed to parse JSON response: {str(e)}", "raw_response": response_text if 'response_text' in locals() else ""}
    except Exception as e:
        return {"error": f"LLM call failed: {str(e)}"}
