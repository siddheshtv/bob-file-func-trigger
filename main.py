import os
import time
import json
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import PyPDF2
import requests
import dotenv

dotenv.load_dotenv()

class PDFHandler(FileSystemEventHandler):
    def __init__(self, api_key, api_url):
        self.api_key = api_key
        self.api_url = api_url

    def on_created(self, event):
        if not event.is_directory and event.src_path.endswith('.pdf'):
            self.process_pdf(event.src_path)

    def process_pdf(self, pdf_path):
        # Extract text from PDF
        text = self.extract_text_from_pdf(pdf_path)

        # Send request to Azure OpenAI
        response = self.send_to_azure_openai(text)

        # Save response as JSON
        self.save_response(response, pdf_path)

    def extract_text_from_pdf(self, pdf_path):
        with open(pdf_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            text = ""
            for page in reader.pages:
                text += page.extract_text()
        return text

    def send_to_azure_openai(self, content):
        headers = {
            "Content-Type": "application/json",
            "api-key": self.api_key
        }
        
        data = {
            "messages": [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": f"""
                Based on the following content, provide:
                1. Implementation Hardness level
                2. Who passed the guideline
                3. When the Guideline was published (active date)
                4. The department of the bank this guideline is for
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

    path = "./bob-summa/files"
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