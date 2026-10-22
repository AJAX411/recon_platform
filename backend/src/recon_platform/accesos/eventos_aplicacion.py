"""Casos de uso de accesos manuales y consultas con política por rol."""

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Callable, Protocol
from uuid import UUID

from recon_platform.accesos.eventos_dominio import (
    EventoAcceso, MOVIMIENTOS, incidencia_secuencia, jornada_utc,
)
from recon_platform.auditoria.dominio import EventoAuditoria

ROLES = frozenset({"OPERADOR", "ADMINISTRADOR", "SUPERADMIN"})
ADMIN = frozenset({"ADMINISTRADOR", "SUPERADMIN"})


class ReferenciaNoDisponible(ValueError):
    pass


class ConflictoIdempotencia(ValueError):
    pass


class ClaveEnCarrera(Exception):
    pass


class PersistenciaAccesoError(Exception):
    pass


@dataclass(frozen=True, slots=True)
class ActorAcceso:
    id_usuario: int
    rol: str


@dataclass(frozen=True, slots=True)
class ResultadoRegistro:
    evento: EventoAcceso
    repetido: bool


def autorizar(actor: ActorAcceso, *, administrativo: bool = False) -> None:
    permitidos = ADMIN if administrativo else ROLES
    if (not isinstance(actor, ActorAcceso) or type(actor.id_usuario) is not int
        or actor.id_usuario <= 0 or actor.rol not in permitidos):
        raise PermissionError("Permiso de acceso denegado.")


def clave_valida(valor: object) -> str:
    if not isinstance(valor, str) or len(valor) != 36:
        raise ValueError("Clave idempotente inválida.")
    try:
        clave = UUID(valor)
    except ValueError as error:
        raise ValueError("Clave idempotente inválida.") from error
    if clave.version != 4 or str(clave) != valor:
        raise ValueError("Clave idempotente inválida.")
    return valor


class RepositorioEventos(Protocol):
    def actor_vigente(self, id_usuario: int, rol: str) -> bool: ...
    def bloquear_persona(self, id_persona: int) -> str | None: ...
    def bloquear_punto(self, id_punto: int) -> str | None: ...
    def por_clave(self, clave: str) -> EventoAcceso | None: ...
    def ultimo_autorizado(self, id_persona: int, inicio: datetime, fin: datetime) -> str | None: ...
    def agregar(self, evento: EventoAcceso) -> EventoAcceso: ...
    def buscar_personas(self, *, criterio: str, valor: str) -> list[dict]: ...
    def historial_operador(self, *, inicio: datetime, fin: datetime,
                           limite: int, desplazamiento: int) -> list[dict]: ...
    def historial_admin(self, *, limite: int, desplazamiento: int, filtros: dict) -> list[dict]: ...
    def alertas_operador(self, *, inicio: datetime, fin: datetime) -> dict[str, int]: ...
    def alertas_admin(self, *, limite: int, desplazamiento: int, filtros: dict) -> list[dict]: ...
    def incidencia_detalle(self, id_evento: int) -> dict | None: ...


class Auditoria(Protocol):
    def agregar(self, evento: EventoAuditoria) -> EventoAuditoria: ...


class UnidadTrabajo(Protocol):
    def iniciar(self) -> None: ...
    def confirmar(self) -> None: ...
    def revertir(self) -> None: ...


class RegistrarEventoManual:
    def __init__(self, eventos: RepositorioEventos, auditoria: Auditoria,
                 unidad: UnidadTrabajo, reloj: Callable[[], datetime] | None = None) -> None:
        self.eventos, self.auditoria, self.unidad = eventos, auditoria, unidad
        self.reloj = reloj or (lambda: datetime.now(UTC))

    @staticmethod
    def _mismo(evento: EventoAcceso, actor: ActorAcceso, persona: int,
               punto: int, movimiento: str) -> bool:
        return (evento.metodo_registro == "MANUAL"
                and (evento.id_usuario_registrador, evento.id_persona,
                     evento.id_punto_acceso, evento.tipo_movimiento)
                == (actor.id_usuario, persona, punto, movimiento))

    def ejecutar(self, *, actor: ActorAcceso, id_persona: int, id_punto_acceso: int,
                tipo_movimiento: str, clave: str) -> ResultadoRegistro:
        autorizar(actor)
        if (type(id_persona) is not int or id_persona <= 0
            or type(id_punto_acceso) is not int or id_punto_acceso <= 0
            or not isinstance(tipo_movimiento, str) or tipo_movimiento not in MOVIMIENTOS):
            raise ValueError("Declaración manual inválida.")
        clave = clave_valida(clave)
        self.unidad.iniciar()  # Cierra la lectura implícita del guard IAM.
        try:
            if not self.eventos.actor_vigente(actor.id_usuario, actor.rol):
                raise PermissionError("Actor no autorizado actualmente.")
            estado_persona = self.eventos.bloquear_persona(id_persona)
            if estado_persona is None:
                raise ReferenciaNoDisponible("Persona no disponible.")
            anterior = self.eventos.por_clave(clave)
            if anterior is not None:
                if not self._mismo(anterior, actor, id_persona, id_punto_acceso, tipo_movimiento):
                    raise ConflictoIdempotencia("La clave pertenece a otra declaración.")
                self.unidad.revertir()
                return ResultadoRegistro(anterior, True)
            # Los estados actuales se exigen solo para una declaración nueva.
            if estado_persona != "ACTIVO":
                raise ReferenciaNoDisponible("Persona no disponible.")
            if self.eventos.bloquear_punto(id_punto_acceso) != "ACTIVO":
                raise ReferenciaNoDisponible("Punto no disponible.")
            ahora = self.reloj()
            if not isinstance(ahora, datetime) or ahora.tzinfo is None:
                raise ValueError("Reloj UTC inválido.")
            ahora = ahora.astimezone(UTC)
            inicio, fin = jornada_utc(ahora)
            ultimo = self.eventos.ultimo_autorizado(id_persona, inicio, fin)
            evento = self.eventos.agregar(EventoAcceso(
                id_persona=id_persona, id_punto_acceso=id_punto_acceso,
                tipo_movimiento=tipo_movimiento, resultado="AUTORIZADO",
                metodo_registro="MANUAL", id_usuario_registrador=actor.id_usuario,
                fecha_hora_ocurrencia=ahora,
                tipo_incidencia_secuencia=incidencia_secuencia(ultimo, tipo_movimiento),
                clave_idempotencia=clave,
            ))
            self.auditoria.agregar(EventoAuditoria(
                id_usuario_actor=actor.id_usuario, accion="REGISTRAR_EVENTO_ACCESO_MANUAL",
                resultado="EXITOSO", recurso_tipo="EVENTO_ACCESO",
                id_recurso_afectado=str(evento.id_evento_acceso),
            ))
            self.unidad.confirmar()
            return ResultadoRegistro(evento, False)
        except ClaveEnCarrera:
            self.unidad.revertir()
            # La UNIQUE puede resolver una carrera entre Personas distintas.
            try:
                ganador = self.eventos.por_clave(clave)
                if ganador is None:
                    raise PersistenciaAccesoError("No se resolvió la clave concurrente.")
                if not self._mismo(ganador, actor, id_persona, id_punto_acceso, tipo_movimiento):
                    raise ConflictoIdempotencia("La clave pertenece a otra declaración.")
                return ResultadoRegistro(ganador, True)
            finally:
                self.unidad.revertir()
        except Exception:
            self.unidad.revertir()
            raise


class ConsultarEventosAcceso:
    def __init__(self, eventos: RepositorioEventos, reloj: Callable[[], datetime] | None = None) -> None:
        self.eventos = eventos
        self.reloj = reloj or (lambda: datetime.now(UTC))

    def buscar_personas(self, *, actor: ActorAcceso, criterio: str, valor: str) -> list[dict]:
        autorizar(actor)
        if criterio not in {"documento", "institucional", "nombre"} or not isinstance(valor, str):
            raise ValueError("Criterio inválido.")
        valor = valor.strip()
        if not 3 <= len(valor) <= 50 or any(ord(c) < 32 for c in valor):
            raise ValueError("Búsqueda inválida.")
        return self.eventos.buscar_personas(criterio=criterio, valor=valor)

    def historial(self, *, actor: ActorAcceso, limite: int, desplazamiento: int,
                  filtros: dict) -> list[dict]:
        autorizar(actor)
        self._paginacion(limite, desplazamiento)
        if actor.rol == "OPERADOR":
            if filtros:
                raise ValueError("Filtros no permitidos.")
            inicio, fin = jornada_utc(self.reloj())
            return self.eventos.historial_operador(inicio=inicio, fin=fin,
                limite=limite, desplazamiento=desplazamiento)
        return self.eventos.historial_admin(limite=limite, desplazamiento=desplazamiento,
                                             filtros=filtros)

    def alertas(self, *, actor: ActorAcceso, limite: int, desplazamiento: int,
                filtros: dict) -> dict | list[dict]:
        autorizar(actor)
        self._paginacion(limite, desplazamiento)
        if actor.rol == "OPERADOR":
            if filtros or desplazamiento != 0:
                raise ValueError("Filtros no permitidos.")
            inicio, fin = jornada_utc(self.reloj())
            return self.eventos.alertas_operador(inicio=inicio, fin=fin)
        return self.eventos.alertas_admin(limite=limite, desplazamiento=desplazamiento,
                                          filtros=filtros)

    def detalle(self, *, actor: ActorAcceso, id_evento: int) -> dict:
        autorizar(actor, administrativo=True)
        if type(id_evento) is not int or id_evento <= 0:
            raise ValueError("Evento inválido.")
        detalle = self.eventos.incidencia_detalle(id_evento)
        if detalle is None:
            raise ReferenciaNoDisponible("Incidencia no disponible.")
        return detalle

    @staticmethod
    def _paginacion(limite: int, desplazamiento: int) -> None:
        if (type(limite) is not int or not 1 <= limite <= 100
            or type(desplazamiento) is not int or not 0 <= desplazamiento <= 1_000_000):
            raise ValueError("Paginación inválida.")
