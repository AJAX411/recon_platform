"""Repositorios SQLAlchemy sin commits propios."""

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from flask_sqlalchemy.session import Session as SesionFlask
from sqlalchemy.orm import Session, scoped_session

from recon_platform.accesos.modelos_puntos import PuntoAccesoModelo, _ahora
from recon_platform.accesos.servicio_puntos import IntegridadPunto, PuntoDuplicado
from recon_platform.accesos.punto_acceso import PuntoAcceso


def _utc(valor: datetime) -> datetime:
    return valor.replace(tzinfo=UTC) if valor.tzinfo is None else valor.astimezone(UTC)


def _traducir(error: IntegrityError) -> ValueError:
    argumentos = getattr(error.orig, "args", ())
    if (argumentos and argumentos[0] == 1062) or "UNIQUE constraint failed" in str(error.orig):
        return PuntoDuplicado("Código de punto duplicado.")
    return IntegridadPunto("Persistencia de punto rechazada.")


class RepositorioPuntosSQLAlchemy:
    def __init__(self, sesion: Session | scoped_session[SesionFlask]) -> None:
        self.sesion = sesion

    def existe_codigo(self, codigo: str) -> bool:
        return self.sesion.scalar(select(PuntoAccesoModelo.id_punto_acceso).where(PuntoAccesoModelo.codigo == codigo)) is not None

    def agregar(self, punto: PuntoAcceso) -> PuntoAcceso:
        modelo = PuntoAccesoModelo(codigo=punto.codigo, nombre=punto.nombre,
                                  descripcion=punto.descripcion, estado=punto.estado)
        self.sesion.add(modelo)
        try:
            self.sesion.flush()
        except IntegrityError as error:
            raise _traducir(error) from error
        return self._dominio(modelo)

    def obtener(self, id_punto: int, *, bloquear: bool = False) -> PuntoAcceso | None:
        modelo = (self.sesion.scalar(select(PuntoAccesoModelo).where(
            PuntoAccesoModelo.id_punto_acceso == id_punto).with_for_update()
            .execution_options(populate_existing=True))
            if bloquear else self.sesion.get(PuntoAccesoModelo, id_punto))
        return self._dominio(modelo) if modelo is not None else None

    def listar(self, *, limite: int, desplazamiento: int, filtros: dict[str, str]) -> list[PuntoAcceso]:
        consulta = select(PuntoAccesoModelo)
        for campo, valor in filtros.items():
            consulta = consulta.where(getattr(PuntoAccesoModelo, campo) == valor)
        modelos = self.sesion.scalars(consulta.order_by(PuntoAccesoModelo.id_punto_acceso)
                                     .limit(limite).offset(desplazamiento)).all()
        return [self._dominio(modelo) for modelo in modelos]

    def actualizar(self, punto: PuntoAcceso) -> PuntoAcceso:
        modelo = self.sesion.get(PuntoAccesoModelo, punto.id_punto_acceso)
        if modelo is None:
            from recon_platform.accesos.servicio_puntos import PuntoNoExiste
            raise PuntoNoExiste("Punto inexistente.")
        if punto.codigo != modelo.codigo:
            raise ValueError("El código de PuntoAcceso es inmutable.")
        if (modelo.nombre, modelo.descripcion, modelo.estado) != (punto.nombre, punto.descripcion, punto.estado):
            modelo.nombre, modelo.descripcion, modelo.estado = punto.nombre, punto.descripcion, punto.estado
            modelo.fecha_actualizacion = _ahora()
        try:
            self.sesion.flush()
        except IntegrityError as error:
            raise _traducir(error) from error
        return self._dominio(modelo)

    @staticmethod
    def _dominio(modelo: PuntoAccesoModelo) -> PuntoAcceso:
        return PuntoAcceso(id_punto_acceso=modelo.id_punto_acceso, codigo=modelo.codigo,
                           nombre=modelo.nombre, descripcion=modelo.descripcion,
                           estado=modelo.estado, fecha_creacion=_utc(modelo.fecha_creacion),
                           fecha_actualizacion=_utc(modelo.fecha_actualizacion))
