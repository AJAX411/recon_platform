"""Casos de uso de PuntoAcceso y su límite transaccional."""

from typing import Protocol

from recon_platform.accesos.dominio import PuntoAcceso, texto
from recon_platform.auditoria.dominio import EventoAuditoria


class PuntoNoExiste(ValueError):
    pass


class PuntoDuplicado(ValueError):
    pass


class IntegridadPunto(ValueError):
    pass


class PermisoPuntoDenegado(ValueError):
    pass


class RepositorioPuntos(Protocol):
    def existe_codigo(self, codigo: str) -> bool: ...
    def agregar(self, punto: PuntoAcceso) -> PuntoAcceso: ...
    def obtener(self, id_punto: int, *, bloquear: bool = False) -> PuntoAcceso | None: ...
    def listar(self, *, limite: int, desplazamiento: int, filtros: dict[str, str]) -> list[PuntoAcceso]: ...
    def actualizar(self, punto: PuntoAcceso) -> PuntoAcceso: ...


class Auditoria(Protocol):
    def agregar(self, evento: EventoAuditoria) -> EventoAuditoria: ...


class UnidadTrabajo(Protocol):
    def confirmar(self) -> None: ...
    def revertir(self) -> None: ...


class AdministrarPuntos:
    def __init__(self, puntos: RepositorioPuntos, auditoria: Auditoria, unidad: UnidadTrabajo) -> None:
        self.puntos, self.auditoria, self.unidad = puntos, auditoria, unidad

    @staticmethod
    def _autorizar(actor_id: int, rol: str, *, editar: bool = False) -> None:
        roles = {"SUPERADMIN", "ADMINISTRADOR"} if editar else {"SUPERADMIN", "ADMINISTRADOR", "OPERADOR"}
        if type(actor_id) is not int or actor_id <= 0 or rol not in roles:
            raise PermisoPuntoDenegado("Permiso de PuntoAcceso denegado.")

    def _transaccion(self, operacion):
        try:
            resultado = operacion()
            self.unidad.confirmar()
            return resultado
        except Exception:
            self.unidad.revertir()
            raise

    def _auditar(self, actor_id: int, accion: str, id_punto: int) -> None:
        self.auditoria.agregar(EventoAuditoria(
            id_usuario_actor=actor_id, accion=accion, resultado="EXITOSO",
            recurso_tipo="PUNTO_ACCESO", id_recurso_afectado=str(id_punto),
        ))

    def crear(self, *, actor_id: int, rol: str, punto: PuntoAcceso) -> PuntoAcceso:
        self._autorizar(actor_id, rol, editar=True)
        def operacion():
            if punto.id_punto_acceso is not None or punto.estado != "ACTIVO" or punto.fecha_creacion is not None:
                raise ValueError("Punto nuevo inválido.")
            if self.puntos.existe_codigo(punto.codigo):
                raise PuntoDuplicado("Código de punto duplicado.")
            guardado = self.puntos.agregar(punto)
            self._auditar(actor_id, "CREAR_PUNTO_ACCESO", guardado.id_punto_acceso)
            return guardado
        return self._transaccion(operacion)

    def consultar(self, *, actor_id: int, rol: str, id_punto: int,
                 bloquear: bool = False) -> PuntoAcceso:
        self._autorizar(actor_id, rol)
        if type(id_punto) is not int or id_punto <= 0:
            raise ValueError("ID de punto inválido.")
        punto = self.puntos.obtener(id_punto, bloquear=bloquear)
        if punto is None:
            raise PuntoNoExiste("Punto inexistente.")
        return punto

    def listar(self, *, actor_id: int, rol: str, limite: int, desplazamiento: int,
               filtros: dict[str, str]) -> list[PuntoAcceso]:
        self._autorizar(actor_id, rol)
        if type(limite) is not int or not 1 <= limite <= 100 or type(desplazamiento) is not int or not 0 <= desplazamiento <= 1_000_000:
            raise ValueError("Paginación inválida.")
        if set(filtros) - {"codigo", "estado"}:
            raise ValueError("Filtro inválido.")
        if "codigo" in filtros:
            texto(filtros["codigo"], 20)
        if "estado" in filtros and filtros["estado"] not in {"ACTIVO", "INACTIVO"}:
            raise ValueError("Estado inválido.")
        return self.puntos.listar(limite=limite, desplazamiento=desplazamiento, filtros=filtros)

    def editar(self, *, actor_id: int, rol: str, id_punto: int, datos: dict) -> PuntoAcceso:
        self._autorizar(actor_id, rol, editar=True)
        if not datos or set(datos) - {"nombre", "descripcion"}:
            raise ValueError("Campos de punto inválidos.")
        def operacion():
            anterior = self.consultar(actor_id=actor_id, rol=rol, id_punto=id_punto, bloquear=True)
            actualizado = PuntoAcceso(id_punto_acceso=anterior.id_punto_acceso, codigo=anterior.codigo,
                nombre=datos.get("nombre", anterior.nombre), descripcion=datos.get("descripcion", anterior.descripcion),
                estado=anterior.estado, fecha_creacion=anterior.fecha_creacion,
                fecha_actualizacion=anterior.fecha_actualizacion)
            guardado = self.puntos.actualizar(actualizado)
            self._auditar(actor_id, "EDITAR_PUNTO_ACCESO", id_punto)
            return guardado
        return self._transaccion(operacion)

    def cambiar_estado(self, *, actor_id: int, rol: str, id_punto: int, estado: str) -> PuntoAcceso:
        self._autorizar(actor_id, rol)
        if not isinstance(estado, str) or estado not in {"ACTIVO", "INACTIVO"}:
            raise ValueError("Estado inválido.")
        def operacion():
            punto = self.consultar(actor_id=actor_id, rol=rol, id_punto=id_punto, bloquear=True)
            punto.estado = estado
            guardado = self.puntos.actualizar(punto)
            self._auditar(actor_id, "CAMBIAR_ESTADO_PUNTO", id_punto)
            return guardado
        return self._transaccion(operacion)
