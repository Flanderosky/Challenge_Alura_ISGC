"""
Cuota diaria y caché de respuestas.

Protegen la disponibilidad de la demo pública: el modelo corre sobre una cuota
gratuita que un bucle automatizado agotaría en minutos.
"""

import pytest

from api.limites import CacheRespuestas, Cuota


@pytest.fixture
def cuota(monkeypatch):
    monkeypatch.setenv("ALURA_LIMITE_DIARIO_IP", "3")
    monkeypatch.setenv("ALURA_LIMITE_DIARIO_TOTAL", "5")
    return Cuota()


def test_permite_hasta_el_limite_por_ip(cuota):
    for _ in range(3):
        assert cuota.disponible("1.1.1.1") is None
        cuota.consumir("1.1.1.1")

    motivo = cuota.disponible("1.1.1.1")
    assert motivo and "3 consultas" in motivo


def test_cada_ip_tiene_su_propia_cuenta(cuota):
    for _ in range(3):
        cuota.consumir("1.1.1.1")
    assert cuota.disponible("2.2.2.2") is None


def test_el_tope_global_corta_a_todos(cuota):
    for ip in ("1.1.1.1", "2.2.2.2"):
        for _ in range(3):
            if cuota.disponible(ip) is None:
                cuota.consumir(ip)

    motivo = cuota.disponible("3.3.3.3")
    assert motivo and "tope de consultas de hoy" in motivo


def test_sin_variables_no_hay_limite(monkeypatch):
    monkeypatch.setenv("ALURA_LIMITE_DIARIO_IP", "0")
    monkeypatch.setenv("ALURA_LIMITE_DIARIO_TOTAL", "0")
    libre = Cuota()
    for _ in range(50):
        assert libre.disponible("1.1.1.1") is None
        libre.consumir("1.1.1.1")


def test_el_estado_informa_lo_que_queda(cuota):
    cuota.consumir("1.1.1.1")
    estado = cuota.estado("1.1.1.1")
    assert estado["limite"] == 3
    assert estado["usadas"] == 1
    assert estado["restantes"] == 2


def test_la_cache_devuelve_la_respuesta_guardada():
    cache = CacheRespuestas()
    clave = cache.clave("¿Cuánto tarda el envío?", ("doc:1", "doc:2"))
    assert cache.obtener(clave) is None

    cache.guardar(clave, "De 3 a 5 días hábiles.")
    assert cache.obtener(clave) == "De 3 a 5 días hábiles."


def test_la_cache_ignora_mayusculas_y_espacios():
    cache = CacheRespuestas()
    cache.guardar(cache.clave("¿Cuánto  tarda?", ("a",)), "Tres días.")
    assert cache.obtener(cache.clave("¿CUÁNTO TARDA?", ("a",))) == "Tres días."


def test_si_cambian_los_fragmentos_la_respuesta_no_se_reutiliza():
    # la biblioteca cambió: la respuesta vieja podría ya no ser cierta
    cache = CacheRespuestas()
    cache.guardar(cache.clave("¿Cuánto tarda?", ("a",)), "Tres días.")
    assert cache.obtener(cache.clave("¿Cuánto tarda?", ("b",))) is None
