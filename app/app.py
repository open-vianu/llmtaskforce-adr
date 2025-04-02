import streamlit as st
import os
import re
# We'll assume you have pipeline.py in the same folder
from pipeline import (
    check_rule_based,
    extract_adrs,
    check_adr_in_extracted_list
)

# Set page config
st.set_page_config(page_title="ADR Labeling Comparison Tool", layout="wide")


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

# Make sure we have a session_state container for the local storage sync
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

# If user typed a new key in the text_input, store it in session
# This ensures that after the user types, we update local storage on next run
if openai_api_input != st.session_state["openai_api_key"]:
    st.session_state["openai_api_key"] = openai_api_input

# ----------------------------------------------------------------
# 5) UI for user to provide ADR & Label
# ----------------------------------------------------------------
st.subheader("User Input")

st.session_state["adr"] = st.text_input(
    "Adverse Drug Reaction (ADR):",
    value=st.session_state["adr"],
    placeholder="Type in your ADR here."
)

LABEL_PATH = "./data/txtfiles/"
available_labels = []
if os.path.isdir(LABEL_PATH):
    available_labels = os.listdir(LABEL_PATH)

selected_label_file = st.selectbox(
    "Choose a sample label file:",
    ["None"] + available_labels
)

drug_label_text = st.text_area(
    "Or paste your own drug label text here:",
    value=st.session_state["drug_label"]
)

# If the user selected a file, load it
if selected_label_file != "None":
    with open(os.path.join(LABEL_PATH, selected_label_file), "r") as f:
        st.session_state["drug_label"] = f.read().lower()
else:
    st.session_state["drug_label"] = drug_label_text.lower()

# ----------------------------------------------------------------
# 6) Buttons: Clear Conversation / Run Check
# ----------------------------------------------------------------
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
            # --- Chat: Display the drug label with a short preview in an assistant message
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

            # 1) Rule-based check
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

                # 2) GPT-4 extraction
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

                # 3) Checking user ADR in that extracted list
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

# ----------------------------------------------------------------
# 7) Display conversation in a chat-like interface
# ----------------------------------------------------------------
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