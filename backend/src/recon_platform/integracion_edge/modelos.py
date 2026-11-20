"""Modelos ORM canónicos."""

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects import mysql
from sqlalchemy.orm import Mapped, mapped_column

from recon_platform.extensions import db

ENTERO_ID = Integer().with_variant(mysql.INTEGER(unsigned=True), "mysql")


def _ahora() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class DispositivoEdgeModelo(db.Model):
    if TYPE_CHECKING:
        from typing import ClassVar
        from sqlalchemy import Table

        __table__: ClassVar[Table]

        def __init__(
            self,
            *,
            id_dispositivo: int | None = None,
            id_punto_acceso: int | None = None,
            codigo: str | None = None,
            nombre: str | None = None,
            modo_operacion: str | None = None,
            estado: str | None = None,
            ultima_comunicacion: datetime | None = None,
            fecha_creacion: datetime | None = None,
            fecha_actualizacion: datetime | None = None,
        ) -> None: ...

    __tablename__ = "dispositivo_edge"
    __table_args__ = (
        UniqueConstraint("codigo", name="uq_dispositivo_edge_codigo"),
        CheckConstraint("estado IN ('ACTIVO', 'INACTIVO')", name="ck_dispositivo_edge_estado"),
        CheckConstraint("modo_operacion IN ('ENTRADA', 'SALIDA', 'AUTOMATICO')", name="ck_dispositivo_edge_modo"),
    )

    id_dispositivo: Mapped[int] = mapped_column(ENTERO_ID, primary_key=True, autoincrement=True)
    id_punto_acceso: Mapped[int] = mapped_column(ENTERO_ID, ForeignKey(
        "punto_acceso.id_punto_acceso", name="fk_dispositivo_edge_punto", ondelete="RESTRICT"), nullable=False, index=True)
    codigo: Mapped[str] = mapped_column(String(20), nullable=False)
    nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    modo_operacion: Mapped[str] = mapped_column(String(20), nullable=False)
    estado: Mapped[str] = mapped_column(String(20), nullable=False, default="INACTIVO", index=True)
    ultima_comunicacion: Mapped[datetime | None] = mapped_column(DateTime(timezone=False), nullable=True)
    fecha_creacion: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False, default=_ahora)
    fecha_actualizacion: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False, default=_ahora, onupdate=_ahora)
