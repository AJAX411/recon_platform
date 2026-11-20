"""Pruebas MySQL 0005 preparadas; requieren autorización y recon_tests aislada."""

import json

import pytest
from sqlalchemy import inspect, select, text
from sqlalchemy.engine import Connection
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session

from recon_platform.accesos.servicio_puntos import AdministrarPuntos
from recon_platform.accesos.punto_acceso import PuntoAcceso
from recon_platform.accesos.modelos_puntos import PuntoAccesoModelo
from recon_platform.accesos.repositorio_puntos import RepositorioPuntosSQLAlchemy
from recon_platform.auditoria.modelos import EventoAuditoriaModelo
from recon_platform.auditoria.repositorio import RepositorioEventosSQLAlchemy
from recon_platform.auditoria.unidad_trabajo import UnidadTrabajoSQLAlchemy
from recon_platform.identidad.servicio_cuentas import BootstrapSuperadmin
from recon_platform.identidad.repositorio_cuentas import RepositorioIAMSQLAlchemy
from recon_platform.identidad.unidad_trabajo import UnidadTrabajoIAMSQLAlchemy
from recon_platform.integracion_edge.servicio import AdministrarDispositivos
from recon_platform.integracion_edge.dispositivo_edge import DispositivoEdge
from recon_platform.integracion_edge.repositorio import ConsultaPuntosSQLAlchemy, RepositorioDispositivosSQLAlchemy
from recon_platform.integracion_edge.modelos import DispositivoEdgeModelo

pytestmark = pytest.mark.mysql_integration


@pytest.fixture
def conexion_0005(conexion_mysql: Connection) -> Connection:
    if conexion_mysql.scalar(text("SELECT version_num FROM alembic_version")) not in {
        "0005_puntos_edge_auditoria", "0006_evento_acceso"}:
        pytest.exit("Estas pruebas requieren 0005 en recon_tests verificada.", returncode=2)
    conexion_mysql.rollback()
    return conexion_mysql


@pytest.fixture
def sesion_0005(conexion_0005: Connection):
    transaccion = conexion_0005.begin()
    sesion = Session(bind=conexion_0005, join_transaction_mode="create_savepoint")
    try:
        yield sesion
    finally:
        sesion.close()
        if transaccion.is_active:
            transaccion.rollback()


def test_esquema_0005_mysql(conexion_0005: Connection):
    inspector = inspect(conexion_0005)
    esperadas = {
        "punto_acceso": {"id_punto_acceso", "codigo", "nombre", "descripcion", "estado",
                         "fecha_creacion", "fecha_actualizacion"},
        "dispositivo_edge": {"id_dispositivo", "id_punto_acceso", "codigo", "nombre",
                             "modo_operacion", "estado", "ultima_comunicacion",
                             "fecha_creacion", "fecha_actualizacion"},
        "evento_auditoria": {"id_auditoria", "id_usuario_actor", "tipo_actor", "accion",
                             "recurso_tipo", "id_recurso_afectado", "resultado", "detalle", "fecha_hora"},
    }
    for tabla, columnas in esperadas.items():
        assert {c["name"] for c in inspector.get_columns(tabla)} == columnas
        assert inspector.get_pk_constraint(tabla)["constrained_columns"] == [{
            "punto_acceso": "id_punto_acceso", "dispositivo_edge": "id_dispositivo",
            "evento_auditoria": "id_auditoria"}[tabla]]
        assert conexion_0005.scalar(text("SELECT COUNT(*) FROM `" + tabla + "`")) == 0
    fks = {f["name"]: f for f in inspector.get_foreign_keys("dispositivo_edge")}
    assert fks["fk_dispositivo_edge_punto"]["referred_table"] == "punto_acceso"
    assert fks["fk_dispositivo_edge_punto"]["constrained_columns"] == ["id_punto_acceso"]
    fks = {f["name"]: f for f in inspector.get_foreign_keys("evento_auditoria")}
    assert fks["fk_evento_auditoria_actor"]["referred_table"] == "usuario_plataforma"
    cols = {c["name"]: c for c in inspector.get_columns("evento_auditoria")}
    assert cols["id_usuario_actor"]["nullable"] is True
    assert cols["detalle"]["nullable"] is True
    assert {u["name"] for u in inspector.get_unique_constraints("punto_acceso")} == {"uq_punto_acceso_codigo"}
    assert {u["name"] for u in inspector.get_unique_constraints("dispositivo_edge")} == {"uq_dispositivo_edge_codigo"}
    checks = {fila[0]: fila[1] for fila in conexion_0005.execute(text(
        "SELECT tc.CONSTRAINT_NAME, tc.ENFORCED FROM information_schema.TABLE_CONSTRAINTS tc "
        "WHERE tc.TABLE_SCHEMA=DATABASE() AND tc.TABLE_NAME IN "
        "('punto_acceso','dispositivo_edge','evento_auditoria') AND tc.CONSTRAINT_TYPE='CHECK'"))}
    assert checks == {name: "YES" for name in {
        "ck_punto_acceso_estado", "ck_dispositivo_edge_estado", "ck_dispositivo_edge_modo",
        "ck_evento_auditoria_tipo_actor", "ck_evento_auditoria_resultado",
        "ck_evento_auditoria_actor"}}


def test_crud_auditoria_y_relacion_mysql(sesion_0005: Session):
    actor = BootstrapSuperadmin(RepositorioIAMSQLAlchemy(sesion_0005),
        UnidadTrabajoIAMSQLAlchemy(sesion_0005)).ejecutar(
            login="superadmin.prueba.0005", contrasena="Clave-Ficticia-Prueba-0005!").usuario
    assert actor.id_usuario is not None
    auditoria = RepositorioEventosSQLAlchemy(sesion_0005)
    unidad = UnidadTrabajoSQLAlchemy(sesion_0005)
    puntos = AdministrarPuntos(RepositorioPuntosSQLAlchemy(sesion_0005), auditoria, unidad)
    dispositivos = AdministrarDispositivos(RepositorioDispositivosSQLAlchemy(sesion_0005),
        ConsultaPuntosSQLAlchemy(sesion_0005), auditoria, unidad)
    punto = puntos.crear(actor_id=actor.id_usuario, rol="SUPERADMIN",
                         punto=PuntoAcceso(codigo="MYSQL-P-0005", nombre="Punto ficticio"))
    assert punto.id_punto_acceso is not None
    dispositivo = dispositivos.crear(actor_id=actor.id_usuario, rol="SUPERADMIN",
        dispositivo=DispositivoEdge(id_punto_acceso=punto.id_punto_acceso,
            codigo="MYSQL-D-0005", nombre="Nodo ficticio", modo_operacion="AUTOMATICO"))
    assert dispositivo.id_dispositivo is not None
    actualizado = dispositivos.cambiar_modo(actor_id=actor.id_usuario, rol="SUPERADMIN",
                                             id_dispositivo=dispositivo.id_dispositivo, modo="ENTRADA")
    assert actualizado.modo_operacion == "ENTRADA"
    assert actualizado.estado == "INACTIVO"
    assert actualizado.ultima_comunicacion is None
    assert sesion_0005.scalar(select(DispositivoEdgeModelo.id_punto_acceso)) == punto.id_punto_acceso
    eventos = sesion_0005.scalars(select(EventoAuditoriaModelo).order_by(EventoAuditoriaModelo.id_auditoria)).all()
    assert [e.accion for e in eventos] == ["CREAR_PUNTO_ACCESO", "CREAR_DISPOSITIVO_EDGE",
                                           "CAMBIAR_MODO_DISPOSITIVO"]
    assert all(e.id_usuario_actor == actor.id_usuario and e.resultado == "EXITOSO" for e in eventos)
    detalle = eventos[-1].detalle
    assert detalle is not None
    assert json.loads(detalle) == {"anterior": "AUTOMATICO", "nuevo": "ENTRADA"}


def test_unicidad_codigo_punto_mysql(sesion_0005: Session):
    sesion_0005.add(PuntoAccesoModelo(codigo="P-DUP", nombre="Primero", estado="ACTIVO"))
    sesion_0005.flush()
    sesion_0005.add(PuntoAccesoModelo(codigo="P-DUP", nombre="Segundo", estado="ACTIVO"))
    with pytest.raises(IntegrityError):
        sesion_0005.flush()


def test_fk_dispositivo_mysql(sesion_0005: Session):
    sesion_0005.add(DispositivoEdgeModelo(id_punto_acceso=999999, codigo="D-SIN-PUNTO",
        nombre="Ficticio", modo_operacion="AUTOMATICO", estado="INACTIVO"))
    with pytest.raises(IntegrityError):
        sesion_0005.flush()


def test_unicidad_codigo_dispositivo_mysql(sesion_0005: Session):
    punto = PuntoAccesoModelo(codigo="P-D-DUP", nombre="Ficticio", estado="ACTIVO")
    sesion_0005.add(punto)
    sesion_0005.flush()
    sesion_0005.add(DispositivoEdgeModelo(id_punto_acceso=punto.id_punto_acceso,
        codigo="D-DUP", nombre="Primero", modo_operacion="ENTRADA", estado="INACTIVO"))
    sesion_0005.flush()
    sesion_0005.add(DispositivoEdgeModelo(id_punto_acceso=punto.id_punto_acceso,
        codigo="D-DUP", nombre="Segundo", modo_operacion="SALIDA", estado="INACTIVO"))
    with pytest.raises(IntegrityError):
        sesion_0005.flush()


def test_modo_invalido_rechazado_por_mysql(sesion_0005: Session):
    punto = PuntoAccesoModelo(codigo="P-MODO", nombre="Ficticio", estado="ACTIVO")
    sesion_0005.add(punto)
    sesion_0005.flush()
    sesion_0005.add(DispositivoEdgeModelo(id_punto_acceso=punto.id_punto_acceso,
        codigo="D-MODO", nombre="Ficticio", modo_operacion="ILEGAL", estado="INACTIVO"))
    with pytest.raises(OperationalError) as error:
        sesion_0005.flush()
    assert error.value.orig is not None
    assert error.value.orig.args[0] == 3819
    assert "ck_dispositivo_edge_modo" in error.value.orig.args[1]


def test_estado_invalido_rechazado_por_mysql(sesion_0005: Session):
    sesion_0005.add(PuntoAccesoModelo(codigo="P-ESTADO", nombre="Ficticio", estado="ILEGAL"))
    with pytest.raises(OperationalError) as error:
        sesion_0005.flush()
    assert error.value.orig is not None
    assert error.value.orig.args[0] == 3819
    assert "ck_punto_acceso_estado" in error.value.orig.args[1]


def test_actor_usuario_requiere_fk_y_id_mysql(sesion_0005: Session):
    sesion_0005.add(EventoAuditoriaModelo(tipo_actor="USUARIO", id_usuario_actor=None,
        accion="PRUEBA_FICTICIA", resultado="FALLIDO"))
    with pytest.raises(OperationalError) as error:
        sesion_0005.flush()
    assert error.value.orig is not None
    assert error.value.orig.args[0] == 3819
    assert "ck_evento_auditoria_actor" in error.value.orig.args[1]


def test_fallo_auditoria_revierte_punto_mysql(sesion_0005: Session, monkeypatch):
    actor = BootstrapSuperadmin(RepositorioIAMSQLAlchemy(sesion_0005),
        UnidadTrabajoIAMSQLAlchemy(sesion_0005)).ejecutar(
            login="superadmin.rollback.0005", contrasena="Clave-Ficticia-Prueba-0005!").usuario
    assert actor.id_usuario is not None
    def fallar(*_args, **_kwargs):
        raise RuntimeError("Fallo ficticio de auditoría")
    auditoria = RepositorioEventosSQLAlchemy(sesion_0005)
    monkeypatch.setattr(auditoria, "agregar", fallar)
    caso = AdministrarPuntos(RepositorioPuntosSQLAlchemy(sesion_0005),
                             auditoria, UnidadTrabajoSQLAlchemy(sesion_0005))
    with pytest.raises(RuntimeError, match="Fallo ficticio"):
        caso.crear(actor_id=actor.id_usuario, rol="SUPERADMIN",
                   punto=PuntoAcceso(codigo="P-ROLLBACK", nombre="Ficticio"))
    assert sesion_0005.scalar(select(PuntoAccesoModelo.id_punto_acceso).where(
        PuntoAccesoModelo.codigo == "P-ROLLBACK")) is None
    assert sesion_0005.scalar(select(EventoAuditoriaModelo.id_auditoria)) is None
