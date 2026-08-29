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
from src.text_utils import normalize_for_comparison

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
    """Legacy helper function using NFC normalization and punctuation stripping."""
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

    os.makedirs("results", exist_ok=True)
    out_path = os.path.join("results", "eval_results.json")
    tmp_path = os.path.join("results", "eval_results.json.tmp")

    per_inscription_results = []
    completed_ids = set()

    # Check for existing checkpoint
    if os.path.exists(out_path):
        try:
            with open(out_path, "r", encoding="utf-8") as f:
                existing_data = json.load(f)
                if isinstance(existing_data, dict) and "per_inscription_results" in existing_data:
                    per_inscription_results = existing_data["per_inscription_results"]
                    for rec in per_inscription_results:
                        if isinstance(rec, dict) and "id" in rec:
                            completed_ids.add(rec["id"])
        except Exception as e:
            print(f"Warning: Could not load existing checkpoint from {out_path}: {e}")
            per_inscription_results = []
            completed_ids = set()

    print(f"Loaded {len(inscriptions)} inscriptions ({len(completed_ids)} already completed). Running evaluation...")

    newly_processed_count = 0

    for i, ins in enumerate(inscriptions):
        ins_id = ins.get("id", f"ins_{i+1}")

        # Check if already completed
        if ins_id in completed_ids:
            print(f"[{ins_id}] Already completed, skipping.")
            continue

        raw_text = ins.get("text", "")
        
        # Strip parenthetical editorial notes before mask selection
        cleaned_text = clean_parentheses(raw_text)
        
        # Split remaining text into words and select target
        tokens = extract_candidates(cleaned_text)
        masked_word, target_idx = select_mask_word(tokens)
        
        if not masked_word or target_idx < 0:
            print(f"[{ins_id}] Could not select a valid mask word. Skipping.")
            continue
            
        masked_text = mask_text_at_word(tokens, target_idx)
        
        # Raw vs Vowel-Normalized Targets
        raw_target_norm = norm_word(masked_word)
        norm_target = normalize_for_comparison(masked_word)

        # Build reference examples (leave-one-out)
        reference_examples = [ex for j, ex in enumerate(inscriptions) if j != i]

        # Run predictions
        # 1) Baseline
        baseline_pred = frequency_baseline(masked_text, reference_examples)
        
        # 2) Zero-shot
        zeroshot_resp = restore_gap(masked_text, [])
        if isinstance(zeroshot_resp, dict) and "error" in zeroshot_resp:
            print(f"[{ins_id}] Incomplete due to error, will retry on next run. Zero-shot error: {zeroshot_resp['error']}")
            continue
        zeroshot_cands = extract_predictions_from_response(zeroshot_resp)

        # 3) Few-shot
        fewshot_resp = restore_gap(masked_text, reference_examples)
        if isinstance(fewshot_resp, dict) and "error" in fewshot_resp:
            print(f"[{ins_id}] Incomplete due to error, will retry on next run. Few-shot error: {fewshot_resp['error']}")
            continue
        fewshot_cands = extract_predictions_from_response(fewshot_resp)

        # Scoring Logic
        # Baseline
        base_raw_norm = norm_word(baseline_pred)
        base_norm = normalize_for_comparison(baseline_pred)
        baseline_raw_exact = (base_raw_norm == raw_target_norm) and bool(raw_target_norm)
        baseline_norm_exact = (base_norm == norm_target) and bool(norm_target)

        # Zero-shot
        zs_cands_raw_norm = [norm_word(c) for c in zeroshot_cands]
        zs_cands_norm = [normalize_for_comparison(c) for c in zeroshot_cands]
        zs_raw_exact = (len(zs_cands_raw_norm) > 0 and zs_cands_raw_norm[0] == raw_target_norm) and bool(raw_target_norm)
        zs_norm_exact = (len(zs_cands_norm) > 0 and zs_cands_norm[0] == norm_target) and bool(norm_target)
        zs_raw_top3 = (raw_target_norm in zs_cands_raw_norm[:3]) and bool(raw_target_norm)
        zs_norm_top3 = (norm_target in zs_cands_norm[:3]) and bool(norm_target)

        # Few-shot
        fs_cands_raw_norm = [norm_word(c) for c in fewshot_cands]
        fs_cands_norm = [normalize_for_comparison(c) for c in fewshot_cands]
        fs_raw_exact = (len(fs_cands_raw_norm) > 0 and fs_cands_raw_norm[0] == raw_target_norm) and bool(raw_target_norm)
        fs_norm_exact = (len(fs_cands_norm) > 0 and fs_cands_norm[0] == norm_target) and bool(norm_target)
        fs_raw_top3 = (raw_target_norm in fs_cands_raw_norm[:3]) and bool(raw_target_norm)
        fs_norm_top3 = (norm_target in fs_cands_norm[:3]) and bool(norm_target)

        newly_processed_count += 1

        # Debug print for first 3 newly-processed inscriptions
        if newly_processed_count <= 3:
            print(f"--- DEBUG REPR [{ins_id}] ---")
            print(f"  True Answer : raw={repr(masked_word)} | norm={repr(norm_target)}")
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
                "exact_match_raw": baseline_raw_exact,
                "exact_match_normalized": baseline_norm_exact
            },
            "zero_shot": {
                "candidates": zeroshot_cands[:3],
                "exact_match_raw": zs_raw_exact,
                "exact_match_normalized": zs_norm_exact,
                "top3_match_raw": zs_raw_top3,
                "top3_match_normalized": zs_norm_top3
            },
            "few_shot": {
                "candidates": fewshot_cands[:3],
                "exact_match_raw": fs_raw_exact,
                "exact_match_normalized": fs_norm_exact,
                "top3_match_raw": fs_raw_top3,
                "top3_match_normalized": fs_norm_top3
            }
        }

        # Save incremental record and update file atomically
        per_inscription_results.append(ins_record)
        completed_ids.add(ins_id)

        current_results = {
            "aggregate": {
                "total_evaluated": len(per_inscription_results),
                "status": "in_progress"
            },
            "per_inscription_results": per_inscription_results
        }
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(current_results, f, indent=2, ensure_ascii=False)
        os.replace(tmp_path, out_path)

        print(f"Completed {ins_id}: Masked='{masked_word}' | Base_Hit(Raw/Norm)={baseline_raw_exact}/{baseline_norm_exact} | ZS_Top1(Raw/Norm)={zs_raw_exact}/{zs_norm_exact} | FS_Top1(Raw/Norm)={fs_raw_exact}/{fs_norm_exact}")

    # Recompute final aggregate summary after main loop
    total_eval = len(per_inscription_results)

    base_raw_cnt = sum(1 for r in per_inscription_results if r.get("baseline", {}).get("exact_match_raw") or r.get("baseline", {}).get("exact_match"))
    base_norm_cnt = sum(1 for r in per_inscription_results if r.get("baseline", {}).get("exact_match_normalized"))

    zs_raw_exact_cnt = sum(1 for r in per_inscription_results if r.get("zero_shot", {}).get("exact_match_raw") or r.get("zero_shot", {}).get("exact_match"))
    zs_norm_exact_cnt = sum(1 for r in per_inscription_results if r.get("zero_shot", {}).get("exact_match_normalized"))
    zs_raw_top3_cnt = sum(1 for r in per_inscription_results if r.get("zero_shot", {}).get("top3_match_raw") or r.get("zero_shot", {}).get("top3_match"))
    zs_norm_top3_cnt = sum(1 for r in per_inscription_results if r.get("zero_shot", {}).get("top3_match_normalized"))

    fs_raw_exact_cnt = sum(1 for r in per_inscription_results if r.get("few_shot", {}).get("exact_match_raw") or r.get("few_shot", {}).get("exact_match"))
    fs_norm_exact_cnt = sum(1 for r in per_inscription_results if r.get("few_shot", {}).get("exact_match_normalized"))
    fs_raw_top3_cnt = sum(1 for r in per_inscription_results if r.get("few_shot", {}).get("top3_match_raw") or r.get("few_shot", {}).get("top3_match"))
    fs_norm_top3_cnt = sum(1 for r in per_inscription_results if r.get("few_shot", {}).get("top3_match_normalized"))

    aggregate_summary = {
        "total_evaluated": total_eval,
        "baseline": f"Baseline (Raw): {base_raw_cnt}/{total_eval} exact | Baseline (Normalized): {base_norm_cnt}/{total_eval} exact",
        "zero_shot": f"Zero-shot (Raw): {zs_raw_exact_cnt}/{total_eval} exact, {zs_raw_top3_cnt}/{total_eval} top-3 | Zero-shot (Normalized): {zs_norm_exact_cnt}/{total_eval} exact, {zs_norm_top3_cnt}/{total_eval} top-3",
        "few_shot": f"Few-shot (Raw): {fs_raw_exact_cnt}/{total_eval} exact, {fs_raw_top3_cnt}/{total_eval} top-3 | Few-shot (Normalized): {fs_norm_exact_cnt}/{total_eval} exact, {fs_norm_top3_cnt}/{total_eval} top-3"
    }

    final_results = {
        "aggregate": aggregate_summary,
        "per_inscription_results": per_inscription_results
    }

    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(final_results, f, indent=2, ensure_ascii=False)
    os.replace(tmp_path, out_path)

    pending_count = len(inscriptions) - total_eval
    print("\n=== EVALUATION COMPLETE ===")
    print(aggregate_summary["baseline"])
    print(aggregate_summary["zero_shot"])
    print(aggregate_summary["few_shot"])
    if pending_count > 0:
        print(f"{total_eval}/{len(inscriptions)} inscriptions evaluated ({pending_count} pending due to earlier errors).")
    else:
        print(f"{total_eval}/{len(inscriptions)} inscriptions evaluated.")
    print(f"Results saved to {out_path}")

if __name__ == "__main__":
    evaluate()
