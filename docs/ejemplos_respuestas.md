# Ejemplos de respuestas del agente

Generado con `python scripts/generar_ejemplos.py`. Todas las respuestas salen del
mismo endpoint que usa la interfaz, con los tiempos medidos en la ejecución real.

- **Fecha**: 2026-07-24 21:00 UTC
- **Commit**: `9c56a42`
- **Servidor**: `http://localhost:8000`
- **Modelo**: `gemini-3.1-flash-lite` · **k** = 6
- **Biblioteca**: `politicas_ejemplo.pdf` (2 fragmentos), `ventas_ejemplo.csv` (7 fragmentos)

---
### 1. ¿Cuántos días de vacaciones corresponden por año?

*Recuperación sobre el PDF, con cita a la página concreta.*

**Respuesta**

> Todos los colaboradores tienen derecho a 15 días hábiles de vacaciones después de cada año de trabajo continuo [3].

**Fuentes recuperadas**

| [n] | Documento | Ubicación | Relevancia |
|-----|-----------|-----------|-----------:|
| [1] | ventas_ejemplo.csv | desglose por fecha | 0.3084 |
| [2] | ventas_ejemplo.csv | desglose por categoria | 0.3082 |
| [3] | politicas_ejemplo.pdf | p. 1 | 0.3081 |
| [4] | ventas_ejemplo.csv | desglose por region | 0.2681 |
| [5] | politicas_ejemplo.pdf | p. 1 | 0.2181 |
| [6] | ventas_ejemplo.csv | resumen | 0.1839 |

**Tiempos** — vectorizar 13 ms · buscar 0 ms · primer token 1.05 s · modelo 1.11 s · **total 1.13 s**

### 2. ¿Qué tecnologías se usan en el back-end?

*Extrae varios datos de un mismo pasaje del PDF.*

**Respuesta**

> La plataforma principal de la empresa utiliza Python en el back-end [1].

**Fuentes recuperadas**

| [n] | Documento | Ubicación | Relevancia |
|-----|-----------|-----------|-----------:|
| [1] | politicas_ejemplo.pdf | p. 1 | 0.4803 |
| [2] | politicas_ejemplo.pdf | p. 1 | 0.3992 |
| [3] | ventas_ejemplo.csv | desglose por region | 0.2444 |
| [4] | ventas_ejemplo.csv | desglose por categoria | 0.2357 |
| [5] | ventas_ejemplo.csv | desglose por fecha | 0.2257 |
| [6] | ventas_ejemplo.csv | resumen | 0.1199 |

**Tiempos** — vectorizar 11 ms · buscar 0 ms · primer token 554 ms · modelo 610 ms · **total 623 ms**

### 3. ¿Cuál fue el total de ventas y el producto más vendido?

*Usa el fragmento de agregados del CSV: ninguna fila contiene el total.*

**Respuesta**

> El total de ingreso sumando todos los registros es 286,150.00 [1]. El producto más frecuente es Laptop Pro [1].

**Fuentes recuperadas**

| [n] | Documento | Ubicación | Relevancia |
|-----|-----------|-----------|-----------:|
| [1] | ventas_ejemplo.csv | resumen | 0.4106 |
| [2] | ventas_ejemplo.csv | desglose por region | 0.3582 |
| [3] | politicas_ejemplo.pdf | p. 1 | 0.2702 |
| [4] | ventas_ejemplo.csv | desglose por fecha | 0.2481 |
| [5] | ventas_ejemplo.csv | desglose por categoria | 0.2210 |
| [6] | politicas_ejemplo.pdf | p. 1 | 0.2045 |

**Tiempos** — vectorizar 17 ms · buscar 0 ms · primer token 567 ms · modelo 1.52 s · **total 1.54 s**

### 4. ¿Qué región generó más ingresos?

*Usa el fragmento de comparativa, calculado sobre todos los grupos.*

**Respuesta**

> La región que generó más ingresos es la región Norte, con un total de 116,350.00 [1].

**Fuentes recuperadas**

| [n] | Documento | Ubicación | Relevancia |
|-----|-----------|-----------|-----------:|
| [1] | ventas_ejemplo.csv | desglose por region | 0.4233 |
| [2] | ventas_ejemplo.csv | resumen | 0.2586 |
| [3] | ventas_ejemplo.csv | desglose por fecha | 0.2533 |
| [4] | ventas_ejemplo.csv | desglose por categoria | 0.2307 |
| [5] | ventas_ejemplo.csv | filas 1–8 | 0.0788 |
| [6] | politicas_ejemplo.pdf | p. 1 | 0.0503 |

**Tiempos** — vectorizar 12 ms · buscar 0 ms · primer token 556 ms · modelo 685 ms · **total 700 ms**

### 5. ¿Y cuál fue el promedio?

*Memoria conversacional: la pregunta solo se entiende con la anterior.*

**Respuesta**

> El promedio de ingreso de la región Norte es 19,391.67 [1].

**Fuentes recuperadas**

| [n] | Documento | Ubicación | Relevancia |
|-----|-----------|-----------|-----------:|
| [1] | ventas_ejemplo.csv | desglose por region | 0.3994 |
| [2] | ventas_ejemplo.csv | desglose por fecha | 0.3901 |
| [3] | ventas_ejemplo.csv | desglose por categoria | 0.2665 |
| [4] | politicas_ejemplo.pdf | p. 1 | 0.1261 |
| [5] | politicas_ejemplo.pdf | p. 1 | 0.0908 |
| [6] | ventas_ejemplo.csv | resumen | 0.0390 |

**Tiempos** — vectorizar 14 ms · buscar 0 ms · primer token 690 ms · modelo 778 ms · **total 796 ms**

### 6. ¿Cuál es la política de coche de empresa?

*El agente no encuentra la respuesta y lo dice, en vez de inventarla.*

**Respuesta**

> Los fragmentos proporcionados no contienen información sobre la política de coche de empresa; haría falta el documento de políticas de beneficios o compensaciones para responder.

**Fuentes recuperadas**

| [n] | Documento | Ubicación | Relevancia |
|-----|-----------|-----------|-----------:|
| [1] | politicas_ejemplo.pdf | p. 1 | 0.2299 |
| [2] | ventas_ejemplo.csv | desglose por fecha | 0.1245 |
| [3] | ventas_ejemplo.csv | desglose por categoria | 0.0357 |
| [4] | ventas_ejemplo.csv | resumen | 0.0224 |
| [5] | ventas_ejemplo.csv | desglose por region | 0.0000 |
| [6] | politicas_ejemplo.pdf | p. 1 | 0.0000 |

**Tiempos** — vectorizar 14 ms · buscar 0 ms · primer token 588 ms · modelo 690 ms · **total 708 ms**

---

> La temperatura del modelo es 0.3, así que la redacción puede variar entre
> ejecuciones. La fecha y el commit de esta generación quedan arriba.
