"""Auditoría administrativa mínima de Personas.

Revision ID: 0004_auditoria_personas
Revises: 0003_sesiones_iam
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

revision = "0004_auditoria_personas"
down_revision = "0003_sesiones_iam"
branch_labels = None
depends_on = None


def upgrade() -> None:
    entero_id = sa.Integer().with_variant(mysql.INTEGER(unsigned=True), "mysql")
    op.create_table(
        "auditoria_personas",
        sa.Column("id_auditoria", entero_id, primary_key=True, autoincrement=True),
        sa.Column("actor_id", entero_id, nullable=False),
        sa.Column("id_persona", entero_id, nullable=False),
        sa.Column("accion", sa.String(30), nullable=False),
        sa.Column("fecha", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "accion IN ('REGISTRAR_PERSONA', 'ACTUALIZAR_PERSONA', 'ACTIVAR_PERSONA', 'DESACTIVAR_PERSONA')",
            name="ck_auditoria_personas_accion",
        ),
        sa.ForeignKeyConstraint(["actor_id"], ["usuario_plataforma.id_usuario"],
                                name="fk_auditoria_personas_actor", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["id_persona"], ["persona.id_persona"],
                                name="fk_auditoria_personas_persona", ondelete="RESTRICT"),
        mysql_engine="InnoDB",
    )
    op.create_index("ix_auditoria_personas_id_persona", "auditoria_personas", ["id_persona"])


def downgrade() -> None:
    op.drop_index("ix_auditoria_personas_id_persona", table_name="auditoria_personas")
    op.drop_table("auditoria_personas")
