import json
import os
import sys
from dotenv import load_dotenv

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.dynasty import guess_dynasty

load_dotenv()

def run_test_dynasty():
    data_path = os.path.join("data", "curated_inscriptions.json")
    if not os.path.exists(data_path):
        print(f"Error: {data_path} not found.")
        return

    with open(data_path, "r", encoding="utf-8") as f:
        inscriptions = json.load(f)

    if not inscriptions:
        print("Error: No inscriptions found in curated_inscriptions.json")
        return

    # Select 4 inscriptions (e.g. index 0, 2, 3, 7)
    sample_indices = [0, 2, 3, 7]
    selected = [inscriptions[idx] for idx in sample_indices if idx < len(inscriptions)]

    api_key = os.getenv("GROQ_API_KEY")
    if not api_key or api_key == "your_groq_key_here":
        print("Warning: GROQ_API_KEY is not set or contains default placeholder in .env")

    print(f"Running dynasty & date estimation for {len(selected)} sample inscriptions using Groq (openai/gpt-oss-120b)...\n")

    for ins in selected:
        ins_id = ins.get("id", "Unknown ID")
        true_dynasty = ins.get("dynasty", "Unknown")
        true_date = ins.get("date", "Unknown")
        target_text = ins.get("text", "")

        # Build leave-one-out examples
        examples = [
            {
                "text": other.get("text", ""),
                "dynasty": other.get("dynasty", "Unknown"),
                "date": other.get("date", "Unknown")
            }
            for other in inscriptions
            if other.get("id") != ins_id
        ]

        result = guess_dynasty(target_text, examples, api_key=api_key)

        print("=" * 70)
        print(f"INSCRIPTION ID : {ins_id}")
        print(f"TRUE DYNASTY   : {true_dynasty}")
        print(f"TRUE DATE      : {true_date}")
        print("-" * 70)
        if "error" in result:
            print(f"ERROR          : {result['error']}")
        else:
            print(f"GUESSED DYNASTY: {result.get('dynasty')}")
            print(f"GUESSED DATE   : {result.get('date_range')}")
            print(f"REASONING      : {result.get('reasoning')}")
        print("=" * 70 + "\n")

if __name__ == "__main__":
    run_test_dynasty()
