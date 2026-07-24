"""
Módulo del agente de IA.
Configura el LLM y la cadena de preguntas y respuestas con RAG.
"""

import os
from typing import Optional

from dotenv import load_dotenv
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnableParallel, RunnablePassthrough
from langchain_community.vectorstores import FAISS

load_dotenv()


def get_llm(provider: Optional[str] = None):
    """Instancia el modelo de lenguaje según el proveedor configurado."""
    provider = (provider or os.getenv("LLM_PROVIDER", "gemini")).lower()

    if provider == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("Falta GOOGLE_API_KEY en las variables de entorno.")
        model = os.getenv("GOOGLE_MODEL", "gemini-1.5-flash")
        return ChatGoogleGenerativeAI(google_api_key=api_key, model=model, temperature=0.3)

    elif provider == "cohere":
        from langchain_cohere import ChatCohere
        api_key = os.getenv("COHERE_API_KEY")
        if not api_key:
            raise ValueError("Falta COHERE_API_KEY en las variables de entorno.")
        model = os.getenv("COHERE_MODEL", "command-r")
        return ChatCohere(cohere_api_key=api_key, model=model, temperature=0.3)

    elif provider == "openai":
        from langchain_openai import ChatOpenAI
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("Falta OPENAI_API_KEY en las variables de entorno.")
        model = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
        return ChatOpenAI(openai_api_key=api_key, model=model, temperature=0.3)

    else:
        raise ValueError(f"Proveedor de LLM no soportado: {provider}")


_CUSTOM_PROMPT = """Eres un asistente experto que responde preguntas basándote únicamente en el contexto proporcionado.
Si no encuentras la respuesta en el contexto, di honestamente que no lo sabes.
No inventes información.

Contexto:
{context}

Pregunta: {question}

Respuesta útil y directa:"""


def _format_docs(docs):
    """Une los documentos recuperados en un solo texto."""
    return "\n\n".join(doc.page_content for doc in docs)


def create_qa_chain(vector_store: FAISS, llm=None):
    """Crea la cadena de QA con RAG usando el vector store."""
    if llm is None:
        llm = get_llm()

    retriever = vector_store.as_retriever(search_kwargs={"k": 4})

    prompt = PromptTemplate(
        template=_CUSTOM_PROMPT,
        input_variables=["context", "question"],
    )

    # Cadena que genera la respuesta
    answer_chain = (
        {"context": retriever | _format_docs, "question": RunnablePassthrough()}
        | prompt
        | llm
        | StrOutputParser()
    )

    # Cadena que también devuelve los documentos fuente
    rag_chain = RunnableParallel(
        {
            "answer": answer_chain,
            "sources": retriever,
        }
    )

    return rag_chain


def ask_question(rag_chain, question: str) -> dict:
    """Ejecuta una pregunta sobre la cadena RAG y devuelve la respuesta y fuentes."""
    result = rag_chain.invoke(question)
    return {
        "answer": result.get("answer", ""),
        "sources": [doc.page_content[:300] for doc in result.get("sources", [])],
    }
