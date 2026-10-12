"""Persistencia de Personas sin confirmar transacciones por cuenta propia."""

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from recon_platform.personas.aplicacion.casos_de_uso import (
    ConflictoIntegridad,
    PersonaDuplicada,
)
from recon_platform.personas.dominio.persona import Persona
from recon_platform.personas.dominio.tipo_persona import TipoPersona
from recon_platform.personas.infraestructura.modelos import (
    PersonaModelo,
    TipoPersonaModelo,
)


def _utc_con_zona(valor: datetime) -> datetime:
    return valor.replace(tzinfo=UTC) if valor.tzinfo is None else valor.astimezone(UTC)


def _traducir_integridad(error: IntegrityError) -> ValueError:
    argumentos = getattr(error.orig, "args", ())
    codigo = argumentos[0] if argumentos else None
    if codigo == 1062 or "UNIQUE constraint failed" in str(error.orig):
        return PersonaDuplicada("Ya existe una Persona con ese identificador.")
    return ConflictoIntegridad("La base de datos rechazó el registro de Persona.")


class RepositorioTiposPersonaSQLAlchemy:
    def __init__(self, sesion: Session) -> None:
        self.sesion = sesion

    def obtener_por_nombre(self, nombre: str) -> TipoPersona | None:
        modelo = self.sesion.scalar(
            select(TipoPersonaModelo).where(TipoPersonaModelo.nombre == nombre)
        )
        if modelo is None:
            return None
        return TipoPersona(
            id_tipo_persona=modelo.id_tipo_persona,
            nombre=modelo.nombre,
            descripcion=modelo.descripcion,
            estado=modelo.estado,
        )


class RepositorioPersonasSQLAlchemy:
    def __init__(self, sesion: Session) -> None:
        self.sesion = sesion

    def existe_documento(self, tipo: str, numero: str) -> bool:
        return (
            self.sesion.scalar(
                select(PersonaModelo.id_persona).where(
                    PersonaModelo.tipo_documento == tipo,
                    PersonaModelo.numero_documento == numero,
                )
            )
            is not None
        )

    def existe_identificador_institucional(self, identificador: str) -> bool:
        return (
            self.sesion.scalar(
                select(PersonaModelo.id_persona).where(
                    PersonaModelo.identificador_institucional == identificador
                )
            )
            is not None
        )

    def agregar(self, persona: Persona) -> Persona:
        tipo_id = persona.tipo_persona.id_tipo_persona
        if tipo_id is None:
            raise ConflictoIntegridad("El TipoPersona debe existir antes del registro.")
        modelo = PersonaModelo(
            id_tipo_persona=tipo_id,
            identificador_institucional=persona.identificador_institucional,
            tipo_documento=persona.tipo_documento,
            numero_documento=persona.numero_documento,
            primer_nombre=persona.primer_nombre,
            segundo_nombre=persona.segundo_nombre,
            primer_apellido=persona.primer_apellido,
            segundo_apellido=persona.segundo_apellido,
            estado=persona.estado,
        )
        self.sesion.add(modelo)
        try:
            self.sesion.flush()
        except IntegrityError as error:
            raise _traducir_integridad(error) from error
        return self._a_dominio(modelo)

    def obtener_por_id(self, id_persona: int) -> Persona | None:
        modelo = self.sesion.get(PersonaModelo, id_persona)
        return None if modelo is None else self._a_dominio(modelo)

    @staticmethod
    def _a_dominio(modelo: PersonaModelo) -> Persona:
        tipo = modelo.tipo_persona
        return Persona(
            id_persona=modelo.id_persona,
            primer_nombre=modelo.primer_nombre,
            segundo_nombre=modelo.segundo_nombre,
            primer_apellido=modelo.primer_apellido,
            segundo_apellido=modelo.segundo_apellido,
            tipo_documento=modelo.tipo_documento,
            numero_documento=modelo.numero_documento,
            identificador_institucional=modelo.identificador_institucional,
            estado=modelo.estado,
            fecha_creacion=_utc_con_zona(modelo.fecha_creacion),
            fecha_actualizacion=_utc_con_zona(modelo.fecha_actualizacion),
            tipo_persona=TipoPersona(
                id_tipo_persona=tipo.id_tipo_persona,
                nombre=tipo.nombre,
                descripcion=tipo.descripcion,
                estado=tipo.estado,
            ),
        )
