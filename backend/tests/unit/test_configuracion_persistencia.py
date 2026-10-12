"""Configuración segura evaluada sin abrir conexiones."""

import pytest

from recon_platform.config import obtener_uri_mysql


def test_sin_configuracion_no_se_abre_persistencia(monkeypatch: pytest.MonkeyPatch) -> None:
    for nombre in ("DB_NAME", "DB_TEST_NAME", "DB_USER", "DB_PASSWORD"):
        monkeypatch.delenv(nombre, raising=False)
    assert obtener_uri_mysql() is None
    assert obtener_uri_mysql(pruebas=True) is None


def test_uri_codifica_clave_y_separa_esquemas(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DB_NAME", "recon_dev")
    monkeypatch.setenv("DB_TEST_NAME", "recon_tests")
    monkeypatch.setenv("DB_USER", "usuario")
    monkeypatch.setenv("DB_PASSWORD", "clave@local")
    assert "/recon_dev?charset=utf8mb4" in obtener_uri_mysql()
    assert "/recon_tests?charset=utf8mb4" in obtener_uri_mysql(pruebas=True)
    assert "clave%40local" in obtener_uri_mysql()


def test_pruebas_rechazan_base_de_desarrollo(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DB_NAME", "recon_dev")
    monkeypatch.setenv("DB_TEST_NAME", "RECON_DEV")
    monkeypatch.setenv("DB_USER", "usuario")
    monkeypatch.setenv("DB_PASSWORD", "clave_ficticia")
    with pytest.raises(ValueError, match="diferente"):
        obtener_uri_mysql(pruebas=True)


def test_configuracion_parcial_falla_sin_revelar_clave(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DB_NAME", "recon_dev")
    monkeypatch.delenv("DB_USER", raising=False)
    monkeypatch.setenv("DB_PASSWORD", "clave_ficticia")
    with pytest.raises(ValueError, match="incompleta") as error:
        obtener_uri_mysql()
    assert "clave_ficticia" not in str(error.value)
