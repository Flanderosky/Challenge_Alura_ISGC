"""
API del agente documental de Meridia.

/api/query devuelve un flujo de eventos (SSE) con lo que va ocurriendo de
verdad en el pipeline: cuánto tardó cada etapa, qué fragmentos se recuperaron
y con qué relevancia, y la respuesta token a token.
"""

import json
import os
import threading
import time
from contextlib import asynccontextmanager
from typing import AsyncIterator, Iterator, List, Optional

from fastapi import Depends, FastAPI, File, HTTPException, Request, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from api.auth import expected_token, require_write_token, write_protected
from api.limites import cache, cuota, limite_ip
from api.store import LibraryError, library
from src.agent import build_prompt, get_llm, model_name, stream_answer
from src.vectorstore import embed_query, search_by_vector

WEB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "web")
TOP_K = 6

def _warmup_llm() -> None:
    """
    Construye el cliente del modelo al arrancar.

    Cuesta un par de segundos y, si no se hace aquí, se los cobra a la primera
    pregunta del usuario.
    """
    try:
        get_llm()
    except Exception:
        pass  # sin clave configurada: el error se reporta al consultar


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """El índice y el cliente del modelo se calientan en segundo plano."""
    library.build_index_async()
    threading.Thread(target=_warmup_llm, daemon=True).start()
    yield


# Sin CORS a propósito: el front se sirve desde este mismo origen con rutas
# relativas, así que ninguna petición es cross-origin.
app = FastAPI(title="Meridia · agente documental", version="2.1.0", lifespan=lifespan)


class Turn(BaseModel):
    role: str
    content: str


class Query(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    history: List[Turn] = Field(default_factory=list)
    k: int = Field(default=TOP_K, ge=1, le=10)


# --------------------------------------------------------------------- estado


@app.get("/api/state")
def get_state(request: Request = None) -> dict:
    estado = library.state()
    estado["quota"] = cuota.estado(_ip(request)) if request else {"limite": limite_ip()}
    estado["model"] = model_name()
    estado["provider"] = os.getenv("LLM_PROVIDER", "gemini")
    estado["top_k"] = TOP_K
    # booleano, nunca el token: el front necesita saber qué dibujar
    estado["write_protected"] = write_protected()
    return estado


# ---------------------------------------------------------------- documentos


@app.get("/api/admin/check", dependencies=[Depends(require_write_token)])
def admin_check() -> dict:
    """Comprueba un token recién introducido, para no fingir que se entró."""
    return {"ok": True}


@app.post("/api/documents", dependencies=[Depends(require_write_token)])
async def add_document(file: UploadFile = File(...)) -> dict:
    contenido = await file.read()
    try:
        # escribir en disco e indexar son bloqueantes: fuera del event loop,
        # o el servidor entero deja de responder mientras se indexa
        registro = await run_in_threadpool(library.add, file.filename or "documento", contenido)
    except LibraryError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    await run_in_threadpool(library.build_index)
    cache.limpiar()  # la biblioteca cambió: las respuestas guardadas ya no valen
    return {"document": registro, "state": get_state()}


@app.delete("/api/documents/{doc_id}", dependencies=[Depends(require_write_token)])
def delete_document(doc_id: str) -> dict:
    # este endpoint es `def`, así que FastAPI ya lo ejecuta en el threadpool
    try:
        library.remove(doc_id)
    except LibraryError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    library.build_index()
    cache.limpiar()
    return {"state": get_state()}


@app.get("/api/documents/{doc_id}/content")
def document_content(doc_id: str, page: Optional[int] = None) -> dict:
    try:
        paginas = library.pages_of(doc_id)
        doc = library.get(doc_id)
    except LibraryError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    total = len(paginas)
    indice = 1 if page is None else max(1, min(total, page))
    return {
        "id": doc_id,
        "filename": doc["filename"],
        "kind": doc["kind"],
        "page": indice,
        "total_pages": total,
        "text": paginas[indice - 1] if total else "",
        "unit": "página" if doc["kind"] == "pdf" else "bloque",
    }


@app.get("/api/documents/{doc_id}/file")
def document_file(doc_id: str):
    try:
        doc = library.get(doc_id)
    except LibraryError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return FileResponse(doc["path"], filename=doc["filename"])


# -------------------------------------------------------------------- consulta


def _ip(request: Optional[Request]) -> str:
    return (request.client.host if request and request.client else "desconocida")


def _es_admin(request: Optional[Request]) -> bool:
    """El token de administración se salta la cuota: es tu propia demo."""
    esperado = expected_token()
    if not esperado or request is None:
        return False
    return request.headers.get("X-Alura-Token") == esperado


def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


def _hit_payload(doc, score: float, orden: int) -> dict:
    return {
        "n": orden,
        "chunk_id": doc.metadata.get("chunk_id"),
        "doc_id": doc.metadata.get("doc_id"),
        "filename": doc.metadata.get("filename"),
        "locator": doc.metadata.get("locator"),
        "page": doc.metadata.get("page"),
        "unit": doc.metadata.get("unit"),
        "score": round(score, 4),
        "text": doc.page_content,
    }


def _run(query: Query, ip: str, admin: bool) -> Iterator[str]:
    """Envoltura: cualquier fallo inesperado llega al cliente como evento, no como conexión cortada."""
    try:
        yield from _pipeline(query, ip, admin)
    except Exception as exc:
        yield _sse({"type": "error", "message": f"El pipeline se interrumpió: {exc}"})


def _pipeline(query: Query, ip: str, admin: bool) -> Iterator[str]:
    estado = library.state()
    if estado["status"] != "listo":
        mensaje = {
            "vacio": "No hay documentos en la biblioteca. Agrega un PDF o CSV para empezar.",
            "indexando": "El índice se está construyendo. Vuelve a preguntar en unos segundos.",
            "error": f"El índice no se pudo construir: {estado.get('error')}",
        }.get(estado["status"], "El índice no está disponible.")
        yield _sse({"type": "error", "message": mensaje})
        return

    vector_store = library.vector_store
    inicio = time.perf_counter()

    try:
        llm = get_llm()
    except ValueError as exc:
        yield _sse({"type": "error", "message": str(exc)})
        return

    # Etapa 1 · vectorizar la pregunta
    yield _sse({"type": "stage", "id": "consulta", "status": "active"})
    t0 = time.perf_counter()
    vector = embed_query(query.question)
    ms_embed = (time.perf_counter() - t0) * 1000
    yield _sse({
        "type": "stage",
        "id": "consulta",
        "status": "done",
        "ms": round(ms_embed, 1),
        "meta": {"dims": len(vector)},
    })

    # Etapa 2 · buscar en el índice
    yield _sse({"type": "stage", "id": "recuperacion", "status": "active"})
    t0 = time.perf_counter()
    resultados = search_by_vector(vector_store, vector, k=query.k)
    ms_busqueda = (time.perf_counter() - t0) * 1000

    hits = [_hit_payload(doc, score, i) for i, (doc, score) in enumerate(resultados, start=1)]
    contribuciones: dict = {}
    for hit in hits:
        actual = contribuciones.setdefault(
            hit["doc_id"], {"doc_id": hit["doc_id"], "filename": hit["filename"], "count": 0, "score": 0.0}
        )
        actual["count"] += 1
        actual["score"] = max(actual["score"], hit["score"])

    yield _sse({
        "type": "stage",
        "id": "recuperacion",
        "status": "done",
        "ms": round(ms_busqueda, 1),
        "meta": {"k": query.k, "chunks": estado["chunk_count"]},
    })
    yield _sse({
        "type": "hits",
        "hits": hits,
        "contributions": sorted(contribuciones.values(), key=lambda c: -c["score"]),
    })

    # Etapa 3 · generar la respuesta
    yield _sse({"type": "stage", "id": "modelo", "status": "active", "meta": {"model": model_name()}})

    # Si esta misma pregunta ya se respondió sobre estos mismos fragmentos, se
    # reutiliza: no se llama al modelo y no consume cuota de nadie.
    clave = cache.clave(query.question, tuple(h["chunk_id"] for h in hits))
    guardada = None if query.history else cache.obtener(clave)

    t0 = time.perf_counter()
    partes: List[str] = []
    primera_ms: Optional[float] = None

    if guardada is not None:
        respuesta = guardada
        yield _sse({"type": "token", "text": respuesta})
    else:
        motivo = None if admin else cuota.disponible(ip)
        if motivo:
            yield _sse({"type": "error", "message": motivo, "quota": cuota.estado(ip)})
            return

        prompt = build_prompt(
            [doc for doc, _ in resultados],
            query.question,
            [turno.model_dump() for turno in query.history],
        )
        try:
            for texto in stream_answer(llm, prompt):
                if primera_ms is None:
                    primera_ms = (time.perf_counter() - t0) * 1000
                partes.append(texto)
                yield _sse({"type": "token", "text": texto})
        except Exception as exc:
            yield _sse({"type": "error", "message": f"El modelo no pudo responder: {exc}"})
            return

        if not admin:
            cuota.consumir(ip)
        respuesta = "".join(partes).strip()
        if not query.history:
            cache.guardar(clave, respuesta)

    ms_modelo = (time.perf_counter() - t0) * 1000

    yield _sse({
        "type": "stage",
        "id": "modelo",
        "status": "done",
        "ms": round(ms_modelo, 1),
        "meta": {"cached": guardada is not None},
    })
    yield _sse({
        "type": "stage",
        "id": "respuesta",
        "status": "done",
        "meta": {"chars": len(respuesta), "cites": len(hits)},
    })
    yield _sse({
        "type": "done",
        "answer": respuesta,
        "model": model_name(),
        "timings": {
            "embedding": round(ms_embed, 1),
            "busqueda": round(ms_busqueda, 1),
            "modelo": round(ms_modelo, 1),
            "primer_token": round(primera_ms, 1) if primera_ms else None,
            "total": round((time.perf_counter() - inicio) * 1000, 1),
        },
        "characters": len(respuesta),
        "cached": guardada is not None,
        "quota": cuota.estado(ip),
    })


@app.post("/api/query")
def query(payload: Query, request: Request) -> StreamingResponse:
    return StreamingResponse(
        _run(payload, _ip(request), _es_admin(request)),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ------------------------------------------------------------------- estáticos

if os.path.isdir(WEB_DIR):
    app.mount("/", StaticFiles(directory=WEB_DIR, html=True), name="web")
