import os
import json
import PyPDF2
import requests
import dotenv
import logging
import hashlib
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import JSONResponse
import uvicorn
from io import BytesIO

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
dotenv.load_dotenv()

app = FastAPI()

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

class PDFProcessor:
    def __init__(self, api_key, api_url):
        self.api_key = api_key
        self.api_url = api_url
        self.processed_files = set()

    async def process_pdf(self, file: UploadFile):
        try:
            contents = await file.read()
            file_hash = self.get_file_hash(contents)
            
            if file_hash in self.processed_files:
                return JSONResponse(content={"message": "Duplicate file, skipped processing"}, status_code=200)

            text = self.extract_text_from_pdf(contents)
            if not text:
                return JSONResponse(content={"message": "Failed to extract text from PDF"}, status_code=400)

            response = self.send_to_azure_openai(text)
            self.processed_files.add(file_hash)
            return JSONResponse(content=response, status_code=200)
        except Exception as e:
            logging.error(f"Error processing PDF: {str(e)}")
            return JSONResponse(content={"message": f"Error processing PDF: {str(e)}"}, status_code=500)

    def get_file_hash(self, contents):
        hasher = hashlib.md5()
        hasher.update(contents)
        return hasher.hexdigest()

    def extract_text_from_pdf(self, contents):
        try:
            pdf_file = BytesIO(contents)
            reader = PyPDF2.PdfReader(pdf_file)
            text = ""
            for page in reader.pages:
                text += page.extract_text()
            return text
        except Exception as e:
            logging.error(f"Error extracting text from PDF: {str(e)}")
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

pdf_processor = PDFProcessor(os.getenv("API_KEY"), os.getenv("API_ENDPOINT"))

@app.post("/process-pdf")
async def process_pdf(file: UploadFile = File(...)):
    if file.filename.endswith('.pdf'):
        return await pdf_processor.process_pdf(file)
    else:
        return JSONResponse(content={"message": "Only PDF files are allowed"}, status_code=400)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)