"""Pruebas MySQL 0006 preparadas; no se ejecutan sin autorización expresa."""

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
import re
from threading import Barrier
from uuid import uuid4

import pytest
from sqlalchemy import func, inspect, insert, select, text
from sqlalchemy.engine import Connection
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session

from recon_platform.accesos.servicios.eventos import (
    ActorAcceso, ConflictoIdempotencia, RegistrarEventoManual, ResultadoRegistro,
)
from recon_platform.accesos.infraestructura.modelos_eventos import EventoAccesoModelo
from recon_platform.accesos.infraestructura.repositorios_eventos import RepositorioEventosSQLAlchemy
from recon_platform.accesos.infraestructura.unidad_trabajo_eventos import UnidadTrabajoEventosSQLAlchemy
from recon_platform.accesos.infraestructura.modelos_puntos import PuntoAccesoModelo
from recon_platform.auditoria.infraestructura.modelos import EventoAuditoriaModelo
from recon_platform.auditoria.infraestructura.repositorios import (
    RepositorioEventosSQLAlchemy as RepoAuditoria,
)
from recon_platform.extensions import db
from recon_platform.identidad.infraestructura.modelos import RolModelo, UsuarioPlataformaModelo
from recon_platform.personas.infraestructura.modelos import PersonaModelo, TipoPersonaModelo

from conftest import _validar_conexion

pytestmark = pytest.mark.mysql_integration
INSTANTE = datetime(2026, 10, 22, 14, 0, tzinfo=UTC)


@pytest.fixture
def conexion_0006(conexion_mysql: Connection) -> Connection:
    if conexion_mysql.scalar(text("SELECT version_num FROM alembic_version")) != "0006_evento_acceso":
        pytest.exit("Estas pruebas requieren 0006 en recon_tests verificada.", returncode=2)
    conexion_mysql.rollback()
    return conexion_mysql


@pytest.fixture
def sesion_0006(conexion_0006: Connection):
    transaccion = conexion_0006.begin()
    sesion = Session(bind=conexion_0006, join_transaction_mode="create_savepoint")
    try:
        yield sesion
    finally:
        sesion.close()
        if transaccion.is_active:
            transaccion.rollback()


def _punto(sesion: Session) -> int:
    punto = PuntoAccesoModelo(codigo="P-" + uuid4().hex[:16],
                              nombre="Punto ficticio", estado="ACTIVO")
    sesion.add(punto)
    sesion.flush()
    return punto.id_punto_acceso


def _evento(punto: int, **cambios) -> EventoAccesoModelo:
    datos = {"id_punto_acceso": punto, "tipo_movimiento": "ENTRADA",
             "resultado": "RECHAZADO", "metodo_registro": "FACIAL",
             "fecha_hora_ocurrencia": INSTANTE.replace(tzinfo=None)}
    datos.update(cambios)
    return EventoAccesoModelo(**datos)


def test_esquema_fk_indices_y_checks_0006(conexion_0006: Connection):
    inspector = inspect(conexion_0006)
    columnas = {col["name"]: col for col in inspector.get_columns("evento_acceso")}
    assert set(columnas) == {"id_evento_acceso", "id_persona", "id_punto_acceso",
        "tipo_movimiento", "resultado", "metodo_registro", "id_usuario_registrador",
        "fecha_hora_ocurrencia", "tipo_incidencia_secuencia", "id_dispositivo",
        "clave_idempotencia"}
    assert columnas["id_persona"]["nullable"] is True
    assert columnas["id_dispositivo"]["nullable"] is True
    assert columns_not_null(columnas, "id_punto_acceso", "fecha_hora_ocurrencia")
    assert {fk["name"] for fk in inspector.get_foreign_keys("evento_acceso")} == {
        "fk_evento_acceso_persona", "fk_evento_acceso_punto",
        "fk_evento_acceso_registrador", "fk_evento_acceso_dispositivo"}
    assert {u["name"] for u in inspector.get_unique_constraints("evento_acceso")} == {
        "uq_evento_acceso_clave_idempotencia"}
    indices = {i["name"] for i in inspector.get_indexes("evento_acceso")}
    assert {"ix_evento_acceso_secuencia", "ix_evento_acceso_fecha",
            "ix_evento_acceso_alertas", "ix_evento_acceso_punto_fecha"} <= indices
    checks = {row[0]: row[1] for row in conexion_0006.execute(text(
        "SELECT CONSTRAINT_NAME, ENFORCED FROM information_schema.TABLE_CONSTRAINTS "
        "WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='evento_acceso' AND CONSTRAINT_TYPE='CHECK'"))}
    assert checks == {name: "YES" for name in {
        "ck_evento_acceso_movimiento", "ck_evento_acceso_resultado",
        "ck_evento_acceso_metodo", "ck_evento_acceso_incidencia",
        "ck_evento_acceso_incidencia_autorizada", "ck_evento_acceso_manual"}}


def columns_not_null(columnas: dict, *nombres: str) -> bool:
    return all(columnas[nombre]["nullable"] is False for nombre in nombres)


@pytest.mark.parametrize("columna,valor", [
    ("id_persona", 999999999), ("id_punto_acceso", 999999999),
    ("id_dispositivo", 999999999), ("id_usuario_registrador", 999999999),
])
def test_fk_evento_rechaza_huerfanos_mysql(sesion_0006: Session, columna: str, valor: int):
    punto = _punto(sesion_0006)
    sesion_0006.add(_evento(punto, **{columna: valor}))
    with pytest.raises(IntegrityError):
        sesion_0006.flush()


@pytest.mark.parametrize("cambios,restriccion", [
    ({"tipo_movimiento": "INVALIDO"}, "ck_evento_acceso_movimiento"),
    ({"resultado": "INVALIDO"}, "ck_evento_acceso_resultado"),
    ({"metodo_registro": "INVALIDO"}, "ck_evento_acceso_metodo"),
    ({"tipo_incidencia_secuencia": "INVALIDA", "resultado": "AUTORIZADO"},
     "ck_evento_acceso_incidencia"),
    ({"tipo_incidencia_secuencia": "ENTRADA_REPETIDA"},
     "ck_evento_acceso_incidencia_autorizada"),
    ({"metodo_registro": "MANUAL", "resultado": "AUTORIZADO"},
     "ck_evento_acceso_manual"),
])
def test_checks_evento_mysql(sesion_0006: Session, cambios: dict, restriccion: str):
    punto = _punto(sesion_0006)
    sesion_0006.add(_evento(punto, **cambios))
    with pytest.raises(OperationalError) as error:
        sesion_0006.flush()
    assert error.value.orig is not None
    assert error.value.orig.args[0] == 3819
    assert re.findall(r"\bck_evento_acceso_[a-z_]+\b", error.value.orig.args[1]) == [restriccion]


def test_unique_idempotencia_mysql(sesion_0006: Session):
    punto = _punto(sesion_0006)
    clave = str(uuid4())
    sesion_0006.add(_evento(punto, clave_idempotencia=clave))
    sesion_0006.flush()
    sesion_0006.add(_evento(punto, clave_idempotencia=clave))
    with pytest.raises(IntegrityError):
        sesion_0006.flush()


@pytest.fixture
def datos_confirmados_0006(conexion_0006: Connection):
    """Semilla visible desde dos conexiones; limpieza exclusiva por IDs propios."""
    marca = uuid4().hex[:12]
    fecha = datetime.now(UTC).replace(tzinfo=None)
    rol_id = conexion_0006.scalar(select(RolModelo.id_rol).where(RolModelo.nombre == "ADMINISTRADOR"))
    tipo_id = conexion_0006.scalar(select(TipoPersonaModelo.id_tipo_persona).where(
        TipoPersonaModelo.nombre == "VISITANTE"))
    clave_usuario = conexion_0006.execute(insert(UsuarioPlataformaModelo).values(
        login="test-0006-" + marca, hash_contrasena="HASH_NO_AUTENTICABLE_DE_PRUEBA",
        id_rol=rol_id, estado="ACTIVO", fecha_creacion=fecha, fecha_actualizacion=fecha
    )).inserted_primary_key
    assert clave_usuario is not None
    usuario = clave_usuario[0]
    clave_persona = conexion_0006.execute(insert(PersonaModelo).values(
        id_tipo_persona=tipo_id, primer_nombre="Prueba", primer_apellido="Ficticia",
        tipo_documento="CC", numero_documento="FICT-" + marca,
        estado="ACTIVO", fecha_creacion=fecha, fecha_actualizacion=fecha
    )).inserted_primary_key
    assert clave_persona is not None
    persona = clave_persona[0]
    clave_otra_persona = conexion_0006.execute(insert(PersonaModelo).values(
        id_tipo_persona=tipo_id, primer_nombre="Otra", primer_apellido="Ficticia",
        tipo_documento="CC", numero_documento="FICT-B-" + marca,
        estado="ACTIVO", fecha_creacion=fecha, fecha_actualizacion=fecha
    )).inserted_primary_key
    assert clave_otra_persona is not None
    otra_persona = clave_otra_persona[0]
    clave_punto = conexion_0006.execute(insert(PuntoAccesoModelo).values(
        codigo="T-" + marca, nombre="Punto ficticio", estado="ACTIVO",
        fecha_creacion=fecha, fecha_actualizacion=fecha
    )).inserted_primary_key
    assert clave_punto is not None
    punto = clave_punto[0]
    conexion_0006.commit()
    try:
        yield usuario, persona, otra_persona, punto
    finally:
        # No elimina ni modifica objetos ajenos; si falla, el script posterior denuncia residuos.
        conexion_0006.execute(EventoAuditoriaModelo.__table__.delete().where(
            EventoAuditoriaModelo.id_usuario_actor == usuario))
        conexion_0006.execute(EventoAccesoModelo.__table__.delete().where(
            EventoAccesoModelo.id_persona.in_((persona, otra_persona))))
        conexion_0006.execute(PersonaModelo.__table__.delete().where(
            PersonaModelo.id_persona.in_((persona, otra_persona))))
        conexion_0006.execute(PuntoAccesoModelo.__table__.delete().where(
            PuntoAccesoModelo.id_punto_acceso == punto))
        conexion_0006.execute(UsuarioPlataformaModelo.__table__.delete().where(
            UsuarioPlataformaModelo.id_usuario == usuario))
        conexion_0006.commit()


def _resultado_exitoso(resultado: ResultadoRegistro | ConflictoIdempotencia) -> ResultadoRegistro:
    assert isinstance(resultado, ResultadoRegistro)
    return resultado


@pytest.mark.parametrize("modo", ["distintas", "reintento", "misma_clave_otra_persona"])
def test_concurrencia_real_dos_conexiones_mysql(aplicacion_mysql, datos_confirmados_0006,
                                                 modo: str):
    usuario, persona, otra_persona, punto = datos_confirmados_0006
    barrera = Barrier(2)
    clave = str(uuid4())

    def registrar(indice: int):
        with aplicacion_mysql.app_context():
            with db.engine.connect() as conexion:
                _validar_conexion(conexion)
                conexion.rollback()
                with Session(bind=conexion) as sesion:
                    # Fuerza una snapshot previa: el caso de uso debe cerrarla.
                    assert sesion.scalar(select(PersonaModelo.estado).where(
                        PersonaModelo.id_persona == persona)) == "ACTIVO"
                    barrera.wait(timeout=20)
                    caso = RegistrarEventoManual(RepositorioEventosSQLAlchemy(sesion),
                        RepoAuditoria(sesion), UnidadTrabajoEventosSQLAlchemy(sesion),
                        lambda: INSTANTE)
                    try:
                        return caso.ejecutar(actor=ActorAcceso(usuario, "ADMINISTRADOR"),
                            id_persona=otra_persona if modo == "misma_clave_otra_persona" and indice else persona,
                            id_punto_acceso=punto, tipo_movimiento="ENTRADA",
                            clave=clave if modo != "distintas" else str(uuid4()))
                    except ConflictoIdempotencia as error:
                        return error

    with ThreadPoolExecutor(max_workers=2) as ejecutor:
        futuros = [ejecutor.submit(registrar, i) for i in range(2)]
        resultados = [f.result(timeout=40) for f in futuros]
    with aplicacion_mysql.app_context():
        with db.engine.connect() as conexion:
            _validar_conexion(conexion)
            eventos = conexion.execute(select(EventoAccesoModelo).where(
                EventoAccesoModelo.id_persona.in_((persona, otra_persona)))).scalars().all()
            auditorias = conexion.scalar(select(func.count()).select_from(EventoAuditoriaModelo).where(
                EventoAuditoriaModelo.id_usuario_actor == usuario,
                EventoAuditoriaModelo.accion == "REGISTRAR_EVENTO_ACCESO_MANUAL"))
            if modo == "reintento":
                assert len(eventos) == auditorias == 1
                assert sorted(_resultado_exitoso(r).repetido for r in resultados) == [False, True]
            elif modo == "distintas":
                assert len(eventos) == auditorias == 2
                assert sorted(_resultado_exitoso(r).evento.tipo_incidencia_secuencia or "" for r in resultados) == [
                    "", "ENTRADA_REPETIDA"]
            else:
                assert len(eventos) == auditorias == 1
                assert sum(isinstance(r, ConflictoIdempotencia) for r in resultados) == 1


def test_rollback_real_si_falla_auditoria_mysql(aplicacion_mysql, datos_confirmados_0006,
                                                monkeypatch):
    usuario, persona, _, punto = datos_confirmados_0006
    clave = str(uuid4())
    with aplicacion_mysql.app_context():
        with db.engine.connect() as conexion:
            _validar_conexion(conexion)
            conexion.rollback()
            with Session(bind=conexion) as sesion:
                original = RepoAuditoria.agregar
                def fallar(*_args):
                    raise RuntimeError("fallo de auditoría ficticio")
                monkeypatch.setattr(RepoAuditoria, "agregar", fallar)
                caso = RegistrarEventoManual(RepositorioEventosSQLAlchemy(sesion),
                    RepoAuditoria(sesion), UnidadTrabajoEventosSQLAlchemy(sesion), lambda: INSTANTE)
                with pytest.raises(RuntimeError):
                    caso.ejecutar(actor=ActorAcceso(usuario, "ADMINISTRADOR"),
                        id_persona=persona, id_punto_acceso=punto,
                        tipo_movimiento="ENTRADA", clave=clave)
                assert sesion.scalar(select(func.count()).select_from(EventoAccesoModelo).where(
                    EventoAccesoModelo.id_persona == persona)) == 0
                monkeypatch.setattr(RepoAuditoria, "agregar", original)
                assert caso.ejecutar(actor=ActorAcceso(usuario, "ADMINISTRADOR"),
                    id_persona=persona, id_punto_acceso=punto,
                    tipo_movimiento="ENTRADA", clave=clave).repetido is False
