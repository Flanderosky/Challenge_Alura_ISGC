"""
Carga y fragmentación de documentos (PDF y CSV).

Cada fragmento conserva de dónde salió (documento, página o fila) para que
la respuesta pueda citar la fuente exacta y la interfaz pueda resaltarla.
"""

import os
import re
from collections import Counter
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


LINEAS_CABECERA = 3
LINEAS_PIE = 2


def _sin_membrete(paginas: List[str]) -> List[str]:
    """
    Quita el encabezado y el pie que se repiten en todas las páginas.

    Al extraer un PDF, el membrete entra como texto normal y se cuela en cada
    fragmento. Eso diluye el vector: un fragmento sobre plazos de devolución
    acaba pareciéndose a cualquier otro del mismo documento, y el que lleva la
    respuesta deja de ganar la búsqueda.

    Solo se miran las primeras y últimas líneas de cada página, y los números
    se ignoran al comparar para que "página 1" y "página 2" cuenten como la
    misma línea.
    """
    if len(paginas) < 2:
        return paginas

    normalizar = lambda linea: re.sub(r"\d+", "#", linea.strip())
    lineas_por_pagina = [pagina.split("\n") for pagina in paginas]

    repetidas: Counter = Counter()
    for lineas in lineas_por_pagina:
        candidatas = lineas[:LINEAS_CABECERA] + lineas[-LINEAS_PIE:]
        for linea in {normalizar(l) for l in candidatas if l.strip()}:
            repetidas[linea] += 1

    umbral = max(2, len(paginas) * 0.6)
    membrete = {texto for texto, veces in repetidas.items() if veces >= umbral}
    if not membrete:
        return paginas

    limpias = []
    for lineas in lineas_por_pagina:
        bordes = set(range(LINEAS_CABECERA)) | set(range(len(lineas) - LINEAS_PIE, len(lineas)))
        limpias.append(
            "\n".join(
                linea
                for i, linea in enumerate(lineas)
                if not (i in bordes and normalizar(linea) in membrete)
            )
        )
    return limpias


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
    pages = _sin_membrete([p.page_content for p in PyPDFLoader(file_path).load()])

    chunks: List[Document] = []
    for page_index, text in enumerate(pages, start=1):
        text = text.strip()
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


MAX_CATEGORIAS = 40
TOP_CATEGORIAS = 25


def _es_fecha(serie: pd.Series) -> bool:
    """Decide si una columna se puede tratar como fecha sin romperse en el intento."""
    if serie.dtype.kind == "M":
        return True
    muestra = serie.dropna().astype(str).head(60)
    if muestra.empty:
        return False
    try:
        parsed = pd.to_datetime(muestra, errors="coerce", format="mixed")
    except (ValueError, TypeError):
        return False
    return bool(parsed.notna().mean() > 0.8)


def _metricas(sub: pd.DataFrame, numericas: List[str]) -> str:
    partes = [f"{len(sub)} registros"]
    for col in numericas:
        serie = sub[col].dropna()
        if serie.empty:
            continue
        partes.append(f"{col}: total {serie.sum():,.2f}, promedio {serie.mean():,.2f}")
    return ", ".join(partes)


def _desglose(
    df: pd.DataFrame,
    columna: str,
    etiquetas: pd.Series,
    numericas: List[str],
    base: dict,
    titulo: str,
) -> List[Document]:
    """
    Un fragmento con el desglose de las métricas por cada valor de `columna`.

    Es lo que permite responder "¿cuántas unidades de Monitor 27 se vendieron?"
    o "¿qué región generó más ingresos?": ninguna fila suelta contiene esa suma.
    """
    grupos = list(df.groupby(etiquetas, sort=False))
    if len(grupos) > MAX_CATEGORIAS:
        conteos = etiquetas.value_counts().head(TOP_CATEGORIAS)
        conservados = set(conteos.index)
        grupos = [(k, v) for k, v in grupos if k in conservados]
        nota = f" Se listan los {len(grupos)} valores más frecuentes de {columna}."
    else:
        nota = ""

    if not grupos:
        return []

    documentos: List[Document] = []

    # El ranking va en su propio fragmento, calculado sobre TODOS los grupos.
    # Si viviera dentro del listado, al partirse en varios trozos el modelo
    # podría deducir el máximo de una lista incompleta y acertar por poco.
    comparativa = []

    # "el más frecuente" es la pregunta más común sobre una columna categórica,
    # y no se responde con las métricas numéricas: hay que rankear por conteo
    conteos = {etiqueta: len(sub) for etiqueta, sub in grupos}
    if len(conteos) > 1:
        frecuente = max(conteos, key=conteos.__getitem__)
        raro = min(conteos, key=conteos.__getitem__)
        comparativa.append(
            f"El valor más frecuente de {columna} es {frecuente}, con {conteos[frecuente]} "
            f"registros. El menos frecuente es {raro}, con {conteos[raro]}."
        )

    for col in numericas:
        totales = {etiqueta: sub[col].dropna().sum() for etiqueta, sub in grupos}
        totales = {k: v for k, v in totales.items() if pd.notna(v)}
        if len(totales) < 2:
            continue
        mayor = max(totales, key=totales.__getitem__)
        menor = min(totales, key=totales.__getitem__)
        comparativa.append(
            f"Mayor {col} por {columna}: {mayor} ({totales[mayor]:,.2f}). "
            f"Menor {col} por {columna}: {menor} ({totales[menor]:,.2f})."
        )

    detalle = "\n".join(f"{etiqueta}: {_metricas(sub, numericas)}." for etiqueta, sub in grupos)
    trozos = _splitter.split_text(detalle)

    # Si el listado entero cabe en un fragmento, ranking y detalle van juntos:
    # separarlos duplicaría fragmentos casi idénticos que compiten entre sí en
    # la búsqueda y desplazan al contenido real de la biblioteca.
    if len(trozos) <= 1:
        cuerpo = [f"{titulo} en {base['filename']}.{nota}"]
        cuerpo += comparativa
        cuerpo += trozos
        return [
            Document(
                page_content="\n".join(cuerpo),
                metadata={**base, "unit": "breakdown", "page": 1, "locator": f"desglose por {columna}"},
            )
        ]

    if comparativa:
        documentos.append(
            Document(
                page_content=f"Comparativa de {columna} en {base['filename']}, "
                f"sobre {len(grupos)} valores.{nota}\n" + "\n".join(comparativa),
                metadata={**base, "unit": "breakdown", "page": 1, "locator": f"comparativa por {columna}"},
            )
        )

    for i, trozo in enumerate(trozos, start=1):
        encabezado = (
            f"{titulo} en {base['filename']}.{nota}"
            f" Listado parcial, parte {i} de {len(trozos)}: no contiene todos los valores, "
            f"por lo que no sirve para deducir máximos ni totales."
        )
        documentos.append(
            Document(
                page_content=f"{encabezado}\n{trozo}",
                metadata={**base, "unit": "breakdown", "page": 1, "locator": f"desglose por {columna}"},
            )
        )

    return documentos


def _csv_breakdowns(df: pd.DataFrame, base: dict) -> List[Document]:
    """Desgloses por cada columna categórica manejable y por mes si hay fechas."""
    numericas = list(df.select_dtypes("number").columns)
    if df.empty or not numericas:
        return []

    documentos: List[Document] = []
    for columna in df.columns:
        if columna in numericas:
            continue
        serie = df[columna]

        if _es_fecha(serie):
            fechas = pd.to_datetime(serie, errors="coerce", format="mixed")
            if fechas.notna().sum() < 2:
                continue
            documentos += _desglose(
                df, columna, fechas.dt.to_period("M").astype(str), numericas, base,
                f"Desglose por mes según {columna}",
            )
            continue

        distintos = serie.nunique(dropna=True)
        # una columna con un valor por fila es un identificador: no agrupa nada
        if distintos < 2 or distintos == len(df):
            continue
        documentos += _desglose(
            df, columna, serie.astype(str), numericas, base, f"Desglose por {columna}"
        )

    return documentos


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
        f"Resumen general y totales del archivo {base['filename']}.",
        f"Contiene {len(df)} registros y {len(df.columns)} columnas: {', '.join(map(str, df.columns))}.",
    ]
    for column in numeric.columns:
        serie = numeric[column].dropna()
        if serie.empty:
            continue
        # el "total general de X" explícito es lo que engancha la pregunta
        # "¿cuál fue el total de X?", que no coincide con ninguna fila
        lines.append(
            f"Total general de {column}, sumando todos los registros: {serie.sum():,.2f}. "
            f"Promedio de {column}: {serie.mean():,.2f}. "
            f"Mínimo: {serie.min():,.2f}. Máximo: {serie.max():,.2f}."
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
    """Carga un CSV en bloques de filas, más los agregados y desgloses calculados."""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"No se encontró el archivo: {file_path}")

    base = _base_metadata(file_path, doc_id, filename)
    df = pd.read_csv(file_path)

    chunks: List[Document] = []
    summary = _csv_summary(df, base)
    if summary is not None:
        chunks.append(summary)
    chunks.extend(_csv_breakdowns(df, base))

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
        # el visor muestra el mismo texto que se indexó, para que el resaltado cuadre
        return _sin_membrete([page.page_content for page in PyPDFLoader(file_path).load()])
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
