"""
Agente de preguntas y respuestas sobre los documentos indexados.

Las etapas (recuperación y generación) están separadas a propósito: así la
interfaz puede medir y mostrar lo que realmente tarda cada una, en vez de
simular el progreso.
"""

import os
from typing import Iterable, Iterator, List, Optional, Sequence, Tuple

from dotenv import load_dotenv
from langchain_core.documents import Document

from src.vectorstore import search

load_dotenv()

MAX_HISTORY_TURNS = 6


_clientes: dict = {}


def get_llm(provider: Optional[str] = None):
    """
    Cliente del modelo de lenguaje según el proveedor configurado.

    Se reutiliza entre consultas: construirlo cuesta un par de segundos que,
    si no, se cargaban al tiempo total de cada pregunta.
    """
    provider = (provider or os.getenv("LLM_PROVIDER", "gemini")).lower()
    clave = (provider, os.getenv("GOOGLE_API_KEY"), os.getenv("COHERE_API_KEY"),
             os.getenv("OPENAI_API_KEY"), model_name(provider))

    if clave not in _clientes:
        _clientes[clave] = _build_llm(provider)
    return _clientes[clave]


def _build_llm(provider: str):
    if provider == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI

        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("Falta GOOGLE_API_KEY en las variables de entorno.")
        model = os.getenv("GOOGLE_MODEL", "gemini-3.1-flash-lite")
        return ChatGoogleGenerativeAI(google_api_key=api_key, model=model, temperature=0.3)

    if provider == "cohere":
        from langchain_cohere import ChatCohere

        api_key = os.getenv("COHERE_API_KEY")
        if not api_key:
            raise ValueError("Falta COHERE_API_KEY en las variables de entorno.")
        model = os.getenv("COHERE_MODEL", "command-r")
        return ChatCohere(cohere_api_key=api_key, model=model, temperature=0.3)

    if provider == "openai":
        from langchain_openai import ChatOpenAI

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("Falta OPENAI_API_KEY en las variables de entorno.")
        model = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
        return ChatOpenAI(openai_api_key=api_key, model=model, temperature=0.3)

    raise ValueError(f"Proveedor de LLM no soportado: {provider}")


def model_name(provider: Optional[str] = None) -> str:
    """Nombre del modelo activo, para mostrarlo en la interfaz."""
    provider = (provider or os.getenv("LLM_PROVIDER", "gemini")).lower()
    return {
        "gemini": os.getenv("GOOGLE_MODEL", "gemini-3.1-flash-lite"),
        "cohere": os.getenv("COHERE_MODEL", "command-r"),
        "openai": os.getenv("OPENAI_MODEL", "gpt-3.5-turbo"),
    }.get(provider, provider)


_SYSTEM = """Eres el asistente de atención al cliente de Meridia, una tienda en línea. Respondes únicamente con lo que dicen los fragmentos numerados que recibes.

Reglas:
- Cita la fuente con [n] al final de cada afirmación que la use. Usa el número del fragmento.
- Si los fragmentos no contienen la respuesta, dilo en una frase y señala qué documento haría falta. No completes con conocimiento propio.
- No inventes cifras, fechas ni nombres.
- Si un fragmento se declara parcial, no deduzcas de él máximos, mínimos ni totales: usa el fragmento de comparativa, y si no está, dilo.
- Responde en español, directo, sin preámbulos."""


def build_prompt(
    fragments: Sequence[Document],
    question: str,
    history: Optional[Iterable[dict]] = None,
) -> str:
    """Arma el prompt con los fragmentos numerados y el historial reciente."""
    bloques = [
        f"[{i}] ({frag.metadata.get('filename', 'documento')}, "
        f"{frag.metadata.get('locator', 's/n')})\n{frag.page_content}"
        for i, frag in enumerate(fragments, start=1)
    ]

    partes = [_SYSTEM, "", "Fragmentos:", "\n\n".join(bloques) or "(sin fragmentos)"]

    turnos = list(history or [])[-MAX_HISTORY_TURNS:]
    if turnos:
        partes += [
            "",
            "Conversación previa (para resolver referencias como «eso» o «y entonces»):",
            "\n".join(
                f"{'Usuario' if t.get('role') == 'user' else 'Asistente'}: {t.get('content', '')}"
                for t in turnos
            ),
        ]

    partes += ["", f"Pregunta: {question}", "", "Respuesta:"]
    return "\n".join(partes)


def retrieve(vector_store, question: str, k: int = 4) -> List[Tuple[Document, float]]:
    """Recupera los fragmentos más relevantes con su puntuación."""
    return search(vector_store, question, k=k)


def _as_text(content) -> str:
    """
    Normaliza el contenido de un fragmento del stream.

    Gemini entrega listas de bloques y no cadenas; el resto de proveedores
    entrega texto plano.
    """
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(
            parte if isinstance(parte, str) else str(parte.get("text", ""))
            for parte in content
            if isinstance(parte, (str, dict))
        )
    return ""


def stream_answer(llm, prompt: str) -> Iterator[str]:
    """Genera la respuesta token a token."""
    for chunk in llm.stream(prompt):
        texto = _as_text(getattr(chunk, "content", ""))
        if texto:
            yield texto


def answer_question(
    vector_store,
    question: str,
    k: int = 4,
    history: Optional[Iterable[dict]] = None,
    llm=None,
) -> dict:
    """Respuesta completa en una sola llamada. Útil para pruebas y uso por script."""
    fragments = retrieve(vector_store, question, k=k)
    prompt = build_prompt([doc for doc, _ in fragments], question, history)
    llm = llm or get_llm()
    respuesta = "".join(stream_answer(llm, prompt))
    return {
        "answer": respuesta,
        "sources": [
            {
                "filename": doc.metadata.get("filename"),
                "locator": doc.metadata.get("locator"),
                "score": score,
                "text": doc.page_content,
            }
            for doc, score in fragments
        ],
    }
