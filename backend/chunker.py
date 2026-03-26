import json
import logging
import re
from dataclasses import dataclass, asdict

from backend.config import CHUNKS_PATH, DOCUMENTS_PATH
from backend.scraper import ScrapedDocument

LOGGER = logging.getLogger("kea.chunker")


@dataclass
class Chunk:
    id: str
    url: str
    text: str


def _estimate_tokens(text: str) -> int:
    # ~4 chars per token is a safe rough estimate for English-heavy text
    return max(1, len(text) // 4)


def _sentence_split(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+", text)
    return [p.strip() for p in parts if p.strip()]


def build_chunks(documents: list[ScrapedDocument], min_tokens: int = 300, max_tokens: int = 800) -> list[Chunk]:
    chunk_list: list[Chunk] = []

    for d_idx, doc in enumerate(documents):
        sentences = _sentence_split(doc.content)
        if not sentences:
            continue

        current: list[str] = []
        for sent in sentences:
            candidate = " ".join(current + [sent]).strip()
            candidate_tokens = _estimate_tokens(candidate)

            if candidate_tokens <= max_tokens:
                current.append(sent)
                continue

            if current:
                assembled = " ".join(current).strip()
                if _estimate_tokens(assembled) >= min_tokens:
                    chunk_id = f"doc{d_idx}_chunk{len(chunk_list)}"
                    chunk_list.append(Chunk(id=chunk_id, url=doc.url, text=assembled))
                current = [sent]
            else:
                chunk_id = f"doc{d_idx}_chunk{len(chunk_list)}"
                chunk_list.append(Chunk(id=chunk_id, url=doc.url, text=sent[:3000]))
                current = []

        if current:
            assembled = " ".join(current).strip()
            if assembled:
                chunk_id = f"doc{d_idx}_chunk{len(chunk_list)}"
                chunk_list.append(Chunk(id=chunk_id, url=doc.url, text=assembled))

    DOCUMENTS_PATH.write_text(
        json.dumps([doc.__dict__ for doc in documents], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    CHUNKS_PATH.write_text(
        json.dumps([asdict(c) for c in chunk_list], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    LOGGER.info("Generated %s chunks", len(chunk_list))
    return chunk_list


def load_chunks() -> list[Chunk]:
    if not CHUNKS_PATH.exists():
        return []
    raw = json.loads(CHUNKS_PATH.read_text(encoding="utf-8"))
    return [Chunk(**item) for item in raw]
