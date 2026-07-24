# Meridia · soporte documentado

Agente de atención al cliente para **Meridia**, una tienda en línea ficticia. Responde preguntas en lenguaje natural usando la documentación real de la tienda en **PDF** y sus datos de operación en **CSV**, y muestra el recorrido de cada consulta: qué se recuperó, de qué documento, con qué relevancia y cuánto tardó cada etapa.

El problema que resuelve es concreto: un cliente pregunta *"¿cuánto tiempo tengo para devolver un producto electrónico?"* y la respuesta sale del documento vigente, con la página citada, en vez de depender de que alguien de soporte se acuerde de la excepción.

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

### Dos decisiones que cambiaron la calidad de las respuestas

**El modelo de embeddings tiene que ser multilingüe.** El corpus está en español y el modelo habitual de los tutoriales, `all-MiniLM-L6-v2`, está entrenado solo en inglés. Medido sobre este corpus con 8 preguntas de control, dejaba fuera del top-6 la mitad de los documentos correctos: el agente contestaba "no lo sé" teniendo la respuesta en la biblioteca. Con `multilingual-e5-small`, los 8 documentos correctos entran en el top-6 y 6 de ellos en primer lugar.

**El membrete del PDF envenena la búsqueda.** Al extraer un PDF, el encabezado y el pie que se repiten en cada página entran como texto normal y se cuelan en todos los fragmentos. Eso los hace parecerse entre sí y hunde al que lleva la respuesta. `src/loader.py` detecta las líneas que se repiten en los bordes de las páginas y las descarta antes de fragmentar.

---

## Tecnologías

- **Python 3.12**
- **FastAPI + Uvicorn** — API y servidor de estáticos
- **LangChain** — orquestación de RAG
- **FAISS** — índice vectorial en memoria
- **sentence-transformers** (`intfloat/multilingual-e5-small`) — embeddings locales, multilingües
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
├── data/                   # corpus de Meridia (5 PDF + 2 CSV) y subidas
├── docs/
│   ├── ejemplos_respuestas.md   # generado, respuestas reales del agente
│   └── capturas/                # evidencia del despliegue
├── scripts/
│   ├── generar_corpus.py        # genera los PDF y CSV de data/
│   └── generar_ejemplos.py      # genera docs/ejemplos_respuestas.md
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
| `ALURA_LIMITE_DIARIO_IP` | Consultas al modelo por IP y día. Por defecto 5. `0` desactiva el límite. |
| `ALURA_LIMITE_DIARIO_TOTAL` | Consultas al modelo por día sumando a todo el mundo. Por defecto 200. `0` desactiva el límite. |

### Por qué hay un límite de consultas

La demo es pública y el modelo corre sobre la **cuota gratuita** de Google Gemini. Sin un tope, un bucle automatizado la agota en minutos y el agente deja de responder justo cuando alguien quiere probarlo. El límite no protege un gasto: protege la disponibilidad.

Tres detalles del diseño:

- **Las respuestas ya dadas no consumen cuota.** Si alguien repite una pregunta que ya se contestó sobre los mismos fragmentos, se sirve la respuesta guardada sin llamar al modelo. La caché se invalida sola cuando cambia la biblioteca.
- **El contador se muestra en la cabecera**, para que se vea cuántas consultas quedan en vez de toparse con un error sin aviso.
- **El token de administración se salta el límite**, así que quien mantiene la instancia siempre puede probarla.

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

## El corpus

Siete documentos de la tienda, generados de forma reproducible con `python scripts/generar_corpus.py`:

| Documento | Contenido |
|---|---|
| `politica_devoluciones.pdf` | Plazos, costos de retorno, productos excluidos, reembolsos |
| `guia_envios.pdf` | Modalidades, cobertura, paqueterías, rastreo, incidencias |
| `politica_privacidad.pdf` | Datos recabados, finalidades, conservación, derechos ARCO |
| `preguntas_frecuentes.pdf` | Pagos, envíos, devoluciones, facturación, garantía |
| `terminos_condiciones.pdf` | Precios, garantía legal, cupones, jurisdicción |
| `pedidos_2026.csv` | 420 pedidos: fecha, categoría, producto, región, canal, importe |
| `devoluciones_2026.csv` | 76 devoluciones: motivo, importe reembolsado, días de resolución |

En total, unos 110 fragmentos indexados.

## Preguntas de ejemplo

De la documentación en PDF:

- ¿Cuánto tiempo tengo para devolver un producto electrónico?
- ¿Cuánto cuesta el envío y cuándo es gratis?
- ¿Qué pasa si nadie recibe el paquete?
- ¿Cómo pido que borren mis datos personales?

De los datos en CSV:

- ¿Qué categoría generó más ingresos?
- ¿Cuál es el motivo de devolución más frecuente?
- ¿Qué región tiene más pedidos?

Los CSV se indexan por bloques de filas **y** con fragmentos calculados: un resumen con los totales generales, y un desglose por cada columna categórica y por mes, con su ranking. Sin ellos, una búsqueda semántica no puede responder "¿qué categoría generó más ingresos?", porque ninguna fila contiene esa suma.

El chat conserva el contexto: después de preguntar por la categoría, "¿y cuál es el motivo de devolución más frecuente?" se resuelve sin repetir el contexto.

---

## Ejemplos de respuestas

Respuestas reales del agente, generadas con `python scripts/generar_ejemplos.py`, que consume el mismo endpoint que la interfaz. Los tiempos son los medidos en esa ejecución.

### ¿Cuánto tiempo tengo para devolver un producto electrónico?

> Los productos de la categoría Electrónica tienen un plazo de 14 días naturales para solicitar la devolución [1], [4].

| [n] | Documento | Ubicación | Relevancia |
|-----|-----------|-----------|-----------:|
| [1] | politica_devoluciones.pdf | p. 1 | 0.9772 |
| [2] | politica_devoluciones.pdf | p. 1 | 0.9764 |
| [4] | preguntas_frecuentes.pdf | p. 1 | 0.9716 |

El plazo general es de 30 días; los 14 de Electrónica son la excepción. Responder bien exige recuperar el pasaje correcto, no el primero que hable de devoluciones.

### ¿Qué categoría generó más ingresos?

> La categoría que generó más ingresos es Electrónica, con un importe total de 1,588,430.00 [1].

| [n] | Documento | Ubicación | Relevancia |
|-----|-----------|-----------|-----------:|
| [1] | pedidos_2026.csv | desglose por categoria | 0.9333 |
| [2] | devoluciones_2026.csv | desglose por categoria | 0.9313 |
| [3] | pedidos_2026.csv | resumen | 0.9256 |

Ninguna fila del CSV contiene esa suma: sale del fragmento de agregados que se calcula al indexar. La cifra coincide con el resultado de `pandas` sobre el mismo archivo.

### ¿Puedo pagar con criptomonedas?

> Los fragmentos proporcionados no mencionan si se aceptan criptomonedas como método de pago; haría falta el documento de términos y condiciones completo o una lista actualizada de métodos de pago aceptados.

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
