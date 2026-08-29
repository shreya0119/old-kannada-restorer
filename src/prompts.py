import json
from typing import Dict, List, Any


def build_restoration_prompt(masked_text: str, examples: List[Dict[str, Any]]) -> str:
    """
    Builds a prompt string for restoring masked inscription text based on reference examples.

    Args:
        masked_text: Inscription text containing '[...]' marking a masked word.
        examples: List of dicts, each containing 'text', 'dynasty', and 'date'.

    Returns:
        Formatted prompt string instructing the model to return valid JSON with candidates.
    """
    examples_formatted = []
    for i, ex in enumerate(examples, 1):
        text = ex.get("text", "")
        dynasty = ex.get("dynasty", "Unknown")
        date = ex.get("date", "Unknown")
        examples_formatted.append(
            f"Example {i}:\n"
            f"- Text: {text}\n"
            f"- Dynasty: {dynasty}\n"
            f"- Date: {date}"
        )

    examples_block = "\n\n".join(examples_formatted) if examples_formatted else "None provided."

    prompt = f"""You are an expert epigraphist and historical linguist specializing in ancient Kannada inscriptions.

### Reference Inscriptions (Context)
{examples_block}

### Target Inscription (Masked Text)
{masked_text}

### Instructions
The target inscription contains a missing or damaged word indicated by '[...]'.
Analyze the vocabulary, syntax, style, and historical context based on the reference inscriptions to deduce the missing word.

Provide up to 3 candidate replacements ranked from most likely to least likely.

You MUST respond with ONLY valid JSON matching this exact structure:
{{
  "candidates": [
    {{
      "text": "<candidate word or phrase>",
      "reasoning": "<explanation based on linguistic/historical context>"
    }}
  ]
}}

Do not include any extra text, markdown wrappers, or preamble outside the valid JSON object."""

    return prompt


def build_dynasty_prompt(text: str, examples: List[Dict[str, Any]]) -> str:
    """
    Builds a prompt string for estimating the dynasty and date range of an Old Kannada inscription.

    Args:
        text: The full text of an Old Kannada inscription (unmasked).
        examples: List of dicts with 'text', 'dynasty', and 'date' for reference.

    Returns:
        Formatted prompt string instructing the model to respond ONLY with valid JSON.
    """
    examples_formatted = []
    for i, ex in enumerate(examples, 1):
        ex_text = ex.get("text", "")
        dynasty = ex.get("dynasty", "Unknown")
        date = ex.get("date", "Unknown")
        examples_formatted.append(
            f"Example {i}:\n"
            f"- Text: {ex_text}\n"
            f"- Dynasty: {dynasty}\n"
            f"- Date: {date}"
        )

    examples_block = "\n\n".join(examples_formatted) if examples_formatted else "None provided."

    prompt = f"""You are an expert epigraphist specializing in Old Kannada inscriptions and historical dynasties.

### Reference Inscriptions (Context)
{examples_block}

### Target Inscription
{text}

### Instructions
Analyze the target inscription's vocabulary, formulaic structures, honorifics, and linguistic style compared to the reference inscriptions.
Estimate the most likely ruling dynasty and approximate date range for this target inscription.

You MUST respond with ONLY valid JSON, no preamble, and no markdown fences, shaped exactly like:
{{"dynasty": "...", "date_range": "...", "reasoning": "..."}}"""

    return prompt
