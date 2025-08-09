import logging
from fastapi import HTTPException

from linebot.v3.webhook import WebhookParser
from linebot.v3.messaging import (
    MessagingApi, MessagingApiBlob, TextMessage,
    Configuration, ApiClient, PushMessageRequest
)
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.webhooks import MessageEvent, ImageMessageContent

from app.config import settings
from app.gcp_services import gcp_service

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

configuration = Configuration(
    access_token=settings.LINE_CHANNEL_ACCESS_TOKEN
)
api_client = ApiClient(configuration)
line_bot_api = MessagingApi(api_client)
line_bot_blob_api = MessagingApiBlob(api_client)

parser = WebhookParser(channel_secret=settings.LINE_CHANNEL_SECRET)

def handle_line_webhook(signature: str, body: bytes):
    events = parser.parse(body.decode(), signature)
    for event in events:
        if isinstance(event, MessageEvent) and isinstance(event.message, ImageMessageContent):
            handle_image_message(event)
    return 'OK'

def handle_image_message(event: MessageEvent):
    if not hasattr(event.source, 'user_id'):
        return
    user_id = event.source.user_id
    message_id = event.message.id
    image_bytes = line_bot_blob_api.get_message_content(message_id)
    slip_data = gcp_service.extract_data_from_image(image_bytes)
    if not any(slip_data.model_dump().values()):
        push_request = PushMessageRequest(
            to=user_id,
            messages=[TextMessage(text="ไม่สามารถประมวลผลรูปภาพได้ กรุณาตรวจสอบว่าเป็นสลิปโอนเงินที่ชัดเจนหรือไม่ แล้วลองใหม่อีกครั้งครับ")]
        )
        line_bot_api.push_message(push_request)
        return
    gcp_service.append_to_sheet(slip_data)
    sheet_url = f"https://docs.google.com/spreadsheets/d/{settings.GOOGLE_SHEET_ID}/edit"
    reply_message_text = (
        f"บันทึกข้อมูลสลิปเรียบร้อยแล้วครับ ✨\n\n"
        f"🗓️ วันที่-เวลา: {slip_data.date or '-'}\n"
        f"👤 จากบัญชี: {slip_data.from_account or '-'}\n"
        f"🏦 ธนาคาร: {slip_data.bank or '-'}\n"
        f"➡️ ผู้รับ: {slip_data.recipient or '-'}\n"
        f"💰 จำนวนเงิน: {f'{slip_data.amount:,.2f}' if slip_data.amount is not None else '0.00'} บาท\n"
        f"📝 บันทึกช่วยจำ: {slip_data.memo or '-'}\n\n"
        f"📄 ดูข้อมูลทั้งหมดใน Sheet:\n{sheet_url}"
    )
    success_push_request = PushMessageRequest(
        to=user_id,
        messages=[TextMessage(text=reply_message_text)]
    )
    line_bot_api.push_message(success_push_request)