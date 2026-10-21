from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from google import genai
import chromadb
import os
from dotenv import load_dotenv

# --- SETUP & CONNECTIONS ---
load_dotenv()

# 1. Connect to Gemini (Make sure to spell it GEMINI, not GIMINI)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
ai_client = genai.Client(api_key=GEMINI_API_KEY)

# 2. Connect to ChromaDB
chroma_client = chromadb.PersistentClient(path="./chroma_db")
# get_collection loads the data you already ingested, without deleting it!
collection = chroma_client.get_collection(name="book_collection")

# 3. Initialize FastAPI App
app = FastAPI(title="Chat with PDF API")

# --- DATA MODELS ---
class ChatRequest(BaseModel):
    question: str

class ChatResponse(BaseModel):
    answer: str
    sources: list[str]

# --- ENDPOINTS ---
@app.post("/chat", response_model=ChatResponse)
def chat_with_pdf(request: ChatRequest):
    
    # Step 1: Embed the user's question
    try:
        query_embedding_response = ai_client.models.embed_content(
            model="gemini-embedding-001",
            contents=[request.question],
        )
        query_embedding = query_embedding_response.embeddings[0].values
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Embedding failed: {e}")

    # Step 2: Search ChromaDB for the 3 most relevant chunks
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=3
    )
    
    retrieved_chunks = results['documents'][0]
    
    # Step 3: Build the Prompt
    context_text = "\n\n---\n\n".join(retrieved_chunks)
    
    prompt = f"""
    You are a helpful assistant. Use ONLY the following context to answer the user's question.
    If the answer is not in the context, say "I don't know based on the provided document."
    
    CONTEXT:
    {context_text}
    
    QUESTION:
    {request.question}
    """

    # Step 4: Generate the final answer using Gemini
    try:
        response = ai_client.models.generate_content(
            model="gemini-3.5-flash-lite",
            contents=prompt,
        )
        final_answer = response.text
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Generation failed: {e}")

    # Step 5: Return the answer and the chunks it used
    return ChatResponse(
        answer=final_answer,
        sources=retrieved_chunks
    )

@app.get("/health")
def health():
    return {"status": "ok"}