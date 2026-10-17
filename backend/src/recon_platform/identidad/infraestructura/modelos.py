"""Persistencia inicial de Rol, UsuarioPlataforma y auditoría IAM."""

from datetime import UTC, datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects import mysql
from sqlalchemy.orm import Mapped, mapped_column, relationship

from recon_platform.extensions import db

ENTERO_ID = Integer().with_variant(mysql.INTEGER(unsigned=True), "mysql")


def _ahora_utc() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class RolModelo(db.Model):
    __tablename__ = "rol"
    __table_args__ = (
        UniqueConstraint("nombre", name="uq_rol_nombre"),
        CheckConstraint(
            "nombre IN ('SUPERADMIN', 'ADMINISTRADOR', 'OPERADOR')",
            name="ck_rol_nombre_aprobado",
        ),
    )

    id_rol: Mapped[int] = mapped_column(ENTERO_ID, primary_key=True, autoincrement=True)
    nombre: Mapped[str] = mapped_column(String(20), nullable=False)


class UsuarioPlataformaModelo(db.Model):
    __tablename__ = "usuario_plataforma"
    __table_args__ = (
        UniqueConstraint("login", name="uq_usuario_plataforma_login"),
        CheckConstraint(
            "estado IN ('ACTIVO', 'INACTIVO')",
            name="ck_usuario_plataforma_estado",
        ),
    )

    id_usuario: Mapped[int] = mapped_column(
        ENTERO_ID, primary_key=True, autoincrement=True
    )
    login: Mapped[str] = mapped_column(String(64), nullable=False)
    hash_contrasena: Mapped[str] = mapped_column(String(255), nullable=False)
    id_rol: Mapped[int] = mapped_column(
        ENTERO_ID,
        ForeignKey("rol.id_rol", name="fk_usuario_plataforma_rol", ondelete="RESTRICT"),
        nullable=False,
    )
    estado: Mapped[str] = mapped_column(String(20), nullable=False, default="ACTIVO")
    fecha_creacion: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), nullable=False, default=_ahora_utc
    )
    fecha_actualizacion: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), nullable=False, default=_ahora_utc, onupdate=_ahora_utc
    )

    rol: Mapped[RolModelo] = relationship(lazy="joined")


class AuditoriaIAMModelo(db.Model):
    __tablename__ = "auditoria_iam"

    id_auditoria: Mapped[int] = mapped_column(
        ENTERO_ID, primary_key=True, autoincrement=True
    )
    actor_id: Mapped[int | None] = mapped_column(
        ENTERO_ID,
        ForeignKey(
            "usuario_plataforma.id_usuario",
            name="fk_auditoria_iam_actor",
            ondelete="RESTRICT",
        ),
        nullable=True,
    )
    usuario_id: Mapped[int] = mapped_column(
        ENTERO_ID,
        ForeignKey(
            "usuario_plataforma.id_usuario",
            name="fk_auditoria_iam_usuario",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    accion: Mapped[str] = mapped_column(String(40), nullable=False)
    resultado: Mapped[str] = mapped_column(String(20), nullable=False)
    anterior: Mapped[str | None] = mapped_column(String(128), nullable=True)
    nuevo: Mapped[str | None] = mapped_column(String(128), nullable=True)
    fecha: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), nullable=False, default=_ahora_utc
    )


class SesionUsuarioModelo(db.Model):
    """Sesión HTTP; la clave primaria es el digest, nunca el token de la cookie."""

    __tablename__ = "sesion_usuario"

    digest: Mapped[str] = mapped_column(String(64), primary_key=True)
    id_usuario: Mapped[int | None] = mapped_column(
        ENTERO_ID,
        ForeignKey("usuario_plataforma.id_usuario", name="fk_sesion_usuario_cuenta", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    fecha_creacion: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False)
    fecha_actividad: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False)
    fecha_expiracion: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False)
    fecha_revocacion: Mapped[datetime | None] = mapped_column(DateTime(timezone=False), nullable=True)
