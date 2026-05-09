import os
import pandas as pd
import chromadb
from chromadb.utils import embedding_functions
from openai import OpenAI
from dotenv import load_dotenv, find_dotenv

# Load environment variables automatically by searching up the directory tree
load_dotenv(find_dotenv(usecwd=True))

# Initialize Groq client using OpenAI SDK
# The user specified using groq with openai library
client = OpenAI(
    api_key=os.environ.get("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1",
)

def chunk_data(csv_path):
    """
    Reads the CSV and chunks the data.
    
    Chunking Strategy:
    Since this dataset consists of discrete configurations (products, packaging, MOQs, etc.), 
    character-based or token-based splitting would arbitrarily cut off related facts 
    (e.g., separating the MOQ from the Lead Time of the same product).
    Therefore, we use 'row-level chunking' where each row is converted into a 
    comprehensive natural language sentence or paragraph. This ensures that the 
    embeddings capture the full context of a single configuration in one chunk.
    """
    df = pd.read_csv(csv_path)
    chunks = []
    metadata = []
    ids = []
    
    for index, row in df.iterrows():
        # Create a descriptive chunk for the embedding model
        chunk_text = (
            f"Product Category: {row['Product Category']}. "
            f"Example Product: {row['Product Name Example']}. "
            f"Packaging Option: {row['Packaging Option']}. "
            f"The Minimum Order Quantity (MOQ) is {row['MOQ (Units)']} units. "
            f"The lead time is {row['Lead Time (Weeks)']} weeks. "
            f"Formulation Capabilities include: {row['Formulation Capabilities']}."
        )
        chunks.append(chunk_text)
        
        # Store structured data as metadata for filtering or exact retrieval if needed
        metadata.append({
            "category": row['Product Category'],
            "packaging": row['Packaging Option'],
            "moq": int(row['MOQ (Units)']),
            "lead_time": int(row['Lead Time (Weeks)'])
        })
        ids.append(f"chunk_{index}")
        
    return chunks, metadata, ids

def setup_vector_store(chunks, metadata, ids, persist_directory=None):
    if persist_directory is None:
        persist_directory = os.path.join(os.path.dirname(os.path.abspath(__file__)), "chroma_db")
    """
    Initializes Chroma vector store and adds chunks.
    Uses the default all-MiniLM-L6-v2 embedding function under the hood, 
    which is an open-source local embedding model perfect for this use case.
    """
    print("Setting up vector store...")
    chroma_client = chromadb.PersistentClient(path=persist_directory)
    
    # Use default sentence-transformers model (open source)
    sentence_transformer_ef = embedding_functions.DefaultEmbeddingFunction()
    
    # Get or create collection
    collection = chroma_client.get_or_create_collection(
        name="cosmetics_knowledge_base",
        embedding_function=sentence_transformer_ef
    )
    
    # If the collection is empty, populate it
    if collection.count() == 0:
        print(f"Adding {len(chunks)} chunks to the knowledge base...")
        collection.add(
            documents=chunks,
            metadatas=metadata,
            ids=ids
        )
    else:
        print(f"Knowledge base already contains {collection.count()} items. Using existing store.")
        
    return collection

def query_knowledge_base(collection, question, top_k=3):
    """
    Queries the vector store for the top K most relevant chunks.
    """
    results = collection.query(
        query_texts=[question],
        n_results=top_k
    )
    return results['documents'][0]

def generate_answer_with_groq(question, retrieved_chunks):
    """
    Uses Groq (via OpenAI SDK) to generate a conversational answer based on the chunks.
    """
    context = "\n- ".join(retrieved_chunks)
    system_prompt = """You are a professional and helpful customer support AI for a cosmetics manufacturing company.
Your primary role is to answer client questions about packaging options, Minimum Order Quantities (MOQs), lead times, and formulation capabilities.

STRICT GUARDRAILS:
1. GROUNDING: ONLY use the information provided in the Context below. Do not use outside knowledge.
2. UNKNOWN INFO: If the user asks a question that is NOT covered by the Context, you MUST politely state that you do not have that information. Do not hallucinate, guess, or make up numbers.
3. NO COMMITMENTS: Do not provide medical advice, formulation safety guarantees, or legally binding commitments (e.g., "we guarantee delivery in exactly 6 weeks").
4. SCOPE: If the user asks about topics completely unrelated to cosmetics manufacturing, packaging, or the provided context, politely refuse to answer.
5. TONE: Keep your answers concise, professional, and easily scannable."""

    user_prompt = f"""Context Information:
{context}

User Question: {question}
"""
    
    try:
        response = client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": system_prompt,
                },
                {
                    "role": "user",
                    "content": user_prompt,
                }
            ],
            # Upgraded to a smarter model with a massive context window for better reasoning
            model="llama-3.3-70b-versatile",
            temperature=0.0, # Set to 0.0 for maximum determinism/grounding
            max_tokens=512
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error connecting to Groq API: {e}"

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    csv_path = os.path.join(script_dir, "data.csv")
    if not os.path.exists(csv_path):
        print(f"Error: {csv_path} not found. Please ensure the CSV is present.")
        return

    # 1 & 2. Read and chunk data
    chunks, metadata, ids = chunk_data(csv_path)
    
    # 3 & 4. Setup vector store and store embeddings
    collection = setup_vector_store(chunks, metadata, ids)
    
    print("\n--- Cosmetics Knowledge Base CLI ---")
    print("Type your question below (or 'exit' to quit).")
    
    while True:
        question = input("\nQuestion: ")
        if question.lower() in ['exit', 'quit']:
            break
            
        if not question.strip():
            continue
            
        print("\nSearching...")
        # 5. Query top 3 chunks
        top_chunks = query_knowledge_base(collection, question, top_k=3)
        
        # print("\n--- Top 3 Retrieved Chunks ---")
        # for i, chunk in enumerate(top_chunks, 1):
        #     print(f"{i}. {chunk}")
            
        print("\n--- AI Agent Answer ---")
        answer = generate_answer_with_groq(question, top_chunks)
        print(answer)
        print("-" * 50)

if __name__ == "__main__":
    main()
