import os
import time
import json
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import PyPDF2
import requests
import dotenv

import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')


dotenv.load_dotenv()

banking_departments = """
Retail Banking/
Corporate Banking/
Treasury/
Risk Management/
Compliance/
Audit and Inspection/
Human Resources/
Information Technology/
Operations/
Credit/
International Banking/
Legal/
Marketing/
Recovery/
Customer Service/
Accounts and Finance/
Branch Administration/
Wealth Management/
Agricultural and Rural Banking/
Small and Medium Enterprises (SME) Banking
"""

class PDFHandler(FileSystemEventHandler):
    def __init__(self, api_key, api_url):
        self.api_key = api_key
        self.api_url = api_url

    def on_created(self, event):
        if not event.is_directory and event.src_path.endswith('.pdf'):
            self.process_pdf(event.src_path)

    def process_pdf(self, pdf_path):
        try:
            text = self.extract_text_from_pdf(pdf_path)
            if not text:
                logging.warning(f"Failed to extract text from {pdf_path}")
                return

            response = self.send_to_azure_openai(text)

            self.save_response(response, pdf_path)
        except Exception as e:
            logging.error(f"Error processing {pdf_path}: {str(e)}")

    def extract_text_from_pdf(self, pdf_path):
        try:
            with open(pdf_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                text = ""
                for page in reader.pages:
                    text += page.extract_text()
            return text
        except Exception as e:
            logging.error(f"Error extracting text from {pdf_path}: {str(e)}")
            return None

    def send_to_azure_openai(self, content):
        headers = {
            "Content-Type": "application/json",
            "api-key": self.api_key
        }
        
        data = {
            "messages": [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": f"""
                Based on the following content, provide (ONE WORD ONLY):
                1. Implementation Hardness level (Easy/Medium/Hard)
                2. Who passed the guideline (Name of person/or someone who has made the guideline)
                3. When the Guideline was published (active date)
                4. The department of the bank this guideline is for {banking_departments}
                Content: {content}
                Please provide concise answers to minimize token usage.
                """}
            ]
        }

        response = requests.post(self.api_url, headers=headers, json=data)
        return response.json()

    def save_response(self, response, pdf_path):
        output_filename = os.path.splitext(os.path.basename(pdf_path))[0] + '_analysis.json'
        output_path = os.path.join(os.path.dirname(pdf_path), output_filename)
        with open(output_path, 'w') as f:
            json.dump(response, f, indent=2)

if __name__ == "__main__":
    api_key = os.getenv("API_KEY")
    api_url = os.getenv("API_ENDPOINT")

    path = "./files"
    event_handler = PDFHandler(api_key, api_url)
    observer = Observer()
    observer.schedule(event_handler, path, recursive=False)
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()