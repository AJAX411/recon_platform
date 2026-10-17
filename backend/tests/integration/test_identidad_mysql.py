"""Validación IAM en recon_tests desde la revisión 0002.

La barrera exige activación, destino autorizado y revisión IAM conocida.
Cada dato ficticio creado por estas pruebas permanece en una transacción reversible.
"""

from uuid import uuid4

import pytest
from sqlalchemy import func, inspect, select, text
from sqlalchemy.engine import Connection
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from recon_platform.identidad.aplicacion.casos_de_uso import (
    BootstrapSuperadmin,
    CambiarRolUsuario,
    CrearUsuarioPlataforma,
)
from recon_platform.identidad.dominio.credenciales import (
    generar_hash_contrasena,
    verificar_contrasena,
)
from recon_platform.identidad.dominio.usuario_plataforma import UsuarioPlataforma
from recon_platform.identidad.infraestructura.modelos import (
    AuditoriaIAMModelo,
    RolModelo,
    UsuarioPlataformaModelo,
)
from recon_platform.identidad.infraestructura.repositorios import RepositorioIAMSQLAlchemy
from recon_platform.identidad.infraestructura.unidad_trabajo import (
    UnidadTrabajoIAMSQLAlchemy,
)
from recon_platform.personas.infraestructura.modelos import PersonaModelo

pytestmark = pytest.mark.mysql_integration

ROLES = {"SUPERADMIN", "ADMINISTRADOR", "OPERADOR"}
CLAVE_FICTICIA = "Clave-Ficticia-IAM-2026!"


def _login() -> str:
    return f"iam.prueba.{uuid4().hex[:20]}"


def _administrador_ficticio(sesion: Session) -> UsuarioPlataforma:
    resultado = BootstrapSuperadmin(
        RepositorioIAMSQLAlchemy(sesion), UnidadTrabajoIAMSQLAlchemy(sesion)
    ).ejecutar(login=_login(), contrasena=CLAVE_FICTICIA)
    assert resultado.creado
    return resultado.usuario


def _crear_cuenta(
    sesion: Session, *, actor_id: int, login: str, rol: str = "OPERADOR"
) -> UsuarioPlataforma:
    return CrearUsuarioPlataforma(
        RepositorioIAMSQLAlchemy(sesion), UnidadTrabajoIAMSQLAlchemy(sesion)
    ).ejecutar(
        actor_id=actor_id, login=login,
        contrasena=CLAVE_FICTICIA, rol_nombre=rol,
    )


def test_esquema_iam_y_revision_sin_fk_a_persona(
    conexion_iam_mysql: Connection,
) -> None:
    assert conexion_iam_mysql.scalar(text("SELECT version_num FROM alembic_version")) in {
        "0002_identity_iam", "0003_sesiones_iam"
    }
    inspector = inspect(conexion_iam_mysql)
    assert {"rol", "usuario_plataforma", "auditoria_iam", "persona"}.issubset(
        inspector.get_table_names()
    )
    esperadas = {
        "rol": {"id_rol", "nombre"},
        "usuario_plataforma": {
            "id_usuario", "login", "hash_contrasena", "id_rol", "estado",
            "fecha_creacion", "fecha_actualizacion",
        },
        "auditoria_iam": {
            "id_auditoria", "actor_id", "usuario_id", "accion", "resultado",
            "anterior", "nuevo", "fecha",
        },
    }
    for tabla, nombres in esperadas.items():
        assert {columna["name"] for columna in inspector.get_columns(tabla)} == nombres

    columnas_rol = {
        columna["name"]: columna for columna in inspector.get_columns("rol")
    }
    assert all(not columna["nullable"] for columna in columnas_rol.values())
    assert inspector.get_pk_constraint("rol")["constrained_columns"] == ["id_rol"]
    columnas_usuario = {
        columna["name"]: columna
        for columna in inspector.get_columns("usuario_plataforma")
    }
    assert all(not columna["nullable"] for columna in columnas_usuario.values())
    assert inspector.get_pk_constraint("usuario_plataforma")["constrained_columns"] == [
        "id_usuario"
    ]
    columnas_auditoria = {
        columna["name"]: columna
        for columna in inspector.get_columns("auditoria_iam")
    }
    assert inspector.get_pk_constraint("auditoria_iam")["constrained_columns"] == [
        "id_auditoria"
    ]
    assert {
        nombre for nombre, columna in columnas_auditoria.items()
        if columna["nullable"]
    } == {"actor_id", "anterior", "nuevo"}

    restricciones = {
        tabla: {
            unica["name"]: unica["column_names"]
            for unica in inspector.get_unique_constraints(tabla)
        }
        for tabla in ("rol", "usuario_plataforma")
    }
    assert restricciones["rol"]["uq_rol_nombre"] == ["nombre"]
    assert restricciones["usuario_plataforma"]["uq_usuario_plataforma_login"] == [
        "login"
    ]
    checks_rol = set(conexion_iam_mysql.execute(text(
        "SELECT CONSTRAINT_NAME FROM information_schema.TABLE_CONSTRAINTS "
        "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'rol' "
        "AND CONSTRAINT_TYPE = 'CHECK'"
    )).scalars())
    assert "ck_rol_nombre_aprobado" in checks_rol
    checks_usuario = set(conexion_iam_mysql.execute(text(
        "SELECT CONSTRAINT_NAME FROM information_schema.TABLE_CONSTRAINTS "
        "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'usuario_plataforma' "
        "AND CONSTRAINT_TYPE = 'CHECK'"
    )).scalars())
    assert "ck_usuario_plataforma_estado" in checks_usuario
    relaciones = {
        tabla: {
            fk["name"]: (
                fk["constrained_columns"], fk["referred_table"],
                fk["referred_columns"],
            )
            for fk in inspector.get_foreign_keys(tabla)
        }
        for tabla in ("rol", "usuario_plataforma", "auditoria_iam")
    }
    assert relaciones["rol"] == {}
    assert relaciones["usuario_plataforma"] == {
        "fk_usuario_plataforma_rol": (["id_rol"], "rol", ["id_rol"])
    }
    assert relaciones["auditoria_iam"] == {
        "fk_auditoria_iam_actor": (
            ["actor_id"], "usuario_plataforma", ["id_usuario"]
        ),
        "fk_auditoria_iam_usuario": (
            ["usuario_id"], "usuario_plataforma", ["id_usuario"]
        ),
    }


def test_catalogo_inicial_y_ausencia_de_cuentas_de_la_migracion(
    conexion_iam_mysql: Connection,
) -> None:
    assert set(conexion_iam_mysql.execute(select(RolModelo.nombre)).scalars()) == ROLES
    assert conexion_iam_mysql.scalar(
        select(func.count()).select_from(UsuarioPlataformaModelo)
    ) == 0
    assert conexion_iam_mysql.scalar(
        select(func.count()).select_from(AuditoriaIAMModelo)
    ) == 0


def test_crear_consultar_cuenta_sin_crear_persona(sesion_iam_mysql: Session) -> None:
    personas_antes = sesion_iam_mysql.scalar(
        select(func.count()).select_from(PersonaModelo)
    )
    actor = _administrador_ficticio(sesion_iam_mysql)
    login = _login()
    creada = _crear_cuenta(sesion_iam_mysql, actor_id=actor.id_usuario, login=login)
    assert creada.id_usuario is not None
    assert creada.rol.nombre == "OPERADOR"
    assert creada.hash_contrasena != CLAVE_FICTICIA
    assert verificar_contrasena(creada.hash_contrasena, CLAVE_FICTICIA)
    sesion_iam_mysql.expire_all()
    consultada = RepositorioIAMSQLAlchemy(sesion_iam_mysql).obtener_por_login(login)
    assert consultada is not None
    assert consultada.id_usuario == creada.id_usuario
    assert consultada.rol.nombre == "OPERADOR"
    assert not hasattr(consultada, "id_persona")
    assert sesion_iam_mysql.scalar(
        select(func.count()).select_from(PersonaModelo)
    ) == personas_antes


def test_cambio_de_rol_conserva_identidad_y_audita(sesion_iam_mysql: Session) -> None:
    actor = _administrador_ficticio(sesion_iam_mysql)
    creada = _crear_cuenta(sesion_iam_mysql, actor_id=actor.id_usuario, login=_login())
    actualizada = CambiarRolUsuario(
        RepositorioIAMSQLAlchemy(sesion_iam_mysql),
        UnidadTrabajoIAMSQLAlchemy(sesion_iam_mysql),
    ).ejecutar(
        actor_id=actor.id_usuario, usuario_id=creada.id_usuario,
        rol_nombre="ADMINISTRADOR",
    )
    assert actualizada.id_usuario == creada.id_usuario
    sesion_iam_mysql.expire_all()
    persistida = RepositorioIAMSQLAlchemy(sesion_iam_mysql).obtener_por_id(
        creada.id_usuario
    )
    assert persistida is not None
    assert persistida.rol.nombre == "ADMINISTRADOR"
    assert sesion_iam_mysql.scalar(
        select(func.count()).select_from(AuditoriaIAMModelo).where(
            AuditoriaIAMModelo.usuario_id == creada.id_usuario,
            AuditoriaIAMModelo.accion == "CAMBIAR_ROL",
            AuditoriaIAMModelo.anterior == "OPERADOR",
            AuditoriaIAMModelo.nuevo == "ADMINISTRADOR",
        )
    ) == 1


def test_mysql_rechaza_login_y_rol_duplicados(sesion_iam_mysql: Session) -> None:
    actor = _administrador_ficticio(sesion_iam_mysql)
    login = _login()
    original = _crear_cuenta(sesion_iam_mysql, actor_id=actor.id_usuario, login=login)
    sesion_iam_mysql.add(UsuarioPlataformaModelo(
        login=login,
        hash_contrasena=generar_hash_contrasena(CLAVE_FICTICIA),
        id_rol=original.rol.id_rol,
    ))
    with pytest.raises(IntegrityError):
        sesion_iam_mysql.flush()
    sesion_iam_mysql.rollback()
    assert RepositorioIAMSQLAlchemy(sesion_iam_mysql).obtener_por_id(
        original.id_usuario
    ) is not None

    sesion_iam_mysql.add(RolModelo(nombre="OPERADOR"))
    with pytest.raises(IntegrityError):
        sesion_iam_mysql.flush()
    sesion_iam_mysql.rollback()


def test_mysql_rechaza_rol_inexistente_y_rol_nulo(sesion_iam_mysql: Session) -> None:
    maximo = sesion_iam_mysql.scalar(select(func.max(RolModelo.id_rol)))
    for id_rol in (maximo + 1000, None):
        login = _login()
        sesion_iam_mysql.add(UsuarioPlataformaModelo(
            login=login,
            hash_contrasena=generar_hash_contrasena(CLAVE_FICTICIA),
            id_rol=id_rol,
        ))
        with pytest.raises(IntegrityError):
            sesion_iam_mysql.flush()
        sesion_iam_mysql.rollback()
        assert RepositorioIAMSQLAlchemy(sesion_iam_mysql).obtener_por_login(login) is None


def test_fallo_posterior_a_flush_revierte_cuenta_y_auditoria(
    sesion_iam_mysql: Session,
) -> None:
    class RepositorioConFallo(RepositorioIAMSQLAlchemy):
        def agregar(self, usuario: UsuarioPlataforma) -> UsuarioPlataforma:
            super().agregar(usuario)
            raise RuntimeError("Fallo ficticio posterior al flush")

    actor = _administrador_ficticio(sesion_iam_mysql)
    login = _login()
    auditorias_antes = sesion_iam_mysql.scalar(
        select(func.count()).select_from(AuditoriaIAMModelo)
    )
    caso = CrearUsuarioPlataforma(
        RepositorioConFallo(sesion_iam_mysql),
        UnidadTrabajoIAMSQLAlchemy(sesion_iam_mysql),
    )
    with pytest.raises(RuntimeError, match="Fallo ficticio"):
        caso.ejecutar(
            actor_id=actor.id_usuario, login=login,
            contrasena=CLAVE_FICTICIA, rol_nombre="OPERADOR",
        )
    assert RepositorioIAMSQLAlchemy(sesion_iam_mysql).obtener_por_login(login) is None
    assert sesion_iam_mysql.scalar(
        select(func.count()).select_from(AuditoriaIAMModelo)
    ) == auditorias_antes


def test_transaccion_externa_aisla_incluso_commits_de_casos_de_uso(
    conexion_iam_mysql: Connection,
) -> None:
    login = _login()
    auditorias_antes = conexion_iam_mysql.scalar(
        select(func.count()).select_from(AuditoriaIAMModelo)
    )
    conexion_iam_mysql.rollback()
    transaccion = conexion_iam_mysql.begin()
    sesion = Session(bind=conexion_iam_mysql, join_transaction_mode="create_savepoint")
    try:
        resultado = BootstrapSuperadmin(
            RepositorioIAMSQLAlchemy(sesion), UnidadTrabajoIAMSQLAlchemy(sesion)
        ).ejecutar(login=login, contrasena=CLAVE_FICTICIA)
        assert resultado.creado
        assert sesion.scalar(
            select(UsuarioPlataformaModelo.id_usuario).where(
                UsuarioPlataformaModelo.login == login
            )
        ) == resultado.usuario.id_usuario
    finally:
        try:
            sesion.close()
        finally:
            if transaccion.is_active:
                transaccion.rollback()

    assert conexion_iam_mysql.scalar(
        select(UsuarioPlataformaModelo.id_usuario).where(
            UsuarioPlataformaModelo.login == login
        )
    ) is None
    assert conexion_iam_mysql.scalar(
        select(func.count()).select_from(AuditoriaIAMModelo)
    ) == auditorias_antes
