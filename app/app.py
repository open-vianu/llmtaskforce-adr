import streamlit as st
import os
import re
import json
# We'll assume you have pipeline.py in the same folder
from pipeline import (
    check_rule_based,
    extract_adrs,
    check_adr_in_extracted_list
)

# -----------------------------------------------------------------------------
# 1) Sentence-splitting helper
# -----------------------------------------------------------------------------
def get_first_sentences(text: str, num_sentences=2) -> str:
    """
    Rough splitting of text into sentences, returning the first `num_sentences`.
    You can improve this logic with proper NLP if needed.
    """
    sentence_split = re.split(r'(?<=[.!?])\s+', text.strip())
    first_part = " ".join(sentence_split[:num_sentences])
    return first_part

# -----------------------------------------------------------------------------
# 2) Clear conversation logic
# -----------------------------------------------------------------------------
def clear_conversation():
    st.session_state["conversation_logs"] = []
    st.session_state["adr"] = ""
    st.session_state["drug_label"] = ""

# -----------------------------------------------------------------------------
# 3) Main Streamlit App
# -----------------------------------------------------------------------------
st.title("ADR Labeling Comparison Tool")
st.write(
    "This app demonstrates a two-step process to determine if a user-provided "
    "ADR (Adverse Drug Reaction) is present in a drug label. "
    "First, we do a quick rule-based check. If not found, we use GPT-4 to extract "
    "potential ADRs and then verify again.\n\n"
)

# Make sure we have a session_state container for local storage
if "openai_api_key" not in st.session_state:
    st.session_state["openai_api_key"] = ""
if "conversation_logs" not in st.session_state:
    st.session_state["conversation_logs"] = []
if "adr" not in st.session_state:
    st.session_state["adr"] = ""
if "drug_label" not in st.session_state:
    st.session_state["drug_label"] = ""

# ----------------------------------------------------------------
# 4) UI for OpenAI Key
# ----------------------------------------------------------------
openai_api_input = st.text_input(
    "Enter your OpenAI API Key (GPT-4 access):",
    type="password",
    value=st.session_state["openai_api_key"]
)

# If user typed a new key, store it in session
if openai_api_input != st.session_state["openai_api_key"]:
    st.session_state["openai_api_key"] = openai_api_input

# -----------------------------------------------------------------------------
# 5) Label Origin
# -----------------------------------------------------------------------------
st.subheader("Label Origin")
label_origin = st.selectbox(
    "Select the origin of the label:",
    ["Experimental", "Switzerland 🇨🇭", "EMA 🇪🇺"]
)

# -----------------------------------------------------------------------------
# 6) UI: ADR
# -----------------------------------------------------------------------------
st.session_state["adr"] = st.text_input(
    "Adverse Drug Reaction (ADR):",
    value=st.session_state["adr"],
    placeholder="Type in your ADR here."
)

# -----------------------------------------------------------------------------
# 7) Load labels based on origin
# -----------------------------------------------------------------------------
LABEL_PATH = "./data/txtfiles/"  # For Experimental
RESULTS_PATH = "./data/results/"  # For JSON files

def load_json_labels(json_file_path):
    """Load and return the array of label objects from the given JSON file."""
    if not os.path.isfile(json_file_path):
        return []
    with open(json_file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data

# Prepare variables for user selection
label_data = []         # Will hold the list of label dictionaries for CH or EMA
label_files_list = []   # Will hold .txt file names for Experimental

if label_origin == "Experimental":
    # List .txt files in LABEL_PATH
    if os.path.isdir(LABEL_PATH):
        label_files_list = [
            f for f in os.listdir(LABEL_PATH) 
            if f.lower().endswith(".txt")
        ]
    else:
        st.warning(f"No directory found at {LABEL_PATH}")

elif label_origin == "Switzerland 🇨🇭":
    # Load labels_ch.json
    label_data = load_json_labels(os.path.join(RESULTS_PATH, "label_ch.json"))
    if not label_data:
        st.warning("No Swiss labels found (label_ch.json missing or empty).")

elif label_origin == "EMA 🇪🇺":
    # Load labels_ema.json
    label_data = load_json_labels(os.path.join(RESULTS_PATH, "label_ema.json"))
    if not label_data:
        st.warning("No EMA labels found (labels_ema.json missing or empty).")


# -----------------------------------------------------------------------------
# 8) Let user pick label (depending on origin)
# -----------------------------------------------------------------------------
st.subheader("Select or Paste Drug Label")

if label_origin == "Experimental":
    # Let user pick from .txt files, or paste their own
    selected_label_file = st.selectbox(
        "Choose a sample text file:",
        ["None"] + label_files_list
    )

    # If user picked a file, read it in
    if selected_label_file != "None":
        with open(os.path.join(LABEL_PATH, selected_label_file), "r", encoding="utf-8") as f:
            label_text = f.read()
        st.session_state["drug_label"] = label_text.lower()
    else:
        # Otherwise, let them paste
        user_paste = st.text_area(
            "Or paste your own drug label text here:",
            value=st.session_state["drug_label"]
        )
        st.session_state["drug_label"] = user_paste.lower()

elif label_origin in ["Switzerland 🇨🇭", "EMA 🇪🇺"]:
    # Let user pick from label_data
    if label_data:
        # Show a selectbox of all "Drug Name" fields
        drug_names = [item["Drug Name"] for item in label_data]
        chosen_drug = st.selectbox("Pick a label:", drug_names)
        # Find the selected drug in label_data
        selected_item = next(x for x in label_data if x["Drug Name"] == chosen_drug)
        # For convenience, combine all relevant fields into the "drug_label"
        # or just the ADR text if that's all you care about:
        # e.g., we combine "Drug Name", "Active Substance", "ADRs" etc. into one big text
        combined_text = (
            f"Drug Name: {selected_item.get('Drug Name','')}\n\n"
            f"Active Substance: {selected_item.get('Active Substance','')}\n\n"
            f"ATC Class: {selected_item.get('Full ATC Class','')}\n\n"
            f"ADRs:\n{selected_item.get('ADRs','')}\n"
        )
        st.session_state["drug_label"] = combined_text.lower()
    else:
        # Fallback if there's no data
        st.info("No JSON data loaded or empty file. Please provide a valid JSON.")

# -----------------------------------------------------------------------------
# 9) Buttons: Clear Conversation / Run Check
# -----------------------------------------------------------------------------
st.button("Clear Conversation", on_click=clear_conversation)

if st.button("Run ADR Check"):
    # Clear logs for a fresh run
    st.session_state["conversation_logs"] = []

    openai_key = st.session_state["openai_api_key"]
    if not openai_key:
        st.error("Please provide an OpenAI API key to continue.")
    else:
        adr = st.session_state["adr"].strip().lower()
        label_text = st.session_state["drug_label"].strip().lower()

        if not adr:
            st.error("ADR cannot be empty.")
        elif not label_text:
            st.error("Drug label cannot be empty.")
        else:
            # 1) Show a short preview of the label
            short_preview = get_first_sentences(label_text, num_sentences=2)
            st.session_state["conversation_logs"].append({
                "role": "assistant",
                "message": (
                    "**Here is the selected drug label (preview):**\n\n"
                    f"{short_preview}\n\n"
                    "You can expand below to see the full text."
                ),
                "full_label": label_text
            })

            # 2) Rule-based check
            user_msg = f"Is the ADR '{adr}' found in the label (rule-based)?"
            st.session_state["conversation_logs"].append({
                "role": "user",
                "message": f"**User:** {user_msg}"
            })

            found_rule_based = check_rule_based(adr, label_text)
            if found_rule_based:
                # If found, just show that we found it
                assistant_msg = (
                    "I am first applying some rule-based checks.\n\n"
                    f"Result: **Yes**, the ADR '{adr}' was found via rule-based check!"
                )
                st.session_state["conversation_logs"].append({
                    "role": "assistant",
                    "message": assistant_msg
                })
            else:
                # If not found, proceed with advanced technique
                assistant_msg = (
                    "I am first applying some rule-based checks.\n\n"
                    f"Result: **No**, the ADR '{adr}' was **not** found via rule-based check.\n\n"
                    "Let's proceed to advanced GPT-4 extraction."
                )
                st.session_state["conversation_logs"].append({
                    "role": "assistant",
                    "message": assistant_msg
                })

                # 2a) GPT-4 extraction
                user_extraction_msg = (
                    "Please extract all potential ADRs from the label using GPT-4 (comma-separated)."
                )
                st.session_state["conversation_logs"].append({
                    "role": "user",
                    "message": f"**User:** {user_extraction_msg}"
                })

                extraction_result = extract_adrs(openai_key, label_text)
                chain_of_thought_extraction = extraction_result["chain_of_thought"]
                extracted_list = extraction_result["extracted_list"]

                assistant_msg_extraction = (
                    f"**GPT-4 chain-of-thought (extraction):**\n\n"
                    f"`{chain_of_thought_extraction}`\n\n"
                    f"**Extracted ADRs (comma-separated):**\n"
                    f"{extracted_list}"
                )
                st.session_state["conversation_logs"].append({
                    "role": "assistant",
                    "message": assistant_msg_extraction
                })

                # 2b) Checking user ADR in that extracted list
                user_check_msg = f"Check if '{adr}' is in the extracted ADR list."
                st.session_state["conversation_logs"].append({
                    "role": "user",
                    "message": f"**User:** {user_check_msg}"
                })

                check_result = check_adr_in_extracted_list(openai_key, adr, extracted_list)
                final_chain_of_thought = check_result["chain_of_thought"]
                final_answer = check_result["final_answer"]

                assistant_msg_check = (
                    f"**GPT-4 reasoning (final check):**\n\n"
                    f"`{final_chain_of_thought}`\n\n"
                    f"**Final Answer:** {final_answer}"
                )
                st.session_state["conversation_logs"].append({
                    "role": "assistant",
                    "message": assistant_msg_check
                })

# -----------------------------------------------------------------------------
# 10) Display conversation in a chat-like interface
# -----------------------------------------------------------------------------
for log in st.session_state["conversation_logs"]:
    if log["role"] == "user":
        with st.chat_message("user"):
            st.markdown(log["message"])
    else:
        # For assistant messages, if there's a full_label, show it in an expander
        with st.chat_message("assistant"):
            if "full_label" in log:
                st.markdown(log["message"])
                with st.expander("Show full drug label"):
                    st.write(log["full_label"])
            else:
                st.markdown(log["message"])