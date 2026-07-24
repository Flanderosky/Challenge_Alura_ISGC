"""
Índice vectorial FAISS.

Los embeddings se cargan una sola vez por proceso: el modelo pesa ~90 MB y
reinstanciarlo en cada indexación era el mayor costo oculto de la aplicación.
"""

from functools import lru_cache
from typing import List, Optional, Tuple

from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings

EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


@lru_cache(maxsize=1)
def get_embeddings() -> HuggingFaceEmbeddings:
    """Modelo de embeddings compartido. Vectores normalizados para que la similitud sea coseno."""
    return HuggingFaceEmbeddings(
        model_name=EMBEDDING_MODEL,
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )


def create_vector_store(documents: List[Document], index_path: Optional[str] = None) -> FAISS:
    """Crea un índice FAISS a partir de una lista de fragmentos."""
    if not documents:
        raise ValueError("No hay fragmentos que indexar.")

    vector_store = FAISS.from_documents(documents, get_embeddings())
    if index_path:
        vector_store.save_local(index_path)
    return vector_store


def load_vector_store(index_path: str) -> FAISS:
    """Carga un índice FAISS previamente guardado."""
    return FAISS.load_local(index_path, get_embeddings(), allow_dangerous_deserialization=True)


def embed_query(query: str) -> List[float]:
    """Vectoriza la pregunta. Separado de la búsqueda para poder medir cada etapa."""
    return get_embeddings().embed_query(query)


def search_by_vector(vector_store: FAISS, vector: List[float], k: int = 4) -> List[Tuple[Document, float]]:
    """
    Busca los k fragmentos más parecidos a un vector ya calculado.

    Devuelve pares (fragmento, relevancia) donde la relevancia va de 0 a 1,
    para poder mostrarla en la interfaz sin que el usuario tenga que
    interpretar una distancia euclídea.
    """
    resultados = vector_store.similarity_search_with_score_by_vector(vector, k=k)
    return [(doc, _to_relevance(distancia)) for doc, distancia in resultados]


def search(vector_store: FAISS, query: str, k: int = 4) -> List[Tuple[Document, float]]:
    """Busca los k fragmentos más parecidos a una pregunta."""
    return search_by_vector(vector_store, embed_query(query), k=k)


def _to_relevance(distancia: float) -> float:
    """Convierte la distancia L2 entre vectores normalizados a una relevancia 0–1."""
    similitud = 1.0 - (float(distancia) ** 2) / 2.0
    return max(0.0, min(1.0, similitud))
