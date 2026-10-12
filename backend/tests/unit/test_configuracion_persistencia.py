"""Configuración segura evaluada sin abrir conexiones."""

import pytest
from sqlalchemy.engine import make_url

from recon_platform import create_app
from recon_platform.config import obtener_uri_mysql


@pytest.fixture(autouse=True)
def limpiar_configuracion_mysql(monkeypatch: pytest.MonkeyPatch) -> None:
    for nombre in (
        "DB_NAME",
        "DB_USER",
        "DB_PASSWORD",
        "DB_TEST_NAME",
        "DB_TEST_USER",
        "DB_TEST_PASSWORD",
    ):
        monkeypatch.delenv(nombre, raising=False)


def configurar_bases_ficticias(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DB_NAME", "recon_dev")
    monkeypatch.setenv("DB_USER", "usuario_dev")
    monkeypatch.setenv("DB_PASSWORD", "clave_dev@ficticia")
    monkeypatch.setenv("DB_TEST_NAME", "recon_tests")
    monkeypatch.setenv("DB_TEST_USER", "usuario_test")
    monkeypatch.setenv("DB_TEST_PASSWORD", "clave_test@ficticia")


def test_sin_configuracion_solo_desarrollo_admite_modo_diagnostico() -> None:
    assert obtener_uri_mysql() is None
    with pytest.raises(ValueError, match="pruebas está incompleta"):
        create_app(pruebas=True)


def test_cada_modo_selecciona_su_base_usuario_y_clave(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    configurar_bases_ficticias(monkeypatch)

    desarrollo = make_url(create_app().config["SQLALCHEMY_DATABASE_URI"])
    pruebas = make_url(create_app(pruebas=True).config["SQLALCHEMY_DATABASE_URI"])

    assert (desarrollo.database, desarrollo.username, desarrollo.password) == (
        "recon_dev",
        "usuario_dev",
        "clave_dev@ficticia",
    )
    assert (pruebas.database, pruebas.username, pruebas.password) == (
        "recon_tests",
        "usuario_test",
        "clave_test@ficticia",
    )
    assert pruebas.query["charset"] == "utf8mb4"


@pytest.mark.parametrize("ausente", ["DB_TEST_NAME", "DB_TEST_USER", "DB_TEST_PASSWORD"])
def test_pruebas_rechazan_credencial_especifica_ausente_sin_heredar_desarrollo(
    monkeypatch: pytest.MonkeyPatch, ausente: str
) -> None:
    configurar_bases_ficticias(monkeypatch)
    monkeypatch.delenv(ausente)

    with pytest.raises(ValueError, match="pruebas está incompleta") as error:
        create_app(pruebas=True)
    assert "clave_dev@ficticia" not in str(error.value)
    assert "mysql+pymysql" not in str(error.value)


def test_pruebas_exigen_nombre_de_desarrollo_para_verificar_separacion(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    configurar_bases_ficticias(monkeypatch)
    monkeypatch.delenv("DB_NAME")

    with pytest.raises(ValueError, match="pruebas está incompleta"):
        obtener_uri_mysql(pruebas=True)


def test_pruebas_no_exigen_credenciales_de_desarrollo(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    configurar_bases_ficticias(monkeypatch)
    monkeypatch.delenv("DB_USER")
    monkeypatch.delenv("DB_PASSWORD")

    pruebas = make_url(obtener_uri_mysql(pruebas=True))
    assert pruebas.username == "usuario_test"


def test_pruebas_rechazan_base_de_desarrollo(monkeypatch: pytest.MonkeyPatch) -> None:
    configurar_bases_ficticias(monkeypatch)
    monkeypatch.setenv("DB_TEST_NAME", "RECON_DEV")

    with pytest.raises(ValueError, match="diferente"):
        obtener_uri_mysql(pruebas=True)


@pytest.mark.parametrize("ausente", ["DB_NAME", "DB_USER", "DB_PASSWORD"])
def test_configuracion_parcial_de_desarrollo_falla_sin_revelar_credenciales(
    monkeypatch: pytest.MonkeyPatch, ausente: str
) -> None:
    configurar_bases_ficticias(monkeypatch)
    monkeypatch.delenv(ausente)

    with pytest.raises(ValueError, match="incompleta") as error:
        obtener_uri_mysql()
    assert "clave_dev@ficticia" not in str(error.value)
    assert "mysql+pymysql" not in str(error.value)
