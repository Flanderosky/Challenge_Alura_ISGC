"""
Pruebas básicas del agente.
"""

import os
import pytest

from src.loader import load_document
from src.vectorstore import create_vector_store


DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")


def test_load_csv():
    path = os.path.join(DATA_DIR, "ventas_ejemplo.csv")
    docs = load_document(path)
    assert len(docs) > 0
    assert "Laptop Pro" in docs[0].page_content


def test_load_pdf():
    path = os.path.join(DATA_DIR, "politicas_ejemplo.pdf")
    docs = load_document(path)
    assert len(docs) > 0
    assert "AluraTech" in docs[0].page_content or "política" in docs[0].page_content.lower()


def test_create_vector_store():
    path = os.path.join(DATA_DIR, "ventas_ejemplo.csv")
    docs = load_document(path)
    vector_store = create_vector_store(docs)
    assert vector_store is not None

    # Buscar algo relacionado con ventas
    results = vector_store.similarity_search("producto más vendido", k=3)
    assert len(results) > 0


def test_get_llm_without_key_raises():
    from src.agent import get_llm

    # Sin configuración debe fallar
    with pytest.raises(ValueError):
        get_llm("gemini")
