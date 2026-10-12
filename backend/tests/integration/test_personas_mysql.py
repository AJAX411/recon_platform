"""Contrato de la migración 0001 y casos de uso contra MySQL real.

Estas pruebas requieren activación explícita y nunca crean el esquema.
"""

from datetime import UTC
from uuid import uuid4

import pytest
from sqlalchemy import func, inspect, select, text
from sqlalchemy.engine import Connection
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from recon_platform.personas.aplicacion.casos_de_uso import (
    ConsultarPersona,
    PersonaDuplicada,
    RegistrarPersona,
)
from recon_platform.personas.dominio.persona import Persona
from recon_platform.personas.dominio.tipo_persona import TipoPersona
from recon_platform.personas.infraestructura.modelos import (
    PersonaModelo,
    TipoPersonaModelo,
)
from recon_platform.personas.infraestructura.repositorios import (
    RepositorioPersonasSQLAlchemy,
    RepositorioTiposPersonaSQLAlchemy,
)
from recon_platform.personas.infraestructura.unidad_trabajo import (
    UnidadTrabajoSQLAlchemy,
)

pytestmark = pytest.mark.mysql_integration

NOMBRES_TIPO = {
    "ESTUDIANTE",
    "DOCENTE",
    "ADMINISTRATIVO",
    "SERVICIOS_GENERALES",
    "VISITANTE",
    "PERSONAL_SEGURIDAD",
}


def _codigo() -> str:
    return uuid4().hex[:20].upper()


def _persona(
    *, nombre_tipo: str = "VISITANTE", documento: str | None = None,
    identificador: str | None = None,
) -> Persona:
    return Persona(
        primer_nombre="Persona",
        primer_apellido="Ficticia",
        tipo_persona=TipoPersona(nombre=nombre_tipo),
        tipo_documento="PRUEBA",
        numero_documento=documento or _codigo(),
        identificador_institucional=identificador,
    )


def _registrador(sesion: Session) -> RegistrarPersona:
    return RegistrarPersona(
        RepositorioPersonasSQLAlchemy(sesion),
        RepositorioTiposPersonaSQLAlchemy(sesion),
        UnidadTrabajoSQLAlchemy(sesion),
    )


def test_esquema_de_alembic_tiene_columnas_fk_y_unicidades(
    conexion_mysql: Connection,
) -> None:
    assert conexion_mysql.scalar(text("SELECT version_num FROM alembic_version")) == (
        "0001_personas"
    )
    inspector = inspect(conexion_mysql)
    assert {"alembic_version", "tipo_persona", "persona"}.issubset(
        inspector.get_table_names()
    )
    assert [col["name"] for col in inspector.get_columns("alembic_version")] == [
        "version_num"
    ]

    columnas_tipo = {col["name"]: col for col in inspector.get_columns("tipo_persona")}
    assert set(columnas_tipo) == {
        "id_tipo_persona", "nombre", "descripcion", "estado"
    }
    assert columnas_tipo["nombre"]["nullable"] is False
    assert columnas_tipo["descripcion"]["nullable"] is True
    assert columnas_tipo["estado"]["nullable"] is False
    assert inspector.get_pk_constraint("tipo_persona")["constrained_columns"] == [
        "id_tipo_persona"
    ]

    columnas = {col["name"]: col for col in inspector.get_columns("persona")}
    assert set(columnas) == {
        "id_persona", "id_tipo_persona", "identificador_institucional",
        "tipo_documento", "numero_documento", "primer_nombre", "segundo_nombre",
        "primer_apellido", "segundo_apellido", "estado", "fecha_creacion",
        "fecha_actualizacion",
    }
    assert columnas["identificador_institucional"]["nullable"] is True
    assert columnas["segundo_nombre"]["nullable"] is True
    assert columnas["segundo_apellido"]["nullable"] is True
    for nombre in (
        "id_tipo_persona", "tipo_documento", "numero_documento",
        "primer_nombre", "primer_apellido", "estado", "fecha_creacion",
        "fecha_actualizacion",
    ):
        assert columnas[nombre]["nullable"] is False
    assert inspector.get_pk_constraint("persona")["constrained_columns"] == [
        "id_persona"
    ]

    for tabla, esperadas in (
        ("tipo_persona", {"uq_tipo_persona_nombre": ["nombre"]}),
        ("persona", {
            "uq_persona_identificador_institucional": [
                "identificador_institucional"
            ],
            "uq_persona_documento": ["tipo_documento", "numero_documento"],
        }),
    ):
        encontradas = {
            restriccion["name"]: restriccion["column_names"]
            for restriccion in inspector.get_unique_constraints(tabla)
        }
        for nombre, columnas_esperadas in esperadas.items():
            assert encontradas[nombre] == columnas_esperadas

    assert any(
        fk["name"] == "fk_persona_tipo_persona"
        and fk["constrained_columns"] == ["id_tipo_persona"]
        and fk["referred_table"] == "tipo_persona"
        and fk["referred_columns"] == ["id_tipo_persona"]
        for fk in inspector.get_foreign_keys("persona")
    )


def test_catalogo_inicial_de_tipo_persona(conexion_mysql: Connection) -> None:
    filas = conexion_mysql.execute(
        select(TipoPersonaModelo.nombre, TipoPersonaModelo.estado)
    ).all()
    assert {nombre for nombre, _ in filas} == NOMBRES_TIPO
    assert all(estado == "ACTIVO" for _, estado in filas)


def test_registrar_y_consultar_persona_ficticia(sesion_mysql: Session) -> None:
    registrada = _registrador(sesion_mysql).ejecutar(
        _persona(nombre_tipo="ESTUDIANTE", identificador=f"TEST-{_codigo()}")
    )
    assert registrada.id_persona is not None
    assert registrada.estado == "ACTIVO"
    assert registrada.fecha_creacion.tzinfo == UTC
    assert registrada.fecha_actualizacion.tzinfo == UTC

    sesion_mysql.expire_all()
    consultada = ConsultarPersona(RepositorioPersonasSQLAlchemy(sesion_mysql)).ejecutar(
        registrada.id_persona
    )
    assert consultada is not None
    assert consultada.numero_documento == registrada.numero_documento
    assert consultada.tipo_persona.nombre == "ESTUDIANTE"
    assert consultada.tipo_persona.id_tipo_persona is not None


@pytest.mark.parametrize("duplicado", ["documento", "institucional"])
def test_caso_de_uso_rechaza_duplicados(
    sesion_mysql: Session, duplicado: str
) -> None:
    documento = _codigo()
    identificador = f"TEST-{_codigo()}"
    original = _registrador(sesion_mysql).ejecutar(
        _persona(nombre_tipo="ESTUDIANTE", documento=documento,
                 identificador=identificador)
    )
    candidato = _persona(
        nombre_tipo="ESTUDIANTE",
        documento=documento if duplicado == "documento" else _codigo(),
        identificador=identificador if duplicado == "institucional" else f"TEST-{_codigo()}",
    )

    with pytest.raises(PersonaDuplicada):
        _registrador(sesion_mysql).ejecutar(candidato)
    assert ConsultarPersona(RepositorioPersonasSQLAlchemy(sesion_mysql)).ejecutar(
        original.id_persona
    ) is not None


@pytest.mark.parametrize("duplicado", ["documento", "institucional"])
def test_mysql_impide_duplicados_aun_sin_validacion_de_aplicacion(
    sesion_mysql: Session, duplicado: str
) -> None:
    documento = _codigo()
    identificador = f"TEST-{_codigo()}"
    original = _registrador(sesion_mysql).ejecutar(
        _persona(nombre_tipo="ESTUDIANTE", documento=documento,
                 identificador=identificador)
    )
    sesion_mysql.add(PersonaModelo(
        id_tipo_persona=original.tipo_persona.id_tipo_persona,
        primer_nombre="Otra",
        primer_apellido="Ficticia",
        tipo_documento="PRUEBA",
        numero_documento=documento if duplicado == "documento" else _codigo(),
        identificador_institucional=(
            identificador if duplicado == "institucional" else f"TEST-{_codigo()}"
        ),
    ))

    with pytest.raises(IntegrityError):
        sesion_mysql.flush()
    sesion_mysql.rollback()
    assert ConsultarPersona(RepositorioPersonasSQLAlchemy(sesion_mysql)).ejecutar(
        original.id_persona
    ) is not None


def test_dos_visitantes_sin_identificador_y_fk_valida(sesion_mysql: Session) -> None:
    registrar = _registrador(sesion_mysql)
    primera = registrar.ejecutar(_persona())
    segunda = registrar.ejecutar(_persona())

    assert primera.id_persona != segunda.id_persona
    assert primera.identificador_institucional is None
    assert segunda.identificador_institucional is None
    assert primera.tipo_persona.id_tipo_persona == segunda.tipo_persona.id_tipo_persona
    assert sesion_mysql.scalar(
        select(func.count()).select_from(PersonaModelo).where(
            PersonaModelo.id_persona.in_([primera.id_persona, segunda.id_persona]),
            PersonaModelo.identificador_institucional.is_(None),
        )
    ) == 2


def test_mysql_rechaza_tipo_persona_inexistente(sesion_mysql: Session) -> None:
    maximo = sesion_mysql.scalar(select(func.max(TipoPersonaModelo.id_tipo_persona)))
    documento = _codigo()
    sesion_mysql.add(PersonaModelo(
        id_tipo_persona=maximo + 1000,
        primer_nombre="Persona",
        primer_apellido="Ficticia",
        tipo_documento="PRUEBA",
        numero_documento=documento,
    ))

    with pytest.raises(IntegrityError):
        sesion_mysql.flush()
    sesion_mysql.rollback()
    assert not sesion_mysql.scalar(
        select(PersonaModelo.id_persona).where(PersonaModelo.numero_documento == documento)
    )


def test_caso_de_uso_revierte_insert_si_falla_despues_de_flush(
    sesion_mysql: Session,
) -> None:
    class RepositorioConFallo(RepositorioPersonasSQLAlchemy):
        def agregar(self, persona: Persona) -> Persona:
            super().agregar(persona)
            raise RuntimeError("Fallo ficticio posterior al flush")

    documento = _codigo()
    caso = RegistrarPersona(
        RepositorioConFallo(sesion_mysql),
        RepositorioTiposPersonaSQLAlchemy(sesion_mysql),
        UnidadTrabajoSQLAlchemy(sesion_mysql),
    )
    with pytest.raises(RuntimeError, match="Fallo ficticio"):
        caso.ejecutar(_persona(documento=documento))

    assert not sesion_mysql.scalar(
        select(PersonaModelo.id_persona).where(PersonaModelo.numero_documento == documento)
    )
