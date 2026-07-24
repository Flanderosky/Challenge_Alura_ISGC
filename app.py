"""
Aplicacion principal del Alura Agente.
Vista de flujo tipo n8n: nodos interactivos del pipeline RAG + chat lateral.
"""

import os
import tempfile
import time

import streamlit as st
from dotenv import load_dotenv

from src.loader import load_document
from src.vectorstore import create_vector_store
from src.agent import create_qa_chain, ask_question

load_dotenv()

st.set_page_config(
    page_title="Alura Agente | Pipeline RAG",
    layout="wide",
    initial_sidebar_state="collapsed",
)

DEFAULT_DOC = os.path.join("data", "politicas_ejemplo.pdf")

CUSTOM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}

/* Contenedor principal */
.main .block-container {
    padding: 1rem 2rem;
    max-width: 100%;
}

/* Nodos estilo n8n */
.node-container {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 0;
    padding: 1rem 0;
}

.node {
    background: #1e1e2e;
    border: 2px solid #3d3d5c;
    border-radius: 12px;
    padding: 0.8rem 1.2rem;
    min-width: 180px;
    text-align: center;
    color: #e0e0e8;
    font-size: 0.9rem;
    font-weight: 500;
    box-shadow: 0 4px 6px rgba(0,0,0,0.2);
    transition: all 0.3s ease;
    position: relative;
    z-index: 2;
}

.node-icon {
    font-size: 1.3rem;
    margin-bottom: 0.3rem;
}

.node-title {
    font-weight: 600;
    margin-bottom: 0.2rem;
}

.node-desc {
    font-size: 0.75rem;
    color: #9090a0;
}

.node.active {
    border-color: #00d4ff;
    box-shadow: 0 0 20px rgba(0, 212, 255, 0.4);
    background: #1a2a3a;
}

.node.success {
    border-color: #00d68f;
    box-shadow: 0 0 20px rgba(0, 214, 143, 0.3);
    background: #1a3a2e;
}

.connector {
    width: 2px;
    height: 24px;
    background: #3d3d5c;
    position: relative;
    z-index: 1;
    transition: all 0.3s ease;
}

.connector.active {
    background: linear-gradient(180deg, #00d4ff, #00d68f);
    box-shadow: 0 0 10px rgba(0, 212, 255, 0.5);
}

.flow-title {
    font-size: 1.1rem;
    font-weight: 600;
    color: #ffffff;
    margin-bottom: 1rem;
    padding-bottom: 0.5rem;
    border-bottom: 1px solid #2a2a3e;
}

.status-badge {
    display: inline-block;
    padding: 0.3rem 0.8rem;
    border-radius: 20px;
    font-size: 0.75rem;
    font-weight: 600;
    margin-top: 1rem;
}

.status-badge.idle {
    background: #2a2a3e;
    color: #9090a0;
}

.status-badge.processing {
    background: rgba(0, 212, 255, 0.15);
    color: #00d4ff;
}

.status-badge.ready {
    background: rgba(0, 214, 143, 0.15);
    color: #00d68f;
}

/* Panel derecho */
.chat-panel {
    background: #13131f;
    border-radius: 16px;
    border: 1px solid #2a2a3e;
    padding: 1.5rem;
    height: calc(100vh - 120px);
    display: flex;
    flex-direction: column;
}

.chat-header {
    font-size: 1.1rem;
    font-weight: 600;
    color: #ffffff;
    margin-bottom: 1rem;
    padding-bottom: 0.8rem;
    border-bottom: 1px solid #2a2a3e;
}

.info-card {
    background: #1e1e2e;
    border: 1px solid #2a2a3e;
    border-radius: 12px;
    padding: 1rem;
    margin-bottom: 1rem;
}

.info-card h4 {
    color: #00d4ff;
    margin: 0 0 0.5rem 0;
    font-size: 0.95rem;
}

.info-card p {
    color: #a0a0b0;
    margin: 0;
    font-size: 0.85rem;
}
</style>
"""

st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


# Nodos del flujo RAG
FLOW_NODES = [
    {"id": "input", "title": "Entrada", "desc": "Pregunta del usuario", "icon": "?"},
    {"id": "retriever", "title": "Retriever", "desc": "Busqueda semantica", "icon": "O"},
    {"id": "vectorstore", "title": "Vector Store", "desc": "FAISS + embeddings", "icon": "#"},
    {"id": "llm", "title": "LLM", "desc": "Gemini genera respuesta", "icon": "IA"},
    {"id": "output", "title": "Salida", "desc": "Respuesta final", "icon": ">>"},
]


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


def render_node(node, state="idle"):
    """Renderiza un nodo individual."""
    active_class = "active" if state == "active" else "success" if state == "success" else ""
    return f"""
    <div class="node {active_class}">
        <div class="node-title">{node['icon']} {node['title']}</div>
        <div class="node-desc">{node['desc']}</div>
    </div>
    """


def render_flow(active_node=None, completed_nodes=None):
    """Renderiza el diagrama completo de nodos."""
    completed_nodes = completed_nodes or []
    html = '<div class="node-container">'

    for i, node in enumerate(FLOW_NODES):
        if node["id"] == active_node:
            state = "active"
        elif node["id"] in completed_nodes:
            state = "success"
        else:
            state = "idle"

        html += render_node(node, state)

        if i < len(FLOW_NODES) - 1:
            connector_active = "active" if node["id"] in completed_nodes else ""
            html += f'<div class="connector {connector_active}"></div>'

    html += '</div>'
    return html


# Sidebar
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


# Header
st.markdown("""
<h1 style="color: white; margin-bottom: 0.2rem;">Alura Agente</h1>
<p style="color: #9090a0; margin-top: 0;">Pipeline RAG visual: consulta documentos y observa como fluye la informacion</p>
""", unsafe_allow_html=True)


# Layout principal
col_flow, col_chat = st.columns([1, 1])

# Columna izquierda: flujo de nodos
with col_flow:
    st.markdown('<div class="flow-title">Pipeline de procesamiento</div>', unsafe_allow_html=True)

    flow_placeholder = st.empty()
    status_placeholder = st.empty()

    # Render inicial
    flow_placeholder.markdown(render_flow(), unsafe_allow_html=True)
    status_placeholder.markdown(
        '<div class="status-badge idle">Esperando pregunta...</div>',
        unsafe_allow_html=True
    )

    # Info del documento
    st.markdown("""
    <div class="info-card">
        <h4>Documento cargado</h4>
        <p>Manual de Politicas Internas - AluraTech</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="info-card">
        <h4>Como funciona</h4>
        <p>1. Escribe una pregunta en el chat.<br>
        2. El retriever busca los fragmentos mas relevantes.<br>
        3. El vector store recupera el contexto.<br>
        4. Gemini genera una respuesta basada en el documento.</p>
    </div>
    """, unsafe_allow_html=True)


# Columna derecha: chat
with col_chat:
    st.markdown('<div class="chat-panel">', unsafe_allow_html=True)
    st.markdown('<div class="chat-header">Chat con el agente</div>', unsafe_allow_html=True)

    if "messages" not in st.session_state:
        st.session_state.messages = [
            {
                "role": "assistant",
                "content": "Hola. Soy tu asistente de documentos. Escribe una pregunta sobre politicas, ventas o tecnologia y observa como se procesa en el pipeline.",
            }
        ]

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    doc_path = get_document_path()

    if doc_path is None:
        st.warning("Sube un documento PDF o CSV desde la barra lateral.")
    else:
        try:
            qa_chain = build_qa_chain(doc_path)
        except ValueError as e:
            st.error(f"Error al configurar el modelo: {e}")
            st.stop()
        except Exception as e:
            st.error(f"Error al procesar el documento: {e}")
            st.stop()

        if question := st.chat_input("Escribe tu pregunta aqui..."):
            st.session_state.messages.append({"role": "user", "content": question})

            with st.chat_message("user"):
                st.markdown(question)

            # Animacion del flujo
            status_placeholder.markdown(
                '<div class="status-badge processing">Procesando pregunta...</div>',
                unsafe_allow_html=True
            )

            completed = []

            # Paso 1: Entrada activa
            flow_placeholder.markdown(render_flow(active_node="input", completed_nodes=completed), unsafe_allow_html=True)
            time.sleep(0.4)
            completed.append("input")

            # Paso 2: Retriever
            flow_placeholder.markdown(render_flow(active_node="retriever", completed_nodes=completed), unsafe_allow_html=True)
            time.sleep(0.6)
            completed.append("retriever")

            # Paso 3: Vector Store
            flow_placeholder.markdown(render_flow(active_node="vectorstore", completed_nodes=completed), unsafe_allow_html=True)
            time.sleep(0.6)
            completed.append("vectorstore")

            # Paso 4: LLM
            flow_placeholder.markdown(render_flow(active_node="llm", completed_nodes=completed), unsafe_allow_html=True)

            with st.chat_message("assistant"):
                try:
                    result = ask_question(qa_chain, question)
                    answer = result["answer"]
                    sources = result["sources"]
                except Exception as e:
                    st.error(f"Error al generar la respuesta: {e}")
                    flow_placeholder.markdown(render_flow(), unsafe_allow_html=True)
                    status_placeholder.markdown(
                        '<div class="status-badge idle">Error en el pipeline</div>',
                        unsafe_allow_html=True
                    )
                    st.stop()

                st.markdown(answer)

                if sources:
                    with st.expander("Ver fuentes consultadas"):
                        for i, source in enumerate(sources, 1):
                            st.markdown(f"**Fuente {i}:** {source}...")

            # Paso 5: Salida completada
            completed.append("llm")
            completed.append("output")
            flow_placeholder.markdown(render_flow(completed_nodes=completed), unsafe_allow_html=True)
            status_placeholder.markdown(
                '<div class="status-badge ready">Respuesta generada</div>',
                unsafe_allow_html=True
            )

            st.session_state.messages.append({"role": "assistant", "content": answer})

    st.markdown('</div>', unsafe_allow_html=True)
