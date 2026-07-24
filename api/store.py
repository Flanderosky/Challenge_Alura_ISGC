"""
Biblioteca de documentos e índice vectorial.

Mantiene el registro de documentos en disco, reconstruye el índice cuando la
biblioteca cambia y expone el estado para que la interfaz pueda dibujarlo.
"""

import json
import os
import threading
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional

from langchain_core.documents import Document

from src.loader import load_document, read_pages
from src.vectorstore import create_vector_store

DATA_DIR = os.path.join("data")
UPLOAD_DIR = os.path.join(DATA_DIR, "uploads")
REGISTRY_PATH = os.path.join(UPLOAD_DIR, "registry.json")
SEED_FILES = [
    "politica_devoluciones.pdf",
    "guia_envios.pdf",
    "politica_privacidad.pdf",
    "preguntas_frecuentes.pdf",
    "terminos_condiciones.pdf",
    "pedidos_2026.csv",
    "devoluciones_2026.csv",
]
ALLOWED_EXTENSIONS = {".pdf", ".csv"}
MAX_UPLOAD_BYTES = 25 * 1024 * 1024


class LibraryError(Exception):
    """Error esperable de la biblioteca, con mensaje apto para mostrar al usuario."""


class Library:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        # Lock aparte y a propósito: serializa las reconstrucciones sin tocar
        # `_lock`, que protege lecturas rápidas como state() y vector_store.
        # Usar el mismo dejaría /api/state colgado durante toda la indexación.
        self._build_lock = threading.Lock()
        self._documents: Dict[str, dict] = {}
        self._chunks: Dict[str, List[Document]] = {}
        self._vector_store = None
        self._status = "vacio"
        self._error: Optional[str] = None
        # Si el volumen no es escribible, la aplicación sigue en pie y responde
        # consultas: solo se desactiva agregar y quitar documentos. Antes, un
        # error de permisos aquí tumbaba el servidor entero en el arranque.
        self._error_escritura: Optional[str] = None

        try:
            os.makedirs(UPLOAD_DIR, exist_ok=True)
        except OSError as exc:
            self._error_escritura = (
                f"El directorio {UPLOAD_DIR} no es escribible ({exc.strerror}). "
                "Se pueden consultar los documentos, pero no agregar ni quitar."
            )

        self._load_registry()
        self._seed_examples()

    # ---------------------------------------------------------------- registro

    def _load_registry(self) -> None:
        if not os.path.exists(REGISTRY_PATH):
            return
        try:
            with open(REGISTRY_PATH, "r", encoding="utf-8") as handle:
                registro = json.load(handle)
        except (OSError, json.JSONDecodeError):
            return
        for doc in registro.get("documents", []):
            if os.path.exists(doc.get("path", "")):
                self._documents[doc["id"]] = doc

    def _save_registry(self) -> None:
        payload = {"documents": list(self._documents.values())}
        try:
            with open(REGISTRY_PATH, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, ensure_ascii=False, indent=2)
        except OSError as exc:
            # sin registro en disco la biblioteca sigue funcionando en memoria;
            # lo que se pierde es recordar las subidas tras un reinicio.
            # No se pisa un error anterior: ese describe la causa raíz.
            self._error_escritura = self._error_escritura or (
                f"No se pudo guardar el registro de documentos ({exc.strerror})."
            )

    def _seed_examples(self) -> None:
        """Carga los documentos de ejemplo la primera vez, para que la app no arranque vacía."""
        conocidos = {doc["path"] for doc in self._documents.values()}
        for nombre in SEED_FILES:
            ruta = os.path.join(DATA_DIR, nombre)
            if not os.path.exists(ruta) or ruta in conocidos:
                continue
            doc_id = uuid.uuid4().hex[:12]
            self._documents[doc_id] = {
                "id": doc_id,
                "filename": nombre,
                "path": ruta,
                "kind": os.path.splitext(nombre)[1].lstrip("."),
                "bytes": os.path.getsize(ruta),
                "added_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "seeded": True,
            }
        self._save_registry()

    # ----------------------------------------------------------------- índice

    def build_index(self) -> None:
        """Reconstruye el índice completo. Bloqueante; llamar en segundo plano."""
        with self._build_lock:
            self._build_index_locked()

    def _build_index_locked(self) -> None:
        with self._lock:
            documentos = list(self._documents.values())
            if not documentos:
                self._vector_store = None
                self._chunks = {}
                self._status = "vacio"
                self._error = None
                return
            self._status = "indexando"
            self._error = None

        fragmentos: List[Document] = []
        por_documento: Dict[str, List[Document]] = {}
        try:
            for doc in documentos:
                trozos = load_document(doc["path"], doc_id=doc["id"], filename=doc["filename"])
                for i, trozo in enumerate(trozos):
                    trozo.metadata["chunk_id"] = f"{doc['id']}:{i}"
                    trozo.metadata["chunk_index"] = i
                por_documento[doc["id"]] = trozos
                fragmentos.extend(trozos)
            vector_store = create_vector_store(fragmentos)
        except Exception as exc:  # el índice queda inutilizable: hay que reportarlo entero
            with self._lock:
                self._status = "error"
                self._error = str(exc)
                self._vector_store = None
            return

        with self._lock:
            self._chunks = por_documento
            self._vector_store = vector_store
            self._status = "listo"
            self._error = None

    def build_index_async(self) -> None:
        threading.Thread(target=self.build_index, daemon=True).start()

    @property
    def vector_store(self):
        with self._lock:
            return self._vector_store

    # ----------------------------------------------------------------- estado

    def state(self) -> dict:
        with self._lock:
            documentos = [self._public(doc) for doc in self._documents.values()]
            return {
                "status": self._status,
                "error": self._error,
                "storage_error": self._error_escritura,
                "documents": documentos,
                "chunk_count": sum(doc["chunks"] for doc in documentos),
            }

    def _public(self, doc: dict) -> dict:
        trozos = self._chunks.get(doc["id"], [])
        return {
            "id": doc["id"],
            "filename": doc["filename"],
            "kind": doc["kind"],
            "bytes": doc["bytes"],
            "added_at": doc["added_at"],
            "seeded": doc.get("seeded", False),
            "chunks": len(trozos),
            "units": len({t.metadata.get("page") for t in trozos}) if trozos else 0,
        }

    def get(self, doc_id: str) -> dict:
        with self._lock:
            doc = self._documents.get(doc_id)
            if not doc:
                raise LibraryError("Ese documento ya no está en la biblioteca.")
            return doc

    def chunks_of(self, doc_id: str) -> List[Document]:
        with self._lock:
            return list(self._chunks.get(doc_id, []))

    def pages_of(self, doc_id: str) -> List[str]:
        doc = self.get(doc_id)
        return read_pages(doc["path"], doc["filename"])

    # ------------------------------------------------------------ mutaciones

    def add(self, filename: str, content: bytes) -> dict:
        if self._error_escritura:
            raise LibraryError(self._error_escritura)

        extension = os.path.splitext(filename)[1].lower()
        if extension not in ALLOWED_EXTENSIONS:
            raise LibraryError(f"Solo se aceptan archivos PDF o CSV. Recibido: {extension or 'sin extensión'}")
        if not content:
            raise LibraryError("El archivo llegó vacío.")
        if len(content) > MAX_UPLOAD_BYTES:
            raise LibraryError(f"El archivo pesa más de {MAX_UPLOAD_BYTES // (1024 * 1024)} MB.")

        doc_id = uuid.uuid4().hex[:12]
        destino = os.path.join(UPLOAD_DIR, f"{doc_id}{extension}")
        with open(destino, "wb") as handle:
            handle.write(content)

        registro = {
            "id": doc_id,
            "filename": os.path.basename(filename),
            "path": destino,
            "kind": extension.lstrip("."),
            "bytes": len(content),
            "added_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "seeded": False,
        }
        with self._lock:
            self._documents[doc_id] = registro
            self._save_registry()
        return registro

    def remove(self, doc_id: str) -> None:
        with self._lock:
            doc = self._documents.pop(doc_id, None)
            if not doc:
                raise LibraryError("Ese documento ya no está en la biblioteca.")
            self._chunks.pop(doc_id, None)
            self._save_registry()
        if not doc.get("seeded") and os.path.exists(doc["path"]):
            try:
                os.remove(doc["path"])
            except OSError:
                pass


library = Library()
