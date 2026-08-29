import json
import random
import re
from pathlib import Path
import streamlit as st

from src.restore import restore_gap
from src.dynasty import guess_dynasty

# Ensure page config is set
st.set_page_config(page_title="Old Kannada Restorer", layout="wide")

@st.cache_data
def load_data():
    json_path = Path("data/curated_inscriptions.json")
    if not json_path.exists():
        st.error(f"Data file not found at {json_path}")
        return []
    with open(json_path, "r", encoding="utf-8") as f:
        return json.load(f)

def is_maskable(word):
    """
    Check if a word is maskable.
    Skips words with parentheses, brackets, asterisks, or numbers.
    """
    if any(c in word for c in "()[]*0123456789"):
        return False
    # Only keep words with characters (allowing extended Latin/diacritics)
    if not re.search(r'[a-zA-Z\u00C0-\u024F\u1E00-\u1EFF]', word):
        return False
    return True

def generate_masked_text(text):
    words = text.split()
    maskable_indices = [i for i, w in enumerate(words) if is_maskable(w)]
    
    if not maskable_indices:
        return text, ""
    
    target_idx = random.choice(maskable_indices)
    target_word = words[target_idx]
    
    # Replace the exact word at that index
    words[target_idx] = "[...]"
    return " ".join(words), target_word

def contains_non_latin(text):
    # Check for Kannada unicode block or other obvious non-Latin scripts
    # Kannada block is \u0C80-\u0CFF
    if re.search(r'[\u0C80-\u0CFF]', text):
        return True
    return False

def main():
    st.title("Old Kannada Inscription Restorer")
    st.markdown("""
        **Welcome to the Old Kannada Inscription Restorer.**
        
        This prototype uses large language models (Gemini & Groq) with few-shot prompting to deduce missing words in transliterated Old Kannada inscriptions. Rather than relying on a custom-trained model, it dynamically builds context using a curated reference dataset to restore damaged text and estimate the dynasty/date of the artifact.
    """)
    st.write("") # Light spacing
    
    inscriptions = load_data()
    
    if not inscriptions:
        return

    tab1, tab2 = st.tabs(["Mode 1: Verified (Dropdown)", "Mode 2: Free Text"])

    # --- MODE 1: VERIFIED ---
    with tab1:
        st.header("Verified Inscriptions")
        
        # Dropdown selection
        options = {ins["id"]: ins for ins in inscriptions}
        selected_id = st.selectbox("Select an inscription:", list(options.keys()))
        selected_ins = options[selected_id]
        
        # Handle state so the random mask doesn't change on every UI interaction
        state_key_masked = f"masked_{selected_id}"
        state_key_target = f"target_{selected_id}"
        
        if state_key_masked not in st.session_state:
            m_text, t_word = generate_masked_text(selected_ins["text"])
            st.session_state[state_key_masked] = m_text
            st.session_state[state_key_target] = t_word
            
        masked_text = st.session_state[state_key_masked]
        target_word = st.session_state[state_key_target]
        
        st.subheader("Original Text:")
        st.text_area("Original", selected_ins["text"], height=150, disabled=True, key=f"orig_{selected_id}")
        
        st.subheader("Masked Text (Input):")
        st.text_area("Masked", masked_text, height=150, disabled=True, key=f"mask_{selected_id}")
        
        if st.button("Restore", key="btn_mode1"):
            st.caption("Uses automatic multi-key, multi-provider failover (Gemini + Groq) for reliability.")
            
            with st.spinner("Restoring text and estimating dynasty..."):
                other_examples = [ins for ins in inscriptions if ins["id"] != selected_id]
                
                # Call APIs
                restore_res = restore_gap(masked_text, other_examples)
                dynasty_res = guess_dynasty(selected_ins["text"], other_examples)
                
                st.markdown("---")
                st.subheader("Results")
                
                # Check for errors
                if "error" in restore_res:
                    st.error(f"Restoration Error: {restore_res['error']}")
                else:
                    st.markdown("#### Top Restoration Candidates:")
                    candidates = restore_res.get("candidates", [])
                    
                    match_found = False
                    for i, cand in enumerate(candidates, 1):
                        cand_text = cand.get("text", "")
                        st.write(f"**{i}. {cand_text}**")
                        st.write(f"*Reasoning:* {cand.get('reasoning', '')}")
                        
                        # Case-insensitive comparison without punctuation
                        clean_cand = re.sub(r'[^\w\s]', '', cand_text.lower())
                        clean_target = re.sub(r'[^\w\s]', '', target_word.lower())
                        
                        if clean_cand == clean_target or clean_cand in clean_target or clean_target in clean_cand:
                            match_found = True
                            
                    st.write("---")
                    st.write(f"**True Word:** {target_word}")
                    if match_found:
                        st.success("✅ Match: The true word was found in the candidates!")
                    else:
                        st.error("❌ No Match: The true word was not in the top candidates.")

                st.write("---")
                if "error" in dynasty_res:
                    st.error(f"Dynasty Estimation Error: {dynasty_res['error']}")
                else:
                    st.markdown("#### Dynasty Estimation:")
                    pred_dynasty = dynasty_res.get("dynasty", "Unknown")
                    true_dynasty = selected_ins.get("dynasty", "Unknown")
                    
                    st.write(f"**Predicted Dynasty:** {pred_dynasty}")
                    st.write(f"**True Dynasty:** {true_dynasty}")
                    st.write(f"**Date Range:** {dynasty_res.get('date_range', 'Unknown')}")
                    st.write(f"*Reasoning:* {dynasty_res.get('reasoning', '')}")
                    
                    if pred_dynasty.lower().strip() == true_dynasty.lower().strip() or \
                       pred_dynasty.lower().strip() in true_dynasty.lower().strip() or \
                       true_dynasty.lower().strip() in pred_dynasty.lower().strip():
                        st.success("✅ Dynasty Match!")
                    else:
                        st.error("❌ Dynasty No-Match")

    # --- MODE 2: FREE TEXT ---
    with tab2:
        st.header("Free Text Input")
        st.write("Paste transliterated Old Kannada text. Mark exactly one missing word with `[...]`.")
        
        user_input = st.text_area("Input Text", height=200, placeholder="e.g., svasti śrî jayâbhyudaya [...] saṁvatsarada...")
        
        if st.button("Submit", key="btn_mode2"):
            # Validation
            if contains_non_latin(user_input):
                st.error("Error: Input contains non-Latin scripts (e.g., Kannada script). Please provide transliterated text only.")
            elif user_input.count("[...]") != 1:
                st.error("Error: The text must contain exactly one '[...]' marker.")
            else:
                st.caption("Uses automatic multi-key, multi-provider failover (Gemini + Groq) for reliability.")
                with st.spinner("Restoring text and estimating dynasty..."):
                    
                    # Call APIs with all 12 examples
                    restore_res = restore_gap(user_input, inscriptions)
                    dynasty_res = guess_dynasty(user_input, inscriptions)
                    
                    st.markdown("---")
                    st.subheader("Results")
                    st.info("No ground truth available — result is unverified.")
                    
                    if "error" in restore_res:
                        st.error(f"Restoration Error: {restore_res['error']}")
                    else:
                        st.markdown("#### Top Restoration Candidates:")
                        candidates = restore_res.get("candidates", [])
                        for i, cand in enumerate(candidates, 1):
                            st.write(f"**{i}. {cand.get('text', '')}**")
                            st.write(f"*Reasoning:* {cand.get('reasoning', '')}")
                            
                    st.write("---")
                    
                    if "error" in dynasty_res:
                        st.error(f"Dynasty Estimation Error: {dynasty_res['error']}")
                    else:
                        st.markdown("#### Dynasty Estimation:")
                        st.write(f"**Predicted Dynasty:** {dynasty_res.get('dynasty', 'Unknown')}")
                        st.write(f"**Date Range:** {dynasty_res.get('date_range', 'Unknown')}")
                        st.write(f"*Reasoning:* {dynasty_res.get('reasoning', '')}")

# EVAL SUMMARY SECTION GOES HERE
    st.markdown("---")
    st.header("Evaluation Summary (Curated Benchmark)")
    st.caption("These results are loaded statically from the rigorous evaluation phase (results/eval_results.json) and are not live-recomputed.")
    
    eval_path = Path("results/eval_results.json")
    if eval_path.exists():
        with open(eval_path, "r", encoding="utf-8") as f:
            eval_data = json.load(f)
            
        agg = eval_data.get("aggregate", {})
        
        # Parse exact match counts out of the aggregate strings
        def extract_exact(text):
            m = re.search(r'Raw\):\s*(\d+)/12 exact', text)
            return m.group(1) if m else "0"
            
        baseline_exact = extract_exact(agg.get("baseline", ""))
        zeroshot_exact = extract_exact(agg.get("zero_shot", ""))
        fewshot_exact = extract_exact(agg.get("few_shot", ""))
        
        col1, col2, col3 = st.columns(3)
        col1.metric("Baseline Exact Match", f"{baseline_exact}/12")
        col2.metric("Zero-Shot Exact Match", f"{zeroshot_exact}/12")
        col3.metric("Few-Shot Exact Match", f"{fewshot_exact}/12")
        
        st.subheader("Per-Inscription Breakdown (Few-Shot)")
        
        table_data = []
        for res in eval_data.get("per_inscription_results", []):
            fs_data = res.get("few_shot", {})
            candidates = fs_data.get("candidates", [])
            top_cand = candidates[0] if candidates else "N/A"
            match_status = "✅ Match" if fs_data.get("exact_match_normalized", False) else "❌ No Match"
            
            table_data.append({
                "ID": res.get("id", ""),
                "True Masked Word": res.get("masked_word", ""),
                "Few-Shot Top Candidate": top_cand,
                "Match Status": match_status
            })
            
        st.table(table_data)
    else:
        st.warning("No evaluation results found at results/eval_results.json")

if __name__ == "__main__":
    main()
