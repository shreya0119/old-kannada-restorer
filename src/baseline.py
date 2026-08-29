"""
Baseline frequency model for Old Kannada text restoration.
"""

import re
from collections import Counter
from typing import List, Dict, Any


def frequency_baseline(masked_text: str, corpus_examples: List[Dict[str, Any]]) -> str:
    """
    Returns the most frequent word in corpus_examples that fits simple context heuristics or overall frequency.
    """
    all_words = []
    for ex in corpus_examples:
        text = ex.get("text", "")
        # Remove parenthetical notes
        text = re.sub(r"\(.*?\)", "", text)
        words = re.findall(r"\b[\w\dĀ-ža-zA-Z\-'âîûêôâîûêôśṣṇṭḍḷṁḥŚṢṆṬḌḶṀḤ]+\b", text)
        for w in words:
            w_clean = w.strip(" .,|:;!?()[]{}*\"'").lower()
            if len(w_clean) > 2:
                all_words.append(w_clean)

    if not all_words:
        return ""

    counts = Counter(all_words)
    # Filter out common exclusion boilerplate words if present
    exclusions = {"śrî", "svasti", "namaḥ", "śubham", "râja", "saha"}
    filtered_counts = [w for w in counts.most_common(10) if w[0] not in exclusions]
    return filtered_counts[0][0] if filtered_counts else counts.most_common(1)[0][0]
