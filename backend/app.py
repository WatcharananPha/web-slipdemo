import json
from datetime import datetime
import os
import io
import binascii
from dotenv import load_dotenv
import base64
from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
import google.generativeai as genai
from PIL import Image
from google.oauth2.service_account import Credentials
import gspread

load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    raise ValueError("GOOGLE_API_KEY is not set in the environment variables.")
genai.configure(api_key=api_key)

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
CREDS_JSON_ENV = os.getenv("CREDS_JSON_ENV")
DEFAULT_SHEET_ID = "1wXIirCxkOYl2X4-B6-Q3UOj7WPKBrQub_Yrg0APnh04"

app = FastAPI(title="Slip Data Extractor API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

model = genai.GenerativeModel('gemini-2.5-pro')

prompt = """
You are an expert OCR data extraction system for financial documents.
Your task is to meticulously analyze the provided image of a Thai money transfer slip and extract key information.

### CRITICAL DIRECTIVES: ANTI-HALLUCINATION & DATA SOURCE RULES
- **STRICTLY USE THE PROVIDED IMAGE ONLY:** You MUST extract information *exclusively* from the uploaded image. Do not use any external knowledge, training data examples, or general information. Your entire response must be based SOLELY on the visual data in the input.
- **NO GUESSING OR FABRICATION:** Do not invent, create, or guess any information that is not explicitly written on the slip. If a piece of data is blurry, ambiguous, or not present, you MUST use `null` for that field as per the rules below.
- **VALIDATE DOCUMENT TYPE:** If the provided image is clearly NOT a money transfer slip (e.g., it's a picture of a landscape, an invoice, or a random photo), you MUST return a JSON object where all values are `null`. For example: `{"date": null, "transaction_id": null, "bank": null, "recipient": null, "amount": null}`.
- **YOUR PRIMARY GOAL IS ACCURACY:** It is better to return `null` for a field than to return incorrect or hallucinated information.

Return the data ONLY in a valid, raw JSON object format. Do not include any explanatory text, markdown formatting like ```json, or anything outside of the JSON structure itself.

The required JSON schema is as follows, designed to match the Google Sheet columns:
{
  "date": "The transaction date and time in YYYY-MM-DD HH:MM format",
  "transaction_id": "The transaction reference number or ID",
  "bank": "The name of the bank (e.g., K-Bank, SCB, Krungthai, TTB)",
  "recipient": "The full name of the recipient",
  "amount": 0.00
}

**Crucial Rules:**
1.  **Data Types:** The `amount` field MUST be a numeric type (float or integer), not a string.
2.  **Date and Year Conversion:** You MUST convert the Thai Buddhist year (e.g., 2568, 68) to the corresponding Gregorian year (e.g., 2025). The final `date` field must be in YYYY-MM-DD HH:MM format.
3.  **Missing Information:** If any piece of information cannot be found or is not present on the slip, use `null` as the value for that field. Do not omit the key.
"""

def get_gspread_creds():
    if os.path.isfile(CREDS_JSON_ENV):
        return Credentials.from_service_account_file(CREDS_JSON_ENV, scopes=SCOPES)
    
    current_dir = os.path.dirname(os.path.abspath(__file__))
    file_name = os.path.basename(CREDS_JSON_ENV)
    local_path = os.path.join(current_dir, file_name)
    if os.path.isfile(local_path):
        return Credentials.from_service_account_file(local_path, scopes=SCOPES)
    
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    relative_path = os.path.join(project_root, CREDS_JSON_ENV)
    if os.path.isfile(relative_path):
        return Credentials.from_service_account_file(relative_path, scopes=SCOPES)
    
    env = CREDS_JSON_ENV
    pad = len(env) % 4
    if pad:
        env += '=' * (4 - pad)
    creds_json = base64.b64decode(env).decode('utf-8')
    creds_info = json.loads(creds_json)
    return Credentials.from_service_account_info(creds_info, scopes=SCOPES)

def append_to_sheet(data):
    creds = get_gspread_creds()
    client = gspread.authorize(creds)
    worksheet = client.open_by_key(DEFAULT_SHEET_ID).get_worksheet(0)
    values = [
        data.get("date"),
        data.get("transaction_id"),
        data.get("bank"),
        data.get("recipient"),
        data.get("amount")
    ]
    worksheet.append_row(values, value_input_option='RAW')

@app.post("/api/upload")
async def upload_and_extract_data(file: UploadFile = File(...)):
    image_bytes = await file.read()
    image = Image.open(io.BytesIO(image_bytes))
    response = model.generate_content([prompt, image])
    cleaned = response.text.strip().replace("```json", "").replace("```", "")
    extracted = json.loads(cleaned)
    dt = extracted.get("date")
    if dt:
        extracted["date"] = datetime.strptime(dt, "%Y-%m-%d %H:%M").isoformat()
    append_to_sheet(extracted)
    return {"extracted_data": extracted}

@app.get("/")
async def read_root():
    return {"status": "OK", "message": "Slip Reader API is running"}