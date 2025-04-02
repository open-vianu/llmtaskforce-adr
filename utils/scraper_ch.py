import pandas as pd
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup

def search_spc(xml_file_path, output_json_path):
    """
    1. Parse XML for <medicalInformation lang="de" type="fi"> elements.
    2. Retrieve:
       - Drug Title (<title>)
       - Active Substance (<substances>)
       - Single ATC Code (<atcCode>)
       - In the "ADRs" field, store the text content from the 
         "Unerwünschte Wirkungen" section (Section #11) inside <content>.
    3. Write results to JSON with columns:
       - Drug Name
       - Active Substance
       - Full ATC Class
       - ADRs
    """

    try:
        tree = ET.parse(xml_file_path)
        root = tree.getroot()
    except Exception as e:
        print(f"Error parsing XML: {e}")
        return

    # Select all <medicalInformation> elements with the required attributes
    medical_info_elements = root.findall(".//medicalInformation[@lang='de'][@type='fi']")
    print(f"Found {len(medical_info_elements)} <medicalInformation> elements matching lang='de' and type='fi'.")

    records = []

    for mi_elem in medical_info_elements:
        # 1) Title (drug name)
        title_elem = mi_elem.find("title")
        drug_name = title_elem.text.strip() if (title_elem is not None and title_elem.text) else "Unknown Drug"

        # 2) Substances (active substance)
        subs_elem = mi_elem.find("substances")
        active_substance = subs_elem.text.strip() if (subs_elem is not None and subs_elem.text) else "Unknown Active Substance"

        # 3) ATC code
        atc_elem = mi_elem.find("atcCode")
        atc_code = atc_elem.text.strip() if (atc_elem is not None and atc_elem.text) else ""

        # Skip if no ATC code
        if not atc_code:
            continue

        # 4) Extract <content> HTML so we can find "Unerwünschte Wirkungen" text
        content_elem = mi_elem.find("content")
        adrs_text = ""  # default if we don't find anything

        if content_elem is not None and content_elem.text:
            # Parse <content> as HTML
            soup = BeautifulSoup(content_elem.text, "html.parser")
            
            # Find the <p> with id="section11" -> "Unerwünschte Wirkungen"
            start_tag = soup.find("p", {"id": "section11"})
            if start_tag:
                # We'll collect paragraphs until the next <p> with an id=
                extracted_paras = []
                
                # Move to the *next* sibling after the "Unerwünschte Wirkungen" title
                sibling = start_tag.find_next_sibling()
                while sibling:
                    # If it's a <p> (or other element) *and* has an `id`, we assume the next section started
                    if sibling.name == "p" and sibling.has_attr("id"):
                        break

                    # Otherwise, collect its text
                    extracted_paras.append(sibling.get_text(strip=True))
                    sibling = sibling.find_next_sibling()

                # Join them into one big chunk
                if extracted_paras:
                    adrs_text = "\n".join(extracted_paras)

        # 5) Add record to final DataFrame
        records.append({
            "Drug Name": drug_name,
            "Active Substance": active_substance,
            "Full ATC Class": atc_code,
            "ADRs": adrs_text
        })

    # Convert to DataFrame and export to JSON
    df = pd.DataFrame(records, columns=["Drug Name", "Active Substance", "Full ATC Class", "ADRs"])
    df.to_json(output_json_path, indent=4, orient="records", force_ascii=False)
    print(f"Results successfully written to {output_json_path}")

if __name__ == "__main__":
    xml_path = "./data/AipsDownload_20250402/AipsDownload_20250402.xml"
    output_path = "./data/results/label_ch.json"
    search_spc(xml_path, output_path)