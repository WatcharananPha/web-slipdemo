import logging
from fastapi import FastAPI, Request, HTTPException, status, Depends
import gspread
from linebot.v3.webhook import WebhookParser
from linebot.v3.messaging import (
    MessagingApi,
    MessagingApiBlob,
    TextMessage,
    Configuration,
    ApiClient,
    PushMessageRequest,
)
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.webhooks import MessageEvent, ImageMessageContent
from app.config import settings
from app.models import SlipData
from app.gcp_services import (
    get_gspread_client,
    get_gemini_model,
    get_ocr_prompt,
    extract_data_from_image,
    append_to_sheet,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="LINE Slip Reader API (Production Grade)",
    description="A stateless, robust API to process slips, deployed on Azure.",
    version="3.0.0",
)


def get_line_api_client() -> ApiClient:
    configuration = Configuration(access_token=settings.LINE_CHANNEL_ACCESS_TOKEN)
    return ApiClient(configuration)


def get_line_bot_api(
    api_client: ApiClient = Depends(get_line_api_client),
) -> MessagingApi:
    return MessagingApi(api_client)


def get_line_bot_blob_api(
    api_client: ApiClient = Depends(get_line_api_client),
) -> MessagingApiBlob:
    return MessagingApiBlob(api_client)


def get_parser() -> WebhookParser:
    return WebhookParser(channel_secret=settings.LINE_CHANNEL_SECRET)


@app.post("/line/webhook", status_code=status.HTTP_200_OK)
async def webhook(
    request: Request,
    parser: WebhookParser = Depends(get_parser),
    line_bot_api: MessagingApi = Depends(get_line_bot_api),
    line_bot_blob_api: MessagingApiBlob = Depends(get_line_bot_blob_api),
    gspread_client: gspread.Client = Depends(get_gspread_client),
    gemini_model=Depends(get_gemini_model),
    ocr_prompt: str = Depends(get_ocr_prompt),
):
    signature = request.headers.get("X-Line-Signature")
    body = await request.body()
    events = parser.parse(body.decode(), signature)
    for event in events:
        if isinstance(event, MessageEvent) and isinstance(
            event.message, ImageMessageContent
        ):
            user_id = event.source.user_id
            message_id = event.message.id
            image_bytes = line_bot_blob_api.get_message_content(message_id)
            slip_data = extract_data_from_image(image_bytes, gemini_model, ocr_prompt)
            if not any(slip_data.model_dump().values()):
                line_bot_api.push_message(
                    PushMessageRequest(
                        to=user_id,
                        messages=[
                            TextMessage(
                                text="ไม่สามารถประมวลผลรูปภาพได้ กรุณาตรวจสอบว่าเป็นสลิปโอนเงินที่ชัดเจนหรือไม่ แล้วลองใหม่อีกครั้งครับ"
                            )
                        ],
                    )
                )
                return "OK"
            append_to_sheet(slip_data, gspread_client)
            sheet_url = f"https://docs.google.com/spreadsheets/d/{settings.GOOGLE_SHEET_ID}/edit"
            reply_text = (
                f"บันทึกข้อมูลสลิปเรียบร้อยแล้วครับ ✨\n\n"
                f"🗓️ วันที่-เวลา: {slip_data.date or '-'}\n"
                f"👤 จากบัญชี: {slip_data.from_account or '-'}\n"
                f"🏦 ธนาคาร: {slip_data.bank or '-'}\n"
                f"➡️ ผู้รับ: {slip_data.recipient or '-'}\n"
                f"💰 จำนวนเงิน: {f'{slip_data.amount:,.2f}' if slip_data.amount is not None else '0.00'} บาท\n"
                f"📝 บันทึกช่วยจำ: {slip_data.memo or '-'}\n\n"
                f"📄 ดูข้อมูลทั้งหมดใน Sheet:\n{sheet_url}"
            )
            line_bot_api.push_message(
                PushMessageRequest(to=user_id, messages=[TextMessage(text=reply_text)])
            )
    return "OK"


@app.get("/health", status_code=status.HTTP_200_OK)
def health_check():
    return {"status": "healthy"}
