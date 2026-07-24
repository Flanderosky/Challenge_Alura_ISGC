FROM python:3.12-slim

# Imagen multiarquitectura: en la instancia Ampere de OCI se resuelve a
# linux/arm64 sin tocar nada. Conviene construir en la propia instancia;
# hacerlo desde x86 con QEMU tarda muchísimo por culpa de torch.

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    # con 1 OCPU, los hilos de OpenMP solo añaden contención
    OMP_NUM_THREADS=1 \
    MKL_NUM_THREADS=1 \
    TOKENIZERS_PARALLELISM=false \
    # caché del modelo fuera de /root, para que el usuario sin privilegios la lea
    HF_HOME=/opt/hf \
    SENTENCE_TRANSFORMERS_HOME=/opt/hf

# libgomp1 lo enlazan FAISS y torch; build-essential cubre el caso de que
# alguna dependencia no tenga rueda binaria para esta arquitectura.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# El modelo de embeddings se descarga en el build para que el primer arranque
# no dependa de la red. El chmod lo deja legible para el usuario no-root.
RUN mkdir -p /opt/hf \
    && python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')" \
    && chmod -R a+rX /opt/hf

# UID 1000 a propósito: es el del usuario por defecto en las imágenes de OCI
# (opc / ubuntu), y `./data` se monta desde el host. Si no coinciden, subir un
# documento falla con PermissionError al escribir el registro.
RUN useradd --create-home --uid 1000 --shell /usr/sbin/nologin appuser

COPY --chown=appuser:appuser . .
RUN mkdir -p /app/data/uploads && chown -R appuser /app/data

USER appuser

EXPOSE 8000

# Comprueba que el proceso atiende HTTP, no que el RAG funcione: si falta la
# clave de la API no queremos reinicios en bucle. El start-period es largo
# porque en 1 OCPU importar torch y cargar el modelo tarda.
HEALTHCHECK --interval=30s --timeout=5s --start-period=180s --retries=3 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/api/state',timeout=4).status==200 else 1)"

# Un solo worker, y no es negociable: la biblioteca y el índice FAISS viven en
# la memoria de este proceso. Con varios workers cada uno tendría su copia, un
# documento subido a uno sería invisible para los demás y /api/state
# respondería cosas distintas según a quién le tocara la petición.
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
