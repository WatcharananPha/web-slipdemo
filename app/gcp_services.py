import json
import io
import logging
from PIL import Image
import google.generativeai as genai
import gspread
from google.oauth2.service_account import Credentials
from pydantic import ValidationError

from app.config import settings
from app.models import SlipData

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GoogleCloudService:
    def __init__(self):
        genai.configure(api_key=settings.GOOGLE_API_KEY)
        self.model = genai.GenerativeModel('gemini-2.5-pro')
        self._load_prompt()
        self.service_account_info = json.loads(settings.GOOGLE_SERVICE_ACCOUNT_JSON_STR)
        self.scopes = ["https://www.googleapis.com/auth/spreadsheets"]
        self.creds = Credentials.from_service_account_info(self.service_account_info, scopes=self.scopes)
        self.gspread_client = None

    def _load_prompt(self):
        with open(settings.PROMPT_FILE_PATH, "r", encoding="utf-8") as f:
            self.prompt = f.read()

    def _get_gspread_client(self) -> gspread.Client:
        if self.gspread_client and self.gspread_client.session.authorized:
            return self.gspread_client
        client = gspread.authorize(self.creds)
        self.gspread_client = client
        return client

    def extract_data_from_image(self, image_bytes: bytes) -> SlipData:
        image = Image.open(io.BytesIO(image_bytes))
        response = self.model.generate_content([self.prompt, image])
        cleaned_text = response.text.strip().replace("```json", "").replace("```", "")
        try:
            extracted_data = json.loads(cleaned_text)
            validated_data = SlipData(**extracted_data)
            return validated_data
        except (json.JSONDecodeError, ValidationError):
            return SlipData()

    def append_to_sheet(self, data: SlipData):
        sheet_data = [
            data.date, data.from_account, data.bank,
            data.recipient, data.amount, data.memo
        ]
        client = self._get_gspread_client()
        worksheet = client.open_by_key(settings.GOOGLE_SHEET_ID).sheet1
        worksheet.append_row(sheet_data, value_input_option='USER_ENTERED')

gcp_service = GoogleCloudService()