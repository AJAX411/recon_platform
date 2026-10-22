"""Rutas de preflight 0006 aisladas: no se abre ninguna conexión MySQL."""

import importlib
from contextlib import nullcontext
from pathlib import Path

import pytest


@pytest.fixture
def modulo(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[2] / "scripts"))
    return importlib.import_module("verificar_recon_0006")


class Filas:
    def __init__(self, filas):
        self.filas = filas

    def all(self):
        return self.filas

    def scalars(self):
        return self


class ConexionFicticia:
    def __init__(self, modulo, *, roles=None, superadmin_activo=1,
                 base="recon_dev", etapa="antes"):
        self.modulo = modulo
        self.roles = roles or ["SUPERADMIN", "ADMINISTRADOR", "OPERADOR"]
        self.superadmin_activo = superadmin_activo
        self.base = base
        self.etapa = etapa

    def execute(self, consulta):
        sql = str(consulta)
        if "information_schema.TABLES" in sql:
            tablas = self.modulo.TABLAS_ANTERIORES | (
                {"evento_acceso"} if self.etapa == "despues" else set())
            return Filas([(tabla, "InnoDB") for tabla in tablas])
        if "version_num FROM alembic_version" in sql:
            return Filas([self.modulo.REVISION_NUEVA if self.etapa == "despues"
                          else self.modulo.REVISION_ANTERIOR])
        if "REFERENTIAL_CONSTRAINTS" in sql:
            return Filas([("fk_persona_tipo_persona", "RESTRICT")])
        if "SELECT nombre FROM rol" in sql:
            return Filas(self.roles)
        raise AssertionError(f"Consulta inesperada: {sql}")

    def scalar(self, consulta):
        sql = str(consulta)
        if "WHERE r.nombre='SUPERADMIN' AND u.estado='ACTIVO'" in sql:
            return self.superadmin_activo
        if "WHERE r.nombre='SUPERADMIN'" in sql:
            return 1
        if self.base == "recon_tests" and ("SELECT COUNT(*) FROM `" in sql
                                         or "COUNT(*) FROM evento_acceso" in sql):
            return 0
        raise AssertionError(f"Conteo operativo no autorizado en {self.base}: {sql}")


class EsquemaPersonas:
    def get_pk_constraint(self, tabla):
        return {"constrained_columns": [{"tipo_persona": "id_tipo_persona",
                                         "persona": "id_persona"}[tabla]]}

    def get_unique_constraints(self, tabla):
        nombres = {
            "tipo_persona": {"uq_tipo_persona_nombre": ["nombre"]},
            "persona": {"uq_persona_identificador_institucional": ["identificador_institucional"],
                        "uq_persona_documento": ["tipo_documento", "numero_documento"]},
        }
        return [{"name": nombre, "column_names": columnas}
                for nombre, columnas in nombres[tabla].items()]

    def get_foreign_keys(self, tabla):
        assert tabla == "persona"
        return [{"name": "fk_persona_tipo_persona", "constrained_columns": ["id_tipo_persona"],
                 "referred_table": "tipo_persona", "referred_columns": ["id_tipo_persona"]}]


def test_recon_dev_valida_esquema_y_superadmin_sin_exigir_tablas_vacias(modulo, monkeypatch):
    llamadas = []
    monkeypatch.setattr(modulo, "inspect", lambda _: EsquemaPersonas())
    monkeypatch.setattr(modulo, "verificar_esquema", lambda _: llamadas.append("iam"))
    monkeypatch.setattr(modulo, "verificar_sesion_nueva",
                        lambda _, *, exigir_vacia: llamadas.append(("sesion", exigir_vacia)))
    modulo.validar_base_dev(ConexionFicticia(modulo))
    assert llamadas == ["iam", ("sesion", False)]


def test_recon_dev_rechaza_fk_de_persona_incorrecta(modulo, monkeypatch):
    class EsquemaSinFK(EsquemaPersonas):
        def get_foreign_keys(self, tabla):
            return []

    monkeypatch.setattr(modulo, "inspect", lambda _: EsquemaSinFK())
    with pytest.raises(ValueError, match="FK de Persona"):
        modulo.validar_base_dev(ConexionFicticia(modulo))


@pytest.mark.parametrize("roles,activo", [
    (["SUPERADMIN", "OPERADOR"], 1),
    (["SUPERADMIN", "ADMINISTRADOR", "OPERADOR"], 0),
])
def test_recon_dev_falla_cerrado_si_rol_o_superadmin_no_cuadra(modulo, monkeypatch,
                                                                roles, activo):
    monkeypatch.setattr(modulo, "inspect", lambda _: EsquemaPersonas())
    monkeypatch.setattr(modulo, "verificar_esquema", lambda _: None)
    monkeypatch.setattr(modulo, "verificar_sesion_nueva", lambda _, *, exigir_vacia: None)
    with pytest.raises(ValueError):
        modulo.validar_base_dev(ConexionFicticia(modulo, roles=roles,
                                                  superadmin_activo=activo))


@pytest.mark.parametrize("base,etapa,propias,prohibidas", [
    ("recon_tests", "antes", {"validar_0002", "validar_0003"}, {"validar_base_dev"}),
    ("recon_tests", "despues", {"validar_0002", "validar_0003"}, {"validar_base_dev"}),
    ("recon_dev", "antes", {"validar_base_dev"}, {"validar_0002", "validar_0003"}),
    ("recon_dev", "despues", {"validar_base_dev"}, {"validar_0002", "validar_0003"}),
])
def test_preflight_elige_validadores_de_su_base(modulo, monkeypatch, tmp_path,
                                               base, etapa, propias, prohibidas):
    for nombre in ("DB_HOST", "DB_PORT", "DB_NAME", "DB_TEST_NAME",
                   "DB_TEST_USER", "DB_TEST_PASSWORD", "DB_USER", "DB_PASSWORD"):
        monkeypatch.setenv(nombre, "ficticio")
    monkeypatch.setattr(modulo, "obtener_uri_mysql", lambda *, pruebas:
                        "mysql+pymysql://ficticio:ficticio@127.0.0.1:3306/"
                        + ("recon_tests" if pruebas else "recon_dev"))
    conexion = ConexionFicticia(modulo, base=base, etapa=etapa)

    class MotorFicticio:
        def connect(self):
            return nullcontext(conexion)

        def dispose(self):
            pass

    monkeypatch.setattr(modulo, "create_engine", lambda *_, **__: MotorFicticio())
    llamadas = []
    for nombre in ("destino_tests", "destino_dev", "identidad_tests", "identidad_dev",
                   "validar_privilegios_migracion", "validar_0002", "validar_0003",
                   "validar_base_dev", "validar_0004", "validar_0005",
                   "validar_0006", "huellas_previas"):
        monkeypatch.setattr(modulo, nombre,
                            lambda *_, _nombre=nombre, **__: llamadas.append(_nombre)
                            or {"datos": "ficticios"})
    estado_previo = None
    if etapa == "despues":
        estado_previo = tmp_path / "huellas_previas.json"
        estado_previo.write_text('{"datos": "ficticios"}', encoding="utf-8")
    modulo.verificar(base, etapa, None, estado_previo)
    assert propias <= set(llamadas)
    assert not prohibidas.intersection(llamadas)
    assert {"validar_0004", "validar_0005", "huellas_previas"} <= set(llamadas)
    assert ("validar_privilegios_migracion" in llamadas) == (etapa == "antes")
    assert ("validar_0006" in llamadas) == (etapa == "despues")
    assert f"identidad_{'tests' if base == 'recon_tests' else 'dev'}" in llamadas
