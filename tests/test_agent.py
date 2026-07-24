"""
Pruebas del núcleo: carga, fragmentación, índice y construcción del prompt.
No requieren clave de API.
"""

import os

import pytest

from src.loader import load_document, read_pages
from src.vectorstore import create_vector_store, search

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
CSV = os.path.join(DATA_DIR, "pedidos_2026.csv")
PDF = os.path.join(DATA_DIR, "politica_devoluciones.pdf")
PRODUCTO = "Laptop Meridia Pro 14"


def test_load_csv_incluye_resumen_y_filas():
    docs = load_document(CSV)
    assert docs, "el CSV debería producir fragmentos"
    assert docs[0].metadata["unit"] == "summary"
    assert any(PRODUCTO in d.page_content for d in docs)


def test_csv_genera_desgloses_por_categoria():
    docs = load_document(CSV)
    desgloses = [d for d in docs if d.metadata["unit"] == "breakdown"]
    assert desgloses, "el CSV debería producir desgloses por columna categórica"

    texto = "\n".join(d.page_content for d in desgloses)
    # el desglose por producto es lo que permite sumar unidades de un producto
    assert PRODUCTO in texto
    assert "Mayor" in texto, "debería incluir el ranking explícito por métrica"
    assert any("desglose por" in d.metadata["locator"] for d in desgloses)


def test_desglose_ignora_columnas_identificador():
    import pandas as pd

    from src.loader import _csv_breakdowns

    df = pd.DataFrame({"id": [f"r{i}" for i in range(10)], "monto": range(10)})
    assert _csv_breakdowns(df, {"filename": "x.csv", "doc_id": "x"}) == []


def test_load_pdf_anota_pagina():
    docs = load_document(PDF)
    assert docs
    assert all(d.metadata["page"] >= 1 for d in docs)
    assert all(d.metadata["locator"].startswith("p. ") for d in docs)


def test_fragmentos_llevan_procedencia():
    docs = load_document(PDF, doc_id="abc123", filename="devoluciones.pdf")
    assert {d.metadata["doc_id"] for d in docs} == {"abc123"}
    assert {d.metadata["filename"] for d in docs} == {"devoluciones.pdf"}


def test_el_pdf_conserva_los_acentos():
    # las fuentes base del PDF son latin-1: si algo se rompe, se rompe aquí
    texto = " ".join(d.page_content for d in load_document(PDF))
    assert "días" in texto and "devolución" in texto


def test_chunking_acota_el_tamano():
    docs = load_document(PDF)
    # el margen cubre el solapamiento del divisor
    assert max(len(d.page_content) for d in docs) <= 1100


def test_busqueda_devuelve_relevancia_normalizada():
    store = create_vector_store(load_document(CSV))
    resultados = search(store, "categoría con más ingresos", k=3)
    assert len(resultados) == 3
    assert all(0.0 <= score <= 1.0 for _, score in resultados)
    # el más parecido va primero
    scores = [score for _, score in resultados]
    assert scores == sorted(scores, reverse=True)


def test_el_modelo_de_embeddings_coincide_con_el_dockerfile():
    # el Dockerfile precarga el modelo por nombre, antes de copiar el código
    from src.vectorstore import EMBEDDING_MODEL

    with open(os.path.join(os.path.dirname(__file__), "..", "Dockerfile"), encoding="utf-8") as f:
        assert EMBEDDING_MODEL in f.read(), "el Dockerfile precarga otro modelo distinto"


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
