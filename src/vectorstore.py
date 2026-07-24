"""
Módulo para crear y consultar el vector store con FAISS.
"""

from typing import List, Optional

from langchain.schema import Document
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings


def create_vector_store(documents: List[Document], index_path: Optional[str] = None) -> FAISS:
    """
    Crea un índice FAISS a partir de una lista de documentos.

    Args:
        documents: Lista de Documentos de LangChain.
        index_path: Ruta opcional para guardar el índice en disco.

    Returns:
        Vector store FAISS listo para consultas.
    """
    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2",
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": False},
    )

    vector_store = FAISS.from_documents(documents, embeddings)

    if index_path:
        vector_store.save_local(index_path)

    return vector_store


def load_vector_store(index_path: str) -> FAISS:
    """Carga un índice FAISS previamente guardado."""
    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2",
        model_kwargs={"device": "cpu"},
    )
    return FAISS.load_local(index_path, embeddings, allow_dangerous_deserialization=True)
