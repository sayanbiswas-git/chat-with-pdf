import chromadb
from google import genai
import os
from dotenv import load_dotenv
from pypdf import PdfReader
import time

load_dotenv()


# Connect to Gimini
GIMINI_API_KEY = os.getenv("GIMINI_API_KEY")
ai_client = genai.Client(api_key=GIMINI_API_KEY)

# Connect to ChromaDb
chroma_client = chromadb.PersistentClient(path="./chroma_db")

# Delete old data if we run the script twice
try:
    chroma_client.delete_collection(name="book_collection")
except Exception:
    pass
collection = chroma_client.create_collection(name="book_collection")



def extract_and_chunk_pdf(file_pdf, chunk_size=1000, chunk_overlap=200):
    reader = PdfReader(file_pdf)
    full_text =""

    # Extract all text from the PDF
    for page in reader.pages:
        text = page.extract_text()
        if text:
            full_text += text + "\n"


    # Slice the text into chunks
    chunks =[]
    start = 0
    while start < len(full_text):
        end = start + chunk_size
        chunk = full_text[start:end]
        chunks.append(chunk)
        start += (chunk_size - chunk_overlap)
    return chunks



if __name__ == "__main__":
    # Prepare the data
    print("Reading and chunking PDF...")
    chunks = extract_and_chunk_pdf("test.pdf")

    print(f"Generating embeddings for {len(chunks)} chunks using Gimini. (This might take a minute)...")

    # Create IDs and metadatas
    ids = [f"chunk_{i}" for i in range(len(chunks))]
    metadatas = [{"source":"test.pdf", "chunk_index": i} for i in range(len(chunks))]

        # Batching and Upload Loop
    batch_size = 20
    for i in range(0, len(chunks), batch_size):
        # Grab the current batch
        batch_chunks = chunks[i:i+batch_size]
        batch_ids = ids[i:i+batch_size]
        batch_metadatas = metadatas[i:i+batch_size]
        
        print(f"Processing batch {i//batch_size + 1}...")

        # The retry safety Net
        success = False
        while not success:
            try:
                response = ai_client.models.embed_content(
                    model="gemini-embedding-001",
                    contents=batch_chunks,
                )
                embeddings = [emb.values for emb in response.embeddings]

                # Save the text and the numbers into ChromaDb
                collection.add(
                    embeddings=embeddings,
                    documents=batch_chunks,
                    metadatas=batch_metadatas,
                    ids=batch_ids
                )
                success = True # Break the retry loop if it worked
                
            except Exception as e:
                # if "too many requests", wait 15 secs and try again
                print(f"⚠️ Rate limit hit on batch {i//batch_size + 1}. Waiting 15 seconds to retry...")
                time.sleep(15) # Wait before trying this batch again
                
        # wait 5 secs to prevent hitting the limit in the first place
        time.sleep(5) 

    print(f"\n Succesfully added {len(chunks)} chunks to ChromaDB!")
    print("You should now see a folder named 'chroma_db' in your file explorer.")
