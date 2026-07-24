"""
Comportamiento cuando el volumen de datos no es escribible.

En el despliegue real esto tumbaba el servidor entero en el arranque: el uid
del contenedor no coincidía con el dueño de data/ en el host. La aplicación
debe seguir en pie y responder consultas, con la escritura desactivada.
"""

import os

import pytest

import api.store as store


@pytest.fixture
def sin_permisos(monkeypatch, tmp_path):
    monkeypatch.setattr(store, "DATA_DIR", str(tmp_path))
    monkeypatch.setattr(store, "UPLOAD_DIR", str(tmp_path / "uploads"))
    monkeypatch.setattr(store, "REGISTRY_PATH", str(tmp_path / "uploads" / "registry.json"))
    monkeypatch.setattr(store, "SEED_FILES", [])

    real_makedirs = os.makedirs

    def denegar(path, *args, **kwargs):
        if "uploads" in str(path):
            raise PermissionError(13, "Permission denied")
        return real_makedirs(path, *args, **kwargs)

    monkeypatch.setattr(store.os, "makedirs", denegar)
    return store.Library()


def test_la_biblioteca_arranca_aunque_no_pueda_escribir(sin_permisos):
    # lo importante: llegar hasta aquí sin excepción
    estado = sin_permisos.state()
    assert estado["storage_error"]
    assert "no es escribible" in estado["storage_error"]


def test_agregar_da_un_error_claro_en_vez_de_reventar(sin_permisos):
    with pytest.raises(store.LibraryError) as exc:
        sin_permisos.add("x.csv", b"a,b\n1,2\n")
    assert "no es escribible" in str(exc.value)


def test_sin_problemas_de_permisos_no_se_reporta_error(monkeypatch, tmp_path):
    monkeypatch.setattr(store, "DATA_DIR", str(tmp_path))
    monkeypatch.setattr(store, "UPLOAD_DIR", str(tmp_path / "uploads"))
    monkeypatch.setattr(store, "REGISTRY_PATH", str(tmp_path / "uploads" / "registry.json"))
    monkeypatch.setattr(store, "SEED_FILES", [])

    assert store.Library().state()["storage_error"] is None
