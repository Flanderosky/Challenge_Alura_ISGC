"""
Módulo del agente de IA.
Configura el LLM y la cadena de preguntas y respuestas con RAG.
"""

import os
from typing import Optional

from dotenv import load_dotenv
from langchain.schema import Document
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate
from langchain_community.vectorstores import FAISS

load_dotenv()


def get_llm(provider: Optional[str] = None):
    """Instancia el modelo de lenguaje según el proveedor configurado."""
    provider = (provider or os.getenv("LLM_PROVIDER", "cohere")).lower()

    if provider == "cohere":
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


def create_qa_chain(vector_store: FAISS, llm=None):
    """Crea la cadena de QA con RAG usando el vector store."""
    if llm is None:
        llm = get_llm()

    prompt = PromptTemplate(
        template=_CUSTOM_PROMPT,
        input_variables=["context", "question"],
    )

    qa_chain = RetrievalQA.from_chain_type(
        llm=llm,
        chain_type="stuff",
        retriever=vector_store.as_retriever(search_kwargs={"k": 4}),
        return_source_documents=True,
        chain_type_kwargs={"prompt": prompt},
    )
    return qa_chain


def ask_question(qa_chain, question: str) -> dict:
    """Ejecuta una pregunta sobre la cadena QA y devuelve la respuesta y fuentes."""
    result = qa_chain.invoke({"query": question})
    return {
        "answer": result.get("result", ""),
        "sources": [doc.page_content[:200] for doc in result.get("source_documents", [])],
    }
