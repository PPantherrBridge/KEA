import hashlib
import json
import logging
from dataclasses import asdict

import faiss
import numpy as np
from openai import OpenAI

from backend.chunker import Chunk, load_chunks
from backend.config import (
    CHUNKS_PATH,
    EMBED_CACHE_PATH,
    EMBEDDING_MODEL,
    FAISS_INDEX_PATH,
    METADATA_PATH,
    OPENAI_API_KEY,
)

LOGGER = logging.getLogger("kea.vector")


class EmbeddingCache:
    def __init__(self, path=EMBED_CACHE_PATH):
        self.path = path
        if self.path.exists():
            self.data = json.loads(self.path.read_text(encoding="utf-8"))
        else:
            self.data = {}

    @staticmethod
    def _key(text: str) -> str:
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    def get(self, text: str):
        return self.data.get(self._key(text))

    def set(self, text: str, embedding: list[float]):
        self.data[self._key(text)] = embedding

    def save(self):
        self.path.write_text(json.dumps(self.data), encoding="utf-8")


class VectorStore:
    def __init__(self):
        if not OPENAI_API_KEY:
            raise RuntimeError("OPENAI_API_KEY is not set")
        self.client = OpenAI(api_key=OPENAI_API_KEY)
        self.cache = EmbeddingCache()
        self.index = None
        self.metadata: list[dict] = []

    def _embed_texts(self, texts: list[str]) -> np.ndarray:
        vectors = []
        to_fetch = []
        to_fetch_idx = []

        for i, text in enumerate(texts):
            cached = self.cache.get(text)
            if cached is None:
                to_fetch.append(text)
                to_fetch_idx.append(i)
                vectors.append(None)
            else:
                vectors.append(cached)

        if to_fetch:
            response = self.client.embeddings.create(model=EMBEDDING_MODEL, input=to_fetch)
            for pos, emb_data in enumerate(response.data):
                idx = to_fetch_idx[pos]
                embedding = emb_data.embedding
                vectors[idx] = embedding
                self.cache.set(to_fetch[pos], embedding)
            self.cache.save()

        array = np.array(vectors, dtype="float32")
        faiss.normalize_L2(array)
        return array

    def build_from_chunks(self, chunks: list[Chunk]) -> None:
        if not chunks:
            raise RuntimeError(f"No chunks available at {CHUNKS_PATH}")

        texts = [c.text for c in chunks]
        vectors = self._embed_texts(texts)
        dim = vectors.shape[1]
        index = faiss.IndexFlatIP(dim)
        index.add(vectors)

        self.index = index
        self.metadata = [asdict(c) for c in chunks]

        faiss.write_index(self.index, str(FAISS_INDEX_PATH))
        METADATA_PATH.write_text(json.dumps(self.metadata, ensure_ascii=False, indent=2), encoding="utf-8")
        LOGGER.info("Built FAISS index with %s vectors", len(chunks))

    def load(self) -> None:
        if not FAISS_INDEX_PATH.exists() or not METADATA_PATH.exists():
            raise RuntimeError("FAISS index or metadata missing. Run build first.")
        self.index = faiss.read_index(str(FAISS_INDEX_PATH))
        self.metadata = json.loads(METADATA_PATH.read_text(encoding="utf-8"))

    def retrieve(self, query: str, top_k: int = 4) -> list[dict]:
        if self.index is None:
            self.load()
        query_vec = self._embed_texts([query])
        scores, indices = self.index.search(query_vec, top_k)

        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < 0 or idx >= len(self.metadata):
                continue
            item = self.metadata[idx]
            item["score"] = float(score)
            results.append(item)
        return results


def load_or_build_vector_store() -> VectorStore:
    store = VectorStore()
    if FAISS_INDEX_PATH.exists() and METADATA_PATH.exists():
        store.load()
        return store

    chunks = load_chunks()
    store.build_from_chunks(chunks)
    return store
