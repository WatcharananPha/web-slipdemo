import os
from pydantic_settings import BaseSettings
from pydantic import Field
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env")

class Settings(BaseSettings):
    GOOGLE_API_KEY: str = Field(..., env="GOOGLE_API_KEY")
    GOOGLE_SHEET_ID: str = Field(..., env="GOOGLE_SHEET_ID")
    GOOGLE_SERVICE_ACCOUNT_JSON_STR: str = Field(..., env="GOOGLE_SERVICE_ACCOUNT_JSON_STR")
    PROMPT_FILE_PATH: str = Field(str(BASE_DIR / "prompts" / "slip_ocr_prompt.txt"))
    LINE_CHANNEL_ACCESS_TOKEN: str = Field(..., env="LINE_CHANNEL_ACCESS_TOKEN")
    LINE_CHANNEL_SECRET: str = Field(..., env="LINE_CHANNEL_SECRET")

    class Config:
        env_file = ".env"
        env_file_encoding = 'utf-8'
        extra = 'ignore'

settings = Settings()