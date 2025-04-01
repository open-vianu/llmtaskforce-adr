import streamlit as st
from utils import is_in_label

import ollama


st.write("ADR labeling comaprison Tool")
adr = st.text_input("Adverse Drug Reaction", key="adr", placeholder="Type in your ADR here.")
drug_label = st.text_input("Drug Label", key="label", placeholder="Type in your Label document here.")
model_names = ["deepseek-r1:1.5b","llama3.2:1b"]
selected_model = st.multiselect("Select the model you want to use", model_names)

if adr and drug_label:
    prompt = f'You will be asked wether a user defined ADR was found in a given drug label. Make sure to return only a True (if the ADR was foudn in the drug label) or False (if it was not found in the drug label) \n User entered ADR: {adr}\nThe drug label is: {drug_label}. '
    response = ollama.chat(
        selected_model,
        messages=[{'role': 'user', 'content': prompt}],
        )
    results = response["message"]["content"]
    model_used = response["model"]

    st.write(f"Model used: {model_used}")
    st.write(f"Models response:\n{results}")

