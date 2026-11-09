# 1. Use an official Python lightweight image
FROM python:3.11

# 2. Set the working directory
WORKDIR /app

# 3. Install system dependencies (build-essential includes gcc, g++, make)
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# 4. Upgrade pip (the notice in your terminal suggested this)
RUN pip install --upgrade pip

# 5. Copy requirements.txt 
COPY requirements.txt .

# 6. Install the Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# 7. Copy the backend code AND the database folder
COPY main.py .
COPY ingest.py .
COPY chroma_db ./chroma_db

# 8. Expose the backend port
EXPOSE 8000

# 9. Run the FastAPI backend
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]