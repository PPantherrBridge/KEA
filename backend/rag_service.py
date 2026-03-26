import logging

from openai import OpenAI

from backend.config import CHAT_MODEL, DEFAULT_TOP_K, OPENAI_API_KEY
from backend.vector_store import VectorStore

LOGGER = logging.getLogger("kea.rag")
FALLBACK_ANSWER = "I don't have enough information from the provided source"

SYSTEM_PROMPT = (
    "You are a strict KEA website assistant. Use ONLY the given context from kea.kar.nic.in. "
    "If the context does not contain the answer, respond exactly: "
    "I don't have enough information from the provided source. "
    "Do not use outside knowledge. Keep answers concise and factual."
)


class RAGService:
    def __init__(self, vector_store: VectorStore):
        if not OPENAI_API_KEY:
            raise RuntimeError("OPENAI_API_KEY is not set")
        self.client = OpenAI(api_key=OPENAI_API_KEY)
        self.vector_store = vector_store

    def ask(self, question: str, top_k: int = DEFAULT_TOP_K) -> dict:
        retrieved = self.vector_store.retrieve(question, top_k=top_k)

        if not retrieved:
            return {"answer": FALLBACK_ANSWER, "sources": []}

        context_blocks = []
        for idx, item in enumerate(retrieved, start=1):
            context_blocks.append(f"[{idx}] URL: {item['url']}\n{item['text']}")

        prompt = (
            "Context:\n"
            + "\n\n".join(context_blocks)
            + f"\n\nQuestion: {question}\n"
            + "Answer using only context. If missing, output fallback sentence exactly."
        )

        completion = self.client.chat.completions.create(
            model=CHAT_MODEL,
            temperature=0.0,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
        )

        answer = completion.choices[0].message.content.strip()
        if not answer:
            answer = FALLBACK_ANSWER

        return {
            "answer": answer,
            "sources": [{"url": item["url"], "score": item["score"]} for item in retrieved],
        }
