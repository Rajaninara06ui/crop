from app.rag.chunker import TextChunker
from app.rag.document_loader import Document
from app.rag.retriever import Retriever
from app.rag.vector_store import MockVectorStore


def test_chunker_splits_text():
    content = "Paragraph 1 about tomato yellow leaf.\n\nParagraph 2 about pest control in chilli.\n\nParagraph 3 about paddy irrigation."
    doc = Document(content=content, metadata={"title": "Test Guide", "source": "test.txt"})
    chunker = TextChunker(chunk_size=50, chunk_overlap=10)
    chunks = chunker.chunk_document(doc)
    assert len(chunks) >= 2
    assert all("title" in c.metadata for c in chunks)


def test_mock_vector_store_retrieval():
    store = MockVectorStore()
    results = store.similarity_search("tomato leaves yellow", k=2)
    assert len(results) > 0
    doc, score = results[0]
    assert score > 0.0
    assert doc.metadata["crop"] == "tomato"


def test_retriever_build_context():
    retriever = Retriever()
    chunks = retriever.retrieve("paddy water irrigation")
    context = retriever.build_context(chunks)
    assert len(context) > 0
