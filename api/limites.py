"""
Cuota de consultas y caché de respuestas.

La demo es pública y el modelo corre sobre una cuota gratuita. Sin un tope,
un bucle automatizado la agota en minutos y el día de la evaluación el agente
no responde. El límite protege la disponibilidad, no un gasto.

Los contadores viven en memoria del proceso, igual que el índice. Es coherente
con el resto de la arquitectura: un solo worker.
"""

import os
import threading
from collections import OrderedDict
from datetime import date
from typing import Optional, Tuple

CACHE_MAX = 200


def _entero(nombre: str, defecto: int) -> int:
    try:
        return max(0, int(os.getenv(nombre, str(defecto))))
    except ValueError:
        return defecto


def limite_ip() -> int:
    """Consultas al modelo por dirección IP y día. 0 desactiva el límite."""
    return _entero("ALURA_LIMITE_DIARIO_IP", 5)


def limite_total() -> int:
    """Consultas al modelo por día, sumando a todo el mundo. 0 desactiva el límite."""
    return _entero("ALURA_LIMITE_DIARIO_TOTAL", 200)


class Cuota:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._dia = date.today()
        self._por_ip: dict = {}
        self._total = 0

    def _al_dia(self) -> None:
        hoy = date.today()
        if hoy != self._dia:
            self._dia = hoy
            self._por_ip.clear()
            self._total = 0

    def estado(self, ip: str) -> dict:
        with self._lock:
            self._al_dia()
            tope_ip, tope_total = limite_ip(), limite_total()
            usadas = self._por_ip.get(ip, 0)
            return {
                "limite": tope_ip,
                "usadas": usadas,
                "restantes": None if not tope_ip else max(0, tope_ip - usadas),
                "restantes_global": None if not tope_total else max(0, tope_total - self._total),
            }

    def disponible(self, ip: str) -> Optional[str]:
        """Devuelve None si se puede consultar, o el motivo por el que no."""
        with self._lock:
            self._al_dia()
            tope_ip, tope_total = limite_ip(), limite_total()
            if tope_total and self._total >= tope_total:
                return (
                    "La demo alcanzó su tope de consultas de hoy. Se reinicia mañana. "
                    "En el README hay ejemplos de respuestas reales por si quieres verlas ahora."
                )
            if tope_ip and self._por_ip.get(ip, 0) >= tope_ip:
                return (
                    f"Has usado tus {tope_ip} consultas de hoy. El límite existe para que la "
                    "cuota gratuita del modelo siga disponible para el resto. Se reinicia mañana."
                )
            return None

    def consumir(self, ip: str) -> None:
        """Se llama solo cuando de verdad se invocó al modelo."""
        with self._lock:
            self._al_dia()
            self._por_ip[ip] = self._por_ip.get(ip, 0) + 1
            self._total += 1


class CacheRespuestas:
    """
    Guarda la respuesta de una pregunta ya contestada.

    La clave incluye los fragmentos recuperados: si la biblioteca cambia y la
    búsqueda devuelve otra cosa, la respuesta vieja deja de servir y se descarta
    sola.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._datos: OrderedDict = OrderedDict()

    @staticmethod
    def clave(pregunta: str, chunk_ids: Tuple[str, ...]) -> tuple:
        return (" ".join(pregunta.lower().split()), chunk_ids)

    def obtener(self, clave: tuple) -> Optional[str]:
        with self._lock:
            if clave not in self._datos:
                return None
            self._datos.move_to_end(clave)
            return self._datos[clave]

    def guardar(self, clave: tuple, respuesta: str) -> None:
        if not respuesta:
            return
        with self._lock:
            self._datos[clave] = respuesta
            self._datos.move_to_end(clave)
            while len(self._datos) > CACHE_MAX:
                self._datos.popitem(last=False)

    def limpiar(self) -> None:
        with self._lock:
            self._datos.clear()


cuota = Cuota()
cache = CacheRespuestas()
