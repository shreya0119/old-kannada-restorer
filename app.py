import json
import random
import re
from pathlib import Path
import streamlit as st
import pandas as pd

from src.restore import restore_gap
from src.dynasty import guess_dynasty

# Ensure page config is set
st.set_page_config(page_title="Old Kannada Restorer", layout="wide")

def apply_stone_theme():
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&family=Spectral:wght@400;700&family=Yatra+One&display=swap');

        :root {
            --bg-primary: #201D19;
            --bg-surface: #2E2A25;
            --bg-elevated: #3A352E;
            --text-primary: #D9D0C1;
            --text-muted: #948A7A;
            --accent: #8B5A3C;
            --accent-hover: #A66F4D;
            --match-color: #6E7C5A;
            --nomatch-color: #8C4B3D;
        }

        /* 4. Style the overall app background */
        .stApp {
            background-color: var(--bg-primary);
            background-image: 
                repeating-linear-gradient(
                    45deg,
                    rgba(255, 255, 255, 0.02) 0px,
                    rgba(255, 255, 255, 0.02) 1px,
                    transparent 1px,
                    transparent 4px
                ),
                linear-gradient(rgba(32, 29, 25, 0.85), rgba(32, 29, 25, 0.85)),
                url('https://commons.wikimedia.org/wiki/Special:FilePath/Halmidi_OldKannada_inscription.JPG');
            background-size: auto, cover, cover;
            background-position: center, center, center;
            background-repeat: repeat, no-repeat, no-repeat;
            background-attachment: scroll, fixed, fixed;
        }

        /* Ensure transparent backgrounds for content containers so the watermark shows through */
        .stMainBlockContainer, [data-testid="stHeader"] {
            background: transparent !important;
        }

        /* 5. Headings and typography */
        html {
            font-size: calc(100% + 1pt);
        }

        h1, h2, h3, h4, h5, h6, .st-emotion-cache-10trblm h1 {
            font-family: 'Yatra One', cursive !important;
            color: var(--text-primary) !important;
            letter-spacing: 0.05em;
        }
        
        .stApp, p, div, span, label {
            font-family: 'Spectral', serif;
            color: var(--text-primary);
        }
        
        small, .stCaption, [data-testid="stCaptionContainer"] p, [data-testid="stCaptionContainer"] span {
            font-family: 'Spectral', serif;
            color: var(--text-muted) !important;
        }

        /* Inscription ID text and table data */
        table, th, td, [data-testid="stSelectbox"] div, [data-testid="stSelectbox"] span {
            font-family: 'JetBrains Mono', monospace !important;
        }

        /* 6. Mode 1 / Mode 2 tab selector */
        .stTabs [data-baseweb="tab-list"] {
            gap: 10px;
        }
        .stTabs [data-baseweb="tab"] {
            background-color: var(--bg-surface) !important;
            border-radius: 8px 8px 0 0 !important;
            box-shadow: 0 -2px 5px rgba(0,0,0,0.2) !important;
            border-bottom: 3px solid transparent !important;
            padding: 10px 20px !important;
            border-top: 1px solid var(--bg-elevated);
            border-left: 1px solid var(--bg-elevated);
            border-right: 1px solid var(--bg-elevated);
        }
        .stTabs [data-baseweb="tab"][aria-selected="true"] {
            border-bottom: 3px solid var(--accent) !important;
            background-color: var(--bg-elevated) !important;
        }
        .stTabs [data-baseweb="tab"] p {
            font-family: 'Yatra One', cursive !important;
            color: var(--text-primary) !important;
            font-size: calc(100% + 4pt) !important;
        }

        /* 7. Stone Panel and Gap */
        .stone-panel {
            background-color: var(--bg-surface);
            border: 1px solid var(--bg-elevated);
            padding: 15px;
            color: var(--text-primary);
            font-family: 'Spectral', serif;
            border-radius: 4px;
            min-height: 100px;
            white-space: pre-wrap;
            box-shadow: inset 0 2px 4px rgba(0,0,0,0.3);
        }
        .stone-gap {
            background-color: var(--accent);
            padding: 0 15px;
            /* Jagged notch effect */
            clip-path: polygon(2% 10%, 98% 5%, 100% 90%, 5% 95%, 8% 50%);
            display: inline-block;
            color: var(--text-primary);
        }

        /* 8. Mode 2 free-text input */
        .stTextArea textarea {
            background-color: var(--bg-surface) !important;
            border: 1px solid var(--bg-elevated) !important;
            color: var(--text-primary) !important;
            font-family: 'Spectral', serif !important;
            box-shadow: inset 0 2px 4px rgba(0,0,0,0.3) !important;
        }

        /* Override Streamlit's default red focus borders globally */
        div[data-baseweb="input"] > div,
        div[data-baseweb="select"] > div,
        textarea {
            transition: border-color 0.2s, box-shadow 0.2s !important;
        }
        
        div[data-baseweb="input"]:focus-within > div,
        div[data-baseweb="select"]:focus-within > div,
        textarea:focus {
            border-color: #D4AF37 !important;
            box-shadow: 0 0 0 1px #D4AF37 !important;
        }

        /* 9. Restyle st.button */
        .stButton button {
            background-color: var(--bg-elevated) !important;
            border: 1px solid var(--accent) !important;
            color: var(--text-primary) !important;
            font-family: 'Yatra One', cursive !important;
            font-variant: small-caps !important;
            border-radius: 4px !important;
            box-shadow: 2px 2px 5px rgba(0,0,0,0.3) !important;
            transition: all 0.2s ease !important;
        }
        .stButton button:hover {
            background-color: var(--accent) !important;
            color: var(--bg-primary) !important;
            border-color: var(--accent-hover) !important;
        }

        /* 10. Eval Summary */
        [data-testid="stMetricValue"] div {
            font-family: 'JetBrains Mono', monospace !important;
            color: var(--accent) !important;
        }
        [data-testid="stMetricLabel"] p, [data-testid="stMetricLabel"] div {
            color: var(--text-muted) !important;
            font-family: 'Spectral', serif !important;
        }
        /* 11. Alerts / Messages */
        [data-testid="stAlert"] {
            background-color: var(--bg-elevated) !important;
            color: var(--text-primary) !important;
        }
        [data-testid="stAlert"] p, [data-testid="stAlert"] span {
            color: var(--text-primary) !important;
        }
        /* Success */
        div[data-testid="stAlert"]:has(> div[data-baseweb="notification"] > div[role="alert"][aria-label="Success"]) {
            border-left: 4px solid var(--match-color) !important;
        }
        /* Error */
        div[data-testid="stAlert"]:has(> div[data-baseweb="notification"] > div[role="alert"][aria-label="Error"]) {
            border-left: 4px solid var(--nomatch-color) !important;
        }
        /* Info */
        div[data-testid="stAlert"]:has(> div[data-baseweb="notification"] > div[role="alert"][aria-label="Info"]) {
            border-left: 4px solid var(--accent) !important;
        }
        /* Warning */
        div[data-testid="stAlert"]:has(> div[data-baseweb="notification"] > div[role="alert"][aria-label="Warning"]) {
            border-left: 4px solid var(--accent-hover) !important;
        }

        /* 12. Eval Table Custom HTML */
        .eval-table {
            width: 100%;
            border-collapse: collapse;
            border: 1px solid var(--bg-elevated);
        }
        .eval-table th, .eval-table td {
            font-family: 'JetBrains Mono', monospace;
            padding: 10px;
            text-align: left;
            border-bottom: 1px solid var(--bg-elevated);
        }
        .eval-table th {
            background-color: var(--bg-elevated);
            color: var(--text-muted);
            font-weight: 700;
        }
        .eval-table tr:nth-child(even) {
            background-color: var(--bg-elevated);
        }
        .eval-table tr:nth-child(odd) {
            background-color: var(--bg-surface);
        }

        /* 13. Candidate Tags */
        .candidate-tag {
            display: inline-block;
            background-color: white;
            color: #D4AF37;
            padding: 2px 8px;
            border-radius: 8px;
            font-weight: bold;
            margin-right: 5px;
            font-family: 'JetBrains Mono', monospace;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

apply_stone_theme()

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
    st.markdown("<h1 style='text-align: center; font-size: calc(2.25rem + 2pt);'>Halegannada Inscription Restorer</h1>", unsafe_allow_html=True)
    st.markdown("""
        <p style='font-size: calc(100% + 2pt);'>
            
        This prototype uses large language models (Gemini & Groq) with few-shot prompting to deduce missing words in transliterated Old Kannada inscriptions. Rather than relying on a custom-trained model, it dynamically builds context using a curated reference dataset to restore damaged text and estimate the dynasty/date of the artifact.
        </p>
    """, unsafe_allow_html=True)
    st.write("") # Light spacing
    
    inscriptions = load_data()
    
    if not inscriptions:
        return

    tab1, tab2 = st.tabs(["Mode 1: Verified (Dropdown)", "Mode 2: Free Text"])

    # --- MODE 1: VERIFIED ---
    with tab1:
        st.markdown("### Verified Inscriptions")
        
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
        
        st.markdown("#### Original Text")
        st.markdown(f'<div class="stone-panel">{selected_ins["text"]}</div>', unsafe_allow_html=True)
        
        st.markdown("#### Masked Text (Input)")
        # Find [...] and wrap it in the stone-gap span
        masked_html = masked_text.replace("[...]", '<span class="stone-gap">[...]</span>')
        st.markdown(f'<div class="stone-panel">{masked_html}</div>', unsafe_allow_html=True)
        
        st.write("") # spacing
        
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
                        st.markdown(f'<span class="candidate-tag">{i}. {cand_text}</span>', unsafe_allow_html=True)
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
        st.markdown("### Free Text Input")
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
                            cand_text = cand.get('text', '')
                            st.markdown(f'<span class="candidate-tag">{i}. {cand_text}</span>', unsafe_allow_html=True)
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
    st.markdown("### Evaluation Summary (Curated Benchmark)")
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
        
        st.markdown("#### Per-Inscription Breakdown (Few-Shot)")
        
        table_html = '<table class="eval-table">'
        table_html += '<thead><tr><th>ID</th><th>True Masked Word</th><th>Few-Shot Top Candidate</th><th>Match Status</th></tr></thead><tbody>'
        
        for res in eval_data.get("per_inscription_results", []):
            fs_data = res.get("few_shot", {})
            candidates = fs_data.get("candidates", [])
            top_cand = candidates[0] if candidates else "N/A"
            is_match = fs_data.get("exact_match_normalized", False)
            match_status = "✅ Match" if is_match else "❌ No Match"
            
            # Use inline styles for the color since it needs to render raw
            color_var = "var(--match-color)" if is_match else "var(--nomatch-color)"
            
            table_html += f'<tr><td>{res.get("id", "")}</td><td>{res.get("masked_word", "")}</td><td>{top_cand}</td><td style="color: {color_var}; font-weight: bold;">{match_status}</td></tr>'
            
        table_html += '</tbody></table>'
        st.markdown(table_html, unsafe_allow_html=True)
    else:
        st.warning("No evaluation results found at results/eval_results.json")

    # Image attribution
    st.markdown("<p style='text-align: center; color: var(--text-muted); font-size: 0.8rem; margin-top: 3rem;'>Background: Halmidi inscription (450 CE) photograph by Dineshkannambadi, CC BY-SA 3.0, via Wikimedia Commons.</p>", unsafe_allow_html=True)

if __name__ == "__main__":
    main()
