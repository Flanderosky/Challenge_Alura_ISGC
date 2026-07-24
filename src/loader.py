"""
Módulo de carga de documentos.
Soporta archivos PDF y CSV.
"""

import os
from typing import List, Union

import pandas as pd
from langchain_core.documents import Document
from langchain_community.document_loaders import PyPDFLoader


def load_pdf(file_path: str) -> List[Document]:
    """Carga un archivo PDF y lo divide en páginas."""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"No se encontró el archivo: {file_path}")

    loader = PyPDFLoader(file_path)
    return loader.load()


def load_csv(file_path: str) -> List[Document]:
    """Carga un archivo CSV y convierte cada fila en un Document."""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"No se encontró el archivo: {file_path}")

    df = pd.read_csv(file_path)
    documents = []
    for _, row in df.iterrows():
        text = ". ".join([f"{col}: {row[col]}" for col in df.columns])
        documents.append(Document(page_content=text, metadata={"source": file_path}))
    return documents


def load_document(file_path: str) -> List[Document]:
    """Carga un documento PDF o CSV según su extensión."""
    ext = os.path.splitext(file_path)[1].lower()
    if ext == ".pdf":
        return load_pdf(file_path)
    elif ext == ".csv":
        return load_csv(file_path)
    else:
        raise ValueError(f"Formato no soportado: {ext}. Usa .pdf o .csv")
