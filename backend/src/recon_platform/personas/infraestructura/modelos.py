"""Tablas SQLAlchemy de Persona y TipoPersona; no son entidades de dominio."""

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects import mysql
from sqlalchemy.orm import Mapped, mapped_column, relationship

from recon_platform.extensions import db

ENTERO_ID = Integer().with_variant(mysql.INTEGER(unsigned=True), "mysql")


def _ahora_utc_para_mysql() -> datetime:
    """MySQL DATETIME no conserva zona; persistimos valores convencionales UTC."""
    return datetime.now(UTC).replace(tzinfo=None)


class TipoPersonaModelo(db.Model):
    if TYPE_CHECKING:
        from typing import ClassVar
        from sqlalchemy import Table

        __table__: ClassVar[Table]

        def __init__(
            self,
            *,
            id_tipo_persona: int | None = None,
            nombre: str | None = None,
            descripcion: str | None = None,
            estado: str | None = None,
        ) -> None: ...

    __tablename__ = "tipo_persona"
    __table_args__ = (UniqueConstraint("nombre", name="uq_tipo_persona_nombre"),)

    id_tipo_persona: Mapped[int] = mapped_column(
        ENTERO_ID, primary_key=True, autoincrement=True
    )
    nombre: Mapped[str] = mapped_column(String(50), nullable=False)
    descripcion: Mapped[str | None] = mapped_column(String(200), nullable=True)
    estado: Mapped[str] = mapped_column(String(20), nullable=False, default="ACTIVO")


class PersonaModelo(db.Model):
    if TYPE_CHECKING:
        from typing import ClassVar
        from sqlalchemy import Table

        __table__: ClassVar[Table]

        def __init__(
            self,
            *,
            id_persona: int | None = None,
            id_tipo_persona: int | None = None,
            identificador_institucional: str | None = None,
            tipo_documento: str | None = None,
            numero_documento: str | None = None,
            primer_nombre: str | None = None,
            segundo_nombre: str | None = None,
            primer_apellido: str | None = None,
            segundo_apellido: str | None = None,
            estado: str | None = None,
            fecha_creacion: datetime | None = None,
            fecha_actualizacion: datetime | None = None,
            tipo_persona: TipoPersonaModelo | None = None,
        ) -> None: ...

    __tablename__ = "persona"
    __table_args__ = (
        UniqueConstraint(
            "identificador_institucional",
            name="uq_persona_identificador_institucional",
        ),
        UniqueConstraint(
            "tipo_documento", "numero_documento", name="uq_persona_documento"
        ),
    )

    id_persona: Mapped[int] = mapped_column(
        ENTERO_ID, primary_key=True, autoincrement=True
    )
    id_tipo_persona: Mapped[int] = mapped_column(
        ENTERO_ID,
        ForeignKey(
            "tipo_persona.id_tipo_persona",
            name="fk_persona_tipo_persona",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    identificador_institucional: Mapped[str | None] = mapped_column(
        String(50), nullable=True
    )
    tipo_documento: Mapped[str] = mapped_column(String(20), nullable=False)
    numero_documento: Mapped[str] = mapped_column(String(30), nullable=False)
    primer_nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    segundo_nombre: Mapped[str | None] = mapped_column(String(100), nullable=True)
    primer_apellido: Mapped[str] = mapped_column(String(100), nullable=False)
    segundo_apellido: Mapped[str | None] = mapped_column(String(100), nullable=True)
    estado: Mapped[str] = mapped_column(String(20), nullable=False, default="ACTIVO")
    fecha_creacion: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), nullable=False, default=_ahora_utc_para_mysql
    )
    fecha_actualizacion: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        nullable=False,
        default=_ahora_utc_para_mysql,
        onupdate=_ahora_utc_para_mysql,
    )

    tipo_persona: Mapped[TipoPersonaModelo] = relationship(lazy="joined")


class AuditoriaPersonasModelo(db.Model):
    """Traza mínima de cambios administrativos; sin instantáneas de datos personales."""

    if TYPE_CHECKING:
        from typing import ClassVar
        from sqlalchemy import Table

        __table__: ClassVar[Table]

        def __init__(
            self,
            *,
            id_auditoria: int | None = None,
            actor_id: int | None = None,
            id_persona: int | None = None,
            accion: str | None = None,
            fecha: datetime | None = None,
        ) -> None: ...


    __tablename__ = "auditoria_personas"
    __table_args__ = (CheckConstraint(
        "accion IN ('REGISTRAR_PERSONA', 'ACTUALIZAR_PERSONA', 'ACTIVAR_PERSONA', 'DESACTIVAR_PERSONA')",
        name="ck_auditoria_personas_accion",
    ),)

    id_auditoria: Mapped[int] = mapped_column(ENTERO_ID, primary_key=True, autoincrement=True)
    actor_id: Mapped[int] = mapped_column(ENTERO_ID, ForeignKey(
        "usuario_plataforma.id_usuario", name="fk_auditoria_personas_actor", ondelete="RESTRICT"
    ), nullable=False)
    id_persona: Mapped[int] = mapped_column(ENTERO_ID, ForeignKey(
        "persona.id_persona", name="fk_auditoria_personas_persona", ondelete="RESTRICT"
    ), nullable=False, index=True)
    accion: Mapped[str] = mapped_column(String(30), nullable=False)
    fecha: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False,
                                            default=_ahora_utc_para_mysql)
