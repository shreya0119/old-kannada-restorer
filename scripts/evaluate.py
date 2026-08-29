import json
import os
import re
import sys
import time
import unicodedata
from typing import List, Dict, Any, Tuple, Optional

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.baseline import frequency_baseline
from src.restore import restore_gap

# Exclusion list for boilerplate/formulaic/very short/dynasty/royal-title words
EXCLUSION_WORDS = {
    "śubham", "dattam", "dattaṁ", "grâmas", "namaḥ", "namas", "astu", "svasti",
    "śrî", "śrîman", "śrîmad", "vijayâbhyudaya", "śâlivâhana", "śaka", "varsha",
    "varshaṅgaḷu", "varusha", "saṁvatsarada", "puṇya", "kâladallu", "kâladalu",
    "râjâdhirâja", "râja", "paramêśvara", "mahârâjâdhirâja", "mahârâya", "mahârâyaru",
    "pṛithvî", "pṛithivî", "râjyaṁ", "sâmbrâjyaṁ", "sâmrâjyaṁ", "geyyut", "geyiütta",
    "geye", "gaivuttâ", "iralu", "viralu", "mâḍi", "koṭṭu", "koṭṭev", "koṭṭan",
    "saha", "dharma", "śâsana", "tâmra", "tâmbra", "śîlâ", "harêr", "lîlâ",
    "tuṅga", "sva", "para", "dattâm", "vishṭhâyâm", "krimir", "krimiḥ", "bhûtvâ",
    "yô", "harêta", "vasundharâm", "001", "002", "003", "004", "005", "1", "2", "3", "4"
}

# Known dynasty & title words
DYNASTY_TITLE_WORDS = {
    "ganga", "gaṅga", "chalukya", "rashtrakuta", "râshṭrakûṭa", "vijayanagara",
    "kalinga", "kaliṅga", "avati", "belur", "bêlûru", "mysore", "permmânaḍi",
    "râchamalla", "achyuta", "raṅga", "kempê", "kempa", "vîra", "dêva", "bairê",
    "gôpâla", "vîrapâṇa", "sâlva", "kaṭhâri"
}

def clean_parentheses(text: str) -> str:
    """Strip out any parenthetical editorial notes from the text."""
    cleaned = re.sub(r"\(.*?\)", "", text, flags=re.DOTALL)
    return re.sub(r"\s+", " ", cleaned).strip()

def extract_candidates(text: str) -> List[str]:
    """Split text into candidate words for masking."""
    tokens = re.findall(r"\b[\w\dĀ-ža-zA-Z\-'âîûêôśṣṇṭḍḷṁḥŚṢṆṬḌḶṀḤ]+\b", text)
    return tokens

def norm_word(word: str) -> str:
    """Normalize word for case-insensitive exact matching with Unicode NFC normalization."""
    if not word:
        return ""
    normalized = unicodedata.normalize("NFC", str(word))
    cleaned = normalized.strip(" .,|:;!?()[]{}*\"'").lower()
    return cleaned

def select_mask_word(tokens: List[str]) -> Tuple[Optional[str], int]:
    """Select a suitable word to mask based on exclusion rules and heuristics."""
    candidates = []
    for idx, token in enumerate(tokens):
        raw = token.strip()
        norm = norm_word(raw)
        
        # Skip short words (< 4 chars)
        if len(norm) < 4:
            continue
            
        # Skip exclusion / boilerplate words
        if norm in EXCLUSION_WORDS:
            continue
            
        # Skip dynasty/royal-title words
        if norm in DYNASTY_TITLE_WORDS:
            continue
            
        # Skip numbers/digits
        if norm.isdigit():
            continue
            
        # Prefer capitalized words (proper nouns) or specific nouns
        score = 0
        if raw[0].isupper():
            score += 2
        if len(norm) >= 6:
            score += 1
            
        candidates.append((score, idx, raw))
        
    if not candidates:
        for idx, token in enumerate(tokens):
            raw = token.strip()
            norm = norm_word(raw)
            if len(norm) >= 3 and norm not in EXCLUSION_WORDS:
                candidates.append((0, idx, raw))

    if not candidates:
        return None, -1

    candidates.sort(key=lambda x: x[0], reverse=True)
    best_score, best_idx, best_word = candidates[0]
    return best_word, best_idx

def mask_text_at_word(tokens: List[str], target_idx: int) -> str:
    """Replace target word at index with [...] and reconstruct string."""
    tokens_copy = list(tokens)
    tokens_copy[target_idx] = "[...]"
    return " ".join(tokens_copy)

def extract_predictions_from_response(resp: Dict[str, Any]) -> List[str]:
    """Extract candidate list from model output dict."""
    if not isinstance(resp, dict) or "error" in resp:
        return []
        
    candidates = []
    if "candidates" in resp and isinstance(resp["candidates"], list):
        for item in resp["candidates"]:
            if isinstance(item, dict):
                val = item.get("text") or item.get("word") or item.get("candidate")
                if val:
                    candidates.append(str(val))
            elif isinstance(item, str):
                candidates.append(item)
    elif "restoration_candidates" in resp and isinstance(resp["restoration_candidates"], list):
        for item in resp["restoration_candidates"]:
            if isinstance(item, dict):
                val = item.get("word") or item.get("text") or item.get("candidate")
                if val:
                    candidates.append(str(val))
            elif isinstance(item, str):
                candidates.append(item)
                
    return candidates

def evaluate():
    data_path = os.path.join("data", "curated_inscriptions.json")
    if not os.path.exists(data_path):
        print(f"Error: {data_path} not found.")
        return

    with open(data_path, "r", encoding="utf-8") as f:
        inscriptions = json.load(f)

    per_inscription_results = []
    
    baseline_exact_cnt = 0
    zeroshot_exact_cnt = 0
    zeroshot_top3_cnt = 0
    fewshot_exact_cnt = 0
    fewshot_top3_cnt = 0
    total_eval = 0

    print(f"Loaded {len(inscriptions)} inscriptions. Running evaluation...")

    for i, ins in enumerate(inscriptions):
        ins_id = ins.get("id", f"ins_{i+1}")
        raw_text = ins.get("text", "")
        
        # Step 1: Strip parenthetical editorial notes before mask selection
        cleaned_text = clean_parentheses(raw_text)
        
        # Step 2: Split remaining text into words and select target
        tokens = extract_candidates(cleaned_text)
        masked_word, target_idx = select_mask_word(tokens)
        
        if not masked_word or target_idx < 0:
            print(f"[{ins_id}] Could not select a valid mask word. Skipping.")
            continue
            
        masked_text = mask_text_at_word(tokens, target_idx)
        target_norm = norm_word(masked_word)

        # Step 3: Build reference examples (leave-one-out)
        reference_examples = [ex for j, ex in enumerate(inscriptions) if j != i]

        # Step 4: Run predictions
        # 1) Baseline
        baseline_pred = frequency_baseline(masked_text, reference_examples)
        
        # 2) Zero-shot
        zeroshot_resp = restore_gap(masked_text, [])
        if "error" in zeroshot_resp:
            print(f"[{ins_id}] Zero-shot error: {zeroshot_resp['error']}")
        zeroshot_cands = extract_predictions_from_response(zeroshot_resp)

        # 3) Few-shot
        fewshot_resp = restore_gap(masked_text, reference_examples)
        if "error" in fewshot_resp:
            print(f"[{ins_id}] Few-shot error: {fewshot_resp['error']}")
        fewshot_cands = extract_predictions_from_response(fewshot_resp)

        # Step 5: Scoring
        # Baseline score
        base_norm = norm_word(baseline_pred)
        baseline_exact = (base_norm == target_norm) and bool(target_norm)
        if baseline_exact:
            baseline_exact_cnt += 1

        # Zero-shot scoring
        zs_cands_norm = [norm_word(c) for c in zeroshot_cands]
        zeroshot_exact = (len(zs_cands_norm) > 0 and zs_cands_norm[0] == target_norm) and bool(target_norm)
        zeroshot_top3 = (target_norm in zs_cands_norm[:3]) and bool(target_norm)
        if zeroshot_exact:
            zeroshot_exact_cnt += 1
        if zeroshot_top3:
            zeroshot_top3_cnt += 1

        # Few-shot scoring
        fs_cands_norm = [norm_word(c) for c in fewshot_cands]
        fewshot_exact = (len(fs_cands_norm) > 0 and fs_cands_norm[0] == target_norm) and bool(target_norm)
        fewshot_top3 = (target_norm in fs_cands_norm[:3]) and bool(target_norm)
        if fewshot_exact:
            fewshot_exact_cnt += 1
        if fewshot_top3:
            fewshot_top3_cnt += 1

        total_eval += 1

        # Debug print for first 3 inscriptions
        if total_eval <= 3:
            print(f"--- DEBUG REPR [{ins_id}] ---")
            print(f"  True Answer : raw={repr(masked_word)} | norm={repr(target_norm)}")
            print(f"  Baseline    : raw={repr(baseline_pred)} | norm={repr(base_norm)}")
            print(f"  Zero-Shot   : raw={repr(zeroshot_cands[:3])} | norm={repr(zs_cands_norm[:3])}")
            print(f"  Few-Shot    : raw={repr(fewshot_cands[:3])} | norm={repr(fs_cands_norm[:3])}")
            print("-----------------------------")

        ins_record = {
            "id": ins_id,
            "masked_word": masked_word,
            "masked_text": masked_text,
            "baseline": {
                "prediction": baseline_pred,
                "exact_match": baseline_exact
            },
            "zero_shot": {
                "candidates": zeroshot_cands[:3],
                "exact_match": zeroshot_exact,
                "top3_match": zeroshot_top3
            },
            "few_shot": {
                "candidates": fewshot_cands[:3],
                "exact_match": fewshot_exact,
                "top3_match": fewshot_top3
            }
        }
        per_inscription_results.append(ins_record)
        print(f"Completed {ins_id}: Masked='{masked_word}' | Base_Hit={baseline_exact} | ZS_Top1={zeroshot_exact} | FS_Top1={fewshot_exact}")

    aggregate_summary = {
        "total_evaluated": total_eval,
        "baseline": f"Baseline: {baseline_exact_cnt}/{total_eval} exact",
        "zero_shot": f"Zero-shot: {zeroshot_exact_cnt}/{total_eval} exact, {zeroshot_top3_cnt}/{total_eval} top-3",
        "few_shot": f"Few-shot: {fewshot_exact_cnt}/{total_eval} exact, {fewshot_top3_cnt}/{total_eval} top-3"
    }

    results = {
        "aggregate": aggregate_summary,
        "per_inscription_results": per_inscription_results
    }

    os.makedirs("results", exist_ok=True)
    out_path = os.path.join("results", "eval_results.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    # Sync to src/evaluate.py
    src_eval_path = os.path.join("src", "evaluate.py")
    with open(src_eval_path, "w", encoding="utf-8") as f_src:
        with open(__file__, "r", encoding="utf-8") as f_self:
            f_src.write(f_self.read())

    print("\n=== EVALUATION COMPLETE ===")
    print(aggregate_summary["baseline"])
    print(aggregate_summary["zero_shot"])
    print(aggregate_summary["few_shot"])
    print(f"Results saved to {out_path}")

if __name__ == "__main__":
    evaluate()
