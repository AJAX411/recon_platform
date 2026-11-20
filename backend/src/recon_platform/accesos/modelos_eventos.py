"""Mapeo ORM de EventoAcceso, sus referencias e idempotencia.
Describe restricciones persistidas; las reglas de secuencia viven en dominio."""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CHAR, CheckConstraint, DateTime, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.dialects import mysql
from sqlalchemy.orm import Mapped, mapped_column

from recon_platform.extensions import db

ENTERO_ID = Integer().with_variant(mysql.INTEGER(unsigned=True), "mysql")
CLAVE_UUID = CHAR(36).with_variant(mysql.CHAR(36, charset="ascii", collation="ascii_bin"), "mysql")
FECHA_UTC = DateTime().with_variant(mysql.DATETIME(fsp=6), "mysql")
MOVIMIENTO_SQL = String(10).with_variant(mysql.VARCHAR(10, charset="utf8mb4", collation="utf8mb4_bin"), "mysql")
RESULTADO_SQL = String(10).with_variant(mysql.VARCHAR(10, charset="utf8mb4", collation="utf8mb4_bin"), "mysql")
METODO_SQL = String(10).with_variant(mysql.VARCHAR(10, charset="utf8mb4", collation="utf8mb4_bin"), "mysql")
INCIDENCIA_SQL = String(40).with_variant(mysql.VARCHAR(40, charset="utf8mb4", collation="utf8mb4_bin"), "mysql")


class EventoAccesoModelo(db.Model):
    if TYPE_CHECKING:
        from typing import ClassVar
        from sqlalchemy import Table

        __table__: ClassVar[Table]

        def __init__(
            self,
            *,
            id_evento_acceso: int | None = None,
            id_persona: int | None = None,
            id_punto_acceso: int | None = None,
            tipo_movimiento: str | None = None,
            resultado: str | None = None,
            metodo_registro: str | None = None,
            id_usuario_registrador: int | None = None,
            fecha_hora_ocurrencia: datetime | None = None,
            tipo_incidencia_secuencia: str | None = None,
            id_dispositivo: int | None = None,
            clave_idempotencia: str | None = None,
        ) -> None: ...

    __tablename__ = "evento_acceso"
    __table_args__ = (
        CheckConstraint("tipo_movimiento IN ('ENTRADA', 'SALIDA')", name="ck_evento_acceso_movimiento"),
        CheckConstraint("resultado IN ('AUTORIZADO', 'RECHAZADO')", name="ck_evento_acceso_resultado"),
        CheckConstraint("metodo_registro IN ('MANUAL', 'FACIAL')", name="ck_evento_acceso_metodo"),
        CheckConstraint("tipo_incidencia_secuencia IS NULL OR tipo_incidencia_secuencia IN "
                        "('ENTRADA_REPETIDA', 'SALIDA_REPETIDA', 'SALIDA_SIN_ENTRADA_DEL_DIA')",
                        name="ck_evento_acceso_incidencia"),
        CheckConstraint("tipo_incidencia_secuencia IS NULL OR resultado = 'AUTORIZADO'",
                        name="ck_evento_acceso_incidencia_autorizada"),
        CheckConstraint("metodo_registro <> 'MANUAL' OR (id_persona IS NOT NULL AND "
                        "id_usuario_registrador IS NOT NULL AND id_dispositivo IS NULL AND "
                        "clave_idempotencia IS NOT NULL)", name="ck_evento_acceso_manual"),
        UniqueConstraint("clave_idempotencia", name="uq_evento_acceso_clave_idempotencia"),
        Index("ix_evento_acceso_secuencia", "id_persona", "resultado",
              "fecha_hora_ocurrencia", "id_evento_acceso"),
        Index("ix_evento_acceso_fecha", "fecha_hora_ocurrencia", "id_evento_acceso"),
        Index("ix_evento_acceso_alertas", "tipo_incidencia_secuencia",
              "fecha_hora_ocurrencia", "id_evento_acceso"),
        Index("ix_evento_acceso_punto_fecha", "id_punto_acceso", "fecha_hora_ocurrencia"),
        Index("ix_evento_acceso_registrador", "id_usuario_registrador"),
        Index("ix_evento_acceso_dispositivo", "id_dispositivo"),
        {"mysql_engine": "InnoDB"},
    )

    id_evento_acceso: Mapped[int] = mapped_column(ENTERO_ID, primary_key=True, autoincrement=True)
    id_persona: Mapped[int | None] = mapped_column(ENTERO_ID, ForeignKey(
        "persona.id_persona", name="fk_evento_acceso_persona", ondelete="RESTRICT"), nullable=True)
    id_punto_acceso: Mapped[int] = mapped_column(ENTERO_ID, ForeignKey(
        "punto_acceso.id_punto_acceso", name="fk_evento_acceso_punto", ondelete="RESTRICT"), nullable=False)
    tipo_movimiento: Mapped[str] = mapped_column(MOVIMIENTO_SQL, nullable=False)
    resultado: Mapped[str] = mapped_column(RESULTADO_SQL, nullable=False)
    metodo_registro: Mapped[str] = mapped_column(METODO_SQL, nullable=False)
    id_usuario_registrador: Mapped[int | None] = mapped_column(ENTERO_ID, ForeignKey(
        "usuario_plataforma.id_usuario", name="fk_evento_acceso_registrador", ondelete="RESTRICT"),
        nullable=True)
    fecha_hora_ocurrencia: Mapped[datetime] = mapped_column(FECHA_UTC, nullable=False)
    tipo_incidencia_secuencia: Mapped[str | None] = mapped_column(INCIDENCIA_SQL, nullable=True)
    id_dispositivo: Mapped[int | None] = mapped_column(ENTERO_ID, ForeignKey(
        "dispositivo_edge.id_dispositivo", name="fk_evento_acceso_dispositivo", ondelete="RESTRICT"),
        nullable=True)
    clave_idempotencia: Mapped[str | None] = mapped_column(CLAVE_UUID, nullable=True)
