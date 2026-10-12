"""Registro y consulta internos, sin interfaz HTTP ni biometría."""

from recon_platform.personas.aplicacion.puertos import (
    RepositorioPersonas,
    RepositorioTiposPersona,
    UnidadTrabajo,
)
from recon_platform.personas.dominio.persona import Persona


class TipoPersonaNoExiste(ValueError):
    """La clasificación solicitada no está en el catálogo persistido."""


class PersonaDuplicada(ValueError):
    """Un identificador aprobado ya corresponde a otra Persona."""


class ConflictoIntegridad(ValueError):
    """La base de datos rechazó una operación de Persona."""


class RegistrarPersona:
    """Valida identificadores y confirma una sola transacción por registro."""

    def __init__(
        self,
        personas: RepositorioPersonas,
        tipos: RepositorioTiposPersona,
        unidad_trabajo: UnidadTrabajo,
    ) -> None:
        self.personas = personas
        self.tipos = tipos
        self.unidad_trabajo = unidad_trabajo

    def ejecutar(self, persona: Persona) -> Persona:
        if persona.id_persona is not None:
            raise ValueError("Una Persona nueva no puede traer id_persona.")
        if persona.estado != "ACTIVO":
            raise ValueError("Una Persona nueva debe iniciar en estado ACTIVO.")
        if persona.fecha_creacion is not None or persona.fecha_actualizacion is not None:
            raise ValueError("Las fechas de una Persona nueva las asigna la persistencia.")
        try:
            tipo_persistido = self.tipos.obtener_por_nombre(persona.tipo_persona.nombre)
            if tipo_persistido is None:
                raise TipoPersonaNoExiste("El TipoPersona no existe en el catálogo.")
            persona.tipo_persona = tipo_persistido

            if self.personas.existe_documento(
                persona.tipo_documento, persona.numero_documento
            ):
                raise PersonaDuplicada("Ya existe una Persona con ese documento.")
            identificador = persona.identificador_institucional
            if identificador is not None and self.personas.existe_identificador_institucional(
                identificador
            ):
                raise PersonaDuplicada(
                    "Ya existe una Persona con ese identificador institucional."
                )

            registrada = self.personas.agregar(persona)
            self.unidad_trabajo.confirmar()
            return registrada
        except Exception:
            self.unidad_trabajo.revertir()
            raise


class ConsultarPersona:
    """Recupera una Persona por su identificador interno estable."""

    def __init__(self, personas: RepositorioPersonas) -> None:
        self.personas = personas

    def ejecutar(self, id_persona: int) -> Persona | None:
        if not isinstance(id_persona, int) or id_persona <= 0:
            raise ValueError("id_persona debe ser un entero positivo.")
        return self.personas.obtener_por_id(id_persona)
