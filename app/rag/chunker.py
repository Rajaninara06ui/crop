from __future__ import annotations
from typing import List
from app.core.config import settings
from app.rag.document_loader import Document


class TextChunker:
    SEPARATORS = ["\n\n", "\n", ". ", "! ", "? ", "; ", ", ", " ", ""]

    def __init__(self, chunk_size: int = settings.CHUNK_SIZE, chunk_overlap: int = settings.CHUNK_OVERLAP) -> None:
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def _split_text(self, text: str) -> List[str]:
        if len(text) <= self.chunk_size:
            return [text]
        for sep in self.SEPARATORS:
            if sep and sep in text:
                parts = text.split(sep)
                chunks: List[str] = []
                current = ""
                for part in parts:
                    candidate = current + (sep if current else "") + part
                    if len(candidate) <= self.chunk_size:
                        current = candidate
                    else:
                        if current:
                            chunks.append(current)
                        current = part
                if current:
                    chunks.append(current)
                merged: List[str] = []
                for i, chunk in enumerate(chunks):
                    if i > 0 and self.chunk_overlap > 0:
                        overlap_text = chunks[i - 1][-self.chunk_overlap:]
                        chunk = overlap_text + " " + chunk
                    merged.append(chunk.strip())
                return [c for c in merged if c]
        return [text[i: i + self.chunk_size] for i in range(0, len(text), self.chunk_size - self.chunk_overlap)]

    def chunk_document(self, doc: Document) -> List[Document]:
        raw_chunks = self._split_text(doc.content)
        return [
            Document(content=chunk_text, metadata={**doc.metadata, "chunk_index": idx})
            for idx, chunk_text in enumerate(raw_chunks) if chunk_text.strip()
        ]

    def chunk_documents(self, docs: List[Document]) -> List[Document]:
        chunks: List[Document] = []
        for doc in docs:
            chunks.extend(self.chunk_document(doc))
        return chunks
