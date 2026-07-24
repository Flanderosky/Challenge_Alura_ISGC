# 🤖 Alura Agente

Asistente de inteligencia artificial para responder preguntas en lenguaje natural a partir de documentos internos en formato **PDF** o **CSV**.

Este proyecto fue desarrollado como desafío final del programa **Alura Agente** y combina procesamiento de documentos, recuperación de información (RAG) y despliegue en la nube con Oracle Cloud Infrastructure (OCI).

---

## 🎯 Objetivo

Facilitar el acceso a la información contenida en manuales, informes, políticas y hojas de cálculo internas, permitiendo que cualquier colaborador haga preguntas directas y reciba respuestas claras sin necesidad de abrir los archivos.

---

## 🏗️ Arquitectura

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   Navegador     │────▶│  Streamlit (UI)  │────▶│  LangChain RAG  │
│   del usuario   │◀────│    Puerto 8501   │◀────│   + LLM (Cohere │
└─────────────────┘     └──────────────────┘     │   / OpenAI)     │
                                                 └────────┬────────┘
                                                          │
                              ┌───────────────────────────┼───────────┐
                              │                           ▼           │
                              │  ┌──────────────┐   ┌─────────────┐  │
                              │  │  Carga PDF   │   │  Embeddings │  │
                              │  │     CSV      │──▶│   FAISS     │  │
                              │  └──────────────┘   └─────────────┘  │
                              │        Docker / OCI Compute          │
                              └──────────────────────────────────────┘
```

### Flujo

1. **Carga de documentos**: el usuario sube un PDF o CSV, o se usa el documento de ejemplo.
2. **Procesamiento**: el archivo se divide en fragmentos y se convierte en vectores con `sentence-transformers`.
3. **Indexación**: los vectores se almacenan en `FAISS` para búsqueda semántica rápida.
4. **Pregunta y respuesta**: LangChain recupera los fragmentos más relevantes y el LLM genera una respuesta clara basada únicamente en el contexto.

---

## 🛠️ Tecnologías y herramientas

- **Python 3.12**
- **Streamlit** — interfaz web
- **LangChain** — orquestación de RAG
- **PyPDF** — lectura de PDFs
- **Pandas** — lectura de CSVs
- **FAISS** — base de datos vectorial en memoria
- **langchain-huggingface** — embeddings locales con sentence-transformers
- **Cohere / OpenAI** — modelos de lenguaje
- **Docker** — contenedorización
- **OCI Compute** — despliegue en la nube

---

## 📁 Estructura del repositorio

```
alura-agente/
├── app.py                  # Aplicación Streamlit
├── requirements.txt        # Dependencias Python
├── Dockerfile              # Imagen para despliegue
├── docker-compose.yml      # Orquestación local
├── .env.example            # Variables de entorno de ejemplo
├── data/
│   ├── ventas_ejemplo.csv       # Datos de ejemplo
│   └── politicas_ejemplo.pdf    # Documento PDF de ejemplo
├── src/
│   ├── loader.py           # Carga de PDF y CSV
│   ├── vectorstore.py      # Creación del índice FAISS
│   └── agent.py            # Configuración del LLM y cadena QA
├── tests/
│   └── test_agent.py       # Pruebas básicas
└── README.md               # Este archivo
```

---

## 🚀 Cómo ejecutar el proyecto

### 1. Clonar el repositorio

```bash
git clone https://github.com/tu-usuario/alura-agente.git
cd alura-agente
```

### 2. Crear entorno virtual e instalar dependencias

```bash
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Configurar variables de entorno

```bash
cp .env.example .env
```

Edita `.env` con tu proveedor y clave de API:

```env
LLM_PROVIDER=cohere
COHERE_API_KEY=tu_cohere_api_key
COHERE_MODEL=command-r
```

También puedes usar OpenAI:

```env
LLM_PROVIDER=openai
OPENAI_API_KEY=tu_openai_api_key
OPENAI_MODEL=gpt-3.5-turbo
```

### 4. Ejecutar localmente

```bash
streamlit run app.py
```

Abre tu navegador en `http://localhost:8501`.

---

## 🐳 Ejecutar con Docker

```bash
# Construir imagen
docker build -t alura-agente .

# Ejecutar con variables de entorno
docker run -p 8501:8501 --env-file .env alura-agente
```

O con Docker Compose:

```bash
docker-compose up --build
```

---

## ☁️ Despliegue en OCI Compute

### Paso a paso sugerido

1. **Crear una instancia** en OCI Compute:
   - Forma: `VM.Standard.E2.1.Micro` (free tier) o superior.
   - Sistema operativo: Ubuntu 22.04 o Oracle Linux 8.
   - Añadir tu clave SSH y anotar la IP pública.

2. **Abrir el puerto 8501**:
   - En la *Security List* del subnet de la instancia, agregar una regla de entrada:
     - Tipo: `Stateful`
     - Protocolo: `TCP`
     - Puerto destino: `8501`
     - Origen: `0.0.0.0/0`

3. **Conectarse por SSH**:

```bash
ssh -i ~/.oci/llave.pem ubuntu@<IP_PUBLICA>
```

4. **Instalar Docker**:

```bash
sudo apt-get update
sudo apt-get install -y docker.io docker-compose
sudo usermod -aG docker $USER
newgrp docker
```

5. **Subir el código**:

```bash
# Desde tu máquina local
git clone https://github.com/tu-usuario/alura-agente.git
# o
scp -r -i ~/.oci/llave.pem ./alura-agente ubuntu@<IP_PUBLICA>:/home/ubuntu/
```

6. **Desplegar la aplicación**:

```bash
cd alura-agente
cp .env.example .env
nano .env  # Agrega tus claves de API
docker-compose up -d --build
```

7. **Verificar**:

```bash
docker logs -f alura-agente
```

Accede desde el navegador a:

```
http://<IP_PUBLICA>:8501
```

---

## 💬 Ejemplos de preguntas que el agente puede responder

### Con el CSV de ventas (`data/ventas_ejemplo.csv`)

- **Pregunta:** ¿Cuál fue el producto más vendido en diciembre de 2015?
- **Pregunta:** ¿Cuántas unidades de `Mouse Inalámbrico` se vendieron en total?
- **Pregunta:** ¿Qué región generó más ingresos?

### Con el PDF de políticas (`data/politicas_ejemplo.pdf`)

- **Pregunta:** ¿Cuántos días de vacaciones corresponden a los colaboradores?
- **Pregunta:** ¿Qué lenguajes y tecnologías se usan en la plataforma?
- **Pregunta:** ¿Cuál es el horario de trabajo del equipo de tecnología?

---

## ✅ Ejemplos de respuestas generadas

> **Pregunta:** ¿Cuál fue el producto más vendido en diciembre de 2015?
>
> **Respuesta:** El producto más vendido en diciembre de 2015 fue la **Laptop Pro**, con un total de 160 unidades vendidas en las diferentes regiones.

> **Pregunta:** ¿Qué tecnologías se usan en el back-end de la plataforma?
>
> **Respuesta:** Según el documento, el back-end utiliza **Python**, la base de datos principal es **PostgreSQL** y se usa **Docker** para el despliegue de servicios.

*(Las respuestas reales dependen del modelo de lenguaje configurado y del documento cargado.)*

---

## 🧪 Pruebas

```bash
pytest tests/
```

> **Nota:** las pruebas del LLM requieren una clave de API configurada. Las pruebas de carga y vectorización funcionan sin conexión a APIs externas.

---

## ☁️ Evidencia del deploy en OCI

La aplicación fue desplegada exitosamente en OCI Compute.

- **URL pública:** *(agregar aquí la URL de tu instancia, ej. `http://<IP_PUBLICA>:8501`)*
- **Captura de pantalla:** *(agregar aquí la imagen del agente funcionando en la nube)*

---

## ⚠️ Notas importantes

- **Nunca subas tu archivo `.env` con claves reales** al repositorio; está incluido en `.gitignore`.
- El proyecto usa un modelo de embeddings local, por lo que no requiere conexión a internet para indexar documentos.
- El LLM sí requiere una clave de API de Cohere u OpenAI.
- Para OCI free tier, recomendamos Cohere u OpenAI para evitar consumir recursos de CPU/GPU en la instancia.

---

## 📄 Licencia

Este proyecto es de uso educativo para el desafío final de Alura.

---

## 🙋 Autor

Desarrollado por **[Tu nombre]** como parte del desafío final **Alura Agente**.
