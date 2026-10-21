"""Persistencia de PuntoAcceso; sin commits propios."""

from datetime import UTC, datetime

from sqlalchemy import CheckConstraint, DateTime, Integer, String, UniqueConstraint, select
from sqlalchemy.dialects import mysql
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Mapped, Session, mapped_column

from recon_platform.accesos.aplicacion import IntegridadPunto, PuntoDuplicado
from recon_platform.accesos.dominio import PuntoAcceso
from recon_platform.extensions import db

ENTERO_ID = Integer().with_variant(mysql.INTEGER(unsigned=True), "mysql")


def _ahora() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _utc(valor: datetime) -> datetime:
    return valor.replace(tzinfo=UTC) if valor.tzinfo is None else valor.astimezone(UTC)


def _traducir(error: IntegrityError) -> ValueError:
    argumentos = getattr(error.orig, "args", ())
    if (argumentos and argumentos[0] == 1062) or "UNIQUE constraint failed" in str(error.orig):
        return PuntoDuplicado("Código de punto duplicado.")
    return IntegridadPunto("Persistencia de punto rechazada.")


class PuntoAccesoModelo(db.Model):
    __tablename__ = "punto_acceso"
    __table_args__ = (
        UniqueConstraint("codigo", name="uq_punto_acceso_codigo"),
        CheckConstraint("estado IN ('ACTIVO', 'INACTIVO')", name="ck_punto_acceso_estado"),
    )

    id_punto_acceso: Mapped[int] = mapped_column(ENTERO_ID, primary_key=True, autoincrement=True)
    codigo: Mapped[str] = mapped_column(String(20), nullable=False)
    nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    descripcion: Mapped[str | None] = mapped_column(String(150), nullable=True)
    estado: Mapped[str] = mapped_column(String(20), nullable=False, default="ACTIVO", index=True)
    fecha_creacion: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False, default=_ahora)
    fecha_actualizacion: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False, default=_ahora, onupdate=_ahora)


class RepositorioPuntosSQLAlchemy:
    def __init__(self, sesion: Session) -> None:
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
            from recon_platform.accesos.aplicacion import PuntoNoExiste
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
