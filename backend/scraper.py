import hashlib
import json
import logging
import re
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from pypdf import PdfReader

from backend.config import CRAWL_STATE_PATH, DEFAULT_SITE_URL, MAX_CRAWL_PAGES, RAW_DIR, REQUEST_TIMEOUT_SECONDS

LOGGER = logging.getLogger("kea.scraper")

TEXT_TAGS = ["p", "li", "h1", "h2", "h3", "h4", "h5", "h6", "table", "article", "section"]
BLOCKED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".svg", ".zip", ".mp4", ".doc", ".docx", ".xls", ".xlsx"}


@dataclass
class ScrapedDocument:
    url: str
    content: str
    content_type: str


def _is_same_site(url: str, root_domain: str) -> bool:
    parsed = urlparse(url)
    return (parsed.netloc == root_domain) or parsed.netloc.endswith(f".{root_domain}")


def _normalize_url(url: str) -> str:
    parsed = urlparse(url)
    clean_path = parsed.path or "/"
    return f"{parsed.scheme}://{parsed.netloc}{clean_path}"


def _safe_filename(url: str, suffix: str) -> Path:
    digest = hashlib.sha256(url.encode("utf-8")).hexdigest()[:16]
    return RAW_DIR / f"{digest}{suffix}"


def _clean_text(text: str) -> str:
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _extract_html_text(html: str) -> str:
    soup = BeautifulSoup(html, "lxml")

    for tag in soup(["script", "style", "noscript", "header", "footer", "nav", "aside"]):
        tag.decompose()

    text_parts = []
    for tag_name in TEXT_TAGS:
        for elem in soup.find_all(tag_name):
            text = _clean_text(elem.get_text(" ", strip=True))
            if text and len(text) > 25:
                text_parts.append(text)

    if not text_parts:
        body_text = _clean_text(soup.get_text(" ", strip=True))
        return body_text

    joined = "\n".join(dict.fromkeys(text_parts))
    return _clean_text(joined)


def _extract_links(base_url: str, html: str) -> Iterable[str]:
    soup = BeautifulSoup(html, "lxml")
    for a in soup.find_all("a", href=True):
        href = urljoin(base_url, a["href"])
        if href.startswith("mailto:") or href.startswith("javascript:"):
            continue
        yield href


def _download_pdf_text(url: str, response_content: bytes) -> str:
    temp_pdf = _safe_filename(url, ".pdf")
    temp_pdf.write_bytes(response_content)
    reader = PdfReader(str(temp_pdf))
    pages = []
    for page in reader.pages:
        page_text = page.extract_text() or ""
        cleaned = _clean_text(page_text)
        if cleaned:
            pages.append(cleaned)
    return "\n".join(pages)


def crawl_site(start_url: str = DEFAULT_SITE_URL, force_rescrape: bool = False) -> list[ScrapedDocument]:
    parsed_start = urlparse(start_url)
    root_domain = parsed_start.netloc

    seen = set()
    queue = deque([_normalize_url(start_url)])
    documents: list[ScrapedDocument] = []

    if CRAWL_STATE_PATH.exists() and not force_rescrape:
        LOGGER.info("Loading previous crawl state from %s", CRAWL_STATE_PATH)
        saved = json.loads(CRAWL_STATE_PATH.read_text(encoding="utf-8"))
        for item in saved.get("documents", []):
            documents.append(ScrapedDocument(**item))
        return documents

    session = requests.Session()
    session.headers.update({"User-Agent": "KEA-RAG-Bot/1.0 (+https://kea.kar.nic.in)"})

    while queue and len(seen) < MAX_CRAWL_PAGES:
        current = queue.popleft()
        norm = _normalize_url(current)
        if norm in seen:
            continue
        seen.add(norm)

        try:
            response = session.get(norm, timeout=REQUEST_TIMEOUT_SECONDS)
            response.raise_for_status()
        except Exception as exc:
            LOGGER.warning("Skipping %s due to request error: %s", norm, exc)
            continue

        content_type = response.headers.get("Content-Type", "").lower()
        LOGGER.info("Fetched %s [%s]", norm, content_type)

        if "pdf" in content_type or norm.lower().endswith(".pdf"):
            try:
                text = _download_pdf_text(norm, response.content)
            except Exception as exc:
                LOGGER.warning("Unable to parse PDF %s: %s", norm, exc)
                continue
            if text:
                documents.append(ScrapedDocument(url=norm, content=text, content_type="pdf"))
            continue

        if "text/html" not in content_type:
            path = urlparse(norm).path.lower()
            if any(path.endswith(ext) for ext in BLOCKED_EXTENSIONS):
                continue

        html = response.text
        text = _extract_html_text(html)
        if text:
            documents.append(ScrapedDocument(url=norm, content=text, content_type="html"))

        for link in _extract_links(norm, html):
            normalized = _normalize_url(link)
            parsed = urlparse(normalized)
            if parsed.scheme not in {"http", "https"}:
                continue
            if not _is_same_site(normalized, root_domain):
                continue
            lower_path = parsed.path.lower()
            if any(lower_path.endswith(ext) for ext in BLOCKED_EXTENSIONS):
                continue
            if normalized not in seen:
                queue.append(normalized)

    payload = {
        "start_url": start_url,
        "count": len(documents),
        "documents": [doc.__dict__ for doc in documents],
    }
    CRAWL_STATE_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    LOGGER.info("Saved crawl state with %s documents", len(documents))
    return documents
