"""Barreras de 0004 verificadas con dobles; nunca conecta a MySQL."""

import importlib

import pytest
from sqlalchemy.engine import make_url


@pytest.fixture
def verificador(monkeypatch):
    from pathlib import Path
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[2] / "scripts"))
    return importlib.import_module("verificar_recon_tests_0004")


def test_destino_distinto_falla_antes_de_abrir_conexion(verificador, monkeypatch):
    monkeypatch.setenv("DB_NAME", "recon_dev")
    correcta = make_url("mysql+pymysql://recon_test_app:prueba@127.0.0.1:3306/recon_tests")
    verificador.validar_destino(correcta)
    for direccion in (
        "mysql+pymysql://recon_test_app:prueba@127.0.0.1:3306/recon_dev",
        "mysql+pymysql://otro:prueba@127.0.0.1:3306/recon_tests",
        "mysql+pymysql://recon_test_app:prueba@192.0.2.1:3306/recon_tests",
    ):
        with pytest.raises(verificador.VerificacionFallida):
            verificador.validar_destino(make_url(direccion))
    monkeypatch.setenv("DB_NAME", "otra_base")
    with pytest.raises(verificador.VerificacionFallida):
        verificador.validar_destino(correcta)
    with pytest.raises(verificador.VerificacionFallida):
        verificador.verificar("etapa_invalida")


class ResultadoFalso:
    def __init__(self, filas):
        self.filas = filas

    def mappings(self):
        return iter(self.filas)

    def all(self):
        return self.filas

    def __iter__(self):
        return iter(self.filas)


class ConexionFalsa:
    def __init__(self):
        self.longitud_accion = 30
        self.borrados = [("fk_auditoria_personas_actor", "RESTRICT"),
                         ("fk_auditoria_personas_persona", "RESTRICT")]
        self.check = [("ck_auditoria_personas_accion", "accion in ('REGISTRAR_PERSONA','ACTUALIZAR_PERSONA','ACTIVAR_PERSONA','DESACTIVAR_PERSONA')", "YES")]

    def execute(self, consulta):
        sql = str(consulta)
        if "information_schema.COLUMNS" in sql:
            return ResultadoFalso([
                {"COLUMN_NAME": nombre, "DATA_TYPE": "int", "COLUMN_TYPE": "int unsigned",
                 "CHARACTER_MAXIMUM_LENGTH": None}
                for nombre in ("id_auditoria", "actor_id", "id_persona")
            ] + [
                {"COLUMN_NAME": "accion", "DATA_TYPE": "varchar", "COLUMN_TYPE": "varchar(30)",
                 "CHARACTER_MAXIMUM_LENGTH": self.longitud_accion},
                {"COLUMN_NAME": "fecha", "DATA_TYPE": "datetime", "COLUMN_TYPE": "datetime",
                 "CHARACTER_MAXIMUM_LENGTH": None},
            ])
        if "REFERENTIAL_CONSTRAINTS" in sql:
            return ResultadoFalso(self.borrados)
        if "CHECK_CONSTRAINTS" in sql:
            return ResultadoFalso(self.check)
        raise AssertionError("Consulta inesperada")


class InspectorFalso:
    def __init__(self):
        self.indice = [
            {"name": "ix_auditoria_personas_id_persona", "column_names": ["id_persona"]},
            {"name": "fk_auditoria_personas_actor", "column_names": ["actor_id"]},
        ]

    def get_columns(self, _tabla):
        return [{"name": nombre, "nullable": False} for nombre in
                ("id_auditoria", "actor_id", "id_persona", "accion", "fecha")]

    def get_pk_constraint(self, _tabla):
        return {"constrained_columns": ["id_auditoria"]}

    def get_foreign_keys(self, _tabla):
        return [
            {"name": "fk_auditoria_personas_actor", "constrained_columns": ["actor_id"],
             "referred_table": "usuario_plataforma", "referred_columns": ["id_usuario"]},
            {"name": "fk_auditoria_personas_persona", "constrained_columns": ["id_persona"],
             "referred_table": "persona", "referred_columns": ["id_persona"]},
        ]

    def get_indexes(self, _tabla):
        return self.indice

    def get_unique_constraints(self, _tabla):
        return []


CLAUSULA_NORMAL = (
    "accion in ('REGISTRAR_PERSONA','ACTUALIZAR_PERSONA',"
    "'ACTIVAR_PERSONA','DESACTIVAR_PERSONA')"
)
CLAUSULA_MYSQL = (
    r"(`accion` in (_utf8mb4\'REGISTRAR_PERSONA\',"
    r"_utf8mb4\'ACTUALIZAR_PERSONA\',"
    r"_utf8mb4\'ACTIVAR_PERSONA\',"
    r"_utf8mb4\'DESACTIVAR_PERSONA\'))"
)


@pytest.mark.parametrize("clausula", [CLAUSULA_NORMAL, CLAUSULA_MYSQL])
def test_check_admite_comillas_normales_y_formato_mysql(verificador, monkeypatch, clausula):
    monkeypatch.setattr(verificador, "inspect", lambda _conexion: InspectorFalso())
    conexion = ConexionFalsa()
    conexion.check = [("ck_auditoria_personas_accion", clausula, "YES")]
    verificador.validar_0004(conexion)


@pytest.mark.parametrize("check", [
    [("ck_accion_incorrecto", CLAUSULA_MYSQL, "YES")],
    [("ck_auditoria_personas_accion", CLAUSULA_MYSQL, "NO")],
    [("ck_auditoria_personas_accion", CLAUSULA_MYSQL.replace(
        r"_utf8mb4\'DESACTIVAR_PERSONA\'", ""), "YES")],
    [("ck_auditoria_personas_accion", CLAUSULA_MYSQL.replace(
        "DESACTIVAR_PERSONA", "ELIMINAR_PERSONA"), "YES")],
    [("ck_auditoria_personas_accion", CLAUSULA_NORMAL.replace(
        "'DESACTIVAR_PERSONA'", "'ACTIVAR_PERSONA'"), "YES")],
    [("ck_auditoria_personas_accion", CLAUSULA_NORMAL.replace(
        "'DESACTIVAR_PERSONA'", "'DESACTIVAR_PERSONA','ELIMINAR_PERSONA'"), "YES")],
    [("ck_auditoria_personas_accion", CLAUSULA_NORMAL, "YES"),
     ("otro_check", CLAUSULA_NORMAL, "YES")],
])
def test_check_rechaza_restricciones_incorrectas(verificador, monkeypatch, check):
    monkeypatch.setattr(verificador, "inspect", lambda _conexion: InspectorFalso())
    conexion = ConexionFalsa()
    conexion.check = check
    with pytest.raises(verificador.VerificacionFallida, match="CHECK de acciones"):
        verificador.validar_0004(conexion)


def test_verificacion_esquema_detecta_tipos_fk_check_e_indice(verificador, monkeypatch):
    inspector = InspectorFalso()
    conexion = ConexionFalsa()
    monkeypatch.setattr(verificador, "inspect", lambda _conexion: inspector)
    verificador.validar_0004(conexion)
    conexion.longitud_accion = 29
    with pytest.raises(verificador.VerificacionFallida):
        verificador.validar_0004(conexion)
    conexion.longitud_accion = 30
    conexion.borrados[0] = ("fk_auditoria_personas_actor", "CASCADE")
    with pytest.raises(verificador.VerificacionFallida):
        verificador.validar_0004(conexion)
    conexion.borrados[0] = ("fk_auditoria_personas_actor", "RESTRICT")
    conexion.check = [("ck_auditoria_personas_accion", "accion in ('REGISTRAR_PERSONA')", "YES")]
    with pytest.raises(verificador.VerificacionFallida):
        verificador.validar_0004(conexion)
    conexion.check = [("ck_auditoria_personas_accion", "accion in ('REGISTRAR_PERSONA','ACTUALIZAR_PERSONA','ACTIVAR_PERSONA','DESACTIVAR_PERSONA')", "YES")]
    inspector.indice = []
    with pytest.raises(verificador.VerificacionFallida):
        verificador.validar_0004(conexion)
