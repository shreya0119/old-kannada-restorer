import os
from typing import List, Tuple
from dotenv import load_dotenv

load_dotenv()


def call_llm(prompt: str) -> str:
    """
    Calls an LLM using a fallback cascade of configured API keys and providers.
    
    Tries GEMINI_API_KEY(1-4) first, then GROQ_API_KEY(1-4).
    Returns the raw plain text response from the first successful call.
    Raises RuntimeError if all available keys fail.
    """
    candidates: List[Tuple[str, str, str]] = []
    
    # 1. Gather Gemini keys
    for key_name in ["GEMINI_API_KEY", "GEMINI_API_KEY2", "GEMINI_API_KEY3", "GEMINI_API_KEY4"]:
        val = os.getenv(key_name)
        if val:
            candidates.append(("gemini", key_name, val))
            
    # 2. Gather Groq keys
    for key_name in ["GROQ_API_KEY", "GROQ_API_KEY2", "GROQ_API_KEY3", "GROQ_API_KEY4"]:
        val = os.getenv(key_name)
        if val:
            candidates.append(("groq", key_name, val))

    if not candidates:
        raise RuntimeError("No API keys found in environment variables (checked GEMINI_API_KEY* and GROQ_API_KEY*).")

    errors = []

    for provider, key_name, api_key in candidates:
        try:
            if provider == "gemini":
                from google import genai
                client = genai.Client(api_key=api_key)
                response = client.models.generate_content(
                    model="gemini-3.6-flash",
                    contents=prompt,
                )
                print(f"Success: {provider}, key {key_name}")
                return response.text or ""

            elif provider == "groq":
                from groq import Groq
                client = Groq(api_key=api_key)
                response = client.chat.completions.create(
                    model="openai/gpt-oss-120b",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.2,
                )
                print(f"Success: {provider}, key {key_name}")
                return response.choices[0].message.content or ""

        except Exception as e:
            err_msg = f"{provider.capitalize()} call failed with {key_name}: {str(e)}"
            print(f"Warning: {err_msg}")
            errors.append(err_msg)

    # If we get here, all attempts failed
    raise RuntimeError(
        "All configured LLM providers/keys failed to generate a response.\n" + 
        "\n".join(errors)
    )
