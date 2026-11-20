"""Repositorios SQLAlchemy sin commits propios."""

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from flask_sqlalchemy.session import Session as SesionFlask
from sqlalchemy.orm import Session, scoped_session

from recon_platform.integracion_edge.modelos import DispositivoEdgeModelo, _ahora
from recon_platform.accesos.modelos_puntos import PuntoAccesoModelo
from recon_platform.integracion_edge.servicio import DispositivoDuplicado, DispositivoNoExiste, IntegridadDispositivo, PuntoAsociadoNoExiste
from recon_platform.integracion_edge.dispositivo_edge import DispositivoEdge


def _utc(valor: datetime | None) -> datetime | None:
    return None if valor is None else valor.replace(tzinfo=UTC) if valor.tzinfo is None else valor.astimezone(UTC)


def _traducir(error: IntegrityError) -> ValueError:
    argumentos = getattr(error.orig, "args", ())
    codigo = argumentos[0] if argumentos else None
    if codigo == 1062 or "UNIQUE constraint failed" in str(error.orig):
        return DispositivoDuplicado("Código de dispositivo duplicado.")
    if codigo == 1452 or "FOREIGN KEY constraint failed" in str(error.orig):
        return PuntoAsociadoNoExiste("Punto asociado inexistente.")
    return IntegridadDispositivo("Persistencia de dispositivo rechazada.")


class ConsultaPuntosSQLAlchemy:
    """Implementa el puerto de Integración Edge; no usa repositorios de Accesos."""
    def __init__(self, sesion: Session | scoped_session[SesionFlask]) -> None:
        self.sesion = sesion

    def existe(self, id_punto: int) -> bool:
        return self.sesion.scalar(select(PuntoAccesoModelo.id_punto_acceso).where(
            PuntoAccesoModelo.id_punto_acceso == id_punto)) is not None


class RepositorioDispositivosSQLAlchemy:
    def __init__(self, sesion: Session | scoped_session[SesionFlask]) -> None:
        self.sesion = sesion

    def existe_codigo(self, codigo: str) -> bool:
        return self.sesion.scalar(select(DispositivoEdgeModelo.id_dispositivo).where(
            DispositivoEdgeModelo.codigo == codigo)) is not None

    def agregar(self, dispositivo: DispositivoEdge) -> DispositivoEdge:
        modelo = DispositivoEdgeModelo(id_punto_acceso=dispositivo.id_punto_acceso,
            codigo=dispositivo.codigo, nombre=dispositivo.nombre,
            modo_operacion=dispositivo.modo_operacion, estado=dispositivo.estado)
        self.sesion.add(modelo)
        try:
            self.sesion.flush()
        except IntegrityError as error:
            raise _traducir(error) from error
        return self._dominio(modelo)

    def obtener(self, id_dispositivo: int, *, bloquear: bool = False) -> DispositivoEdge | None:
        modelo = (self.sesion.scalar(select(DispositivoEdgeModelo).where(
            DispositivoEdgeModelo.id_dispositivo == id_dispositivo).with_for_update()
            .execution_options(populate_existing=True))
            if bloquear else self.sesion.get(DispositivoEdgeModelo, id_dispositivo))
        return self._dominio(modelo) if modelo is not None else None

    def listar(self, *, limite: int, desplazamiento: int, filtros: dict) -> list[DispositivoEdge]:
        consulta = select(DispositivoEdgeModelo)
        for campo, valor in filtros.items():
            consulta = consulta.where(getattr(DispositivoEdgeModelo, campo) == valor)
        modelos = self.sesion.scalars(consulta.order_by(DispositivoEdgeModelo.id_dispositivo)
                                     .limit(limite).offset(desplazamiento)).all()
        return [self._dominio(modelo) for modelo in modelos]

    def actualizar(self, dispositivo: DispositivoEdge) -> DispositivoEdge:
        modelo = self.sesion.get(DispositivoEdgeModelo, dispositivo.id_dispositivo)
        if modelo is None:
            raise DispositivoNoExiste("Dispositivo inexistente.")
        if (dispositivo.codigo != modelo.codigo or
            dispositivo.id_punto_acceso != modelo.id_punto_acceso or
            dispositivo.ultima_comunicacion != _utc(modelo.ultima_comunicacion)):
            raise ValueError("Código, punto y comunicación no son editables administrativamente.")
        if ((modelo.nombre, modelo.modo_operacion, modelo.estado) !=
            (dispositivo.nombre, dispositivo.modo_operacion, dispositivo.estado)):
            modelo.nombre, modelo.modo_operacion, modelo.estado = (
                dispositivo.nombre, dispositivo.modo_operacion, dispositivo.estado)
            modelo.fecha_actualizacion = _ahora()
        try:
            self.sesion.flush()
        except IntegrityError as error:
            raise _traducir(error) from error
        return self._dominio(modelo)

    @staticmethod
    def _dominio(modelo: DispositivoEdgeModelo) -> DispositivoEdge:
        return DispositivoEdge(id_dispositivo=modelo.id_dispositivo,
            id_punto_acceso=modelo.id_punto_acceso, codigo=modelo.codigo,
            nombre=modelo.nombre, modo_operacion=modelo.modo_operacion, estado=modelo.estado,
            ultima_comunicacion=_utc(modelo.ultima_comunicacion),
            fecha_creacion=_utc(modelo.fecha_creacion), fecha_actualizacion=_utc(modelo.fecha_actualizacion))
