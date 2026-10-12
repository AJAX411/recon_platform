"""Crear TipoPersona y Persona con integridad y catálogo inicial.

Revision ID: 0001_personas
Revises:
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

revision = "0001_personas"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    id_entero = sa.Integer().with_variant(mysql.INTEGER(unsigned=True), "mysql")
    op.create_table(
        "tipo_persona",
        sa.Column("id_tipo_persona", id_entero, primary_key=True, autoincrement=True),
        sa.Column("nombre", sa.String(50), nullable=False),
        sa.Column("descripcion", sa.String(200), nullable=True),
        sa.Column("estado", sa.String(20), nullable=False),
        sa.UniqueConstraint("nombre", name="uq_tipo_persona_nombre"),
    )
    tabla_tipos = sa.table(
        "tipo_persona",
        sa.column("nombre", sa.String(50)),
        sa.column("estado", sa.String(20)),
    )
    op.bulk_insert(
        tabla_tipos,
        [
            {"nombre": nombre, "estado": "ACTIVO"}
            for nombre in (
                "ESTUDIANTE",
                "DOCENTE",
                "ADMINISTRATIVO",
                "SERVICIOS_GENERALES",
                "VISITANTE",
                "PERSONAL_SEGURIDAD",
            )
        ],
    )
    op.create_table(
        "persona",
        sa.Column("id_persona", id_entero, primary_key=True, autoincrement=True),
        sa.Column("id_tipo_persona", id_entero, nullable=False),
        sa.Column("identificador_institucional", sa.String(50), nullable=True),
        sa.Column("tipo_documento", sa.String(20), nullable=False),
        sa.Column("numero_documento", sa.String(30), nullable=False),
        sa.Column("primer_nombre", sa.String(100), nullable=False),
        sa.Column("segundo_nombre", sa.String(100), nullable=True),
        sa.Column("primer_apellido", sa.String(100), nullable=False),
        sa.Column("segundo_apellido", sa.String(100), nullable=True),
        sa.Column("estado", sa.String(20), nullable=False),
        sa.Column("fecha_creacion", sa.DateTime(), nullable=False),
        sa.Column("fecha_actualizacion", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["id_tipo_persona"],
            ["tipo_persona.id_tipo_persona"],
            name="fk_persona_tipo_persona",
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint(
            "identificador_institucional", name="uq_persona_identificador_institucional"
        ),
        sa.UniqueConstraint(
            "tipo_documento", "numero_documento", name="uq_persona_documento"
        ),
    )


def downgrade() -> None:
    op.drop_table("persona")
    op.drop_table("tipo_persona")
