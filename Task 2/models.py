from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

class ChatRequest(BaseModel):
    session_id: str
    channel: str
    message: str

class ChatResponse(BaseModel):
    reply: str
    language_detected: str
    fields_collected: Dict[str, Any]
    complete: bool

class LeadFields(BaseModel):
    company_name: Optional[str] = None
    contact_name: Optional[str] = None
    product_category: Optional[str] = None
    target_quantity: Optional[str] = None
    timeline: Optional[str] = None
    brand_goals: Optional[str] = None

class SessionState(BaseModel):
    session_id: str
    language: str = "english"
    history: List[Dict[str, str]] = Field(default_factory=list)
    fields: LeadFields = Field(default_factory=LeadFields)
    complete: bool = False
