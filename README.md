# Alura · banco documental

Agente que responde preguntas en lenguaje natural sobre documentos internos en **PDF** o **CSV**, y muestra el recorrido real de cada consulta: qué se recuperó, de qué documento, con qué relevancia y cuánto tardó cada etapa.

Desarrollado como desafío final del programa **Alura Agente**.

---

## Qué lo distingue

La mayoría de las demos de RAG entregan una respuesta y una lista de fuentes en texto plano. Aquí la interfaz está partida en dos:

- **Izquierda — recorrido de la consulta.** Un grafo donde cada nodo se enciende cuando esa etapa está corriendo de verdad. Los tiempos son medidos, no simulados. Las conexiones que van de los documentos al índice se pintan de amarillo según cuántos fragmentos aportó cada documento y con qué relevancia.
- **Derecha — la conversación.** La respuesta llega token a token, con citas `[n]` clicables. Cada cita abre el documento original con el pasaje resaltado sobre el texto real.

Los documentos se agregan, revisan y quitan desde la biblioteca, y el índice se reconstruye solo.

---

## Arquitectura

```
┌──────────────────────┐        ┌─────────────────────────────────────┐
│  Front propio        │  SSE   │  FastAPI (api/)                     │
│  HTML + CSS + JS     │◀──────▶│  /api/state                         │
│  sin build ni deps   │        │  /api/documents  (alta, baja, visor)│
└──────────────────────┘        │  /api/query      (stream de eventos)│
                                └──────────────┬──────────────────────┘
                                               │
                    ┌──────────────────────────┼──────────────────────┐
                    │  src/                    ▼                      │
                    │  loader.py     → fragmenta y anota procedencia  │
                    │  vectorstore.py→ embeddings locales + FAISS     │
                    │  agent.py      → prompt con citas + streaming   │
                    └─────────────────────────────────────────────────┘
```

### El flujo de una consulta

1. La pregunta se vectoriza con `sentence-transformers` (local, sin red).
2. FAISS devuelve los `k` fragmentos más cercanos con su relevancia (0–1, coseno).
3. Se arma el prompt con los fragmentos numerados y los últimos turnos de la conversación.
4. El modelo redacta citando `[n]`; la respuesta se transmite token a token.

Cada paso emite un evento SSE, y eso es exactamente lo que dibuja el grafo.

---

## Tecnologías

- **Python 3.12**
- **FastAPI + Uvicorn** — API y servidor de estáticos
- **LangChain** — orquestación de RAG
- **FAISS** — índice vectorial en memoria
- **sentence-transformers** (`all-MiniLM-L6-v2`) — embeddings locales
- **PyPDF / Pandas** — lectura de PDF y CSV
- **Google Gemini** — modelo por defecto (Cohere y OpenAI como alternativas)
- **Docker** — contenedorización
- **OCI Compute** — despliegue en la nube

El front no usa framework ni build: HTML, CSS y módulos ES nativos.

---

## Estructura

```
Challenge_Alura_ISGC/
├── api/
│   ├── main.py             # endpoints y stream de eventos del pipeline
│   └── store.py            # biblioteca de documentos e índice
├── src/
│   ├── loader.py           # carga y fragmentación con procedencia
│   ├── vectorstore.py      # embeddings compartidos + FAISS
│   └── agent.py            # LLM, prompt con citas, streaming
├── web/
│   ├── index.html
│   ├── styles.css
│   └── js/{app,flow,library,api}.js
├── data/                   # documentos de ejemplo y subidas
├── tests/test_agent.py
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

---

## Cómo ejecutarlo

```bash
python -m venv venv
venv\Scripts\activate        # Linux/macOS: source venv/bin/activate
pip install -r requirements.txt

cp .env.example .env         # y edita tu clave de API
uvicorn api.main:app --reload
```

Abre `http://localhost:8000`.

La primera vez se descarga el modelo de embeddings (~90 MB). Mientras tanto la cabecera muestra el índice en estado *construyendo*.

### Variables de entorno

```env
LLM_PROVIDER=gemini
GOOGLE_API_KEY=tu_google_api_key
GOOGLE_MODEL=gemini-3.1-flash-lite
```

También acepta `cohere` (`COHERE_API_KEY`, `COHERE_MODEL`) y `openai` (`OPENAI_API_KEY`, `OPENAI_MODEL`).

---

## Docker

```bash
docker compose up --build
```

La imagen descarga el modelo de embeddings durante el build, así que el contenedor arranca listo.

---

## Despliegue en OCI Compute

1. **Instancia**: `VM.Standard.E2.1.Micro` (free tier) o superior, Ubuntu 22.04 u Oracle Linux 8.
2. **Puerto 8000** abierto en la *Security List* del subnet: `Stateful`, `TCP`, destino `8000`, origen `0.0.0.0/0`.
3. **Docker** en la instancia:

```bash
sudo apt-get update && sudo apt-get install -y docker.io docker-compose-v2
sudo usermod -aG docker $USER && newgrp docker
```

4. **Código y arranque**:

```bash
git clone https://github.com/Flanderosky/Challenge_Alura_ISGC.git
cd Challenge_Alura_ISGC
cp .env.example .env   # agrega tus claves
docker compose up -d --build
```

5. **Verificar**: `docker logs -f alura-agente` y abrir `http://<IP_PUBLICA>:8000`.

---

## Preguntas de ejemplo

Con el PDF de políticas:

- ¿Cuántos días de vacaciones corresponden por año?
- ¿Qué dice la política de trabajo remoto?
- ¿Qué tecnologías se usan en el back-end?

Con el CSV de ventas:

- ¿Cuál fue el total de ventas y el producto más vendido?
- ¿Qué región generó más ingresos?

El CSV se indexa por bloques de filas **y** con un fragmento de agregados (totales, promedios, máximos, valores más frecuentes). Sin ese fragmento, una búsqueda semántica no puede responder "¿cuál fue el total?", porque ninguna fila contiene el total.

El chat conserva el contexto: después de preguntar por el total, "¿y cuál fue el promedio?" se resuelve sola.

---

## Pruebas

```bash
pytest tests/
```

Cubren carga, fragmentación con procedencia, relevancia normalizada, construcción del prompt y validación de configuración. No requieren clave de API.

---

## Notas

- **Nunca subas tu `.env`** con claves reales; está en `.gitignore`.
- Los documentos subidos viven en `data/uploads/`, fuera del control de versiones.
- El índice se reconstruye completo al agregar o quitar un documento. Para bibliotecas grandes conviene pasar a un índice persistente.
- Los embeddings corren en local: indexar no requiere internet. El modelo de lenguaje sí.

---

## Licencia

Uso educativo, desafío final de Alura.
