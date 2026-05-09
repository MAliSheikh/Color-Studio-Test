from fastapi import FastAPI, HTTPException
from contextlib import asynccontextmanager

from .models import ChatRequest, ChatResponse, LeadFields
from .database import init_db, get_session, save_session
from .agent import process_message_with_agent

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize SQLite DB on startup
    init_db()
    yield
    # Cleanup on shutdown

app = FastAPI(title="AI Customer Intake Agent", lifespan=lifespan)

@app.post("/chat", response_model=ChatResponse)
def chat_endpoint(request: ChatRequest):
    # 1. Retrieve session state from DB
    state = get_session(request.session_id)
    
    # 2. Call LLM Agent
    llm_response = process_message_with_agent(request.message, state)
    
    # 3. Update State
    reply = llm_response.get("reply", "Sorry, I missed that.")
    state.language = llm_response.get("language", state.language)
    
    extracted = llm_response.get("extracted_fields", {})
    state.fields = LeadFields(**extracted)
    
    # Update history
    state.history.append({"role": "user", "content": request.message})
    state.history.append({"role": "assistant", "content": reply})
    
    # Check if complete (all fields are filled)
    fields_dict = state.fields.model_dump()
    state.complete = all(v is not None for v in fields_dict.values())
    
    # 4. Save to DB
    save_session(state)
    
    return ChatResponse(
        reply=reply,
        language_detected=state.language,
        fields_collected=fields_dict,
        complete=state.complete
    )

@app.get("/lead/{session_id}")
def get_lead(session_id: str):
    state = get_session(session_id)
    
    if not state.history:
        raise HTTPException(status_code=404, detail="Session not found")
        
    if not state.complete:
        return {
            "status": "incomplete",
            "message": "Lead intake is not yet complete.",
            "current_fields": state.fields.model_dump()
        }
        
    return {
        "status": "complete",
        "lead_summary": state.fields.model_dump()
    }
