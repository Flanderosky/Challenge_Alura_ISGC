"""
Carga y fragmentación de documentos (PDF y CSV).

Cada fragmento conserva de dónde salió (documento, página o fila) para que
la respuesta pueda citar la fuente exacta y la interfaz pueda resaltarla.
"""

import os
from typing import List, Optional

import pandas as pd
from langchain_community.document_loaders import PyPDFLoader
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

CHUNK_SIZE = 900
CHUNK_OVERLAP = 150
CSV_ROWS_PER_CHUNK = 8

_splitter = RecursiveCharacterTextSplitter(
    chunk_size=CHUNK_SIZE,
    chunk_overlap=CHUNK_OVERLAP,
    separators=["\n\n", "\n", ". ", " ", ""],
)


def _base_metadata(file_path: str, doc_id: Optional[str], filename: Optional[str]) -> dict:
    name = filename or os.path.basename(file_path)
    return {
        "doc_id": doc_id or name,
        "filename": name,
    }


def load_pdf(
    file_path: str,
    doc_id: Optional[str] = None,
    filename: Optional[str] = None,
) -> List[Document]:
    """Carga un PDF y lo divide en fragmentos, anotando la página de origen."""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"No se encontró el archivo: {file_path}")

    base = _base_metadata(file_path, doc_id, filename)
    pages = PyPDFLoader(file_path).load()

    chunks: List[Document] = []
    for page_index, page in enumerate(pages, start=1):
        text = page.page_content.strip()
        if not text:
            continue
        for piece in _splitter.split_text(text):
            chunks.append(
                Document(
                    page_content=piece,
                    metadata={
                        **base,
                        "unit": "page",
                        "page": page_index,
                        "locator": f"p. {page_index}",
                    },
                )
            )
    return chunks


def _csv_summary(df: pd.DataFrame, base: dict) -> Optional[Document]:
    """
    Documento sintético con los agregados del CSV.

    Sin esto, una búsqueda semántica fila por fila nunca puede responder
    "¿cuál fue el total de ventas?", porque ninguna fila contiene el total.
    """
    numeric = df.select_dtypes("number")
    if df.empty:
        return None

    lines = [
        f"Resumen del archivo {base['filename']}.",
        f"Contiene {len(df)} registros y {len(df.columns)} columnas: {', '.join(map(str, df.columns))}.",
    ]
    for column in numeric.columns:
        serie = numeric[column].dropna()
        if serie.empty:
            continue
        lines.append(
            f"Columna {column}: total {serie.sum():,.2f}, promedio {serie.mean():,.2f}, "
            f"mínimo {serie.min():,.2f}, máximo {serie.max():,.2f}."
        )
    for column in (c for c in df.columns if c not in numeric.columns):
        top = df[column].value_counts().head(3)
        if top.empty:
            continue
        detalle = ", ".join(f"{valor} ({conteo})" for valor, conteo in top.items())
        lines.append(f"Valores más frecuentes en {column}: {detalle}.")

    return Document(
        page_content="\n".join(lines),
        metadata={**base, "unit": "summary", "page": 1, "locator": "resumen"},
    )


def load_csv(
    file_path: str,
    doc_id: Optional[str] = None,
    filename: Optional[str] = None,
) -> List[Document]:
    """Carga un CSV en bloques de filas, más un fragmento de agregados."""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"No se encontró el archivo: {file_path}")

    base = _base_metadata(file_path, doc_id, filename)
    df = pd.read_csv(file_path)

    chunks: List[Document] = []
    summary = _csv_summary(df, base)
    if summary is not None:
        chunks.append(summary)

    for start in range(0, len(df), CSV_ROWS_PER_CHUNK):
        block = df.iloc[start : start + CSV_ROWS_PER_CHUNK]
        filas = [
            ". ".join(f"{col}: {row[col]}" for col in df.columns)
            for _, row in block.iterrows()
        ]
        primera, ultima = start + 1, start + len(block)
        chunks.append(
            Document(
                page_content="\n".join(filas),
                metadata={
                    **base,
                    "unit": "rows",
                    "page": start // CSV_ROWS_PER_CHUNK + 1,
                    "row_start": primera,
                    "row_end": ultima,
                    "locator": f"filas {primera}–{ultima}",
                },
            )
        )
    return chunks


def load_document(
    file_path: str,
    doc_id: Optional[str] = None,
    filename: Optional[str] = None,
) -> List[Document]:
    """Carga un documento PDF o CSV según su extensión."""
    ext = os.path.splitext(filename or file_path)[1].lower()
    if ext == ".pdf":
        return load_pdf(file_path, doc_id, filename)
    if ext == ".csv":
        return load_csv(file_path, doc_id, filename)
    raise ValueError(f"Formato no soportado: {ext}. Usa .pdf o .csv")


def read_pages(file_path: str, filename: Optional[str] = None) -> List[str]:
    """Devuelve el texto de cada página (PDF) o bloque de filas (CSV), para el visor."""
    ext = os.path.splitext(filename or file_path)[1].lower()
    if ext == ".pdf":
        return [page.page_content for page in PyPDFLoader(file_path).load()]
    if ext == ".csv":
        df = pd.read_csv(file_path)
        paginas = []
        for start in range(0, len(df), CSV_ROWS_PER_CHUNK):
            block = df.iloc[start : start + CSV_ROWS_PER_CHUNK]
            paginas.append(
                "\n".join(
                    ". ".join(f"{col}: {row[col]}" for col in df.columns)
                    for _, row in block.iterrows()
                )
            )
        return paginas
    raise ValueError(f"Formato no soportado: {ext}")
