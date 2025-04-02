
import json
from pathlib import Path
import requests
import fitz  # PyMuPDF
from io import BytesIO
import time

import pandas as pd

_EMA_FILENAME = Path(__file__).parents[1] / 'data' / 'PI_URLS.csv'

# List of URLs to PDF files
urls = [
    'http://example.com/path/to/pdf1.pdf',
    'http://example.com/path/to/pdf2.pdf',
    # Add more URLs as needed
]

def extract_text_between_chapters(pdf_text):
    # Use regular expressions to find the text between the start and end chapters
    start = pdf_text.lower().find('undesirable effects')
    end = pdf_text.lower().find('overdose')
    if start == -1 or end == -1:
        raise ValueError("Chapter not found")

    return pdf_text[start:end]

def download_and_extract_text(url):
    response = requests.get(url, timeout=10)
    if response.status_code == 200:
        pdf_file = BytesIO(response.content)
        document = fitz.open(stream=pdf_file, filetype="pdf")
        text = ""
        for page_num in range(len(document)):
            page = document[page_num]
            text += page.get_text()
        return text
    else:
        try:
            response.raise_for_status()
        except Exception as e:
            raise ValueError(f"Failed to download PDF from {url}: {e}")

def scrape_text(url: str):
    pdf_text = download_and_extract_text(url)
    extracted_text = extract_text_between_chapters(pdf_text)
    return extracted_text


if __name__ == '__main__':
    print('Opening file...')
    df = pd.read_csv(_EMA_FILENAME)
    print(df.head())
    number_of_tries = 2
    error_timout = 10
    iter_timeout = 2
    start = 50
    end = 60

    ema_data = []
    for i, row in list(df.iterrows())[start:end]:
        print(f'Processing row {i}...')
        product_name = row['ProductName']
        url = row['URL(currentwebsite)']
        count = 0
        err = None

        while count < number_of_tries:
            try:
                text = scrape_text(url)
                ema_data.append({'Drug Name': product_name, "ADRs": text})
                break
            except Exception as e:
                err = e
                sleep = error_timout*(count+1)
                print(f'   Retrying {product_name} (count={count}, sleep={sleep})...')
                time.sleep(sleep)
                count += 1
        
        if err:
            print(f'Error occurred for {product_name} and url={url} (ignorring): {err}')
            continue
        # Save json
        with open(f'data/lable_ema_{start:04}_{end-1:04}.json', 'w') as jfile:
            json.dump(ema_data, jfile, indent=4)
        
        time.sleep(iter_timeout)  # Add a delay to avoid hitting the server too frequently

