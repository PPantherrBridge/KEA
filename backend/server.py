import logging
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory

from backend.chunker import build_chunks
from backend.config import ADMIN_TOKEN, DEFAULT_SITE_URL
from backend.logger import setup_logging
from backend.rag_service import FALLBACK_ANSWER, RAGService
from backend.scraper import crawl_site
from backend.vector_store import VectorStore, load_or_build_vector_store

setup_logging()
LOGGER = logging.getLogger("kea.server")

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"

app = Flask(__name__, static_folder=str(FRONTEND_DIR), static_url_path="")

vector_store: VectorStore | None = None
rag: RAGService | None = None


def initialize_rag() -> None:
    global vector_store, rag
    vector_store = load_or_build_vector_store()
    rag = RAGService(vector_store)


@app.get("/")
def index():
    return send_from_directory(FRONTEND_DIR, "index.html")


@app.post("/ask")
def ask():
    try:
        payload = request.get_json(force=True)
    except Exception:
        return jsonify({"error": "Invalid JSON body"}), 400

    question = (payload or {}).get("question", "").strip()
    if not question:
        return jsonify({"error": "Question is required"}), 400

    try:
        if rag is None:
            initialize_rag()
        result = rag.ask(question)
        return jsonify(result)
    except Exception as exc:
        LOGGER.exception("Ask request failed: %s", exc)
        return jsonify({"answer": FALLBACK_ANSWER, "sources": [], "error": str(exc)}), 500


@app.post("/admin/rescrape")
def rescrape():
    token = request.headers.get("X-Admin-Token", "")
    if ADMIN_TOKEN and token != ADMIN_TOKEN:
        return jsonify({"error": "Unauthorized"}), 401

    body = request.get_json(silent=True) or {}
    start_url = body.get("start_url", DEFAULT_SITE_URL)

    try:
        documents = crawl_site(start_url=start_url, force_rescrape=True)
        chunks = build_chunks(documents)

        global vector_store, rag
        vector_store = VectorStore()
        vector_store.build_from_chunks(chunks)
        rag = RAGService(vector_store)

        return jsonify(
            {
                "status": "ok",
                "documents": len(documents),
                "chunks": len(chunks),
            }
        )
    except Exception as exc:
        LOGGER.exception("Rescrape failed: %s", exc)
        return jsonify({"error": str(exc)}), 500


@app.get("/health")
def health():
    return jsonify({"status": "ok"})
