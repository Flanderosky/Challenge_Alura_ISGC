"""
Genera el documento de ejemplos de respuestas del agente.

Consume el mismo endpoint que usa la interfaz (`/api/query`, por SSE), no una
ruta paralela: los tiempos y las fuentes que salen aquí son los reales del
sistema desplegado.

Uso:
    python scripts/generar_ejemplos.py
    python scripts/generar_ejemplos.py --base-url http://<IP>:8501
"""

import argparse
import json
import subprocess
from datetime import datetime, timezone
from typing import List, Optional

import requests

SALIDA = "docs/ejemplos_respuestas.md"

# Catálogo fijo: es lo que hace el documento reproducible. Cada pregunta
# demuestra algo distinto, y la última demuestra lo más importante.
PREGUNTAS = [
    ("¿Cuántos días de vacaciones corresponden por año?",
     "Recuperación sobre el PDF, con cita a la página concreta."),
    ("¿Qué tecnologías se usan en el back-end?",
     "Extrae varios datos de un mismo pasaje del PDF."),
    ("¿Cuál fue el total de ventas y el producto más vendido?",
     "Usa el fragmento de agregados del CSV: ninguna fila contiene el total."),
    ("¿Qué región generó más ingresos?",
     "Usa el fragmento de comparativa, calculado sobre todos los grupos."),
    ("¿Y cuál fue el promedio?",
     "Memoria conversacional: la pregunta solo se entiende con la anterior."),
    ("¿Cuál es la política de coche de empresa?",
     "El agente no encuentra la respuesta y lo dice, en vez de inventarla."),
]

# Índices (base 0) de las preguntas que se envían con el turno anterior
CON_HISTORIAL = {4}


def consultar(base_url: str, pregunta: str, history: List[dict]) -> dict:
    """Lanza la consulta y recoge los eventos del pipeline."""
    respuesta = requests.post(
        f"{base_url}/api/query",
        json={"question": pregunta, "history": history},
        stream=True,
        timeout=180,
    )
    respuesta.raise_for_status()

    texto, hits, done, error = "", [], {}, None
    for linea in respuesta.iter_lines(decode_unicode=True):
        if not linea or not linea.startswith("data:"):
            continue
        evento = json.loads(linea[5:])
        if evento["type"] == "token":
            texto += evento["text"]
        elif evento["type"] == "hits":
            hits = evento["hits"]
        elif evento["type"] == "done":
            done = evento
        elif evento["type"] == "error":
            error = evento["message"]

    return {
        "answer": (done.get("answer") or texto).strip(),
        "hits": hits,
        "timings": done.get("timings", {}),
        "model": done.get("model"),
        "error": error,
    }


def ms(valor: Optional[float]) -> str:
    if valor is None:
        return "—"
    return f"{valor / 1000:.2f} s" if valor >= 1000 else f"{round(valor)} ms"


def commit_actual() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], text=True
        ).strip()
    except (subprocess.SubprocessError, OSError):
        return "desconocido"


def bloque(numero: int, pregunta: str, nota: str, resultado: dict) -> str:
    partes = [f"### {numero}. {pregunta}", "", f"*{nota}*", ""]

    if resultado["error"]:
        partes += ["**Error**", "", f"> {resultado['error']}", ""]
        return "\n".join(partes)

    partes += ["**Respuesta**", ""]
    partes += [f"> {linea}" if linea else ">" for linea in resultado["answer"].split("\n")]
    partes += ["", "**Fuentes recuperadas**", "",
               "| [n] | Documento | Ubicación | Relevancia |",
               "|-----|-----------|-----------|-----------:|"]
    for hit in resultado["hits"]:
        partes.append(
            f"| [{hit['n']}] | {hit['filename']} | {hit['locator']} | {hit['score']:.4f} |"
        )

    t = resultado["timings"]
    partes += [
        "",
        f"**Tiempos** — vectorizar {ms(t.get('embedding'))} · buscar {ms(t.get('busqueda'))} · "
        f"primer token {ms(t.get('primer_token'))} · modelo {ms(t.get('modelo'))} · "
        f"**total {ms(t.get('total'))}**",
        "",
    ]
    return "\n".join(partes)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--salida", default=SALIDA)
    args = parser.parse_args()

    base_url = args.base_url.rstrip("/")
    estado = requests.get(f"{base_url}/api/state", timeout=30).json()
    if estado["status"] != "listo":
        raise SystemExit(f"El índice no está listo (estado: {estado['status']}). Espera y reintenta.")

    bloques, history, modelo = [], [], None
    for i, (pregunta, nota) in enumerate(PREGUNTAS):
        print(f"[{i + 1}/{len(PREGUNTAS)}] {pregunta}")
        resultado = consultar(base_url, pregunta, history if i in CON_HISTORIAL else [])
        modelo = modelo or resultado["model"]
        bloques.append(bloque(i + 1, pregunta, nota, resultado))
        if resultado["answer"]:
            history = [
                {"role": "user", "content": pregunta},
                {"role": "assistant", "content": resultado["answer"]},
            ]

    documentos = ", ".join(f"`{d['filename']}` ({d['chunks']} fragmentos)" for d in estado["documents"])
    cabecera = [
        "# Ejemplos de respuestas del agente",
        "",
        "Generado con `python scripts/generar_ejemplos.py`. Todas las respuestas salen del",
        "mismo endpoint que usa la interfaz, con los tiempos medidos en la ejecución real.",
        "",
        f"- **Fecha**: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        f"- **Commit**: `{commit_actual()}`",
        f"- **Servidor**: `{base_url}`",
        f"- **Modelo**: `{modelo or estado.get('model')}` · **k** = {estado.get('top_k')}",
        f"- **Biblioteca**: {documentos}",
        "",
        "---",
        "",
    ]

    pie = [
        "---",
        "",
        "> La temperatura del modelo es 0.3, así que la redacción puede variar entre",
        "> ejecuciones. La fecha y el commit de esta generación quedan arriba.",
        "",
    ]

    import os

    os.makedirs(os.path.dirname(args.salida) or ".", exist_ok=True)
    with open(args.salida, "w", encoding="utf-8") as handle:
        handle.write("\n".join(cabecera) + "\n".join(bloques) + "\n" + "\n".join(pie))

    print(f"\nEscrito en {args.salida}")


if __name__ == "__main__":
    main()
