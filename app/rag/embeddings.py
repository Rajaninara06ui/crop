from __future__ import annotations
from functools import lru_cache
from typing import List
import numpy as np
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class EmbeddingService:
    def __init__(self, model_name: str = settings.EMBEDDING_MODEL) -> None:
        self.model_name = model_name
        self._model = None

    def _load(self):
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
                self._model = SentenceTransformer(self.model_name)
                logger.info("Loaded embedding model: %%s", self.model_name)
            except ImportError:
                logger.error("sentence-transformers not installed.")
                raise
        return self._model

    def embed(self, texts: List[str]) -> np.ndarray:
        model = self._load()
        return model.encode(texts, normalize_embeddings=True, show_progress_bar=False)

    def embed_one(self, text: str) -> np.ndarray:
        return self.embed([text])[0]


@lru_cache(maxsize=1)
def get_embedding_service() -> EmbeddingService:
    return EmbeddingService()
