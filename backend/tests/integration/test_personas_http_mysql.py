"""Integración pendiente de autorización: exige 0004 y recon_tests verificado."""

from uuid import uuid4

import pytest
from sqlalchemy import inspect, select, text
from sqlalchemy.engine import Connection
from sqlalchemy.orm import Session

from recon_platform.identidad.aplicacion.casos_de_uso import BootstrapSuperadmin
from recon_platform.identidad.infraestructura.repositorios import RepositorioIAMSQLAlchemy
from recon_platform.identidad.infraestructura.unidad_trabajo import UnidadTrabajoIAMSQLAlchemy
from recon_platform.personas.aplicacion.casos_de_uso import ActorPersonas, AdministrarPersonas, PersonaDuplicada
from recon_platform.personas.dominio.persona import Persona
from recon_platform.personas.dominio.tipo_persona import TipoPersona
from recon_platform.personas.infraestructura.modelos import AuditoriaPersonasModelo, PersonaModelo
from recon_platform.personas.infraestructura.repositorios import RepositorioPersonasSQLAlchemy, RepositorioTiposPersonaSQLAlchemy
from recon_platform.personas.infraestructura.unidad_trabajo import UnidadTrabajoSQLAlchemy

pytestmark = pytest.mark.mysql_integration


@pytest.fixture
def conexion_0004(conexion_mysql: Connection):
    if conexion_mysql.scalar(text("SELECT version_num FROM alembic_version")) not in {
        "0004_auditoria_personas", "0005_puntos_edge_auditoria", "0006_evento_acceso"}:
        pytest.exit("Las pruebas de Personas HTTP requieren 0004 o 0005.", returncode=2)
    conexion_mysql.rollback()
    return conexion_mysql


@pytest.fixture
def sesion_0004(conexion_0004: Connection):
    transaccion = conexion_0004.begin()
    sesion = Session(bind=conexion_0004, join_transaction_mode="create_savepoint")
    try:
        yield sesion
    finally:
        sesion.close()
        if transaccion.is_active:
            transaccion.rollback()


def _persona(numero: str, *, identificador: str | None = None) -> Persona:
    return Persona(primer_nombre="Persona", primer_apellido="Ficticia",
                   tipo_persona=TipoPersona(nombre="VISITANTE"),
                   tipo_documento="PRUEBA", numero_documento=numero,
                   identificador_institucional=identificador)


def _caso(sesion: Session, repo=None) -> AdministrarPersonas:
    return AdministrarPersonas(repo or RepositorioPersonasSQLAlchemy(sesion),
                              RepositorioTiposPersonaSQLAlchemy(sesion),
                              UnidadTrabajoSQLAlchemy(sesion))


def test_esquema_auditoria_personas(conexion_0004: Connection) -> None:
    inspector = inspect(conexion_0004)
    columnas = {c["name"]: c for c in inspector.get_columns("auditoria_personas")}
    assert set(columnas) == {"id_auditoria", "actor_id", "id_persona", "accion", "fecha"}
    assert all(not columna["nullable"] for columna in columnas.values())
    assert inspector.get_pk_constraint("auditoria_personas")["constrained_columns"] == ["id_auditoria"]
    assert {fk["name"]: fk["referred_table"] for fk in inspector.get_foreign_keys("auditoria_personas")} == {
        "fk_auditoria_personas_actor": "usuario_plataforma",
        "fk_auditoria_personas_persona": "persona",
    }
    indices = {indice["name"]: indice["column_names"] for indice in
               inspector.get_indexes("auditoria_personas")}
    assert indices["ix_auditoria_personas_id_persona"] == ["id_persona"]
    assert any(columnas and columnas[0] == "actor_id" for columnas in indices.values())
    tipos = {fila["COLUMN_NAME"]: fila for fila in conexion_0004.execute(text(
        "SELECT COLUMN_NAME, DATA_TYPE, COLUMN_TYPE, CHARACTER_MAXIMUM_LENGTH "
        "FROM information_schema.COLUMNS WHERE TABLE_SCHEMA = DATABASE() "
        "AND TABLE_NAME = 'auditoria_personas'"
    )).mappings()}
    assert all(tipos[n]["DATA_TYPE"] == "int" and "unsigned" in tipos[n]["COLUMN_TYPE"]
               for n in ("id_auditoria", "actor_id", "id_persona"))
    assert tipos["accion"]["DATA_TYPE"] == "varchar"
    assert tipos["accion"]["CHARACTER_MAXIMUM_LENGTH"] == 30
    assert tipos["fecha"]["DATA_TYPE"] == "datetime"
    checks = conexion_0004.execute(text(
        "SELECT CONSTRAINT_NAME, ENFORCED FROM information_schema.TABLE_CONSTRAINTS "
        "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'auditoria_personas' "
        "AND CONSTRAINT_TYPE = 'CHECK'"
    )).all()
    assert checks == [("ck_auditoria_personas_accion", "YES")]
    assert conexion_0004.scalar(text("SELECT COUNT(*) FROM auditoria_personas")) == 0


def test_crud_auditoria_y_unicidades_mysql(sesion_0004: Session) -> None:
    actor_iam = BootstrapSuperadmin(
        RepositorioIAMSQLAlchemy(sesion_0004), UnidadTrabajoIAMSQLAlchemy(sesion_0004)
    ).ejecutar(login=f"personas.{uuid4().hex[:20]}",
              contrasena="Clave-Ficticia-Prueba-2026!").usuario
    actor = ActorPersonas(actor_iam.id_usuario, "SUPERADMIN")
    caso = _caso(sesion_0004)
    primera = caso.registrar(actor=actor, persona=_persona(uuid4().hex[:20], identificador="TEST-"+uuid4().hex[:20]))
    segunda = caso.registrar(actor=actor, persona=_persona(uuid4().hex[:20], identificador="TEST-"+uuid4().hex[:20]))
    with pytest.raises(PersonaDuplicada):
        caso.actualizar(actor=actor, id_persona=segunda.id_persona,
                        datos={"identificador_institucional": primera.identificador_institucional})
    actualizada = caso.actualizar(actor=actor, id_persona=segunda.id_persona,
                                  datos={"primer_nombre": "Nueva"})
    assert actualizada.id_persona == segunda.id_persona
    assert caso.cambiar_estado(actor=actor, id_persona=segunda.id_persona,
                              estado="INACTIVO").estado == "INACTIVO"
    assert caso.cambiar_estado(actor=actor, id_persona=segunda.id_persona,
                              estado="ACTIVO").estado == "ACTIVO"
    eventos = sesion_0004.scalars(select(AuditoriaPersonasModelo).where(
        AuditoriaPersonasModelo.id_persona == segunda.id_persona).order_by(
            AuditoriaPersonasModelo.id_auditoria)).all()
    assert [e.accion for e in eventos] == ["REGISTRAR_PERSONA", "ACTUALIZAR_PERSONA",
                                          "DESACTIVAR_PERSONA", "ACTIVAR_PERSONA"]
    assert all(e.actor_id == actor.id_usuario and e.fecha is not None for e in eventos)
    assert sesion_0004.scalar(select(PersonaModelo.id_persona).where(
        PersonaModelo.id_persona == segunda.id_persona)) == segunda.id_persona


def test_fallo_auditoria_revierte_registro_mysql(sesion_0004: Session) -> None:
    actor_iam = BootstrapSuperadmin(
        RepositorioIAMSQLAlchemy(sesion_0004), UnidadTrabajoIAMSQLAlchemy(sesion_0004)
    ).ejecutar(login=f"personas.{uuid4().hex[:20]}",
              contrasena="Clave-Ficticia-Prueba-2026!").usuario
    actor = ActorPersonas(actor_iam.id_usuario, "SUPERADMIN")
    class RepositorioConFallo(RepositorioPersonasSQLAlchemy):
        def auditar(self, **_kwargs):
            raise RuntimeError("Fallo ficticio de auditoría")
    numero = uuid4().hex[:20]
    with pytest.raises(RuntimeError):
        _caso(sesion_0004, RepositorioConFallo(sesion_0004)).registrar(
            actor=actor, persona=_persona(numero))
    assert sesion_0004.scalar(select(PersonaModelo.id_persona).where(
        PersonaModelo.numero_documento == numero)) is None
