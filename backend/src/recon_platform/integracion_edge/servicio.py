"""Servicios y casos de uso existentes."""

import json

from recon_platform.accesos.punto_acceso import texto
from recon_platform.auditoria.evento_auditoria import EventoAuditoria
from recon_platform.integracion_edge.dispositivo_edge import DispositivoEdge, ESTADOS, MODOS
from recon_platform.integracion_edge.contratos import Auditoria, ConsultaPuntos, RepositorioDispositivos, UnidadTrabajo


class DispositivoNoExiste(ValueError):
    pass


class DispositivoDuplicado(ValueError):
    pass


class PuntoAsociadoNoExiste(ValueError):
    pass


class IntegridadDispositivo(ValueError):
    pass


class PermisoDispositivoDenegado(ValueError):
    pass


class AdministrarDispositivos:
    def __init__(self, dispositivos: RepositorioDispositivos, puntos: ConsultaPuntos,
                 auditoria: Auditoria, unidad: UnidadTrabajo) -> None:
        self.dispositivos, self.puntos = dispositivos, puntos
        self.auditoria, self.unidad = auditoria, unidad

    @staticmethod
    def _autorizar(actor_id: int, rol: str, *, editar: bool = False) -> None:
        roles = {"SUPERADMIN", "ADMINISTRADOR"} if editar else {"SUPERADMIN", "ADMINISTRADOR", "OPERADOR"}
        if type(actor_id) is not int or actor_id <= 0 or rol not in roles:
            raise PermisoDispositivoDenegado("Permiso de DispositivoEdge denegado.")

    def _transaccion(self, operacion):
        try:
            resultado = operacion()
            self.unidad.confirmar()
            return resultado
        except Exception:
            self.unidad.revertir()
            raise

    def _auditar(self, actor_id: int, accion: str, id_dispositivo: int,
                 detalle: str | None = None) -> None:
        self.auditoria.agregar(EventoAuditoria(
            id_usuario_actor=actor_id, accion=accion, resultado="EXITOSO",
            recurso_tipo="DISPOSITIVO_EDGE", id_recurso_afectado=str(id_dispositivo),
            detalle=detalle,
        ))

    def crear(self, *, actor_id: int, rol: str, dispositivo: DispositivoEdge) -> DispositivoEdge:
        self._autorizar(actor_id, rol, editar=True)
        def operacion():
            if (dispositivo.id_dispositivo is not None or dispositivo.estado != "INACTIVO"
                or dispositivo.ultima_comunicacion is not None or dispositivo.fecha_creacion is not None):
                raise ValueError("Dispositivo nuevo inválido.")
            if not self.puntos.existe(dispositivo.id_punto_acceso):
                raise PuntoAsociadoNoExiste("Punto asociado inexistente.")
            if self.dispositivos.existe_codigo(dispositivo.codigo):
                raise DispositivoDuplicado("Código de dispositivo duplicado.")
            guardado = self.dispositivos.agregar(dispositivo)
            id_dispositivo = guardado.id_dispositivo
            if type(id_dispositivo) is not int or id_dispositivo <= 0:
                raise IntegridadDispositivo("La persistencia no asignó un ID de DispositivoEdge válido.")
            self._auditar(actor_id, "CREAR_DISPOSITIVO_EDGE", id_dispositivo)
            return guardado
        return self._transaccion(operacion)

    def consultar(self, *, actor_id: int, rol: str, id_dispositivo: int,
                 bloquear: bool = False) -> DispositivoEdge:
        self._autorizar(actor_id, rol)
        if type(id_dispositivo) is not int or id_dispositivo <= 0:
            raise ValueError("ID de dispositivo inválido.")
        dispositivo = self.dispositivos.obtener(id_dispositivo, bloquear=bloquear)
        if dispositivo is None:
            raise DispositivoNoExiste("Dispositivo inexistente.")
        return dispositivo

    def listar(self, *, actor_id: int, rol: str, limite: int, desplazamiento: int,
               filtros: dict) -> list[DispositivoEdge]:
        self._autorizar(actor_id, rol)
        if type(limite) is not int or not 1 <= limite <= 100 or type(desplazamiento) is not int or not 0 <= desplazamiento <= 1_000_000:
            raise ValueError("Paginación inválida.")
        if set(filtros) - {"codigo", "estado", "modo_operacion", "id_punto_acceso"}:
            raise ValueError("Filtro inválido.")
        if "codigo" in filtros:
            texto(filtros["codigo"], 20)
        if "estado" in filtros and filtros["estado"] not in ESTADOS:
            raise ValueError("Estado inválido.")
        if "modo_operacion" in filtros and filtros["modo_operacion"] not in MODOS:
            raise ValueError("Modo inválido.")
        if "id_punto_acceso" in filtros and (type(filtros["id_punto_acceso"]) is not int or filtros["id_punto_acceso"] <= 0):
            raise ValueError("Punto inválido.")
        return self.dispositivos.listar(limite=limite, desplazamiento=desplazamiento, filtros=filtros)

    def editar(self, *, actor_id: int, rol: str, id_dispositivo: int, nombre: str) -> DispositivoEdge:
        self._autorizar(actor_id, rol, editar=True)
        def operacion():
            dispositivo = self.consultar(actor_id=actor_id, rol=rol, id_dispositivo=id_dispositivo,
                                          bloquear=True)
            dispositivo.nombre = texto(nombre, 100)
            guardado = self.dispositivos.actualizar(dispositivo)
            self._auditar(actor_id, "EDITAR_DISPOSITIVO_EDGE", id_dispositivo)
            return guardado
        return self._transaccion(operacion)

    def cambiar_estado(self, *, actor_id: int, rol: str, id_dispositivo: int, estado: str) -> DispositivoEdge:
        self._autorizar(actor_id, rol)
        if not isinstance(estado, str) or estado not in ESTADOS:
            raise ValueError("Estado inválido.")
        def operacion():
            dispositivo = self.consultar(actor_id=actor_id, rol=rol, id_dispositivo=id_dispositivo,
                                          bloquear=True)
            dispositivo.estado = estado
            guardado = self.dispositivos.actualizar(dispositivo)
            self._auditar(actor_id, "CAMBIAR_ESTADO_DISPOSITIVO", id_dispositivo)
            return guardado
        return self._transaccion(operacion)

    def cambiar_modo(self, *, actor_id: int, rol: str, id_dispositivo: int, modo: str) -> DispositivoEdge:
        self._autorizar(actor_id, rol)
        if not isinstance(modo, str) or modo not in MODOS:
            raise ValueError("Modo inválido.")
        def operacion():
            dispositivo = self.consultar(actor_id=actor_id, rol=rol, id_dispositivo=id_dispositivo,
                                          bloquear=True)
            anterior = dispositivo.modo_operacion
            dispositivo.modo_operacion = modo
            guardado = self.dispositivos.actualizar(dispositivo)
            self._auditar(actor_id, "CAMBIAR_MODO_DISPOSITIVO", id_dispositivo,
                          json.dumps({"anterior": anterior, "nuevo": modo}, separators=(",", ":")))
            return guardado
        return self._transaccion(operacion)
