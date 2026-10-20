"""Casos de uso administrativos de Personas, sin dependencia HTTP ni biométrica."""

from dataclasses import dataclass

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


class PersonaNoExiste(ValueError):
    """No existe el identificador interno solicitado."""


class DatosInvalidosPersona(ValueError):
    """El cambio administrativo incumple una regla de Persona."""


class PermisoPersonasDenegado(ValueError):
    """El actor no puede acceder a información personal."""


@dataclass(frozen=True, slots=True)
class ActorPersonas:
    id_usuario: int
    rol: str


def _exigir_administrador(actor: ActorPersonas) -> None:
    if (not isinstance(actor, ActorPersonas) or type(actor.id_usuario) is not int
        or actor.id_usuario <= 0 or actor.rol not in {"SUPERADMIN", "ADMINISTRADOR"}):
        raise PermisoPersonasDenegado("La operación requiere administración de Personas.")


def _id_valido(id_persona: int) -> None:
    if type(id_persona) is not int or id_persona <= 0:
        raise ValueError("id_persona debe ser un entero positivo.")


def _registrar(persona: Persona, personas: RepositorioPersonas,
               tipos: RepositorioTiposPersona) -> Persona:
    if persona.id_persona is not None or persona.estado != "ACTIVO":
        raise ValueError("Una Persona nueva debe iniciar sin ID y en estado ACTIVO.")
    if persona.fecha_creacion is not None or persona.fecha_actualizacion is not None:
        raise ValueError("Las fechas de una Persona nueva las asigna la persistencia.")
    tipo = tipos.obtener_por_nombre(persona.tipo_persona.nombre)
    if tipo is None or tipo.estado != "ACTIVO":
        raise TipoPersonaNoExiste("El TipoPersona no está disponible.")
    persona.tipo_persona = tipo
    if personas.existe_documento(persona.tipo_documento, persona.numero_documento):
        raise PersonaDuplicada("Ya existe una Persona con ese documento.")
    if (persona.identificador_institucional is not None
        and personas.existe_identificador_institucional(persona.identificador_institucional)):
        raise PersonaDuplicada("Ya existe una Persona con ese identificador institucional.")
    return personas.agregar(persona)


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
        try:
            registrada = _registrar(persona, self.personas, self.tipos)
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
        _id_valido(id_persona)
        return self.personas.obtener_por_id(id_persona)


class AdministrarPersonas:
    """Todas las escrituras incluyen auditoría en la misma transacción."""

    def __init__(self, personas: RepositorioPersonas, tipos: RepositorioTiposPersona,
                 unidad_trabajo: UnidadTrabajo) -> None:
        self.personas, self.tipos, self.unidad_trabajo = personas, tipos, unidad_trabajo

    def _transaccion(self, operacion):
        try:
            resultado = operacion()
            self.unidad_trabajo.confirmar()
            return resultado
        except Exception:
            self.unidad_trabajo.revertir()
            raise

    def registrar(self, *, actor: ActorPersonas, persona: Persona) -> Persona:
        _exigir_administrador(actor)
        def operacion():
            registrada = _registrar(persona, self.personas, self.tipos)
            self.personas.auditar(actor_id=actor.id_usuario, accion="REGISTRAR_PERSONA",
                                  id_persona=registrada.id_persona)
            return registrada
        return self._transaccion(operacion)

    def consultar(self, *, actor: ActorPersonas, id_persona: int) -> Persona:
        _exigir_administrador(actor)
        _id_valido(id_persona)
        persona = self.personas.obtener_por_id(id_persona)
        if persona is None:
            raise PersonaNoExiste("La Persona no existe.")
        return persona

    def listar(self, *, actor: ActorPersonas, limite: int = 50,
               desplazamiento: int = 0, filtros: dict[str, str] | None = None) -> list[Persona]:
        _exigir_administrador(actor)
        if (type(limite) is not int or not 1 <= limite <= 100
            or type(desplazamiento) is not int or not 0 <= desplazamiento <= 1_000_000):
            raise ValueError("La paginación no es válida.")
        filtros = filtros or {}
        if set(filtros) - {"tipo_documento", "numero_documento", "identificador_institucional",
                            "tipo_persona", "estado"}:
            raise ValueError("Los filtros no son válidos.")
        return self.personas.listar(limite=limite, desplazamiento=desplazamiento, filtros=filtros)

    def listar_tipos(self, *, actor: ActorPersonas):
        _exigir_administrador(actor)
        return self.tipos.listar()

    def actualizar(self, *, actor: ActorPersonas, id_persona: int,
                   datos: dict[str, object]) -> Persona:
        _exigir_administrador(actor)
        def operacion():
            anterior = self.consultar(actor=actor, id_persona=id_persona)
            tipo_nombre = datos.get("tipo_persona", anterior.tipo_persona.nombre)
            tipo = self.tipos.obtener_por_nombre(tipo_nombre)
            if tipo is None or tipo.estado != "ACTIVO":
                raise TipoPersonaNoExiste("El TipoPersona no está disponible.")
            campos = {nombre: getattr(anterior, nombre) for nombre in (
                "primer_nombre", "segundo_nombre", "primer_apellido", "segundo_apellido",
                "tipo_documento", "numero_documento", "identificador_institucional")}
            campos.update({nombre: valor for nombre, valor in datos.items() if nombre in campos})
            try:
                nueva = Persona(**campos, tipo_persona=tipo, estado=anterior.estado,
                                id_persona=id_persona, fecha_creacion=anterior.fecha_creacion,
                                fecha_actualizacion=anterior.fecha_actualizacion)
            except ValueError as error:
                raise DatosInvalidosPersona("Los datos de Persona no son válidos.") from error
            if ((nueva.tipo_documento, nueva.numero_documento) !=
                (anterior.tipo_documento, anterior.numero_documento)
                and self.personas.existe_documento(nueva.tipo_documento, nueva.numero_documento,
                                                  excluir_id=id_persona)):
                raise PersonaDuplicada("Ya existe una Persona con ese documento.")
            if (nueva.identificador_institucional is not None
                and nueva.identificador_institucional != anterior.identificador_institucional
                and self.personas.existe_identificador_institucional(
                    nueva.identificador_institucional, excluir_id=id_persona)):
                raise PersonaDuplicada("Ya existe una Persona con ese identificador institucional.")
            actualizada = self.personas.actualizar(nueva)
            self.personas.auditar(actor_id=actor.id_usuario, accion="ACTUALIZAR_PERSONA",
                                  id_persona=id_persona)
            return actualizada
        return self._transaccion(operacion)

    def cambiar_estado(self, *, actor: ActorPersonas, id_persona: int,
                       estado: str) -> Persona:
        _exigir_administrador(actor)
        if estado not in {"ACTIVO", "INACTIVO"}:
            raise ValueError("El estado de Persona no es válido.")
        def operacion():
            persona = self.consultar(actor=actor, id_persona=id_persona)
            if persona.estado == estado:
                return persona
            persona.estado = estado
            actualizada = self.personas.actualizar(persona)
            self.personas.auditar(actor_id=actor.id_usuario,
                                  accion="ACTIVAR_PERSONA" if estado == "ACTIVO" else "DESACTIVAR_PERSONA",
                                  id_persona=id_persona)
            return actualizada
        return self._transaccion(operacion)
