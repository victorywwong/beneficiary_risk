from pydantic import BaseModel
from datetime import datetime


class Sender(BaseModel):
    name: str
    account_id: str
    bank: str


class Recipient(BaseModel):
    name: str
    account_id: str
    bank: str


class Payment(BaseModel):
    payment_id: str
    sender: Sender
    recipient: Recipient
    amount: float
    currency: str
    reference: str
    timestamp: datetime
