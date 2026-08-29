import json
import os
import sys
from pathlib import Path

# Ensure project root is in sys.path
root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir))

from src.restore import restore_gap


def main():
    json_path = root_dir / "data" / "curated_inscriptions.json"
    if not json_path.exists():
        print(f"Error: Could not find {json_path}")
        sys.exit(1)

    with open(json_path, "r", encoding="utf-8") as f:
        inscriptions = json.load(f)

    if not inscriptions:
        print("Error: curated_inscriptions.json is empty")
        sys.exit(1)

    # Pick the first entry as target
    target_entry = inscriptions[0]
    examples = inscriptions[1:]

    target_text = target_entry["text"]
    word_to_mask = "Bâraṇâsiyan"

    if word_to_mask in target_text:
        masked_text = target_text.replace(word_to_mask, "[...]", 1)
    else:
        # Fallback mask on first word after space if specific word not present
        words = target_text.split()
        word_to_mask = words[3] if len(words) > 3 else words[0]
        words[words.index(word_to_mask)] = "[...]"
        masked_text = " ".join(words)

    print("=== TEST RESTORATION ===")
    print(f"Target ID: {target_entry.get('id')}")
    print(f"Original Word Masked: {word_to_mask}")
    print(f"Masked Text:\n{masked_text}\n")
    print(f"Number of reference examples provided: {len(examples)}")
    print("Calling restore_gap...\n")

    result = restore_gap(masked_text, examples)

    print("=== MODEL RESULT ===")
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
