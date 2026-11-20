"""Modelos ORM canónicos."""

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects import mysql
from sqlalchemy.orm import Mapped, mapped_column

from recon_platform.extensions import db

ENTERO_ID = Integer().with_variant(mysql.INTEGER(unsigned=True), "mysql")


def _ahora() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class EventoAuditoriaModelo(db.Model):
    if TYPE_CHECKING:
        from typing import ClassVar
        from sqlalchemy import Table

        __table__: ClassVar[Table]

        def __init__(
            self,
            *,
            id_auditoria: int | None = None,
            id_usuario_actor: int | None = None,
            tipo_actor: str | None = None,
            accion: str | None = None,
            recurso_tipo: str | None = None,
            id_recurso_afectado: str | None = None,
            resultado: str | None = None,
            detalle: str | None = None,
            fecha_hora: datetime | None = None,
        ) -> None: ...

    __tablename__ = "evento_auditoria"
    __table_args__ = (
        CheckConstraint("tipo_actor IN ('USUARIO', 'SISTEMA')", name="ck_evento_auditoria_tipo_actor"),
        CheckConstraint("resultado IN ('EXITOSO', 'FALLIDO')", name="ck_evento_auditoria_resultado"),
        CheckConstraint("(tipo_actor = 'USUARIO' AND id_usuario_actor IS NOT NULL) OR (tipo_actor = 'SISTEMA' AND id_usuario_actor IS NULL)", name="ck_evento_auditoria_actor"),
        Index("ix_evento_auditoria_recurso", "recurso_tipo", "id_recurso_afectado"),
    )

    id_auditoria: Mapped[int] = mapped_column(ENTERO_ID, primary_key=True, autoincrement=True)
    id_usuario_actor: Mapped[int | None] = mapped_column(ENTERO_ID, ForeignKey(
        "usuario_plataforma.id_usuario", name="fk_evento_auditoria_actor", ondelete="RESTRICT"), nullable=True, index=True)
    tipo_actor: Mapped[str] = mapped_column(String(20), nullable=False)
    accion: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    recurso_tipo: Mapped[str | None] = mapped_column(String(50), nullable=True)
    id_recurso_afectado: Mapped[str | None] = mapped_column(String(100), nullable=True)
    resultado: Mapped[str] = mapped_column(String(20), nullable=False)
    detalle: Mapped[str | None] = mapped_column(Text, nullable=True)
    fecha_hora: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False, default=_ahora, index=True)
