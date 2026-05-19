"""Document loading + chunking — independent of the vector store backend."""

from __future__ import annotations

from pathlib import Path
from typing import List

from langchain_community.document_loaders import PyPDFLoader
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from ..core.logging import get_logger

logger = get_logger(__name__)


class DocumentRepository:
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200) -> None:
        self._splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size, chunk_overlap=chunk_overlap
        )

    def load_pdf_directory(self, pdf_dir: str | Path) -> List[Document]:
        pdf_path = Path(pdf_dir)
        if not pdf_path.exists() or not pdf_path.is_dir():
            raise ValueError(f"pdf_dir not found or not a directory: {pdf_dir}")

        pdf_files = sorted(p for p in pdf_path.rglob("*.pdf") if p.is_file())
        if not pdf_files:
            raise ValueError(f"No PDF files found under: {pdf_dir}")

        chunks: List[Document] = []
        for pdf in pdf_files:
            chunks.extend(self.load_pdf(pdf))
        logger.info("DOC_REPO | %d PDF(s) → %d chunk(s)", len(pdf_files), len(chunks))
        return chunks

    def load_pdf(self, pdf_path: str | Path) -> List[Document]:
        pdf = Path(pdf_path)
        loader = PyPDFLoader(str(pdf))
        docs = loader.load()
        for d in docs:
            d.metadata = dict(d.metadata or {})
            d.metadata.setdefault("source", str(pdf))
            d.metadata.setdefault("title", pdf.stem)
        return self._splitter.split_documents(docs)
