from __future__ import annotations
import re
from pathlib import Path
from typing import Dict, List


class Document:
    def __init__(self, content: str, metadata: Dict) -> None:
        self.content = content
        self.metadata = metadata

    def __repr__(self) -> str:
        return f"Document(title={self.metadata.get('title', '?')!r}, chars={len(self.content)})"


def _clean_text(text: str) -> str:
    text = re.sub(r"[\r\n]+", "\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def load_text_file(path: Path, metadata: Dict | None = None) -> Document:
    text = path.read_text(encoding="utf-8", errors="ignore")
    meta = {
        "title": path.stem.replace("_", " ").title(),
        "source": path.name,
        "language": "en",
        "category": "general",
    }
    if metadata:
        meta.update(metadata)
    return Document(content=_clean_text(text), metadata=meta)


def load_pdf_file(path: Path, metadata: Dict | None = None) -> List[Document]:
    try:
        from pypdf import PdfReader
    except ImportError:
        return []
    reader = PdfReader(str(path))
    docs = []
    base_meta = {
        "title": path.stem.replace("_", " ").title(),
        "source": path.name,
        "language": "en",
        "category": "general",
    }
    if metadata:
        base_meta.update(metadata)
    for i, page in enumerate(reader.pages):
        text = page.extract_text() or ""
        if not text.strip():
            continue
        docs.append(Document(content=_clean_text(text), metadata={**base_meta, "page": i + 1}))
    return docs


def load_directory(directory: Path, metadata_override: Dict | None = None) -> List[Document]:
    docs: List[Document] = []
    for path in sorted(directory.rglob("*")):
        if path.is_dir():
            continue
        if path.suffix.lower() in (".txt", ".md"):
            docs.append(load_text_file(path, metadata_override))
        elif path.suffix.lower() == ".pdf":
            docs.extend(load_pdf_file(path, metadata_override))
    return docs
