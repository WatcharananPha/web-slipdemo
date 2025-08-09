import logging
from fastapi import FastAPI, Request, HTTPException, status
from app.line_handler import handle_line_webhook

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="LINE Slip Reader API",
    description="An API to process Thai bank transfer slips via LINE and save data to Google Sheets. Deployed on Azure.",
    version="2.0.0"
)

@app.post("/line/webhook", status_code=status.HTTP_200_OK)
async def webhook(request: Request):
    signature = request.headers.get('X-Line-Signature')
    if not signature:
        raise HTTPException(status_code=400, detail="X-Line-Signature header is missing.")
    body = await request.body()
    handle_line_webhook(signature=signature, body=body)
    return 'OK'

@app.get("/health", status_code=status.HTTP_200_OK)
def health_check():
    return {"status": "healthy"}

@app.get("/", status_code=status.HTTP_200_OK)
def read_root():
    return {"status": "OK", "message": "Welcome to the LINE Slip Reader API!"}