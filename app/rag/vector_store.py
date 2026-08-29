from __future__ import annotations
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import numpy as np
from app.core.config import settings
from app.core.logging import get_logger
from app.rag.document_loader import Document
from app.rag.embeddings import get_embedding_service

logger = get_logger(__name__)


class FAISSVectorStore:
    INDEX_FILE = "index.faiss"
    META_FILE = "metadata.json"

    def __init__(self, store_path: str = settings.VECTOR_STORE_PATH) -> None:
        self.store_path = Path(store_path)
        self.store_path.mkdir(parents=True, exist_ok=True)
        self._index = None
        self._metadata: List[Dict] = []
        self._texts: List[str] = []
        self._embedder = get_embedding_service()
        self._try_load()

    def _try_load(self) -> None:
        idx_path = self.store_path / self.INDEX_FILE
        meta_path = self.store_path / self.META_FILE
        if idx_path.exists() and meta_path.exists():
            try:
                import faiss
                self._index = faiss.read_index(str(idx_path))
                with open(meta_path, encoding="utf-8") as f:
                    saved = json.load(f)
                self._metadata = saved.get("metadata", [])
                self._texts = saved.get("texts", [])
                logger.info("Loaded vector store: %%d vectors", self._index.ntotal)
            except Exception as exc:
                logger.warning("Could not load vector store: %%s", exc)

    def _save(self) -> None:
        import faiss
        faiss.write_index(self._index, str(self.store_path / self.INDEX_FILE))
        with open(self.store_path / self.META_FILE, "w", encoding="utf-8") as f:
            json.dump({"metadata": self._metadata, "texts": self._texts}, f, ensure_ascii=False)

    def add_documents(self, docs: List[Document]) -> None:
        if not docs:
            return
        import faiss
        texts = [d.content for d in docs]
        embeddings = self._embedder.embed(texts).astype(np.float32)
        dim = embeddings.shape[1]
        if self._index is None:
            self._index = faiss.IndexFlatIP(dim)
        self._index.add(embeddings)
        self._metadata.extend([d.metadata for d in docs])
        self._texts.extend(texts)
        self._save()

    def similarity_search(self, query: str, k: int = settings.TOP_K, threshold: float = settings.SIMILARITY_THRESHOLD) -> List[Tuple[Document, float]]:
        if self._index is None or self._index.ntotal == 0:
            return []
        import faiss
        query_vec = self._embedder.embed_one(query).reshape(1, -1).astype(np.float32)
        k = min(k, self._index.ntotal)
        scores, indices = self._index.search(query_vec, k)
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < 0:
                continue
            sim = float(score)
            if sim < threshold:
                continue
            doc = Document(content=self._texts[idx], metadata=self._metadata[idx])
            results.append((doc, sim))
        return results

    @property
    def is_ready(self) -> bool:
        return self._index is not None and self._index.ntotal > 0


class MockVectorStore:
    def __init__(self) -> None:
        self._demo: List[Document] = []
        self._load_demo()

    def _load_demo(self) -> None:
        demo_data = [
            ("Tomato Yellow Leaf Knowledge Base", "tomato",
             "Tomato leaves turning yellow can indicate nutrient deficiency, overwatering, or fungal diseases. "
             "Check soil pH (6.0-6.8), ensure proper drainage, inspect for pests. Magnesium deficiency causes "
             "interveinal chlorosis. Iron deficiency causes yellowing of new leaves. Apply balanced fertilizer."),
            ("Paddy Irrigation Guide", "paddy",
             "Paddy requires flooding 5-7 cm deep during vegetative stage. Drain fields 10 days before harvest. "
             "Water stress at booting and flowering stages reduces yield. Use AWD (Alternate Wetting and Drying) "
             "technique to save water by 30%%. Monitor soil moisture with field water tubes."),
            ("Chilli Pest Management", "chilli",
             "Common chilli pests include thrips, mites, and aphids. Thrips cause silvery streaks on leaves. "
             "Use neem-based pesticides (Azadirachtin 0.3%%) for organic control. Spray dimethoate 30EC for "
             "severe thrips infestation. Introduce predatory insects for biological control."),
            ("Cotton Fertilizer Recommendations", "cotton",
             "Cotton requires NPK 120:60:60 kg/ha. Apply nitrogen in splits: 30%% basal, 30%% at squaring, "
             "40%% at boll formation. Potassium is critical for fiber quality. Apply zinc (25 kg ZnSO4/ha)."),
            ("Crop Disease General Guide", "general",
             "Early detection of plant diseases is key. Common symptoms: leaf spots, wilting, discoloration. "
             "Implement IPM combining cultural, biological, and chemical methods. Rotate crops to break disease cycles."),
        ]
        for title, crop, content in demo_data:
            self._demo.append(Document(
                content=content,
                metadata={"title": title, "category": "crop", "crop": crop, "language": "en", "source": "demo"},
            ))

    def add_documents(self, docs: List[Document]) -> None:
        self._demo.extend(docs)

    def similarity_search(self, query: str, k: int = 3, threshold: float = 0.0) -> List[Tuple[Document, float]]:
        query_lower = query.lower()
        scored = []
        for doc in self._demo:
            words = set(query_lower.split())
            doc_words = set(doc.content.lower().split())
            overlap = len(words & doc_words)
            score = min(0.95, 0.5 + overlap * 0.05)
            scored.append((doc, score))
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:k]

    @property
    def is_ready(self) -> bool:
        return True


def get_vector_store():
    if settings.MOCK_MODE:
        return MockVectorStore()
    return FAISSVectorStore()
