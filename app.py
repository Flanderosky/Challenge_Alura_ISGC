"""
Aplicación principal del Alura Agente.
Interfaz web futurista con chatbot integrado para consultar documentos.
"""

import os
import tempfile

import streamlit as st
from dotenv import load_dotenv

from src.loader import load_document
from src.vectorstore import create_vector_store
from src.agent import create_qa_chain, ask_question

load_dotenv()

st.set_page_config(
    page_title="Alura Agente | Consulta Inteligente de Documentos",
    layout="wide",
    initial_sidebar_state="collapsed",
)

DEFAULT_DOC = os.path.join("data", "ventas_ejemplo.pdf")

CUSTOM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&family=Orbitron:wght@500;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}

h1, h2, h3, .orbitron {
    font-family: 'Orbitron', sans-serif;
}

.hero {
    text-align: center;
    padding: 4rem 1rem 3rem 1rem;
    background: radial-gradient(circle at top center, #1a1a2e 0%, #0a0a12 70%);
    border-bottom: 1px solid #222;
}

.hero h1 {
    font-size: 3.2rem;
    font-weight: 700;
    color: #ffffff;
    margin-bottom: 0.5rem;
    letter-spacing: -1px;
}

.hero .gradient-text {
    background: linear-gradient(90deg, #00d4ff, #7b2cbf);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}

.hero p {
    font-size: 1.2rem;
    color: #a0a0b0;
    max-width: 700px;
    margin: 0 auto;
}

.card {
    background: rgba(255, 255, 255, 0.03);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 16px;
    padding: 1.5rem;
    transition: transform 0.2s ease, border-color 0.2s ease;
}

.card:hover {
    transform: translateY(-4px);
    border-color: #00d4ff;
}

.card h4 {
    color: #00d4ff;
    margin-bottom: 0.5rem;
}

.card p {
    color: #c0c0d0;
    font-size: 0.95rem;
    margin: 0;
}

.section-title {
    font-size: 1.8rem;
    color: #ffffff;
    margin-bottom: 1rem;
    border-left: 4px solid #00d4ff;
    padding-left: 1rem;
}

.chat-welcome {
    background: rgba(0, 212, 255, 0.08);
    border-left: 3px solid #00d4ff;
    padding: 1rem;
    border-radius: 0 12px 12px 0;
    margin-bottom: 1rem;
}

.footer {
    text-align: center;
    padding: 2rem 1rem;
    color: #666;
    font-size: 0.85rem;
    border-top: 1px solid #1a1a2e;
    margin-top: 3rem;
}

.stButton button {
    background: linear-gradient(90deg, #00d4ff, #7b2cbf);
    color: white;
    border: none;
    border-radius: 8px;
    padding: 0.6rem 1.5rem;
    font-weight: 600;
}

.stButton button:hover {
    opacity: 0.9;
}
</style>
"""

st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


@st.cache_resource(show_spinner="Indexando documentos...")
def build_qa_chain(file_path: str):
    """Carga el documento, crea el vector store y la cadena QA."""
    documents = load_document(file_path)
    vector_store = create_vector_store(documents)
    return create_qa_chain(vector_store)


def get_document_path():
    """Determina la ruta del documento a utilizar."""
    uploaded_file = st.session_state.get("uploaded_file")
    if uploaded_file:
        suffix = os.path.splitext(uploaded_file.name)[1]
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(uploaded_file.getvalue())
            return tmp.name
    if os.path.exists(DEFAULT_DOC):
        return DEFAULT_DOC
    return None


# Sidebar con carga de documentos
with st.sidebar:
    st.header("Configuracion")
    st.markdown("Carga un documento PDF o CSV para personalizar el agente.")
    uploaded_file = st.file_uploader(
        "Sube un archivo PDF o CSV", type=["pdf", "csv"], key="uploaded_file"
    )

    if uploaded_file:
        st.success(f"Archivo cargado: {uploaded_file.name}")
    elif os.path.exists(DEFAULT_DOC):
        st.info(f"Documento por defecto: {DEFAULT_DOC}")

    st.divider()
    st.markdown("### Proveedores de IA soportados")
    st.markdown("- Google Gemini")
    st.markdown("- Cohere")
    st.markdown("- OpenAI")


# Hero section
st.markdown("""
<div class="hero">
    <h1>Alura <span class="gradient-text">Agente</span></h1>
    <p>Consulta documentos internos de tu empresa con inteligencia artificial. 
    Politicas, manuales, reportes y hojas de calculo resumidos en segundos.</p>
</div>
""", unsafe_allow_html=True)


# Seccion de capacidades
st.markdown("<div class='section-title'>Que puedes consultar</div>", unsafe_allow_html=True)

col1, col2, col3 = st.columns(3)
with col1:
    st.markdown("""
    <div class="card">
        <h4>Politicas internas</h4>
        <p>Vacaciones, horarios, codigos de conducta y beneficios del equipo.</p>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown("""
    <div class="card">
        <h4>Datos de ventas</h4>
        <p>Productos mas vendidos, ingresos por region y tendencias mensuales.</p>
    </div>
    """, unsafe_allow_html=True)

with col3:
    st.markdown("""
    <div class="card">
        <h4>Documentacion tecnica</h4>
        <p>Lenguajes, herramientas, arquitectura y procesos del equipo de tecnologia.</p>
    </div>
    """, unsafe_allow_html=True)


# Seccion de documentacion / fuentes
st.markdown("<div class='section-title'>Documentacion disponible</div>", unsafe_allow_html=True)

st.markdown("""
<div class="card">
    <h4>Manual de Politicas Internas - AluraTech</h4>
    <p>Contiene informacion sobre vacaciones, horario laboral, tecnologias utilizadas y codigo de conducta.</p>
</div>
""", unsafe_allow_html=True)

st.markdown("""
<div class="card" style="margin-top: 1rem;">
    <h4>Reporte de Ventas - Diciembre 2015</h4>
    <p>Registro de productos vendidos, categorias, regiones y montos de ingreso.</p>
</div>
""", unsafe_allow_html=True)


# Chatbot
st.markdown("<div class='section-title'>Habla con el agente</div>", unsafe_allow_html=True)

# Inicializar historial de chat
if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": "Hola, soy tu asistente virtual. Puedo ayudarte a consultar documentos internos de la empresa. Escribe una pregunta sobre politicas, ventas o tecnologia y te respondo con base en la documentacion.",
        }
    ]

# Mostrar mensajes
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Procesar documento
doc_path = get_document_path()

if doc_path is None:
    st.warning("Por favor sube un documento PDF o CSV para comenzar.")
else:
    try:
        qa_chain = build_qa_chain(doc_path)
    except ValueError as e:
        st.error(f"Error al configurar el modelo: {e}")
        st.stop()
    except Exception as e:
        st.error(f"Error al procesar el documento: {e}")
        st.stop()

    # Input de chat
    if question := st.chat_input("Escribe tu pregunta aqui..."):
        st.session_state.messages.append({"role": "user", "content": question})

        with st.chat_message("user"):
            st.markdown(question)

        with st.chat_message("assistant"):
            with st.spinner("Analizando documentos..."):
                try:
                    result = ask_question(qa_chain, question)
                    answer = result["answer"]
                    sources = result["sources"]
                except Exception as e:
                    st.error(f"Error al generar la respuesta: {e}")
                    st.stop()

            st.markdown(answer)

            if sources:
                with st.expander("Ver fuentes consultadas"):
                    for i, source in enumerate(sources, 1):
                        st.markdown(f"**Fuente {i}:** {source}...")

        st.session_state.messages.append({"role": "assistant", "content": answer})


# Footer
st.markdown("""
<div class="footer">
    Alura Agente - Desafio final Alura | Desplegado en Oracle Cloud Infrastructure
</div>
""", unsafe_allow_html=True)
