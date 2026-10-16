"""Crear Rol, UsuarioPlataforma independiente y auditoría IAM.

Revision ID: 0002_identity_iam
Revises: 0001_personas
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

revision = "0002_identity_iam"
down_revision = "0001_personas"
branch_labels = None
depends_on = None


def upgrade() -> None:
    id_entero = sa.Integer().with_variant(mysql.INTEGER(unsigned=True), "mysql")
    op.create_table(
        "rol",
        sa.Column("id_rol", id_entero, primary_key=True, autoincrement=True),
        sa.Column("nombre", sa.String(20), nullable=False),
        sa.UniqueConstraint("nombre", name="uq_rol_nombre"),
        sa.CheckConstraint(
            "nombre IN ('SUPERADMIN', 'ADMINISTRADOR', 'OPERADOR')",
            name="ck_rol_nombre_aprobado",
        ),
    )
    roles = sa.table("rol", sa.column("nombre", sa.String(20)))
    op.bulk_insert(roles, [
        {"nombre": "SUPERADMIN"},
        {"nombre": "ADMINISTRADOR"},
        {"nombre": "OPERADOR"},
    ])
    op.create_table(
        "usuario_plataforma",
        sa.Column("id_usuario", id_entero, primary_key=True, autoincrement=True),
        sa.Column("login", sa.String(64), nullable=False),
        sa.Column("hash_contrasena", sa.String(255), nullable=False),
        sa.Column("id_rol", id_entero, nullable=False),
        sa.Column("estado", sa.String(20), nullable=False),
        sa.Column("fecha_creacion", sa.DateTime(), nullable=False),
        sa.Column("fecha_actualizacion", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["id_rol"], ["rol.id_rol"],
            name="fk_usuario_plataforma_rol", ondelete="RESTRICT",
        ),
        sa.UniqueConstraint("login", name="uq_usuario_plataforma_login"),
        sa.CheckConstraint(
            "estado IN ('ACTIVO', 'INACTIVO')",
            name="ck_usuario_plataforma_estado",
        ),
    )
    op.create_table(
        "auditoria_iam",
        sa.Column("id_auditoria", id_entero, primary_key=True, autoincrement=True),
        sa.Column("actor_id", id_entero, nullable=True),
        sa.Column("usuario_id", id_entero, nullable=False),
        sa.Column("accion", sa.String(40), nullable=False),
        sa.Column("resultado", sa.String(20), nullable=False),
        sa.Column("anterior", sa.String(128), nullable=True),
        sa.Column("nuevo", sa.String(128), nullable=True),
        sa.Column("fecha", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["actor_id"], ["usuario_plataforma.id_usuario"],
            name="fk_auditoria_iam_actor", ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["usuario_id"], ["usuario_plataforma.id_usuario"],
            name="fk_auditoria_iam_usuario", ondelete="RESTRICT",
        ),
    )


def downgrade() -> None:
    op.drop_table("auditoria_iam")
    op.drop_table("usuario_plataforma")
    op.drop_table("rol")
