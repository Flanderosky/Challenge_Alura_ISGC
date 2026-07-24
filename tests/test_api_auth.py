"""
Protección de escritura de la API.

Lo que se comprueba no es solo que la dependencia funcione, sino que esté
conectada a los endpoints que modifican la biblioteca: olvidarse del
`dependencies=[...]` es exactamente el fallo que deja el servidor abierto.
"""

import pytest
from fastapi.testclient import TestClient

from api.auth import TOKEN_ENV, require_write_token, write_protected
from api.main import app

TOKEN = "token-de-prueba-123"

# Sin el gestor de contexto no se disparan los eventos de arranque, así que
# estas pruebas no construyen el índice ni instancian el modelo.
client = TestClient(app)


@pytest.fixture
def sin_token(monkeypatch):
    monkeypatch.delenv(TOKEN_ENV, raising=False)


@pytest.fixture
def con_token(monkeypatch):
    monkeypatch.setenv(TOKEN_ENV, TOKEN)


def _rutas_de_escritura():
    """Las rutas que modifican la biblioteca, tal como las registra FastAPI."""
    objetivo = {("/api/documents", "POST"), ("/api/documents/{doc_id}", "DELETE")}
    for route in app.routes:
        for metodo in getattr(route, "methods", set()):
            if (getattr(route, "path", ""), metodo) in objetivo:
                yield route


def test_los_endpoints_de_escritura_llevan_la_guardia():
    rutas = list(_rutas_de_escritura())
    assert len(rutas) == 2, "deberían existir el alta y la baja de documentos"
    for route in rutas:
        llamadas = [d.call for d in route.dependant.dependencies]
        assert require_write_token in llamadas, f"{route.path} quedó sin protección"


def test_sin_variable_la_escritura_esta_abierta(sin_token):
    assert write_protected() is False
    assert client.get("/api/state").json()["write_protected"] is False
    assert client.get("/api/admin/check").status_code == 200


def test_con_variable_la_escritura_exige_token(con_token):
    assert write_protected() is True
    assert client.get("/api/state").json()["write_protected"] is True

    assert client.get("/api/admin/check").status_code == 401
    assert client.get("/api/admin/check", headers={"X-Alura-Token": "otro"}).status_code == 401
    assert client.get("/api/admin/check", headers={"X-Alura-Token": TOKEN}).status_code == 200


def test_borrar_sin_token_no_llega_al_almacen(con_token):
    respuesta = client.delete("/api/documents/inexistente")
    # 401 y no 404: la guardia corta antes de tocar la biblioteca
    assert respuesta.status_code == 401
    assert respuesta.json()["detail"]


def test_subir_sin_token_es_rechazado(con_token):
    respuesta = client.post("/api/documents", files={"file": ("x.csv", b"a,b\n1,2\n", "text/csv")})
    assert respuesta.status_code == 401


def test_la_lectura_sigue_siendo_publica(con_token):
    # el evaluador entra sin credenciales y tiene que poder consultar
    assert client.get("/api/state").status_code == 200


def test_el_estado_nunca_expone_el_token(con_token):
    assert TOKEN not in client.get("/api/state").text
