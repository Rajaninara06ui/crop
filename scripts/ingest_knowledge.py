from __future__ import annotations
import argparse
import sys
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from app.core.config import settings
from app.core.logging import get_logger, setup_logging
from app.rag.chunker import TextChunker
from app.rag.document_loader import load_directory, load_text_file
from app.rag.vector_store import FAISSVectorStore

logger = get_logger("ingest_knowledge")


def main():
    parser = argparse.ArgumentParser(description="Ingest agricultural knowledge documents into vector store.")
    parser.add_argument(
        "--data-dir",
        type=str,
        default=str(backend_dir / "app" / "data" / "sample_knowledge"),
        help="Directory containing agricultural documents (.txt, .md, .pdf)",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=str(backend_dir / settings.VECTOR_STORE_PATH),
        help="Directory to save the vector index and metadata",
    )
    parser.add_argument("--chunk-size", type=int, default=settings.CHUNK_SIZE)
    parser.add_argument("--chunk-overlap", type=int, default=settings.CHUNK_OVERLAP)
    args = parser.parse_args()

    setup_logging(debug=True)
    logger.info("Starting knowledge ingestion from '%s'...", args.data_dir)

    data_path = Path(args.data_dir)
    if not data_path.exists():
        logger.error("Data directory does not exist: %s", data_path)
        sys.exit(1)

    # 1. Load Documents
    docs = load_directory(data_path)
    logger.info("Loaded %d raw documents.", len(docs))
    if not docs:
        logger.warning("No documents found to ingest.")
        return

    # 2. Chunk Documents
    chunker = TextChunker(chunk_size=args.chunk_size, chunk_overlap=args.chunk_overlap)
    chunks = chunker.chunk_documents(docs)
    logger.info("Generated %d text chunks.", len(chunks))

    # 3. Embed & Store
    logger.info("Creating vector index at '%s'...", args.output_dir)
    try:
        store = FAISSVectorStore(store_path=args.output_dir)
        store.add_documents(chunks)
        logger.info("Successfully ingested %d chunks into FAISS vector store.", len(chunks))
    except Exception as exc:
        logger.error("Failed to build vector index: %s", exc)
        logger.info("Note: When MOCK_MODE=true, the app automatically uses pre-built in-memory knowledge.")


if __name__ == "__main__":
    main()
