"""Guardas preparadas de 0005 probadas sin conexiones MySQL."""

import importlib
import importlib.util
from pathlib import Path

import pytest


@pytest.fixture
def verificador(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[2] / "scripts"))
    return importlib.import_module("verificar_recon_tests_0005")


class ConexionGrants:
    def __init__(self, grants):
        self.grants = grants

    def execute(self, consulta):
        assert "SHOW GRANTS FOR CURRENT_USER()" in str(consulta)
        return [(grant,) for grant in self.grants]


def test_permiso_directo_completo_para_migracion(verificador):
    verificador.validar_privilegios_migracion(ConexionGrants([
        "GRANT SELECT, INSERT, UPDATE, CREATE, INDEX, REFERENCES ON `recon_tests`.* TO 'recon_test_app'@'localhost'"
    ]), "recon_tests")
    verificador.validar_privilegios_migracion(ConexionGrants([
        "GRANT ALL PRIVILEGES ON `recon_dev`.* TO 'recon_dev_app'@'localhost'"
    ]), "recon_dev")


@pytest.mark.parametrize("grant", [
    "GRANT SELECT, INSERT, CREATE, INDEX, REFERENCES ON `recon_tests`.* TO 'recon_test_app'@'localhost'",
    "GRANT ALL PRIVILEGES ON `recon_dev`.* TO 'recon_test_app'@'localhost'",
    "GRANT USAGE ON *.* TO 'recon_test_app'@'localhost'",
])
def test_permiso_incompleto_o_de_otra_base_no_habilita_migracion(verificador, grant):
    with pytest.raises(verificador.VerificacionFallida):
        verificador.validar_privilegios_migracion(ConexionGrants([grant]), "recon_tests")


def test_revision_0005_cabe_en_alembic_version(verificador):
    ruta = Path(__file__).resolve().parents[2] / "migrations" / "versions" / "0005_puntos_edge_auditoria.py"
    spec = importlib.util.spec_from_file_location("revision_0005_preparada", ruta)
    assert spec is not None and spec.loader is not None
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    assert modulo.revision == verificador.REVISION
    assert modulo.down_revision == "0004_auditoria_personas"
    assert len(modulo.revision) <= 32


def test_visibilidad_respaldo_pruebas_exige_privilegios_directos(verificador):
    modulo = importlib.import_module("verificar_objetos_recon_tests_0005")
    suficientes = [
        "GRANT SELECT, SHOW_ROUTINE ON *.* TO 'auditor'@'localhost'",
        "GRANT EVENT, TRIGGER ON `recon_tests`.* TO 'auditor'@'localhost'",
    ]
    assert modulo.visibilidad_suficiente(suficientes)
    assert not modulo.visibilidad_suficiente(suficientes[:1])
    assert not modulo.visibilidad_suficiente([
        suficientes[0], "GRANT EVENT, TRIGGER ON `recon_dev`.* TO 'auditor'@'localhost'"])
    assert not modulo.visibilidad_suficiente(suficientes + [
        "REVOKE TRIGGER ON `recon_tests`.* FROM 'auditor'@'localhost'"])


@pytest.mark.parametrize("nombre,base,mensaje", [
    ("verificar_recon_tests_0004", "recon_tests", "Falta configuración explícita"),
    ("verificar_recon_tests_0005", "recon_tests", "Falta configuración explícita"),
    ("verificar_recon_dev_0004", "recon_dev", "configuración MySQL de desarrollo está incompleta"),
    ("verificar_recon_dev_0005", "recon_dev", "Falta URI"),
    ("verificar_recon_0006", "recon_tests", "Configuración explícita incompleta"),
    ("verificar_recon_0006", "recon_dev", "Configuración explícita incompleta"),
])
@pytest.mark.parametrize("etapa", ["antes", "despues"])
def test_uri_ausente_detiene_verificador_antes_de_crear_motor(
    verificador, monkeypatch, tmp_path, nombre: str, base: str, mensaje: str, etapa: str,
):
    modulo = importlib.import_module(nombre)
    for variable, valor in {
        "DB_HOST": "127.0.0.1", "DB_PORT": "3306", "DB_NAME": "recon_dev",
        "DB_USER": "recon_dev_app", "DB_PASSWORD": "clave-ficticia",
        "DB_TEST_NAME": "recon_tests", "DB_TEST_USER": "recon_test_app",
        "DB_TEST_PASSWORD": "clave-ficticia",
    }.items():
        monkeypatch.setenv(variable, valor)
    monkeypatch.setattr(modulo, "obtener_uri_mysql", lambda **_opciones: None)

    def motor_prohibido(*_args, **_kwargs):
        pytest.fail("Una URI ausente no puede alcanzar la creación del motor.")

    monkeypatch.setattr(modulo, "create_engine", motor_prohibido)
    error_esperado = (modulo.VerificacionFallida if nombre in {
        "verificar_recon_tests_0004", "verificar_recon_tests_0005", "verificar_recon_dev_0004",
    } else ValueError)
    with pytest.raises(error_esperado, match=mensaje):
        if nombre == "verificar_recon_0006":
            modulo.verificar(base, etapa, None, tmp_path / "estado-ficticio.json")
        elif base == "recon_dev":
            modulo.verificar(etapa, comparar=tmp_path / "estado-ficticio.json")
        else:
            modulo.verificar(etapa)


def test_helper_integracion_termina_con_error_sanitizado():
    ruta = Path(__file__).resolve().parents[1] / "integration" / "conftest.py"
    spec = importlib.util.spec_from_file_location("guardas_mysql_unitarias", ruta)
    assert spec is not None and spec.loader is not None
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    with pytest.raises(pytest.exit.Exception, match="motivo ficticio") as error:
        modulo._detener("motivo ficticio")
    assert error.value.returncode == 2
