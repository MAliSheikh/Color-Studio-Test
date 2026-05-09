# Task 2: AI Customer Intake Agent (Bilingual)

This is a FastAPI application that simulates an AI customer intake agent capable of automatically qualifying leads through a simulated WhatsApp/Instagram channel.

## Design Choices & Architecture

### State Management: SQLite
We chose **SQLite** for maintaining conversational state (storing history and extracted fields per `session_id`) rather than a simple in-memory dictionary. 
- **Why SQLite?** While an in-memory dictionary is faster to set up, all conversation history would be wiped out the moment the FastAPI server restarts or crashes. Using SQLite ensures the conversation state persists across restarts. It also mimics a production-ready approach where sessions would be stored in a real relational database (like PostgreSQL) or Redis, making it easier to scale.

### Bilingual Support (Prompt-Based NLP)
We did not use any external translation APIs or heavy Python NLP language-detection packages. 
- **Why?** Modern LLMs (like `llama-3.3-70b-versatile`) are extremely proficient at natively understanding and generating multiple languages (including Roman Urdu and script Urdu). We configured the System Prompt to strictly instruct the agent to identify the user's language/script on the fly and mirror it naturally. This reduces latency, drops unnecessary dependencies, and makes the conversation flow much more naturally.

### Vector Knowledge Base Integration
The agent imports the ChromaDB client and resolves the path up to `Task 1/task_1b_vector_knowledge_base/chroma_db`. When a user sends a message, a quick semantic search is performed. If relevant MOQ/Packaging facts are found, they are injected into the LLM's system prompt to ground the AI in reality and prevent hallucinations.

### Dynamic File Structure
The code is strictly separated into logical modules (`main.py`, `agent.py`, `database.py`, `models.py`) to simulate a clean microservice pattern, rather than stuffing everything into a single monolithic file.

---

## Example `curl` Conversations

### English Flow

1. **Initial Message**
```bash
curl -X POST http://127.0.0.1:8000/chat \
-H "Content-Type: application/json" \
-d '{"session_id": "eng-123", "channel": "whatsapp", "message": "Hi, I am looking to start a new skincare brand."}'
```

2. **Providing Fields**
```bash
curl -X 'POST' \
  'http://127.0.0.1:8000/chat' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
  "session_id": "a1",
  "channel": "whatsapp",
  "message": "My name is John from GlowCare. We want to make a Vitamin C serum, probably around 5000 units. We need it in 8 weeks."
}'
```

3. **Check Lead Status**
```bash
curl -X GET http://127.0.0.1:8000/lead/a1
```

---

### Urdu Flow

1. **Initial Message**
```bash
curl -X 'POST' \
  'http://127.0.0.1:8000/chat' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
  "session_id": "a2",
  "channel": "whatsapp",
  "message": "Asalam o alaikum, mujhe ek naya makeup brand shuru karna hai."
}'
```

2. **Providing Fields**
```bash
curl -X 'POST' \
  'http://127.0.0.1:8000/chat' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
  "session_id": "a2",
  "channel": "whatsapp",
  "message": "Mera naam Ali hai, meri company AliCosmetics hai. Hamein lipstick banwani hai, taqreeban 10,000 piece. Hamara goal market me high quality sasti lipstick lana hai aur 12 weeks me launch karna hai."
}'
```

3. **Check Lead Status**
```bash
curl -X GET http://127.0.0.1:8000/lead/urdu-456
```

4. **Initial Message**
```bash
curl -X 'POST' \
  'http://127.0.0.1:8000/chat' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
  "session_id": "a3",
  "channel": "whatsapp",
  "message": "میرا نام علی ہے، میری کمپنی AliCosmetics ہے۔ ہمیں لپ اسٹک بنوانی ہے، تقریباً 10,000 پیس۔ ہمارا مقصد مارکیٹ میں اعلیٰ معیار کی سستی لپ اسٹک لانا ہے اور اسے 12 ہفتوں میں لانچ کرنا ہے۔"
}'

