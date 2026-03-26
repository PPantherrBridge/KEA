# KEA Website RAG Chatbot

Production-style beginner-friendly chatbot that answers questions using only content scraped from:
- https://kea.kar.nic.in

## Project Structure

```
.
├── app.py
├── backend/
│   ├── server.py
│   ├── scraper.py
│   ├── chunker.py
│   ├── vector_store.py
│   ├── rag_service.py
│   ├── config.py
│   └── logger.py
├── frontend/
│   ├── index.html
│   ├── styles.css
│   └── script.js
├── scripts/
│   └── build_knowledge_base.py
├── data/
│   ├── raw/
│   └── processed/
└── requirements.txt
```

## Features

- Full-site crawler (same-domain) with HTML text cleaning
- PDF ingestion and text extraction
- Chunking into semantically coherent sentence blocks (roughly 300-800 token target)
- OpenAI embeddings + local FAISS index
- Embedding cache (`data/processed/embedding_cache.json`) for faster rebuilds
- Strict answer policy: fallback message when info is missing
- Flask API (`/ask`), health endpoint (`/health`)
- Admin re-scrape endpoint (`/admin/rescrape`)
- Simple chat frontend with loading state
- Logging and error handling

## Setup

### 1) Create virtual environment

```bash
python -m venv .venv
source .venv/bin/activate
```

### 2) Install dependencies

```bash
pip install -r requirements.txt
```

### 3) Set environment variables

```bash
export OPENAI_API_KEY="your_openai_api_key"
# Optional
export OPENAI_CHAT_MODEL="gpt-4o-mini"
export OPENAI_EMBEDDING_MODEL="text-embedding-3-small"
export ADMIN_TOKEN="choose_a_secret_token"
```

### 4) Build the knowledge base

```bash
python scripts/build_knowledge_base.py --force
```

This will:
1. Crawl `kea.kar.nic.in`
2. Parse HTML/PDF content
3. Chunk and save processed chunks
4. Create FAISS index

### 5) Start app

```bash
python app.py
```

Open: `http://localhost:8000`

## API Usage

### Ask a question

`POST /ask`

Request:
```json
{ "question": "When does KEA release admission notifications?" }
```

Response:
```json
{
  "answer": "...",
  "sources": [
    {"url": "https://kea.kar.nic.in/...", "score": 0.82}
  ]
}
```

### Re-scrape and rebuild index

`POST /admin/rescrape`

Header:
- `X-Admin-Token: <ADMIN_TOKEN>` (required only if ADMIN_TOKEN is set)

Body (optional):
```json
{ "start_url": "https://kea.kar.nic.in" }
```

## Strict Answering Rule

The model is prompted to answer only from retrieved chunks. If answer is not found:

`I don't have enough information from the provided source`

## Debugging Tips

- Check logs in terminal for crawler, chunker, vector, and API errors.
- If index files are missing, run `python scripts/build_knowledge_base.py --force`.
- If answers are weak, rebuild after a fresh crawl.
