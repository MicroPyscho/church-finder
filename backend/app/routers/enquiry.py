"""
Enquiry router — AI-powered enquiry generation using Groq.
"""
import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.services.groq_client import generate_enquiry

router = APIRouter(prefix="/api/enquiry", tags=["enquiry"])
logger = logging.getLogger(__name__)

class EnquiryRequest(BaseModel):
    property_id:      str
    property_data:    dict
    user_intent:      dict | None = None
    user_description: str  | None = None

class EnquiryResponse(BaseModel):
    subject: str
    body:    str
    to:      str | None = None

@router.post("/draft", response_model=EnquiryResponse)
async def draft_enquiry(req: EnquiryRequest):
    if not req.property_data:
        raise HTTPException(status_code=400, detail="Property data required")
    raw = await generate_enquiry(
        property_data=req.property_data,
        user_intent=req.user_intent,
        user_description=req.user_description,
    )
    if not raw:
        raise HTTPException(status_code=503, detail="AI service unavailable")

    subject = "Enquiry regarding church property"
    body = raw
    for i, line in enumerate(raw.strip().split("\n")):
        if line.lower().startswith("subject:"):
            subject = line.split(":", 1)[1].strip()
            body = "\n".join(raw.strip().split("\n")[i + 1:]).strip()
            break

    source_url = req.property_data.get("url", "")
    to_email = None
    if "alex-martin" in source_url:
        to_email = "info@alex-martin.co.uk"
    elif "sw.co.uk" in source_url:
        to_email = "info@sw.co.uk"

    return EnquiryResponse(subject=subject, body=body, to=to_email)

@router.post("/send")
async def send_enquiry(req: EnquiryRequest):
    draft = await draft_enquiry(req)
    return {"status": "drafted", "message": "Email drafted. SMTP sending not yet configured.", "draft": draft}
