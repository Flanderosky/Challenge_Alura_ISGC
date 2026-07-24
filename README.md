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
│   ├── store.py            # biblioteca de documentos e índice
│   └── auth.py             # token para agregar y quitar documentos
├── src/
│   ├── loader.py           # carga, fragmentación y agregados con procedencia
│   ├── vectorstore.py      # embeddings compartidos + FAISS
│   └── agent.py            # LLM, prompt con citas, streaming
├── web/
│   ├── index.html
│   ├── styles.css
│   └── js/{app,flow,library,api}.js
├── data/                   # documentos de ejemplo y subidas
├── docs/
│   ├── ejemplos_respuestas.md   # generado, respuestas reales del agente
│   └── capturas/                # evidencia del despliegue
├── scripts/
│   ├── generar_ejemplos.py      # genera docs/ejemplos_respuestas.md
│   └── generate_sample_pdf.py
├── tests/
│   ├── test_agent.py            # carga, fragmentación, índice, prompt
│   └── test_api_auth.py         # protección de escritura
├── Dockerfile
├── .dockerignore
├── docker-compose.yml
├── requirements.txt
└── requirements-dev.txt
```

---

## Cómo ejecutarlo

```bash
python -m venv venv
source venv/bin/activate     # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env         # y edita tu clave de API
uvicorn api.main:app --reload
```

Abre `http://localhost:8000`.

La primera vez se descarga el modelo de embeddings (~90 MB). Mientras tanto la cabecera muestra el índice en estado *construyendo*.

Para desarrollo (pruebas y utilidades): `pip install -r requirements-dev.txt`.

### Variables de entorno

```env
LLM_PROVIDER=gemini
GOOGLE_API_KEY=tu_google_api_key
GOOGLE_MODEL=gemini-3.1-flash-lite
```

También acepta `cohere` (`COHERE_API_KEY`, `COHERE_MODEL`) y `openai` (`OPENAI_API_KEY`, `OPENAI_MODEL`).

Dos variables más, ambas opcionales:

| Variable | Efecto |
|---|---|
| `ALURA_ADMIN_TOKEN` | Si está definida, agregar y quitar documentos exige la cabecera `X-Alura-Token`. Consultar y leer siguen siendo públicos. Si está vacía, la escritura queda abierta, que es lo cómodo en local. |
| `HOST_PORT` | Puerto del host donde se publica la aplicación con Docker. El contenedor siempre escucha en el 8000. |

---

## Docker

```bash
docker compose up --build
```

La imagen descarga el modelo de embeddings durante el build, así que el contenedor arranca listo. `HOST_PORT` en el `.env` cambia el puerto publicado sin tocar la imagen.

Dos cosas que conviene saber antes de tocar el despliegue:

- **Un solo worker, a propósito.** La biblioteca y el índice FAISS viven en la memoria del proceso. Con varios workers, cada uno tendría su copia: un documento subido a uno sería invisible para los demás.
- **El volumen `./data` tapa el `data/` de la imagen.** El directorio del host debe contener los documentos de ejemplo, o la biblioteca arranca vacía. Un `git clone` ya los trae.

---

## Despliegue en OCI Compute

1. **Instancia**: `VM.Standard.A1.Flex` (Ampere, aarch64) del free tier, Ubuntu 22.04 u Oracle Linux 8.

   No uses `VM.Standard.E2.1.Micro`: con 1 GB de RAM no soporta ni el build ni la ejecución de torch con sentence-transformers. La A1 del free tier llega a 4 OCPU y 24 GB.

2. **Puerto** abierto en la *Security List* del subnet: `Stateful`, `TCP`, origen `0.0.0.0/0`. En este despliegue se usa el **8501**, publicado hacia el 8000 del contenedor mediante `HOST_PORT`.

   Abrir el puerto en la Security List no siempre basta: las imágenes de Ubuntu y Oracle Linux en OCI traen sus propias reglas de iptables. Un puerto publicado por Docker entra por `nat/PREROUTING`, no por `INPUT`, así que si otro contenedor ya se veía en ese puerto, este también se verá.

3. **Docker** en la instancia:

```bash
# Ubuntu
sudo apt-get update && sudo apt-get install -y docker.io docker-compose-v2
# Oracle Linux
sudo dnf install -y docker-engine docker-cli docker-compose-plugin && sudo systemctl enable --now docker

sudo usermod -aG docker $USER && newgrp docker
```

4. **Código y configuración**:

```bash
git clone https://github.com/Flanderosky/Challenge_Alura_ISGC.git
cd Challenge_Alura_ISGC
cp .env.example .env && chmod 600 .env
nano .env    # GOOGLE_API_KEY, HOST_PORT=8501, ALURA_ADMIN_TOKEN=$(openssl rand -hex 24)
```

5. **Build y arranque**. En 1 OCPU el build tarda entre 15 y 35 minutos, así que conviene lanzarlo dentro de `tmux` para que sobreviva a una caída de la sesión SSH:

```bash
tmux new -s build
docker compose up -d --build
```

6. **Verificar**:

```bash
docker compose ps                                  # 0.0.0.0:8501->8000/tcp
curl -s http://localhost:8501/api/state            # "status": "listo"
curl -o /dev/null -w '%{http_code}\n' -X DELETE \
     http://localhost:8501/api/documents/x         # 401: la escritura está protegida
```

Después, `http://<IP_PUBLICA>:8501` desde el navegador. El índice se construye al arrancar, así que durante el primer minuto la cabecera muestra *construyendo*.

---

## Preguntas de ejemplo

Con el PDF de políticas:

- ¿Cuántos días de vacaciones corresponden por año?
- ¿Qué tecnologías se usan en el back-end?
- ¿Qué horario tiene el equipo de tecnología?

Con el CSV de ventas:

- ¿Cuál fue el total de ventas y el producto más vendido?
- ¿Qué región generó más ingresos?

El CSV se indexa por bloques de filas **y** con fragmentos calculados: un resumen con los totales generales, y un desglose por cada columna categórica y por mes. Sin ellos, una búsqueda semántica no puede responder "¿cuál fue el total?" ni "¿qué región generó más ingresos?", porque ninguna fila contiene esa suma.

El chat conserva el contexto: después de preguntar por el total, "¿y cuál fue el promedio?" se resuelve sola.

---

## Ejemplos de respuestas

Respuestas reales del agente, generadas con `python scripts/generar_ejemplos.py`, que consume el mismo endpoint que la interfaz. Los tiempos son los medidos en esa ejecución.

### ¿Cuál fue el total de ventas y el producto más vendido?

> El total de ingreso sumando todos los registros es 286,150.00 [1]. El producto más frecuente es Laptop Pro [1].

| [n] | Documento | Ubicación | Relevancia |
|-----|-----------|-----------|-----------:|
| [1] | ventas_ejemplo.csv | resumen | 0.4128 |
| [2] | ventas_ejemplo.csv | desglose por region | 0.3592 |
| [3] | politicas_ejemplo.pdf | p. 1 | 0.2681 |

Ninguna fila del CSV contiene ese total: sale del fragmento de agregados que se calcula al indexar.

### ¿Cuál es la política de coche de empresa?

> Los fragmentos proporcionados no contienen información sobre la política de coche de empresa; haría falta el documento de políticas de beneficios o compensaciones para responder.

Este ejemplo está aquí a propósito. El agente responde solo con lo que hay en los documentos, y cuando no está, lo dice en vez de inventarlo.

**[Ver los seis ejemplos completos](docs/ejemplos_respuestas.md)**, con todas las fuentes y los tiempos por etapa.

---

## Evidencia del despliegue

*(Pendiente: enlace público y capturas, tras el redespliegue en la instancia.)*

---

## Pruebas

```bash
pip install -r requirements-dev.txt
pytest tests/
```

18 pruebas, ninguna requiere clave de API. Cubren carga y fragmentación con procedencia, los agregados y desgloses del CSV, la relevancia normalizada, la construcción del prompt y la protección de escritura de la API.

---

## Notas

- **Nunca subas tu `.env`** con claves reales; está en `.gitignore` y en `.dockerignore`, así que tampoco entra en la imagen.
- Los documentos subidos viven en `data/uploads/`, fuera del control de versiones. El contenedor los escribe con el UID 1000, que es el del usuario por defecto en las instancias de OCI.
- El índice se reconstruye completo al agregar o quitar un documento. Para bibliotecas grandes conviene pasar a un índice persistente.
- Los embeddings corren en local: indexar no requiere internet. El modelo de lenguaje sí.
- Mejora pendiente para ARM: sustituir torch por ONNX Runtime (`fastembed`) con el mismo modelo dejaría la imagen en una fracción de su tamaño y el build en unos minutos.

---

## Licencia

Uso educativo, desafío final de Alura.
