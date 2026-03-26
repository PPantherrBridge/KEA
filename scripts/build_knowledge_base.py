"""Crawl KEA site, chunk text, and build FAISS index."""

from backend.chunker import build_chunks
from backend.config import DEFAULT_SITE_URL
from backend.logger import setup_logging
from backend.scraper import crawl_site
from backend.vector_store import VectorStore



def main(force: bool = False):
    setup_logging()
    docs = crawl_site(start_url=DEFAULT_SITE_URL, force_rescrape=force)
    chunks = build_chunks(docs)
    store = VectorStore()
    store.build_from_chunks(chunks)
    print(f"Done. documents={len(docs)} chunks={len(chunks)}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true", help="Force a fresh crawl")
    args = parser.parse_args()
    main(force=args.force)
