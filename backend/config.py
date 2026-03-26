import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"

CRAWL_STATE_PATH = RAW_DIR / "crawl_state.json"
DOCUMENTS_PATH = PROCESSED_DIR / "documents.json"
CHUNKS_PATH = PROCESSED_DIR / "chunks.json"
METADATA_PATH = PROCESSED_DIR / "metadata.json"
FAISS_INDEX_PATH = PROCESSED_DIR / "index.faiss"
EMBED_CACHE_PATH = PROCESSED_DIR / "embedding_cache.json"

DEFAULT_SITE_URL = "https://kea.kar.nic.in"
DEFAULT_TOP_K = 4
EMBEDDING_MODEL = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
CHAT_MODEL = os.getenv("OPENAI_CHAT_MODEL", "gpt-4o-mini")
MAX_CRAWL_PAGES = int(os.getenv("MAX_CRAWL_PAGES", "2000"))
REQUEST_TIMEOUT_SECONDS = int(os.getenv("REQUEST_TIMEOUT_SECONDS", "30"))

ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

for directory in (DATA_DIR, RAW_DIR, PROCESSED_DIR):
    directory.mkdir(parents=True, exist_ok=True)
