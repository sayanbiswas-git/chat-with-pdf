# Cowork: Full-Stack AI Document Assistant

A multi-tenant, Retrieval-Augmented Generation (RAG) application that allows users to upload PDFs and have real-time streaming conversations with their documents. 

## Features
- **Multi-Chat Architecture:** Create and manage multiple isolated chat sessions. Documents uploaded to one chat are strictly filtered and cannot be accessed by another (Metadata Filtering).
- **Real-Time Streaming:** AI responses are streamed word-by-word to the frontend using Server-Sent Events (SSE), resulting in a ChatGPT-like experience.
- **Local Embeddings:** Uses `SentenceTransformers` (all-MiniLM-L6-v2) to generate vector embeddings locally, completely eliminating API rate limits and costs for ingestion.
- **Advanced Retrieval:** Implements a two-stage retrieval pipeline using ChromaDB (vector search) followed by FlashRank (cross-encoder reranking) for high-accuracy context retrieval.
- **Persistent Chat History:** All conversations and file names are stored in a local SQLite database, allowing users to switch between chats without losing context.

## Tech Stack
- **Backend:** Python, FastAPI, SQLite (SQLAlchemy), ChromaDB
- **Frontend:** React, TypeScript, Vite, React-Markdown
- **AI & ML:** Google Gemini API (Generation), SentenceTransformers (Local Embeddings), FlashRank (Reranking)

## Architecture
1. **Ingestion:** User uploads a PDF -> Text is extracted and chunked -> Local SentenceTransformer generates embeddings -> Stored in ChromaDB with a specific `chat_id`.
2. **Retrieval:** User asks a question -> Local embedding generated -> ChromaDB searches only for that `chat_id` -> FlashRank reranks the top chunks.
3. **Generation:** Reranked chunks are sent to Gemini as context -> The response is streamed back to the React UI in real-time.

## How to Run Locally

**1. Install Everything (Copy and paste this entire block into your terminal):**

```bash
git clone https://github.com/sayanbiswas-git/chat-with-pdf.git
cd chat-with-pdf
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
cd frontend
npm install
cd ..