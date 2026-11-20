"""Mapeo ORM del catálogo PuntoAcceso.
El modelo representa tablas; la entidad y el servicio validan cambios administrativos."""

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, Integer, String, UniqueConstraint
from sqlalchemy.dialects import mysql
from sqlalchemy.orm import Mapped, mapped_column

from recon_platform.extensions import db

ENTERO_ID = Integer().with_variant(mysql.INTEGER(unsigned=True), "mysql")


def _ahora() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class PuntoAccesoModelo(db.Model):
    if TYPE_CHECKING:
        from typing import ClassVar
        from sqlalchemy import Table

        __table__: ClassVar[Table]

        def __init__(
            self,
            *,
            id_punto_acceso: int | None = None,
            codigo: str | None = None,
            nombre: str | None = None,
            descripcion: str | None = None,
            estado: str | None = None,
            fecha_creacion: datetime | None = None,
            fecha_actualizacion: datetime | None = None,
        ) -> None: ...

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
