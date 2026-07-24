"""
Pruebas del núcleo: carga, fragmentación, índice y construcción del prompt.
No requieren clave de API.
"""

import os

import pytest

from src.loader import load_document, read_pages
from src.vectorstore import create_vector_store, search

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
CSV = os.path.join(DATA_DIR, "ventas_ejemplo.csv")
PDF = os.path.join(DATA_DIR, "politicas_ejemplo.pdf")


def test_load_csv_incluye_resumen_y_filas():
    docs = load_document(CSV)
    assert docs, "el CSV debería producir fragmentos"
    assert docs[0].metadata["unit"] == "summary"
    assert any("Laptop Pro" in d.page_content for d in docs)


def test_load_pdf_anota_pagina():
    docs = load_document(PDF)
    assert docs
    assert all(d.metadata["page"] >= 1 for d in docs)
    assert all(d.metadata["locator"].startswith("p. ") for d in docs)


def test_fragmentos_llevan_procedencia():
    docs = load_document(PDF, doc_id="abc123", filename="politicas.pdf")
    assert {d.metadata["doc_id"] for d in docs} == {"abc123"}
    assert {d.metadata["filename"] for d in docs} == {"politicas.pdf"}


def test_chunking_acota_el_tamano():
    docs = load_document(PDF)
    # el margen cubre el solapamiento del divisor
    assert max(len(d.page_content) for d in docs) <= 1100


def test_busqueda_devuelve_relevancia_normalizada():
    store = create_vector_store(load_document(CSV))
    resultados = search(store, "producto más vendido", k=3)
    assert len(resultados) == 3
    assert all(0.0 <= score <= 1.0 for _, score in resultados)
    # el más parecido va primero
    scores = [score for _, score in resultados]
    assert scores == sorted(scores, reverse=True)


def test_read_pages_para_el_visor():
    paginas = read_pages(PDF)
    assert paginas and isinstance(paginas[0], str)


def test_build_prompt_numera_los_fragmentos():
    from src.agent import build_prompt

    docs = load_document(CSV)[:2]
    prompt = build_prompt(docs, "¿cuánto se vendió?", history=[{"role": "user", "content": "hola"}])
    assert "[1]" in prompt and "[2]" in prompt
    assert "¿cuánto se vendió?" in prompt
    assert "hola" in prompt


def test_get_llm_sin_clave_falla(monkeypatch):
    from src.agent import get_llm

    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    with pytest.raises(ValueError):
        get_llm("gemini")


def test_formato_no_soportado():
    with pytest.raises(ValueError):
        load_document("archivo.docx")
