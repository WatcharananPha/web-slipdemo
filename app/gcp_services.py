import json
import io
import logging
from PIL import Image
import google.generativeai as genai
import gspread
from google.oauth2.service_account import Credentials
from pydantic import ValidationError
from functools import lru_cache

from app.config import settings
from app.models import SlipData

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@lru_cache(maxsize=1)
def get_gspread_client() -> gspread.Client:
    service_account_info = json.loads(settings.GOOGLE_SERVICE_ACCOUNT_JSON_STR)
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = Credentials.from_service_account_info(service_account_info, scopes=scopes)
    client = gspread.authorize(creds)
    return client

@lru_cache(maxsize=1)
def get_gemini_model():
    genai.configure(api_key=settings.GOOGLE_API_KEY)
    model = genai.GenerativeModel('gemini-2.5-pro')
    return model

@lru_cache(maxsize=1)
def get_ocr_prompt() -> str:
    with open(settings.PROMPT_FILE_PATH, "r", encoding="utf-8") as f:
        return f.read()

def extract_data_from_image(image_bytes: bytes, model, prompt: str) -> SlipData:
    image = Image.open(io.BytesIO(image_bytes))
    response = model.generate_content([prompt, image])
    cleaned_text = response.text.strip().replace("```json", "").replace("```", "")
    try:
        extracted_data = json.loads(cleaned_text)
        validated_data = SlipData(**extracted_data)
        return validated_data
    except (json.JSONDecodeError, ValidationError):
        return SlipData()

def append_to_sheet(data: SlipData, client: gspread.Client):
    sheet_data = [
        data.date, data.from_account, data.bank,
        data.recipient, data.amount, data.memo
    ]
    worksheet = client.open_by_key(settings.GOOGLE_SHEET_ID).sheet1
    worksheet.append_row(sheet_data, value_input_option='USER_ENTERED')