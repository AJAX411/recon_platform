"""Sesiones HTTP humanas persistidas del lado del servidor.

Revision ID: 0003_sesiones_iam
Revises: 0002_identity_iam
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

revision = "0003_sesiones_iam"
down_revision = "0002_identity_iam"
branch_labels = None
depends_on = None


def upgrade() -> None:
    id_entero = sa.Integer().with_variant(mysql.INTEGER(unsigned=True), "mysql")
    op.create_table(
        "sesion_usuario",
        sa.Column("digest", sa.String(64), primary_key=True),
        sa.Column("id_usuario", id_entero, nullable=True),
        sa.Column("fecha_creacion", sa.DateTime(), nullable=False),
        sa.Column("fecha_actividad", sa.DateTime(), nullable=False),
        sa.Column("fecha_expiracion", sa.DateTime(), nullable=False),
        sa.Column("fecha_revocacion", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["id_usuario"], ["usuario_plataforma.id_usuario"],
            name="fk_sesion_usuario_cuenta", ondelete="RESTRICT",
        ),
        mysql_engine="InnoDB",
    )
    op.create_index("ix_sesion_usuario_id_usuario", "sesion_usuario", ["id_usuario"])


def downgrade() -> None:
    op.drop_index("ix_sesion_usuario_id_usuario", table_name="sesion_usuario")
    op.drop_table("sesion_usuario")
