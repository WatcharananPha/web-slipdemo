from pydantic import BaseModel, Field
from typing import Optional

class SlipData(BaseModel):
    date: Optional[str] = Field(None, description="Transaction date in YYYY-MM-DD HH:MM format")
    from_account: Optional[str] = Field(None, description="Sender's name or account number")
    bank: Optional[str] = Field(None, description="Sender's bank name (e.g., K-Bank, SCB)")
    recipient: Optional[str] = Field(None, description="Recipient's full name")
    amount: Optional[float] = Field(None, description="Transaction amount as a numeric value")
    memo: Optional[str] = Field(None, description="Transaction memo or note")

class ApiResponse(BaseModel):
    extracted_data: SlipData