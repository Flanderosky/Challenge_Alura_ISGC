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

## Por qué hay un límite de consultas

La demo es pública y el modelo corre sobre la **cuota gratuita** de Google Gemini. Sin un tope, un bucle automatizado la agota en minutos y el agente deja de responder justo cuando alguien quiere probarlo. El límite no protege un gasto: protege la disponibilidad.

Tres detalles del diseño:

- **Las respuestas ya dadas no consumen cuota.** Si alguien repite una pregunta que ya se contestó sobre los mismos fragmentos, se sirve la respuesta guardada sin llamar al modelo. La caché se invalida sola cuando cambia la biblioteca.
- **El contador se muestra en la cabecera**, para que se vea cuántas consultas quedan en vez de toparse con un error sin aviso.
- **El token de administración se salta el límite**, así que quien mantiene la instancia siempre puede probarla.

---

## Despliegue en OCI Compute

La aplicación corre en una instancia **OCI Compute `VM.Standard.A1.Flex`** (Ampere, aarch64, free tier — 4 OCPU / 24 GB, Ubuntu), publicada en el puerto **8501**.

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

---

## Evidencia del despliegue
<img width="910" height="910" alt="image" src="https://github.com/user-attachments/assets/083c5b73-b7a2-4839-83e7-7e26cd010949" />

<img width="999" height="138" alt="image" src="https://github.com/user-attachments/assets/c0d5a751-6563-4727-a94b-42435ff26e54" />



---

## Pruebas

```bash
pip install -r requirements-dev.txt
pytest tests/
```

18 pruebas, ninguna requiere clave de API. Cubren carga y fragmentación con procedencia, los agregados y desgloses del CSV, la relevancia normalizada, la construcción del prompt y la protección de escritura de la API.

---

## Licencia

Uso educativo, desafío final de Alura.
