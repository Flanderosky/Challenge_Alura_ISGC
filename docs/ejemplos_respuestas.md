# Ejemplos de respuestas del agente

Generado con `python scripts/generar_ejemplos.py`. Todas las respuestas salen del
mismo endpoint que usa la interfaz, con los tiempos medidos en la ejecución real.

- **Fecha**: 2026-07-24 21:33 UTC
- **Commit**: `0588255`
- **Servidor**: `http://localhost:8000`
- **Modelo**: `gemini-3.1-flash-lite` · **k** = 6
- **Biblioteca**: `politica_devoluciones.pdf` (6 fragmentos), `guia_envios.pdf` (4 fragmentos), `politica_privacidad.pdf` (4 fragmentos), `preguntas_frecuentes.pdf` (4 fragmentos), `terminos_condiciones.pdf` (5 fragmentos), `pedidos_2026.csv` (68 fragmentos), `devoluciones_2026.csv` (20 fragmentos)

---
### 1. ¿Cuánto tiempo tengo para devolver un producto electrónico?

*Dato concreto de un PDF, con cita a la página exacta. El plazo de Electrónica es una excepción al general, así que responderlo bien exige recuperar el pasaje correcto.*

**Respuesta**

> Los productos de la categoría Electrónica tienen un plazo de 14 días naturales para solicitar la devolución [1], [4].

**Fuentes recuperadas**

| [n] | Documento | Ubicación | Relevancia |
|-----|-----------|-----------|-----------:|
| [1] | politica_devoluciones.pdf | p. 1 | 0.9817 |
| [2] | politica_devoluciones.pdf | p. 1 | 0.9798 |
| [3] | politica_devoluciones.pdf | p. 2 | 0.9758 |
| [4] | preguntas_frecuentes.pdf | p. 1 | 0.9744 |
| [5] | preguntas_frecuentes.pdf | p. 1 | 0.9735 |
| [6] | politica_devoluciones.pdf | p. 2 | 0.9676 |

**Tiempos** — vectorizar 32 ms · buscar 0 ms · primer token 586 ms · modelo 692 ms · **total 728 ms**

### 2. ¿Cuánto cuesta el envío y cuándo es gratis?

*Combina varias condiciones de un mismo documento.*

**Respuesta**

> El envío estándar tiene un costo de 99 pesos mexicanos y es gratuito en pedidos cuyo importe iguale o supere los 999 pesos [2]. El envío exprés tiene un costo de 199 pesos y no tiene umbral de gratuidad [2]. El envío el mismo día tiene un costo de 299 pesos [2].

**Fuentes recuperadas**

| [n] | Documento | Ubicación | Relevancia |
|-----|-----------|-----------|-----------:|
| [1] | preguntas_frecuentes.pdf | p. 1 | 0.9823 |
| [2] | guia_envios.pdf | p. 1 | 0.9742 |
| [3] | preguntas_frecuentes.pdf | p. 1 | 0.9671 |
| [4] | preguntas_frecuentes.pdf | p. 1 | 0.9646 |
| [5] | politica_devoluciones.pdf | p. 1 | 0.9610 |
| [6] | politica_devoluciones.pdf | p. 2 | 0.9600 |

**Tiempos** — vectorizar 27 ms · buscar 0 ms · primer token 592 ms · modelo 839 ms · **total 871 ms**

### 3. ¿Qué pasa si nadie recibe el paquete?

*Pregunta en lenguaje natural que no usa ninguna palabra del documento: obliga a la búsqueda semántica a trabajar.*

**Respuesta**

> La paquetería realiza hasta tres intentos de entrega en días hábiles consecutivos [2][5]. Tras el tercer intento fallido, el paquete se resguarda 5 días hábiles en la sucursal más cercana antes de retornar al centro de distribución de Meridia [2]. Si el pedido retorna por no haber sido recogido, se reembolsa el importe del producto descontando el costo del envío original [2][3].

**Fuentes recuperadas**

| [n] | Documento | Ubicación | Relevancia |
|-----|-----------|-----------|-----------:|
| [1] | guia_envios.pdf | p. 1 | 0.9518 |
| [2] | guia_envios.pdf | p. 1 | 0.9485 |
| [3] | guia_envios.pdf | p. 2 | 0.9468 |
| [4] | preguntas_frecuentes.pdf | p. 1 | 0.9448 |
| [5] | preguntas_frecuentes.pdf | p. 1 | 0.9374 |
| [6] | politica_devoluciones.pdf | p. 1 | 0.9352 |

**Tiempos** — vectorizar 23 ms · buscar 0 ms · primer token 510 ms · modelo 759 ms · **total 786 ms**

### 4. ¿Qué categoría generó más ingresos?

*Sale del fragmento de comparativa del CSV, calculado sobre todos los grupos. Ninguna fila contiene esa suma.*

**Respuesta**

> La categoría que generó más ingresos es Electrónica, con un importe total de 1,588,430.00 [1].

**Fuentes recuperadas**

| [n] | Documento | Ubicación | Relevancia |
|-----|-----------|-----------|-----------:|
| [1] | pedidos_2026.csv | desglose por categoria | 0.9333 |
| [2] | devoluciones_2026.csv | desglose por categoria | 0.9313 |
| [3] | pedidos_2026.csv | desglose por canal | 0.9298 |
| [4] | pedidos_2026.csv | comparativa por region | 0.9261 |
| [5] | pedidos_2026.csv | resumen | 0.9256 |
| [6] | pedidos_2026.csv | desglose por fecha | 0.9222 |

**Tiempos** — vectorizar 32 ms · buscar 0 ms · primer token 578 ms · modelo 663 ms · **total 698 ms**

### 5. ¿Y cuál es el motivo de devolución más frecuente?

*Memoria conversacional y salto a otro documento en la misma conversación.*

**Respuesta**

> El motivo de devolución más frecuente es Producto defectuoso, con 22 registros [1].

**Fuentes recuperadas**

| [n] | Documento | Ubicación | Relevancia |
|-----|-----------|-----------|-----------:|
| [1] | devoluciones_2026.csv | desglose por motivo | 0.9621 |
| [2] | devoluciones_2026.csv | comparativa por fecha_solicitud | 0.9588 |
| [3] | politica_devoluciones.pdf | p. 1 | 0.9568 |
| [4] | politica_devoluciones.pdf | p. 1 | 0.9559 |
| [5] | preguntas_frecuentes.pdf | p. 1 | 0.9541 |
| [6] | politica_devoluciones.pdf | p. 1 | 0.9538 |

**Tiempos** — vectorizar 27 ms · buscar 0 ms · primer token 521 ms · modelo 624 ms · **total 655 ms**

### 6. ¿Puedo pagar con criptomonedas?

*El agente no encuentra la respuesta y lo dice, en vez de inventarla.*

**Respuesta**

> Los fragmentos proporcionados no mencionan si se aceptan criptomonedas como método de pago; haría falta el documento de términos y condiciones completo o una lista actualizada de métodos de pago aceptados.

**Fuentes recuperadas**

| [n] | Documento | Ubicación | Relevancia |
|-----|-----------|-----------|-----------:|
| [1] | preguntas_frecuentes.pdf | p. 1 | 0.9494 |
| [2] | politica_privacidad.pdf | p. 1 | 0.9387 |
| [3] | terminos_condiciones.pdf | p. 2 | 0.9320 |
| [4] | politica_privacidad.pdf | p. 2 | 0.9318 |
| [5] | preguntas_frecuentes.pdf | p. 1 | 0.9303 |
| [6] | terminos_condiciones.pdf | p. 2 | 0.9291 |

**Tiempos** — vectorizar 22 ms · buscar 0 ms · primer token 694 ms · modelo 860 ms · **total 886 ms**

---

> La temperatura del modelo es 0.3, así que la redacción puede variar entre
> ejecuciones. La fecha y el commit de esta generación quedan arriba.
