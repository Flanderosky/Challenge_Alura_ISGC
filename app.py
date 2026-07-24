"""
Aplicación principal del Alura Agente.
Interfaz web construida con Streamlit.
"""

import os
import tempfile

import streamlit as st
from dotenv import load_dotenv

from src.loader import load_document
from src.vectorstore import create_vector_store
from src.agent import create_qa_chain, ask_question

load_dotenv()

st.set_page_config(page_title="Alura Agente", layout="wide")

st.title("Alura Agente")
st.markdown(
    "Asistente de inteligencia artificial para responder preguntas sobre documentos internos (PDF o CSV)."
)

# Documento por defecto
DEFAULT_DOC = os.path.join("data", "ventas_ejemplo.csv")

# Sidebar: carga de documento
with st.sidebar:
    st.header("Documento fuente")
    uploaded_file = st.file_uploader(
        "Sube un archivo PDF o CSV", type=["pdf", "csv"]
    )

    if uploaded_file:
        st.success(f"Archivo cargado: {uploaded_file.name}")
    elif os.path.exists(DEFAULT_DOC):
        st.info(f"Usando documento por defecto: {DEFAULT_DOC}")

    st.divider()
    st.markdown("### Ejemplos de preguntas")
    st.markdown("- ¿Cuál fue el producto más vendido en diciembre de 2015?")
    st.markdown("- ¿Cuál es la política de vacaciones de la empresa?")
    st.markdown("- Resume los puntos más importantes del documento.")


@st.cache_resource(show_spinner="Procesando documento...")
def build_qa_chain(file_path: str):
    """Carga el documento, crea el vector store y la cadena QA."""
    documents = load_document(file_path)
    vector_store = create_vector_store(documents)
    return create_qa_chain(vector_store)


def get_document_path():
    """Determina la ruta del documento a utilizar."""
    if uploaded_file:
        suffix = os.path.splitext(uploaded_file.name)[1]
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(uploaded_file.getvalue())
            return tmp.name
    if os.path.exists(DEFAULT_DOC):
        return DEFAULT_DOC
    return None


doc_path = get_document_path()

if doc_path is None:
    st.warning("Por favor sube un documento PDF o CSV para comenzar.")
    st.stop()

try:
    qa_chain = build_qa_chain(doc_path)
except ValueError as e:
    st.error(f"Error al configurar el modelo: {e}")
    st.stop()
except Exception as e:
    st.error(f"Error al procesar el documento: {e}")
    st.stop()

st.success("Documento procesado correctamente. Haz una pregunta.")

# Área de preguntas
question = st.text_input("Escribe tu pregunta aquí:", placeholder="¿Qué necesitas saber?")

if question:
    with st.spinner("Buscando la mejor respuesta..."):
        try:
            result = ask_question(qa_chain, question)
        except Exception as e:
            st.error(f"Error al generar la respuesta: {e}")
            st.stop()

    st.markdown("### Respuesta")
    st.write(result["answer"])

    with st.expander("Ver contexto utilizado"):
        for i, source in enumerate(result["sources"], 1):
            st.markdown(f"**Fragmento {i}:** {source}...")
