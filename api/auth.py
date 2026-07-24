"""
Protección de las operaciones de escritura.

La demo es pública: cualquiera puede consultar y abrir documentos. Agregar o
quitar documentos exige un token, porque en un servidor abierto eso significa
gastar la cuota de la API de otro.

Si la variable no está definida, la escritura queda abierta: en local se
trabaja sin fricción y clonar el repo no requiere configurar nada.
"""

import hmac
import os
from typing import Optional

from fastapi import Header, HTTPException

TOKEN_ENV = "ALURA_ADMIN_TOKEN"
TOKEN_HEADER = "X-Alura-Token"

MENSAJE_401 = (
    "Esta demo es pública en modo lectura. Para agregar o quitar documentos "
    "hace falta el token de administración."
)


def expected_token() -> str:
    """Token configurado, o cadena vacía si no hay ninguno."""
    return os.getenv(TOKEN_ENV, "").strip()


def write_protected() -> bool:
    """
    Si la escritura está protegida.

    Se lee en cada llamada y no al importar el módulo, para que las pruebas
    puedan cambiar el entorno y para no depender del orden de `load_dotenv()`.
    """
    return bool(expected_token())


def require_write_token(x_alura_token: Optional[str] = Header(default=None)) -> None:
    """Dependencia de guardia para los endpoints que modifican la biblioteca."""
    esperado = expected_token()
    if not esperado:
        return
    # compare_digest: la comparación no revela el token por el tiempo que tarda
    if not x_alura_token or not hmac.compare_digest(x_alura_token, esperado):
        raise HTTPException(status_code=401, detail=MENSAJE_401)
