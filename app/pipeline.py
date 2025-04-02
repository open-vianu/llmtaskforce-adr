import re
import openai
import sys

def check_rule_based(adr: str, drug_label: str) -> bool:
    """
    Basic, fast rule-based check to see if `adr` is in `drug_label`.
    Both inputs are expected to be pre-lowercased.
    Returns True if adr is found, else False.
    """
    # Basic exact substring check
    if adr in drug_label:
        return True

    # Optionally, you could add more sophisticated logic here, e.g.:
    # - word boundary checks
    # - simple fuzzy matching
    # - etc.
    # For demonstration, let's do a simple word boundary check:
    pattern = r"\b" + re.escape(adr) + r"\b"
    if re.search(pattern, drug_label):
        return True

    return False

def extract_adrs(openai_api_key: str, drug_label: str, language: str) -> dict:
    """
    Calls the OpenAI ChatCompletion endpoint using GPT-4.
    Asks the model to extract all potential Adverse Events (AEs) in a comma-separated list,
    keeping to the language provided,
    returning chain-of-thought in <think> ... </think> and the final list outside.
    Returns a dict with keys: 'chain_of_thought', 'extracted_list'.
    """
    openai.api_key = openai_api_key

    system_msg = (
        "You are a helpful assistant. Extract all potential Adverse Events (AEs) "
        f"from the provided drug label in a comma-separated list. Keep the language in {language}, "
        "including your chain-of-thought."
        "Return your chain-of-thought inside <think> ... </think> tags, "
        "followed by the final comma-separated list outside those tags."
    )
    user_msg = f"Drug label:\n{drug_label}"

    response = openai.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": system_msg},
            {"role": "user", "content": user_msg}
        ],
        temperature=0.0
    )

    # The new library returns an object with attribute access
    full_text = response.choices[0].message.content

    chain_of_thought = ""
    extracted_list = ""

    # Attempt to parse out <think> ... </think>
    pattern = re.compile(r"<think>(.*?)</think>(.*)", re.DOTALL)
    match = pattern.search(full_text)
    if match:
        chain_of_thought = match.group(1).strip()
        extracted_list = match.group(2).strip()
    else:
        # Fallback if no <think> tags
        extracted_list = full_text.strip()

    return {
        "chain_of_thought": chain_of_thought,
        "extracted_list": extracted_list
    }

def check_adr_in_extracted_list(openai_api_key: str, adr: str, extracted_adrs: str, language: str) -> dict:
    """
    Calls the OpenAI ChatCompletion endpoint (GPT-4) to verify 
    if `adr` is in the extracted list of AEs that are provided in a given language.
    Returns a dict with 'chain_of_thought' and 'final_answer' (Yes/No).
    """
    openai.api_key = openai_api_key

    system_msg = (
        "You are a helpful assistant. Given a user ADR, see if it's present in a "
        f"list of extracted ADRs in {language}. "
        " These are extracted ADRs from a drug label and we want to check whether we could consider the user provided ADR as labelled or not. "
        "Therefore, we are not only checking the exact match of the ADR in the list, but synonyms as well. "
        "Provide chain-of-thought in <think> tags, "
        f"Please have your chain-of-thought reasoning in {language}. "
        "Note that your chain-of-thought reasoning around whether the ADR can be considered labelled or not is very important "
        "and will be reviewed by a human assessor, so please explain your reasoning well. "
        "Finally, output your final answer regarding whether the user provided ADR is labelled or not, "
        "outside those <think> tags as 'Yes' or 'No'."
    )
    user_msg = f"User ADR: {adr}\nExtracted ADRs: {extracted_adrs}"

    response = openai.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": system_msg},
            {"role": "user", "content": user_msg}
        ],
        temperature=0.0
    )

    # Use attribute access in the new library
    full_text = response.choices[0].message.content
    chain_of_thought = ""
    final_answer = ""

    pattern = re.compile(r"<think>(.*?)</think>(.*)", re.DOTALL)
    match = pattern.search(full_text)
    if match:
        chain_of_thought = match.group(1).strip()
        final_answer = match.group(2).strip()
    else:
        final_answer = full_text.strip()

    return {
        "chain_of_thought": chain_of_thought,
        "final_answer": final_answer
    }

def pipeline(
    openai_api_key: str,
    adr: str,
    drug_label: str,
    skip_advanced_if_found: bool = True
):
    """
    Full pipeline demonstration: 
      1) do basic rule-based check 
      2) if not found, do advanced GPT extraction 
      3) do advanced GPT check 
    Returns a dictionary with results from each step.
    """
    results = {
        "rule_based_found": None,
        "extraction_chain_of_thought": None,
        "extracted_adr_list": None,
        "advanced_check_chain_of_thought": None,
        "advanced_check_answer": None
    }

    # 1) Rule-based check
    found_rule = check_rule_based(adr, drug_label)
    results["rule_based_found"] = found_rule

    if found_rule and skip_advanced_if_found:
        # Stop if found in rule-based step
        return results

    # 2) Advanced extraction
    extraction_result = extract_adrs(openai_api_key, drug_label)
    results["extraction_chain_of_thought"] = extraction_result["chain_of_thought"]
    results["extracted_adr_list"] = extraction_result["extracted_list"]

    # 3) Check if ADR is in extracted list
    check_result = check_adr_in_extracted_list(
        openai_api_key,
        adr,
        extraction_result["extracted_list"]
    )
    results["advanced_check_chain_of_thought"] = check_result["chain_of_thought"]
    results["advanced_check_answer"] = check_result["final_answer"]

    return results


if __name__ == "__main__":
    """
    Example usage of pipeline in a standalone manner:
    python pipeline.py "my-openai-key" "headache" "this label has headache and dizziness"
    """
    if len(sys.argv) < 4:
        print("Usage: python pipeline.py <OPENAI_API_KEY> <ADR> <LABEL>")
        sys.exit(1)

    openai_api_key = sys.argv[1]
    adr = sys.argv[2].lower().strip()  # quick basic sanitization
    drug_label = " ".join(sys.argv[3:]).lower()  # combine the rest as label

    results = pipeline(openai_api_key, adr, drug_label)

    print("----- PIPELINE RESULTS -----")
    print(f"1) Rule-based found: {results['rule_based_found']}")
    if not results["rule_based_found"]:
        print("2) Extraction chain-of-thought:")
        print(results["extraction_chain_of_thought"])
        print("   Extracted ADR list:")
        print(results["extracted_adr_list"])
        print("3) Advanced check chain-of-thought:")
        print(results["advanced_check_chain_of_thought"])
        print("   Final advanced check answer (Yes/No):")
        print(results["advanced_check_answer"])
    print("----------------------------")