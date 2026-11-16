from fastapi import FastAPI, HTTPException, Depends, UploadFile, File 
from pydantic import BaseModel
from google import genai
import chromadb
import os
import time
from dotenv import load_dotenv
from flashrank import Ranker, RerankRequest
from sqlalchemy import create_engine, Column, String, Integer
from sqlalchemy.orm import declarative_base, sessionmaker, Session
import uuid
import io
from pypdf import PdfReader
from sentence_transformers import SentenceTransformer
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import json


load_dotenv()


GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
ai_client = genai.Client(api_key=GEMINI_API_KEY)
embedding_model = SentenceTransformer('all-MiniLM-L6-v2')

# SQL Databse
SQLALCHEMY_DATABASE_URL = "sqlite:///./chat_session.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class ChatsessionDB(Base):
    __tablename__ = "chats"
    id = Column(String, primary_key=True, index=True)
    title = Column(String)

class MessageDB(Base):
    __tablename__ = "messages"
    id = Column(Integer, primary_key=True, index=True)
    chat_id = Column(String, index=True)
    role= Column(String)
    content= Column(String)

Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 2. Connect to ChromaDB
chroma_client = chromadb.PersistentClient(path="./chroma_db")
collection = chroma_client.get_or_create_collection(name="documents")

ranker = Ranker(model_name="ms-marco-MiniLM-L-12-v2", cache_dir="/tmp")

# 3. Initialize FastAPI App
app = FastAPI(title="Chat with PDF API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic Models
class ChatCreateResponse(BaseModel):
    chat_id: str
    title: str

class QueryRequest(BaseModel):
    question: str

class QueryResponse(BaseModel):
    answer: str
    sources: list[str]

# ENDPOINTS 
@app.get("/chats/{chat_id}/messages")
def get_chat_messages(chat_id: str, db: Session = Depends(get_db)):
    messages = db.query(MessageDB).filter(MessageDB.chat_id == chat_id).order_by(MessageDB.id).all()
    return [{"role": m.role, "content": m.content} for m in messages]

@app.post("/chat/{chat_id}")
def chat_with_pdf(chat_id: str, request: QueryRequest, db: Session = Depends(get_db)):

    user_msg = MessageDB(chat_id=chat_id, role="user", content=request.question)
    db.add(user_msg)
    db.commit()

    query_embedding = embedding_model.encode([request.question])[0].tolist()

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=15,
        where={"chat_id": chat_id}
    )

    if not results['documents'][0]:
        
        def error_stream():
            yield "I couldn't find any documents in this chat."
        return StreamingResponse(error_stream(), media_type="text/plain")

    retrieved_chunks = results['documents'][0]
    passages = [{"id": str(i), "text": chunk} for i, chunk in enumerate(retrieved_chunks)]
    rerank_request = RerankRequest(query=request.question, passages=passages)
    rerank_results = ranker.rerank(rerank_request)
    top_3_chunks = [result["text"] for result in rerank_results[:3]]

    context_text = "\n\n---\n\n".join(top_3_chunks)
    prompt = f"""
Use the provided context to answer the user's question.
If the answer is not in the context, say "I don't know based on the provided document."

CONTEXT: {context_text}
QUESTION: {request.question}"""

    
    def stream_generator():
        full_response = ""
        try:
            
            response = ai_client.models.generate_content_stream(
                model="gemini-3.5-flash",
                contents=prompt
            )
            for chunk in response:
                if chunk.text:
                    full_response += chunk.text
                    yield chunk.text 
        except Exception as e:
            yield f"\n[Error: {e}]"
        finally:
           
            ai_msg = MessageDB(chat_id=chat_id, role="ai", content=full_response)
            db.add(ai_msg)
            db.commit()
            
            
            yield f"\n\n__SOURCES__{json.dumps(top_3_chunks)}"

    return StreamingResponse(stream_generator(), media_type="text/plain")

@app.get("/")
def home():
    return {"messsage": "Chat with PDF API is running"}

@app.post("/chats", response_model=ChatCreateResponse)
def create_chat(db: Session = Depends(get_db)):
    chat_id = str(uuid.uuid4())
    new_chat = ChatsessionDB(id = chat_id, title = "New Document Chat")
    db.add(new_chat)
    db.commit()
    return {"chat_id": chat_id, "title": "New Document Chat"}

@app.get("/chats")
def get_chats(db: Session = Depends(get_db)):
    chats = db.query(ChatsessionDB).all()
    return chats

@app.post("/upload/{chat_id}")
async def upload_pdf(chat_id: str, file: UploadFile = File(...)):
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only Pdfs")

    contents =await file.read()
    reader = PdfReader(io.BytesIO(contents))

    full_text = ""
    for page in reader.pages:
        text = page.extract_text()
        if text: full_text += text + "\n"

    chunks = [full_text[i:i+1000]for i in range(0, len(full_text), 800)]

        
    batch_size = 32 
    for i in range(0, len(chunks), batch_size):
        batch_chunks = chunks[i:i+batch_size]
        batch_ids = [f"{chat_id}_{i+j}" for j in range(len(batch_chunks))]
        metadatas = [{"chat_id": chat_id, "source": file.filename} for _ in batch_chunks]
        
        
        embeddings = embedding_model.encode(batch_chunks).tolist()
        
        collection.add(
            embeddings=embeddings,
            documents=batch_chunks,
            metadatas=metadatas,
            ids=batch_ids
        )
    
    return {"message": "File processed successfully"}

@app.post("/upload/{chat_id}")
async def upload_pdf(chat_id: str, file: UploadFile = File(...)):
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only Pdfs")

    contents = await file.read()
    reader = PdfReader(io.BytesIO(contents))

    full_text = ""
    for page in reader.pages:
        text = page.extract_text()
        if text: full_text += text + "\n"

    chunks = [full_text[i:i+1000] for i in range(0, len(full_text), 800)]

    # Batch embed and upload (Now using local model!)
    batch_size = 32 
    for i in range(0, len(chunks), batch_size):
        batch_chunks = chunks[i:i+batch_size]
        batch_ids = [f"{chat_id}_{i+j}" for j in range(len(batch_chunks))]
        metadatas = [{"chat_id": chat_id, "source": file.filename} for _ in batch_chunks]
        
        embeddings = embedding_model.encode(batch_chunks).tolist()
        
        collection.add(
            embeddings=embeddings,
            documents=batch_chunks,
            metadatas=metadatas,
            ids=batch_ids
        )
    
    return {"message": "File processed successfully"}

@app.post("/chat/{chat_id}", response_model=QueryResponse)
def chat_with_pdf(chat_id: str, request: QueryRequest):

    query_embedding = embedding_model.encode([request.question])[0].tolist()

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=15,
        where={"chat_id": chat_id}
    )

    if not results['documents'][0]:
        return QueryResponse(answer="I couldn't find any documents in this chat.", sources=[])

    retrieved_chunks = results['documents'][0]

    passages = [{"id": str(i), "text": chunk} for i, chunk in enumerate(retrieved_chunks)]
    rerank_request = RerankRequest(query=request.question, passages=passages)
    rerank_results = ranker.rerank(rerank_request)
    top_3_chunks = [result["text"] for result in rerank_results[:3]]

    context_text = "\n\n---\n\n".join(top_3_chunks)
    
    prompt = f"""
Use the provided context to answer the user's question.
If the answer is not in the context, say "I don't know based on the provided document."

CONTEXT: {context_text}
QUESTION: {request.question}"""

    response = ai_client.models.generate_content(
        model="gemini-3.5-flash", # Changed to 2.5 just to be safe, but 3.5 is fine if it works!
        contents=prompt
    )

    return QueryResponse(answer=response.text, sources=top_3_chunks)