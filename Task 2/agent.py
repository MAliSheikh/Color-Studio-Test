import os
import json
import chromadb
from openai import OpenAI
from dotenv import load_dotenv, find_dotenv
from .models import SessionState, LeadFields

# Load environment variables
load_dotenv(find_dotenv(usecwd=True))

client = OpenAI(
    api_key=os.environ.get("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1",
)

# Connect to the Vector Knowledge Base from Task 1B
# We resolve the path relative to this file to point to Task 1B's chroma_db
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
chroma_path = os.path.join(root_dir, "Task 1", "task_1b_vector_knowledge_base", "chroma_db")

try:
    chroma_client = chromadb.PersistentClient(path=chroma_path)
    # The collection name from Task 1B is usually "cosmetics_knowledge"
    collection = chroma_client.get_collection("cosmetics_knowledge")
except Exception as e:
    print(f"Warning: Could not load ChromaDB: {e}")
    collection = None

def get_knowledge_context(message: str) -> str:
    """Queries the vector DB for context if it exists."""
    if not collection:
        return ""
    try:
        results = collection.query(
            query_texts=[message],
            n_results=2
        )
        if results and results['documents'] and results['documents'][0]:
            return "\n- ".join(results['documents'][0])
    except Exception:
        pass
    return ""

def process_message_with_agent(message: str, state: SessionState) -> dict:
    """
    Calls the LLM with the conversation history and user message.
    Expects a JSON response from the LLM.
    """
    
    # Get relevant facts from vector DB
    knowledge_context = get_knowledge_context(message)
    context_injection = f"\nRelevant Knowledge Base Facts:\n{knowledge_context}\n" if knowledge_context else ""

    system_prompt = f"""You are a bilingual AI customer intake agent for a cosmetics manufacturer.
You communicate via WhatsApp/Instagram.

YOUR GOALS:
1. Identify if the user is speaking English or Urdu (including Roman Urdu), and always reply in the exact same language/script.
2. Qualify the lead by naturally collecting these 6 fields over the conversation:
   - Company Name
   - Contact Name
   - Product Category of interest
   - Target Quantity (MOQ)
   - Timeline
   - Brand Goals
3. Answer questions about packaging or MOQ using ONLY the "Relevant Knowledge Base Facts" provided below. Do not hallucinate outside info.
4. Once all 6 fields are collected, thank them and let them know an executive will reach out to book a meeting.

{context_injection}

CURRENT STATE:
Here is what you have already collected:
{state.fields.model_dump_json(indent=2)}

INSTRUCTIONS FOR OUTPUT:
You must output a raw JSON object and nothing else.
Format:
{{
  "reply": "Your friendly conversational reply here",
  "language": "english" or "urdu",
  "extracted_fields": {{
    "company_name": "Extracted name or null",
    "contact_name": "Extracted name or null",
    "product_category": "Extracted category or null",
    "target_quantity": "Extracted quantity or null",
    "timeline": "Extracted timeline or null",
    "brand_goals": "Extracted goals or null"
  }}
}}
Note: For extracted_fields, merge what you already know from the CURRENT STATE with any new information found in the latest message.
"""

    messages = [{"role": "system", "content": system_prompt}]
    
    # Append history
    for msg in state.history:
        messages.append(msg)
        
    messages.append({"role": "user", "content": message})

    try:
        response = client.chat.completions.create(
            messages=messages,
            model="llama-3.3-70b-versatile",
            temperature=0.1,
            response_format={"type": "json_object"}
        )
        
        result_text = response.choices[0].message.content
        result_json = json.loads(result_text)
        return result_json
        
    except Exception as e:
        print(f"LLM Error: {e}")
        return {
            "reply": "I am experiencing technical difficulties. Please try again later.",
            "language": state.language,
            "extracted_fields": state.fields.model_dump()
        }
